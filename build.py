#!/usr/bin/env python3
"""Genera il sito statico de La Voce Vesuviana in site/."""

import json
import re
import shutil
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA, ART, STATIC, OUT = BASE / "data", BASE / "articoli", BASE / "static", BASE / "site"

TESTATA = "La Voce Vesuviana"
CLAIM = "Cronaca, politica e vita dei paesi del Vesuvio"
COMUNI_NAV = ["Terzigno", "Boscoreale", "Ottaviano", "Poggiomarino",
              "Somma Vesuviana", "San Giuseppe Vesuviano", "Pompei"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def leggi_json(nome):
    f = DATA / (nome + ".json")
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def data_lunga(dt):
    return "%d %s %d" % (dt.day, MESI[dt.month - 1], dt.year)


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")[:70]


def md(testo):
    """Markdown minimo: titoletti, grassetto, corsivo, link, paragrafi."""
    out = []
    for blocco in re.split(r"\n\s*\n", testo.strip()):
        b = escape(blocco.strip())
        b = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', b)
        b = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", b)
        b = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", b)
        if b.startswith("## "):
            out.append("<h2>%s</h2>" % b[3:])
        else:
            out.append("<p>%s</p>" % b.replace("\n", "<br>"))
    return "\n".join(out)


def carica_articoli():
    """Legge articoli/*.md con intestazione chiave: valore, poi --- , poi testo."""
    articoli = []
    for f in sorted(ART.glob("*.md")):
        grezzo = f.read_text(encoding="utf-8")
        testa, _, corpo = grezzo.partition("\n---\n")
        meta = {}
        for riga in testa.splitlines():
            if ":" in riga:
                k, _, v = riga.partition(":")
                meta[k.strip().lower()] = v.strip()
        try:
            dt = datetime.strptime(meta.get("data", ""), "%Y-%m-%d")
        except ValueError:
            dt = datetime.fromtimestamp(f.stat().st_mtime)
        articoli.append({
            "titolo": meta.get("titolo", f.stem),
            "occhiello": meta.get("occhiello", ""),
            "comune": meta.get("comune", ""),
            "foto": meta.get("foto", ""),
            "dt": dt,
            "url": "articoli/%s-%s.html" % (dt.strftime("%Y-%m-%d"), slug(meta.get("titolo", f.stem))),
            "corpo": md(corpo or grezzo),
            "sommario": re.sub(r"<[^>]+>", "", md(corpo or grezzo))[:190],
        })
    articoli.sort(key=lambda a: a["dt"], reverse=True)
    return articoli


def guscio(titolo, contenuto, prof=0):
    su = "../" * prof
    return """<!doctype html>
<html lang="it"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titolo}</title>
<link rel="stylesheet" href="{su}style.css">
</head><body>
<header class="testata">
  <a class="marchio" href="{su}index.html">
    <img src="{su}logo.png" alt="{t}" onerror="this.replaceWith(document.getElementById('wm').content.cloneNode(true))">
    <template id="wm"><span class="wordmark"><b>LA VOCE</b><i>VESUVIANA</i></span></template>
  </a>
  <p class="claim">{claim}</p>
</header>
<nav class="comuni">{nav}</nav>
<main>{contenuto}</main>
<footer>
  <p><strong>{t}</strong> — testata in costruzione. Contenuti istituzionali ripresi da atti e
     comunicati della pubblica amministrazione (art. 5 L. 633/1941), con indicazione della fonte.
     La rassegna riporta esclusivamente titoli e collegamenti alle testate originali.</p>
</footer>
</body></html>""".format(
        titolo=escape(titolo), t=escape(TESTATA), claim=escape(CLAIM), su=su, contenuto=contenuto,
        nav="".join('<a href="%scomuni/%s.html">%s</a>' % (su, slug(c), escape(c)) for c in COMUNI_NAV))


def sorgente_foto(nome, prof=0):
    """Accetta sia un file dentro static/foto/ sia un indirizzo completo."""
    if not nome:
        return ""
    return nome if nome.startswith("http") else "%sfoto/%s" % ("../" * prof, nome)


def scheda(a, prof=0):
    su = "../" * prof
    return """<article class="scheda">
  {foto}
  {occhiello}
  <h3><a href="{su}{url}">{titolo}</a></h3>
  <p class="sommario">{sommario}…</p>
  <p class="meta">{data}</p>
</article>""".format(
        su=su, url=a["url"], titolo=escape(a["titolo"]), sommario=escape(a["sommario"]),
        data=data_lunga(a["dt"]),
        foto='<a class="foto" href="%s%s"><img src="%s" alt="" loading="lazy"></a>' % (
            su, a["url"], sorgente_foto(a["foto"], prof)) if a.get("foto") else "",
        occhiello='<p class="occhiello">%s</p>' % escape(a["comune"] or a["occhiello"]) if (a["comune"] or a["occhiello"]) else "")


def blocco_rassegna(rassegna, n=14):
    voci = []
    for r in rassegna[:n]:
        try:
            quando = data_lunga(parsedate_to_datetime(r["data"]))
        except Exception:
            quando = ""
        voci.append("""<li><a href="{link}" target="_blank" rel="noopener nofollow">{titolo}</a>
          <span class="fonte">{fonte}{quando}</span></li>""".format(
            link=escape(r["link"], True), titolo=escape(r["titolo"]),
            fonte=escape(r["fonte"]), quando=" · " + quando if quando else ""))
    return """<section class="rassegna">
  <h2 class="sezione">Rassegna vesuviana</h2>
  <p class="nota">Titoli dalle altre testate del territorio. Il collegamento porta all'articolo originale.</p>
  <ul>%s</ul></section>""" % "\n".join(voci)


def blocco_comuni(avvisi, n=12):
    voci = ["""<li><a href="{link}" target="_blank" rel="noopener">{titolo}</a>
             <span class="fonte">{fonte}</span></li>""".format(
        link=escape(a["link"], True), titolo=escape(a["titolo"]), fonte=escape(a["fonte"]))
        for a in avvisi[:n]]
    return """<section class="istituzionale">
  <h2 class="sezione">Dai Comuni</h2>
  <p class="nota">Avvisi, bandi e ordinanze pubblicati dagli enti. Atti pubblici, liberamente ripubblicabili.</p>
  <ul>%s</ul></section>""" % "\n".join(voci)


def blocco_sismico(eventi):
    if not eventi:
        return '<aside class="sismo quieto"><b>Vesuvio</b> nessuna scossa di magnitudo ≥ 1.0 negli ultimi 30 giorni</aside>'
    e = eventi[0]
    quando = e["data"][:16].replace("T", " ore ")
    return ('<aside class="sismo"><b>Ultima scossa</b> magnitudo {m:.1f} — {luogo}, '
            'profondità {p:.0f} km · {quando} · <a href="{link}" target="_blank" rel="noopener">dati INGV</a>'
            ' <span class="conta">{n} eventi negli ultimi 30 giorni</span></aside>').format(
        m=e["magnitudo"], luogo=escape(e["luogo"]), p=e["prof"], quando=quando,
        link=escape(e["link"], True), n=len(eventi))


def costruisci():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "articoli").mkdir(parents=True)
    (OUT / "comuni").mkdir(parents=True)
    for f in STATIC.glob("*"):
        if f.is_dir():
            shutil.copytree(f, OUT / f.name, dirs_exist_ok=True)
        else:
            shutil.copy(f, OUT / f.name)

    articoli = carica_articoli()
    rassegna, avvisi, sismi = leggi_json("rassegna"), leggi_json("comuni"), leggi_json("terremoti")

    apertura = ""
    if articoli:
        a = articoli[0]
        apertura = """<article class="apertura">
          {foto}{occhiello}<h1><a href="{url}">{titolo}</a></h1>
          <p class="sommario">{sommario}…</p><p class="meta">{data}</p></article>""".format(
            url=a["url"], titolo=escape(a["titolo"]), sommario=escape(a["sommario"]),
            data=data_lunga(a["dt"]),
            foto='<a class="foto grande" href="%s"><img src="%s" alt=""></a>' % (
                a["url"], sorgente_foto(a["foto"])) if a.get("foto") else "",
            occhiello='<p class="occhiello">%s</p>' % escape(a["comune"]) if a["comune"] else "")
    else:
        apertura = ('<article class="apertura vuota"><h1>Il primo articolo è tuo</h1>'
                    '<p class="sommario">Aggiungi un file in <code>articoli/</code> e comparirà qui in apertura.</p></article>')

    home = """{sismo}
<div class="colonne">
  <div class="principale">{apertura}<div class="griglia">{schede}</div>{comuni}</div>
  <div class="laterale">{rassegna}</div>
</div>""".format(sismo=blocco_sismico(sismi), apertura=apertura,
                 schede="".join(scheda(a) for a in articoli[1:7]),
                 comuni=blocco_comuni(avvisi), rassegna=blocco_rassegna(rassegna))
    (OUT / "index.html").write_text(guscio(TESTATA + " — " + CLAIM, home), encoding="utf-8")

    for a in articoli:
        pag = """<article class="pezzo">
          {occhiello}<h1>{titolo}</h1><p class="meta">{data}</p>{foto}{corpo}</article>""".format(
            titolo=escape(a["titolo"]), data=data_lunga(a["dt"]), corpo=a["corpo"],
            foto='<figure class="foto principale"><img src="%s" alt=""></figure>' % sorgente_foto(a["foto"], 1) if a.get("foto") else "",
            occhiello='<p class="occhiello">%s</p>' % escape(a["comune"]) if a["comune"] else "")
        (OUT / a["url"]).write_text(guscio(a["titolo"] + " — " + TESTATA, pag, prof=1), encoding="utf-8")

    for c in COMUNI_NAV:
        suoi = [a for a in articoli if a["comune"] == c]
        loro = [r for r in rassegna if c in r.get("comuni", [])]
        atti = [x for x in avvisi if c in x.get("comuni", [])]
        corpo = '<h1 class="titolo-comune">%s</h1>' % escape(c)
        corpo += ('<div class="griglia">%s</div>' % "".join(scheda(a, prof=1) for a in suoi)
                  if suoi else '<p class="nota">Ancora nessun articolo nostro su %s.</p>' % escape(c))
        if atti:
            corpo += blocco_comuni(atti, n=20)
        if loro:
            corpo += blocco_rassegna(loro, n=20)
        (OUT / "comuni" / (slug(c) + ".html")).write_text(
            guscio(c + " — " + TESTATA, corpo, prof=1), encoding="utf-8")

    (DATA / "indice.json").write_text(json.dumps(
        [{"titolo": a["titolo"], "url": a["url"], "sommario": a["sommario"],
          "comune": a["comune"], "data": a["dt"].strftime("%Y-%m-%d")} for a in articoli],
        ensure_ascii=False, indent=1), encoding="utf-8")

    print("Generato: 1 home, %d articoli, %d pagine comune" % (len(articoli), len(COMUNI_NAV)))
    print("  rassegna %d · avvisi %d · eventi sismici %d" % (len(rassegna), len(avvisi), len(sismi)))


if __name__ == "__main__":
    costruisci()
