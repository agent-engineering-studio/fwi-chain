"""Il diario del pericolo d'incendio: una piccola API sopra fwi-chain, e la sua pagina.

L'ente porta il meteo di un luogo, una riga per giorno. La pagina mostra la
catena FWI giorno per giorno e che cosa ha mosso l'indice. Non scarica meteo,
non mostra incendi né perimetri, non fa previsioni. Un indice di pericolo
meteorologico non è un'allerta: il pericolo ufficiale è pubblicato da EFFIS
e, in Italia, dal Dipartimento della Protezione Civile e dalle Regioni.

    uvicorn diario.api:app        # http://127.0.0.1:8000

Ogni numero sull'indice viene da ``fwi_chain`` (``walk_chain``,
``facts.day_facts``, ``facts.walk_facts``): qui si legge il CSV e si
controllano le letture, nient'altro.

Configurazione, con variabili d'ambiente:

* ``FWI_CHAIN_ENTE``: il nome dell'ente nella testata;
* ``FWI_CHAIN_DATI``: il file dell'esempio (default: ``data/`` dell'app);
* ``FWI_CHAIN_STATIC``: la cartella della pagina (default: ``static/`` dell'app).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, replace
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import BaseRoute, Mount, Route
from starlette.staticfiles import StaticFiles

from fwi_chain import (
    EFFIS_FWI_CLASSES,
    STANDARD_PARAMS,
    ChainDay,
    FwiParams,
    NoonObservation,
    __version__,
    walk_chain,
)
from fwi_chain.facts import EFFIS_URL, RULE, day_facts, walk_facts

HERE = Path(__file__).resolve().parent
DATA = Path(
    os.environ.get("FWI_CHAIN_DATI", HERE.parent.parent / "data" / "esempio_canada_1985.csv")
)
STATIC = Path(os.environ.get("FWI_CHAIN_STATIC", HERE.parent.parent / "static"))

ENTE = "Diario del pericolo d'incendio"
REGOLA = (
    "Un indice di pericolo meteorologico non è un'allerta né una previsione di incendi: "
    "dice quanto facilmente un incendio partirebbe e si propagherebbe con il meteo dato, "
    "non che ce ne sarà uno. Il pericolo d'incendio ufficiale per l'Europa è pubblicato da "
    f"EFFIS ({EFFIS_URL}); in Italia il bollettino è emesso dal Dipartimento della "
    "Protezione Civile e dalle Regioni."
)
ETICHETTE = {
    "low": "basso",
    "moderate": "moderato",
    "high": "alto",
    "very high": "molto alto",
    "extreme": "estremo",
    "very extreme": "molto estremo",
}
GIORNI_AVVIAMENTO = 30
MAX_GAP_DAYS = 30
MAX_RIGHE = 20_000

# Le quattro letture, nell'ordine delle colonne: nome, campo e intervallo ammesso.
LETTURE: tuple[tuple[str, str, float, float], ...] = (
    ("temperatura", "°C", -90.0, 60.0),
    ("umidità", "%", 0.0, 100.0),
    ("vento", "km/h", 0.0, 500.0),
    ("pioggia", "mm", 0.0, 2000.0),
)


@dataclass(frozen=True, slots=True)
class Meteo:
    """Il CSV letto: i giorni misurati, e quelli con una lettura vuota."""

    osservazioni: dict[date, NoonObservation]
    saltati: list[date]


@cache
def esempio() -> str:
    """Il CSV dell'esempio: Canada 1985, la serie di prova del pacchetto R cffdrs."""
    return DATA.read_text(encoding="utf-8")


def leggi_righe(testo: str) -> Meteo:
    """CSV ``giorno,temperatura,umidita,vento,pioggia``, una riga per giorno.

    Separatore ``;`` o ``,``; con ``;`` la virgola è decimale. Una riga di
    intestazione e le righe che iniziano con ``#`` sono ignorate. Un valore
    vuoto vuol dire "non misurato": il giorno è saltato, mai messo a zero.

    ``ValueError`` con il numero della riga se una riga non si può leggere.
    """
    righe = testo.removeprefix("﻿").splitlines()
    if len(righe) > MAX_RIGHE:
        raise ValueError(f"troppe righe: {len(righe)}, al massimo {MAX_RIGHE}")
    dati = [(n, r.strip()) for n, r in enumerate(righe, start=1)]
    dati = [(n, r) for n, r in dati if r and not r.startswith("#")]
    separatore = ";" if any(";" in r for _, r in dati) else ","
    if dati and not dati[0][1][:1].isdigit():
        dati = dati[1:]  # l'intestazione

    osservazioni: dict[date, NoonObservation] = {}
    saltati: list[date] = []
    viste: dict[date, int] = {}
    for n, riga in dati:
        campi = [c.strip() for c in riga.split(separatore)]
        if len(campi) != 5:
            consiglio = (
                " Con la virgola decimale il separatore deve essere «;»."
                if separatore == "," and len(campi) > 5
                else ""
            )
            raise ValueError(
                f"riga {n}: {len(campi)} valori, ne servono 5 "
                f"(giorno, temperatura, umidità, vento, pioggia).{consiglio}"
            )
        try:
            giorno = date.fromisoformat(campi[0])
        except ValueError:
            raise ValueError(f"riga {n}: «{campi[0]}» non è un giorno (AAAA-MM-GG)") from None
        if giorno in viste:
            raise ValueError(f"riga {n}: il giorno {giorno} è già alla riga {viste[giorno]}")
        viste[giorno] = n
        valori = [
            _lettura(c, n, lettura, virgola=separatore == ";")
            for c, lettura in zip(campi[1:], LETTURE, strict=True)
        ]
        if any(v is None for v in valori):
            saltati.append(giorno)
            continue
        t, h, w, p = (v for v in valori if v is not None)
        osservazioni[giorno] = NoonObservation(
            temperature_c=t, relative_humidity_pct=h, wind_speed_kmh=w, rain_24h_mm=p
        )
    if not osservazioni:
        raise ValueError("nessun giorno con tutte e quattro le letture: la catena non parte")
    return Meteo(osservazioni, sorted(saltati))


def _lettura(
    testo: str, riga: int, lettura: tuple[str, str, float, float], *, virgola: bool
) -> float | None:
    """Una lettura: ``None`` se vuota (non misurata), ``ValueError`` se non è un numero."""
    nome, unita, minimo, massimo = lettura
    if not testo:
        return None
    try:
        valore = float(testo.replace(",", ".") if virgola else testo)
    except ValueError:
        raise ValueError(f"riga {riga}: {nome} «{testo}» non è un numero") from None
    if not math.isfinite(valore) or not minimo <= valore <= massimo:
        raise ValueError(
            f"riga {riga}: {nome} {testo} {unita} fuori dall'intervallo "
            f"{minimo:g}-{massimo:g} {unita}"
        )
    return valore


def cammina(
    osservazioni: dict[date, NoonObservation], *, params: FwiParams, max_gap_days: int
) -> list[ChainDay]:
    """La catena sui giorni misurati, in ordine.

    Un giorno alla volta, ognuno dal punto lasciato dal precedente: così è
    ``walk_chain`` a decidere se un buco è troppo lungo (più di
    ``max_gap_days``) e la catena riparte dai codici iniziali.
    """
    camminati: list[ChainDay] = []
    for giorno in sorted(osservazioni):
        camminati += walk_chain(
            osservazioni,
            [giorno],
            start=camminati[-1].point if camminati else None,
            params=params,
            max_gap_days=max_gap_days,
        )
    return camminati


def _params(codici: Any) -> FwiParams:
    """I parametri standard, con i codici iniziali dell'ente dove li dà."""
    if codici is None:
        return STANDARD_PARAMS
    if not isinstance(codici, dict):
        raise ValueError("codici_iniziali: servono ffmc, dmc e dc")
    limiti = {"ffmc": 101.0, "dmc": 10_000.0, "dc": 10_000.0}
    p = STANDARD_PARAMS
    scelti = {"ffmc": p.ffmc_start, "dmc": p.dmc_start, "dc": p.dc_start}
    for nome, massimo in limiti.items():
        if codici.get(nome) is None:
            continue
        valore = _numero(codici[nome], f"codici_iniziali.{nome}")
        if not 0.0 <= valore <= massimo:
            raise ValueError(f"codici_iniziali.{nome}: {valore:g} fuori da 0-{massimo:g}")
        scelti[nome] = valore
    return replace(p, ffmc_start=scelti["ffmc"], dmc_start=scelti["dmc"], dc_start=scelti["dc"])


def _numero(valore: Any, nome: str) -> float:
    if isinstance(valore, bool) or not isinstance(valore, int | float) or not math.isfinite(valore):
        raise ValueError(f"{nome}: serve un numero")
    return float(valore)


def _intero(q: dict[str, Any], nome: str, default: int, massimo: int) -> int:
    valore = q.get(nome)
    if valore is None:
        return default
    if isinstance(valore, bool) or not isinstance(valore, int) or not 0 <= valore <= massimo:
        raise ValueError(f"{nome}: serve un numero intero di giorni da 0 a {massimo}")
    return valore


def _giorno(
    giorno: ChainDay, precedente: ChainDay | None, params: FwiParams, avviamento: int
) -> Any:
    """``day_facts`` del giorno, senza i testi ripetuti a ogni riga."""
    fatti = day_facts(giorno, previous=precedente, params=params, spinup_days=avviamento)
    del fatti["rule"], fatti["effis_class_from"]
    return fatti


async def config(_: Request) -> JSONResponse:
    p = STANDARD_PARAMS
    return JSONResponse(
        {
            "ente": os.environ.get("FWI_CHAIN_ENTE", "").strip() or ENTE,
            "regola": REGOLA,
            "rule": RULE,
            "effis": EFFIS_URL,
            "classi": [
                {"nome": nome, "da": da, "etichetta": ETICHETTE[nome]}
                for da, nome in EFFIS_FWI_CLASSES
            ],
            "versione": __version__,
            "predefiniti": {
                "codici_iniziali": {"ffmc": p.ffmc_start, "dmc": p.dmc_start, "dc": p.dc_start},
                "giorni_avviamento": GIORNI_AVVIAMENTO,
                "max_gap_days": MAX_GAP_DAYS,
            },
        }
    )


async def catena(request: Request) -> JSONResponse:
    """La catena di un luogo sul meteo dato: ogni giorno, e che cosa l'ha mosso."""
    try:
        q = await request.json()
        if not isinstance(q, dict) or not isinstance(q.get("righe"), str):
            raise ValueError("serve «righe»: il CSV del meteo, una riga per giorno")
        params = _params(q.get("codici_iniziali"))
        avviamento = _intero(q, "giorni_avviamento", GIORNI_AVVIAMENTO, 3650)
        max_gap_days = _intero(q, "max_gap_days", MAX_GAP_DAYS, 3650)
        meteo = leggi_righe(q["righe"])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    camminati = cammina(meteo.osservazioni, params=params, max_gap_days=max_gap_days)
    # Il giorno prima è quello da cui la catena è arrivata: nessuno, se è ripartita.
    giorni = [
        _giorno(g, camminati[i - 1] if g.chain_days > 1 else None, params, avviamento)
        for i, g in enumerate(camminati)
    ]
    sintesi = walk_facts(camminati, params=params, spinup_days=avviamento)
    del sintesi["series"], sintesi["rule"]  # già in «giorni» e in «regola»
    sintesi["last"] = giorni[-1]
    primo, ultimo = camminati[0].day, camminati[-1].day
    return JSONResponse(
        {
            "giorni": giorni,
            "sintesi": sintesi,
            "saltati": [g.isoformat() for g in meteo.saltati],
            "giorni_senza_riga": (ultimo - primo).days
            + 1
            - len(camminati)
            - sum(primo < g < ultimo for g in meteo.saltati),
            "ripartenze": [g.day.isoformat() for g in camminati[1:] if g.chain_days == 1],
            "codici_iniziali": {
                "ffmc": params.ffmc_start,
                "dmc": params.dmc_start,
                "dc": params.dc_start,
            },
            "giorni_avviamento": avviamento,
            "max_gap_days": max_gap_days,
            "regola": REGOLA,
        }
    )


async def esempio_csv(_: Request) -> PlainTextResponse:
    return PlainTextResponse(esempio(), media_type="text/csv; charset=utf-8")


async def salute(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "giorni_esempio": len(leggi_righe(esempio()).osservazioni)})


routes: list[BaseRoute] = [
    Route("/api/salute", salute),
    Route("/api/config", config),
    Route("/api/catena", catena, methods=["POST"]),
    Route("/api/esempio", esempio_csv),
]
if STATIC.is_dir():
    routes.append(Mount("/", StaticFiles(directory=STATIC, html=True), name="pagina"))

app = Starlette(routes=routes)
