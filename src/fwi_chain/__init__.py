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
from fwi_chain.climatology import (
    QUANTILE_LEVELS,
    accumulate_monthly,
    coverage_is_valid,
    node_ceiling,
    percentile,
    quantiles,
)
from fwi_chain.walk import (
    ChainDay,
    ChainPoint,
    NoonObservation,
    correct_rain,
    days_to_walk,
    rewalk_with_rain,
    walk_chain,
    writable_days,
)

__version__ = version("fwi-chain")

__all__ = [
    "QUANTILE_LEVELS",
    "STANDARD_PARAMS",
    "ChainDay",
    "ChainPoint",
    "FwiOutputs",
    "FwiParams",
    "FwiState",
    "NoonObservation",
    "__version__",
    "accumulate_monthly",
    "advance",
    "buildup_index",
    "correct_rain",
    "coverage_is_valid",
    "days_to_walk",
    "drought_code",
    "duff_moisture_code",
    "fine_fuel_moisture_code",
    "fire_weather_index",
    "initial_spread_index",
    "node_ceiling",
    "percentile",
    "quantiles",
    "rewalk_with_rain",
    "walk_chain",
    "writable_days",
]
