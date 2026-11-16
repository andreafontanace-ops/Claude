# Assistente Outlook: comandi per lavorare con Claude da una chat, senza collegamenti speciali.
#
#   assistente [giorni]   riepilogo di posta, agenda e posta inviata (predefinito 7 giorni)
#                         → copiato negli appunti: poi Cmd+V nella chat con Claude
#   assistente esegui     esegue il blocco di azioni copiato dalla chat (bozze, flag, attività)
#                         → l'esito viene copiato negli appunti: incollalo in chat
#
# A ogni uso lo script outlook.js si aggiorna dal repository. Non invia e non elimina mai email.
#
# Installazione: salva questo file come ~/.assistente-outlook.zsh e aggiungi a ~/.zshrc la riga
#   source ~/.assistente-outlook.zsh

ASSISTENTE_URL="https://raw.githubusercontent.com/andreafontanace-ops/Claude/claude/zen-hawking-vfbu9v/plugins/outlook-mac/server/outlook.js"

assistente() {
  local js="$HOME/outlook.js"
  if curl -fsSL "$ASSISTENTE_URL?$(date +%s)" -o "$js.new" 2>/dev/null; then
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
