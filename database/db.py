from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

Base = declarative_base()

db_path = Path(__file__).parent.parent / "mahjong_room.db"
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from database.models import (MahjongTable, CycleRule, Booking, Coupon,
                                  DiscountOrderConfig, Bill, BillDiscount,
                                  MachineInspection, Member, MemberConsumption)
    Base.metadata.create_all(bind=engine)
