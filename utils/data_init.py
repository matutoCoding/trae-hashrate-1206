from datetime import date, time, timedelta
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import CouponType, DiscountApplyOrder
from modules.table_service import TableService
from modules.discount_service import DiscountService


def init_sample_data(db: Session):
    table_service = TableService(db)
    discount_service = DiscountService(db)

    tables = table_service.get_all_tables()
    if not tables:
        sample_tables = [
            {"table_number": "A01", "name": "豪华包厢1", "room_type": "豪华包厢", "hourly_rate": 60.0, "machine_model": "雀友T380", "location": "二楼"},
            {"table_number": "A02", "name": "豪华包厢2", "room_type": "豪华包厢", "hourly_rate": 60.0, "machine_model": "雀友T380", "location": "二楼"},
            {"table_number": "B01", "name": "标准间1", "room_type": "标准间", "hourly_rate": 40.0, "machine_model": "雀友T280", "location": "一楼"},
            {"table_number": "B02", "name": "标准间2", "room_type": "标准间", "hourly_rate": 40.0, "machine_model": "雀友T280", "location": "一楼"},
            {"table_number": "B03", "name": "标准间3", "room_type": "标准间", "hourly_rate": 40.0, "machine_model": "雀友T280", "location": "一楼"},
            {"table_number": "C01", "name": "普通厅1", "room_type": "普通厅", "hourly_rate": 25.0, "machine_model": "雀友T180", "location": "大厅"},
            {"table_number": "C02", "name": "普通厅2", "room_type": "普通厅", "hourly_rate": 25.0, "machine_model": "雀友T180", "location": "大厅"},
            {"table_number": "C03", "name": "普通厅3", "room_type": "普通厅", "hourly_rate": 25.0, "machine_model": "雀友T180", "location": "大厅"},
        ]
        for t in sample_tables:
            table_service.create_table(**t, purchase_date=date.today() - timedelta(days=365))
        print(f"已创建 {len(sample_tables)} 个麻将桌")

    coupons = discount_service.get_all_coupons(only_active=False)
    if not coupons:
        today = date.today()
        sample_coupons = [
            {"code": "DISCOUNT08", "name": "会员8折券", "coupon_type": CouponType.DISCOUNT, "discount_value": 8.0, "description": "全场8折"},
            {"code": "DISCOUNT09", "name": "新客9折券", "coupon_type": CouponType.DISCOUNT, "discount_value": 9.0, "description": "新顾客专享9折"},
            {"code": "DISCOUNT75", "name": "VIP75折券", "coupon_type": CouponType.DISCOUNT, "discount_value": 7.5, "max_discount": 50.0, "description": "VIP会员75折，最高减50"},
            {"code": "MANJIAN50", "name": "满200减50", "coupon_type": CouponType.DEDUCTION, "discount_value": 50.0, "min_consumption": 200.0, "description": "消费满200减50"},
            {"code": "MANJIAN30", "name": "满100减30", "coupon_type": CouponType.DEDUCTION, "discount_value": 30.0, "min_consumption": 100.0, "description": "消费满100减30"},
            {"code": "MANJIAN100", "name": "满500减100", "coupon_type": CouponType.DEDUCTION, "discount_value": 100.0, "min_consumption": 500.0, "total_quantity": 10, "description": "消费满500减100"},
        ]
        for c in sample_coupons:
            c["valid_from"] = today
            c["valid_to"] = today + timedelta(days=365)
            discount_service.create_coupon(**c)
        print(f"已创建 {len(sample_coupons)} 个优惠券")

    config = discount_service.get_discount_config()
    if not config:
        discount_service.create_discount_config(
            apply_order=DiscountApplyOrder.DISCOUNT_FIRST,
            allow_negative=False
        )
        print("已配置优惠计算规则：先折扣后满减，禁止负值")
