"""Limite ai tentativi (accesso, registrazione, recupero password) per indirizzo IP e per email.

Il conteggio sta in memoria nel singolo processo: con più processi il limite effettivo si moltiplica per
il loro numero, che resta comunque basso. Davanti al sito, Cloudflare aggiunge un limite globale.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self):
        self._hits: dict[tuple, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: tuple, limit: int, window_seconds: int) -> bool:
        """Registra un tentativo. False se il limite è già stato superato nella finestra."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self, key: tuple) -> None:
        with self._lock:
            self._hits.pop(key, None)
