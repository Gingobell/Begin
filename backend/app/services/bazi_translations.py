"""bazi_translations stub — used by fortune.py mock fallback only."""


def translate_heavenly_stem(stem: str, language: str = "zh-CN") -> str:
    return stem


def translate_ten_god(god: str, language: str = "zh-CN") -> str:
    return god


def translate_ten_god_analysis(god: str, language: str = "zh-CN") -> str:
    return f"{god}的影响"
