# La Voce Vesuviana — istruzioni

Costo totale: **0 €**. Nessun hosting da pagare, nessun abbonamento.

## Cosa fa da solo, ogni ora
- raccoglie i titoli di **11 testate** (VesuvioLive, Vesuviano News, La Provincia Online,
  Il Fatto Vesuviano, L'Ora Vesuviana, Metropolis, Il Mediano, Cronache della Campania,
  Internapoli, NapoliToday, ANSA Campania) — solo titolo + link: è una rassegna, non una copia.
  Le testate non vesuviane vengono filtrate e restano solo i pezzi sul nostro territorio
- **accumula**: non riparte da zero a ogni giro, quindi le pagine dei paesi piccoli
  si riempiono con il passare delle settimane
- raccoglie avvisi, bandi e ordinanze dai Comuni di **Ottaviano, Poggiomarino e Somma Vesuviana** — sono atti pubblici, ripubblicabili per legge
- controlla i terremoti INGV sotto il Vesuvio e aggiorna la striscia in cima
- ricostruisce il sito e lo rimette online
- pubblica sulla Pagina Facebook **solo i tuoi articoli**, mai quelli altrui

## Cosa devi fare tu
Due o tre articoli a settimana. Un articolo è un file dentro `articoli/`:

    titolo: Terzigno, il consiglio approva il bilancio tra le proteste
    comune: Terzigno
    data: 2026-08-20
    occhiello: Esclusiva
    foto: consiglio-terzigno.jpg
    ---
    Il testo dell'articolo. **Grassetto** così, *corsivo* così.

    ## Un sottotitolo

    Altro testo.

**Le foto**: carichi l'immagine in `static/foto/` e scrivi il nome del file nella
riga `foto:`. Compare in apertura, nella scheda in home e dentro l'articolo. Se la
foto è già online da qualche parte, puoi incollare direttamente il suo indirizzo.

Salvi il file su GitHub (si fa anche dal telefono, dal browser) e in tre minuti
l'articolo è online e su Facebook.

## Messa in funzione (una volta sola, ~30 minuti)
1. Account gratuito su github.com, nuovo repository **pubblico** chiamato `lavocevesuviana`.
2. Carichi questa cartella (Add file → Upload files).
3. Settings → Pages → Source: **GitHub Actions**. Il sito nasce su
   `https://TUONOME.github.io/lavocevesuviana`.
4. Per Facebook: Settings → Secrets and variables → Actions, aggiungi
   `FB_PAGE_ID` e `FB_TOKEN`. Finché non li metti, il sito funziona lo stesso
   e il passaggio Facebook viene semplicemente saltato.
5. Variabile `SITO_URL` con l'indirizzo del sito.

## Comandi in locale
    python3 ingest.py    # riscarica le fonti
    python3 build.py     # rigenera il sito in site/

## Regole che il progetto rispetta
- degli articoli altrui si pubblicano solo titolo e collegamento
- gli atti della pubblica amministrazione si ripubblicano citando l'ente (art. 5 L. 633/1941)
- su Facebook finiscono in automatico solo gli articoli scritti da noi
