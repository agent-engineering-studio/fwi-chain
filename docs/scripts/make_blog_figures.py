"""The figures of the Open Data article, in Italian and in English.

    uv run --with matplotlib python docs/scripts/make_blog_figures.py

Both are computed by the library on the 48 days of the cffdrs test series
(benchmarks/cffdrs/): nothing is drawn by hand.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fwi_chain import (
    EFFIS_FWI_CLASSES,
    STANDARD_PARAMS,
    ChainDay,
    explain_change,
    walk_chain,
)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "docs" / "images" / "blog"
# The cffdrs series is downloaded and checked, not committed (GPL-2).
sys.path.insert(0, str(ROOT))
from benchmarks import cffdrs_data  # noqa: E402

COLOURS = ["#7bc67b", "#f2e25a", "#f5a742", "#e8552d", "#a8281e", "#5c1a4a"]

TEXT = {
    "it": {
        "classes": ["basso", "moderato", "alto", "molto alto", "estremo", "molto estremo"],
        "memory": "memoria della catena",
        "inputs": {
            "wind": "vento",
            "humidity": "umidità",
            "temperature": "temperatura",
            "rain": "pioggia",
        },
        "moved_title": "7 maggio 1985: l'indice passa da 21,7 a 52,6. Che cosa lo ha mosso",
        "moved_x": "punti di FWI",
        "fwi": "FWI",
        "here": "fwi-chain",
        "series_title": "48 giorni, due implementazioni: fwi-chain e cffdrs",
        "diff": "differenza da cffdrs\n(punti di FWI)",
        "comma": True,
    },
    "en": {
        "classes": ["low", "moderate", "high", "very high", "extreme", "very extreme"],
        "memory": "the chain's memory",
        "inputs": {
            "wind": "wind",
            "humidity": "humidity",
            "temperature": "temperature",
            "rain": "rain",
        },
        "moved_title": "7 May 1985: the index goes from 21.7 to 52.6. What moved it",
        "moved_x": "FWI points",
        "fwi": "FWI",
        "here": "fwi-chain",
        "series_title": "48 days, two implementations: fwi-chain and cffdrs",
        "diff": "difference from cffdrs\n(FWI points)",
        "comma": False,
    },
}
UNITS = {"wind": "km/h", "humidity": "%", "temperature": "°C", "rain": "mm"}


def series() -> tuple[list[ChainDay], list[float]]:
    observations = cffdrs_data.observations()
    theirs = [e["fwi"] for e in cffdrs_data.expected()]
    walked = walk_chain(
        observations, sorted(observations), start=None, params=STANDARD_PARAMS, max_gap_days=7
    )
    return walked, theirs


def number(value: float, comma: bool, signed: bool = False) -> str:
    text = f"{value:+.1f}" if signed else f"{value:g}"
    return text.replace(".", ",") if comma else text


def what_moved(walked: list[ChainDay], lang: str) -> None:
    t = TEXT[lang]
    at = [d.day for d in walked].index(date(1985, 5, 7))
    e = explain_change(walked[at - 1], walked[at], params=STANDARD_PARAMS)
    labels = [t["memory"]]
    for d in e.drivers:
        was, now = number(d.yesterday, t["comma"]), number(d.today, t["comma"])
        labels.append(f"{t['inputs'][d.input]}\n{was} \u2192 {now} {UNITS[d.input]}")
    effects = [e.carry_over] + [d.effect for d in e.drivers]
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=160)
    colours = ["#5d7083"] + ["#b3261e" if x > 0 else "#2f6fb3" for x in effects[1:]]
    ax.barh(labels[::-1], effects[::-1], color=colours[::-1], height=0.6)
    for y, x in enumerate(effects[::-1]):
        ax.text(x + 0.4, y, number(x, t["comma"], signed=True), va="center", fontsize=11)
    ax.axvline(0, color="#222", lw=0.8)
    ax.set_xlim(-1, 22)
    ax.set_xlabel(t["moved_x"])
    ax.set_title(t["moved_title"], loc="left", fontsize=12, fontweight="bold")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / f"what-moved-{lang}.png")
    plt.close(fig)


def against_cffdrs(walked: list[ChainDay], theirs: list[float], lang: str) -> None:
    t = TEXT[lang]
    days = [d.day for d in walked]
    ours = [d.outputs.fwi for d in walked]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9, 5.4), dpi=160, sharex=True, gridspec_kw={"height_ratios": [3, 1.2]}
    )
    edges = [lower for lower, _ in EFFIS_FWI_CLASSES] + [80.0]
    bands = zip(EFFIS_FWI_CLASSES, edges[1:], COLOURS, t["classes"], strict=True)
    for (lower, _), upper, colour, name in bands:
        top.axhspan(lower, upper, color=colour, alpha=0.25, lw=0)
        if lower < 60:
            top.text(days[-1], lower + 0.8, name + " ", fontsize=8, color="#333", ha="right")
    top.plot(days, theirs, color="#888", lw=4, alpha=0.6, label="cffdrs")
    top.plot(days, ours, color="#111", lw=1.2, marker="o", ms=2.5, label=t["here"])
    top.set_ylim(0, 60)
    top.set_ylabel(t["fwi"])
    top.legend(loc="upper left", frameon=False)
    top.set_title(t["series_title"], loc="left", fontsize=12, fontweight="bold")
    bottom.bar(days, [a - b for a, b in zip(ours, theirs, strict=True)], color="#5d7083")
    bottom.set_ylim(0, 0.3)
    bottom.set_ylabel(t["diff"], fontsize=8)
    for ax in (top, bottom):
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / f"against-cffdrs-{lang}.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    walked, theirs = series()
    for lang in TEXT:
        what_moved(walked, lang)
        against_cffdrs(walked, theirs, lang)
    for path in sorted(OUT.glob("*.png")):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
