from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

pytest.importorskip("mcp")

from mcp import Client
from mcp.server.mcpserver import MCPServer

from fwi_chain import STANDARD_PARAMS, advance
from fwi_chain import mcp_server as m
from fwi_chain.facts import RULE

READINGS: list[list[Any]] = [
    ["2026-07-01", 30.0, 25.0, 20.0, 0.0],
    ["2026-07-02", 31.0, 22.0, 18.0, 0.0],
    ["2026-07-03", None, None, None, None],  # not measured: skipped
    ["2026-07-04", 24.0, 60.0, 8.0, 12.4],
]


async def call(client: Client, tool: str, **args: Any) -> dict[str, Any]:
    result = await client.call_tool(tool, args)
    assert not result.is_error, result.content
    found: dict[str, Any] = result.structured_content
    return found


async def test_the_tools_and_the_rules() -> None:
    async with Client(m.create_server()) as client:
        tools = {t.name: t for t in (await client.list_tools()).tools}
        assert sorted(tools) == ["check", "explain", "percentile", "walk"]
        assert all(t.description for t in tools.values())
        assert client.instructions == m.INSTRUCTIONS
        assert "not an alert" in m.INSTRUCTIONS and "never filled with zeros" in m.INSTRUCTIONS


async def test_walk_is_the_chain_and_a_day_not_measured_is_skipped() -> None:
    async with Client(m.create_server()) as client:
        w = await call(client, "walk", readings=READINGS, spinup_days=30)
        first = advance(
            STANDARD_PARAMS.initial_state,
            month=7,
            temperature_c=30.0,
            relative_humidity_pct=25.0,
            wind_speed_kmh=20.0,
            rain_24h_mm=0.0,
            params=STANDARD_PARAMS,
        )
        assert w["series"][0]["fwi"] == round(first.fwi, 1)
        assert [row["day"] for row in w["series"]] == ["2026-07-01", "2026-07-02", "2026-07-04"]
        assert w["walked_days"] == 3 and w["rain_total_mm"] == 12.4
        assert w["last"]["settled"] is False and w["rule"] == RULE
        assert w["last"]["change"]["drivers"][0]["input"] == "rain"


async def test_walk_resumes_from_a_stored_point_and_from_other_start_codes() -> None:
    async with Client(m.create_server()) as client:
        resume = {"day": "2026-06-30", "ffmc": 90.0, "dmc": 80.0, "dc": 500.0, "chain_days": 60}
        w = await call(client, "walk", readings=READINGS[:1], resume=resume)
        assert w["last"]["chain_days"] == 61 and w["series"][0]["dc"] > 500.0
        seeded = await call(client, "walk", readings=READINGS[:1], start_codes={"dc": 300.0})
        assert 300.0 < seeded["series"][0]["dc"] < 320.0


async def test_explain_percentile_and_check() -> None:
    async with Client(m.create_server()) as client:
        values = [float(v) for v in range(101)]
        e = await call(client, "explain", readings=READINGS, day="2026-07-04", month_values=values)
        assert e["change"]["previous_day"] == "2026-07-02"
        assert e["climatology"]["median_fwi"] == 50.0
        first = await call(client, "explain", readings=READINGS, day="2026-07-01")
        assert "change" not in first and "climatology" not in first
        p = await call(client, "percentile", values=values, fwi=92.5)
        assert p["percentile"] == 92.5 and p["effis_class"] == "very extreme"
        wrong_unit = f"it rained {e['observation']['rain_24h_mm']} %"
        c = await call(client, "check", text=wrong_unit, facts=e)
        assert c["faithful"] is False and c["misquotes"][0]["fault"] == "unit"
        good = await call(client, "check", text="it rained 12.4 mm", facts=e)
        assert good == {"misquotes": [], "faithful": True}


@pytest.mark.parametrize(
    ("tool", "args", "message"),
    [
        ("explain", {"readings": READINGS, "day": "2026-07-03"}, "has no readings"),
        ("walk", {"readings": [["2026-07-01", None, None, None, None]]}, "no day was walked"),
        ("walk", {"readings": [["2026-07-01", 30.0]]}, "validation error"),
        ("walk", {"readings": [["yesterday", 30.0, 25.0, 20.0, 0.0]]}, "ValueError"),
        ("walk", {"readings": READINGS[:1], "resume": {"day": "2026-06-30"}}, "KeyError"),
        ("percentile", {"values": []}, "needs values"),
    ],
)
async def test_what_the_library_refuses_is_an_error_the_agent_can_read(
    tool: str, args: dict[str, Any], message: str
) -> None:
    async with Client(m.create_server()) as client:
        result = await client.call_tool(tool, args)
        assert result.is_error
        assert message in str(result.content)


def test_the_command_line_picks_the_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    served: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        MCPServer, "run", lambda self, transport, **kw: served.append((transport, kw))
    )
    m.main([])
    m.main(["--http"])
    m.main(["--http", "9000", "--host", "0.0.0.0"])
    assert served == [
        ("stdio", {}),
        ("streamable-http", {"host": "127.0.0.1", "port": m.DEFAULT_PORT}),
        ("streamable-http", {"host": "0.0.0.0", "port": 9000}),
    ]
    assert m.DEFAULT_PORT == 8772


def test_the_package_does_not_import_mcp() -> None:
    code = "import sys, fwi_chain; print('mcp' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
