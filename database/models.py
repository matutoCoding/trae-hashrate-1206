from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Time, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from database.db import Base
import enum


class TableStatus(str, enum.Enum):
    IDLE = "空闲"
    OCCUPIED = "占用中"
    RESERVED = "已预订"
    MAINTENANCE = "维护中"


class BookingStatus(str, enum.Enum):
    PENDING = "待确认"
    CONFIRMED = "已确认"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"


class CouponType(str, enum.Enum):
    DISCOUNT = "折扣券"
    DEDUCTION = "满减券"


class DiscountApplyOrder(str, enum.Enum):
    DISCOUNT_FIRST = "先折扣后满减"
    DEDUCTION_FIRST = "先满减后折扣"


class InspectionStatus(str, enum.Enum):
    PENDING = "待点检"
    NORMAL = "正常"
    ABNORMAL = "异常"
    REPAIRED = "已维修"


class MemberLevel(str, enum.Enum):
    NORMAL = "普通会员"
    SILVER = "银卡会员"
    GOLD = "金卡会员"
    DIAMOND = "钻石会员"


class MahjongTable(Base):
    __tablename__ = "mahjong_tables"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(String(20), unique=True, nullable=False)
    name = Column(String(50))
    room_type = Column(String(50))
    hourly_rate = Column(Float, nullable=False)
    minimum_hours = Column(Float, default=1.0)
    max_people = Column(Integer, default=4)
    machine_model = Column(String(100))
    purchase_date = Column(Date)
    status = Column(Enum(TableStatus), default=TableStatus.IDLE)
    location = Column(String(100))
    description = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    bookings = relationship("Booking", back_populates="table")
    inspections = relationship("MachineInspection", back_populates="table")


class CycleRule(Base):
    __tablename__ = "cycle_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20))
    table_id = Column(Integer, ForeignKey("mahjong_tables.id"))
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    people_count = Column(Integer, default=4)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    repeat_weeks = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime)

    generated_bookings = relationship("Booking", back_populates="cycle_rule")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("mahjong_tables.id"), nullable=False)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20))
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    people_count = Column(Integer, default=4)
    total_hours = Column(Float)
    base_amount = Column(Float)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    cycle_rule_id = Column(Integer, ForeignKey("cycle_rules.id"))
    is_from_cycle = Column(Boolean, default=False)
    note = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    table = relationship("MahjongTable", back_populates="bookings")
    cycle_rule = relationship("CycleRule", back_populates="generated_bookings")
    bill = relationship("Bill", back_populates="booking", uselist=False)


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(Enum(CouponType), nullable=False)
    discount_value = Column(Float)
    min_consumption = Column(Float, default=0)
    max_discount = Column(Float)
    valid_from = Column(Date)
    valid_to = Column(Date)
    total_quantity = Column(Integer, default=1)
    used_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime)


class DiscountOrderConfig(Base):
    __tablename__ = "discount_order_config"

    id = Column(Integer, primary_key=True, index=True)
    apply_order = Column(Enum(DiscountApplyOrder), default=DiscountApplyOrder.DISCOUNT_FIRST)
    allow_negative = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime)


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    bill_no = Column(String(50), unique=True, nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    table_number = Column(String(20))
    customer_name = Column(String(100))
    checkin_time = Column(DateTime)
    checkout_time = Column(DateTime)
    total_hours = Column(Float)
    hourly_rate = Column(Float)
    base_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0)
    final_amount = Column(Float, nullable=False)
    payment_method = Column(String(50))
    member_id = Column(Integer, ForeignKey("members.id"))
    is_paid = Column(Boolean, default=False)
    note = Column(Text)
    created_at = Column(DateTime)
    paid_at = Column(DateTime)

    booking = relationship("Booking", back_populates="bill")
    discounts = relationship("BillDiscount", back_populates="bill", cascade="all, delete-orphan")


class BillDiscount(Base):
    __tablename__ = "bill_discounts"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("coupons.id"))
    coupon_name = Column(String(100))
    coupon_type = Column(String(50))
    discount_value = Column(Float)
    applied_amount = Column(Float)
    apply_order = Column(Integer)

    bill = relationship("Bill", back_populates="discounts")


class MachineInspection(Base):
    __tablename__ = "machine_inspections"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("mahjong_tables.id"), nullable=False)
    inspection_date = Column(Date, nullable=False)
    inspector = Column(String(100))
    status = Column(Enum(InspectionStatus), default=InspectionStatus.PENDING)
    tiles_complete = Column(Boolean)
    dice_normal = Column(Boolean)
    power_supply_normal = Column(Boolean)
    operation_normal = Column(Boolean)
    cleaning_done = Column(Boolean)
    issues_found = Column(Text)
    actions_taken = Column(Text)
    next_inspection_date = Column(Date)
    remark = Column(Text)
    created_at = Column(DateTime)

    table = relationship("MahjongTable", back_populates="inspections")


class RechargePackage(Base):
    __tablename__ = "recharge_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    recharge_amount = Column(Float, nullable=False)
    bonus_amount = Column(Float, default=0.0)
    description = Column(String(200))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    level = Column(Enum(MemberLevel), default=MemberLevel.NORMAL)
    balance = Column(Float, default=0.0)
    total_consumption = Column(Float, default=0.0)
    total_saved = Column(Float, default=0.0)
    visit_count = Column(Integer, default=0)
    remark = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    consumptions = relationship("MemberConsumption", back_populates="member")


class MemberConsumption(Base):
    __tablename__ = "member_consumptions"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    bill_id = Column(Integer, ForeignKey("bills.id"))
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float)
    balance_after = Column(Float)
    description = Column(String(200))
    bill_no = Column(String(50))
    table_number = Column(String(20))
    recharge_amount = Column(Float, default=0.0)
    bonus_amount = Column(Float, default=0.0)
    member_discount = Column(Float, default=0.0)
    coupon_discount = Column(Float, default=0.0)
    discount_detail = Column(Text)
    created_at = Column(DateTime)

    member = relationship("Member", back_populates="consumptions")
    bill = relationship("Bill")
