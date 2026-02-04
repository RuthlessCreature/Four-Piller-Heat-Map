from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from math import floor

from ..adapters.sxtwl_adapter import (
    next_jieqi_datetime,
    pillars_from_lunar,
    pillars_from_solar,
    prev_jieqi_datetime,
)
from ..config import (
    CHINA_TZ,
    SHORT_CYCLE_FACTOR_MAX,
    SHORT_CYCLE_FACTOR_MIN,
    TIME_LAYER_WEIGHTS,
    YEAR_VIEW_WINDOW,
)
from ..engine.bazi import BaziProfile, Pillar, Pillars, compute_bazi_profile
from ..engine.constants import BRANCHES, STEMS, STEM_POLARITY
from ..engine.scoring import (
    CATEGORIES,
    merge_scores,
    merge_ten_god_scores,
    relative_ratio,
    risk_level_from_ratio,
    score_pillar,
    score_pillar_ten_gods,
    score_summary,
    structure_labels,
)
from ..engine.ten_gods import TEN_GODS, ten_god_labels
from ..models import BehaviorResponse, HeatmapResponse


@dataclass(frozen=True)
class BirthInfo:
    gender: str
    calendar: str
    birth_date: date
    birth_time: time
    is_leap_month: bool


@dataclass(frozen=True)
class TimePoint:
    label: str
    dt: datetime


@dataclass(frozen=True)
class LuckContext:
    forward: bool
    start_age_years: float
    month_index: int
    birth_dt: datetime


_GANZHI_CYCLE = [Pillar(stem=STEMS[i % 10], branch=BRANCHES[i % 12]) for i in range(60)]
_GANZHI_INDEX = {(pillar.stem, pillar.branch): idx for idx, pillar in enumerate(_GANZHI_CYCLE)}
_SECONDS_PER_YEAR = 365.2425 * 86400


def normalize_birth(birth) -> BirthInfo:
    return BirthInfo(
        gender=birth.gender,
        calendar=birth.calendar,
        birth_date=birth.birth_date,
        birth_time=birth.birth_time,
        is_leap_month=birth.is_leap_month,
    )


def _pillar_payload(pillar: Pillar) -> dict[str, str]:
    return {"stem": pillar.stem, "branch": pillar.branch, "label": f"{pillar.stem}{pillar.branch}"}


def _time_pillars_payload(pillars: Pillars) -> dict[str, dict[str, str]]:
    return {
        "year": _pillar_payload(pillars.year),
        "month": _pillar_payload(pillars.month),
        "day": _pillar_payload(pillars.day),
        "hour": _pillar_payload(pillars.hour),
    }


def _china_datetime(birth_date: date, birth_time: time) -> datetime:
    return datetime(
        birth_date.year,
        birth_date.month,
        birth_date.day,
        birth_time.hour,
        birth_time.minute,
        birth_time.second,
        tzinfo=CHINA_TZ,
    )


def _luck_direction(birth: BirthInfo, birth_pillars: Pillars) -> bool:
    # 子平法：阳男阴女顺行，阴男阳女逆行。
    is_yang = STEM_POLARITY[birth_pillars.year.stem] == "yang"
    return (birth.gender == "male" and is_yang) or (birth.gender == "female" and not is_yang)


def _luck_start_age_years(birth_dt: datetime, forward: bool) -> float:
    # 子平法：以出生时刻到最近节气的时间差，三天折一年。
    if forward:
        target = next_jieqi_datetime(birth_dt)
        delta = target - birth_dt
    else:
        target = prev_jieqi_datetime(birth_dt)
        delta = birth_dt - target
    diff_days = delta.total_seconds() / 86400
    return diff_days / 3.0


def _luck_context(birth: BirthInfo, birth_pillars: Pillars) -> LuckContext:
    birth_dt = _china_datetime(birth.birth_date, birth.birth_time)
    forward = _luck_direction(birth, birth_pillars)
    start_age_years = _luck_start_age_years(birth_dt, forward)
    month_index = _GANZHI_INDEX[(birth_pillars.month.stem, birth_pillars.month.branch)]
    return LuckContext(
        forward=forward,
        start_age_years=start_age_years,
        month_index=month_index,
        birth_dt=birth_dt,
    )


def _birth_pillars(birth: BirthInfo) -> Pillars:
    if birth.calendar == "solar":
        return pillars_from_solar(
            birth.birth_date.year,
            birth.birth_date.month,
            birth.birth_date.day,
            birth.birth_time.hour,
        )
    return pillars_from_lunar(
        birth.birth_date.year,
        birth.birth_date.month,
        birth.birth_date.day,
        birth.birth_time.hour,
        birth.is_leap_month,
    )


def _time_pillars(dt: datetime) -> Pillars:
    return pillars_from_solar(dt.year, dt.month, dt.day, dt.hour)


def _big_luck_pillar(context: LuckContext, target_dt: datetime) -> Pillar:
    age_years = (target_dt - context.birth_dt).total_seconds() / _SECONDS_PER_YEAR
    cycles = floor((age_years - context.start_age_years) / 10.0)
    # 起运前 cycles 会为 -1，此时 step=0，等同使用本命月柱占位。
    step = (cycles + 1) * (1 if context.forward else -1)
    idx = (context.month_index + step) % 60
    return _GANZHI_CYCLE[idx]


def _build_profile(birth: BirthInfo) -> BaziProfile:
    pillars = _birth_pillars(birth)
    return compute_bazi_profile(pillars, stem_weight=1.0, hidden_weight=0.6)


def _year_points(center_year: int) -> list[TimePoint]:
    # Assumption: use mid-year noon as the representative point for yearly buckets.
    start = center_year - (YEAR_VIEW_WINDOW // 2) + 1
    return [
        TimePoint(label=str(year), dt=datetime(year, 7, 1, 12, 0, tzinfo=CHINA_TZ))
        for year in range(start, start + YEAR_VIEW_WINDOW)
    ]


def _month_points(year: int) -> list[TimePoint]:
    # Assumption: use mid-month noon as the representative point for monthly buckets.
    return [
        TimePoint(label=f"{month:02d}月", dt=datetime(year, month, 15, 12, 0, tzinfo=CHINA_TZ))
        for month in range(1, 13)
    ]


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return (date(year + 1, 1, 1) - date(year, month, 1)).days
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def _day_points(year: int, month: int) -> list[TimePoint]:
    # Assumption: use local noon as the representative point for daily buckets.
    days = _days_in_month(year, month)
    return [
        TimePoint(label=f"{day:02d}日", dt=datetime(year, month, day, 12, 0, tzinfo=CHINA_TZ))
        for day in range(1, days + 1)
    ]


def _hour_points(year: int, month: int, day: int) -> list[TimePoint]:
    # Assumption: use the hour start as the representative point for hourly buckets.
    return [
        TimePoint(
            label=f"{hour:02d}:00",
            dt=datetime(year, month, day, hour, 0, tzinfo=CHINA_TZ),
        )
        for hour in range(0, 24)
    ]


def _points_for_view(view: str, year: int | None, month: int | None, day: int | None) -> list[TimePoint]:
    if view == "year":
        if year is None:
            raise ValueError("year 视图需要提供 year")
        return _year_points(year)
    if view == "month":
        if year is None:
            raise ValueError("month 视图需要提供 year")
        return _month_points(year)
    if view == "day":
        if year is None or month is None:
            raise ValueError("day 视图需要提供 year 与 month")
        return _day_points(year, month)
    if view == "hour":
        if year is None or month is None or day is None:
            raise ValueError("hour 视图需要提供 year、month、day")
        return _hour_points(year, month, day)
    raise ValueError("未知视图类型")


def _layer_scores(
    profile: BaziProfile,
    context: LuckContext,
    dt: datetime,
) -> dict[str, dict[str, float]]:
    pillars = _time_pillars(dt)
    big_luck = _big_luck_pillar(context, dt)
    return {
        "big_luck": score_pillar(profile, big_luck),
        "year": score_pillar(profile, pillars.year),
        "month": score_pillar(profile, pillars.month),
        "day": score_pillar(profile, pillars.day),
        "hour": score_pillar(profile, pillars.hour),
    }


def _layer_ten_god_scores(
    profile: BaziProfile,
    context: LuckContext,
    dt: datetime,
) -> dict[str, dict[str, float]]:
    pillars = _time_pillars(dt)
    big_luck = _big_luck_pillar(context, dt)
    return {
        "big_luck": score_pillar_ten_gods(profile, big_luck),
        "year": score_pillar_ten_gods(profile, pillars.year),
        "month": score_pillar_ten_gods(profile, pillars.month),
        "day": score_pillar_ten_gods(profile, pillars.day),
        "hour": score_pillar_ten_gods(profile, pillars.hour),
    }


def _weighted_scores(layer_scores: dict[str, dict[str, float]]) -> dict[str, float]:
    merged = {cat: 0.0 for cat in CATEGORIES}
    for layer, scores in layer_scores.items():
        merged = merge_scores(merged, scores, TIME_LAYER_WEIGHTS[layer])
    return merged


def _weighted_ten_god_scores(layer_scores: dict[str, dict[str, float]]) -> dict[str, float]:
    merged = {god: 0.0 for god in TEN_GODS}
    for layer, scores in layer_scores.items():
        merged = merge_ten_god_scores(merged, scores, TIME_LAYER_WEIGHTS[layer])
    return merged


def _short_cycle_component(layer_scores: dict[str, dict[str, float]]) -> float:
    month = score_summary(layer_scores["month"]) * TIME_LAYER_WEIGHTS["month"]
    day = score_summary(layer_scores["day"]) * TIME_LAYER_WEIGHTS["day"]
    hour = score_summary(layer_scores["hour"]) * TIME_LAYER_WEIGHTS["hour"]
    return month + day + hour


def build_heatmap_response(request) -> HeatmapResponse:
    birth = normalize_birth(request.birth)
    profile = _build_profile(birth)
    birth_pillars = _birth_pillars(birth)
    luck_context = _luck_context(birth, birth_pillars)
    points = _points_for_view(request.view, request.year, request.month, request.day)

    short_components = []
    cell_raw = []
    ten_god_snapshots = []

    for point in points:
        time_pillars = _time_pillars(point.dt)
        big_luck_pillar = _big_luck_pillar(luck_context, point.dt)
        layer_scores = _layer_scores(profile, luck_context, point.dt)
        ten_god_layer_scores = _layer_ten_god_scores(profile, luck_context, point.dt)
        ten_god_scores = _weighted_ten_god_scores(ten_god_layer_scores)
        long_base = (
            score_summary(layer_scores["big_luck"]) * TIME_LAYER_WEIGHTS["big_luck"]
            + score_summary(layer_scores["year"]) * TIME_LAYER_WEIGHTS["year"]
        )
        short_component = _short_cycle_component(layer_scores)
        short_components.append(short_component)
        cell_raw.append((point, long_base, short_component))
        ten_god_snapshots.append(
            (
                point,
                ten_god_scores,
                {
                    "big_luck": _pillar_payload(big_luck_pillar),
                    **_time_pillars_payload(time_pillars),
                },
            )
        )

    if not cell_raw:
        raise ValueError("无法生成 heatmap 数据")

    short_min = min(short_components)
    short_max = max(short_components)
    short_span = max(1e-6, short_max - short_min)

    activations = []
    for point, long_base, short_component in cell_raw:
        short_norm = (short_component - short_min) / short_span
        short_factor = SHORT_CYCLE_FACTOR_MIN + (SHORT_CYCLE_FACTOR_MAX - SHORT_CYCLE_FACTOR_MIN) * short_norm
        activation = long_base * short_factor
        activations.append((point, activation))

    values = [value for _, value in activations]
    v_min = min(values)
    v_max = max(values)
    span = max(1e-6, v_max - v_min)

    max_abs_ten_god = max(
        (abs(score) for _, scores, _ in ten_god_snapshots for score in scores.values()),
        default=0.0,
    )
    max_abs_ten_god = max(1e-6, max_abs_ten_god)
    ten_god_name_map = ten_god_labels()

    cells = [
        {
            "label": point.label,
            "value": (value - v_min) / span,
            "iso_datetime": point.dt.isoformat(),
            "ten_god_scores": [
                {
                    "key": god,
                    "label": ten_god_name_map.get(god, god),
                    "score": max(-100, min(100, int(round((scores[god] / max_abs_ten_god) * 100)))),
                }
                for god in TEN_GODS
            ],
            "pillars": pillars_payload,
        }
        for (point, value), (_, scores, pillars_payload) in zip(activations, ten_god_snapshots)
    ]

    next_view = {"year": "month", "month": "day", "day": "hour", "hour": None}[request.view]

    return HeatmapResponse(
        view=request.view,
        next_view=next_view,
        cells=cells,
        birth_pillars=_time_pillars_payload(birth_pillars),
        definition=(
            "颜色强度表示：该时间层级中结构被激活的相对强度；"
            "格子内展示对应层级的大运/流年/流月/流日/流时天干地支；"
            "十神评分为视图内相对值（-100 ~ 100），负值代表承载不足。"
        ),
        uncertainty_note="该结果为时间结构相对强度展示，受时间边界与输入精度影响，存在不确定性。",
        meta={
            "day_master": profile.day_master,
            "day_master_strength": profile.day_master_strength_label,
            "structure_labels": structure_labels(),
            "ten_god_labels": ten_god_name_map,
        },
    )


def build_behavior_response(request) -> BehaviorResponse:
    birth = normalize_birth(request.birth)
    profile = _build_profile(birth)
    birth_pillars = _birth_pillars(birth)
    luck_context = _luck_context(birth, birth_pillars)

    try:
        focus_dt = datetime.fromisoformat(request.focus_datetime)
    except ValueError as exc:
        raise ValueError("focus_datetime 需为 ISO 格式日期时间") from exc

    if focus_dt.tzinfo is None:
        focus_dt = focus_dt.replace(tzinfo=CHINA_TZ)

    layer_scores = _layer_scores(profile, luck_context, focus_dt)
    current_scores = _weighted_scores(layer_scores)

    natal_layers = _layer_scores(profile, luck_context, _china_datetime(birth.birth_date, birth.birth_time))
    baseline_scores = _weighted_scores(natal_layers)

    labels = structure_labels()
    ratios = {}
    abs_scores = {cat: abs(current_scores[cat]) for cat in CATEGORIES}
    total_abs = sum(abs_scores.values()) or 1e-6
    relative_strengths = {cat: abs_scores[cat] / total_abs for cat in CATEGORIES}
    levels = {}
    prompts = []
    for category in CATEGORIES:
        ratios[category] = relative_ratio(current_scores[category], baseline_scores[category])
        levels[category] = risk_level_from_ratio(ratios[category])

    if all(level == "低" for level in levels.values()):
        ordered = sorted(CATEGORIES, key=lambda cat: ratios[cat], reverse=True)
        for idx, category in enumerate(ordered):
            if idx == 0:
                levels[category] = "高"
            elif idx <= 2:
                levels[category] = "中"
            else:
                levels[category] = "低"

    for category in CATEGORIES:
        label = labels[category]
        level = levels[category]
        prompts.append(
            {
                "label": label,
                "risk_level": level,
                "text": f"从时间结构上看，在当前时间结构下，{label}的风险暴露水平为：{level}。",
                "relative_strength": relative_strengths[category],
            }
        )

    return BehaviorResponse(
        focus_datetime=focus_dt.isoformat(),
        prompts=prompts,
        uncertainty_note=(
            "行为提示仅反映结构风险暴露强度，风险级别为当前时间结构下的相对分布，"
            "受时间边界与输入精度影响，存在不确定性，不构成结论或建议。"
        ),
    )
