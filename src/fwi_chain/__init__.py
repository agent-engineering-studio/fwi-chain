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
from fwi_chain.danger import EFFIS_FWI_CLASSES, effis_class
from fwi_chain.explain import Driver, Explanation, explain_change
from fwi_chain.noon import HourlySample, NoonReading, noon_reading, noon_readings
from fwi_chain.walk import (
    ChainDay,
    ChainPoint,
    NoonObservation,
    catch_up,
    correct_rain,
    days_to_walk,
    rewalk_with_rain,
    start_is_stale,
    walk_chain,
    writable_days,
)

__version__ = version("fwi-chain")

__all__ = [
    "EFFIS_FWI_CLASSES",
    "QUANTILE_LEVELS",
    "STANDARD_PARAMS",
    "ChainDay",
    "ChainPoint",
    "Driver",
    "Explanation",
    "FwiOutputs",
    "FwiParams",
    "FwiState",
    "HourlySample",
    "NoonObservation",
    "NoonReading",
    "__version__",
    "accumulate_monthly",
    "advance",
    "buildup_index",
    "catch_up",
    "correct_rain",
    "coverage_is_valid",
    "days_to_walk",
    "drought_code",
    "duff_moisture_code",
    "effis_class",
    "explain_change",
    "fine_fuel_moisture_code",
    "fire_weather_index",
    "initial_spread_index",
    "node_ceiling",
    "noon_reading",
    "noon_readings",
    "percentile",
    "quantiles",
    "rewalk_with_rain",
    "start_is_stale",
    "walk_chain",
    "writable_days",
]
