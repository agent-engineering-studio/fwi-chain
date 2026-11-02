"""Many locations at once: one state per station (or grid cell).

This is how the chain runs in production for a whole country: a mapping from
location to ``FwiState``, advanced once a day. Each location is independent,
so the loop parallelises trivially (processes, a task queue, a SQL job...).

Run:  python examples/04_many_stations.py
"""

from weather import synthetic_season

from fwi_chain import STANDARD_PARAMS, FwiState, advance

# Three toy "stations": the same synthetic climate with a different seed,
# i.e. different weather on each day.
stations = {"north-valley": 11, "coastal-plain": 7, "inland-hills": 3}
weather = {name: list(synthetic_season(seed=seed)) for name, seed in stations.items()}
states: dict[str, FwiState] = dict.fromkeys(stations, STANDARD_PARAMS.initial_state)

n_days = len(next(iter(weather.values())))
for i in range(n_days):
    fwi_today = {}
    for name in stations:
        r = weather[name][i]
        out = advance(
            states[name],
            month=r.day.month,
            temperature_c=r.temperature_c,
            relative_humidity_pct=r.relative_humidity_pct,
            wind_speed_kmh=r.wind_speed_kmh,
            rain_24h_mm=r.rain_24h_mm,
            params=STANDARD_PARAMS,
        )
        states[name] = out.state
        fwi_today[name] = out.fwi
    day = weather["north-valley"][i].day
    if day.day == 1:  # print the first of each month
        cells = "  ".join(f"{name} {fwi:5.1f}" for name, fwi in fwi_today.items())
        print(f"{day}  {cells}")
