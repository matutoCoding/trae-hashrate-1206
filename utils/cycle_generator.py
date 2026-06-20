from dataclasses import dataclass
from typing import List, Optional
from datetime import date, time, datetime, timedelta
from dateutil import rrule
from dateutil.parser import parse as dateparse


@dataclass
class CycleRuleInput:
    name: str
    customer_name: str
    customer_phone: str
    table_id: int
    day_of_week: int
    start_time: time
    end_time: time
    people_count: int
    start_date: date
    end_date: Optional[date] = None
    repeat_weeks: int = 1
    description: str = ""


@dataclass
class GeneratedBooking:
    table_id: int
    customer_name: str
    customer_phone: str
    booking_date: date
    start_time: time
    end_time: time
    people_count: int
    total_hours: float
    base_amount: float
    cycle_rule_id: Optional[int] = None
    note: str = ""


class CycleBookingGenerator:
    def __init__(self, hourly_rate: float, minimum_hours: float = 1.0):
        self.hourly_rate = hourly_rate
        self.minimum_hours = minimum_hours

    def generate(self, rule: CycleRuleInput,
                 check_conflict_func=None) -> List[GeneratedBooking]:
        if rule.end_date:
            end_date = rule.end_date
        else:
            end_date = rule.start_date + timedelta(weeks=52)

        bookings = []
        byweekday = rule.day_of_week - 1 if rule.day_of_week >= 1 else 6

        for dt in rrule.rrule(
            rrule.WEEKLY,
            dtstart=rule.start_date,
            until=end_date,
            byweekday=byweekday,
            interval=rule.repeat_weeks
        ):
            booking_date = dt.date()

            total_hours = self._calculate_hours(rule.start_time, rule.end_time)
            if total_hours < self.minimum_hours:
                total_hours = self.minimum_hours

            base_amount = round(total_hours * self.hourly_rate, 2)

            booking = GeneratedBooking(
                table_id=rule.table_id,
                customer_name=rule.customer_name,
                customer_phone=rule.customer_phone,
                booking_date=booking_date,
                start_time=rule.start_time,
                end_time=rule.end_time,
                people_count=rule.people_count,
                total_hours=total_hours,
                base_amount=base_amount,
                note=f"周期生成: {rule.name}"
            )

            if check_conflict_func:
                if check_conflict_func(booking):
                    continue

            bookings.append(booking)

        return bookings

    def _calculate_hours(self, start: time, end: time) -> float:
        start_dt = datetime.combine(date.today(), start)
        end_dt = datetime.combine(date.today(), end)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        delta = end_dt - start_dt
        hours = delta.total_seconds() / 3600
        return round(hours, 2)

    def check_time_conflict(self, booking: GeneratedBooking, existing_bookings) -> bool:
        for existing in existing_bookings:
            if existing.table_id != booking.table_id:
                continue
            if existing.booking_date != booking.booking_date:
                continue

            existing_start = datetime.combine(existing.booking_date, existing.start_time)
            existing_end = datetime.combine(existing.booking_date, existing.end_time)
            if existing_end <= existing_start:
                existing_end += timedelta(days=1)

            new_start = datetime.combine(booking.booking_date, booking.start_time)
            new_end = datetime.combine(booking.booking_date, booking.end_time)
            if new_end <= new_start:
                new_end += timedelta(days=1)

            if not (new_end <= existing_start or new_start >= existing_end):
                return True

        return False


def generate_booking_no(rule_id: int, booking_date: date, seq: int = 0) -> str:
    return f"B{rule_id:04d}{booking_date.strftime('%Y%m%d')}{seq:02d}"
