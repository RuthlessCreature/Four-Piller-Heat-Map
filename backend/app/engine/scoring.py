from __future__ import annotations

from math import copysign

from ..config import HIDDEN_STEM_WEIGHT, STEM_WEIGHT
from .bazi import BaziProfile, Pillar
from .constants import (
    BRANCH_CLASHES,
    BRANCH_COMBINES,
    BRANCH_HARMS,
    BRANCH_PUNISHES,
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    HIDDEN_STEMS,
    STEM_ELEMENT,
)
from .ten_gods import STRUCTURE_LABELS, TEN_GODS, TEN_GOD_TO_STRUCTURE, ten_god_relation

CATEGORIES = ["resource", "constraint", "support", "output", "competition"]


def relation_factor(day_master_element: str, other_element: str) -> float:
    if other_element == day_master_element:
        return 1.0
    if ELEMENT_GENERATES[other_element] == day_master_element:
        return 1.05
    if ELEMENT_GENERATES[day_master_element] == other_element:
        return 0.95
    if ELEMENT_CONTROLS[other_element] == day_master_element:
        return 1.10
    if ELEMENT_CONTROLS[day_master_element] == other_element:
        return 0.90
    return 1.0


def _pair_in_set(branch_a: str, branch_b: str, pairs: set[tuple[str, str]]) -> bool:
    return (branch_a, branch_b) in pairs or (branch_b, branch_a) in pairs


def volatility_factor(natal_branches: list[str], time_branch: str) -> float:
    clashes = sum(1 for b in natal_branches if _pair_in_set(b, time_branch, BRANCH_CLASHES))
    harms = sum(1 for b in natal_branches if _pair_in_set(b, time_branch, BRANCH_HARMS))
    punish = sum(1 for b in natal_branches if _pair_in_set(b, time_branch, BRANCH_PUNISHES))
    combines = sum(1 for b in natal_branches if _pair_in_set(b, time_branch, BRANCH_COMBINES))

    factor = 1.0 + 0.06 * (clashes + harms + punish) - 0.04 * combines
    return max(0.8, min(1.3, factor))


def score_pillar(profile: BaziProfile, pillar: Pillar) -> dict[str, float]:
    scores = {cat: 0.0 for cat in CATEGORIES}
    dm_element = profile.day_master_element
    capacity = 2 * profile.day_master_strength - 1

    def add_stem(stem: str, weight: float) -> None:
        other_element = STEM_ELEMENT[stem]
        factor = relation_factor(dm_element, other_element)
        ten_god = ten_god_relation(profile.day_master, stem)
        category = TEN_GOD_TO_STRUCTURE[ten_god]
        scores[category] += weight * factor

    add_stem(pillar.stem, STEM_WEIGHT)
    for hidden in HIDDEN_STEMS[pillar.branch]:
        add_stem(hidden, HIDDEN_STEM_WEIGHT)

    scores["resource"] *= capacity
    scores["constraint"] *= capacity

    volatility = volatility_factor(profile.natal_branches, pillar.branch)
    for cat in scores:
        scores[cat] *= volatility

    return scores


def score_pillar_ten_gods(profile: BaziProfile, pillar: Pillar) -> dict[str, float]:
    scores = {god: 0.0 for god in TEN_GODS}
    dm_element = profile.day_master_element
    capacity = 2 * profile.day_master_strength - 1

    def add_stem(stem: str, weight: float) -> None:
        other_element = STEM_ELEMENT[stem]
        factor = relation_factor(dm_element, other_element)
        ten_god = ten_god_relation(profile.day_master, stem)
        scores[ten_god] += weight * factor

    add_stem(pillar.stem, STEM_WEIGHT)
    for hidden in HIDDEN_STEMS[pillar.branch]:
        add_stem(hidden, HIDDEN_STEM_WEIGHT)

    for god in ("zhengcai", "piancai", "zhengguan", "qisha"):
        scores[god] *= capacity

    volatility = volatility_factor(profile.natal_branches, pillar.branch)
    for god in scores:
        scores[god] *= volatility

    return scores


def merge_scores(base: dict[str, float], addition: dict[str, float], weight: float) -> dict[str, float]:
    return {cat: base.get(cat, 0.0) + addition.get(cat, 0.0) * weight for cat in CATEGORIES}


def merge_ten_god_scores(
    base: dict[str, float],
    addition: dict[str, float],
    weight: float,
) -> dict[str, float]:
    return {god: base.get(god, 0.0) + addition.get(god, 0.0) * weight for god in TEN_GODS}


def score_summary(scores: dict[str, float]) -> float:
    return sum(abs(value) for value in scores.values())


def structure_labels() -> dict[str, str]:
    return STRUCTURE_LABELS.copy()


def risk_level_from_ratio(ratio: float) -> str:
    if ratio >= 1.2:
        return "高"
    if ratio >= 0.8:
        return "中"
    return "低"


def relative_ratio(current: float, baseline: float) -> float:
    return abs(current) / (abs(baseline) + 0.35)


def sign_label(value: float) -> str:
    return "匹配" if copysign(1.0, value) > 0 else "承载不足"
