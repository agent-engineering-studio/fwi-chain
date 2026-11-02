"""Regenerate the figures in docs/images from the library itself.

Run:  make figures
      (= uv run --with matplotlib python docs/scripts/make_figures.py)

matplotlib is needed only here, never by the package. Every number drawn is
computed by fwi_chain from the synthetic season in examples/weather.py.
"""

from __future__ import annotations

import datetime as dt
import sys
from collections.abc import Iterable
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples"))

from weather import NoonReading, synthetic_season  # noqa: E402

from fwi_chain import STANDARD_PARAMS, FwiOutputs, FwiState, advance  # noqa: E402

OUT = ROOT / "docs" / "images"

# Chart tokens (light mode): surface, inks, hairlines, and fixed series hues.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
FFMC_C = "#2a78d6"  # slot 1, blue
DMC_C = "#eb6834"  # slot 2, orange
DC_C = "#1baf7a"  # slot 3, aqua
FWI_C = "#e34948"  # slot 8, red: the index itself, always this colour
RAIN_C = "#86b6ef"  # blue ramp step 250

# EFFIS danger classes, lower bounds.
CLASSES = [(5.2, "low"), (11.2, "moderate"), (21.3, "high"), (38.0, "very high"), (50.0, "extreme")]

plt.rcParams.update(
    {
        "font.family": ["DejaVu Sans"],
        "font.size": 10,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
        "legend.frameon": False,
        "legend.labelcolor": INK_2,
        "svg.fonttype": "none",
        "svg.hashsalt": "fwi-chain",
    }
)


def run(readings: Iterable[NoonReading], state: FwiState) -> list[tuple[NoonReading, FwiOutputs]]:
    rows = []
    for r in readings:
        out = advance(
            state,
            month=r.day.month,
            temperature_c=r.temperature_c,
            relative_humidity_pct=r.relative_humidity_pct,
            wind_speed_kmh=r.wind_speed_kmh,
            rain_24h_mm=r.rain_24h_mm,
            params=STANDARD_PARAMS,
        )
        state = out.state
        rows.append((r, out))
    return rows


def month_axis(ax: Axes) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.margins(x=0.01)


def caption(fig: Figure, text: str) -> None:
    fig.text(0.01, 0.01, text, color=MUTED, fontsize=8, ha="left", va="bottom")


def save(fig: Figure, name: str) -> None:
    fig.savefig(OUT / name, metadata={"Date": None})
    plt.close(fig)
    print(f"wrote docs/images/{name}")


SEASON = list(synthetic_season())
ROWS = run(SEASON, STANDARD_PARAMS.initial_state)
DAYS = [r.day for r, _ in ROWS]
SYNTHETIC = "Synthetic Mediterranean season (examples/weather.py), computed with fwi-chain."


def fig_season() -> None:
    fig, (ax, ax_rain) = plt.subplots(
        2, 1, figsize=(10, 5.2), sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.12}
    )
    fwi = [o.fwi for _, o in ROWS]
    for lower, label in CLASSES:
        ax.axhline(lower, color=GRID, linewidth=0.8, zorder=0)
        ax.text(DAYS[-1] + dt.timedelta(days=3), lower, label, color=MUTED, fontsize=8, va="bottom")
    ax.plot(DAYS, fwi, color=FWI_C, linewidth=1.6)
    ax.grid(False)
    ax.set_title("Fire Weather Index through one fire season")
    ax.set_ylabel("FWI")
    ax.set_ylim(0, max(fwi) * 1.08)
    peak_i = max(range(len(fwi)), key=fwi.__getitem__)
    peak_r = ROWS[peak_i][0]
    ax.annotate(
        f"{fwi[peak_i]:.0f}: a windy day ({peak_r.wind_speed_kmh:.0f} km/h)\n"
        "on a summer of drought",
        xy=(DAYS[peak_i], fwi[peak_i]),
        xytext=(DAYS[peak_i] - dt.timedelta(days=75), fwi[peak_i] * 0.93),
        color=INK_2,
        fontsize=9,
        arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8},
    )
    ax.text(
        DAYS[3],
        max(fwi) * 0.93,
        "April rain keeps\nthe index near zero",
        color=INK_2,
        fontsize=9,
        va="top",
    )

    ax_rain.bar(DAYS, [r.rain_24h_mm for r, _ in ROWS], color=RAIN_C, width=0.9)
    ax_rain.set_ylabel("Rain (mm)")
    ax_rain.invert_yaxis()
    ax_rain.grid(False)
    month_axis(ax_rain)
    fig.subplots_adjust(left=0.07, right=0.91, top=0.92, bottom=0.1)
    caption(fig, SYNTHETIC + " Class bounds: EFFIS.")
    save(fig, "fire-season.svg")


def fig_codes() -> None:
    fig, axes = plt.subplots(3, 1, figsize=(10, 6.2), sharex=True, gridspec_kw={"hspace": 0.45})
    panels = [
        ("FFMC: fine fuel. Reacts within a day", [o.state.ffmc for _, o in ROWS], FFMC_C),
        ("DMC: duff layer. Remembers about 12 days", [o.state.dmc for _, o in ROWS], DMC_C),
        ("DC: deep drought. Remembers about 52 days", [o.state.dc for _, o in ROWS], DC_C),
    ]
    for ax, (title, values, color) in zip(axes, panels, strict=True):
        ax.plot(DAYS, values, color=color, linewidth=1.6)
        ax.set_title(title, fontsize=10.5)
        ax.set_ylim(bottom=0)
        rain_days = [d for (r, _), d in zip(ROWS, DAYS, strict=True) if r.rain_24h_mm > 10]
        for d in rain_days:
            ax.axvline(d, color=RAIN_C, alpha=0.35, linewidth=1, zorder=0)
    month_axis(axes[-1])
    fig.suptitle(
        "The three moisture codes: same weather, three memories",
        x=0.07,
        ha="left",
        fontweight="bold",
        color=INK,
        fontsize=12,
    )
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.09)
    caption(fig, SYNTHETIC + " Light-blue lines: days with more than 10 mm of rain.")
    save(fig, "moisture-codes.svg")


def fig_memory() -> None:
    start = FwiState(ffmc=90.0, dmc=60.0, dc=450.0)
    july = dt.date(2026, 7, 10)
    storm = NoonReading(july, 20.0, 85.0, 8.0, 40.0)
    dry = [NoonReading(july + dt.timedelta(days=i), 31.0, 25.0, 12.0, 0.0) for i in range(1, 22)]
    rows = run([storm, *dry], start)
    after = rows[0][1].state

    def recovered(name: str) -> list[float]:
        before, low = getattr(start, name), getattr(after, name)
        return [0.0] + [
            100.0 * (getattr(o.state, name) - low) / (before - low) for _, o in rows[1:]
        ]

    days = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.axhline(100, color=AXIS, linewidth=1, zorder=0)
    for name, label, color in (
        ("ffmc", "FFMC", FFMC_C),
        ("dmc", "DMC", DMC_C),
        ("dc", "DC", DC_C),
    ):
        # Past 100 % the code is drier than before the storm: cap it there,
        # the question is only how long the way back takes.
        ys = [min(y, 100.0) for y in recovered(name)]
        ax.plot(days, ys, color=color, label=label, marker="o", markersize=3.5)
        back = next(d for d, y in zip(days, ys, strict=True) if y >= 100.0)
        ax.annotate(
            f"{label}: {back} day{'s' if back > 1 else ''}",
            xy=(back, 100),
            xytext=(back, 108),
            ha="center",
            color=INK,
            fontsize=9,
            arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.8},
        )
    ax.set_xlim(0, days[-1])
    ax.set_ylim(0, 116)
    ax.set_xticks(range(0, days[-1] + 1, 5))
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Dry days after a 40 mm storm (31 °C, 25 % RH)")
    ax.set_ylabel("Way back to pre-storm dryness (%)")
    ax.set_title(
        "After a storm, fine fuel is dry again in two days; deep drought takes weeks", pad=18
    )
    ax.legend(loc="lower right")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14)
    caption(fig, "Start: FFMC 90, DMC 60, DC 450 (mid-July). Computed with fwi-chain.")
    save(fig, "memory.svg")


def fig_restart() -> None:
    restart = dt.date(2026, 7, 1)
    i0 = DAYS.index(restart)
    cold = run(SEASON[i0:], STANDARD_PARAMS.initial_state)
    days = DAYS[i0:]
    warm = ROWS[i0:]

    fig, (ax_dc, ax_fwi) = plt.subplots(
        2, 1, figsize=(10, 5.6), sharex=True, gridspec_kw={"hspace": 0.35}
    )
    for ax, get, title in (
        (ax_dc, lambda o: o.state.dc, "Drought Code"),
        (ax_fwi, lambda o: o.fwi, "Fire Weather Index"),
    ):
        ax.plot(
            days,
            [get(o) for _, o in warm],
            color=FWI_C if ax is ax_fwi else DC_C,
            label="state carried since 1 April",
        )
        ax.plot(
            days,
            [get(o) for _, o in cold],
            color=MUTED,
            linewidth=1.6,
            label="restarted on 1 July from 85 / 6 / 15",
        )
        ax.set_title(title, fontsize=10.5)
        ax.set_ylim(bottom=0)
    ax_dc.legend(loc="upper left")
    month_axis(ax_fwi)
    fig.suptitle(
        "Why you must persist the state: a cold restart underestimates danger for weeks",
        x=0.07,
        ha="left",
        fontweight="bold",
        color=INK,
        fontsize=12,
    )
    fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.09)
    caption(fig, SYNTHETIC)
    save(fig, "restart.svg")


def fig_social() -> None:
    """1280x640 card for the GitHub social preview and for posts."""
    fig = plt.figure(figsize=(12.8, 6.4), dpi=100)
    fig.patch.set_facecolor("#1a1a19")
    fig.text(0.06, 0.80, "fwi-chain", color="#f0efec", fontsize=54, fontweight="bold")
    fig.text(
        0.06,
        0.69,
        "The Canadian Fire Weather Index, in pure Python",
        color="#c3c2b7",
        fontsize=22,
    )
    fig.text(
        0.06,
        0.60,
        "zero dependencies  ·  fully typed  ·  verified to 1e-9  ·  Apache-2.0",
        color="#898781",
        fontsize=15,
    )
    fig.text(0.06, 0.08, "pip install fwi-chain", color="#f0efec", fontsize=20, family="monospace")
    fig.text(
        0.94,
        0.08,
        "github.com/agent-engineering-studio/fwi-chain",
        color="#898781",
        fontsize=13,
        ha="right",
    )
    ax = fig.add_axes((0.06, 0.2, 0.88, 0.34))
    ax.set_facecolor("#1a1a19")
    fwi = [o.fwi for _, o in ROWS]
    ax.fill_between(DAYS, fwi, color="#e66767", alpha=0.18, linewidth=0)
    ax.plot(DAYS, fwi, color="#e66767", linewidth=2.2)
    ax.axis("off")
    ax.margins(x=0)
    fig.savefig(OUT / "social-preview.png", facecolor="#1a1a19", metadata={"Software": None})
    plt.close(fig)
    print("wrote docs/images/social-preview.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig_season()
    fig_codes()
    fig_memory()
    fig_restart()
    fig_social()
