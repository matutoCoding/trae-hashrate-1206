from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from database.models import Coupon, CouponType, DiscountOrderConfig, DiscountApplyOrder
from utils.discount_engine import DiscountCalculator, CouponItem as EngineCouponItem, ApplyOrder, DiscountResult


class DiscountService:
    def __init__(self, db: Session):
        self.db = db
        self._init_default_config()

    def _init_default_config(self):
        config = self.db.query(DiscountOrderConfig).filter(DiscountOrderConfig.is_active == True).first()
        if not config:
            config = DiscountOrderConfig(
                apply_order=DiscountApplyOrder.DISCOUNT_FIRST,
                allow_negative=False,
                is_active=True,
                updated_at=datetime.now()
            )
            self.db.add(config)
            self.db.commit()

    def create_coupon(self, code: str, name: str, coupon_type: CouponType,
                      discount_value: float, **kwargs) -> Coupon:
        existing = self.db.query(Coupon).filter(Coupon.code == code).first()
        if existing:
            raise ValueError(f"券号 {code} 已存在")

        coupon = Coupon(
            code=code,
            name=name,
            type=coupon_type,
            discount_value=discount_value,
            min_consumption=kwargs.get("min_consumption", 0),
            max_discount=kwargs.get("max_discount"),
            valid_from=kwargs.get("valid_from"),
            valid_to=kwargs.get("valid_to"),
            total_quantity=kwargs.get("total_quantity", 1),
            used_quantity=0,
            is_active=True,
            description=kwargs.get("description"),
            created_at=datetime.now()
        )
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def get_coupon(self, coupon_id: int) -> Optional[Coupon]:
        return self.db.query(Coupon).filter(Coupon.id == coupon_id).first()

    def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        return self.db.query(Coupon).filter(Coupon.code == code).first()

    def get_all_coupons(self, only_active: bool = True, only_valid: bool = False) -> List[Coupon]:
        query = self.db.query(Coupon)
        if only_active:
            query = query.filter(Coupon.is_active == True)
        if only_valid:
            today = date.today()
            query = query.filter(
                (Coupon.valid_from == None) | (Coupon.valid_from <= today),
                (Coupon.valid_to == None) | (Coupon.valid_to >= today)
            )
        return query.order_by(Coupon.created_at.desc()).all()

    def get_available_coupons(self, base_amount: float, check_date: date = None) -> List[Coupon]:
        check_date = check_date or date.today()
        coupons = self.get_all_coupons(only_active=True, only_valid=True)
        available = []
        for coupon in coupons:
            if coupon.used_quantity >= coupon.total_quantity:
                continue
            if base_amount < coupon.min_consumption:
                continue
            available.append(coupon)
        return available

    def update_coupon(self, coupon_id: int, **kwargs) -> Optional[Coupon]:
        coupon = self.get_coupon(coupon_id)
        if not coupon:
            return None

        for key, value in kwargs.items():
            if hasattr(coupon, key) and value is not None:
                setattr(coupon, key, value)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def delete_coupon(self, coupon_id: int) -> bool:
        coupon = self.get_coupon(coupon_id)
        if not coupon:
            return False
        self.db.delete(coupon)
        self.db.commit()
        return True

    def use_coupon(self, coupon_id: int) -> Optional[Coupon]:
        coupon = self.get_coupon(coupon_id)
        if not coupon:
            return None
        if coupon.used_quantity >= coupon.total_quantity:
            raise ValueError("优惠券已用完")
        coupon.used_quantity += 1
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def get_discount_config(self) -> Optional[DiscountOrderConfig]:
        return self.db.query(DiscountOrderConfig).filter(DiscountOrderConfig.is_active == True).first()

    def create_discount_config(self, apply_order: DiscountApplyOrder,
                               allow_negative: bool) -> DiscountOrderConfig:
        existing = self.get_discount_config()
        if existing:
            existing.is_active = False
            self.db.commit()

        config = DiscountOrderConfig(
            apply_order=apply_order,
            allow_negative=allow_negative,
            is_active=True
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update_discount_config(self, apply_order: DiscountApplyOrder = None,
                               allow_negative: bool = None) -> Optional[DiscountOrderConfig]:
        config = self.get_discount_config()
        if not config:
            return None

        if apply_order is not None:
            config.apply_order = apply_order
        if allow_negative is not None:
            config.allow_negative = allow_negative
        config.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(config)
        return config

    def calculate_discount(self, base_amount: float, coupon_ids: List[int] = None,
                           coupon_codes: List[str] = None, check_date: date = None) -> DiscountResult:
        config = self.get_discount_config()
        apply_order = ApplyOrder.DISCOUNT_FIRST
        allow_negative = False
        if config:
            apply_order = ApplyOrder(config.apply_order.value)
            allow_negative = config.allow_negative

        coupons = []
        if coupon_ids:
            for cid in coupon_ids:
                coupon = self.get_coupon(cid)
                if coupon:
                    coupons.append(coupon)
        if coupon_codes:
            for code in coupon_codes:
                coupon = self.get_coupon_by_code(code)
                if coupon and coupon not in coupons:
                    coupons.append(coupon)

        engine_coupons = []
        for coupon in coupons:
            engine_coupons.append(EngineCouponItem(
                id=coupon.id,
                code=coupon.code,
                name=coupon.name,
                type=CouponType(coupon.type.value),
                discount_value=coupon.discount_value,
                min_consumption=coupon.min_consumption,
                max_discount=coupon.max_discount,
                valid_from=coupon.valid_from,
                valid_to=coupon.valid_to
            ))

        calculator = DiscountCalculator(apply_order=apply_order, allow_negative=allow_negative)
        return calculator.calculate(base_amount, engine_coupons, check_date)
