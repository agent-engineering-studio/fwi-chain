"""The chain's answers as data: what a tool, a report or a model can quote.

Every function returns a plain ``dict`` (JSON-ready) with the numbers, their
units in the key names (``_c``, ``_pct``, ``_kmh``, ``_mm``, ``_days``; the
six codes have no unit), and the rule that goes with every answer:

    A fire weather index is not an alert.

A language model may word these facts; it never computes them. The numbers
come from here, and :func:`fwi_chain.check.check_text` checks a text against
them. Codes and effects are rounded to one decimal, as fire services publish
them; the chain itself keeps every digit.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from fwi_chain.chain import FwiParams
from fwi_chain.climatology import percentile, quantiles
from fwi_chain.danger import EFFIS_FWI_CLASSES, effis_class
from fwi_chain.explain import INPUTS, explain_change
from fwi_chain.walk import ChainDay

__all__ = ["EFFIS_URL", "RULE", "day_facts", "distribution_facts", "walk_facts"]

#: Where the official fire danger of Europe is. Every answer carries it.
EFFIS_URL = "https://forest-fire.emergency.copernicus.eu/"

RULE = (
    "A fire weather index is not an alert and not a forecast of fires: it says how "
    "easily a fire would start and spread in the weather given, not that one will. "
    f"The official fire danger for Europe is published by EFFIS ({EFFIS_URL}); in Italy "
    "the fire danger bulletin is issued by the Dipartimento della Protezione Civile "
    "and by the regions."
)

#: The FWI each EFFIS class starts at, so a text may quote a boundary.
_CLASS_FROM = {name: lower for lower, name in EFFIS_FWI_CLASSES}


def _r(value: float) -> float:
    return round(value, 1)


def _codes(day: ChainDay) -> dict[str, float]:
    o = day.outputs
    return {
        "ffmc": _r(o.state.ffmc),
        "dmc": _r(o.state.dmc),
        "dc": _r(o.state.dc),
        "isi": _r(o.isi),
        "bui": _r(o.bui),
        "fwi": _r(o.fwi),
    }


def day_facts(
    day: ChainDay,
    *,
    previous: ChainDay | None = None,
    params: FwiParams | None = None,
    month_quantiles: Sequence[float] | None = None,
    spinup_days: int | None = None,
) -> dict[str, Any]:
    """One walked day: the readings, the six codes, the class, and what moved it.

    With ``previous`` (the walked day before) and ``params``, ``change`` says
    what moved the FWI: the chain's memory, and each of the four readings
    (:func:`fwi_chain.explain.explain_change`). With ``month_quantiles`` (the
    21 quantiles of this place and month), ``climatology`` says where the FWI
    falls among them. With ``spinup_days``, ``settled`` is false while the
    chain has walked fewer days than that and is still reporting its seed.
    """
    observation = day.observation
    facts: dict[str, Any] = {
        "day": day.day.isoformat(),
        "observation": {
            "temperature_c": observation.temperature_c,
            "relative_humidity_pct": observation.relative_humidity_pct,
            "wind_speed_kmh": observation.wind_speed_kmh,
            "rain_24h_mm": observation.rain_24h_mm,
        },
        "codes": _codes(day),
        "effis_class": effis_class(day.outputs.fwi),
        "effis_class_from": _CLASS_FROM,
        "chain_days": day.chain_days,
    }
    if spinup_days is not None:
        facts["settled"] = day.chain_days >= spinup_days
        facts["spinup_days"] = spinup_days
    if previous is not None:
        if params is None:
            raise ValueError("what moved the index needs the params the chain was walked with")
        e = explain_change(previous, day, params=params)
        facts["change"] = {
            "previous_day": previous.day.isoformat(),
            "fwi_previous": _r(e.fwi_yesterday),
            "fwi_change": _r(e.change),
            "carry_over": _r(e.carry_over),
            "weather": _r(e.weather),
            "drivers": [
                {
                    "input": d.input,
                    "previous_" + INPUTS[d.input].rsplit("_", 1)[-1]: d.yesterday,
                    "today_" + INPUTS[d.input].rsplit("_", 1)[-1]: d.today,
                    "effect": _r(d.effect),
                }
                for d in e.drivers
            ],
            "how": (
                "carry_over: the FWI with the previous day's weather again, minus the "
                "previous FWI. Each effect: FWI points moved by that reading alone "
                "(Shapley split of the weather's share; the four add up to `weather`)."
            ),
        }
    if month_quantiles is not None:
        facts["climatology"] = {
            "percentile": _r(percentile(day.outputs.fwi, month_quantiles)),
            "median_fwi": _r(month_quantiles[10]),
            "p90_fwi": _r(month_quantiles[18]),
            "quantile_levels": [50, 90],
            "month": day.day.month,
        }
    facts["rule"] = RULE
    return facts


def walk_facts(
    walked: Sequence[ChainDay],
    *,
    params: FwiParams,
    quantiles_by_month: Mapping[int, Sequence[float]] | None = None,
    spinup_days: int | None = None,
) -> dict[str, Any]:
    """A walked stretch of days: each day, the peak, the rain, and the last day in full.

    ``series`` has one row per walked day. ``last`` is :func:`day_facts` of
    the last day, with what moved it when there is a day before.

    Raises ``ValueError`` on an empty walk: no day was walked, and "no fire
    danger" would be a different statement.
    """
    if not walked:
        raise ValueError("no day was walked: the chain needs at least one observation")
    last = walked[-1]
    peak = max(walked, key=lambda d: d.outputs.fwi)
    by_class = Counter(effis_class(d.outputs.fwi) for d in walked)
    q = None if quantiles_by_month is None else quantiles_by_month.get(last.day.month)
    return {
        "first_day": walked[0].day.isoformat(),
        "last_day": last.day.isoformat(),
        "walked_days": len(walked),
        "rain_total_mm": _r(sum(d.observation.rain_24h_mm for d in walked)),
        "peak": {
            "day": peak.day.isoformat(),
            "fwi": _r(peak.outputs.fwi),
            "effis_class": effis_class(peak.outputs.fwi),
        },
        "class_days": {name: by_class[name] for _, name in EFFIS_FWI_CLASSES if by_class[name]},
        "series": [
            {
                "day": d.day.isoformat(),
                **_codes(d),
                "effis_class": effis_class(d.outputs.fwi),
                "rain_24h_mm": d.observation.rain_24h_mm,
            }
            for d in walked
        ],
        "last": day_facts(
            last,
            previous=walked[-2] if len(walked) > 1 else None,
            params=params,
            month_quantiles=q,
            spinup_days=spinup_days,
        ),
        "rule": RULE,
    }


def distribution_facts(values: Sequence[float], *, value: float | None = None) -> dict[str, Any]:
    """A list of FWI values as 21 quantiles, and where ``value`` falls among them."""
    q = quantiles(values)
    facts: dict[str, Any] = {
        "values": len(values),
        "quantiles": [_r(x) for x in q],
        "median_fwi": _r(q[10]),
        "p90_fwi": _r(q[18]),
        "quantile_levels": [50, 90, 100],
        "max_fwi": _r(q[20]),
    }
    if value is not None:
        facts["fwi"] = _r(value)
        facts["percentile"] = _r(percentile(value, q))
        facts["effis_class"] = effis_class(value)
    facts["rule"] = RULE
    return facts
