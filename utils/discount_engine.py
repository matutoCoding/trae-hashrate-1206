from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum
from datetime import date


class CouponType(str, Enum):
    DISCOUNT = "折扣券"
    DEDUCTION = "满减券"


class ApplyOrder(str, Enum):
    DISCOUNT_FIRST = "先折扣后满减"
    DEDUCTION_FIRST = "先满减后折扣"


@dataclass
class CouponItem:
    id: int
    code: str
    name: str
    type: CouponType
    discount_value: float
    min_consumption: float = 0
    max_discount: Optional[float] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


@dataclass
class DiscountResult:
    base_amount: float
    discount_amount: float
    final_amount: float
    applied_discounts: List[dict] = field(default_factory=list)
    calculation_steps: List[str] = field(default_factory=list)
    has_negative_protection: bool = False


class DiscountCalculator:
    def __init__(self, apply_order: ApplyOrder = ApplyOrder.DISCOUNT_FIRST,
                 allow_negative: bool = False):
        self.apply_order = apply_order
        self.allow_negative = allow_negative

    def calculate(self, base_amount: float, coupons: List[CouponItem],
                  check_date: Optional[date] = None) -> DiscountResult:
        if base_amount <= 0:
            return DiscountResult(
                base_amount=0,
                discount_amount=0,
                final_amount=0,
                calculation_steps=["基础金额为0，无需计算优惠"]
            )

        check_date = check_date or date.today()
        valid_coupons = self._filter_valid_coupons(coupons, check_date, base_amount)

        if not valid_coupons:
            return DiscountResult(
                base_amount=base_amount,
                discount_amount=0,
                final_amount=base_amount,
                calculation_steps=["无可用优惠券"]
            )

        discount_coupons = [c for c in valid_coupons if c.type == CouponType.DISCOUNT]
        deduction_coupons = [c for c in valid_coupons if c.type == CouponType.DEDUCTION]

        current_amount = base_amount
        total_discount = 0
        applied_discounts = []
        steps = [f"原始金额: ¥{base_amount:.2f}"]
        apply_order_num = 1

        if self.apply_order == ApplyOrder.DISCOUNT_FIRST:
            for coupon in discount_coupons:
                current_amount, discount = self._apply_discount_coupon(current_amount, coupon)
                total_discount += discount
                applied_discounts.append({
                    "coupon_id": coupon.id,
                    "coupon_name": coupon.name,
                    "coupon_type": coupon.type.value,
                    "discount_value": coupon.discount_value,
                    "applied_amount": discount,
                    "apply_order": apply_order_num
                })
                steps.append(f"[步骤{apply_order_num}] 使用{coupon.name}({coupon.code}): 折扣 ¥{discount:.2f}，当前金额 ¥{current_amount:.2f}")
                apply_order_num += 1

            for coupon in deduction_coupons:
                current_amount, discount = self._apply_deduction_coupon(current_amount, coupon)
                total_discount += discount
                applied_discounts.append({
                    "coupon_id": coupon.id,
                    "coupon_name": coupon.name,
                    "coupon_type": coupon.type.value,
                    "discount_value": coupon.discount_value,
                    "applied_amount": discount,
                    "apply_order": apply_order_num
                })
                steps.append(f"[步骤{apply_order_num}] 使用{coupon.name}({coupon.code}): 满减 ¥{discount:.2f}，当前金额 ¥{current_amount:.2f}")
                apply_order_num += 1
        else:
            for coupon in deduction_coupons:
                current_amount, discount = self._apply_deduction_coupon(current_amount, coupon)
                total_discount += discount
                applied_discounts.append({
                    "coupon_id": coupon.id,
                    "coupon_name": coupon.name,
                    "coupon_type": coupon.type.value,
                    "discount_value": coupon.discount_value,
                    "applied_amount": discount,
                    "apply_order": apply_order_num
                })
                steps.append(f"[步骤{apply_order_num}] 使用{coupon.name}({coupon.code}): 满减 ¥{discount:.2f}，当前金额 ¥{current_amount:.2f}")
                apply_order_num += 1

            for coupon in discount_coupons:
                current_amount, discount = self._apply_discount_coupon(current_amount, coupon)
                total_discount += discount
                applied_discounts.append({
                    "coupon_id": coupon.id,
                    "coupon_name": coupon.name,
                    "coupon_type": coupon.type.value,
                    "discount_value": coupon.discount_value,
                    "applied_amount": discount,
                    "apply_order": apply_order_num
                })
                steps.append(f"[步骤{apply_order_num}] 使用{coupon.name}({coupon.code}): 折扣 ¥{discount:.2f}，当前金额 ¥{current_amount:.2f}")
                apply_order_num += 1

        has_negative_protection = False
        if current_amount < 0 and not self.allow_negative:
            steps.append(f"[负值兜底校验] 计算结果为 ¥{current_amount:.2f}，根据配置禁止负值，已调整为 ¥0.00")
            total_discount = base_amount
            current_amount = 0
            has_negative_protection = True

        steps.append(f"优惠合计: ¥{total_discount:.2f}，最终应付: ¥{current_amount:.2f}")

        return DiscountResult(
            base_amount=base_amount,
            discount_amount=round(total_discount, 2),
            final_amount=round(current_amount, 2),
            applied_discounts=applied_discounts,
            calculation_steps=steps,
            has_negative_protection=has_negative_protection
        )

    def _filter_valid_coupons(self, coupons: List[CouponItem], check_date: date,
                              base_amount: float) -> List[CouponItem]:
        valid = []
        for coupon in coupons:
            if coupon.valid_from and check_date < coupon.valid_from:
                continue
            if coupon.valid_to and check_date > coupon.valid_to:
                continue
            if base_amount < coupon.min_consumption:
                continue
            valid.append(coupon)
        return valid

    def _apply_discount_coupon(self, current_amount: float, coupon: CouponItem) -> Tuple[float, float]:
        if current_amount <= 0:
            return current_amount, 0

        discount_rate = coupon.discount_value
        if 0 < discount_rate < 1:
            discounted = current_amount * discount_rate
            discount = current_amount - discounted
        elif discount_rate >= 1:
            discount_rate = discount_rate / 10
            discounted = current_amount * discount_rate
            discount = current_amount - discounted
        else:
            return current_amount, 0

        if coupon.max_discount and discount > coupon.max_discount:
            discount = coupon.max_discount
            discounted = current_amount - discount

        return round(discounted, 2), round(discount, 2)

    def _apply_deduction_coupon(self, current_amount: float, coupon: CouponItem) -> Tuple[float, float]:
        if current_amount <= 0:
            return current_amount, 0

        if current_amount >= coupon.min_consumption:
            discount = coupon.discount_value
            discounted = current_amount - discount
            return round(discounted, 2), round(discount, 2)

        return current_amount, 0
