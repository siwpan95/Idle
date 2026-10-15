"""
数字格式化 — 处理放置游戏中超大数字的显示。
"""
import math


def fmt_num(num: float) -> str:
    """格式化超大数字，处理浮点数溢出（>10³⁰⁸）。"""
    if not isinstance(num, (int, float)):
        num = float(num)
    # 防御：指数乘区后期可能出现 inf/nan，直接返回 ∞，避免死循环。
    # 仅对 float 校验（int 永远有限；对超大 int 调 isinf/isnan 反而抛 OverflowError）。
    if isinstance(num, float) and (math.isinf(num) or math.isnan(num)):
        return "∞"
    if num < 10 ** 15:
        return f"{int(num):,}"
    if num < 10 ** 308:
        return f"{num:.1e}"
    quant = 0
    while num > 10 ** 308:
        quant += 1
        num //= 10 ** 308
    label = f"{num:.1e}"
    base, size_str = label.split("e+")
    size = int(size_str) + 308 * quant
    return f"{base}e+{fmt_num(size)}"


def fmt_gold(amount: float) -> str:
    """格式化金币数量。"""
    if amount < 10 ** 15:
        return f"{int(amount):,}"
    return fmt_num(amount)


def fmt_dps(val: float) -> str:
    """格式化 DPS 数值。"""
    return fmt_num(val)
