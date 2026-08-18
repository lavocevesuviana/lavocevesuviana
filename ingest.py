#!/usr/bin/env python3
"""Raccoglie le fonti per La Voce Vesuviana.

Due categorie, tenute rigorosamente separate:

  RASSEGNA  -> altre testate. Si salvano SOLO titolo, link e data.
               Il testo non viene mai scaricato ne' ripubblicato.
  FONTI     -> atti e comunicati della pubblica amministrazione.
               Art. 5 L.633/1941: non sono coperti da diritto d'autore,
               quindi si possono ripubblicare per intero citando la fonte.
"""

import json
import re
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
UA = "Mozilla/5.0 (compatible; LaVoceVesuviana/1.0; +https://lavocevesuviana.it)"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

COMUNI = ["Terzigno", "Boscoreale", "Ottaviano", "Poggiomarino",
          "Somma Vesuviana", "San Giuseppe Vesuviano", "Striano",
          "Boscotrecase", "Pompei", "Torre Annunziata"]

RASSEGNA_FEED = [
    # (nome, feed, solo_locale)  solo_locale=True -> tiene solo i pezzi che
    # nominano uno dei nostri comuni, cosi' le testate larghe non ci sommergono.
    ("VesuvioLive",             "https://www.vesuviolive.it/feed/", False),
    ("Vesuviano News",          "https://www.vesuvianonews.it/feed/", False),
    ("La Provincia Online",     "https://www.laprovinciaonline.info/feed/", False),
    ("Il Fatto Vesuviano",      "https://www.ilfattovesuviano.it/feed/", False),
    ("L'Ora Vesuviana",         "https://www.loravesuviana.it/feed/", False),
    ("Metropolis",              "https://www.metropolisweb.it/feed", False),
    ("Il Mediano",              "https://www.ilmediano.com/feed", False),
    ("Cronache della Campania", "https://www.cronachedellacampania.it/feed", True),
    ("Internapoli",             "https://www.internapoli.it/feed", True),
    ("NapoliToday",             "https://www.napolitoday.it/rss", True),
    ("Positano News",           "https://www.positanonews.it/feed", True),
    ("ANSA Campania",           "https://www.ansa.it/campania/notizie/campania_rss.xml", True),
]

COMUNI_NEWS = [
    ("Ottaviano",    "https://www.comune.ottaviano.na.it/it/news",
     r'href="(https://www\.comune\.ottaviano\.na\.it/it/news/[^"#?]+)"[^>]*class="link-detail">\s*<h1[^>]*>\s*([^<]{12,300}?)\s*<'),
    ("Poggiomarino", "https://www.comune.poggiomarino.na.it/it/novita/comunicati",
     r'href="(/it/novita/page/[^"#?]+)"[^>]*>\s*([^<]{12,200}?)\s*<'),
    ("Poggiomarino", "https://www.comune.poggiomarino.na.it/it/novita/notizie",
     r'href="(/it/novita/page/[^"#?]+)"[^>]*>\s*([^<]{12,200}?)\s*<'),
    ("Somma Vesuviana", "https://www.comune.sommavesuviana.na.it/it/novita/notizie",
     r'href="(/it/novita/page/[^"#?]+)"[^>]*>\s*([^<]{12,200}?)\s*<'),
    ("Somma Vesuviana", "https://www.comune.sommavesuviana.na.it/it/novita/comunicati",
     r'href="(/it/novita/page/[^"#?]+)"[^>]*>\s*([^<]{12,200}?)\s*<'),
]

INGV = ("https://webservices.ingv.it/fdsnws/event/1/query"
        "?starttime={start}&minlatitude=40.70&maxlatitude=40.95"
        "&minlongitude=14.25&maxlongitude=14.60&minmagnitude=1.0&format=text")


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def ripulisci_xml(testo):
    """Alcuni feed (Metropolis) contengono caratteri di controllo e & non
    codificate che fanno fallire il parser. Li normalizziamo prima di leggere."""
    testo = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", testo)
    return re.sub(r"&(?!(?:[a-zA-Z][a-zA-Z0-9]{1,7}|#[0-9]{1,7}|#x[0-9a-fA-F]{1,6});)", "&amp;", testo)


def strip_tags(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


VESUVIANO = ["vesuvi", "circumvesuviana", "monte somma", "miglio d'oro"]


def e_vesuviano(testo):
    """Vero se il pezzo riguarda il nostro territorio, anche senza nominare
    un comune preciso (es. 'allerta sul Vesuvio', 'guasto Circumvesuviana')."""
    t = (testo or "").lower()
    return bool(comuni_citati(testo)) or any(k in t for k in VESUVIANO)


def comuni_citati(testo):
    """Il comune va cercato anche nelle categorie e nello slug dell'indirizzo:
    moltissimi pezzi nominano il paese li' dentro e non nel titolo."""
    t = re.sub(r"[^a-z0-9]+", " ", (testo or "").lower())
    return [c for c in COMUNI if re.sub(r"[^a-z0-9]+", " ", c.lower()) in t]


def rassegna():
    """Titolo + link. Nessun testo: e' una rassegna, non una copia."""
    out = []
    for nome, url, solo_locale in RASSEGNA_FEED:
        try:
            root = ElementTree.fromstring(ripulisci_xml(get(url)))
        except Exception as e:
            print("  ! %-22s %s" % (nome, e))
            continue
        n = 0
        for item in root.iter("item"):
            titolo = strip_tags(item.findtext("title"))
            link = (item.findtext("link") or "").strip()
            if not titolo or not link:
                continue
            categorie = " ".join(c.text or "" for c in item.findall("category"))
            dove = comuni_citati(" ".join([titolo, categorie, link]))
            if solo_locale and not (dove or e_vesuviano(titolo + " " + categorie)):
                continue          # testata larga: teniamo solo il vesuviano
            out.append({
                "titolo": titolo,
                "link": link,
                "fonte": nome,
                "data": (item.findtext("pubDate") or "").strip(),
                "comuni": dove,
            })
            n += 1
        print("  + %-22s %3d titoli" % (nome, n))
    return out


def comuni_avvisi():
    """News dai siti comunali: atti pubblici, ripubblicabili."""
    out = []
    for comune, url, pattern in COMUNI_NEWS:
        try:
            html = get(url)
        except Exception as e:
            print("  ! %-22s %s" % (comune, e))
            continue
        visti, n = set(), 0
        for link, titolo in re.findall(pattern, html):
            titolo = strip_tags(titolo)
            if len(titolo) < 15 or link in visti:
                continue
            visti.add(link)
            if link.startswith("/"):
                link = url.split("/it/")[0] + link
            out.append({"titolo": titolo, "link": link,
                        "fonte": "Comune di " + comune, "comuni": [comune]})
            n += 1
        print("  + %-22s %3d avvisi" % (comune, n))
    return out


def terremoti(giorni=30):
    """INGV, dati aperti. Ogni scossa avvertita sul Vesuvio e' una notizia."""
    start = (datetime.now(timezone.utc) - timedelta(days=giorni)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        testo = get(INGV.format(start=start))
    except Exception as e:
        print("  ! INGV %s" % e)
        return []
    out = []
    for riga in testo.splitlines():
        if riga.startswith("#") or "|" not in riga:
            continue
        p = riga.split("|")
        if len(p) < 13:
            continue
        try:
            out.append({"data": p[1], "lat": float(p[2]), "lon": float(p[3]),
                        "prof": float(p[4]), "magnitudo": float(p[10]),
                        "luogo": p[12].strip(),
                        "link": "https://terremoti.ingv.it/event/" + p[0].strip()})
        except ValueError:
            continue
    out.sort(key=lambda e: e["data"], reverse=True)
    print("  + %-22s %3d eventi (M>=1.0, 30gg)" % ("INGV terremoti", len(out)))
    return out


def accumula(nome, nuovi, chiave="link", tetto=1500):
    """I feed mostrano solo le ultime notizie: se ogni volta ripartissimo da
    zero, i paesi piccoli resterebbero sempre vuoti. Qui uniamo il raccolto di
    oggi all'archivio, senza duplicati, tenendo i piu' recenti in cima."""
    f = DATA / (nome + ".json")
    vecchi = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    visti, uniti = set(), []
    for voce in nuovi + vecchi:            # i nuovi hanno la precedenza
        k = voce.get(chiave)
        if k and k not in visti:
            visti.add(k)
            uniti.append(voce)
    aggiunti = len(uniti) - len(vecchi)
    print("  %-12s %4d in archivio (+%d nuovi)" % (nome, min(len(uniti), tetto), aggiunti))
    return uniti[:tetto]


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    print("RASSEGNA (solo titoli e link)")
    r = rassegna()
    print("FONTI PUBBLICHE (ripubblicabili)")
    c = comuni_avvisi()
    s = terremoti()
    print("ARCHIVIO")
    r = accumula("rassegna", r)
    c = accumula("comuni", c, tetto=800)
    s = accumula("terremoti", s, chiave="link", tetto=400)
    for nome, dati in (("rassegna", r), ("comuni", c), ("terremoti", s)):
        (DATA / (nome + ".json")).write_text(
            json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
