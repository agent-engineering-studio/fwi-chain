"""Custom parameters: running the chain in the southern hemisphere.

``STANDARD_PARAMS`` carries Van Wagner's day-length factors for 46°N,
January first. South of the equator the seasons are flipped, so the common
approximation is to shift both tables by six months. For latitudes far from
46° (north or south), use tables adjusted for your band, such as the ones
the ``cffdrs`` R package ships.

Run:  python examples/05_southern_hemisphere.py
"""

from fwi_chain import STANDARD_PARAMS, FwiParams, advance


def shift_six_months(table: tuple[float, ...]) -> tuple[float, ...]:
    return table[6:] + table[:6]


SOUTHERN = FwiParams(
    ffmc_start=85.0,
    dmc_start=6.0,
    dc_start=15.0,
    day_length_dmc=shift_six_months(STANDARD_PARAMS.day_length_dmc),
    day_length_dc=shift_six_months(STANDARD_PARAMS.day_length_dc),
)

# The same hot January afternoon, north and south of the equator.
for label, params in (("46°N tables", STANDARD_PARAMS), ("shifted (south)", SOUTHERN)):
    out = advance(
        params.initial_state,
        month=1,
        temperature_c=30.0,
        relative_humidity_pct=30.0,
        wind_speed_kmh=20.0,
        rain_24h_mm=0.0,
        params=params,
    )
    print(f"{label:<16} DMC {out.state.dmc:5.2f}  DC {out.state.dc:5.2f}  FWI {out.fwi:5.2f}")

# A table with the wrong number of months is refused up front.
try:
    FwiParams(85.0, 6.0, 15.0, day_length_dmc=(1.0,) * 11, day_length_dc=(0.0,) * 12)
except ValueError as e:
    print(f"Refused: {e}")
