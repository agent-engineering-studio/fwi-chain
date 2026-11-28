"""The MCP server: the chain as tools an assistant can call.

    pip install "fwi-chain[mcp]"
    fwi-chain-mcp                    # on standard input and output
    fwi-chain-mcp --http 8772        # streamable HTTP, at http://127.0.0.1:8772/mcp

The tools compute only from what the call gives them: no network, no weather
of their own, no clock. Bring the noon readings from a station or a model;
the answer is the chain's, with the rule that a fire weather index is not an
alert. The tools are the functions of :mod:`fwi_chain.facts`, and ``check``
is :func:`fwi_chain.check.check_text`.

This module is the only one that needs the ``mcp`` extra. Nothing else in
the package imports it.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import date
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from fwi_chain.chain import CFFDRS_PARAMS, STANDARD_PARAMS, Constants, FwiParams, FwiState
from fwi_chain.check import check_text
from fwi_chain.facts import RULE, day_facts, distribution_facts, walk_facts
from fwi_chain.walk import ChainDay, ChainPoint, NoonObservation, walk_chain

__all__ = ["DEFAULT_PORT", "INSTRUCTIONS", "create_server", "main", "run"]

#: The HTTP port when ``--http`` is given without one.
DEFAULT_PORT = 8772

INSTRUCTIONS = f"""The Canadian Fire Weather Index chain (Van Wagner 1987): FFMC, DMC, DC, ISI,
BUI and FWI, computed day by day from four noon readings.

Rules for every answer:
- Quote numbers only from the tools, with their units: temperature in \u00b0C,
  humidity in %, wind in km/h, rain in mm over the 24 hours before noon. The
  six codes have no unit.
- The codes are recursive: a chain started from the standard codes needs
  weeks of weather before DMC and DC mean anything. When `settled` is false,
  say the chain is still spinning up.
- A day without readings is left out, never filled with zeros: a rain of 0
  is a dry day, not a missing one.
- The classes are the EFFIS fire danger classes: a convention on the number.
  Whether a value is rare in a place is `percentile`, not the class.
- `change` says what moved the index: `carry_over` is the chain's memory,
  each `effect` the FWI points moved by one reading. Do not add causes that
  are not there.
- {RULE} For danger to people, point to the official bulletin and to 112.
- Before answering in words, you can pass your text and the facts to `check`.
"""

Row = tuple[str, float | None, float | None, float | None, float | None]


def _params(start_codes: dict[str, float] | None, constants: Constants = "1987") -> FwiParams:
    if not start_codes:
        return CFFDRS_PARAMS if constants == "cffdrs" else STANDARD_PARAMS
    return FwiParams(
        ffmc_start=float(start_codes.get("ffmc", STANDARD_PARAMS.ffmc_start)),
        dmc_start=float(start_codes.get("dmc", STANDARD_PARAMS.dmc_start)),
        dc_start=float(start_codes.get("dc", STANDARD_PARAMS.dc_start)),
        day_length_dmc=STANDARD_PARAMS.day_length_dmc,
        day_length_dc=STANDARD_PARAMS.day_length_dc,
        constants=constants,
    )


def _walk(
    readings: Sequence[Row],
    resume: dict[str, Any] | None,
    start_codes: dict[str, float] | None,
    max_gap_days: int,
    constants: Constants = "1987",
) -> tuple[list[ChainDay], FwiParams]:
    observations: dict[date, NoonObservation] = {}
    for row in readings:
        day, t, rh, wind, rain = row
        if None in (t, rh, wind, rain):
            continue  # not measured: the day is skipped, never zeroed
        observations[date.fromisoformat(day)] = NoonObservation(
            float(t or 0.0), float(rh or 0.0), float(wind or 0.0), float(rain or 0.0)
        )
    start = None
    if resume:
        start = ChainPoint(
            day=date.fromisoformat(resume["day"]),
            state=FwiState(
                ffmc=float(resume["ffmc"]), dmc=float(resume["dmc"]), dc=float(resume["dc"])
            ),
            chain_days=int(resume.get("chain_days", 0)),
        )
    params = _params(start_codes, constants)
    walked = walk_chain(
        observations, sorted(observations), start=start, params=params, max_gap_days=max_gap_days
    )
    return walked, params


def create_server(**options: Any) -> MCPServer[Any]:
    """The MCP server with its four tools. ``options`` go to ``MCPServer``."""
    from fwi_chain import __version__

    server: MCPServer[Any] = MCPServer(
        name="fwi-chain",
        title="Fire Weather Index chain (Van Wagner 1987)",
        instructions=INSTRUCTIONS,
        website_url="https://agentengineering.it/fwi-chain/",
        version=__version__,
        **options,
    )

    @server.tool()
    def walk(
        readings: list[Row],
        resume: dict[str, Any] | None = None,
        start_codes: dict[str, float] | None = None,
        max_gap_days: int = 7,
        spinup_days: int | None = None,
        constants: Constants = "1987",
    ) -> dict[str, Any]:
        """The chain over a stretch of days, from the noon readings given.

        ``readings``: ``[[day, temperature_c, relative_humidity_pct,
        wind_speed_kmh, rain_24h_mm], ...]``, day in ISO 8601, rain over the
        24 hours before noon; a value ``null`` means the day was not measured
        and is skipped (never write 0 for it). ``resume``: the stored point to
        continue from, ``{day, ffmc, dmc, dc, chain_days}``; without it the
        chain starts from the standard codes (85 / 6 / 15, or ``start_codes``).
        ``constants``: ``"1987"`` (the report, the default) or ``"cffdrs"``
        (the 1985 program, to match the cffdrs R package). Answers every day's
        codes and class, the peak, the rain, and the last day with what moved it.
        """
        return _guard(
            lambda: _walk_facts(readings, resume, start_codes, max_gap_days, spinup_days, constants)
        )

    @server.tool()
    def explain(
        readings: list[Row],
        day: str,
        resume: dict[str, Any] | None = None,
        start_codes: dict[str, float] | None = None,
        max_gap_days: int = 7,
        month_values: list[float] | None = None,
        constants: Constants = "1987",
    ) -> dict[str, Any]:
        """One day of a walked stretch, and what moved its FWI from the day before.

        ``readings``, ``resume``, ``start_codes`` and ``constants`` as in ``walk``; ``day``
        is the day to explain, which must have readings. ``month_values``:
        past FWI values of this place in the same month, to say where the day
        falls among them (its percentile). Answers the readings, the six
        codes, the class, and ``change``: the chain's memory and the FWI
        points moved by each of temperature, humidity, wind and rain.
        """

        def facts() -> dict[str, Any]:
            walked, params = _walk(readings, resume, start_codes, max_gap_days, constants)
            wanted = date.fromisoformat(day)
            at = next((i for i, d in enumerate(walked) if d.day == wanted), None)
            if at is None:
                raise ValueError(f"{day} has no readings: nothing was computed for it")
            quantiles = None
            if month_values:
                from fwi_chain.climatology import quantiles as q

                quantiles = q(month_values)
            return day_facts(
                walked[at],
                previous=walked[at - 1] if at else None,
                params=params,
                month_quantiles=quantiles,
            )

        return _guard(facts)

    @server.tool()
    def percentile(values: list[float], fwi: float | None = None) -> dict[str, Any]:
        """Where an FWI falls among the values of its place and month.

        ``values``: past FWI values, of one place and one month over years.
        Answers their 21 quantiles (0, 5, ..., 100), the median and the 90th,
        and for ``fwi`` its percentile and its class.
        """
        return _guard(lambda: distribution_facts(values, value=fwi))

    @server.tool()
    def check(text: str, facts: dict[str, Any], question: str = "") -> dict[str, Any]:
        """Check a text against the facts of a tool: numbers invented, in the wrong unit, rounded.

        ``facts``: the answer of ``walk``, ``explain`` or ``percentile``.
        Empty ``misquotes`` means every number is a fact of its unit; it does
        not prove the number is said of the right thing.
        """
        found = check_text(text, facts, question=question)
        return {"misquotes": [asdict(m) for m in found], "faithful": not found}

    return server


def _walk_facts(
    readings: Sequence[Row],
    resume: dict[str, Any] | None,
    start_codes: dict[str, float] | None,
    max_gap_days: int,
    spinup_days: int | None,
    constants: Constants = "1987",
) -> dict[str, Any]:
    walked, params = _walk(readings, resume, start_codes, max_gap_days, constants)
    return walk_facts(walked, params=params, spinup_days=spinup_days)


def _guard(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """What the library refuses, as an error the agent can read and act on."""
    try:
        return call()
    except (ValueError, KeyError, TypeError) as exc:
        raise ToolError(f"{type(exc).__name__}: {exc}") from exc


def run(*, http_port: int | None = None, http_host: str = "127.0.0.1") -> None:
    """Serve on standard input and output, or over streamable HTTP at ``/mcp``."""
    if http_port is None:
        create_server().run("stdio")
    else:
        create_server().run("streamable-http", host=http_host, port=http_port)


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point of ``fwi-chain-mcp``."""
    parser = argparse.ArgumentParser(
        prog="fwi-chain-mcp", description="The Fire Weather Index chain as an MCP server."
    )
    parser.add_argument(
        "--http",
        type=int,
        nargs="?",
        const=DEFAULT_PORT,
        metavar="PORT",
        help=f"serve over streamable HTTP at /mcp (default port {DEFAULT_PORT}); "
        "without it, standard input and output",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP address (default 127.0.0.1; 0.0.0.0 in a container)",
    )
    args = parser.parse_args(argv)
    run(http_port=args.http, http_host=args.host)
