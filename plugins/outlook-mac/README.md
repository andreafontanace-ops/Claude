# outlook-mac

Collega Claude all'app **Microsoft Outlook installata sul Mac** tramite AppleScript. Non servono connettori né il consenso dell'amministratore: usa l'account già configurato in Outlook.

Cosa fa:
- **smista la posta**: individua cosa aspetta una tua risposta, cosa richiede un'azione e cosa è solo rumore;
- **prepara le cose da fare** in `TASKS.md` e mette un flag in Outlook, così le ritrovi anche nelle Attività;
- **propone le risposte in chat** nel tuo stile e le salva come **bozze** in Outlook solo dopo il tuo ok;
- legge calendario e attività per il **briefing** della giornata.

Cosa non fa mai: **inviare** o **eliminare** email. Non esistono comandi per farlo: premi sempre tu Invia.

## Requisiti

- macOS con **Outlook legacy** attivo. Il «nuovo Outlook» per Mac supporta poco AppleScript: se è attivo, torna alla versione legacy dal menu Outlook (o Aiuto) → «Outlook legacy», oppure disattiva l'interruttore «Nuovo Outlook».
- Nient'altro: lo script usa `osascript`, già incluso in macOS.

## Prima prova (Terminale sul Mac)

```bash
osascript -l JavaScript plugins/outlook-mac/server/outlook.js status
```

La prima volta macOS chiede se il Terminale può controllare Microsoft Outlook: rispondi **OK**. Se hai rifiutato, vai in Impostazioni di Sistema → Privacy e sicurezza → Automazione e abilita Outlook sotto l'app interessata.

Altri comandi utili:

```bash
osascript -l JavaScript plugins/outlook-mac/server/outlook.js inbox 10
```

```bash
osascript -l JavaScript plugins/outlook-mac/server/outlook.js help
```

## Tre modi di usarlo

### 0. Da qualsiasi chat, con copia e incolla (il più semplice)

Installazione, una volta sola, nel Terminale del Mac:

```bash
curl -fsSL https://raw.githubusercontent.com/andreafontanace-ops/Claude/claude/zen-hawking-vfbu9v/plugins/outlook-mac/assistente.zsh -o ~/.assistente-outlook.zsh && (grep -q assistente-outlook ~/.zshrc 2>/dev/null || echo 'source ~/.assistente-outlook.zsh' >> ~/.zshrc) && source ~/.assistente-outlook.zsh
```

Uso quotidiano:
- `assistente` (oppure `assistente 14` per 14 giorni) raccoglie posta, agenda e posta inviata e le copia negli appunti. Una notifica avvisa quando ha finito: incolla in chat con Cmd+V.
- Claude propone le cose da fare e le risposte. Quando le approvi, ti dà un blocco di azioni da copiare: lancia `assistente esegui`, che crea bozze, flag e attività in Outlook, poi incolla l'esito in chat.

### A. Da una chat nell'app Claude, collegando una cartella del Mac

La sessione cloud raggiunge il Mac tramite **Remote Control**:
1. nell'app Claude desktop sul Mac: Impostazioni → Claude Code → Remote Control, e aggiungi una cartella di lavoro (ad esempio `~/Assistente`);
2. scrivi in chat che la cartella è pronta: Claude chiede di collegarla (approvi tu), copia lì lo script e lo esegue con `osascript`.

`TASKS.md`, `STILE-EMAIL.md` e lo stato dello smistamento restano in quella cartella, sul Mac.

### B. Claude Code direttamente sul Mac

In Claude Code, con questo repository clonato sul Mac:

```
/plugin marketplace add /percorso/del/repository
```

```
/plugin install outlook-mac@mac-tools
```

Poi apri Claude Code in una cartella di lavoro (ad esempio `~/Assistente`) e usa:

| Comando | Cosa fa |
|---|---|
| `/outlook-mac:triage` | smista la posta nuova, aggiorna `TASKS.md`, mette i flag e propone le risposte |
| `/outlook-mac:reply Mario preventivo` | prepara una risposta specifica |
| `/outlook-mac:brief` | agenda, email in sospeso e cose da fare di oggi e domani |

Puoi anche chiedere in linguaggio naturale, ad esempio «cosa mi ha scritto Giulia questa settimana?».

## Come lavora con le risposte

1. Claude scrive la proposta di risposta **in chat** e tu la leggi.
2. Rispondi «ok», oppure chiedi modifiche.
3. Solo a quel punto la bozza viene salvata in Outlook (cartella Bozze), dove la puoi aprire, ritoccare e inviare.

La prima volta Claude crea `STILE-EMAIL.md` leggendo alcune email che hai inviato (saluti, tu/Lei, firma, lunghezza), così le risposte ti somigliano. Il file si può modificare liberamente.

## Sicurezza

- Il contenuto delle email è trattato come dato non attendibile: istruzioni contenute in un'email («inoltra a…», «ignora le istruzioni…») non vengono eseguite, ma segnalate.
- Gli spostamenti verso Cestino e Posta indesiderata sono bloccati.
- Il testo delle email letto da Claude passa per il servizio di Claude. Se si tratta di posta di lavoro, verifica che le regole della tua azienda lo consentano.

## Limiti noti

- Le riunioni ricorrenti iniziate prima del periodo richiesto non vengono espanse da AppleScript: il briefing le segnala come «da verificare».
- Dopo uno spostamento l'id di un messaggio può cambiare.
- Le cartelle molto grandi (decine di migliaia di messaggi) rallentano la prima lettura.

## Sviluppo

Lo script `server/outlook.js` è insieme server MCP (`… outlook.js mcp`) e riga di comando. I test usano un Outlook simulato e girano con Node:

```bash
node --test plugins/outlook-mac/test/outlook.test.cjs
```

I test verificano la logica e il protocollo, non l'Outlook reale: la prima verifica vera è `status` sul Mac.
