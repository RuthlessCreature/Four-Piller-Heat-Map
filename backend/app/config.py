from zoneinfo import ZoneInfo

# Time assumptions (must be fixed in code, not exposed as user options):
# 1) Input birth date/time is interpreted as China Standard Time (UTC+8).
# 2) When exact 大运起运时间无法由库直接给出时，使用出生年份对齐的十年周期近似。

CHINA_TZ = ZoneInfo("Asia/Shanghai")

TIME_LAYER_WEIGHTS = {
    "big_luck": 0.40,
    "year": 0.30,
    "month": 0.20,
    "day": 0.08,
    "hour": 0.02,
}

STEM_WEIGHT = 1.0
HIDDEN_STEM_WEIGHT = 0.6

SHORT_CYCLE_FACTOR_MIN = 0.85
SHORT_CYCLE_FACTOR_MAX = 1.15

YEAR_VIEW_WINDOW = 10
