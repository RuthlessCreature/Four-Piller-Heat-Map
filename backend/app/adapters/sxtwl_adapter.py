from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from ..config import CHINA_TZ
from ..engine.bazi import Pillar, Pillars
from ..engine.constants import BRANCHES, STEMS


@dataclass(frozen=True)
class GanzhiPillars:
    pillars: Pillars


def _require_sxtwl():
    try:
        import sxtwl

        return sxtwl
    except Exception as exc:  # pragma: no cover - runtime guard
        raise RuntimeError("sxtwl 未安装或不可用，请先安装 sxtwl。") from exc


def _gz_to_pillar(gz) -> Pillar:
    tg = getattr(gz, "tg", None)
    dz = getattr(gz, "dz", None)
    if tg is None or dz is None:
        raise RuntimeError("sxtwl GZ 对象格式未知，无法读取天干地支索引。")
    return Pillar(stem=STEMS[tg], branch=BRANCHES[dz])


def pillars_from_solar(year: int, month: int, day: int, hour: int) -> Pillars:
    sxtwl = _require_sxtwl()
    solar_day = sxtwl.fromSolar(year, month, day)
    year_gz = solar_day.getYearGZ()
    month_gz = solar_day.getMonthGZ()
    day_gz = solar_day.getDayGZ()
    hour_gz = solar_day.getHourGZ(hour)
    return Pillars(
        year=_gz_to_pillar(year_gz),
        month=_gz_to_pillar(month_gz),
        day=_gz_to_pillar(day_gz),
        hour=_gz_to_pillar(hour_gz),
    )


def pillars_from_lunar(year: int, month: int, day: int, hour: int, is_leap: bool) -> Pillars:
    sxtwl = _require_sxtwl()
    lunar_day = sxtwl.fromLunar(year, month, day, is_leap)
    year_gz = lunar_day.getYearGZ()
    month_gz = lunar_day.getMonthGZ()
    day_gz = lunar_day.getDayGZ()
    hour_gz = lunar_day.getHourGZ(hour)
    return Pillars(
        year=_gz_to_pillar(year_gz),
        month=_gz_to_pillar(month_gz),
        day=_gz_to_pillar(day_gz),
        hour=_gz_to_pillar(hour_gz),
    )


def _jieqi_datetime_for_day(sxtwl, year: int, month: int, day: int) -> Optional[datetime]:
    solar_day = sxtwl.fromSolar(year, month, day)
    if hasattr(solar_day, "hasJieQi") and not solar_day.hasJieQi():
        return None
    if hasattr(solar_day, "getJieQi") and solar_day.getJieQi() < 0:
        return None
    if not hasattr(solar_day, "getJieQiJD"):
        raise RuntimeError("sxtwl 未提供节气精确时间接口，无法计算起运。")
    jd = solar_day.getJieQiJD()
    dd = sxtwl.JD2DD(jd)
    if isinstance(dd, tuple):
        year, month, day, hour, minute, second = dd[:6]
    else:
        year = getattr(dd, "y", getattr(dd, "Y", None))
        month = getattr(dd, "M", getattr(dd, "month", getattr(dd, "m", None)))
        day = getattr(dd, "D", getattr(dd, "day", getattr(dd, "d", None)))
        hour = getattr(dd, "h", getattr(dd, "H", getattr(dd, "hour", 0)))
        minute = getattr(dd, "mi", getattr(dd, "min", getattr(dd, "minute", 0)))
        second = getattr(dd, "s", getattr(dd, "S", getattr(dd, "second", 0)))
    if not (1 <= int(month) <= 12):
        raise RuntimeError("sxtwl 节气时间解析失败：月份异常。")
    if not (1 <= int(day) <= 31):
        raise RuntimeError("sxtwl 节气时间解析失败：日期异常。")
    return datetime(
        int(year),
        int(month),
        int(day),
        int(hour),
        int(minute),
        int(second),
        tzinfo=CHINA_TZ,
    )


def next_jieqi_datetime(dt: datetime) -> datetime:
    sxtwl = _require_sxtwl()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CHINA_TZ)
    cursor = dt.date()
    for _ in range(400):
        jieqi_dt = _jieqi_datetime_for_day(sxtwl, cursor.year, cursor.month, cursor.day)
        if jieqi_dt and jieqi_dt >= dt:
            return jieqi_dt
        cursor += timedelta(days=1)
    raise RuntimeError("无法定位下一个节气，请检查 sxtwl 可用性。")


def prev_jieqi_datetime(dt: datetime) -> datetime:
    sxtwl = _require_sxtwl()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CHINA_TZ)
    cursor = dt.date()
    for _ in range(400):
        jieqi_dt = _jieqi_datetime_for_day(sxtwl, cursor.year, cursor.month, cursor.day)
        if jieqi_dt and jieqi_dt <= dt:
            return jieqi_dt
        cursor -= timedelta(days=1)
    raise RuntimeError("无法定位上一个节气，请检查 sxtwl 可用性。")
