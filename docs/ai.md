# Facts, what moved the index, and the MCP server

*New in 1.2.* The rule of everything on this page: **the numbers come from
the chain; a model may explain them, never invent them.**

!!! warning "A fire weather index is not an alert"
    It says how easily a fire would start and spread in the weather given, not
    that one will. The official fire danger for Europe is published by
    [EFFIS](https://forest-fire.emergency.copernicus.eu/); in Italy the fire
    danger bulletin is issued by the Dipartimento della Protezione Civile and
    by the regions.

## What moved the index

On 7 May 1985, in the test series of `cffdrs`, the FWI went from 21.7 to 52.6.
`explain_change` takes the two days apart:

```python
from fwi_chain import STANDARD_PARAMS, explain_change

e = explain_change(walked[i - 1], walked[i], params=STANDARD_PARAMS)
# FWI 21.7 -> 52.6  (+30.9)
#   the chain's memory    +1.2
#   wind                 +18.0   12 -> 27 km/h
#   humidity             +11.1   33 -> 17 %
#   temperature           +0.6   27 -> 28 °C
#   rain                  +0.0
```

Two parts. **The chain's memory** (`carry_over`): with the very same weather
as the day before, the index would still have moved, because fuel that is
drying keeps drying. **The weather** (`weather`): what the change in the four
readings did, split among them.

The readings act together (wind matters more on dry fuel), so the split is a
choice. The one used is the Shapley value: the effect of a reading is its
average effect over every order in which the four could have changed. It is
the split in which the four effects add up exactly, and it costs 16 runs of
the equations. Removing one reading at a time, the obvious alternative, was
tried first: on a constructed day with a storm after dry weather it left 14 of
21.6 points assigned to no reading.

What it is not: it says what moved the number, not why the weather changed,
and nothing about fires.

## The answers as facts

`fwi_chain.facts` gives the same answers as plain `dict`s, ready for JSON,
with the units in the key names (`_c`, `_pct`, `_kmh`, `_mm`, `_days`; the
six codes have no unit) and the rule in every answer.

| Function | What it gives |
|---|---|
| `day_facts(day, *, previous=None, params=None, month_quantiles=None, spinup_days=None)` | one walked day: readings, six codes, EFFIS class, `chain_days`; with `previous`, what moved the FWI; with `month_quantiles`, its percentile; with `spinup_days`, whether the chain is `settled` |
| `walk_facts(walked, *, params, quantiles_by_month=None, spinup_days=None)` | a stretch: every day, the peak, the rain, days per class, the last day in full |
| `distribution_facts(values, *, value=None)` | a list of FWI values as 21 quantiles, and where `value` falls |

Codes and effects are rounded to one decimal, as fire services publish them.
Rounded parts may not add up to the rounded total by 0.1.

## Checking a text

`fwi_chain.check.check_text(text, facts, *, question="")` returns the numbers
of a text that are not facts as written:

| Fault | Example, when the facts say 12.4 mm of rain and an FWI of 52.6 |
|---|---|
| `unit` | "12.4 %", "an FWI of 52.6 km/h" |
| `rounded` | "12.5 mm" |
| `invented` | "gusts of 77 km/h" |

```python
from fwi_chain.check import check_text

check_text("The wind rose to 27 % and added 18.5 points.", facts)
# [Misquote(text='27 %', unit='pct', fault='unit', nearest='observation.wind_speed_kmh = 27 kmh'),
#  Misquote(text='18.5', unit=None, fault='invented', nearest=None)]
```

Its limits, measured on the [faithfulness set](benchmark.md#the-faithfulness-set):
it knows a number is a fact of the right unit, not that it is said of the
right thing; and against the facts of a whole series a small invented integer
can pass by chance. Check a text against the facts of the day it is about.

## The MCP server

```bash
pip install "fwi-chain[mcp]"
fwi-chain-mcp                # standard input and output
fwi-chain-mcp --http         # streamable HTTP, http://127.0.0.1:8772/mcp
```

The package itself still needs nothing: `mcp` is an extra, and only
`fwi_chain.mcp_server` imports it. The tools compute only from what a call
gives them: no network, no weather of their own, no clock.

| Tool | What it answers |
|---|---|
| `walk` | the chain over the noon readings given: every day, the peak, the last day with what moved it |
| `explain` | one day of that stretch, taken apart; with past values of the month, its percentile |
| `percentile` | where an FWI falls among the values of its place and month |
| `check` | the numbers of a text that are not facts of a tool's answer |

A reading is `[day, temperature_c, relative_humidity_pct, wind_speed_kmh,
rain_24h_mm]`. A value `null` means the day was not measured: it is skipped,
never zeroed.

For a client such as Claude Desktop:

```json
{ "mcpServers": { "fwi-chain": { "command": "fwi-chain-mcp" } } }
```

## For agents that write code

The site serves [`llms.txt`](https://agentengineering.it/fwi-chain/llms.txt),
the whole documentation as one text
([`llms-full.txt`](https://agentengineering.it/fwi-chain/llms-full.txt)) and an
[agent skill](https://agentengineering.it/fwi-chain/skills/fwi-chain/SKILL.md)
with the recipe and the traps.
