"""Canadian Fire Weather Index chain (Van Wagner 1987)."""

from importlib.metadata import version

from fwi_chain.chain import (
    STANDARD_PARAMS,
    FwiOutputs,
    FwiParams,
    FwiState,
    advance,
    buildup_index,
    drought_code,
    duff_moisture_code,
    fine_fuel_moisture_code,
    fire_weather_index,
    initial_spread_index,
)

__version__ = version("fwi-chain")

__all__ = [
    "STANDARD_PARAMS",
    "FwiOutputs",
    "FwiParams",
    "FwiState",
    "__version__",
    "advance",
    "buildup_index",
    "drought_code",
    "duff_moisture_code",
    "fine_fuel_moisture_code",
    "fire_weather_index",
    "initial_spread_index",
]
