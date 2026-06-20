from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from database.models import Member, MemberConsumption, MemberLevel, Bill, RechargePackage
from database.migrate import get_member_level_discount


class MemberService:
    def __init__(self, db: Session):
        self.db = db

    def get_level_discount(self, level: MemberLevel) -> float:
        return get_member_level_discount(level.value)

    def create_member(self, name: str, phone: str, **kwargs) -> Member:
        existing = self.db.query(Member).filter(Member.phone == phone).first()
        if existing:
            raise ValueError(f"手机号 {phone} 已注册会员")

        member = Member(
            name=name,
            phone=phone,
            level=kwargs.get("level", MemberLevel.NORMAL),
            balance=kwargs.get("balance", 0.0),
            total_consumption=kwargs.get("total_consumption", 0.0),
            visit_count=kwargs.get("visit_count", 0),
            remark=kwargs.get("remark"),
            is_active=kwargs.get("is_active", True),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(member)
        self.db.flush()

        if member.balance > 0:
            consumption = MemberConsumption(
                member_id=member.id,
                type="充值",
                amount=member.balance,
                balance_before=0.0,
                balance_after=member.balance,
                description="开户充值",
                created_at=datetime.now()
            )
            self.db.add(consumption)

        self.db.commit()
        self.db.refresh(member)
        return member

    def get_member(self, member_id: int) -> Optional[Member]:
        return self.db.query(Member).filter(Member.id == member_id).first()

    def get_member_by_phone(self, phone: str) -> Optional[Member]:
        return self.db.query(Member).filter(Member.phone == phone).first()

    def get_all_members(self, only_active: bool = True) -> List[Member]:
        query = self.db.query(Member)
        if only_active:
            query = query.filter(Member.is_active == True)
        return query.order_by(Member.id).all()

    def update_member(self, member_id: int, **kwargs) -> Optional[Member]:
        member = self.get_member(member_id)
        if not member:
            return None

        if "phone" in kwargs:
            existing = self.db.query(Member).filter(
                Member.phone == kwargs["phone"],
                Member.id != member_id
            ).first()
            if existing:
                raise ValueError(f"手机号 {kwargs['phone']} 已被其他会员使用")

        for key, value in kwargs.items():
            if hasattr(member, key) and value is not None:
                setattr(member, key, value)
        member.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(member)
        return member

    def delete_member(self, member_id: int) -> bool:
        member = self.get_member(member_id)
        if not member:
            return False
        member.is_active = False
        member.updated_at = datetime.now()
        self.db.commit()
        return True

    def recharge(self, member_id: int, amount: float, description: str = "") -> MemberConsumption:
        member = self.get_member(member_id)
        if not member:
            raise ValueError("会员不存在")
        if amount <= 0:
            raise ValueError("充值金额必须大于0")

        balance_before = member.balance
        member.balance = round(member.balance + amount, 2)
        member.updated_at = datetime.now()

        consumption = MemberConsumption(
            member_id=member_id,
            type="充值",
            amount=amount,
            balance_before=balance_before,
            balance_after=member.balance,
            description=description or f"充值 ¥{amount:.2f}",
            created_at=datetime.now()
        )
        self.db.add(consumption)
        self.db.commit()
        self.db.refresh(member)
        self.db.refresh(consumption)
        return consumption

    def consume(self, member_id: int, amount: float, bill_id: int = None,
                description: str = "") -> MemberConsumption:
        member = self.get_member(member_id)
        if not member:
            raise ValueError("会员不存在")
        if amount <= 0:
            raise ValueError("消费金额必须大于0")
        if member.balance < amount:
            raise ValueError(f"余额不足！当前余额 ¥{member.balance:.2f}，需要支付 ¥{amount:.2f}，差额 ¥{amount - member.balance:.2f}")

        balance_before = member.balance
        member.balance = round(member.balance - amount, 2)
        member.total_consumption = round(member.total_consumption + amount, 2)
        member.visit_count += 1
        member.updated_at = datetime.now()

        consumption = MemberConsumption(
            member_id=member_id,
            bill_id=bill_id,
            type="消费",
            amount=amount,
            balance_before=balance_before,
            balance_after=member.balance,
            description=description or f"会员卡消费 ¥{amount:.2f}",
            created_at=datetime.now()
        )
        self.db.add(consumption)
        self.db.commit()
        self.db.refresh(member)
        self.db.refresh(consumption)
        return consumption

    def get_consumptions(self, member_id: int, limit: int = 50) -> List[MemberConsumption]:
        return self.db.query(MemberConsumption).filter(
            MemberConsumption.member_id == member_id
        ).order_by(MemberConsumption.created_at.desc()).limit(limit).all()

    def get_member_by_name_or_phone(self, keyword: str) -> List[Member]:
        return self.db.query(Member).filter(
            (Member.name.contains(keyword) | Member.phone.contains(keyword)),
            Member.is_active == True
        ).all()

    def get_recharge_packages(self, only_active: bool = True) -> List[RechargePackage]:
        query = self.db.query(RechargePackage)
        if only_active:
            query = query.filter(RechargePackage.is_active == True)
        return query.order_by(RechargePackage.sort_order.asc(), RechargePackage.id.asc()).all()

    def get_recharge_package(self, package_id: int) -> Optional[RechargePackage]:
        return self.db.query(RechargePackage).filter(RechargePackage.id == package_id).first()

    def create_recharge_package(self, name: str, recharge_amount: float,
                                 bonus_amount: float = 0.0, **kwargs) -> RechargePackage:
        pkg = RechargePackage(
            name=name,
            recharge_amount=recharge_amount,
            bonus_amount=bonus_amount,
            description=kwargs.get("description"),
            sort_order=kwargs.get("sort_order", 0),
            is_active=kwargs.get("is_active", True),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self.db.add(pkg)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def update_recharge_package(self, package_id: int, **kwargs) -> Optional[RechargePackage]:
        pkg = self.get_recharge_package(package_id)
        if not pkg:
            return None
        for key, value in kwargs.items():
            if hasattr(pkg, key) and value is not None:
                setattr(pkg, key, value)
        pkg.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def delete_recharge_package(self, package_id: int) -> bool:
        pkg = self.get_recharge_package(package_id)
        if not pkg:
            return False
        pkg.is_active = False
        pkg.updated_at = datetime.now()
        self.db.commit()
        return True

    def recharge_with_package(self, member_id: int, package_id: int) -> MemberConsumption:
        member = self.get_member(member_id)
        if not member:
            raise ValueError("会员不存在")

        pkg = self.get_recharge_package(package_id)
        if not pkg or not pkg.is_active:
            raise ValueError("储值套餐不可用")

        balance_before = member.balance
        total_add = pkg.recharge_amount + pkg.bonus_amount
        member.balance = round(member.balance + total_add, 2)
        member.updated_at = datetime.now()

        consumption = MemberConsumption(
            member_id=member_id,
            type="充值",
            amount=total_add,
            balance_before=balance_before,
            balance_after=member.balance,
            description=f"套餐充值: {pkg.name}",
            recharge_amount=pkg.recharge_amount,
            bonus_amount=pkg.bonus_amount,
            created_at=datetime.now()
        )
        self.db.add(consumption)
        self.db.commit()
        self.db.refresh(member)
        self.db.refresh(consumption)
        return consumption

    def consume_with_detail(self, member_id: int, amount: float, bill_id: int = None,
                            bill_no: str = None, table_number: str = None,
                            member_discount: float = 0.0, coupon_discount: float = 0.0,
                            discount_detail: str = None,
                            description: str = "") -> MemberConsumption:
        member = self.get_member(member_id)
        if not member:
            raise ValueError("会员不存在")
        if amount <= 0:
            raise ValueError("消费金额必须大于0")
        if member.balance < amount:
            raise ValueError(
                f"余额不足！当前余额 ¥{member.balance:.2f}，"
                f"需要支付 ¥{amount:.2f}，差额 ¥{amount - member.balance:.2f}"
            )

        balance_before = member.balance
        member.balance = round(member.balance - amount, 2)
        member.total_consumption = round(member.total_consumption + amount, 2)
        member.visit_count += 1

        if hasattr(member, 'total_saved'):
            member.total_saved = (member.total_saved or 0) + member_discount + coupon_discount

        member.updated_at = datetime.now()

        consumption = MemberConsumption(
            member_id=member_id,
            bill_id=bill_id,
            type="消费",
            amount=amount,
            balance_before=balance_before,
            balance_after=member.balance,
            description=description or f"会员卡消费 ¥{amount:.2f}",
            bill_no=bill_no,
            table_number=table_number,
            member_discount=member_discount,
            coupon_discount=coupon_discount,
            discount_detail=discount_detail,
            created_at=datetime.now()
        )
        self.db.add(consumption)
        self.db.commit()
        self.db.refresh(member)
        self.db.refresh(consumption)
        return consumption

    def record_consumption_only(self, member_id: int, amount: float, bill_id: int = None,
                                 bill_no: str = None, table_number: str = None,
                                 member_discount: float = 0.0, coupon_discount: float = 0.0,
                                 discount_detail: str = None, payment_method: str = "",
                                 description: str = "") -> MemberConsumption:
        member = self.get_member(member_id)
        if not member:
            raise ValueError("会员不存在")
        if amount <= 0:
            raise ValueError("消费金额必须大于0")

        balance_before = member.balance
        member.total_consumption = round(member.total_consumption + amount, 2)
        member.visit_count += 1

        if hasattr(member, 'total_saved'):
            member.total_saved = (member.total_saved or 0) + member_discount + coupon_discount

        member.updated_at = datetime.now()

        desc_prefix = f"{payment_method}支付，未扣余额" if payment_method else "未扣余额"
        consumption = MemberConsumption(
            member_id=member_id,
            bill_id=bill_id,
            type="消费",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_before,
            description=f"{desc_prefix} | {description or f'账单 {bill_no or bill_id}'}",
            bill_no=bill_no,
            table_number=table_number,
            member_discount=member_discount,
            coupon_discount=coupon_discount,
            discount_detail=discount_detail,
            created_at=datetime.now()
        )
        self.db.add(consumption)
        self.db.commit()
        self.db.refresh(member)
        self.db.refresh(consumption)
        return consumption

    def get_member_statistics(self, member_id: int, start_date: date = None,
                               end_date: date = None) -> dict:
        member = self.get_member(member_id)
        if not member:
            return {}

        query = self.db.query(MemberConsumption).filter(
            MemberConsumption.member_id == member_id
        )
        if start_date:
            query = query.filter(
                MemberConsumption.created_at >= datetime.combine(start_date, datetime.min.time())
            )
        if end_date:
            query = query.filter(
                MemberConsumption.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        consumptions = query.order_by(MemberConsumption.created_at.desc()).all()

        total_recharge = 0.0
        total_recharge_actual = 0.0
        total_recharge_bonus = 0.0
        total_consume = 0.0
        total_member_discount = 0.0
        total_coupon_discount = 0.0
        recharge_count = 0
        consume_count = 0

        for c in consumptions:
            if c.type == "充值":
                recharge_count += 1
                total_recharge += c.amount or 0
                if hasattr(c, 'recharge_amount') and c.recharge_amount:
                    total_recharge_actual += c.recharge_amount
                else:
                    total_recharge_actual += c.amount or 0
                if hasattr(c, 'bonus_amount') and c.bonus_amount:
                    total_recharge_bonus += c.bonus_amount
            elif c.type == "消费":
                consume_count += 1
                total_consume += c.amount or 0
                if hasattr(c, 'member_discount') and c.member_discount:
                    total_member_discount += c.member_discount
                if hasattr(c, 'coupon_discount') and c.coupon_discount:
                    total_coupon_discount += c.coupon_discount

        total_saved = total_member_discount + total_coupon_discount

        first_record = consumptions[-1] if consumptions else None
        last_record = consumptions[0] if consumptions else None
        start_balance = first_record.balance_before if first_record else member.balance
        end_balance = last_record.balance_after if last_record else member.balance

        return {
            "member": member,
            "start_date": start_date,
            "end_date": end_date,
            "recharge_count": recharge_count,
            "consume_count": consume_count,
            "total_recharge": round(total_recharge, 2),
            "total_recharge_actual": round(total_recharge_actual, 2),
            "total_recharge_bonus": round(total_recharge_bonus, 2),
            "total_consume": round(total_consume, 2),
            "total_member_discount": round(total_member_discount, 2),
            "total_coupon_discount": round(total_coupon_discount, 2),
            "total_saved": round(total_saved, 2),
            "start_balance": round(start_balance, 2),
            "end_balance": round(end_balance, 2),
            "balance_change": round(end_balance - start_balance, 2),
            "consumptions": consumptions
        }

    def get_member_monthly_statement(self, member_id: int, year: int, month: int) -> dict:
        from datetime import timedelta
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        return self.get_member_statistics(member_id, start_date, end_date)
