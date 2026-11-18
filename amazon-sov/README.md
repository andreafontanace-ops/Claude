# amazon-sov · share of voice degli integratori di ferro su Amazon.it

Cerca su Amazon.it una lista di keyword (integratore ferro, ferritina, ferro bisglicinato, …), legge le
pagine dei risultati e classifica **prodotti**, **marchi** e **produttori** per *share of voice* (SoV):
quanta parte della visibilità nei risultati occupano, pesando di più le prime posizioni e separando
posizioni organiche e annunci. Per ogni prodotto indica anche la **formulazione**: la forma (compresse,
capsule, gocce, bustine…) e il tipo di ferro (bisglicinato, liposomiale, sucrosomiale…).

Produce un report HTML, quattro CSV pronti per Excel e uno storico SQLite per confrontare un'esecuzione
con la precedente.

## Installazione

Serve Python 3.11 o successivo.

```bash
cd amazon-sov
```

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -e ".[browser,dev]"
```

```bash
playwright install chromium
```

## Uso

### 1. Crawl automatico

```bash
amazon-sov crawl
```

Si apre una finestra del browser che cerca le keyword di `config.toml` una dopo l'altra, con una pausa
casuale di 8–15 secondi tra le pagine. Le 13 keyword di default su 2 pagine richiedono circa 5 minuti.
Alla fine nel terminale compare la classifica e in `reports/<esecuzione>/` trovi report e CSV.

Se Amazon mostra un captcha, il crawler si ferma: lo risolvi nella finestra del browser, premi Invio
nel terminale e il crawl riprende. Non ci sono trucchi per aggirare i controlli di Amazon.

Opzioni utili:

```bash
amazon-sov crawl --keyword "ferritina" --keyword "ferro bisglicinato" --pages 1
```

```bash
amazon-sov crawl --enrich-brands 20
```

Alla fine del crawl il programma apre alcune pagine prodotto per leggere marchio, produttore e forma:
quelle dei prodotti di ferro il cui marchio non si legge nei risultati e, per ogni marchio di cui non
conosce ancora il produttore, quella del suo prodotto più visibile (il produttore trovato vale per
tutto il marchio). Ne apre al massimo 40 per esecuzione: il numero si cambia con `product_pages` in
`config.toml` o con `--product-pages N` (`0` = mai). Quello che trova resta in archivio, quindi dalla
seconda esecuzione le pagine da aprire sono poche.

### 2. Pagine salvate a mano (senza automazione)

Cerca su Amazon dal tuo browser, salva ogni pagina dei risultati (Ctrl+S / Cmd+S) in una cartella,
poi:

```bash
amazon-sov parse cartella-con-le-pagine/
```

La keyword e il numero di pagina vengono letti dalla pagina stessa. Se non ci riesce, chiama i file
`keyword-con-trattini__p1.html`, `…__p2.html`.

### 3. Altri comandi

```bash
amazon-sov report
```

Rigenera report e CSV dell'ultima esecuzione (o di `--run ID`) con la configurazione attuale: utile dopo
aver aggiunto alias di marchio o correzioni.

```bash
amazon-sov brands
```

Completa marchi e produttori dell'ultima esecuzione senza rifare le ricerche: apre le pagine prodotto
che servono (al massimo 80, `--max N`) e rigenera il report. Si può lanciare più volte: riprende da
dove era rimasto.

```bash
amazon-sov inspect
```

Mostra cosa il parser estrae dalla prima pagina dell'ultima esecuzione (oppure da un file indicato:
`amazon-sov inspect percorso/pagina.html`): posizione, annuncio sì/no, ASIN, marchio e da dove viene,
prezzo, valutazione, recensioni, acquisti del mese scorso, badge. È il primo controllo da fare se i
numeri sembrano strani. Con `--html` aggiunge l'HTML ridotto dei risultati senza riga del marchio: su
Mac `amazon-sov inspect --html | pbcopy` lo copia negli appunti per mandarlo a chi sistema il parser.

```bash
amazon-sov runs
```

```bash
amazon-sov update
```

Scarica da GitHub l'ultima versione del programma e la installa al posto di quella vecchia. Dati e
report restano dove sono; se le impostazioni cambiano, le tue precedenti vengono salvate in
`config.backup.toml`.

## Come si calcola la share of voice

Per ogni keyword ogni risultato riceve un **peso per posizione** che scende man mano che si va giù
nella pagina. Di default è `1 / posizione` (la posizione 1 vale 1, la 2 vale 0,5, la 10 vale 0,1),
che approssima la distribuzione dei clic.

- **SoV di un prodotto su una keyword** = somma dei pesi delle posizioni che occupa ÷ somma dei pesi
  di tutte le posizioni lette per quella keyword.
- **SoV complessiva** = media delle SoV per keyword, pesata con il `weight` di ciascuna keyword. Se
  metti i volumi di ricerca mensili come pesi, le keyword più cercate contano di più.
- **SoV di un marchio** = somma delle SoV dei suoi prodotti. Lo stesso vale per **produttore**, **forma**
  e **tipo di ferro**. Per forme e tipi di ferro il report mostra la quota tra i soli prodotti di ferro.

| Colonna | Significato |
|---|---|
| SoV totale | quota della visibilità su tutti gli slot, organici e sponsorizzati |
| SoV organica | quota calcolata solo sui risultati organici, con la posizione organica |
| SoV ads | quota calcolata solo sui risultati sponsorizzati |
| % da ads | quanta parte della visibilità del prodotto o marchio viene da annunci |
| Top 10 | quota dei primi 10 slot occupati, media sulle keyword |
| Miglior pos. | migliore posizione organica raggiunta su tutte le keyword |

I prodotti che non sono integratori di ferro (per esempio vitamina D o multivitaminici «senza ferro»)
restano nel denominatore, perché occupano spazio reale nella pagina. Sono raggruppati alla voce
«Prodotti non di ferro» e non entrano nella classifica. Con `--denominator relevant` la SoV è invece
calcolata sui soli integratori di ferro. L'ordine della classifica non cambia, cambia solo la scala.

### Produttore

Amazon non mostra il produttore nei risultati di ricerca: si legge nella pagina prodotto, in «Dettagli
prodotto» → Produttore (l'indirizzo viene tolto). Ordine di priorità:

1. la correzione per ASIN in `[manufacturers.asin_overrides]`;
2. il produttore del marchio in `[manufacturers.by_brand]`;
3. la pagina prodotto;
4. un altro prodotto dello stesso marchio di cui si conosce il produttore.

Lo stesso produttore scritto in modi diversi («PharmaNutra S.p.A.», «PHARMANUTRA SPA») viene unito.

### Formulazione

Si ricava dal titolo con le regole di `[formulation.forms]` e `[formulation.iron_types]`. Se il titolo
non dice la forma, si usa la «Forma del prodotto» della pagina prodotto, quando è stata letta. Le regole
si possono cambiare e ampliare in `config.toml`.

### Marchio

Per ogni prodotto il marchio viene preso, in ordine di priorità, da:

1. la correzione manuale in `[brands.asin_overrides]`;
2. la riga del marchio sopra il titolo nei risultati;
3. la pagina prodotto (letta in automatico alla fine del crawl o con `amazon-sov brands`);
4. un alias di `[brands.aliases]` trovato nel titolo;
5. la prima parola del titolo, se non è una parola generica come «Integratore» o «Ferro».

In fondo al report vedi quanta visibilità viene da ciascuna fonte e l'elenco «Marchi da verificare».
Se restano prodotti sconosciuti, lancia `amazon-sov brands` oppure scrivi il marchio in
`[brands.asin_overrides]` e lancia `amazon-sov report`.

## Configurazione (`config.toml`)

- `[[keywords]]`: le ricerche da monitorare e il loro peso.
- `[crawl]`: numero di pagine, pause, tetto di pagine per esecuzione, browser visibile o no.
- `[scoring]`: curva dei pesi (`zipf`, `dcg`, `flat`, `table`), taglio ai primi N risultati, peso dei
  widget Sponsored Brands (di default sono registrati ma esclusi dal punteggio).
- `[relevance]`: termini che rendono un prodotto «integratore di ferro» e termini che lo escludono.
- `[brands]`: alias dei marchi e correzioni per ASIN.
- `[manufacturers]`: produttore per marchio e correzioni per ASIN.
- `[formulation]`: regole per forma e tipo di ferro.
- `[output] csv_dialect`: `excel-it` usa `;` e la virgola decimale, `standard` usa `,` e il punto.

## File prodotti

```
data/sov.sqlite                       storico di tutte le esecuzioni
data/html/<esecuzione>/*.html         pagine scaricate (per ricontrollare o rianalizzare)
data/browser-profile/                 profilo del browser del crawler
reports/<esecuzione>/report.html      report
reports/<esecuzione>/sov_marchi.csv   classifica marchi
reports/<esecuzione>/sov_prodotti.csv classifica prodotti (con produttore, forma e tipo di ferro)
reports/<esecuzione>/sov_produttori.csv classifica produttori
reports/<esecuzione>/sov_forme.csv    quota per forma
reports/<esecuzione>/sov_tipi_ferro.csv quota per tipo di ferro
reports/<esecuzione>/sov_keyword_marchi.csv  SoV di ogni marchio per keyword
reports/<esecuzione>/serp.csv         ogni risultato letto, riga per riga
```

## Limiti da conoscere

- **Termini di Amazon.** Le condizioni d'uso di Amazon vietano la raccolta automatica di dati dal sito.
  Questo strumento è pensato per analisi occasionali a basso volume, con pause umane. Per un
  monitoraggio continuo conviene una fonte autorizzata: le API di Amazon per gli affiliati, oppure
  servizi di dati SERP Amazon come DataForSEO, Traject Data (Rainforest API) o Keepa. Il calcolo della
  SoV di questo progetto si può applicare anche a quei dati.
- **Risultati personalizzati.** Annunci e ordine dei risultati cambiano con l'ora, la località di
  consegna e l'account. Non fare login su Amazon nel browser del crawler e confronta esecuzioni fatte
  nelle stesse condizioni.
- **Markup che cambia.** Amazon modifica spesso l'HTML. Il parser ha più selettori di riserva per ogni
  campo, ma se un campo risulta vuoto, controlla con `amazon-sov inspect` su una pagina salvata.
- **Varianti.** Formati diversi dello stesso prodotto hanno ASIN diversi e sono contati separatamente.
  A livello di marchio si sommano.

## Test

```bash
python -m pytest
```

Le pagine in `tests/fixtures/` sono costruite a mano sulla struttura delle pagine di Amazon. Non sono
copie di pagine reali.
