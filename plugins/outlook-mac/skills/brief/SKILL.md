---
name: brief
description: Riepilogo della giornata da Outlook sul Mac, con appuntamenti, email che aspettano una risposta e cose da fare aperte o in scadenza. Usala per «com'è la mia giornata», «briefing», «cosa ho oggi/domani/questa settimana».
argument-hint: "[oggi | domani | settimana]"
---

# Briefing

Segui le regole della skill `outlook`. Solo lettura: non creare bozze e non cambiare niente senza una richiesta.

## Raccogli
1. **Calendario**: `list_events`. Oggi: `days: 2`, per vedere anche domani. «settimana»: `days: 7`. Se nel risultato c'è `recurring_series_not_expanded`, ripeti con `include_recurring: true` e indica le serie ricorrenti che probabilmente cadono nel periodo (stesso giorno della settimana), con «verifica in calendario».
2. **Email in sospeso**: `list_messages` con `flagged_only: true` e `limit: 30`, più i non letti delle ultime 24 ore (`unread_only: true`, `since_days: 1`).
3. **Cose da fare**: sezioni Active e Waiting On di `TASKS.md` (scadute, in scadenza oggi o domani), più `list_tasks`.

## Presenta (breve, in italiano)
```
**<giorno, data>**

📅 Agenda
- 10:00–11:00 Riunione progetto (Sala 2)
- …
  ↳ da preparare: … (se un'email o un'attività è collegata alla riunione)

🔴 Aspettano una tua risposta (<n>)
- Mario Rossi — Preventivo (da 2 giorni) …

✅ Da fare: scadute / oggi / domani
- …

⏳ In attesa da altri: …
```
Chiudi con un suggerimento concreto, ad esempio «Vuoi che prepari le risposte per i primi tre?».
