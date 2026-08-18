#!/usr/bin/env python3
"""Genera il sito statico de La Voce Vesuviana in site/."""

import json
import re
import hashlib
import os
import shutil
from urllib.parse import quote
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA, ART, STATIC, OUT = BASE / "data", BASE / "articoli", BASE / "static", BASE / "site"

SITO = os.environ.get("SITO_URL", "https://lavocevesuviana.github.io/lavocevesuviana").rstrip("/")
TESTATA = "La Voce Vesuviana"
CLAIM = "Cronaca, politica e vita dei paesi del Vesuvio"
from ingest import COMUNI          # l'elenco dei paesi sta in un posto solo
COMUNI_NAV = ["Terzigno", "Boscoreale", "Ottaviano", "Poggiomarino",
              "Somma Vesuviana", "San Giuseppe Vesuviano", "Pompei",
              "Torre Annunziata", "Torre del Greco", "Ercolano",
              "Castellammare di Stabia", "Nola"]
PER_PAGINA = 60
PONTI_MAX = 3000      # un link condiviso su Facebook deve restare vivo a lungo:
                      # oltre questa soglia la pagina ponte sparirebbe e chi
                      # ci clicca troverebbe un errore.
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


def versione_css():
    """Sigla del foglio di stile, da appendere al collegamento. Cambiando la
    sigla a ogni modifica, il browser e' costretto a riscaricarlo: senza,
    i lettori continuerebbero a vedere la pagina nuova con lo stile vecchio."""
    testo = (STATIC / "style.css").read_bytes()
    return hashlib.sha1(testo).hexdigest()[:8]


def anteprima_social(titolo, descrizione, percorso, immagine=""):
    """Etichette che Facebook e WhatsApp leggono per costruire l'anteprima del
    link. Senza queste, chi incolla l'indirizzo vede solo un rettangolo vuoto."""
    url = "%s/%s" % (SITO, percorso.lstrip("/"))
    figura = immagine if immagine.startswith("http") else "%s/%s" % (SITO, immagine or "social.png")
    return "".join(
        '<meta property="og:%s" content="%s">' % (chiave, escape(valore, True))
        for chiave, valore in (("type", "article"), ("site_name", TESTATA), ("locale", "it_IT"),
                               ("title", titolo), ("description", descrizione),
                               ("url", url), ("image", figura))
    ) + ('<meta name="twitter:card" content="summary_large_image">'
         '<meta name="description" content="%s">' % escape(descrizione, True))


def condivisione(titolo, percorso):
    url = "%s/%s" % (SITO, percorso.lstrip("/"))
    testo = quote("%s — %s" % (titolo, url))
    return """<div class="condividi">
      <span class="etichetta">Condividi</span>
      <a class="wa" href="https://wa.me/?text={testo}" target="_blank" rel="noopener">WhatsApp</a>
      <a class="fb" href="https://www.facebook.com/sharer/sharer.php?u={u}" target="_blank" rel="noopener">Facebook</a>
      <button class="copia" data-url="{url}">Copia link</button>
    </div>""".format(testo=testo, u=quote(url, safe=""), url=escape(url, True))


def guscio(titolo, contenuto, prof=0, social="", canonico=""):
    su = "../" * prof
    return """<!doctype html>
<html lang="it"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titolo}</title>
<link rel="stylesheet" href="{su}style.css?v={ver}">
<link rel="icon" href="{su}favicon.png">
{canonico}{social}
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
  <img class="emblema" src="{su}emblema.png" alt="">
  <p><strong>{t}</strong> — testata in costruzione. Contenuti istituzionali ripresi da atti e
     comunicati della pubblica amministrazione (art. 5 L. 633/1941), con indicazione della fonte.
     La rassegna riporta esclusivamente titoli e collegamenti alle testate originali.</p>
</footer>
<script>
document.addEventListener("click", function (e) {{
  var b = e.target.closest(".copia");
  if (!b) return;
  var url = b.dataset.url, originale = b.dataset.testo || b.textContent;
  b.dataset.testo = originale;
  function esito(ok) {{
    b.textContent = ok ? "Copiato!" : "Premi \u2318C";
    if (!ok) {{ var s = document.createElement("input"); s.value = url;
      b.parentNode.insertBefore(s, b.nextSibling); s.select(); }}
    setTimeout(function () {{
      b.textContent = originale;
      var v = b.nextSibling; if (v && v.tagName === "INPUT") v.remove();
    }}, 2500);
  }}
  // via moderna; se non disponibile o rifiutata, si ripiega sul vecchio metodo
  if (navigator.clipboard && window.isSecureContext) {{
    navigator.clipboard.writeText(url).then(function () {{ esito(true); }},
                                            function () {{ ripiego(); }});
  }} else {{ ripiego(); }}
  function ripiego() {{
    try {{
      var t = document.createElement("textarea");
      t.value = url; t.style.position = "fixed"; t.style.opacity = "0";
      document.body.appendChild(t); t.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(t); esito(ok);
    }} catch (err) {{ esito(false); }}
  }}
}});
</script>
</body></html>""".format(
        titolo=escape(titolo), t=escape(TESTATA), claim=escape(CLAIM), su=su, contenuto=contenuto,
        ver=versione_css(), social=social,
        canonico='<link rel="canonical" href="%s">' % escape(canonico, True) if canonico else "",
        nav='<a class="home" href="%sindex.html">Home</a>' % su
            + '<a class="tutte" href="%srassegna-vesuviana.html">Rassegna</a>' % su
            + "".join('<a href="%scomuni/%s.html">%s</a>' % (su, slug(c), escape(c)) for c in COMUNI_NAV))


def copertina(a):
    """Quando un articolo non ha foto, invece di lasciare un buco disegniamo
    una copertina con i colori della testata e il nome del comune. E' un SVG
    scritto dentro la pagina: nessun file da caricare, nessuna libreria."""
    etichetta = escape((a.get("comune") or TESTATA).upper())
    corpo = escape(a["titolo"])[:78]
    return (
        '<svg class="copertina" viewBox="0 0 1200 430" preserveAspectRatio="xMidYMid slice" '
        'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="%s">'
        '<rect width="1200" height="430" fill="#111"/>'
        '<path d="M760 430 L900 190 L960 250 L1050 130 L1200 330 L1200 430 Z" '
        'fill="#F6D04D" opacity="0.14"/>'
        '<rect x="64" y="150" width="10" height="118" fill="#F6D04D"/>'
        '<text x="98" y="205" fill="#F6D04D" font-family="Archivo Black,Helvetica,Arial" '
        'font-size="46" font-weight="900" letter-spacing="2">%s</text>'
        '<text x="98" y="256" fill="#ffffff" font-family="Helvetica,Arial" '
        'font-size="25" opacity="0.85">%s</text>'
        '<text x="64" y="392" fill="#ffffff" font-family="Helvetica,Arial" font-size="17" '
        'letter-spacing="4" opacity="0.45">LA VOCE VESUVIANA</text>'
        "</svg>" % (etichetta, etichetta, corpo))


def sorgente_foto_assoluta(nome):
    if not nome:
        return ""
    return nome if nome.startswith("http") else "foto/" + nome


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
        foto='<a class="foto%s" href="%s%s">%s</a>' % (
            "" if a.get("foto") else " senza-foto", su, a["url"],
            '<img src="%s" alt="" loading="lazy">' % sorgente_foto(a["foto"], prof)
            if a.get("foto") else copertina(a)),
        occhiello='<p class="occhiello">%s</p>' % escape(a["comune"] or a["occhiello"]) if (a["comune"] or a["occhiello"]) else "")


def ponte_url(r):
    """Indirizzo stabile della pagina ponte: deve restare uguale nel tempo,
    altrimenti i link gia' condivisi su Facebook smetterebbero di funzionare."""
    firma = hashlib.sha1(r["link"].encode()).hexdigest()[:7]
    return "rassegna/%s-%s.html" % (slug(r["titolo"])[:58], firma)


def pagina_ponte(r):
    """Pagina di rimando: titolo, fonte, immagine e un pulsante che porta
    all'originale. Nessuna riga del testo altrui viene ripresa."""
    figura = ('<img class="scatto" src="%s" alt="" onerror="this.remove()">'
              % escape(r["img"], True)) if r.get("img") else ""
    return """<article class="ponte">
      <p class="occhiello">{fonte}</p>
      <h1>{titolo}</h1>
      {figura}
      <p class="avvertenza">Questo articolo &egrave; stato scritto e pubblicato da
        <strong>{fonte}</strong>. La Voce Vesuviana ne segnala il titolo e rimanda
        alla fonte: il testo si legge sul sito che lo ha prodotto.</p>
      <p class="prosegui"><a href="{link}" target="_blank" rel="noopener nofollow">
        Continua a leggere su {fonte}</a></p>
      {condividi}
    </article>""".format(fonte=escape(r["fonte"]), titolo=escape(r["titolo"]),
                         figura=figura, link=escape(r["link"], True),
                         condividi=condivisione(r["titolo"], ponte_url(r)))


def blocco_rassegna(rassegna, n=14, ponti=True, su="", intestazione=True):
    voci = []
    for r in rassegna[:n]:
        try:
            quando = data_lunga(parsedate_to_datetime(r["data"]))
        except Exception:
            quando = ""
        miniatura = ('<img class="miniatura" src="%s" alt="" loading="lazy" '
                     'onerror="this.remove()">' % escape(r["img"], True)) if r.get("img") else ""
        destinazione = ("%s%s" % (su, ponte_url(r))) if (ponti and r.get("ponte")) else r["link"]
        fuori = "" if (ponti and r.get("ponte")) else ' target="_blank" rel="noopener nofollow"'
        voci.append("""<li><a href="{link}"{fuori}>{img}
          <span class="testo"><span class="tit">{titolo}</span>
          <span class="fonte">{fonte}{quando}</span></span></a></li>""".format(
            link=escape(destinazione, True), fuori=fuori, img=miniatura,
            titolo=escape(r["titolo"]), fonte=escape(r["fonte"]),
            quando=" · " + quando if quando else ""))
    if not intestazione:
        return '<section class="rassegna larga"><ul>%s</ul></section>' % "\n".join(voci)
    return """<section class="rassegna">
  <h2 class="sezione"><a href="{su}rassegna-vesuviana.html">Rassegna vesuviana</a></h2>
  <p class="nota">Titoli dalle altre testate del territorio. Il collegamento porta all'articolo originale.</p>
  <ul>{voci}</ul>
  <p class="tutta"><a href="{su}rassegna-vesuviana.html">Vedi tutta la rassegna &rarr;</a></p>
  </section>""".format(su=su, voci="\n".join(voci))


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

    (OUT / "rassegna").mkdir(exist_ok=True)
    for r in rassegna[:PONTI_MAX]:
        r["ponte"] = True
        (OUT / ponte_url(r)).write_text(
            guscio(r["titolo"] + " — " + TESTATA, pagina_ponte(r), prof=1,
                   social=anteprima_social(r["titolo"],
                                           "Segnalato da %s. Il testo si legge sulla fonte." % r["fonte"],
                                           ponte_url(r), r.get("img", "")),
                   canonico=r["link"]),
            encoding="utf-8")

    apertura = ""
    if articoli:
        a = articoli[0]
        apertura = """<article class="apertura">
          {foto}{occhiello}<h1><a href="{url}">{titolo}</a></h1>
          <p class="sommario">{sommario}…</p><p class="meta">{data}</p></article>""".format(
            url=a["url"], titolo=escape(a["titolo"]), sommario=escape(a["sommario"]),
            data=data_lunga(a["dt"]),
            foto='<a class="foto grande%s" href="%s">%s</a>' % (
                "" if a.get("foto") else " senza-foto", a["url"],
                '<img src="%s" alt="">' % sorgente_foto(a["foto"])
                if a.get("foto") else copertina(a)),
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
    (OUT / "index.html").write_text(
        guscio(TESTATA + " — " + CLAIM, home,
               social=anteprima_social(TESTATA, CLAIM, "index.html")), encoding="utf-8")

    for a in articoli:
        pag = """<article class="pezzo">
          {occhiello}<h1>{titolo}</h1><p class="meta">{data}</p>{foto}{corpo}
          {condividi}</article>""".format(
            condividi=condivisione(a["titolo"], a["url"]),
            titolo=escape(a["titolo"]), data=data_lunga(a["dt"]), corpo=a["corpo"],
            foto='<figure class="foto principale"><img src="%s" alt=""></figure>' % sorgente_foto(a["foto"], 1) if a.get("foto") else "",
            occhiello='<p class="occhiello">%s</p>' % escape(a["comune"]) if a["comune"] else "")
        (OUT / a["url"]).write_text(
            guscio(a["titolo"] + " — " + TESTATA, pag, prof=1,
                   social=anteprima_social(a["titolo"], a["sommario"], a["url"],
                                           sorgente_foto_assoluta(a["foto"]))),
            encoding="utf-8")

    # rassegna completa: tutto l'archivio dall'inizio, sfogliato
    pagine_r = max(1, -(-len(rassegna) // PER_PAGINA))
    for n in range(pagine_r):
        fetta = rassegna[n * PER_PAGINA:(n + 1) * PER_PAGINA]
        corpo = '<h1 class="titolo-comune">Rassegna vesuviana</h1>'
        corpo += ('<p class="conteggio">%d titoli raccolti dalle testate del territorio '
                  'dall\'avvio del sito%s. Ogni voce rimanda alla fonte che l\'ha '
                  'pubblicata.</p>' % (len(rassegna),
                                       ", pagina %d di %d" % (n + 1, pagine_r) if pagine_r > 1 else ""))
        corpo += blocco_rassegna(fetta, n=PER_PAGINA, intestazione=False)
        if pagine_r > 1:
            voci = []
            for i in range(pagine_r):
                dove = "rassegna-vesuviana" + ("" if i == 0 else "-%d" % (i + 1)) + ".html"
                voci.append('<a class="%s" href="%s">%d</a>' % ("qui" if i == n else "", dove, i + 1))
            corpo += '<nav class="pagine"><span>Pagine</span>%s</nav>' % "".join(voci)
        nome = "rassegna-vesuviana" + ("" if n == 0 else "-%d" % (n + 1)) + ".html"
        (OUT / nome).write_text(
            guscio("Rassegna vesuviana — " + TESTATA, '<div class="elenco">%s</div>' % corpo),
            encoding="utf-8")

    for c in COMUNI_NAV:
        suoi = [a for a in articoli if a["comune"] == c]
        loro = [r for r in rassegna if c in r.get("comuni", [])]
        atti = [x for x in avvisi if c in x.get("comuni", [])]
        totale = len(suoi) + len(atti) + len(loro)

        # l'archivio non si taglia: si sfoglia. Cosi' cresce senza limite.
        pagine = max(1, -(-max(len(atti), len(loro)) // PER_PAGINA))
        for n in range(pagine):
            fetta_atti = atti[n * PER_PAGINA:(n + 1) * PER_PAGINA]
            fetta_loro = loro[n * PER_PAGINA:(n + 1) * PER_PAGINA]

            corpo = '<h1 class="titolo-comune">%s</h1>' % escape(c)
            corpo += ('<p class="conteggio">%d fra articoli, atti comunali e titoli dalle '
                      'altre testate%s. L\'archivio cresce a ogni aggiornamento.</p>'
                      % (totale, " — pagina %d di %d" % (n + 1, pagine) if pagine > 1 else ""))
            if n == 0:
                corpo += ('<div class="griglia">%s</div>' % "".join(scheda(a, prof=1) for a in suoi)
                          if suoi else
                          '<p class="nota">Ancora nessun articolo nostro su %s.</p>' % escape(c))
            if fetta_atti:
                corpo += blocco_comuni(fetta_atti, n=PER_PAGINA)
            if fetta_loro:
                corpo += blocco_rassegna(fetta_loro, n=PER_PAGINA, su="../")
            if pagine > 1:
                voci = []
                for i in range(pagine):
                    dove = slug(c) + ("" if i == 0 else "-%d" % (i + 1)) + ".html"
                    voci.append('<a class="%s" href="%s">%d</a>'
                                % ("qui" if i == n else "", dove, i + 1))
                corpo += '<nav class="pagine"><span>Pagine</span>%s</nav>' % "".join(voci)

            nome = slug(c) + ("" if n == 0 else "-%d" % (n + 1))
            (OUT / "comuni" / (nome + ".html")).write_text(
                guscio(c + " — " + TESTATA, corpo, prof=1), encoding="utf-8")

    print("Generato: 1 home, %d articoli, %d pagine comune" % (len(articoli), len(COMUNI_NAV)))
    print("  rassegna %d · avvisi %d · eventi sismici %d" % (len(rassegna), len(avvisi), len(sismi)))


if __name__ == "__main__":
    costruisci()
