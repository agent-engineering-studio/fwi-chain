"""Freeze what Limen's noon reading returns, for the parity test.

``fwi_chain.noon`` came from ``MeteoSnapshot.noon_observation`` in Limen
(integrations/openmeteo/dtos.py). This script calls Limen's, on fixed hourly
series, and writes inputs and Limen's answers to
``tests/fixtures/limen_noon_parity.json``. It imports Limen, not
``fwi_chain.noon``.

Run it from a Limen checkout's environment, only to regenerate the fixture::

    /path/to/limen/.venv/bin/python scripts/limen_noon_parity.py

A sample in the fixture is ``[time, temperature_c, relative_humidity_pct,
wind_speed_kmh, rain_mm]``; ``null`` is "not measured". Limen has no such
thing for rain: an hour without rain data is a sample with
``precipitation_mm`` left at its default of 0, or no sample at all. Both
happen here, on purpose: they are the cases where Limen guessed.
"""

from __future__ import annotations

import json
import random
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from limen.integrations.openmeteo import dtos
from limen.integrations.openmeteo.dtos import MeteoSnapshot, WeatherSample

OUT = Path(__file__).parent.parent / "tests" / "fixtures" / "limen_noon_parity.json"
FIRST = datetime(2026, 8, 30, tzinfo=UTC)
HOURS = 24 * 5
DAYS = [date(2026, 8, 30) + timedelta(days=i) for i in range(5)]

Row = list[object]


def series(seed: int) -> list[Row]:
    rng = random.Random(seed)
    rows: list[Row] = []
    for h in range(HOURS):
        rain = round(rng.uniform(0.1, 9.0), 1) if rng.random() < 0.2 else 0.0
        rows.append(
            [
                (FIRST + timedelta(hours=h)).isoformat(),
                round(rng.uniform(8.0, 36.0), 1),
                round(rng.uniform(15.0, 100.0), 1),
                round(rng.uniform(0.0, 40.0), 1),
                rain,
            ]
        )
    return rows


def hour(day: int, h: int) -> int:
    return day * 24 + h


def case(name: str, rows: list[Row], noon_hour: int, *, gaps: bool) -> dict[str, object]:
    samples = [
        WeatherSample(
            timestamp=datetime.fromisoformat(str(r[0])),
            temperature_c=r[1],
            relative_humidity_pct=r[2],
            wind_speed_kmh=r[3],
            **({} if r[4] is None else {"precipitation_mm": r[4]}),
        )
        for r in rows
    ]
    snapshot = MeteoSnapshot(
        centroid_lon=16.5,
        centroid_lat=40.1,
        window_start=FIRST,
        window_end=FIRST + timedelta(hours=HOURS),
        samples=samples,
    )
    expected: dict[str, object] = {}
    for day in DAYS:
        o = snapshot.noon_observation(day, noon_hour=noon_hour)
        expected[day.isoformat()] = (
            None
            if o is None
            else [o.temperature_c, o.relative_humidity_pct, o.wind_speed_kmh, o.rain_24h_mm]
        )
    return {
        "name": name,
        "gaps": gaps,
        "noon_hour": noon_hour,
        "samples": rows,
        "expected": expected,
    }


def cases() -> list[dict[str, object]]:
    out = [
        case("every hour measured, noon at 11", series(1), 11, gaps=False),
        case("every hour measured, noon at 12", series(2), 12, gaps=False),
        case("every hour measured, noon at 0", series(3), 0, gaps=False),
    ]

    # The noon hour of day 2 has no temperature; of day 3, hours 6 to 20 have
    # no wind; day 4 has no fire weather at all.
    rows = series(4)
    rows[hour(1, 11)][1] = None
    for h in range(6, 21):
        rows[hour(2, h)][3] = None
    for h in range(24):
        rows[hour(3, h)][2] = None
    out.append(case("noon hour missing: the nearest hour is read", rows, 11, gaps=True))

    # A tie: hours 10, 11 and 12 missing, so 9 and 13 are equally near.
    rows = series(5)
    for h in (10, 11, 12):
        rows[hour(1, h)][1] = None
    out.append(case("two hours equally near: the earlier one", rows, 11, gaps=True))

    # Rain not measured: null for six hours before the noon of day 2, and the
    # samples of the night before day 3 removed altogether.
    rows = series(6)
    for h in range(5, 11):
        rows[hour(1, h)][4] = None
    gone = {hour(1, h) for h in range(18, 24)} | {hour(2, h) for h in range(0, 4)}
    rows = [r for i, r in enumerate(rows) if i not in gone]
    out.append(case("hours of rain not measured", rows, 11, gaps=True))

    # Values outside their range: Limen clamps humidity and wind, and its
    # sample clamps rain.
    rows = series(7)
    rows[hour(1, 11)][2] = 104.0
    rows[hour(2, 11)][3] = -3.0
    rows[hour(3, 9)][4] = -5.0
    out.append(case("values outside their range are clamped", rows, 11, gaps=False))
    return out


def limen_commit() -> str:
    root = Path(dtos.__file__).parents[4]
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    fixture = {"limen_commit": limen_commit(), "cases": cases()}
    OUT.write_text(json.dumps(fixture, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT}: Limen {fixture['limen_commit']}")


if __name__ == "__main__":
    main()
