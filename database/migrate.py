from sqlalchemy import text, inspect
from database.db import engine, Base, SessionLocal
from database.models import (MahjongTable, CycleRule, Booking, Coupon,
                              DiscountOrderConfig, Bill, BillDiscount,
                              MachineInspection, Member, MemberConsumption,
                              RechargePackage)


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return False
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def _table_exists(table_name: str) -> bool:
    inspector = inspect(engine)
    return inspector.has_table(table_name)


def upgrade_database():
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        _upgrade_members_table(conn)
        _upgrade_bills_table(conn)
        _upgrade_member_consumptions_table(conn)
        _init_recharge_packages(conn)
        _init_member_level_defaults(conn)


def _upgrade_members_table(conn):
    if not _table_exists("members"):
        return

    new_columns = [
        ("total_saved", "FLOAT DEFAULT 0.0"),
    ]

    for col_name, col_def in new_columns:
        if not _column_exists("members", col_name):
            try:
                conn.execute(text(f"ALTER TABLE members ADD COLUMN {col_name} {col_def}"))
                print(f"  升级 members 表，新增字段: {col_name}")
            except Exception:
                pass


def _upgrade_bills_table(conn):
    if not _table_exists("bills"):
        return

    new_columns = [
        ("member_id", "INTEGER"),
        ("member_discount", "FLOAT DEFAULT 0.0"),
        ("member_level", "VARCHAR(50)"),
    ]

    for col_name, col_def in new_columns:
        if not _column_exists("bills", col_name):
            try:
                conn.execute(text(f"ALTER TABLE bills ADD COLUMN {col_name} {col_def}"))
                print(f"  升级 bills 表，新增字段: {col_name}")
            except Exception:
                pass


def _upgrade_member_consumptions_table(conn):
    if not _table_exists("member_consumptions"):
        return

    new_columns = [
        ("bill_no", "VARCHAR(50)"),
        ("table_number", "VARCHAR(20)"),
        ("recharge_amount", "FLOAT DEFAULT 0.0"),
        ("bonus_amount", "FLOAT DEFAULT 0.0"),
        ("member_discount", "FLOAT DEFAULT 0.0"),
        ("coupon_discount", "FLOAT DEFAULT 0.0"),
        ("discount_detail", "TEXT"),
    ]

    for col_name, col_def in new_columns:
        if not _column_exists("member_consumptions", col_name):
            try:
                conn.execute(text(f"ALTER TABLE member_consumptions ADD COLUMN {col_name} {col_def}"))
                print(f"  升级 member_consumptions 表，新增字段: {col_name}")
            except Exception:
                pass


def _init_recharge_packages(conn):
    if not _table_exists("recharge_packages"):
        return

    result = conn.execute(text("SELECT COUNT(*) FROM recharge_packages"))
    count = result.scalar()
    if count == 0:
        from datetime import datetime
        now = datetime.now()
        packages = [
            ("充200送20", 200.0, 20.0, "首次充值推荐", 1),
            ("充500送50", 500.0, 50.0, "超值套餐，相当于9折", 2),
            ("充1000送120", 1000.0, 120.0, "银卡会员推荐，相当于8.9折", 3),
            ("充2000送300", 2000.0, 300.0, "金卡会员推荐，相当于8.7折", 4),
            ("充5000送800", 5000.0, 800.0, "钻石会员推荐，相当于8.4折", 5),
        ]
        for name, recharge, bonus, desc, sort in packages:
            conn.execute(text(
                "INSERT INTO recharge_packages (name, recharge_amount, bonus_amount, description, is_active, sort_order, created_at, updated_at) "
                "VALUES (:name, :recharge, :bonus, :desc, 1, :sort, :now, :now)"
            ), {"name": name, "recharge": recharge, "bonus": bonus, "desc": desc, "sort": sort, "now": now})
        print("  已初始化 5 个储值套餐")


def _init_member_level_defaults(conn):
    pass


MEMBER_LEVEL_DISCOUNTS = {
    "普通会员": 10.0,
    "银卡会员": 9.5,
    "金卡会员": 9.0,
    "钻石会员": 8.5,
}


def get_member_level_discount(level_name: str) -> float:
    return MEMBER_LEVEL_DISCOUNTS.get(level_name, 10.0)
