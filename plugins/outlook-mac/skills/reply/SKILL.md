---
name: reply
description: Prepara la risposta a un'email di Outlook sul Mac nello stile dell'utente. Prima la mostra in chat e, dopo l'ok, la salva come bozza in Outlook. Usala per «rispondi a…», «prepara una risposta per…», «scrivi a Mario che…».
argument-hint: "<a chi / quale email> [cosa rispondere]"
---

# Risposta a un'email

Segui le regole della skill `outlook`.

## 1. Trova il messaggio
- Se hai un id, usa `read_message`.
- Altrimenti cerca con `search_messages` (nome, indirizzo o parole dell'oggetto; se non trovi nulla, prova `search_body: true` o `since_days: 90`).
- Se ci sono più candidati plausibili, mostrali (data, mittente, oggetto) e chiedi quale.

## 2. Contesto
- Leggi il messaggio completo con `read_message`.
- Se fa parte di una conversazione, cerca l'oggetto (senza «Re:/R:/I:/Fwd:») per vedere i messaggi precedenti, comprese le risposte già inviate dall'utente.

## 3. Stile
Leggi `STILE-EMAIL.md`. Se non esiste, crealo prima di scrivere:
1. `list_messages` con `folder: "sent"` e `limit: 40`;
2. leggi 8–10 email scritte davvero dall'utente (salta inoltri, risposte di una riga e messaggi automatici);
3. annota in `STILE-EMAIL.md`: lingue usate; saluti iniziali e finali per contesto (colleghi, clienti, fornitori); tu/Lei; lunghezza tipica; formule ricorrenti; firma; cose da evitare;
4. mostra all'utente un riassunto di 5 righe e chiedigli se vuole correggere qualcosa.

## 4. Proposta in chat
Mostra:
```
**Risposta a** Mario Rossi — «Re: Preventivo fornitura» (a: mario@…, cc: —)

Ciao Mario,
…

[DA COMPLETARE: …] ← solo se manca un'informazione
```
Poi chiedi: «La salvo come bozza in Outlook? Posso anche modificarla.»

## 5. Dopo l'ok
- `create_reply_draft` con il testo approvato (`open_window: true`, così la bozza si apre in Outlook). Usa `reply_all` solo se concordato.
- Se l'utente chiede un nuovo messaggio e non una risposta, usa `create_draft`.
- Conferma: «Bozza aperta in Outlook e salvata in Bozze: non è stata inviata».
- Se in `TASKS.md` c'era una voce per questa email, aggiungi «bozza pronta».
