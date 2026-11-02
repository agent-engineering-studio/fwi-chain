"""A whole fire season, day by day, with danger classes and a CSV.

Run:  python examples/02_fire_season.py [output.csv]

Uses the synthetic season in ``weather.py``: replace it with your own
noon observations.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

from weather import synthetic_season

from fwi_chain import STANDARD_PARAMS, advance

# The fire danger classes EFFIS uses to colour its European FWI maps.
# Lower bound inclusive. Classes are regional conventions: calibrate your own
# for a different climate.
DANGER_CLASSES = [
    (50.0, "extreme"),
    (38.0, "very high"),
    (21.3, "high"),
    (11.2, "moderate"),
    (5.2, "low"),
    (0.0, "very low"),
]


def danger_class(fwi: float) -> str:
    return next(label for lower, label in DANGER_CLASSES if fwi >= lower)


state = STANDARD_PARAMS.initial_state
rows = []
for reading in synthetic_season():
    out = advance(
        state,
        month=reading.day.month,
        temperature_c=reading.temperature_c,
        relative_humidity_pct=reading.relative_humidity_pct,
        wind_speed_kmh=reading.wind_speed_kmh,
        rain_24h_mm=reading.rain_24h_mm,
        params=STANDARD_PARAMS,
    )
    state = out.state  # the recursion: today's output is tomorrow's input
    rows.append(
        {
            "date": reading.day.isoformat(),
            "temp_c": reading.temperature_c,
            "rh_pct": reading.relative_humidity_pct,
            "wind_kmh": reading.wind_speed_kmh,
            "rain_mm": reading.rain_24h_mm,
            "ffmc": round(out.state.ffmc, 2),
            "dmc": round(out.state.dmc, 2),
            "dc": round(out.state.dc, 2),
            "isi": round(out.isi, 2),
            "bui": round(out.bui, 2),
            "fwi": round(out.fwi, 2),
            "class": danger_class(out.fwi),
        }
    )

peak = max(rows, key=lambda r: r["fwi"])
print(f"{len(rows)} days, {rows[0]['date']} to {rows[-1]['date']}")
print(f"Peak FWI {peak['fwi']} on {peak['date']} (wind {peak['wind_kmh']} km/h)")
print("Days per danger class:")
counts = Counter(r["class"] for r in rows)
for _, label in reversed(DANGER_CLASSES):
    print(f"  {label:<10} {counts[label]:4d}  {'#' * (counts[label] // 2)}")

if len(sys.argv) > 1:
    with Path(sys.argv[1]).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {sys.argv[1]}")
