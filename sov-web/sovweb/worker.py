"""Processo che fa partire le raccolte da solo: `python -m sovweb.worker`.

Ogni minuto cerca i feed da aggiornare (in base alla frequenza dei piani dei clienti) e li esegue.
Si possono avviare più worker in parallelo su Postgres.
"""

from __future__ import annotations

import logging
import signal
import time

from .catalog import seed_catalog
from .alerts import send_pending_emails
from .collector import run_due
from .db import Database
from .providers import get_provider
from .settings import Settings

log = logging.getLogger("sovweb.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings()
    settings.check()
    db = Database(settings.database_url)
    db.create_all()
    provider = get_provider(settings.data_provider)
    with db.Session() as s:
        seed_catalog(s)
    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log.info("Worker avviato (fonte dati: %s)", provider.name)
    while not stop:
        try:
            with db.Session() as s:
                n = run_due(s, provider)
                send_pending_emails(s, settings)
            if n:
                log.info("Aggiornati %s feed", n)
        except Exception:
            log.exception("Errore nel giro del worker")
        for _ in range(60):
            if stop:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
