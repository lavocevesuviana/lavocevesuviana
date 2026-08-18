#!/usr/bin/env python3
"""Pubblica sulla Pagina Facebook gli articoli nuovi. Solo articoli NOSTRI.

Servono due variabili d'ambiente (su GitHub: Settings > Secrets > Actions):
  FB_PAGE_ID     l'ID numerico della Pagina
  FB_TOKEN       un Page Access Token di lunga durata
La rassegna non viene mai pubblicata in automatico: quelli sono articoli altrui.
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
SITO = os.environ.get("SITO_URL", "https://lavocevesuviana.pages.dev").rstrip("/")
PAGE, TOKEN = os.environ.get("FB_PAGE_ID"), os.environ.get("FB_TOKEN")
STORICO = BASE / "data" / "pubblicati.json"


def gia_pubblicati():
    return set(json.loads(STORICO.read_text())) if STORICO.exists() else set()


def pubblica(a):
    url = "%s/%s" % (SITO, a["url"])
    testo = a["titolo"]
    if a.get("comune"):
        testo = "%s | %s" % (a["comune"].upper(), testo)
    testo += "\n\n%s…\n\n%s" % (a["sommario"], url)
    dati = urllib.parse.urlencode({"message": testo, "link": url,
                                   "access_token": TOKEN}).encode()
    req = urllib.request.Request(
        "https://graph.facebook.com/v21.0/%s/feed" % PAGE, data=dati)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    if not (PAGE and TOKEN):
        print("FB_PAGE_ID / FB_TOKEN non impostati: salto la pubblicazione.")
        raise SystemExit(0)
    indice = json.loads((BASE / "data" / "indice.json").read_text(encoding="utf-8"))
    fatti = gia_pubblicati()
    nuovi = [a for a in indice if a["url"] not in fatti][:5]   # tetto di sicurezza
    for a in nuovi:
        try:
            esito = pubblica(a)
            fatti.add(a["url"])
            print("pubblicato:", a["titolo"][:60], esito.get("id", ""))
        except Exception as e:
            print("ERRORE su", a["titolo"][:60], "->", e)
    STORICO.write_text(json.dumps(sorted(fatti), ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print("Totale pubblicati storici:", len(fatti))
