"""Piani e limiti. I prezzi sono una proposta di partenza da tarare sui costi reali dei dati."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Plan:
    slug: str
    name: str
    price_month_eur: int | None  # None = su preventivo
    categories: int
    sites: int
    interval_minutes: int  # frequenza di aggiornamento
    users: int
    history_days: int
    export: bool
    api: bool
    blurb: str

    @property
    def frequency_label(self) -> str:
        m = self.interval_minutes
        if m >= 1440:
            return "ogni giorno"
        if m >= 60:
            return "ogni ora" if m == 60 else f"ogni {m // 60} ore"
        return f"ogni {m} minuti"


PLANS: dict[str, Plan] = {
    "prova": Plan("prova", "Prova gratuita (14 giorni)", 0, 1, 2, 1440, 1, 30, False, False,
                  "Una categoria su due siti, aggiornata ogni giorno."),
    "base": Plan("base", "Base", 129, 1, 2, 1440, 2, 90, True, False,
                 "Per un brand manager che segue una categoria."),
    "pro": Plan("pro", "Pro", 449, 3, 4, 60, 5, 365, True, False,
                "Per il team e-commerce: più categorie, più siti, aggiornamento orario."),
    "enterprise": Plan("enterprise", "Enterprise", None, 20, 10, 15, 50, 730, True, True,
                       "Categorie su misura, aggiornamento ogni 15 minuti, API e supporto dedicato."),
}

TRIAL_DAYS = 14


def get_plan(slug: str) -> Plan:
    return PLANS.get(slug, PLANS["prova"])


def trial_expired(plan_slug: str, trial_ends_at: datetime | None, now: datetime) -> bool:
    return plan_slug == "prova" and trial_ends_at is not None and now > trial_ends_at
