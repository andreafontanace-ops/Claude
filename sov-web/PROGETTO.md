# Progetto Vetrina · stato e piano di lavoro

Documento tenuto aggiornato a ogni passo (project manager: Claude). Nome «Vetrina» provvisorio.

## Obiettivo
Piattaforma web (SaaS) di share of voice per l'e-commerce: marchi propri e concorrenti su Amazon e
sugli e-commerce rilevanti, nel tempo, con avvisi ed export. Molto più economica delle suite
enterprise (Skai ~114.000 $/anno, Pacvue 1.000–2.500 $/mese, DataHawk da 2.400 $/anno).

## Decisioni prese
- Prodotto web in abbonamento, non app da installare.
- Due tipi di account: **Azienda** e **Agenzia** (spazi cliente separati, report con logo).
- Il prezzo dipende da brand monitorati, siti, keyword (giornaliere + «sorvegliate» orarie), storico,
  utenti. Concorrenti sempre illimitati.
- Account amministratore con accesso completo; piano nascosto «Gratuito – accesso completo» (Alfasigma
  in prova gratuita).
- Dati da un fornitore con licenza (candidato: DataForSEO); niente aggiramento dei blocchi dei siti.
- Hosting candidato: Render (Francoforte) + Cloudflare; pagamenti Stripe + fatturazione elettronica
  SdI (es. Fatture in Cloud).

## In sospeso (servono decisioni o azioni dell'utente)
- [ ] Conferma del listino proposto: Azienda 49 / 149 / 399 €, Agenzia 249 / 599 € al mese.
- [ ] Nome definitivo e verifica del marchio su TMview; poi acquisto del dominio.
- [ ] Partita IVA o società (commercialista) — necessaria prima di incassare.
- [ ] Giuslavorista: contratto Alfasigma (proprietà dello strumento, riservatezza, conflitto di interessi).
- [ ] Informare il responsabile in Alfasigma prima di caricare dati aziendali.

## Fasi

### Fase 1 · codice pronto per l'ambiente di prova (Claude)
- [x] Crawler amazon-sov collegato alla piattaforma (`amazon-sov push`)
- [x] Amministrazione, piano gratuito, CLI `python -m sovweb.admin`
- [x] Sicurezza: intestazioni HTTP (CSP, HSTS, anti-iframe), HTTPS forzato, limite ai tentativi, sessioni chiuse al cambio password, registro di sicurezza
- [x] Recupero password e verifica dell'email (link firmati a scadenza, invio via SMTP)
- [x] Ambiente «staging» (dati dimostrativi ammessi, avviso visibile) oltre a «production»
- [x] Postgres provato davvero (tutti i test e aggiornamento di un database esistente)
- [x] Configurazione Render (`render.yaml` nella radice del repository): sito, worker, database, controllo di salute — simulata in locale, non ancora pubblicata
- [ ] Nuovo listino Azienda/Agenzia e spazi cliente per le agenzie (dopo la conferma dei prezzi)
- [ ] Sito pubblico rifatto: home, «Per le aziende», «Per le agenzie», prezzi con confronto
- [ ] Stripe in modalità di prova (checkout, portale clienti, blocco per mancato pagamento)
- [ ] Fornitore dati (DataForSEO): raccolta autonoma dal server
- [ ] Autenticazione a due fattori per gli amministratori
- [ ] Bozze legali: privacy, termini, accordo sul trattamento dati (da far rivedere a un avvocato)

### Fase 2 · account e messa online di prova (utente guidato passo passo)
- [ ] Account Render, collegamento al repository GitHub, pubblicazione del blueprint
- [ ] Variabili segrete (chiave di sessione, token, SMTP) inserite in Render
- [ ] Provider email (Brevo o Postmark) e dominio mittente
- [ ] Indirizzo di prova (sottodominio Render) → poi dominio vero e Cloudflare

### Fase 3 · beta gratuita (4–6 settimane)
- [ ] Alfasigma + 2–3 aziende/agenzie amiche, dati veri
- [ ] Raccolta riscontri e correzioni

### Fase 4 · apertura al pubblico
- [ ] Pagamenti veri, fatturazione elettronica, testi legali definitivi, listino pubblico

## Registro
- 2026-11-20 · Prototipo sov-web, collegamento crawler, amministrazione e piano gratuito.
- 2026-11-20 · Avvio Fase 1 per l'ambiente di prova.
- 2026-11-20 · Sicurezza, recupero password, verifica email, ambiente staging, Postgres, blueprint Render.
  Prossimo: Fase 2 (account Render, guidato), poi listino Azienda/Agenzia e Stripe in prova.
