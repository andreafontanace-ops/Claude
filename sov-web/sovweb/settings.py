"""Impostazioni da variabili d'ambiente.

SOV_ENV: dev (sul proprio computer) · staging (online, di prova) · production (online, clienti veri).
In staging e production valgono le stesse protezioni; solo in production i dati dimostrativi sono vietati.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEV_SECRET = "dev-solo-in-locale"
ENVIRONMENTS = ("dev", "staging", "production")


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: _env("SOV_ENV", "dev"))
    database_url: str = field(default_factory=lambda: _env("SOV_DATABASE_URL") or _env("DATABASE_URL")
                              or "sqlite:///./sovweb.sqlite")
    secret_key: str = field(default_factory=lambda: _env("SOV_SECRET_KEY", DEV_SECRET))
    # demo = dati dimostrativi generati · none = solo dati caricati via API o da fornitori configurati
    data_provider: str = field(default_factory=lambda: _env("SOV_DATA_PROVIDER", "demo"))
    # token per caricare risultati via API (es. dal crawler locale amazon-sov); vuoto = API disattivata
    ingest_token: str = field(default_factory=lambda: _env("SOV_INGEST_TOKEN"))
    # email (avvisi, recupero password, verifica): senza SMTP le email finiscono solo nel log
    smtp_host: str = field(default_factory=lambda: _env("SOV_SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: int(_env("SOV_SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: _env("SOV_SMTP_USER"))
    smtp_password: str = field(default_factory=lambda: _env("SOV_SMTP_PASSWORD"))
    mail_from: str = field(default_factory=lambda: _env("SOV_MAIL_FROM"))
    base_url: str = field(default_factory=lambda: _env("SOV_BASE_URL", "http://localhost:8000").rstrip("/"))

    @property
    def online(self) -> bool:
        """True quando il sito è su Internet (staging o production): cookie solo HTTPS, HSTS, ecc."""
        return self.environment in ("staging", "production")

    @property
    def production(self) -> bool:
        return self.environment == "production"

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.mail_from)

    def check(self) -> None:
        if self.environment not in ENVIRONMENTS:
            raise RuntimeError(f"SOV_ENV deve essere uno tra {', '.join(ENVIRONMENTS)}")
        if self.online and (self.secret_key == DEV_SECRET or len(self.secret_key) < 32):
            raise RuntimeError("Online serve SOV_SECRET_KEY: una stringa casuale di almeno 32 caratteri")
        if self.online and self.database_url.startswith("sqlite"):
            raise RuntimeError("Online serve un database Postgres (SOV_DATABASE_URL o DATABASE_URL)")
        if self.production and self.data_provider == "demo":
            raise RuntimeError("In produzione i dati dimostrativi non sono ammessi: imposta SOV_DATA_PROVIDER")
        if self.ingest_token and len(self.ingest_token) < 24:
            raise RuntimeError("SOV_INGEST_TOKEN troppo corto: usa almeno 24 caratteri casuali")
