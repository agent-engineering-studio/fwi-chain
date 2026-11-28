// Il diario del pericolo d'incendio: manda il meteo, disegna la catena, mostra che cosa
// ha mosso l'indice. Ogni numero sull'indice viene dall'API: qui si disegna soltanto.
"use strict";

const $ = (id) => document.getElementById(id);
const LETTURE = {
  temperature: { nome: "Temperatura", chiave: "c", unita: "°C" },
  humidity: { nome: "Umidità", chiave: "pct", unita: "%" },
  wind: { nome: "Vento", chiave: "kmh", unita: "km/h" },
  rain: { nome: "Pioggia", chiave: "mm", unita: "mm" },
};
let classi = [];
let ultima = null;
let testoEsempio = null;

const numero = (x, cifre = 1) =>
  x.toLocaleString("it-IT", { minimumFractionDigits: cifre, maximumFractionDigits: cifre });
const lettura = (x) => x.toLocaleString("it-IT", { maximumFractionDigits: 2 });
const conSegno = (x) => (x > 0 ? "+" : x < 0 ? "−" : "") + numero(Math.abs(x));
const tempo = (iso) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
const giornoBreve = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const giornoLungo = (iso) => new Date(tempo(iso)).toLocaleDateString("it-IT", {
  weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC",
});
const indiceClasse = (nome) => classi.findIndex((c) => c.nome === nome);
const etichetta = (nome) => classi[indiceClasse(nome)]?.etichetta ?? nome;

async function chiedi(url, corpo) {
  const r = await fetch(url, corpo === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  if (!r.ok) throw new Error((await r.text()) || `errore ${r.status}`);
  return (r.headers.get("content-type") || "").includes("json") ? r.json() : r.text();
}

function elemento(tag, testo, classe) {
  const e = document.createElement(tag);
  if (testo !== undefined) e.textContent = testo;
  if (classe) e.className = classe;
  return e;
}

function errore(testo) {
  $("errore").textContent = testo;
  $("errore").classList.toggle("d-none", !testo);
}

async function avvio() {
  const c = await chiedi("api/config");
  classi = c.classi;
  $("ente").textContent = c.ente;
  document.title = `${c.ente} · la catena FWI giorno per giorno`;
  $("effis").href = c.effis;
  $("versione").textContent = c.versione;
  const p = c.predefiniti;
  $("ffmc").value = p.codici_iniziali.ffmc;
  $("dmc").value = p.codici_iniziali.dmc;
  $("dc").value = p.codici_iniziali.dc;
  $("avviamento").value = p.giorni_avviamento;
}

async function caricaEsempio() {
  errore("");
  try {
    testoEsempio = await chiedi("api/esempio");
  } catch (e) {
    errore(`L'esempio non si può caricare: ${e.message}`);
    return;
  }
  $("righe").value = testoEsempio;
  await calcola();
}

async function leggiFile() {
  const file = $("file").files[0];
  if (file) $("righe").value = await file.text();
}

function campo(id) {
  const testo = $(id).value.trim().replace(",", ".");
  return testo === "" ? null : Number(testo);
}

async function calcola() {
  errore("");
  const righe = $("righe").value;
  if (!righe.trim()) {
    errore("Manca il meteo: incollate le righe, scegliete un file o caricate l'esempio.");
    return;
  }
  const corpo = {
    righe,
    codici_iniziali: { ffmc: campo("ffmc"), dmc: campo("dmc"), dc: campo("dc") },
    giorni_avviamento: campo("avviamento"),
  };
  try {
    ultima = await chiedi("api/catena", corpo);
  } catch (e) {
    errore(`La catena non si può calcolare: ${e.message}`);
    return;
  }
  ultima.esempio = testoEsempio !== null && righe.trim() === testoEsempio.trim();
  mostra(ultima);
}

function mostra(r) {
  const s = r.sintesi;
  $("vuoto").classList.add("d-none");
  $("risultato").classList.remove("d-none");
  $("nota-esempio").classList.toggle("d-none", !r.esempio);

  const perClasse = Object.entries(s.class_days)
    .map(([nome, n]) => `${etichetta(nome)} ${n}`).join(", ");
  $("sintesi").replaceChildren(
    elemento("strong", `${s.walked_days} giorni`),
    ` calcolati, dal ${giornoBreve(s.first_day)}/${s.first_day.slice(0, 4)} al `
    + `${giornoBreve(s.last_day)}/${s.last_day.slice(0, 4)}. L'indice più alto è `,
    elemento("strong", `FWI ${numero(s.peak.fwi)}`),
    ` il ${giornoBreve(s.peak.day)} (classe ${etichetta(s.peak.effis_class)}). `
    + `Pioggia in tutto: ${numero(s.rain_total_mm)} mm. Giorni per classe: ${perClasse}.`,
  );

  const c = r.codici_iniziali;
  const note = [
    `La catena è partita da FFMC ${lettura(c.ffmc)}, DMC ${lettura(c.dmc)}, DC ${lettura(c.dc)}. `
    + `I primi ${r.giorni_avviamento} giorni sono in avviamento.`,
  ];
  if (r.saltati.length) {
    note.push(`${r.saltati.length} ${r.saltati.length === 1 ? "giorno saltato" : "giorni saltati"} `
      + `perché una lettura non è misurata (mai messa a zero): ${r.saltati.map(giornoBreve).join(", ")}.`);
  } else {
    note.push("Nessun giorno saltato: tutte le righe hanno le quattro letture.");
  }
  if (r.giorni_senza_riga) {
    note.push(`${r.giorni_senza_riga} giorni fra il primo e l'ultimo non hanno una riga: `
      + "la catena li ha saltati.");
  }
  if (r.ripartenze.length) {
    note.push(`Dopo un buco di più di ${r.max_gap_days} giorni la catena riparte dai codici `
      + `iniziali. È successo il ${r.ripartenze.map(giornoBreve).join(", ")}.`);
  }
  $("note").replaceChildren(...note.map((n) => elemento("li", n)));

  tabella(r.giorni);
  grafico(r.giorni);
  $("esporta").disabled = false;
  $("giorno").classList.add("d-none");
  $("scegli").classList.remove("d-none");
}

function tabella(giorni) {
  $("tabella").replaceChildren(...giorni.map((g, i) => {
    const tr = document.createElement("tr");
    tr.dataset.i = i;
    const th = elemento("th");
    th.scope = "row";
    const scegli = elemento("button", g.day, "btn btn-link p-0 giorno");
    scegli.type = "button";
    th.appendChild(scegli);
    if (!g.settled) th.append(" ", elemento("span", "in avviamento", "badge bg-secondary"));
    tr.appendChild(th);
    const o = g.observation;
    for (const v of [o.temperature_c, o.relative_humidity_pct, o.wind_speed_kmh, o.rain_24h_mm]) {
      tr.appendChild(elemento("td", lettura(v), "text-end"));
    }
    const k = g.codes;
    for (const v of [k.ffmc, k.dmc, k.dc, k.isi, k.bui]) {
      tr.appendChild(elemento("td", numero(v), "text-end"));
    }
    tr.appendChild(elemento("td", numero(k.fwi), "text-end fw-bold"));
    const td = elemento("td");
    td.appendChild(elemento("span", etichetta(g.effis_class), `classe classe-${indiceClasse(g.effis_class)}`));
    tr.appendChild(td);
    return tr;
  }));
}

function grafico(giorni) {
  const W = 760, H = 340, m = { l: 44, r: 104, t: 12, b: 40 };
  const t0 = tempo(giorni[0].day), t1 = Math.max(tempo(giorni[giorni.length - 1].day), t0 + 864e5);
  // The axis reaches the top of the class of the highest day, so its band is whole.
  const alto = Math.max(...giorni.map((g) => g.codes.fwi));
  const sopra = classi.map((c) => c.da).find((da) => da > alto);
  const yMax = sopra ?? alto * 1.15;
  const X = (iso) => m.l + (tempo(iso) - t0) / (t1 - t0) * (W - m.l - m.r);
  const Y = (v) => H - m.b - v / yMax * (H - m.t - m.b);
  let svg = "";
  classi.forEach((c, i) => {
    if (c.da >= yMax) return;
    const su = Math.min(classi[i + 1]?.da ?? yMax, yMax);
    svg += `<rect x="${m.l}" y="${Y(su)}" width="${W - m.l - m.r}" height="${Y(c.da) - Y(su)}" class="fascia-${i}"/>`;
    if (Y(c.da) - Y(su) >= 13) {
      svg += `<text x="${W - m.r + 6}" y="${(Y(c.da) + Y(su)) / 2 + 4}">${c.etichetta}</text>`;
    }
    svg += `<text x="${m.l - 6}" y="${Y(c.da) + 4}" text-anchor="end">${lettura(c.da)}</text>`;
  });
  svg += `<text x="${m.l - 6}" y="${Y(yMax) + 4}" text-anchor="end">${lettura(yMax)}</text>
    <line x1="${m.l}" x2="${W - m.r}" y1="${Y(0)}" y2="${Y(0)}" class="asse"/>
    <text x="12" y="${(H - m.b + m.t) / 2}" transform="rotate(-90 12 ${(H - m.b + m.t) / 2})" text-anchor="middle">FWI</text>`;
  const passo = Math.max(1, Math.ceil(giorni.length / 8));
  giorni.forEach((g, i) => {
    if (i % passo) return;
    svg += `<line x1="${X(g.day)}" x2="${X(g.day)}" y1="${H - m.b}" y2="${H - m.b + 5}" class="asse"/>
      <text x="${X(g.day)}" y="${H - m.b + 18}" text-anchor="middle">${giornoBreve(g.day)}</text>`;
  });
  // One line per chain: it breaks where the chain restarted from the start codes.
  let tratto = [];
  const chiudi = () => {
    if (tratto.length > 1) svg += `<polyline points="${tratto.join(" ")}" class="linea"/>`;
    tratto = [];
  };
  for (const g of giorni) {
    if (g.chain_days === 1) chiudi();
    tratto.push(`${X(g.day)},${Y(g.codes.fwi)}`);
  }
  chiudi();
  const r = giorni.length > 120 ? 2.5 : 4;
  giorni.forEach((g, i) => {
    svg += `<circle cx="${X(g.day)}" cy="${Y(g.codes.fwi)}" r="${r}" data-i="${i}" tabindex="0" role="button"
      class="punto${g.settled ? "" : " avviamento"}"><title>${g.day}: FWI ${numero(g.codes.fwi)}, ${etichetta(g.effis_class)}${g.settled ? "" : ", in avviamento"}</title></circle>`;
  });
  $("grafico").innerHTML = svg;
}

function parte(nome, letture, punti, massimo, classe) {
  const riga = elemento("div", undefined, `parte ${classe}`);
  riga.setAttribute("role", "row");
  const etichettaParte = elemento("div", nome, "nome");
  etichettaParte.setAttribute("role", "rowheader");
  if (letture) etichettaParte.appendChild(elemento("span", letture, "letture"));
  const barra = elemento("div", undefined, "barra");
  barra.setAttribute("aria-hidden", "true");
  const segmento = elemento("span", undefined, punti >= 0 ? "su" : "giu");
  segmento.style.width = `${Math.abs(punti) / massimo * 50}%`;
  barra.appendChild(segmento);
  const valore = elemento("div", conSegno(punti), "punti");
  valore.setAttribute("role", "cell");
  riga.append(etichettaParte, barra, valore);
  return riga;
}

function scegliGiorno(i) {
  const g = ultima.giorni[i];
  for (const e of document.querySelectorAll(".scelto")) e.classList.remove("scelto");
  $("tabella").children[i]?.classList.add("scelto");
  $("grafico").querySelector(`circle[data-i="${i}"]`)?.classList.add("scelto");
  $("scegli").classList.add("d-none");
  $("giorno").classList.remove("d-none");
  $("giorno-titolo").textContent = giornoLungo(g.day);
  const avviamento = g.settled ? "" : " Il giorno è in avviamento: i codici di siccità "
    + "riportano ancora in buona parte il loro valore iniziale.";
  const c = g.change;
  if (!c) {
    $("giorno-sintesi").textContent = `FWI ${numero(g.codes.fwi)}, classe ${etichetta(g.effis_class)}. `
      + (i === 0 ? "È il primo giorno della catena: non c'è un giorno prima con cui confrontarlo."
        : "Qui la catena è ripartita dai codici iniziali dopo un buco troppo lungo: non c'è un giorno prima con cui confrontarlo.")
      + avviamento;
    $("barre").replaceChildren();
    $("giorno-somma").textContent = "";
    return;
  }
  const dopoBuco = tempo(g.day) - tempo(c.previous_day) > 864e5
    ? ` Il giorno prima con le quattro letture è il ${giornoBreve(c.previous_day)}: il confronto è con quello.` : "";
  $("giorno-sintesi").replaceChildren(
    `FWI del giorno prima (${giornoBreve(c.previous_day)}): ${numero(c.fwi_previous)} → FWI del giorno: `,
    elemento("strong", numero(g.codes.fwi)),
    ` (classe ${etichetta(g.effis_class)}). Variazione: `,
    elemento("strong", `${conSegno(c.fwi_change)} punti`),
    `.${dopoBuco}${avviamento}`,
  );
  const massimo = Math.max(0.1, Math.abs(c.carry_over), ...c.drivers.map((d) => Math.abs(d.effect)));
  $("barre").replaceChildren(
    parte("La memoria della catena", "con lo stesso meteo del giorno prima", c.carry_over, massimo, "memoria"),
    ...c.drivers.map((d) => {
      const l = LETTURE[d.input];
      return parte(l.nome,
        `${lettura(d[`previous_${l.chiave}`])} ${l.unita} → ${lettura(d[`today_${l.chiave}`])} ${l.unita}`,
        d.effect, massimo, "");
    }),
  );
  $("giorno-somma").textContent = `Memoria ${conSegno(c.carry_over)}, meteo ${conSegno(c.weather)} `
    + `(la somma delle quattro letture): in tutto ${conSegno(c.fwi_change)} punti di FWI. `
    + "Barra a destra: ha alzato l'indice. Barra a sinistra: lo ha abbassato. "
    + "I numeri sono arrotondati a un decimale: la somma può scostarsi di un decimo o due.";
}

function esporta() {
  if (!ultima) return;
  const testa = ["giorno", "temperatura", "umidita", "vento", "pioggia",
    "ffmc", "dmc", "dc", "isi", "bui", "fwi", "classe", "in_avviamento"];
  const righe = ultima.giorni.map((g) => {
    const o = g.observation, k = g.codes;
    return [g.day, o.temperature_c, o.relative_humidity_pct, o.wind_speed_kmh, o.rain_24h_mm,
      k.ffmc, k.dmc, k.dc, k.isi, k.bui, k.fwi, etichetta(g.effis_class), g.settled ? "no" : "si"].join(",");
  });
  const c = ultima.codici_iniziali;
  const testo = [
    `# ${ultima.regola}`,
    `# Calcolato con fwi-chain ${$("versione").textContent}. Codici iniziali: FFMC ${c.ffmc}, DMC ${c.dmc}, DC ${c.dc}. `
      + `Giorni di avviamento: ${ultima.giorni_avviamento}.`,
    ...(ultima.esempio ? ["# ESEMPIO: Gioia del Colle, estate 2025. Meteo Open-Meteo (CC BY 4.0), rianalisi ERA5: non misure di stazione."] : []),
    ...(ultima.saltati.length ? [`# Giorni saltati (lettura non misurata): ${ultima.saltati.join(" ")}`] : []),
    testa.join(","),
    ...righe,
  ].join("\n") + "\n";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([testo], { type: "text/csv;charset=utf-8" }));
  a.download = `diario-fwi_${ultima.sintesi.first_day}_${ultima.sintesi.last_day}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function scelta(evento) {
  const e = evento.target.closest("[data-i]");
  if (!e) return;
  if (evento.type === "keydown") {
    if (evento.key !== "Enter" && evento.key !== " ") return;
    evento.preventDefault();
  }
  scegliGiorno(Number(e.dataset.i));
}

$("carica-esempio").addEventListener("click", caricaEsempio);
$("file").addEventListener("change", leggiFile);
$("calcola").addEventListener("click", calcola);
$("esporta").addEventListener("click", esporta);
$("tabella").addEventListener("click", scelta);
$("grafico").addEventListener("click", scelta);
$("grafico").addEventListener("keydown", scelta);
avvio().catch((e) => errore(`La pagina non riesce a leggere la configurazione: ${e.message}`));
