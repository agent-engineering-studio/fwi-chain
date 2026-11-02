"""A deterministic, synthetic fire season for the examples.

This is *not* observed data. It is a seeded toy climate, shaped like a
Mediterranean year (wet spring, hot dry summer, autumn storms), so the
examples and the documentation figures are reproducible without a download.
Swap it for real noon observations or a weather model in any real use.
"""

from __future__ import annotations

import datetime as dt
import math
import random
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoonReading:
    """The four inputs of the chain, taken at local noon."""

    day: dt.date
    temperature_c: float
    relative_humidity_pct: float
    wind_speed_kmh: float
    rain_24h_mm: float


def synthetic_season(
    start: dt.date = dt.date(2026, 4, 1),
    end: dt.date = dt.date(2026, 10, 31),
    *,
    seed: int = 7,
) -> Iterator[NoonReading]:
    """Yield one noon reading per day from ``start`` to ``end`` inclusive."""
    rng = random.Random(seed)
    raining = False
    day = start
    while day <= end:
        # 0 on 1 January, 1 at the height of summer (late July), back to 0.
        doy = day.timetuple().tm_yday
        summer = 0.5 - 0.5 * math.cos(2.0 * math.pi * (doy - 20) / 365.0)

        # A two-state Markov chain makes rain come in spells, not single days.
        p_rain = 0.06 + 0.28 * (1.0 - summer) ** 2
        raining = rng.random() < (0.55 if raining else p_rain)
        rain = round(rng.expovariate(1.0 / 9.0), 1) if raining else 0.0

        temperature = 9.0 + 22.0 * summer + rng.gauss(0.0, 2.5) - (4.0 if raining else 0.0)
        humidity = 72.0 - 42.0 * summer + rng.gauss(0.0, 8.0) + (22.0 if raining else 0.0)
        wind = max(rng.gammavariate(3.0, 4.5), 0.0)

        yield NoonReading(
            day=day,
            temperature_c=round(temperature, 1),
            relative_humidity_pct=round(min(max(humidity, 8.0), 100.0)),
            wind_speed_kmh=round(wind, 1),
            rain_24h_mm=rain,
        )
        day += dt.timedelta(days=1)
