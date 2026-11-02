"""Persist the state between runs: a daily job backed by SQLite.

The three moisture codes remember weeks of weather, so a job that runs once a
day must load yesterday's state, advance one day, and save the result. This
script does exactly that for one weather station; run it several times and
watch the chain pick up where it left off.

Run:  python examples/03_daily_job_sqlite.py [database.sqlite]
"""

import datetime as dt
import sqlite3
import sys

from weather import synthetic_season

from fwi_chain import STANDARD_PARAMS, FwiState, advance

DB = sys.argv[1] if len(sys.argv) > 1 else "fwi_state.sqlite"
STATION = "demo-station"

con = sqlite3.connect(DB)
con.execute(
    """CREATE TABLE IF NOT EXISTS fwi_state (
        station TEXT NOT NULL,
        day     TEXT NOT NULL,
        ffmc REAL, dmc REAL, dc REAL, isi REAL, bui REAL, fwi REAL,
        PRIMARY KEY (station, day)
    )"""
)

# 1. Load the most recent state, or start the season from the standard codes.
row = con.execute(
    "SELECT day, ffmc, dmc, dc FROM fwi_state WHERE station = ? ORDER BY day DESC LIMIT 1",
    (STATION,),
).fetchone()
if row is None:
    last_day = dt.date(2026, 3, 31)
    state = STANDARD_PARAMS.initial_state
    print("No state yet: starting the season from FFMC/DMC/DC = 85/6/15")
else:
    last_day = dt.date.fromisoformat(row[0])
    state = FwiState(ffmc=row[1], dmc=row[2], dc=row[3])
    print(
        f"Resuming from {last_day}: FFMC {state.ffmc:.1f}, DMC {state.dmc:.1f}, DC {state.dc:.1f}"
    )

# 2. Get "today's" reading. In production this is your weather feed.
today = last_day + dt.timedelta(days=1)
reading = next(r for r in synthetic_season() if r.day == today)

# 3. Advance one day and save. The primary key makes a re-run idempotent.
out = advance(
    state,
    month=today.month,
    temperature_c=reading.temperature_c,
    relative_humidity_pct=reading.relative_humidity_pct,
    wind_speed_kmh=reading.wind_speed_kmh,
    rain_24h_mm=reading.rain_24h_mm,
    params=STANDARD_PARAMS,
)
with con:
    con.execute(
        "INSERT OR REPLACE INTO fwi_state VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            STATION,
            today.isoformat(),
            out.state.ffmc,
            out.state.dmc,
            out.state.dc,
            out.isi,
            out.bui,
            out.fwi,
        ),
    )
print(f"{today}: FWI {out.fwi:.1f}  (state saved to {DB})")
