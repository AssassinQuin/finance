"""公共计算工具函数"""


def calc_change_percent(price: float, prev_close: float) -> float:
    if prev_close > 0:
        return (price - prev_close) / prev_close * 100
    return 0.0
