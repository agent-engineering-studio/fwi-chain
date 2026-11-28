"""Walking the chain over many days, and re-walking it when better rain arrives.

:func:`fwi_chain.advance` is one day. A service that keeps a chain alive has
to do three more things, and they are the same wherever the weather comes
from and wherever the state is stored:

* resume from the last stored day, across days with no observation, without
  welding the chain over a gap too long to mean anything
  (:func:`walk_chain`, :func:`days_to_walk`);
* compute a forecast day without ever storing it (:func:`writable_days`);
* redo the last days when a better rain measurement turns up, keeping the
  temperature, humidity and wind already used (:func:`rewalk_with_rain`,
  :func:`correct_rain`).

Everything here is a pure function of its arguments. Days are
:class:`datetime.date` values the caller supplies: nothing reads a clock, so
"today" is always an argument. Reading and writing the state, and fetching
the weather or the rain, stay with the caller.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from fwi_chain.chain import FwiOutputs, FwiParams, FwiState, advance

__all__ = [
    "ChainDay",
    "ChainPoint",
    "NoonObservation",
    "correct_rain",
    "days_to_walk",
    "rewalk_with_rain",
    "walk_chain",
    "writable_days",
]


@dataclass(frozen=True, slots=True)
class NoonObservation:
    """The four daily inputs of the chain, read at local noon."""

    temperature_c: float
    relative_humidity_pct: float
    wind_speed_kmh: float
    rain_24h_mm: float


@dataclass(frozen=True, slots=True)
class ChainPoint:
    """A chain as of one day: where a walk resumes from.

    ``chain_days`` counts the days the chain has actually been advanced since
    it last started from the standard codes. It is what tells a settled
    drought code from one still reporting its seed.
    """

    day: date
    state: FwiState
    chain_days: int


@dataclass(frozen=True, slots=True)
class ChainDay:
    """One walked day: the outputs, and the observation that produced them."""

    day: date
    outputs: FwiOutputs
    chain_days: int
    observation: NoonObservation

    @property
    def point(self) -> ChainPoint:
        """This day as the starting point of the next walk."""
        return ChainPoint(day=self.day, state=self.outputs.state, chain_days=self.chain_days)


def _step(
    state: FwiState, day: date, observation: NoonObservation, chain_days: int, params: FwiParams
) -> ChainDay:
    outputs = advance(
        state,
        month=day.month,
        temperature_c=observation.temperature_c,
        relative_humidity_pct=observation.relative_humidity_pct,
        wind_speed_kmh=observation.wind_speed_kmh,
        rain_24h_mm=observation.rain_24h_mm,
        params=params,
    )
    return ChainDay(day=day, outputs=outputs, chain_days=chain_days, observation=observation)


def walk_chain(
    observations: Mapping[date, NoonObservation],
    days: Sequence[date],
    *,
    start: ChainPoint | None,
    params: FwiParams,
    max_gap_days: int,
) -> list[ChainDay]:
    """Walk one chain over ``days``, from ``start`` or from the standard codes.

    ``start`` is the most recent stored point strictly before ``days[0]``, or
    ``None`` when there is none. A day with no observation is **skipped, not
    zeroed**: inventing a reading would inject a fake drying day that the
    recursion would carry for weeks.

    A ``start`` more than ``max_gap_days`` before ``days[0]`` is discarded and
    the walk restarts from ``params.initial_state`` with ``chain_days`` back
    at zero. Carrying a drought code across weeks of missing weather as if the
    days were consecutive produces a number with no history behind it.

    Days missing *inside* the window are not counted against ``max_gap_days``:
    only the distance from ``start`` is.
    """
    if not days:
        return []
    if start is not None and (days[0] - start.day).days > max_gap_days:
        start = None
    state = start.state if start is not None else params.initial_state
    chain_days = start.chain_days if start is not None else 0

    out: list[ChainDay] = []
    for day in days:
        observation = observations.get(day)
        if observation is None:
            continue
        chain_days += 1
        walked = _step(state, day, observation, chain_days, params)
        out.append(walked)
        state = walked.outputs.state
    return out


def days_to_walk(target: date, *, last_day: date | None, max_gap_days: int) -> list[date]:
    """The days to walk to bring a chain up to ``target``, earliest first.

    From the day after ``last_day`` (the last stored day before ``target``),
    so a jump two days ahead does not skip the drying in between, but never
    further back than ``max_gap_days`` before ``target``. With no stored day
    the answer is ``target`` alone. Empty when ``last_day`` is not before
    ``target``.
    """
    first = target
    if last_day is not None:
        first = max(last_day + timedelta(days=1), target - timedelta(days=max_gap_days))
    return [first + timedelta(days=i) for i in range((target - first).days + 1)]


def writable_days(walked: Iterable[ChainDay], *, today: date) -> list[ChainDay]:
    """The walked days that may be stored: ``today`` and before.

    A forecast day is worth computing and must never be written. A stored
    forecast would become tomorrow's predecessor, and the operational chain
    would end up recursing on a prediction.
    """
    return [d for d in walked if d.day <= today]


def rewalk_with_rain(
    rows: Sequence[ChainDay],
    start: ChainPoint,
    rain: Mapping[date, float | None],
    *,
    params: FwiParams,
    max_gap_days: int,
) -> list[ChainDay]:
    """Redo ``rows`` from ``start`` with the rain given, in millimetres.

    Each row keeps its temperature, humidity and wind. Its rain becomes
    ``rain[row.day]``; where that is missing or ``None`` the row's own rain
    stays, because a hole in the measurement is not a dry day.

    ``rows`` are in day order and all after ``start.day``. The walk stops at
    the first row more than ``max_gap_days`` after the one before it: the
    original chain restarted from the standard codes there, and welding it
    would invent its history. ``chain_days`` continues from ``start`` rather
    than being copied from the old rows.
    """
    out: list[ChainDay] = []
    state = start.state
    last = start.day
    chain_days = start.chain_days
    for row in rows:
        if (row.day - last).days > max_gap_days:
            break
        observed = rain.get(row.day)
        old = row.observation
        observation = NoonObservation(
            temperature_c=old.temperature_c,
            relative_humidity_pct=old.relative_humidity_pct,
            wind_speed_kmh=old.wind_speed_kmh,
            rain_24h_mm=old.rain_24h_mm if observed is None else observed,
        )
        chain_days += 1
        walked = _step(state, row.day, observation, chain_days, params)
        out.append(walked)
        state = walked.outputs.state
        last = row.day
    return out


def correct_rain(
    series: Sequence[ChainDay],
    *,
    since: date,
    rain: Mapping[date, float | None],
    params: FwiParams,
    max_gap_days: int,
    weather: Mapping[date, NoonObservation] | None = None,
) -> list[ChainDay]:
    """Redo one chain's stored days from ``since`` on, with the rain given.

    ``series`` is the stored chain in day order, reaching back before
    ``since``. The walk restarts from the last row before ``since``; a chain
    born later restarts from its own first row, which is left as it is. Every
    row after that one is redone with :func:`rewalk_with_rain` and returned,
    so the days that follow the corrected ones move with them.

    With ``weather``, a row whose day is in it takes that observation in
    place of its stored one before the rain is applied: analysed noon weather
    replacing the forecast the row was first written with.

    Idempotent: the same series corrected twice with the same rain gives the
    same rows.
    """
    if not series:
        return []
    earlier = [row for row in series if row.day < since]
    start = earlier[-1] if earlier else series[0]
    rows = [row for row in series if row.day > start.day]
    if weather is not None:
        rows = [
            row
            if (observation := weather.get(row.day)) is None
            else ChainDay(
                day=row.day,
                outputs=row.outputs,
                chain_days=row.chain_days,
                observation=observation,
            )
            for row in rows
        ]
    return rewalk_with_rain(rows, start.point, rain, params=params, max_gap_days=max_gap_days)
