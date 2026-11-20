# Vetrina · share of voice per l'e-commerce

Servizio web costruito sul calcolo di [amazon-sov](../amazon-sov): iscrizione, dashboard con più
categorie e più siti, raccolte automatiche a frequenza legata al piano, avvisi e scaricamento dei
dati in Excel, CSV e HTML.

## Come funziona

- **Dati condivisi.** Un *feed* è una categoria su un sito (es. Ferro su Amazon.it). Si raccoglie una
  volta sola per tutti i clienti che lo seguono; la frequenza è la più alta tra i loro piani.
  Chi si iscrive trova subito lo storico.
- **Avvio guidato.** Dopo l'iscrizione: 1) scegli categorie e siti; 2) *facoltativo* indica i tuoi
  marchi e qualche concorrente (la classifica comprende comunque tutti i marchi; ti suggeriamo quelli
  più visibili). Parte subito la prima raccolta.
- **Dashboard.** Panoramica con un riquadro per feed; dettaglio con andamento, classifica dei marchi
  (organica / annunci, variazione) e prodotti più visibili con la formulazione.
- **Avvisi.** Dopo ogni raccolta: un mio marchio perde quota (soglia regolabile), scende di
  posizione, un concorrente entra nei primi 3, un marchio nuovo entra nei primi 10. Nella piattaforma
  e, se è configurato un server SMTP, via email.
- **Scarica.** Excel (fogli Marchi, Prodotti, Andamento, Info), CSV per tabella, pagina HTML autonoma.
- **Piani** (in `sovweb/plans.py`): Prova 14 giorni, Base 129 €/mese, Pro 449 €/mese, Enterprise su
  misura. Limiti su categorie, siti, frequenza, utenti, storico, scaricamento.

## Fonte dei dati

`SOV_DATA_PROVIDER`:
- `demo`: dati **inventati** per sviluppo e dimostrazioni (marchi di fantasia; la dashboard lo dice);
  in produzione è bloccato;
- `none`: nessuna raccolta automatica; i dati arrivano dall'API `POST /api/ingest`
  (token `SOV_INGEST_TOKEN`), per esempio dal crawler amazon-sov eseguito in locale.

Con il crawler amazon-sov il collegamento è già pronto: `amazon-sov push` (vedi il README di
amazon-sov). Per vedere solo dati veri avvia la piattaforma con `SOV_DATA_PROVIDER=none`, altrimenti i
dati dimostrativi si mescolano a quelli caricati.

Per la raccolta automatica in produzione serve un fornitore di dati SERP con licenza: si aggiunge in
`sovweb/providers.py` implementando `Provider.fetch` (restituisce i risultati di una keyword nell'ordine
del sito). Il resto (calcolo, storico, avvisi, dashboard) non cambia.

Formato di `POST /api/ingest`:

```json
{"category": "ferro", "site": "amazon-it",
 "results": {"integratore ferro": [{"id": "B0...", "title": "...", "brand": "...", "sponsored": false,
                                    "price": 12.9, "rating": 4.5, "reviews": 1200}]}}
```

## Avvio in locale

Dalla cartella che contiene `amazon-sov/` e `sov-web/`:

```bash
pip install -e amazon-sov -e "sov-web[dev]"
```

```bash
cd sov-web && uvicorn sovweb.app:create_app --factory --reload
```

In un altro terminale, le raccolte automatiche:

```bash
cd sov-web && python -m sovweb.worker
```

Apri http://localhost:8000 e registrati. Test: `python -m pytest`.

## Amministrazione

L'amministratore ha accesso completo (piano «Gratuito – accesso completo», senza limiti né scadenza)
e la pagina **/admin**: elenco degli spazi, cambio di piano, creazione di spazi nuovi. Il piano
gratuito non compare nella pagina dei prezzi: lo assegna solo l'amministratore.

```bash
python -m sovweb.admin crea-admin tua@email.it
```

```bash
python -m sovweb.admin spazio "Nome azienda" utente@azienda.it gratuito
```

Altri comandi: `piano EMAIL PIANO` (cambia piano), `elenco` (elenca gli spazi).

## In produzione

`docker-compose.yml` avvia Postgres, il sito (4 processi) e il worker. Davanti serve un proxy HTTPS.

```bash
cp sov-web/.env.example sov-web/.env
```

```bash
docker compose -f sov-web/docker-compose.yml --env-file sov-web/.env up -d --build
```

Per crescere: più processi `web` dietro il bilanciatore (non hanno stato: la sessione è nel cookie
firmato) e più `worker` (su Postgres si dividono i feed senza pestarsi i piedi). Il carico vero è la
raccolta dati, non le pagine.

Da fare prima di aprire al pubblico: pagamenti (Stripe), reset della password e verifica email,
inviti per i colleghi dello stesso spazio, privacy policy e termini di servizio, backup del database,
monitoraggio. La versione Postgres non è ancora stata provata (i test girano su SQLite).
