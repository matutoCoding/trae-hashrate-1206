import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db, SessionLocal
from database.migrate import upgrade_database
from database.models import MemberLevel
from utils.discount_engine import DiscountCalculator, CouponItem, DiscountResult, ApplyOrder, CouponType
from datetime import date

print("=== 测试优惠引擎 ===")
coupons = [
    CouponItem(id=1, code="DISC10", name="9折券", type=CouponType.DISCOUNT,
               discount_value=9.0, min_consumption=0),
    CouponItem(id=2, code="OFF20", name="满50减20", type=CouponType.DEDUCTION,
               discount_value=20.0, min_consumption=50),
]

calc = DiscountCalculator(apply_order=ApplyOrder.DISCOUNT_FIRST, allow_negative=False)

print("测试1: 仅优惠券")
result = calc.calculate(100, coupons, date.today())
print(f"  基础: {result.base_amount}, 优惠: {result.discount_amount}, 最终: {result.final_amount}")
print(f"  会员折扣: {result.member_discount}, 优惠券折扣: {result.coupon_discount}")

print("\n测试2: 会员折扣 + 优惠券")
result2 = calc.calculate(100, coupons, date.today(), member_discount_rate=9.0, member_level="金卡")
print(f"  基础: {result2.base_amount}, 优惠: {result2.discount_amount}, 最终: {result2.final_amount}")
print(f"  会员折扣: {result2.member_discount}, 优惠券折扣: {result2.coupon_discount}")
for step in result2.calculation_steps:
    print(f"  {step}")

print("\n测试3: 钻石会员折扣 + 优惠券")
result3 = calc.calculate(100, coupons, date.today(), member_discount_rate=8.5, member_level="钻石卡")
print(f"  基础: {result3.base_amount}, 优惠: {result3.discount_amount}, 最终: {result3.final_amount}")
print(f"  会员折扣: {result3.member_discount}, 优惠券折扣: {result3.coupon_discount}")

print("\n=== 测试数据库升级 ===")
try:
    init_db()
    upgrade_database()
    print("  数据库升级成功!")
except Exception as e:
    print(f"  数据库升级失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 测试等级折扣映射 ===")
from database.migrate import get_member_level_discount
for level in ["普通会员", "银卡会员", "金卡会员", "钻石会员"]:
    print(f"  {level}: {get_member_level_discount(level)}折")

print("\n所有测试通过!")
