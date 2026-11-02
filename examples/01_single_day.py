"""One day of the chain: the published reference day.

Run:  python examples/01_single_day.py
"""

from fwi_chain import STANDARD_PARAMS, advance

# Every chain starts somewhere. Van Wagner's spring start-up codes are
# FFMC 85, DMC 6, DC 15 -- "the snow just melted".
state = STANDARD_PARAMS.initial_state

# Today's noon reading: 17 °C, 42 % relative humidity, 25 km/h wind, no rain, April.
out = advance(
    state,
    month=4,
    temperature_c=17.0,
    relative_humidity_pct=42.0,
    wind_speed_kmh=25.0,
    rain_24h_mm=0.0,
    params=STANDARD_PARAMS,
)

print(f"FFMC {out.state.ffmc:6.2f}   fine fuel moisture (litter, needles)")
print(f"DMC  {out.state.dmc:6.2f}   duff moisture (the spongy layer below)")
print(f"DC   {out.state.dc:6.2f}   drought code (deep organic soil)")
print(f"ISI  {out.isi:6.2f}   initial spread index (how fast it would run)")
print(f"BUI  {out.bui:6.2f}   buildup index (how much fuel would burn)")
print(f"FWI  {out.fwi:6.2f}   fire weather index (how intense it would be)")

# The new state is what tomorrow starts from -- keep it.
tomorrow_starts_from = out.state
