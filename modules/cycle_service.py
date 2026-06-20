from typing import List, Optional, Tuple
from datetime import datetime, date, time
from sqlalchemy.orm import Session
from database.models import CycleRule, Booking, BookingStatus
from utils.cycle_generator import CycleBookingGenerator, CycleRuleInput, GeneratedBooking


class CycleService:
    def __init__(self, db: Session):
        self.db = db

    def create_cycle_rule(self, name: str, customer_name: str, table_id: int,
                          day_of_week: int, start_time: time, end_time: time,
                          start_date: date, **kwargs) -> CycleRule:
        rule = CycleRule(
            name=name,
            customer_name=customer_name,
            customer_phone=kwargs.get("customer_phone"),
            table_id=table_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            people_count=kwargs.get("people_count", 4),
            start_date=start_date,
            end_date=kwargs.get("end_date"),
            repeat_weeks=kwargs.get("repeat_weeks", 1),
            is_active=kwargs.get("is_active", True),
            description=kwargs.get("description"),
            created_at=datetime.now()
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_cycle_rule(self, rule_id: int) -> Optional[CycleRule]:
        return self.db.query(CycleRule).filter(CycleRule.id == rule_id).first()

    def get_all_cycle_rules(self, only_active: bool = False) -> List[CycleRule]:
        query = self.db.query(CycleRule)
        if only_active:
            query = query.filter(CycleRule.is_active == True)
        return query.order_by(CycleRule.created_at.desc()).all()

    def update_cycle_rule(self, rule_id: int, **kwargs) -> Optional[CycleRule]:
        rule = self.get_cycle_rule(rule_id)
        if not rule:
            return None

        for key, value in kwargs.items():
            if hasattr(rule, key) and value is not None:
                setattr(rule, key, value)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_cycle_rule(self, rule_id: int, delete_generated: bool = False) -> bool:
        rule = self.get_cycle_rule(rule_id)
        if not rule:
            return False

        if delete_generated:
            bookings = self.db.query(Booking).filter(
                Booking.cycle_rule_id == rule_id,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
            ).all()
            for booking in bookings:
                self.db.delete(booking)

        self.db.delete(rule)
        self.db.commit()
        return True

    def preview_generated_bookings(self, rule_id: int) -> Tuple[List[GeneratedBooking], List[str]]:
        rule = self.get_cycle_rule(rule_id)
        if not rule:
            return [], []

        from modules.table_service import TableService
        table = TableService(self.db).get_table(rule.table_id)
        if not table:
            return [], ["麻将桌不存在"]

        generator = CycleBookingGenerator(table.hourly_rate, table.minimum_hours)
        rule_input = CycleRuleInput(
            name=rule.name,
            customer_name=rule.customer_name,
            customer_phone=rule.customer_phone or "",
            table_id=rule.table_id,
            day_of_week=rule.day_of_week,
            start_time=rule.start_time,
            end_time=rule.end_time,
            people_count=rule.people_count,
            start_date=rule.start_date,
            end_date=rule.end_date,
            repeat_weeks=rule.repeat_weeks,
            description=rule.description or ""
        )

        existing_bookings = self.db.query(Booking).filter(
            Booking.table_id == rule.table_id,
            Booking.booking_date >= rule.start_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS])
        ).all()

        conflicts = []

        def check_conflict(booking):
            has_conflict = generator.check_time_conflict(booking, existing_bookings)
            if has_conflict:
                conflicts.append(f"{booking.booking_date} {booking.start_time}-{booking.end_time} 与现有预订冲突")
            return has_conflict

        bookings = generator.generate(rule_input, check_conflict)
        return bookings, conflicts

    def generate_bookings(self, rule_id: int, skip_conflicts: bool = True) -> Tuple[int, List[str]]:
        rule = self.get_cycle_rule(rule_id)
        if not rule:
            return 0, ["周期规则不存在"]

        preview_bookings, conflicts = self.preview_generated_bookings(rule_id)

        if not skip_conflicts and conflicts:
            return 0, conflicts

        from modules.booking_service import BookingService
        booking_service = BookingService(self.db)

        created_count = 0
        messages = []

        for preview in preview_bookings:
            try:
                booking = booking_service.create_booking(
                    table_id=preview.table_id,
                    customer_name=preview.customer_name,
                    booking_date=preview.booking_date,
                    start_time=preview.start_time,
                    end_time=preview.end_time,
                    customer_phone=preview.customer_phone,
                    people_count=preview.people_count,
                    cycle_rule_id=rule_id,
                    is_from_cycle=True,
                    note=preview.note
                )
                created_count += 1
            except Exception as e:
                messages.append(f"生成 {preview.booking_date} 预订失败: {str(e)}")

        messages.append(f"成功生成 {created_count} 条预订")
        if conflicts:
            messages.append(f"跳过 {len(conflicts)} 条冲突预订")

        return created_count, messages

    def generate_all_active_cycles(self) -> Tuple[int, List[str]]:
        rules = self.get_all_cycle_rules(only_active=True)
        total_created = 0
        all_messages = []

        for rule in rules:
            count, messages = self.generate_bookings(rule.id, skip_conflicts=True)
            total_created += count
            all_messages.extend([f"[{rule.name}] {msg}" for msg in messages])

        return total_created, all_messages
