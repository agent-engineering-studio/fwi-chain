"""The fire danger class of an FWI, as EFFIS maps it.

The European Forest Fire Information System colours its fire danger maps in
six classes, the same for every country. The boundaries are the ones EFFIS
publishes in its technical background, "Fire danger forecast"
(https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/fire-danger-forecast,
read on 2026-11-28); "very extreme" was added in June 2021.

A class is a convention about a number, not a measurement: the same FWI is an
ordinary summer day in one place and a rare one in another. For that, see
:mod:`fwi_chain.climatology`.
"""

from __future__ import annotations

__all__ = ["EFFIS_FWI_CLASSES", "effis_class"]

EFFIS_FWI_CLASSES: tuple[tuple[float, str], ...] = (
    (0.0, "low"),
    (11.2, "moderate"),
    (21.3, "high"),
    (38.0, "very high"),
    (50.0, "extreme"),
    (70.0, "very extreme"),
)
"""Each class with the FWI it starts at, lowest first."""


def effis_class(fwi: float) -> str:
    """The EFFIS fire danger class of ``fwi``.

    A boundary belongs to the class above it: 11.2 is "moderate". EFFIS
    writes the classes as ranges ("11.2 - 21.3") and does not say which side
    a boundary falls on; the last one it writes as "> 70".

    Raises ``ValueError`` for a negative or non-finite FWI.
    """
    if not fwi >= 0.0 or fwi == float("inf"):
        raise ValueError(f"an FWI is a number from 0 up, got {fwi}")
    name = EFFIS_FWI_CLASSES[0][1]
    for lower, label in EFFIS_FWI_CLASSES:
        if fwi >= lower:
            name = label
    return name
