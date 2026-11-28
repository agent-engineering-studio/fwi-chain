"""Where an FWI falls in the distribution of its place and its month.

An FWI of 30 is an ordinary August day in one place and a once-in-a-decade
day in another. A climatology says which: years of chain summarised, per
place and per month, in 21 quantiles (0, 5, ..., 100).

Pure statistics on lists of numbers. Where the years of weather come from
and where the quantiles are stored stay with the caller.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from datetime import date, timedelta
from itertools import pairwise

from fwi_chain.chain import FwiParams, FwiState, advance
from fwi_chain.walk import NoonObservation

__all__ = [
    "QUANTILE_LEVELS",
    "accumulate_monthly",
    "coverage_is_valid",
    "node_ceiling",
    "percentile",
    "quantiles",
]

QUANTILE_LEVELS: tuple[float, ...] = tuple(5.0 * i for i in range(21))
"""The levels of the stored quantiles: 0, 5, ..., 100."""


def quantiles(values: Sequence[float]) -> list[float]:
    """The 21 quantiles of ``values``, linearly interpolated between ranks.

    Raises ``ValueError`` on an empty sequence.
    """
    if not values:
        raise ValueError("a distribution needs values")
    ordered = sorted(values)
    n = len(ordered)
    out: list[float] = []
    for level in QUANTILE_LEVELS:
        pos = level / 100.0 * (n - 1)
        low = int(pos)
        high = min(low + 1, n - 1)
        fraction = pos - low
        out.append(ordered[low] + (ordered[high] - ordered[low]) * fraction)
    return out


def _flat_centre(value: float, q: Sequence[float]) -> float:
    equal = [level for level, v in zip(QUANTILE_LEVELS, q, strict=True) if v == value]
    return (equal[0] + equal[-1]) / 2


def percentile(value: float, q: Sequence[float]) -> float:
    """The percentile (0-100) at which ``value`` falls among the quantiles ``q``.

    Interpolated between the two quantiles around it; outside the
    distribution it is 0 or 100. On a flat stretch (many winter days at FWI
    0) it takes the centre of the stretch, so a value equal to half the
    distribution reads as neither its minimum nor its maximum.

    Raises ``ValueError`` unless ``q`` has one value per
    :data:`QUANTILE_LEVELS` entry.
    """
    if len(q) != len(QUANTILE_LEVELS):
        raise ValueError(f"expected {len(QUANTILE_LEVELS)} quantiles, got {len(q)}")
    if value <= q[0]:
        return _flat_centre(q[0], q) if value == q[0] else 0.0
    if value >= q[-1]:
        return _flat_centre(q[-1], q) if value == q[-1] else 100.0
    for i in range(1, len(q)):
        if value < q[i]:
            low, high = q[i - 1], q[i]
            return QUANTILE_LEVELS[i - 1] + (value - low) / (high - low) * (
                QUANTILE_LEVELS[i] - QUANTILE_LEVELS[i - 1]
            )
        if value == q[i]:
            return _flat_centre(q[i], q)
    return 100.0


def node_ceiling(
    per_month: Mapping[int, Sequence[float]],
    *,
    quantile: float,
    months: Iterable[int],
    minimum: float,
    maximum: float,
) -> float | None:
    """The FWI that counts as "full" in one place, from its climatology.

    The mean, over ``months``, of the monthly quantile at level ``quantile``,
    kept between ``minimum`` and ``maximum``. ``per_month`` maps a month
    (1-12) to its 21 quantiles; months missing from it, or without all 21,
    are left out. ``None`` when none of ``months`` has a climatology.

    Raises ``ValueError`` when ``quantile`` is not one of
    :data:`QUANTILE_LEVELS`.
    """
    i = QUANTILE_LEVELS.index(quantile)
    values = [
        per_month[m][i]
        for m in months
        if m in per_month and len(per_month[m]) == len(QUANTILE_LEVELS)
    ]
    if not values:
        return None
    return min(max(sum(values) / len(values), minimum), maximum)


def accumulate_monthly(
    observations: Mapping[date, NoonObservation],
    days: Sequence[date],
    per_month: MutableMapping[int, list[float]],
    *,
    state: FwiState,
    days_walked: int,
    params: FwiParams,
    spinup_days: int,
) -> tuple[FwiState, int]:
    """Advance the chain over ``days`` and file each day's FWI under its month.

    Returns the new state and the new count of days walked, to pass back in
    for the next stretch (a year at a time, typically). The FWI values are
    **appended to** ``per_month[month]``, which the caller owns: a missing
    month is created.

    A day with no observation is skipped, not zeroed. The first
    ``spinup_days`` walked days move the chain but stay out of the
    distribution: the chain starts from the standard codes and the drought
    code takes weeks to forget them.
    """
    for day in days:
        observation = observations.get(day)
        if observation is None:
            continue
        outputs = advance(
            state,
            month=day.month,
            temperature_c=observation.temperature_c,
            relative_humidity_pct=observation.relative_humidity_pct,
            wind_speed_kmh=observation.wind_speed_kmh,
            rain_24h_mm=observation.rain_24h_mm,
            params=params,
        )
        state = outputs.state
        days_walked += 1
        if days_walked > spinup_days:
            per_month.setdefault(day.month, []).append(outputs.fwi)
    return state, days_walked


def coverage_is_valid(
    observed: Iterable[date],
    days: Sequence[date],
    *,
    max_gap_days: int,
    min_fraction: float = 0.95,
) -> bool:
    """Whether a stretch of days has enough observations to enter a climatology.

    ``days`` is the full stretch in order (a year, typically) and ``observed``
    the days in it that have an observation. Valid when at least
    ``min_fraction`` of the days are observed and no run of missing days,
    including at either end, is longer than ``max_gap_days``. A chain walked
    across a longer hole would treat its two sides as consecutive days.
    """
    seen = sorted(observed)
    if len(seen) < min_fraction * len(days):
        return False
    edges = [days[0] - timedelta(days=1), *seen, days[-1] + timedelta(days=1)]
    return all((b - a).days - 1 <= max_gap_days for a, b in pairwise(edges))
