from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from database.models import Member, MemberConsumption, MemberLevel, Bill


class MemberService:
    def __init__(self, db: Session):
        self.db = db

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
