"""Freeze what Limen's own functions return, for the parity tests.

The chain walk, the rain re-walk and the climatology were moved here from
Limen. ``tests/test_limen_parity.py`` checks that this library gives the same
numbers Limen's implementation gave on fixed inputs; this script is how
those numbers were produced. It imports **Limen**, not the new modules of
this library, and writes inputs and Limen's outputs to
``tests/fixtures/limen_parity.json``.

Run it from a Limen checkout's environment, only to regenerate the fixture::

    /path/to/limen/.venv/bin/python scripts/limen_parity.py

Limen's database calls are replaced with in-memory stubs; no network, no
database, no clock. The inputs come from ``random.Random`` with fixed seeds.

Two helpers have no callable counterpart in Limen: the days a sweep walks
and the "only the past is written" filter are expressions inside
``FwiUpdateExecutor.run``. They are copied here verbatim, marked
``transcribed`` in the fixture.
"""

from __future__ import annotations

import asyncio
import json
import random
import subprocess
from datetime import date, timedelta
from itertools import pairwise
from pathlib import Path

from limen.cli import fwi_backfill, fwi_climatology
from limen.core.scoring.regional_thresholds import TettoPerNodoBlock
from limen.core.scoring.wildfire import climatology
from limen.data.repos.fwi_state_repo import NodeDay, StoredChain
from limen.integrations.dpc import fwi_pioggia
from limen.integrations.openmeteo.dtos import FireWeatherObservation

from fwi_chain import STANDARD_PARAMS, FwiOutputs, FwiParams, FwiState

OUT = Path(__file__).parent.parent / "tests" / "fixtures" / "limen_parity.json"
NODE = (16.5, 40.1)

SOUTHERN = FwiParams(
    ffmc_start=80.0,
    dmc_start=10.0,
    dc_start=40.0,
    day_length_dmc=(12.4, 10.9, 9.4, 8.0, 7.0, 6.0, 6.5, 7.5, 9.0, 12.8, 13.9, 13.9),
    day_length_dc=(6.4, 5.0, 2.4, 0.4, -1.6, -1.6, -1.6, -1.6, -1.6, 0.9, 3.8, 5.8),
)
PARAMS = {"standard": STANDARD_PARAMS, "southern": SOUTHERN}


def span(first: date, n: int) -> list[date]:
    return [first + timedelta(days=i) for i in range(n)]


def weather(rng: random.Random) -> list[float]:
    """[temperature_c, relative_humidity_pct, wind_speed_kmh, rain_24h_mm]."""
    rain = round(rng.uniform(0.2, 40.0), 1) if rng.random() < 0.25 else 0.0
    return [
        round(rng.uniform(-3.0, 38.0), 1),
        round(rng.uniform(8.0, 100.0), 1),
        round(rng.uniform(0.0, 55.0), 1),
        rain,
    ]


def obs(day: date, w: list[float]) -> FireWeatherObservation:
    return FireWeatherObservation(
        day=day,
        temperature_c=w[0],
        relative_humidity_pct=w[1],
        wind_speed_kmh=w[2],
        rain_24h_mm=w[3],
    )


def row_json(r: NodeDay) -> dict[str, object]:
    return {
        "day": r.day.isoformat(),
        "ffmc": r.outputs.state.ffmc,
        "dmc": r.outputs.state.dmc,
        "dc": r.outputs.state.dc,
        "isi": r.outputs.isi,
        "bui": r.outputs.bui,
        "fwi": r.outputs.fwi,
        "chain_days": r.chain_days,
        "observation": [
            r.temperature_c,
            r.relative_humidity_pct,
            r.wind_speed_kmh,
            r.rain_24h_mm,
        ],
    }


# --------------------------------------------------------------------------
# advance_node
# --------------------------------------------------------------------------
def walk_case(
    name: str,
    *,
    seed: int,
    params: str,
    first: date,
    n: int,
    missing: set[int],
    start: tuple[int, int] | None,
    max_gap_days: int,
) -> dict[str, object]:
    """``start`` is (days before ``first``, chain_days) of the stored point."""
    rng = random.Random(seed)
    days = span(first, n)
    by_day = {d: weather(rng) for i, d in enumerate(days) if i not in missing}
    stored = None
    if start is not None:
        stored = StoredChain(
            day=first - timedelta(days=start[0]),
            state=FwiState(
                ffmc=round(rng.uniform(40, 95), 3),
                dmc=round(rng.uniform(5, 120), 3),
                dc=round(rng.uniform(20, 600), 3),
            ),
            chain_days=start[1],
        )

    async def latest_before(lon: float, lat: float, day: date) -> StoredChain | None:
        assert day == days[0]
        return stored

    fwi_backfill.fwi_state_repo.latest_before = latest_before  # type: ignore[assignment]
    rows = asyncio.run(
        fwi_backfill.advance_node(
            lon=NODE[0],
            lat=NODE[1],
            observations={d: obs(d, w) for d, w in by_day.items()},
            days=days,
            params=PARAMS[params],
            max_gap_days=max_gap_days,
        )
    )
    return {
        "name": name,
        "params": params,
        "max_gap_days": max_gap_days,
        "days": [d.isoformat() for d in days],
        "observations": {d.isoformat(): w for d, w in by_day.items()},
        "start": None
        if stored is None
        else {
            "day": stored.day.isoformat(),
            "ffmc": stored.state.ffmc,
            "dmc": stored.state.dmc,
            "dc": stored.state.dc,
            "chain_days": stored.chain_days,
        },
        "expected": [row_json(r) for r in rows],
    }


def walk_cases() -> list[dict[str, object]]:
    return [
        walk_case(
            "cold start, no gaps",
            seed=1,
            params="standard",
            first=date(2026, 6, 20),
            n=45,
            missing=set(),
            start=None,
            max_gap_days=7,
        ),
        walk_case(
            "cold start, days missing inside the window",
            seed=2,
            params="standard",
            first=date(2026, 8, 25),
            n=40,
            missing={0, 5, 6, 7, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 39},
            start=None,
            max_gap_days=7,
        ),
        walk_case(
            "resumes from the day before",
            seed=3,
            params="standard",
            first=date(2026, 12, 20),
            n=30,
            missing={3, 11},
            start=(1, 112),
            max_gap_days=7,
        ),
        walk_case(
            "resumes at exactly the longest gap allowed",
            seed=4,
            params="southern",
            first=date(2026, 1, 28),
            n=20,
            missing={1},
            start=(7, 40),
            max_gap_days=7,
        ),
        walk_case(
            "stored point one day too old is discarded",
            seed=5,
            params="southern",
            first=date(2026, 3, 1),
            n=20,
            missing={0, 9},
            start=(8, 40),
            max_gap_days=7,
        ),
        walk_case(
            "no observation at all",
            seed=6,
            params="standard",
            first=date(2026, 7, 1),
            n=5,
            missing={0, 1, 2, 3, 4},
            start=(1, 9),
            max_gap_days=7,
        ),
    ]


# --------------------------------------------------------------------------
# FwiUpdateExecutor.run: the days it walks, the rows it writes (transcribed)
# --------------------------------------------------------------------------
def days_to_walk_cases() -> list[dict[str, object]]:
    target = date(2026, 3, 2)
    out: list[dict[str, object]] = []
    for max_gap_days in (0, 3, 7):
        for back in (None, -2, 0, 1, 2, 3, 4, 7, 8, 30):
            stored_day = None if back is None else target - timedelta(days=back)
            # --- fwi_update.py, FwiUpdateExecutor.run, verbatim -------------
            first = target
            if stored_day is not None:
                first = max(
                    stored_day + timedelta(days=1),
                    target - timedelta(days=max_gap_days),
                )
            days = [first + timedelta(days=i) for i in range((target - first).days + 1)]
            # ----------------------------------------------------------------
            out.append(
                {
                    "target": target.isoformat(),
                    "last_day": None if stored_day is None else stored_day.isoformat(),
                    "max_gap_days": max_gap_days,
                    "expected": [d.isoformat() for d in days],
                }
            )
    return out


def writable_cases(walk: dict[str, object]) -> list[dict[str, object]]:
    walked = [date.fromisoformat(r["day"]) for r in walk["expected"]]  # type: ignore[attr-defined]
    out: list[dict[str, object]] = []
    for today in (walked[0] - timedelta(days=1), walked[0], walked[7], walked[-1]):
        # --- fwi_update.py: rows.extend(r for r in walked if r.day <= today)
        kept = [d for d in walked if d <= today]
        out.append(
            {
                "walk": walk["name"],
                "today": today.isoformat(),
                "expected": [d.isoformat() for d in kept],
            }
        )
    return out


# --------------------------------------------------------------------------
# ricalcola / correggi
# --------------------------------------------------------------------------
def stored_series(seed: int, first: date, n: int, missing: set[int]) -> list[NodeDay]:
    """A chain as it sits in storage: walked by Limen from the standard codes."""

    async def latest_before(lon: float, lat: float, day: date) -> None:
        return None

    rng = random.Random(seed)
    days = span(first, n)
    fwi_backfill.fwi_state_repo.latest_before = latest_before  # type: ignore[assignment]
    return asyncio.run(
        fwi_backfill.advance_node(
            lon=NODE[0],
            lat=NODE[1],
            observations={d: obs(d, weather(rng)) for i, d in enumerate(days) if i not in missing},
            days=days,
            params=STANDARD_PARAMS,
            max_gap_days=7,
        )
    )


def rain_for(rng: random.Random, days: list[date]) -> dict[date, float | None]:
    """Measured rain: a value, an explicit hole (None), or no entry at all."""
    out: dict[date, float | None] = {}
    for d in days:
        x = rng.random()
        if x < 0.5:
            out[d] = round(rng.uniform(0.0, 30.0), 1) if rng.random() < 0.6 else 0.0
        elif x < 0.75:
            out[d] = None
    return out


def rain_json(rain: dict[date, float | None]) -> dict[str, float | None]:
    return {d.isoformat(): v for d, v in rain.items()}


def rewalk_cases() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for name, seed, missing, max_gap_days, params in (
        ("no gaps", 11, set(), 7, "standard"),
        ("short gaps are walked across", 12, {9, 10, 11, 20}, 7, "standard"),
        ("stops at a gap longer than allowed", 13, set(range(15, 24)), 7, "standard"),
        ("gap of exactly the limit is walked across", 14, set(range(15, 21)), 7, "southern"),
    ):
        series = stored_series(seed, date(2026, 9, 10), 35, missing)
        prima, righe = series[4], series[5:]
        rain = rain_for(random.Random(seed + 100), [r.day for r in righe])
        nuove = fwi_pioggia.ricalcola(righe, prima, rain, PARAMS[params], max_gap_days)
        out.append(
            {
                "name": name,
                "params": params,
                "max_gap_days": max_gap_days,
                "start": row_json(prima),
                "rows": [row_json(r) for r in righe],
                "rain": rain_json(rain),
                "expected": [row_json(r) for r in nuove],
            }
        )
    return out


def correct_case(
    name: str,
    *,
    seed: int,
    series: list[NodeDay],
    dal: date,
    al: date,
    with_weather: bool,
    max_gap_days: int = 7,
) -> dict[str, object]:
    rng = random.Random(seed)
    giorni = span(dal, (al - dal).days + 1)
    rain = rain_for(rng, giorni)
    analysed = {g: weather(rng) for g in giorni if g < al and rng.random() < 0.8}
    written: list[NodeDay] = []

    async def read_between(a: date, b: date) -> dict[tuple[float, float], list[NodeDay]]:
        assert a == dal - timedelta(days=max_gap_days) and b == al
        return {NODE: [r for r in series if a <= r.day <= b]}

    async def upsert_many(rows: list[NodeDay]) -> int:
        written.extend(rows)
        return len(rows)

    async def fonte(nodi: list[tuple[float, float]], giorno: date) -> list[float | None]:
        return [rain.get(giorno) for _ in nodi]

    async def meteo(
        nodi: list[tuple[float, float]], giorni_: list[date]
    ) -> list[dict[date, FireWeatherObservation]]:
        return [{g: obs(g, analysed[g]) for g in giorni_ if g in analysed} for _ in nodi]

    fwi_pioggia.fwi_state_repo.read_between = read_between  # type: ignore[assignment]
    fwi_pioggia.fwi_state_repo.upsert_many = upsert_many  # type: ignore[assignment]
    asyncio.run(
        fwi_pioggia.correggi(
            dal=dal,
            al=al,
            params=STANDARD_PARAMS,
            max_gap_days=max_gap_days,
            fonte=fonte,
            meteo=meteo if with_weather else None,
        )
    )
    first = dal - timedelta(days=max_gap_days)
    return {
        "name": name,
        "params": "standard",
        "max_gap_days": max_gap_days,
        "since": dal.isoformat(),
        "series": [row_json(r) for r in series if first <= r.day <= al],
        "rain": rain_json(rain),
        "weather": {g.isoformat(): w for g, w in analysed.items()} if with_weather else None,
        "expected": [row_json(r) for r in written],
    }


def correct_cases() -> list[dict[str, object]]:
    full = stored_series(21, date(2026, 9, 1), 50, {30})
    gappy = stored_series(22, date(2026, 9, 1), 50, set(range(32, 42)))
    young = stored_series(23, date(2026, 10, 9), 12, set())
    return [
        correct_case(
            "rain only",
            seed=31,
            series=full,
            dal=date(2026, 10, 14),
            al=date(2026, 10, 20),
            with_weather=False,
        ),
        correct_case(
            "rain and analysed weather",
            seed=32,
            series=full,
            dal=date(2026, 10, 14),
            al=date(2026, 10, 20),
            with_weather=True,
        ),
        correct_case(
            "chain born after the first day restarts from its first row",
            seed=33,
            series=young,
            dal=date(2026, 10, 5),
            al=date(2026, 10, 20),
            with_weather=True,
        ),
        correct_case(
            "stops where the stored chain had a long gap",
            seed=34,
            series=gappy,
            dal=date(2026, 9, 28),
            al=date(2026, 10, 20),
            with_weather=False,
        ),
    ]


# --------------------------------------------------------------------------
# climatology
# --------------------------------------------------------------------------
def quantile_inputs() -> dict[str, list[float]]:
    rng = random.Random(41)
    return {
        "one value": [12.5],
        "two values": [3.0, 9.0],
        "twenty values": [round(rng.uniform(0, 60), 2) for _ in range(20)],
        "twenty-one values": [round(rng.uniform(0, 60), 2) for _ in range(21)],
        "a winter month, mostly zero": [0.0] * 200
        + [round(rng.uniform(0, 4), 2) for _ in range(110)],
        "a summer month": [round(rng.gauss(28, 11), 3) for _ in range(310)],
        "all equal": [7.0] * 31,
        "plateau in the middle": [1.0] * 10 + [5.0] * 40 + [9.0] * 10,
    }


def climatology_cases() -> dict[str, object]:
    inputs = quantile_inputs()
    q = {name: climatology.quantili(values) for name, values in inputs.items()}

    percentiles: list[dict[str, object]] = []
    for name, levels in q.items():
        probes = sorted(
            {-1.0, 0.0, 0.5, 1.0, 5.0, 7.0, 9.0, 12.5, 100.0}
            | set(levels)
            | {(a + b) / 2 for a, b in pairwise(levels)}
            | {a + (b - a) * 0.3 for a, b in pairwise(levels)}
        )
        for value in probes:
            percentiles.append(
                {
                    "quantiles": name,
                    "value": value,
                    "expected": climatology.percentile(value, levels),
                }
            )

    per_month = {
        6: q["twenty values"],
        7: q["a summer month"],
        8: q["twenty-one values"],
        1: q["a winter month, mostly zero"],
        9: q["plateau in the middle"][:20],  # not all 21: left out
    }
    ceilings: list[dict[str, object]] = []
    for quantile, months, minimum, maximum in (
        (90.0, (6, 7, 8), 15.0, 50.0),
        (95.0, (7, 8), 15.0, 50.0),
        (100.0, (7,), 15.0, 50.0),
        (50.0, (1,), 15.0, 50.0),
        (90.0, (6, 7, 8, 9), 15.0, 50.0),
        (90.0, (7, 9, 11), 15.0, 50.0),
        (90.0, (9,), 15.0, 50.0),
        (90.0, (2, 3), 15.0, 50.0),
        (5.0, (6, 7, 8), 1.0, 20.0),
        (0.0, (1, 6), 0.5, 50.0),
    ):
        blocco = TettoPerNodoBlock(quantile=quantile, mesi=months, minimo=minimum)
        ceilings.append(
            {
                "quantile": quantile,
                "months": list(months),
                "minimum": minimum,
                "maximum": maximum,
                "expected": climatology.tetto_del_nodo(per_month, blocco, maximum),
            }
        )

    return {
        "levels": list(climatology.LIVELLI),
        "quantiles": [
            {"name": name, "values": values, "expected": q[name]} for name, values in inputs.items()
        ],
        "percentiles": percentiles,
        "ceiling_per_month": {str(m): v for m, v in per_month.items()},
        "ceilings": ceilings,
    }


def accumulate_cases() -> list[dict[str, object]]:
    """Two stretches walked back to back, as ``_lotto`` does year after year."""
    out: list[dict[str, object]] = []
    for name, seed, params, missing in (
        ("no gaps", 51, "standard", set()),
        ("days missing", 52, "southern", {0, 1, 40, 41, 42, 59, 60, 61, 150, 151, 299}),
    ):
        rng = random.Random(seed)
        stretches = [span(date(2025, 11, 1), 61), span(date(2026, 1, 1), 365)]
        every = [d for s in stretches for d in s]
        by_day = {d: weather(rng) for i, d in enumerate(every) if i not in missing}
        observations = {d: obs(d, w) for d, w in by_day.items()}
        per_mese: dict[int, list[float]] = {}
        stato, avviati = PARAMS[params].initial_state, 0
        steps: list[dict[str, object]] = []
        for giorni in stretches:
            stato, avviati = fwi_climatology.accumula(
                observations, giorni, PARAMS[params], stato, avviati, _Months(per_mese)
            )
            steps.append(
                {
                    "days": [d.isoformat() for d in giorni],
                    "state": [stato.ffmc, stato.dmc, stato.dc],
                    "days_walked": avviati,
                }
            )
        out.append(
            {
                "name": name,
                "params": params,
                "spinup_days": fwi_climatology._AVVIAMENTO,
                "observations": {d.isoformat(): w for d, w in by_day.items()},
                "steps": steps,
                "per_month": {str(m): v for m, v in sorted(per_mese.items())},
            }
        )
    return out


class _Months(dict[int, list[float]]):
    """What ``_lotto`` hands ``accumula``: a defaultdict(list), writing through."""

    def __init__(self, target: dict[int, list[float]]) -> None:
        super().__init__()
        self._target = target

    def __getitem__(self, month: int) -> list[float]:
        return self._target.setdefault(month, [])


def coverage_cases() -> list[dict[str, object]]:
    year = span(date(2026, 1, 1), 365)
    out: list[dict[str, object]] = []
    for name, missing, max_buco in (
        ("complete", set(), 7),
        ("exactly 95 percent, spread out", set(range(0, 360, 20)), 7),
        ("one day short of 95 percent", set(range(0, 380, 20)), 7),
        ("one hole of the longest gap allowed", set(range(100, 107)), 7),
        ("one hole a day too long", set(range(100, 108)), 7),
        ("hole at the start, allowed", set(range(0, 7)), 7),
        ("hole at the start, too long", set(range(0, 8)), 7),
        ("hole at the end, too long", set(range(357, 365)), 7),
        ("nothing observed", set(range(365)), 7),
        ("no gap allowed, one day missing", {200}, 0),
    ):
        observed = [d for i, d in enumerate(year) if i not in missing]
        out.append(
            {
                "name": name,
                "days": [year[0].isoformat(), year[-1].isoformat()],
                "missing": sorted(missing),
                "max_gap_days": max_buco,
                "expected": fwi_climatology.copertura_valida(observed, year, max_buco),
            }
        )
    return out


def limen_commit() -> str:
    root = Path(fwi_backfill.__file__).parents[3]
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    assert isinstance(STANDARD_PARAMS.initial_state, FwiState) and FwiOutputs
    walks = walk_cases()
    fixture = {
        "limen_commit": limen_commit(),
        "params": {
            name: {
                "ffmc_start": p.ffmc_start,
                "dmc_start": p.dmc_start,
                "dc_start": p.dc_start,
                "day_length_dmc": list(p.day_length_dmc),
                "day_length_dc": list(p.day_length_dc),
            }
            for name, p in PARAMS.items()
        },
        "walk": walks,
        "days_to_walk_transcribed": days_to_walk_cases(),
        "writable_transcribed": writable_cases(walks[0]),
        "rewalk": rewalk_cases(),
        "correct": correct_cases(),
        "climatology": climatology_cases(),
        "accumulate": accumulate_cases(),
        "coverage": coverage_cases(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fixture, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: Limen {fixture['limen_commit']}")


if __name__ == "__main__":
    main()
