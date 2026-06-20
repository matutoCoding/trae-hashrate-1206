from typing import List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from database.models import Bill, BillDiscount, Booking, BookingStatus
from utils.discount_engine import DiscountResult


class BillService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_bill_no(self) -> str:
        today = date.today()
        prefix = f"MB{today.strftime('%Y%m%d')}"
        last_bill = self.db.query(Bill).filter(
            Bill.bill_no.like(f"{prefix}%")
        ).order_by(Bill.bill_no.desc()).first()
        if last_bill:
            seq = int(last_bill.bill_no[-4:]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    def has_unpaid_bill(self, booking_id: int) -> bool:
        existing = self.db.query(Bill).filter(
            Bill.booking_id == booking_id
        ).first()
        return existing is not None

    def create_bill(self, booking_id: int, discount_result: DiscountResult = None,
                    **kwargs) -> Bill:
        booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise ValueError("预订不存在")

        existing_bill = self.db.query(Bill).filter(
            Bill.booking_id == booking_id
        ).first()
        if existing_bill:
            if existing_bill.is_paid:
                raise ValueError(f"该预订已生成账单（账单号：{existing_bill.bill_no}），不能重复结账")
            else:
                return existing_bill

        bill_no = self._generate_bill_no()
        base_amount = kwargs.get("base_amount", booking.base_amount)

        if discount_result:
            discount_amount = discount_result.discount_amount
            final_amount = discount_result.final_amount
        else:
            discount_amount = kwargs.get("discount_amount", 0)
            final_amount = kwargs.get("final_amount", base_amount - discount_amount)

        bill = Bill(
            bill_no=bill_no,
            booking_id=booking_id,
            table_number=kwargs.get("table_number", booking.table.table_number if booking.table else ""),
            customer_name=kwargs.get("customer_name", booking.customer_name),
            checkin_time=kwargs.get("checkin_time", datetime.combine(booking.booking_date, booking.start_time)),
            checkout_time=kwargs.get("checkout_time", datetime.now()),
            total_hours=kwargs.get("total_hours", booking.total_hours),
            hourly_rate=kwargs.get("hourly_rate", booking.table.hourly_rate if booking.table else 0),
            base_amount=base_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            payment_method=kwargs.get("payment_method"),
            is_paid=kwargs.get("is_paid", False),
            note=kwargs.get("note"),
            created_at=datetime.now()
        )
        self.db.add(bill)
        self.db.flush()

        if discount_result and discount_result.applied_discounts:
            for d in discount_result.applied_discounts:
                bill_discount = BillDiscount(
                    bill_id=bill.id,
                    coupon_id=d.get("coupon_id"),
                    coupon_name=d.get("coupon_name"),
                    coupon_type=d.get("coupon_type"),
                    discount_value=d.get("discount_value"),
                    applied_amount=d.get("applied_amount"),
                    apply_order=d.get("apply_order")
                )
                self.db.add(bill_discount)

        self.db.commit()
        self.db.refresh(bill)
        return bill

    def get_bill(self, bill_id: int) -> Optional[Bill]:
        return self.db.query(Bill).filter(Bill.id == bill_id).first()

    def get_bill_by_no(self, bill_no: str) -> Optional[Bill]:
        return self.db.query(Bill).filter(Bill.bill_no == bill_no).first()

    def get_bills_by_date(self, bill_date: date) -> List[Bill]:
        return self.db.query(Bill).filter(
            Bill.created_at >= datetime.combine(bill_date, datetime.min.time()),
            Bill.created_at <= datetime.combine(bill_date, datetime.max.time())
        ).order_by(Bill.created_at.desc()).all()

    def get_all_bills(self, start_date: date = None, end_date: date = None,
                      only_unpaid: bool = False) -> List[Bill]:
        query = self.db.query(Bill)
        if start_date:
            query = query.filter(Bill.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(Bill.created_at <= datetime.combine(end_date, datetime.max.time()))
        if only_unpaid:
            query = query.filter(Bill.is_paid == False)
        return query.order_by(Bill.created_at.desc()).all()

    def get_bills_by_booking(self, booking_id: int) -> List[Bill]:
        return self.db.query(Bill).filter(Bill.booking_id == booking_id).all()

    def update_bill(self, bill_id: int, **kwargs) -> Optional[Bill]:
        bill = self.get_bill(bill_id)
        if not bill:
            return None

        for key, value in kwargs.items():
            if hasattr(bill, key) and value is not None:
                setattr(bill, key, value)
        self.db.commit()
        self.db.refresh(bill)
        return bill

    def pay_bill(self, bill_id: int, payment_method: str, member_id: int = None) -> Optional[Bill]:
        bill = self.get_bill(bill_id)
        if not bill:
            return None

        if bill.is_paid:
            raise ValueError("该账单已支付")

        from modules.discount_service import DiscountService
        discount_service = DiscountService(self.db)
        for bd in bill.discounts:
            if bd.coupon_id:
                try:
                    discount_service.use_coupon(bd.coupon_id)
                except:
                    pass

        if payment_method == "会员卡" and member_id:
            from modules.member_service import MemberService
            member_service = MemberService(self.db)
            member_service.consume(
                member_id=member_id,
                amount=bill.final_amount,
                bill_id=bill.id,
                description=f"账单 {bill.bill_no} 会员卡支付"
            )
            bill.member_id = member_id

        bill.is_paid = True
        bill.payment_method = payment_method
        bill.paid_at = datetime.now()
        self.db.commit()
        self.db.refresh(bill)

        booking = self.db.query(Booking).filter(Booking.id == bill.booking_id).first()
        if booking:
            from modules.booking_service import BookingService
            booking_service = BookingService(self.db)
            if booking.status != BookingStatus.COMPLETED:
                booking_service.check_out(booking.id)

        return bill

    def delete_bill(self, bill_id: int) -> bool:
        bill = self.get_bill(bill_id)
        if not bill:
            return False
        self.db.delete(bill)
        self.db.commit()
        return True

    def get_daily_statistics(self, stat_date: date) -> dict:
        bills = self.get_bills_by_date(stat_date)
        paid_bills = [b for b in bills if b.is_paid]
        return {
            "date": stat_date,
            "total_bills": len(bills),
            "paid_bills": len(paid_bills),
            "unpaid_bills": len(bills) - len(paid_bills),
            "total_base_amount": round(sum(b.base_amount for b in bills), 2),
            "total_discount_amount": round(sum(b.discount_amount for b in bills), 2),
            "total_final_amount": round(sum(b.final_amount for b in bills), 2),
            "total_paid_amount": round(sum(b.final_amount for b in paid_bills), 2)
        }

    def get_statistics(self, start_date: date, end_date: date) -> dict:
        bills = self.db.query(Bill).filter(
            Bill.is_paid == True,
            Bill.paid_at >= datetime.combine(start_date, datetime.min.time()),
            Bill.paid_at <= datetime.combine(end_date, datetime.max.time())
        ).all()

        total_base = round(sum(b.base_amount for b in bills), 2)
        total_discount = round(sum(b.discount_amount for b in bills), 2)
        total_final = round(sum(b.final_amount for b in bills), 2)
        total_hours = round(sum(b.total_hours or 0 for b in bills), 2)
        bill_count = len(bills)
        avg_per_bill = round(total_final / bill_count, 2) if bill_count > 0 else 0

        by_payment = {}
        for b in bills:
            method = b.payment_method or "未知"
            if method not in by_payment:
                by_payment[method] = {"count": 0, "amount": 0.0, "hours": 0.0}
            by_payment[method]["count"] += 1
            by_payment[method]["amount"] = round(by_payment[method]["amount"] + b.final_amount, 2)
            by_payment[method]["hours"] = round(by_payment[method]["hours"] + (b.total_hours or 0), 2)

        by_date = {}
        for b in bills:
            d = b.paid_at.date() if b.paid_at else (b.created_at.date() if b.created_at else None)
            if d is None:
                continue
            ds = d.isoformat()
            if ds not in by_date:
                by_date[ds] = {"count": 0, "base": 0.0, "discount": 0.0, "final": 0.0, "hours": 0.0}
            by_date[ds]["count"] += 1
            by_date[ds]["base"] = round(by_date[ds]["base"] + b.base_amount, 2)
            by_date[ds]["discount"] = round(by_date[ds]["discount"] + b.discount_amount, 2)
            by_date[ds]["final"] = round(by_date[ds]["final"] + b.final_amount, 2)
            by_date[ds]["hours"] = round(by_date[ds]["hours"] + (b.total_hours or 0), 2)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "bill_count": bill_count,
            "total_base": total_base,
            "total_discount": total_discount,
            "total_final": total_final,
            "total_hours": total_hours,
            "avg_per_bill": avg_per_bill,
            "by_payment": by_payment,
            "by_date": by_date
        }

    def generate_print_content(self, bill_id: int) -> str:
        bill = self.get_bill(bill_id)
        if not bill:
            return ""

        lines = []
        lines.append("=" * 40)
        lines.append("          茶楼麻将房账单")
        lines.append("=" * 40)
        lines.append(f"账单号: {bill.bill_no}")
        lines.append(f"日期: {bill.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"桌号: {bill.table_number}")
        lines.append(f"客人: {bill.customer_name}")
        lines.append("-" * 40)
        lines.append(f"入场时间: {bill.checkin_time.strftime('%Y-%m-%d %H:%M') if bill.checkin_time else ''}")
        lines.append(f"结账时间: {bill.checkout_time.strftime('%Y-%m-%d %H:%M') if bill.checkout_time else ''}")
        lines.append(f"时长: {bill.total_hours:.1f} 小时")
        lines.append(f"单价: ¥{bill.hourly_rate:.2f}/小时")
        lines.append("-" * 40)
        lines.append(f"基础金额: ¥{bill.base_amount:.2f}")

        if bill.discounts:
            lines.append("优惠明细:")
            for d in sorted(bill.discounts, key=lambda x: x.apply_order or 0):
                lines.append(f"  [{d.apply_order}] {d.coupon_name} ({d.coupon_type}): -¥{d.applied_amount:.2f}")

        lines.append(f"优惠合计: -¥{bill.discount_amount:.2f}")
        lines.append("-" * 40)
        lines.append(f"应付金额: ¥{bill.final_amount:.2f}")
        if bill.is_paid:
            lines.append(f"支付方式: {bill.payment_method}")
            lines.append(f"支付状态: 已支付")
            lines.append(f"支付时间: {bill.paid_at.strftime('%Y-%m-%d %H:%M:%S') if bill.paid_at else ''}")
        else:
            lines.append(f"支付状态: 未支付")
        lines.append("=" * 40)
        lines.append("          谢谢光临，欢迎再来！")
        lines.append("=" * 40)

        return "\n".join(lines)
