from typing import List, Optional
from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from database.models import Booking, BookingStatus, MahjongTable, TableStatus
from database.db import get_db


class BookingService:
    def __init__(self, db: Session):
        self.db = db

    def check_conflict(self, table_id: int, booking_date: date,
                       start_time: time, end_time: time,
                       exclude_booking_id: int = None) -> Optional[Booking]:
        from datetime import datetime as dt

        bookings = self.db.query(Booking).filter(
            Booking.table_id == table_id,
            Booking.booking_date == booking_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS])
        ).all()

        if exclude_booking_id:
            bookings = [b for b in bookings if b.id != exclude_booking_id]

        new_start = dt.combine(booking_date, start_time)
        new_end = dt.combine(booking_date, end_time)
        if new_end <= new_start:
            new_end += timedelta(days=1)

        for booking in bookings:
            exist_start = dt.combine(booking.booking_date, booking.start_time)
            exist_end = dt.combine(booking.booking_date, booking.end_time)
            if exist_end <= exist_start:
                exist_end += timedelta(days=1)

            if not (new_end <= exist_start or new_start >= exist_end):
                return booking
        return None

    def create_booking(self, table_id: int, customer_name: str,
                       booking_date: date, start_time: time, end_time: time,
                       check_conflict: bool = True, **kwargs) -> Booking:
        from modules.table_service import TableService
        table_service = TableService(self.db)
        table = table_service.get_table(table_id)
        if not table:
            raise ValueError("麻将桌不存在")

        if check_conflict:
            conflict = self.check_conflict(table_id, booking_date, start_time, end_time)
            if conflict:
                conflict_time = f"{conflict.start_time.strftime('%H:%M')}-{conflict.end_time.strftime('%H:%M')}"
                raise ValueError(f"时间冲突！该麻将桌在 {conflict.booking_date} {conflict_time} 已有预订（客人：{conflict.customer_name}）")

        total_hours = self._calculate_hours(start_time, end_time)
        if total_hours < table.minimum_hours:
            total_hours = table.minimum_hours

        base_amount = round(total_hours * table.hourly_rate, 2)

        booking = Booking(
            table_id=table_id,
            customer_name=customer_name,
            customer_phone=kwargs.get("customer_phone"),
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            people_count=kwargs.get("people_count", 4),
            total_hours=total_hours,
            base_amount=base_amount,
            status=kwargs.get("status", BookingStatus.CONFIRMED),
            cycle_rule_id=kwargs.get("cycle_rule_id"),
            is_from_cycle=kwargs.get("is_from_cycle", False),
            note=kwargs.get("note"),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_booking(self, booking_id: int) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

    def get_bookings_by_date(self, booking_date: date) -> List[Booking]:
        return self.db.query(Booking).filter(
            Booking.booking_date == booking_date
        ).order_by(Booking.start_time).all()

    def get_bookings_by_table(self, table_id: int, start_date: date = None,
                              end_date: date = None) -> List[Booking]:
        query = self.db.query(Booking).filter(Booking.table_id == table_id)
        if start_date:
            query = query.filter(Booking.booking_date >= start_date)
        if end_date:
            query = query.filter(Booking.booking_date <= end_date)
        return query.order_by(Booking.booking_date, Booking.start_time).all()

    def get_bookings_by_cycle(self, cycle_rule_id: int) -> List[Booking]:
        return self.db.query(Booking).filter(
            Booking.cycle_rule_id == cycle_rule_id
        ).order_by(Booking.booking_date, Booking.start_time).all()

    def update_booking(self, booking_id: int, check_conflict: bool = True, **kwargs) -> Optional[Booking]:
        booking = self.get_booking(booking_id)
        if not booking:
            return None

        new_table_id = kwargs.get("table_id", booking.table_id)
        new_date = kwargs.get("booking_date", booking.booking_date)
        new_start = kwargs.get("start_time", booking.start_time)
        new_end = kwargs.get("end_time", booking.end_time)

        if check_conflict and (
            "table_id" in kwargs or "booking_date" in kwargs or
            "start_time" in kwargs or "end_time" in kwargs
        ):
            conflict = self.check_conflict(new_table_id, new_date, new_start, new_end,
                                            exclude_booking_id=booking_id)
            if conflict:
                conflict_time = f"{conflict.start_time.strftime('%H:%M')}-{conflict.end_time.strftime('%H:%M')}"
                raise ValueError(f"时间冲突！该麻将桌在 {conflict.booking_date} {conflict_time} 已有预订（客人：{conflict.customer_name}）")

        for key, value in kwargs.items():
            if hasattr(booking, key) and value is not None:
                setattr(booking, key, value)

        if "start_time" in kwargs or "end_time" in kwargs or "table_id" in kwargs:
            table = self.db.query(MahjongTable).filter(MahjongTable.id == booking.table_id).first()
            if table:
                total_hours = self._calculate_hours(booking.start_time, booking.end_time)
                if total_hours < table.minimum_hours:
                    total_hours = table.minimum_hours
                booking.total_hours = total_hours
                booking.base_amount = round(total_hours * table.hourly_rate, 2)

        booking.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def cancel_booking(self, booking_id: int) -> Optional[Booking]:
        return self.update_booking(booking_id, status=BookingStatus.CANCELLED)

    def delete_booking(self, booking_id: int) -> bool:
        booking = self.get_booking(booking_id)
        if not booking:
            return False
        self.db.delete(booking)
        self.db.commit()
        return True

    def check_in(self, booking_id: int) -> Optional[Booking]:
        booking = self.get_booking(booking_id)
        if not booking:
            return None
        if booking.status not in [BookingStatus.PENDING, BookingStatus.CONFIRMED]:
            raise ValueError(f"预订状态为「{booking.status.value}」，无法入住")

        booking.status = BookingStatus.IN_PROGRESS
        booking.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(booking)

        from modules.table_service import TableService
        TableService(self.db).update_table_status(booking.table_id, TableStatus.OCCUPIED)
        return booking

    def check_out(self, booking_id: int) -> Optional[Booking]:
        booking = self.get_booking(booking_id)
        if not booking:
            return None

        booking.status = BookingStatus.COMPLETED
        booking.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(booking)

        from modules.table_service import TableService
        TableService(self.db).update_table_status(booking.table_id, TableStatus.IDLE)
        return booking

    def _calculate_hours(self, start: time, end: time) -> float:
        start_dt = datetime.combine(date.today(), start)
        end_dt = datetime.combine(date.today(), end)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        delta = end_dt - start_dt
        hours = delta.total_seconds() / 3600
        return round(hours, 2)
