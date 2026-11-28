"""The noon reading of a day, from hourly weather.

The chain wants one reading a day, taken at local solar noon: temperature,
humidity and wind of that hour, and the rain of the 24 hours before it.
Weather usually comes hour by hour. Two things can go wrong on the way, and
both are silent unless someone counts:

* the noon hour is missing, and the nearest hour that has the three values
  is taken instead. An hour or two away is still a noon reading; nine hours
  away is the weather of the night;
* hours of rain are missing, and a sum over what is there reads them as dry.
  A storm in the missing hours becomes a dry day, and the drought codes carry
  it for weeks.

:func:`noon_reading` takes the largest distance from noon and the fewest
hours of rain it may accept as arguments, with no defaults, and always says
which hour it read and how many hours of rain were not measured.

Pure: the samples are the caller's, and so is the time zone. ``noon_hour``
is an hour on the samples' own clock (for samples in UTC over Italy, 11).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from fwi_chain.walk import NoonObservation

__all__ = ["HourlySample", "NoonReading", "noon_reading", "noon_readings"]

Refusal = Literal["no reading", "too far from noon", "too few hours of rain"]


@dataclass(frozen=True, slots=True)
class HourlySample:
    """One hour of weather. ``None`` is "not measured", never zero.

    ``rain_mm`` is the rain of the hour that ends at ``time``. A dry hour is
    ``0.0``; an hour nobody measured is ``None``.
    """

    time: datetime
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    rain_mm: float | None = None

    @property
    def has_fire_weather(self) -> bool:
        """Whether temperature, humidity and wind are all there."""
        return (
            self.temperature_c is not None
            and self.relative_humidity_pct is not None
            and self.wind_speed_kmh is not None
        )


@dataclass(frozen=True, slots=True)
class NoonReading:
    """What was read for one day, and how good a reading it is.

    ``observation`` is ``None`` when the day has no usable reading, and
    ``refused`` says why. The other fields are filled whenever an hour with
    the three values was found, also when the reading was then refused.
    """

    day: date
    observation: NoonObservation | None
    #: Why there is no observation, or ``None`` when there is one.
    refused: Refusal | None = None
    #: The hour whose temperature, humidity and wind were read.
    time: datetime | None = None
    #: How many hours ``time`` is from ``noon_hour``.
    hours_from_noon: int | None = None
    #: Hours of rain measured in the 24 before ``time``.
    rain_hours: int = 0
    #: Hours of rain not measured in the 24 before ``time``: ``24 - rain_hours``.
    rain_hours_missing: int = 24
    #: The rain of the measured hours. With hours missing, a lower bound.
    rain_measured_mm: float = 0.0


def noon_reading(
    samples: Iterable[HourlySample],
    day: date,
    *,
    noon_hour: int,
    max_hours_from_noon: int | None,
    min_rain_hours: int,
) -> NoonReading:
    """The noon reading of ``day`` from hourly ``samples``.

    The hour read is the one of ``day`` nearest to ``noon_hour`` among those
    that have temperature, humidity and wind (the earlier one on a tie). The
    rain is the sum of the hours after ``time - 24 h`` up to ``time``: the
    window moves with the hour read.

    ``max_hours_from_noon``: the reading is refused when the hour read is
    further than this from ``noon_hour``; ``None`` accepts any hour of the day.
    ``min_rain_hours``: the reading is refused when fewer than this many of
    the 24 hours of rain were measured; ``0`` accepts any, and then missing
    hours count as dry. Both are required: how much to accept is a choice,
    and a default would make it for the caller.

    Humidity is kept within 0-100 and wind and rain at 0 or above, as the
    chain itself does. Samples are expected one per hour.
    """
    if not 0 <= noon_hour <= 23:
        raise ValueError(f"noon_hour must be in 0..23, got {noon_hour}")
    if not 0 <= min_rain_hours <= 24:
        raise ValueError(f"min_rain_hours must be in 0..24, got {min_rain_hours}")
    if max_hours_from_noon is not None and max_hours_from_noon < 0:
        raise ValueError(f"max_hours_from_noon must be 0 or more, got {max_hours_from_noon}")

    samples = list(samples)
    candidates = sorted(
        (s for s in samples if s.time.date() == day and s.has_fire_weather), key=lambda s: s.time
    )
    if not candidates:
        return NoonReading(day=day, observation=None, refused="no reading")
    noon = min(candidates, key=lambda s: abs(s.time.hour - noon_hour))
    distance = abs(noon.time.hour - noon_hour)
    start = noon.time - timedelta(hours=24)
    rain = [
        max(s.rain_mm, 0.0)
        for s in samples
        if s.rain_mm is not None and start < s.time <= noon.time
    ]
    measured = min(len(rain), 24)
    total = float(sum(rain))

    refused: Refusal | None = None
    if max_hours_from_noon is not None and distance > max_hours_from_noon:
        refused = "too far from noon"
    elif measured < min_rain_hours:
        refused = "too few hours of rain"

    # has_fire_weather proved the three are there.
    assert noon.temperature_c is not None
    assert noon.relative_humidity_pct is not None
    assert noon.wind_speed_kmh is not None
    observation = NoonObservation(
        temperature_c=noon.temperature_c,
        relative_humidity_pct=min(max(noon.relative_humidity_pct, 0.0), 100.0),
        wind_speed_kmh=max(noon.wind_speed_kmh, 0.0),
        rain_24h_mm=total,
    )
    return NoonReading(
        day=day,
        observation=None if refused else observation,
        refused=refused,
        time=noon.time,
        hours_from_noon=distance,
        rain_hours=measured,
        rain_hours_missing=24 - measured,
        rain_measured_mm=total,
    )


def noon_readings(
    samples: Iterable[HourlySample],
    days: Sequence[date],
    *,
    noon_hour: int,
    max_hours_from_noon: int | None,
    min_rain_hours: int,
) -> dict[date, NoonReading]:
    """:func:`noon_reading` for each of ``days``, reading the samples once.

    The same answers as calling it day by day. Each day looks only at its own
    samples and at those of the day before, so a year of hours costs a year
    of hours and not a year for every day.

    The observations the chain takes are
    ``{d: r.observation for d, r in readings.items() if r.observation}``.
    """
    by_day: dict[date, list[HourlySample]] = defaultdict(list)
    for sample in samples:
        by_day[sample.time.date()].append(sample)
    return {
        day: noon_reading(
            by_day.get(day - timedelta(days=1), []) + by_day.get(day, []),
            day,
            noon_hour=noon_hour,
            max_hours_from_noon=max_hours_from_noon,
            min_rain_hours=min_rain_hours,
        )
        for day in days
    }
