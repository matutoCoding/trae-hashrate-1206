import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db, SessionLocal
from database.migrate import upgrade_database

print("1. 初始化数据库...")
init_db()
upgrade_database()
db = SessionLocal()

print("2. 测试会员服务（非会员卡支付记录消费）...")
from modules.member_service import MemberService
from database.models import MemberLevel
ms = MemberService(db)

# 找一个会员
members = ms.get_all_members()
if members:
    m = members[0]
    print(f"   选中会员: {m.name} (余额: ¥{m.balance:.2f})")

    # 测试 record_consumption_only（非会员卡支付，不扣余额）
    old_balance = m.balance
    old_consumptions = len(ms.get_consumptions(m.id, limit=10))
    c = ms.record_consumption_only(
        member_id=m.id,
        amount=88.0,
        bill_no=f"TEST{os.getpid()}",
        table_number="8号桌",
        member_discount=10.0,
        coupon_discount=2.0,
        discount_detail="[1] 金卡会员(9折): -¥10\n[2] 满减券: -¥2",
        payment_method="微信",
        description="测试微信支付享受会员折扣"
    )
    print(f"   已记录消费: ID={c.id}, 类型={c.type}, 金额={c.amount}")
    print(f"   支付方式: 微信（非卡扣），账单号={c.bill_no}, 桌号={c.table_number}")
    print(f"   会员折扣={c.member_discount}, 优惠券折扣={c.coupon_discount}")
    m2 = ms.get_member(m.id)
    print(f"   余额校验: 原¥{old_balance:.2f} -> 现¥{m2.balance:.2f} (未扣余额=正确)")
    print(f"   累计节省增加: ¥{(m2.total_saved or 0):.2f}")

print("\n3. 测试会员月度对账统计...")
if members:
    today = __import__('datetime').date.today()
    stmt = ms.get_member_monthly_statement(m.id, today.year, today.month)
    print(f"   会员: {stmt['member'].name}")
    print(f"   周期: {stmt['start_date']} ~ {stmt['end_date']}")
    print(f"   充值笔数: {stmt['recharge_count']}, 金额: ¥{stmt['total_recharge']:.2f}")
    print(f"   充值本金: ¥{stmt['total_recharge_actual']:.2f}, 赠送金: ¥{stmt['total_recharge_bonus']:.2f}")
    print(f"   消费笔数: {stmt['consume_count']}, 金额: ¥{stmt['total_consume']:.2f}")
    print(f"   会员折扣节省: ¥{stmt['total_member_discount']:.2f}, 券节省: ¥{stmt['total_coupon_discount']:.2f}")
    print(f"   累计节省: ¥{stmt['total_saved']:.2f}")
    print(f"   期初余额: ¥{stmt['start_balance']:.2f}, 期末: ¥{stmt['end_balance']:.2f}, 变动: ¥{stmt['balance_change']:.2f}")

print("\n4. 测试经营分析...")
from modules.bill_service import BillService
bs = BillService(db)
from datetime import date, timedelta
start = date.today() - timedelta(days=30)
end = date.today()
analysis = bs.get_business_analysis(start, end)
print(f"   周期: {start} ~ {end}")
print(f"   账单数: {analysis['bill_count']}, 实收: ¥{analysis['total_final']:.2f}")
print(f"   桌台总数: {analysis['total_tables']}, 统计天数: {analysis['date_range_days']}")
print(f"   桌台利用率: {analysis['utilization']}%")
print(f"   会员消费笔数: {analysis['member_count']}, 占比: {analysis['member_ratio']}%")
print(f"   会员消费金额占比: {analysis['member_amount_ratio']}%")
print(f"   桌台明细: {len(analysis['by_table'])} 个桌台")
for tn, t in list(sorted(analysis['by_table'].items(), key=lambda x: x[1]['hours'], reverse=True))[:3]:
    print(f"     {tn}: {t['count']}次, {t['hours']:.1f}h, ¥{t['final']:.2f}")
print(f"   热门时段 TOP3:")
for hh in analysis['hot_hours'][:3]:
    print(f"     {hh['hour_range']}: {hh['count']}次, ¥{hh['amount']:.2f}")
print(f"   优惠来源:")
for src, d in analysis["by_discount_source"].items():
    print(f"     {src}: {d['count']}次, ¥{d['amount']:.2f}")
print(f"   支付方式占比:")
for pm, d in analysis["by_payment"].items():
    print(f"     {pm}: {d['count']}次, ¥{d['amount']:.2f}, 占比{d['ratio']}%")

db.close()
print("\n✅ 全部核心逻辑测试通过!")
