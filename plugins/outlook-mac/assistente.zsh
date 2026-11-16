# Assistente Outlook: comandi per lavorare con Claude da una chat, senza collegamenti speciali.
#
#   assistente [giorni]   riepilogo di posta, agenda e posta inviata (predefinito 7 giorni)
#                         → copiato negli appunti: poi Cmd+V nella chat con Claude
#   assistente esegui     esegue il blocco di azioni copiato dalla chat (bozze, flag, attività)
#                         → l'esito viene copiato negli appunti: incollalo in chat
#
# A ogni uso lo script outlook.js si aggiorna dal repository. Non elimina mai email; invia solo
# le risposte che hai ordinato in chat, dopo la tua conferma in una finestra del Mac.
#
# Installazione: salva questo file come ~/.assistente-outlook.zsh e aggiungi a ~/.zshrc la riga
#   source ~/.assistente-outlook.zsh

ASSISTENTE_REPO="andreafontanace-ops/Claude"
ASSISTENTE_BRANCH="claude/zen-hawking-vfbu9v"

assistente() {
  local js="$HOME/outlook.js"
  # Scarica la versione esatta dell'ultimo commit: l'indirizzo «per branch» di GitHub può restare
  # in cache per alcuni minuti e servire una versione vecchia.
  local sha
  sha=$(curl -fsSL "https://api.github.com/repos/$ASSISTENTE_REPO/commits/$ASSISTENTE_BRANCH" 2>/dev/null |
    sed -n 's/^  "sha": "\([0-9a-f]\{40\}\)".*/\1/p' | head -1)
  local ref="${sha:-$ASSISTENTE_BRANCH}"
  if curl -fsSL "https://raw.githubusercontent.com/$ASSISTENTE_REPO/$ref/plugins/outlook-mac/server/outlook.js" -o "$js.new" 2>/dev/null; then
    mv "$js.new" "$js"
  else
    rm -f "$js.new"
    echo "(aggiornamento non riuscito: uso la versione già presente)"
  fi
  if [[ ! -f "$js" ]]; then
    echo "Script non trovato in $js: controlla la connessione e riprova."
    return 1
  fi

  local out
  if [[ "$1" == "esegui" ]]; then
    echo "Eseguo le azioni copiate dalla chat…"
    out=$(osascript -l JavaScript "$js" run "$(pbpaste)" 2>&1)
    echo "$out"
  else
    local days="${1:-7}"
    echo "Raccolgo posta, agenda e posta inviata degli ultimi $days giorni (può volerci un minuto)…"
    out=$(osascript -l JavaScript "$js" digest "$days" 2>&1)
  fi
  printf '%s\n' "$out" | pbcopy
  osascript -e 'display notification "Risultato copiato: incollalo nella chat con Claude (Cmd+V)" with title "Assistente Outlook" sound name "Glass"' >/dev/null 2>&1
  echo "FATTO: torna nella chat e premi Cmd+V"
}
