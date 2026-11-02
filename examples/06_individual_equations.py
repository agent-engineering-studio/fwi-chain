"""Use the equations one by one: what-if questions and sensitivity.

``advance`` chains six functions; each is exported on its own. Here they
answer two questions a fire analyst asks every summer day.

Run:  python examples/06_individual_equations.py
"""

from fwi_chain import buildup_index, fire_weather_index, initial_spread_index

# 1. "Fuels are dry (FFMC 92). How much does the wind matter?"
print("Wind  ISI    FWI (with BUI 80)")
for wind in (0, 10, 20, 30, 40, 50, 60):
    isi = initial_spread_index(92.0, wind_speed_kmh=wind)
    print(f"{wind:4d}  {isi:5.1f}  {fire_weather_index(isi, 80.0):5.1f}")

# 2. "Same wind, but how much does a long drought add?"
print("\nDC    BUI    FWI (with DMC 40, ISI 12)")
for dc in (100, 200, 300, 400, 500, 600, 700):
    bui = buildup_index(40.0, dc)
    print(f"{dc:4d}  {bui:5.1f}  {fire_weather_index(12.0, bui):5.1f}")
