"""``llms.txt``, ``llms-full.txt`` and the agent skill, written into the built site.

``llms.txt`` (https://llmstxt.org) is the site's index for language models:
one link per page, with what it holds. ``llms-full.txt`` is the whole
documentation as plain Markdown, with the API reference rendered from the
docstrings (the same source as the HTML reference), so an assistant reads
everything in one request. The agent skill, ``skills/fwi-chain/SKILL.md``,
is published as is.

Run it after the site is built (``make docs`` does)::

    uv run --group docs python tools/build_llms.py

All three come from the sources on every build, so they never go stale. A
page in the nav without a description here fails the build.
"""

from __future__ import annotations

import re
import shutil
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = ROOT / "site"
SKILL = Path("skills/fwi-chain/SKILL.md")

SUMMARY = (
    "A small Python library with no dependencies for the Canadian Fire Weather Index chain "
    "(Van Wagner 1987): FFMC, DMC, DC, ISI, BUI and FWI from four noon readings, one day at a "
    "time with an explicit state; walking a chain over many days from a stored point, redoing "
    "it when better rain arrives, a climatology in 21 quantiles, the EFFIS danger classes, and "
    "what moved the index from one day to the next. It also gives the answers as facts, an MCP "
    "server and a check that a text quotes the numbers right."
)

NOTES = """\
- Install: `pip install fwi-chain` (extra: `mcp`). Python 3.12+. No dependencies.
- A fire weather index is not an alert and not a forecast of fires. The official fire danger
  for Europe is published by EFFIS.
- The library fetches no weather: the caller brings one noon reading per day (temperature in
  C, relative humidity in %, 10 m wind in km/h, rain over the previous 24 h in mm).
- The three moisture codes are recursive: persist the state between days. A chain started
  from the standard codes needs weeks before DMC and DC mean anything.
- A day without readings is skipped, never filled with zeros.
- No clock is read: "today" is always an argument.
- It follows the equations as printed in Van Wagner (1987). The cffdrs R package follows the
  1985 FORTRAN program: over its 48-day test series the two differ by at most 0.25 FWI
  points, and agree on the EFFIS class every day. `CFFDRS_PARAMS` (or
  `FwiParams(constants="cffdrs")`) takes the program's constants and matches cffdrs to 0.006."""

#: What each page of the nav holds, for llms.txt.
DESCRIPTIONS = {
    "index.md": "the guide: what the FWI is, install, quick start, the state, what is inside",
    "how-fwi-works.md": "the FWI System in plain language: the three moisture codes, the three "
    "indices, a worked example by hand, the danger classes",
    "getting-started.md": "install, the first day, a season, persisting the state",
    "cookbook.md": "recipes: a daily job, many stations, the southern hemisphere, classes, CSV",
    "faq.md": "common questions: official or not, cffdrs and xclim, why persist the state",
    "ai.md": "the answers as facts, what moved the index, the text check, the MCP server and "
    "its four tools",
    "examples.md": "the seven notebooks, the page for a public body, Docker and the ports",
    "api.md": "every public name with its arguments, by hand, with examples",
    "reference.md": "every public name, its signature and its docstring, read from the source",
    "validation.md": "what the numbers are checked against, and what they are not",
    "benchmark.md": "known cases where the answer is known: 48 days against cffdrs, the rain "
    "each code ignores, a stored state too old",
    "riuso.md": "in Italian, for a public body: the fire danger diary, what it does not do, "
    "what stays with the body",
    "social-kit.md": "ready-made posts and images to tell others about the library",
    "changelog.md": "what changed in each release",
    "contributing.md": "how to contribute",
}

_INCLUDE = re.compile(r'^--8<-- "(?P<path>[^"]+)"\s*$', re.MULTILINE)
_API = re.compile(r"^::: (?P<module>[\w.]+)\s*$", re.MULTILINE)
_HTML_BLOCK = re.compile(r'^<p align="center">.*?^</p>\n', re.MULTILINE | re.DOTALL)
_ROLE = re.compile(r":(?:mod|func|class|meth|data|attr|exc):`~?([^`]+)`")


def main() -> int:
    if not SITE.is_dir():
        print(f"{SITE} is not there: build the site first", file=sys.stderr)
        return 1
    config = tomllib.loads((ROOT / "zensical.toml").read_text(encoding="utf-8"))["project"]
    url = config["site_url"].rstrip("/") + "/"
    pages = list(_pages(config["nav"]))
    (SITE / "llms.txt").write_text(llms_txt(config, url, pages), encoding="utf-8")
    (SITE / "llms-full.txt").write_text(llms_full(config, url, pages), encoding="utf-8")
    target = SITE / SKILL
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / SKILL, target)
    for written in ("llms.txt", "llms-full.txt", SKILL.as_posix()):
        print(f"site/{written}: {(SITE / written).stat().st_size:,} bytes")
    return 0


def llms_txt(config: dict[str, Any], url: str, pages: list[tuple[str, str, str]]) -> str:
    sections: dict[str, list[str]] = {}
    for group, title, file in pages:
        link = f"- [{title}]({url}{_page_url(file)}): {_describe(file)}"
        sections.setdefault(group or "Docs", []).append(link)
    lines = [f"# {config['site_name']}", "", f"> {SUMMARY}", "", NOTES]
    for heading, links in sections.items():
        lines += ["", f"## {heading}", "", *links]
    lines += [
        "",
        "## For agents",
        "",
        f"- [Full documentation as text]({url}llms-full.txt): every page above, "
        "with the API reference rendered from the docstrings",
        f"- [Agent skill]({url}{SKILL.as_posix()}): how to use the library and the traps "
        "of the data, for coding agents",
        "",
        "## Optional",
        "",
        f"- [Source code]({config['repo_url']}): the repository",
        "- [EFFIS](https://forest-fire.emergency.copernicus.eu/): the official fire danger of "
        "Europe, and the danger classes used here",
        "",
    ]
    return "\n".join(lines)


def llms_full(config: dict[str, Any], url: str, pages: list[tuple[str, str, str]]) -> str:
    parts = [f"# {config['site_name']}\n\n> {SUMMARY}\n\nSource: {url}\n"]
    for group, title, file in pages:
        if file == "changelog.md":
            continue  # long, and linked from llms.txt
        label = f"{group} / {title}" if group else title
        parts.append(f"\n\n<!-- page: {label} · {url}{_page_url(file)} -->\n\n")
        parts.append(_markdown(file))
    parts.append(f"\n\n<!-- agent skill · {url}{SKILL.as_posix()} -->\n\n")
    parts.append((ROOT / SKILL).read_text(encoding="utf-8"))
    return "".join(parts)


def _pages(nav: list[Any], group: str = "") -> Iterator[tuple[str, str, str]]:
    for item in nav:
        ((title, value),) = item.items()
        if isinstance(value, list):
            yield from _pages(value, title)
        else:
            yield group, title, value


def _page_url(file: str) -> str:
    return "" if file == "index.md" else file.removesuffix(".md") + "/"


def _source(file: str) -> str:
    return (DOCS / file).read_text(encoding="utf-8")


def _describe(file: str) -> str:
    if file in DESCRIPTIONS:
        return DESCRIPTIONS[file]
    raise ValueError(f"tools/build_llms.py: no description for {file}, add it to DESCRIPTIONS")


def _markdown(file: str) -> str:
    text = _source(file)
    text = _INCLUDE.sub(lambda m: (ROOT / m["path"]).read_text(encoding="utf-8"), text)
    text = _API.sub(lambda m: api_markdown(m["module"]), text)
    return _HTML_BLOCK.sub("", text).strip() + "\n"


# The API reference, from the same docstrings mkdocstrings renders.


def _module(name: str) -> Any:
    import griffe

    return griffe.load(name, search_paths=[str(ROOT / "src")])


def api_markdown(name: str) -> str:
    module = _module(name)
    out = [f"## `{name}`", ""]
    if module.docstring:
        out += [_plain(module.docstring.value), ""]
    for member in _public(module):
        out += _member(member, level=3)
    return "\n".join(out)


def _plain(text: str) -> str:
    """Docstring markup as Markdown: Sphinx roles and ``double`` backticks as code."""
    return _ROLE.sub(r"`\1`", text).replace("``", "`")


def _public(obj: Any) -> list[Any]:
    return [
        m
        for n, m in obj.members.items()
        if not n.startswith("_") and not m.is_alias and (m.is_function or m.is_class or m.docstring)
    ]


def _member(member: Any, *, level: int, owner: str = "") -> list[str]:
    hashes = "#" * level
    name = f"{owner}.{member.name}" if owner else member.name
    if member.is_class:
        head = f"class {name}({_params(member)})"
    elif member.is_function:
        prefix = "async " if "async" in member.labels else ""
        returns = f" -> {member.returns}" if member.returns else ""
        head = f"{prefix}{name}({_params(member)}){returns}"
    else:
        annotation = f": {member.annotation}" if member.annotation else ""
        head = f"{name}{annotation}"
    out = [f"{hashes} `{head}`", ""]
    if member.docstring:
        out += [_plain(member.docstring.value), ""]
    if member.is_class:
        for sub in _public(member):
            if sub.is_function or sub.docstring:
                out += _member(sub, level=level + 1, owner=member.name)
    return out


def _params(obj: Any) -> str:
    import griffe

    params = [p for p in obj.parameters if p.name not in ("self", "cls")]
    text: list[str] = []
    star = False
    for p in params:
        if p.kind is griffe.ParameterKind.keyword_only and not star:
            text.append("*")
            star = True
        if p.kind is griffe.ParameterKind.var_positional:
            star = True
        item = {"var_positional": "*", "var_keyword": "**"}.get(p.kind.name, "") + p.name
        if p.annotation is not None:
            item += f": {p.annotation}"
        if p.default is not None:
            item += f" = {p.default}"
        text.append(item)
    return ", ".join(text)


if __name__ == "__main__":
    raise SystemExit(main())
