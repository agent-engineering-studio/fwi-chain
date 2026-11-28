"""The example notebooks, written from the scripts in ``examples/``.

    uv run --group examples python tools/make_notebooks.py
    make notebooks        # this, then every notebook run and saved
    uv run --group examples python tools/make_notebooks.py --check   # CI: still the examples?

Notebooks 01-06 are the six example scripts, cell by cell: the script is the
source, so the two cannot drift. Notebook 07 is written here: what moved the
index, the facts and the text check, on the test series of cffdrs.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
OUT = ROOT / "notebooks"

RULE = (
    "> **A fire weather index is not an alert.** It says how easily a fire would start and "
    "spread in the weather given, not that one will. The official fire danger for Europe is "
    "published by [EFFIS](https://forest-fire.emergency.copernicus.eu/)."
)

#: Scripts that import ``weather.py`` or write a file read ``sys.argv``: in a
#: notebook they get the examples folder on the path and a scratch file.
SETUP = """\
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path("../examples").resolve()))  # weather.py, the synthetic season
sys.argv = ["notebook", str(Path(tempfile.mkdtemp()) / "{scratch}")]"""

SCRATCH = {"02": "season.csv", "03": "fwi_state.sqlite", "04": "unused"}

TITLES = {
    "01": "One day of the chain",
    "02": "A whole fire season, day by day",
    "03": "A daily job that keeps its state",
    "04": "Many stations, one chain each",
    "05": "The southern hemisphere",
    "06": "The equations one by one",
}


def markdown(text: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip("\n").splitlines(keepends=True),
    }


def notebook(cells: list[dict[str, Any]]) -> dict[str, Any]:
    for i, cell in enumerate(cells):
        cell["id"] = f"cell-{i:02d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def from_script(path: Path) -> dict[str, Any]:
    number = path.name[:2]
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source)
    doc = ast.get_docstring(module) or ""
    body = "\n".join(source.splitlines()[module.body[0].end_lineno :]) if doc else source
    doc = re.sub(r"\n*Run:.*?(?=\n\n|\Z)", "", doc, flags=re.DOTALL).replace("``", "`")
    first, _, rest = doc.partition("\n")
    intro = f"# {int(number)} · {TITLES[number]}\n\n{first}\n{rest}".rstrip()
    intro += f"\n\nThe same code as [`examples/{path.name}`](../examples/{path.name}).\n\n{RULE}"
    cells = [markdown(intro)]
    if number in SCRATCH:
        cells.append(code(SETUP.format(scratch=SCRATCH[number])))
    cells += [code(chunk) for chunk in re.split(r"\n{3,}", body.strip("\n")) if chunk.strip()]
    return notebook(cells)


def what_moved_the_index() -> dict[str, Any]:
    return notebook(
        [
            markdown(
                "# 7 · What moved the index\n\n"
                "The FWI of 7 May 1985 was 52.6; the day before, 21.7. What did that? This "
                "notebook walks the chain over the 48 days of the test series of the `cffdrs` "
                "R package (13 April to 30 May 1985, from Van Wagner & Pickett 1985), takes "
                "one day apart, and checks a sentence written about it.\n\n"
                "No network: the series is in `benchmarks/cffdrs/`.\n\n" + RULE
            ),
            code(
                "import csv\n"
                "from datetime import date\n"
                "from pathlib import Path\n\n"
                "import matplotlib.pyplot as plt\n\n"
                "from fwi_chain import (\n"
                "    EFFIS_FWI_CLASSES,\n"
                "    STANDARD_PARAMS,\n"
                "    NoonObservation,\n"
                "    explain_change,\n"
                "    walk_chain,\n"
                ")\n"
                "from fwi_chain.check import check_text\n"
                "from fwi_chain.facts import day_facts\n\n"
                'with Path("../benchmarks/cffdrs/test_fwi.csv").open() as f:\n'
                '    rows = list(csv.DictReader(f, delimiter=";"))\n'
                "observations = {\n"
                '    date(int(r["yr"]), int(r["mon"]), int(r["day"])): NoonObservation(\n'
                '        float(r["temp"]), float(r["rh"]), float(r["ws"]), float(r["prec"])\n'
                "    )\n"
                "    for r in rows\n"
                "}\n"
                "walked = walk_chain(\n"
                "    observations, sorted(observations), start=None, params=STANDARD_PARAMS, "
                "max_gap_days=7\n"
                ")\n"
                "len(walked), walked[0].day, walked[-1].day"
            ),
            markdown(
                "## The 48 days\n\nThe FWI, over the fire danger classes EFFIS maps it in, "
                "and the rain of each day."
            ),
            code(
                "days = [d.day for d in walked]\n"
                "fig, (top, bottom) = plt.subplots(\n"
                '    2, 1, figsize=(10, 5), sharex=True, gridspec_kw={"height_ratios": [3, 1]}\n'
                ")\n"
                "edges = [lower for lower, _ in EFFIS_FWI_CLASSES] + [80.0]\n"
                'colours = ["#7bc67b", "#f2e25a", "#f5a742", "#e8552d", "#a8281e", "#5c1a4a"]\n'
                "bands = zip(EFFIS_FWI_CLASSES, edges[1:], colours, strict=True)\n"
                "for (lower, name), upper, colour in bands:\n"
                "    top.axhspan(lower, upper, color=colour, alpha=0.25, lw=0)\n"
                '    top.text(days[0], lower + 0.8, name, fontsize=8, color="#333")\n'
                'top.plot(days, [d.outputs.fwi for d in walked], color="#222", marker="o", ms=3)\n'
                'top.set_ylim(0, 60)\ntop.set_ylabel("FWI")\n'
                'bottom.bar(days, [d.observation.rain_24h_mm for d in walked], color="#3b7dd8")\n'
                'bottom.set_ylabel("rain, mm")\n'
                "fig.autofmt_xdate()\nplt.show()"
            ),
            markdown(
                "## One day, taken apart\n\n"
                "With the very same weather as the day before, the index would still have "
                "moved: fuel that is drying keeps drying. That is the chain's memory "
                "(`carry_over`). The rest is the weather, split among the four readings: the "
                "effect of a reading is its average effect over every order in which the four "
                "could have changed (the Shapley value), so the four add up."
            ),
            code(
                "at = days.index(date(1985, 5, 7))\n"
                "e = explain_change(walked[at - 1], walked[at], params=STANDARD_PARAMS)\n"
                'print(f"FWI {e.fwi_yesterday:.1f} -> {e.fwi_today:.1f}  ({e.change:+.1f})")\n'
                'print(f"  the chain\'s memory   {e.carry_over:+6.1f}")\n'
                "for d in e.drivers:\n"
                '    print(f"  {d.input:<18} {d.effect:+6.1f}   {d.yesterday:g} -> {d.today:g}")\n'
                "assert abs(e.carry_over + sum(d.effect for d in e.drivers) - e.change) < 1e-9"
            ),
            code(
                'labels = ["memory"] + [d.input for d in e.drivers]\n'
                "effects = [e.carry_over] + [d.effect for d in e.drivers]\n"
                "fig, ax = plt.subplots(figsize=(8, 2.8))\n"
                'ax.barh(labels[::-1], effects[::-1], color=["#c0392b" if x > 0 else "#3b7dd8" '
                "for x in effects[::-1]])\n"
                'ax.axvline(0, color="#222", lw=0.8)\n'
                'ax.set_xlabel("FWI points, 6 to 7 May 1985")\nplt.show()'
            ),
            markdown(
                "## The same as facts, and a sentence checked against them\n\n"
                "`day_facts` gives the day as plain data, units in the key names. A model may "
                "word these numbers; it never computes them. `check_text` finds the numbers of "
                "a text that are not facts of their unit."
            ),
            code(
                "facts = day_facts(\n"
                "    walked[at], previous=walked[at - 1], params=STANDARD_PARAMS, spinup_days=30\n"
                ")\n"
                '{k: facts[k] for k in ("day", "observation", "codes", "effis_class", "settled")}'
            ),
            code(
                "faithful = (\n"
                '    "On 7 May 1985 the FWI rose from 21.7 to 52.6. "\n'
                '    "The wind, from 12 to 27 km/h, "\n'
                '    "moved it by 18.0 points; drier air, from 33 % to 17 %, by 11.1."\n'
                ")\n"
                'wrong = "The FWI reached 52.6 as the wind rose to 27 % and added 18.5 points."\n'
                "print(check_text(faithful, facts))\n"
                "for m in check_text(wrong, facts):\n"
                "    print(m.text, m.fault, m.nearest)"
            ),
            markdown(
                "## What this does not say\n\n"
                "- The chain had walked 25 days on 7 May: `settled` is false. The drought code "
                "needs weeks before it stops reporting its starting value.\n"
                "- The check knows a number is a fact of the right unit, not that it is said "
                "of the right thing.\n"
                "- `cffdrs` gives 52.31 for this day, this library 52.56: the two follow "
                "different printings of the same constants. See `benchmarks/README.md`."
            ),
        ]
    )


def sources(book: dict[str, Any]) -> list[tuple[str, str]]:
    return [(c["cell_type"], "".join(c["source"])) for c in book["cells"]]


def main() -> int:
    OUT.mkdir(exist_ok=True)
    books = {p.stem: from_script(p) for p in sorted(EXAMPLES.glob("[0-9][0-9]_*.py"))}
    books["07_what_moved_the_index"] = what_moved_the_index()
    check = "--check" in sys.argv[1:]
    stale = []
    for name, book in books.items():
        path = OUT / f"{name}.ipynb"
        if check:
            saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"cells": []}
            if sources(saved) != sources(book):
                stale.append(path.name)
            continue
        path.write_text(json.dumps(book, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    if stale:
        print("not the examples any more (run `make notebooks`):", *stale, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
