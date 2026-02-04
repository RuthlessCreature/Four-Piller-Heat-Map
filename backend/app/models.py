from __future__ import annotations

from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BirthInput(BaseModel):
    gender: Literal["male", "female"]
    calendar: Literal["solar", "lunar"]
    birth_date: date
    birth_time: time
    is_leap_month: bool = False


class HeatmapRequest(BaseModel):
    birth: BirthInput
    view: Literal["year", "month", "day", "hour"]
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None


class GanzhiPillar(BaseModel):
    stem: str
    branch: str
    label: str


class TimePillars(BaseModel):
    year: GanzhiPillar
    month: GanzhiPillar
    day: GanzhiPillar
    hour: GanzhiPillar


class CellPillars(TimePillars):
    big_luck: GanzhiPillar


class TenGodScore(BaseModel):
    key: str
    label: str
    score: int = Field(ge=-100, le=100)


class HeatmapCell(BaseModel):
    label: str
    value: float = Field(ge=0.0, le=1.0)
    iso_datetime: str
    ten_god_scores: list[TenGodScore]
    pillars: CellPillars


class HeatmapResponse(BaseModel):
    view: Literal["year", "month", "day", "hour"]
    next_view: Optional[Literal["month", "day", "hour"]]
    cells: list[HeatmapCell]
    birth_pillars: TimePillars
    definition: str
    uncertainty_note: str
    meta: dict


class BehaviorRequest(BaseModel):
    birth: BirthInput
    focus_datetime: str


class BehaviorPrompt(BaseModel):
    label: str
    risk_level: Literal["高", "中", "低"]
    text: str
    relative_strength: float = Field(ge=0.0, le=1.0)


class BehaviorResponse(BaseModel):
    focus_datetime: str
    prompts: list[BehaviorPrompt]
    uncertainty_note: str
