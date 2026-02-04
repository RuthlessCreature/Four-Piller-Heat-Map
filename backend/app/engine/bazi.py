from __future__ import annotations

from dataclasses import dataclass

from .constants import ELEMENT_CONTROLS, ELEMENT_GENERATES, HIDDEN_STEMS, STEM_ELEMENT


@dataclass(frozen=True)
class Pillar:
    stem: str
    branch: str


@dataclass(frozen=True)
class Pillars:
    year: Pillar
    month: Pillar
    day: Pillar
    hour: Pillar


@dataclass(frozen=True)
class BaziProfile:
    pillars: Pillars
    day_master: str
    day_master_element: str
    day_master_strength: float
    day_master_strength_label: str
    element_balance: dict[str, float]
    natal_branches: list[str]


def _element_balance(pillars: Pillars, stem_weight: float, hidden_weight: float) -> dict[str, float]:
    counts = {"Wood": 0.0, "Fire": 0.0, "Earth": 0.0, "Metal": 0.0, "Water": 0.0}
    for pillar in (pillars.year, pillars.month, pillars.day, pillars.hour):
        stem_element = STEM_ELEMENT[pillar.stem]
        counts[stem_element] += stem_weight
        for hidden in HIDDEN_STEMS[pillar.branch]:
            counts[STEM_ELEMENT[hidden]] += hidden_weight
    return counts


def _day_master_strength(day_master_element: str, balance: dict[str, float]) -> float:
    support = balance[day_master_element] + balance[ELEMENT_GENERATES[day_master_element]]
    drain = balance[ELEMENT_CONTROLS[day_master_element]] + balance[
        ELEMENT_GENERATES[ELEMENT_CONTROLS[day_master_element]]
    ]
    total = support + drain + 1e-6
    raw = (support - drain) / total
    return max(0.0, min(1.0, 0.5 + 0.5 * raw))


def _strength_label(strength: float) -> str:
    if strength >= 0.62:
        return "strong"
    if strength <= 0.38:
        return "weak"
    return "balanced"


def compute_bazi_profile(pillars: Pillars, stem_weight: float, hidden_weight: float) -> BaziProfile:
    day_master = pillars.day.stem
    day_master_element = STEM_ELEMENT[day_master]
    balance = _element_balance(pillars, stem_weight, hidden_weight)
    strength = _day_master_strength(day_master_element, balance)
    return BaziProfile(
        pillars=pillars,
        day_master=day_master,
        day_master_element=day_master_element,
        day_master_strength=strength,
        day_master_strength_label=_strength_label(strength),
        element_balance=balance,
        natal_branches=[pillars.year.branch, pillars.month.branch, pillars.day.branch, pillars.hour.branch],
    )
