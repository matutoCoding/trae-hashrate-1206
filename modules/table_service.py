from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from database.models import MahjongTable, TableStatus, Booking, BookingStatus
from database.db import get_db


class TableService:
    def __init__(self, db: Session):
        self.db = db

    def create_table(self, table_number: str, hourly_rate: float, **kwargs) -> MahjongTable:
        existing = self.db.query(MahjongTable).filter(MahjongTable.table_number == table_number).first()
        if existing:
            raise ValueError(f"桌号 {table_number} 已存在")

        table = MahjongTable(
            table_number=table_number,
            hourly_rate=hourly_rate,
            name=kwargs.get("name", table_number),
            room_type=kwargs.get("room_type"),
            minimum_hours=kwargs.get("minimum_hours", 1.0),
            max_people=kwargs.get("max_people", 4),
            machine_model=kwargs.get("machine_model"),
            purchase_date=kwargs.get("purchase_date"),
            location=kwargs.get("location"),
            description=kwargs.get("description"),
            status=TableStatus.IDLE,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(table)
        self.db.commit()
        self.db.refresh(table)
        return table

    def get_table(self, table_id: int) -> Optional[MahjongTable]:
        return self.db.query(MahjongTable).filter(MahjongTable.id == table_id).first()

    def get_all_tables(self) -> List[MahjongTable]:
        return self.db.query(MahjongTable).order_by(MahjongTable.table_number).all()

    def get_available_tables(self, booking_date: date, start_time, end_time) -> List[MahjongTable]:
        all_tables = self.get_all_tables()
        available = []
        for table in all_tables:
            if table.status == TableStatus.MAINTENANCE:
                continue
            if not self._check_conflict(table.id, booking_date, start_time, end_time):
                available.append(table)
        return available

    def update_table(self, table_id: int, **kwargs) -> Optional[MahjongTable]:
        table = self.get_table(table_id)
        if not table:
            return None

        for key, value in kwargs.items():
            if hasattr(table, key) and value is not None:
                setattr(table, key, value)
        table.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(table)
        return table

    def delete_table(self, table_id: int) -> bool:
        table = self.get_table(table_id)
        if not table:
            return False
        self.db.delete(table)
        self.db.commit()
        return True

    def update_table_status(self, table_id: int, status: TableStatus) -> Optional[MahjongTable]:
        return self.update_table(table_id, status=status)

    def get_table_schedule(self, table_id: int, start_date: date, end_date: date) -> List[Booking]:
        return self.db.query(Booking).filter(
            Booking.table_id == table_id,
            Booking.booking_date >= start_date,
            Booking.booking_date <= end_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS])
        ).order_by(Booking.booking_date, Booking.start_time).all()

    def _check_conflict(self, table_id: int, booking_date: date, start_time, end_time) -> bool:
        from datetime import datetime as dt, timedelta

        bookings = self.db.query(Booking).filter(
            Booking.table_id == table_id,
            Booking.booking_date == booking_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED, BookingStatus.IN_PROGRESS])
        ).all()

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
                return True
        return False
