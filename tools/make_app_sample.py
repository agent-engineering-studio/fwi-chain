"""Write the diary's sample: a summer of noon readings for an Italian place.

    uv run python tools/make_app_sample.py

Downloads hourly weather from the Open-Meteo historical weather API (ERA5
reanalysis, CC BY 4.0), takes the noon reading of each day with
:func:`fwi_chain.noon_readings`, and writes ``app/data/esempio_gioia_del_colle_2025.csv``.
Needs the network; CI never runs it. The file it writes is committed, so the
page needs no network.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from fwi_chain import HourlySample, noon_readings

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "data" / "esempio_gioia_del_colle_2025.csv"

PLACE = "Gioia del Colle (BA)"
LATITUDE, LONGITUDE = 40.80, 16.92
FIRST, LAST = date(2025, 5, 1), date(2025, 9, 30)
#: Solar noon at 17°E is about 10:52 UTC: the hour read is 11 UTC.
NOON_HOUR_UTC = 11

API = "https://archive-api.open-meteo.com/v1/archive"


def download() -> dict[str, list[object]]:
    query = urllib.parse.urlencode(
        {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            # The day before the first: its rain counts for the first noon.
            "start_date": (FIRST - timedelta(days=1)).isoformat(),
            "end_date": LAST.isoformat(),
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "timezone": "GMT",
            "models": "era5",
        }
    )
    with urllib.request.urlopen(f"{API}?{query}", timeout=60) as response:
        hourly: dict[str, list[object]] = json.load(response)["hourly"]
    return hourly


def number(value: float) -> str:
    return f"{value:.1f}".removesuffix(".0")


def main() -> None:
    h = download()
    samples = [
        HourlySample(
            time=datetime.fromisoformat(str(t)),
            temperature_c=h["temperature_2m"][i],  # type: ignore[arg-type]
            relative_humidity_pct=h["relative_humidity_2m"][i],  # type: ignore[arg-type]
            wind_speed_kmh=h["wind_speed_10m"][i],  # type: ignore[arg-type]
            rain_mm=h["precipitation"][i],  # type: ignore[arg-type]
        )
        for i, t in enumerate(h["time"])
    ]
    days = [FIRST + timedelta(days=i) for i in range((LAST - FIRST).days + 1)]
    readings = noon_readings(
        samples, days, noon_hour=NOON_HOUR_UTC, max_hours_from_noon=1, min_rain_hours=24
    )
    lines = [
        f"# ESEMPIO, non dati misurati: {PLACE}, dal 1 maggio al 30 settembre 2025"
        f" ({len(days)} giorni).",
        "# Fonte: Open-Meteo, Historical Weather API (https://open-meteo.com/), licenza CC BY 4.0;",
        "# rianalisi ERA5 di Copernicus (circa 25 km), punto più vicino a"
        f" {LATITUDE}N {LONGITUDE}E.",
        "# È meteo ricostruito da un modello, non una stazione: i temporali locali"
        " possono mancare.",
        f"# Letture alle {NOON_HOUR_UTC}:00 UTC (il mezzogiorno solare): temperatura (°C),"
        " umidità relativa (%),",
        "# vento a 10 m (km/h), pioggia nelle 24 ore prima (mm).",
        "# Rigenerato con tools/make_app_sample.py del repository fwi-chain.",
        "giorno,temperatura,umidita,vento,pioggia",
    ]
    for day in days:
        r = readings[day]
        if r.observation is None:
            lines.append(f"{day.isoformat()},,,,")  # not read: the page skips it
            continue
        o = r.observation
        lines.append(
            ",".join(
                (
                    day.isoformat(),
                    number(o.temperature_c),
                    number(o.relative_humidity_pct),
                    number(o.wind_speed_kmh),
                    number(o.rain_24h_mm),
                )
            )
        )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(days)} days")


if __name__ == "__main__":
    main()
