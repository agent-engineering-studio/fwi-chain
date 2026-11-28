"""What moved the index from one day to the next.

The FWI of today differs from yesterday's for two reasons. The chain has a
memory: with the very same weather the codes would still have moved, because
fuel that is drying keeps drying. And the weather changed. This module
separates the two, and splits the second among the four readings.

The readings act together (wind matters more on dry fuel), so "the effect of
the rain" depends on what else is taken to have changed. The split used here
is the Shapley value: the effect of a reading is its average effect over
every order in which the four could have changed from yesterday's values to
today's. It is the one split in which the four effects add up exactly to the
weather's share, and none depends on the order the readings are listed in.

It is arithmetic on the chain: the same equations, run 16 times. It says what
moved the number, not why the weather changed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
from math import factorial
from typing import Literal

from fwi_chain.chain import FwiParams, advance
from fwi_chain.walk import ChainDay

__all__ = ["INPUTS", "Driver", "Explanation", "explain_change"]

Input = Literal["temperature", "humidity", "wind", "rain"]

INPUTS: dict[Input, str] = {
    "temperature": "temperature_c",
    "humidity": "relative_humidity_pct",
    "wind": "wind_speed_kmh",
    "rain": "rain_24h_mm",
}
"""The four readings, and the field of ``NoonObservation`` each one is."""


@dataclass(frozen=True, slots=True)
class Driver:
    """One reading, and what its change did to today's FWI."""

    input: Input
    yesterday: float
    today: float
    #: FWI points: positive, the change in this reading raised the index.
    effect: float


@dataclass(frozen=True, slots=True)
class Explanation:
    """Today's FWI against yesterday's, taken apart.

    ``change == carry_over + weather`` and
    ``weather == sum(d.effect for d in drivers)``, to floating-point rounding.
    """

    fwi_yesterday: float
    fwi_today: float
    change: float
    #: What the chain's memory alone did: today with yesterday's weather again.
    carry_over: float
    #: What the change in the weather did, all four readings together.
    weather: float
    #: The four readings, the largest effect first.
    drivers: tuple[Driver, ...]


def explain_change(previous: ChainDay, today: ChainDay, *, params: FwiParams) -> Explanation:
    """What moved the FWI from ``previous`` to ``today``.

    ``previous`` and ``today`` are two walked days, ``today`` computed from
    the state ``previous`` left (consecutive rows of ``walk_chain``).
    ``params`` are the ones the chain was walked with.
    """
    names = tuple(INPUTS)

    def fwi_with(changed: frozenset[Input]) -> float:
        """Today's FWI with only the readings in ``changed`` at today's values."""
        swaps = {INPUTS[n]: getattr(today.observation, INPUTS[n]) for n in changed}
        observation = replace(previous.observation, **swaps)
        return advance(
            previous.outputs.state,
            month=today.day.month,
            temperature_c=observation.temperature_c,
            relative_humidity_pct=observation.relative_humidity_pct,
            wind_speed_kmh=observation.wind_speed_kmh,
            rain_24h_mm=observation.rain_24h_mm,
            params=params,
        ).fwi

    value = {
        frozenset(subset): fwi_with(frozenset(subset))
        for size in range(len(names) + 1)
        for subset in combinations(names, size)
    }
    n = len(names)
    drivers = []
    for name in names:
        others = [x for x in names if x != name]
        effect = 0.0
        for size in range(n):
            weight = factorial(size) * factorial(n - size - 1) / factorial(n)
            for subset in combinations(others, size):
                before = frozenset(subset)
                effect += weight * (value[before | {name}] - value[before])
        drivers.append(
            Driver(
                input=name,
                yesterday=getattr(previous.observation, INPUTS[name]),
                today=getattr(today.observation, INPUTS[name]),
                effect=effect,
            )
        )
    drivers.sort(key=lambda d: -abs(d.effect))
    same_weather = value[frozenset()]
    fwi_today = today.outputs.fwi
    fwi_yesterday = previous.outputs.fwi
    return Explanation(
        fwi_yesterday=fwi_yesterday,
        fwi_today=fwi_today,
        change=fwi_today - fwi_yesterday,
        carry_over=same_weather - fwi_yesterday,
        weather=fwi_today - same_weather,
        drivers=tuple(drivers),
    )
