# Il diario del pericolo d'incendio

Una pagina per un ente: l'indice di pericolo meteorologico d'incendio (FWI) di
un luogo, giorno per giorno, sul meteo che l'ente porta. E che cosa ha mosso
l'indice da un giorno all'altro.

> **Un indice di pericolo meteorologico non è un'allerta né una previsione di
> incendi.** Il pericolo d'incendio ufficiale è pubblicato da
> [EFFIS](https://forest-fire.emergency.copernicus.eu/) e, in Italia, dal
> Dipartimento della Protezione Civile e dalle Regioni.

La pagina non scarica meteo, non mostra incendi né perimetri, non fa
previsioni: per quello c'è
[Limen](https://github.com/agent-engineering-studio/limen). Né il server né la
pagina chiamano la rete.

## Avviarla

Con Docker, dalla radice del repository:

```bash
FWI_CHAIN_ENTE="Comune di Gioia del Colle" docker compose up ui
# http://localhost:3007
```

Con [uv](https://docs.astral.sh/uv/) e Node, dalla radice del repository:

```bash
make demo       # scarica Bootstrap Italia in static/vendor e avvia su http://127.0.0.1:3007
```

Oppure a mano, da `app/`:

```bash
sh vendor.sh                                    # Bootstrap Italia in static/vendor
uv run uvicorn diario.api:app --port 3007       # http://127.0.0.1:3007
uv run pytest                                   # i test dell'API
```

| Variabile | Che cosa fa | Senza |
|---|---|---|
| `FWI_CHAIN_ENTE` | il nome dell'ente in testata | "Diario del pericolo d'incendio" |
| `FWI_CHAIN_DATI` | il file CSV dell'esempio | `data/esempio_gioia_del_colle_2025.csv` |
| `FWI_CHAIN_STATIC` | la cartella della pagina | `static/` |

Per pubblicarla, mettetela dietro il proxy del vostro sito.

## Che cosa fa

1. **Il meteo.** Un CSV, una riga per giorno, con le letture di mezzogiorno:
   `giorno,temperatura,umidita,vento,pioggia` (AAAA-MM-GG; °C; %; km/h; mm
   nelle 24 ore prima di mezzogiorno). Separatore `,` o `;`; con `;` vale la
   virgola decimale. L'intestazione è facoltativa. Un valore vuoto vuol dire
   «non misurato»: il giorno è saltato, mai messo a zero, e la pagina dice
   quanti giorni ha saltato. «Carica l'esempio» mette l'estate 2025 di Gioia
   del Colle (BA), meteo ricostruito da Open-Meteo: non sono misure di stazione.
2. **La catena, giorno per giorno.** Il grafico dell'FWI sulle fasce delle
   classi EFFIS, e la tabella: le quattro letture, FFMC, DMC, DC, ISI, BUI,
   FWI, classe. I primi giorni (30, se non si cambia) sono «in avviamento»: i
   codici di siccità riportano ancora il loro valore iniziale.
3. **Che cosa ha mosso l'indice.** Scelto un giorno: l'FWI del giorno prima e
   quello del giorno, la memoria della catena (con lo stesso meteo l'indice
   si sarebbe mosso comunque, perché il combustibile continua ad asciugarsi) e
   i punti di FWI mossi da ognuna delle quattro letture. Le parti si sommano.
4. **Esporta.** La tabella come CSV, con la regola in testa.

I codici iniziali (85 / 6 / 15, quelli standard di primavera) e i giorni di
avviamento si possono cambiare. Dopo un buco di più di 30 giorni nel meteo la
catena riparte dai codici iniziali, e la pagina lo dice.

## L'API

| Indirizzo | Che cosa risponde |
|---|---|
| `GET /api/config` | ente, la regola, il link a EFFIS, le classi (nome, FWI da cui partono, etichetta italiana), la versione di fwi-chain, i valori predefiniti |
| `POST /api/catena` | `{righe: "<csv>", codici_iniziali?: {ffmc, dmc, dc}, giorni_avviamento?, max_gap_days?}` → `{giorni, sintesi, saltati, giorni_senza_riga, ripartenze, regola}` |
| `GET /api/esempio` | il CSV dell'esempio |
| `GET /api/salute` | `{ok, giorni_esempio}` |

Una riga che non si può leggere dà un 400 con il numero della riga e il motivo.

Ogni numero sull'indice viene da [fwi-chain](https://github.com/agent-engineering-studio/fwi-chain)
(`walk_chain`, `facts.day_facts`, `facts.walk_facts`): l'app legge il CSV,
controlla le letture e disegna. I codici sono arrotondati a un decimale, come
li pubblicano i servizi antincendio.

## Dati

L'esempio (`data/esempio_gioia_del_colle_2025.csv`) è l'estate 2025 di Gioia
del Colle (BA), dal 1 maggio al 30 settembre: 153 letture di mezzogiorno (11
UTC) dalla [Historical Weather API di Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api),
rianalisi ERA5 di Copernicus, licenza [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Il mezzogiorno di ogni giorno è letto con `fwi_chain.noon_readings`. È meteo
ricostruito da un modello a circa 25 km, non una stazione: i temporali locali
possono mancare. Si rigenera con `uv run python tools/make_app_sample.py` (serve
la rete). Fino a fwi-chain 1.3.0 l'esempio era la serie di prova di cffdrs
(Canada, 1985): è stato tolto perché cffdrs è distribuito sotto GPL-2. Le classi di
pericolo sono quelle di EFFIS. Le tabelle della durata del giorno sono quelle
standard di Van Wagner (46°N). Bootstrap Italia è servito dalla pagina stessa,
senza CDN.
