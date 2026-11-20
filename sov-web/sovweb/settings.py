"""Impostazioni da variabili d'ambiente (in produzione non si usano mai i valori di sviluppo)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.environ.get("SOV_DATABASE_URL", "sqlite:///./sovweb.sqlite"))
    secret_key: str = field(default_factory=lambda: os.environ.get("SOV_SECRET_KEY", "dev-solo-in-locale"))
    # demo = dati dimostrativi generati (sviluppo) · none = solo dati caricati via API o da fornitori configurati
    data_provider: str = field(default_factory=lambda: os.environ.get("SOV_DATA_PROVIDER", "demo"))
    # token per caricare risultati via API (es. dal crawler locale amazon-sov); vuoto = API disattivata
    ingest_token: str = field(default_factory=lambda: os.environ.get("SOV_INGEST_TOKEN", ""))
    # email per gli avvisi (facoltativa): senza SMTP gli avvisi restano solo nella piattaforma
    smtp_host: str = field(default_factory=lambda: os.environ.get("SOV_SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.environ.get("SOV_SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.environ.get("SOV_SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.environ.get("SOV_SMTP_PASSWORD", ""))
    mail_from: str = field(default_factory=lambda: os.environ.get("SOV_MAIL_FROM", ""))
    base_url: str = field(default_factory=lambda: os.environ.get("SOV_BASE_URL", "http://localhost:8000"))
    production: bool = field(default_factory=lambda: os.environ.get("SOV_ENV", "dev") == "production")

    def check(self) -> None:
        if self.production and self.secret_key == "dev-solo-in-locale":
            raise RuntimeError("In produzione imposta SOV_SECRET_KEY con una chiave segreta lunga e casuale")
        if self.production and self.data_provider == "demo":
            raise RuntimeError("In produzione i dati dimostrativi non sono ammessi: imposta SOV_DATA_PROVIDER")
