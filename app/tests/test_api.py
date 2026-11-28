from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

import pytest
from diario import api
from starlette.testclient import TestClient

from fwi_chain import EFFIS_FWI_CLASSES, STANDARD_PARAMS, walk_chain

RIGHE = "\n".join(
    [
        "giorno,temperatura,umidita,vento,pioggia",
        "2026-07-01,31.5,28,14,0",
        "2026-07-02,33,24,20,0",
        "2026-07-03,29,45,8,6.5",
        "2026-07-04,30,35,25,0",
    ]
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("FWI_CHAIN_ENTE", "Comune di Prova")
    return TestClient(api.app)


def catena(client: TestClient, righe: str, **altro: Any) -> Any:
    r = client.post("/api/catena", json={"righe": righe, **altro})
    assert r.status_code == 200, r.text
    return r.json()


def test_config_names_the_body_the_rule_and_the_classes(client: TestClient) -> None:
    c = client.get("/api/config").json()
    assert c["ente"] == "Comune di Prova"
    assert "non è un'allerta" in c["regola"] and c["effis"] in c["regola"]
    assert c["effis"].startswith("https://forest-fire.emergency.copernicus.eu")
    assert [(k["da"], k["nome"]) for k in c["classi"]] == list(EFFIS_FWI_CLASSES)
    assert [k["etichetta"] for k in c["classi"]] == [
        "basso",
        "moderato",
        "alto",
        "molto alto",
        "estremo",
        "molto estremo",
    ]
    assert c["predefiniti"]["codici_iniziali"] == {"ffmc": 85.0, "dmc": 6.0, "dc": 15.0}
    assert c["predefiniti"]["giorni_avviamento"] == 30
    assert c["versione"]


def test_without_a_name_the_header_is_the_diary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FWI_CHAIN_ENTE", raising=False)
    assert TestClient(api.app).get("/api/config").json()["ente"] == (
        "Diario del pericolo d'incendio"
    )


def test_the_sample_says_where_it_is_from(client: TestClient) -> None:
    r = client.get("/api/esempio")
    assert r.headers["content-type"].startswith("text/csv")
    assert "ESEMPIO" in r.text and "Canada" in r.text and "cffdrs" in r.text
    assert client.get("/api/salute").json() == {"ok": True, "giorni_esempio": 48}


def test_the_sample_is_48_days_and_the_library_s_own_chain(client: TestClient) -> None:
    testo = client.get("/api/esempio").text
    r = catena(client, testo)
    assert len(r["giorni"]) == 48 and r["saltati"] == [] and r["giorni_senza_riga"] == 0
    assert r["giorni"][0]["day"] == "1985-04-13" and r["giorni"][-1]["day"] == "1985-05-30"

    osservazioni = api.leggi_righe(testo).osservazioni
    diretti = walk_chain(
        osservazioni, sorted(osservazioni), start=None, params=STANDARD_PARAMS, max_gap_days=30
    )
    assert [g["codes"]["fwi"] for g in r["giorni"]] == [round(d.outputs.fwi, 1) for d in diretti]
    assert [g["codes"]["dc"] for g in r["giorni"]] == [
        round(d.outputs.state.dc, 1) for d in diretti
    ]

    s = r["sintesi"]
    assert s["walked_days"] == 48
    assert s["peak"]["fwi"] == max(g["codes"]["fwi"] for g in r["giorni"])
    assert sum(s["class_days"].values()) == 48
    assert s["last"] == r["giorni"][-1]
    assert "non è un'allerta" in r["regola"]


def test_spin_up_days_are_marked(client: TestClient) -> None:
    r = catena(client, client.get("/api/esempio").text)
    assert [g["settled"] for g in r["giorni"]] == [False] * 29 + [True] * 19
    r = catena(client, RIGHE, giorni_avviamento=2)
    assert [g["settled"] for g in r["giorni"]] == [False, True, True, True]


def test_an_empty_value_skips_the_day_and_never_zeroes_it(client: TestClient) -> None:
    con_buco = RIGHE.replace("2026-07-03,29,45,8,6.5", "2026-07-03,29,45,8,")
    r = catena(client, con_buco)
    assert r["saltati"] == ["2026-07-03"]
    assert [g["day"] for g in r["giorni"]] == ["2026-07-01", "2026-07-02", "2026-07-04"]
    # The day after is compared with the last measured day, and the chain did not restart.
    assert r["giorni"][2]["change"]["previous_day"] == "2026-07-02"
    assert r["giorni"][2]["chain_days"] == 3 and r["ripartenze"] == []

    zero = catena(client, RIGHE.replace("2026-07-03,29,45,8,6.5", "2026-07-03,29,45,8,0"))
    assert len(zero["giorni"]) == 4
    assert zero["giorni"][3]["codes"] != r["giorni"][2]["codes"]

    senza_riga = catena(client, RIGHE.replace("2026-07-03,29,45,8,6.5\n", ""))
    assert senza_riga["saltati"] == [] and senza_riga["giorni_senza_riga"] == 1
    assert [g["codes"] for g in senza_riga["giorni"]] == [g["codes"] for g in r["giorni"]]


def test_semicolons_take_a_decimal_comma(client: TestClient) -> None:
    con_virgola = RIGHE.replace(",", ";").replace(".", ",")
    assert "2026-07-01;31,5;28;14;0" in con_virgola
    a, b = catena(client, RIGHE), catena(client, con_virgola)
    assert a["giorni"] == b["giorni"]
    assert a["giorni"][0]["observation"]["temperature_c"] == 31.5
    # No header, comment lines, blank lines, days out of order.
    righe = RIGHE.splitlines()[1:]
    sparse = "# il mio pluviometro\n\n" + "\n".join(reversed(righe)) + "\n"
    assert catena(client, sparse)["giorni"] == a["giorni"]


@pytest.mark.parametrize(
    ("riga", "atteso"),
    [
        ("2026-07-05,trenta,30,10,0", "riga 6: temperatura «trenta» non è un numero"),
        ("05/07/2026,30,30,10,0", "riga 6: «05/07/2026» non è un giorno"),
        ("2026-07-05,30,130,10,0", "riga 6: umidità 130 % fuori"),
        ("2026-07-05,30,30,10,-2", "riga 6: pioggia -2 mm fuori"),
        ("2026-07-05,30,30,10", "riga 6: 4 valori, ne servono 5"),
        ("2026-07-05,30,5,30,10,0", "riga 6: 6 valori, ne servono 5"),
        ("2026-07-02,30,30,10,0", "riga 6: il giorno 2026-07-02 è già alla riga 3"),
        ("2026-07-05,nan,30,10,0", "riga 6: temperatura nan °C fuori"),
    ],
)
def test_a_bad_row_is_a_400_that_names_it(client: TestClient, riga: str, atteso: str) -> None:
    r = client.post("/api/catena", json={"righe": f"{RIGHE}\n{riga}"})
    assert r.status_code == 400
    assert atteso in r.text


def test_bad_requests_are_400(client: TestClient) -> None:
    def stato(corpo: Any) -> int:
        return int(client.post("/api/catena", json=corpo).status_code)

    assert stato({}) == 400
    assert stato([1]) == 400
    assert stato({"righe": ""}) == 400
    assert stato({"righe": "2026-07-01,,,,"}) == 400
    assert stato({"righe": RIGHE, "codici_iniziali": {"ffmc": 140}}) == 400
    assert stato({"righe": RIGHE, "codici_iniziali": {"dc": "tanto"}}) == 400
    assert stato({"righe": RIGHE, "giorni_avviamento": -1}) == 400
    assert stato({"righe": RIGHE, "max_gap_days": 1.5}) == 400
    r = client.post("/api/catena", content="{", headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_start_codes_are_honoured(client: TestClient) -> None:
    codici = {"ffmc": 90.0, "dmc": 40.0, "dc": 300.0}
    r = catena(client, RIGHE, codici_iniziali=codici)
    assert r["codici_iniziali"] == codici
    params = replace(STANDARD_PARAMS, ffmc_start=90.0, dmc_start=40.0, dc_start=300.0)
    osservazioni = api.leggi_righe(RIGHE).osservazioni
    diretti = walk_chain(
        osservazioni, sorted(osservazioni), start=None, params=params, max_gap_days=30
    )
    assert [g["codes"]["fwi"] for g in r["giorni"]] == [round(d.outputs.fwi, 1) for d in diretti]
    standard = catena(client, RIGHE)
    assert r["giorni"][0]["codes"]["dc"] > standard["giorni"][0]["codes"]["dc"] + 200
    # A code left out keeps its standard value.
    solo_dc = catena(client, RIGHE, codici_iniziali={"dc": 300.0, "ffmc": None})
    assert solo_dc["codici_iniziali"] == {"ffmc": 85.0, "dmc": 6.0, "dc": 300.0}


def test_the_change_of_a_day_adds_up(client: TestClient) -> None:
    r = catena(client, client.get("/api/esempio").text)
    assert "change" not in r["giorni"][0]
    for ieri, oggi in zip(r["giorni"], r["giorni"][1:], strict=False):
        c = oggi["change"]
        assert c["previous_day"] == ieri["day"]
        assert c["fwi_previous"] == ieri["codes"]["fwi"]
        assert c["fwi_change"] == pytest.approx(oggi["codes"]["fwi"] - c["fwi_previous"], abs=0.11)
        effetti = [d["effect"] for d in c["drivers"]]
        assert {d["input"] for d in c["drivers"]} == {"temperature", "humidity", "wind", "rain"}
        # Each number is rounded to one decimal on its own: the sums hold within 0.2.
        assert sum(effetti) == pytest.approx(c["weather"], abs=0.2 + 1e-9)
        assert c["carry_over"] + sum(effetti) == pytest.approx(c["fwi_change"], abs=0.2 + 1e-9)


def test_a_long_gap_restarts_the_chain(client: TestClient) -> None:
    righe = RIGHE + "\n2026-09-15,28,30,12,0\n2026-09-16,29,28,15,0"
    r = catena(client, righe)
    assert r["ripartenze"] == ["2026-09-15"]
    ripartito = r["giorni"][4]
    assert ripartito["chain_days"] == 1 and "change" not in ripartito
    assert r["giorni"][5]["change"]["previous_day"] == "2026-09-15"
    assert ripartito["codes"] == catena(client, "2026-09-15,28,30,12,0")["giorni"][0]["codes"]
    # With a longer limit the same chain is carried across the gap.
    r = catena(client, righe, max_gap_days=100)
    assert r["ripartenze"] == [] and r["giorni"][4]["chain_days"] == 5


def test_the_page_is_served_and_calls_nothing_outside(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    pagina = r.text
    assert "Diario del pericolo d'incendio" in pagina
    assert "non è un'allerta" in pagina and "Canada" in pagina and "Limen" in pagina
    # The only absolute URLs are plain links the reader may follow.
    senza_link = re.sub(r"<a\b[^>]*>", "", pagina)
    assert "http://" not in senza_link and "https://" not in senza_link
    for nome in ("app.js", "app.css"):
        testo = client.get(f"/{nome}").text
        assert "http://" not in testo and "https://" not in testo
