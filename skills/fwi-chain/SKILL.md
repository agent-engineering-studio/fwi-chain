---
name: fwi-chain
description: Compute the Canadian Fire Weather Index (FFMC, DMC, DC, ISI, BUI, FWI; Van Wagner 1987) in Python with the fwi-chain library - one day from four noon readings, a chain walked over many days from a stored state, redone when better rain arrives, a climatology in 21 quantiles, the EFFIS danger classes, what moved the index from one day to the next, and a check that a text quotes the numbers right. Use when code or an answer needs a fire weather index, fire danger from weather, or mentions FWI, FFMC, DMC, DC, drought code, Van Wagner, cffdrs or fwi-chain.
---

# fwi-chain

`fwi-chain` answers one question: **how easily would a fire start and spread
in this weather?** It has no dependencies. It fetches no weather: the caller
brings one noon reading per day. It reads no clock: "today" is an argument.

Full documentation: https://agentengineering.it/fwi-chain/ ·
everything as plain text: https://agentengineering.it/fwi-chain/llms-full.txt

## The rule that goes with every answer

**A fire weather index is not an alert, and not a forecast of fires.** It
says how easily a fire would start and spread, not that one will. The official
fire danger for Europe is published by EFFIS
(https://forest-fire.emergency.copernicus.eu/); in Italy the fire danger
bulletin is issued by the Dipartimento della Protezione Civile and by the
regions. For danger to people, point to the official bulletin and to 112.
Never write "alert", "warning" or "a fire will start here" from an index alone.

## Setup

```bash
pip install fwi-chain            # the library, no dependencies
pip install "fwi-chain[mcp]"     # + the MCP server: fwi-chain-mcp
```

## Recipe

```python
from datetime import date

from fwi_chain import STANDARD_PARAMS, ChainPoint, NoonObservation, catch_up, effis_class

observations: dict[date, NoonObservation] = ...  # one per day; a missing day is simply absent
stored: ChainPoint | None = ...  # the last point you saved, or None
walked = catch_up(
    observations, date(2026, 7, 20), start=stored, params=STANDARD_PARAMS, max_gap_days=7
)
today = walked[-1]
print(today.outputs.fwi, effis_class(today.outputs.fwi), today.chain_days)
save(today.point)  # the state is yours to persist
```

One day alone is `advance(state, month=..., temperature_c=..., ...)`. A whole
window with a known start is `walk_chain`. Measured rain replacing a model's:
`correct_rain`. Where a value falls in its place and month: `quantiles`,
`percentile`.

For an answer in words: `fwi_chain.facts` (`day_facts`, `walk_facts`,
`distribution_facts`) gives the numbers as data, with what moved the index;
before you send the text, `fwi_chain.check.check_text(text, facts)`.

## The traps

- **The codes remember.** FFMC forgets in a day, DMC in about 12, DC in about
  52. A chain started from the standard codes (85 / 6 / 15) says nothing about
  the drought until it has walked for weeks. Persist the state; do not restart
  each day. `chain_days` counts the days walked since the last start.
- **Not measured is not dry.** A day with no reading is left out of
  `observations`, never given a rain of 0: an invented dry day is carried by
  the recursion for weeks.
- **A stored state too old is not a state.** Past `max_gap_days` restart from
  the standard codes. Use `catch_up`: calling `days_to_walk` and then
  `walk_chain` yourself keeps a state up to twice the limit.
- **Never store a forecast day.** Compute it, show it, and keep only
  `writable_days(walked, today=...)`: a stored forecast becomes tomorrow's
  predecessor.
- **Noon, and the rain of the 24 hours before it.** Local solar noon readings;
  `rain_24h_mm` is the total up to that hour, not the calendar day's. From
  hourly weather use `noon_readings(samples, days, noon_hour=...,
  max_hours_from_noon=2, min_rain_hours=20)`: it refuses a reading taken far
  from noon or with hours of rain missing, and says which. Never sum the hours
  that happen to be there: a missing hour is not a dry hour.
- **Units are in the names:** `temperature_c`, `relative_humidity_pct`,
  `wind_speed_kmh` (10 m wind, not m/s), `rain_24h_mm`. The six codes have no
  unit: never "an FWI of 30 %".
- **The class is a convention, the percentile a fact about a place.** An FWI of
  30 is an ordinary August day in Sicily and a rare one in the Alps.
  `effis_class` gives the first, `percentile` the second.
- **What moved the index** (`explain_change`) is arithmetic on the chain: the
  chain's memory, and the FWI points moved by each reading. It does not say
  why the weather changed. Do not add causes that are not in it.
- **Day-length tables are for 46°N.** Far from that latitude, or in the
  southern hemisphere, pass your own `FwiParams`.
- **Not cffdrs's digits.** The library follows Van Wagner (1987) as printed;
  cffdrs follows the 1985 FORTRAN program. Over cffdrs's 48-day test series
  they differ by at most 0.25 FWI points and agree on the class every day.
- **No overwintering, no snow.** The chain does not stop or restart with the
  season; that is the caller's choice.

Reference: Van Wagner, C.E. (1987), Development and structure of the Canadian
Forest Fire Weather Index System, Forestry Technical Report 35.
