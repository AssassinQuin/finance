COMMON_CURRENCIES = {
    "USD": "美元",
    "CNY": "人民币",
    "EUR": "欧元",
    "GBP": "英镑",
    "JPY": "日元",
    "KRW": "韩元",
    "HKD": "港币",
    "TWD": "新台币",
    "SGD": "新加坡元",
    "AUD": "澳元",
    "CAD": "加元",
    "CHF": "瑞士法郎",
    "THB": "泰铢",
    "MYR": "马来西亚林吉特",
    "INR": "印度卢比",
    "RUB": "俄罗斯卢布",
}


def get_currency_name(code: str) -> str:
    return COMMON_CURRENCIES.get(code.upper(), code)


def format_currency_display(code: str) -> str:
    name = COMMON_CURRENCIES.get(code.upper())
    return f"{code}（{name}）" if name else code
