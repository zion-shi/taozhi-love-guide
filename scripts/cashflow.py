"""Recheck the F.4 and F.5 arithmetic, without scoring a household."""

import argparse
from decimal import Decimal, InvalidOperation, localcontext


def amount(value):
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError("金额应为有限、非负数字。")
    if not number.is_finite() or number < 0:
        raise argparse.ArgumentTypeError("金额应为有限、非负数字；口径不明时请留空。")
    if number and (number.adjusted() > 18 or number.adjusted() < -8):
        raise argparse.ArgumentTypeError("金额数量级异常，请核对单位后输入。")
    return number


def quotient(numerator, denominator, percent=False):
    if denominator == 0:
        return "不计算（分母为零）"
    if numerator is None or denominator is None:
        return "不计算（所需金额未知）"
    with localcontext() as context:
        context.prec = 40
        value = numerator / denominator * (100 if percent else 1)
        return f"{value:.2f}%" if percent else f"{value:.2f} 个月"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--income", type=amount, help="同周期税后月收入")
    parser.add_argument("--fixed", type=amount, help="非债务硬刚性月支出")
    parser.add_argument("--debt", type=amount, help="最低月债务偿付")
    parser.add_argument("--liquid", type=amount, help="可立即动用且未受限的存量")
    parser.add_argument("--emergency", type=amount, help="应急必要月支出")
    parser.add_argument("--ordinary", type=amount, help="普通月实际对外总支出")
    args = parser.parse_args()
    hard = args.fixed + args.debt if args.fixed is not None and args.debt is not None else None
    print("《人间爱情指南》v1.2 · F.4、F.5。输入须为同一家庭范围、币种和时间口径。")
    print("FCR＝（非债务硬刚性月支出＋最低月债务偿付）÷税后月收入：" + quotient(hard, args.income, True))
    print("DTI＝最低月债务偿付÷税后月收入：" + quotient(args.debt, args.income, True))
    print("SR＝可立即动用且未受限的存量÷应急必要月支出：" + quotient(args.liquid, args.emergency))
    print("MR＝同一存量÷普通月实际对外总支出：" + quotient(args.liquid, args.ordinary))
    print("债务已计入 FCR，不再加 DTI。SR 与 MR 使用同一存量，不能相加。内部转账不重复算对外消费。")
    print("这些数值只核对资源条件，不能单独证明关系健康或决定是否结婚。")


if __name__ == "__main__":
    main()
