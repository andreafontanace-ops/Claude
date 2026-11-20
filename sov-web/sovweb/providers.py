"""Fonti dei dati di ricerca.

Ogni fonte restituisce, per una keyword e una pagina, la lista dei risultati nell'ordine in cui
compaiono sul sito (stessa struttura del parser di amazon-sov). In produzione la fonte sarà un
fornitore di dati SERP con licenza; la fonte "demo" genera dati dimostrativi per lo sviluppo.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime

from amazon_sov.parser import SerpItem


class ProviderError(RuntimeError):
    pass


class Provider:
    name = "base"

    def supports(self, site_slug: str) -> bool:
        raise NotImplementedError

    def fetch(self, site_slug: str, keyword: str, page: int, brands: list[str], now: datetime) -> list[SerpItem]:
        raise NotImplementedError


class NoProvider(Provider):
    """Nessuna raccolta automatica: i dati arrivano solo dall'API di caricamento."""

    name = "none"

    def supports(self, site_slug: str) -> bool:
        return False


_FORMS = ["30 compresse", "60 capsule", "gocce 30 ml", "20 stick orosolubili", "90 compresse", "gummies"]


class DemoProvider(Provider):
    """Risultati inventati ma realistici, stabili nell'ora e con una lenta deriva nel tempo.

    Servono solo a sviluppare e mostrare la dashboard: ogni esecuzione risulta con fonte "demo"
    e la dashboard lo dichiara.
    """

    name = "demo"

    def supports(self, site_slug: str) -> bool:
        return True

    def fetch(self, site_slug: str, keyword: str, page: int, brands: list[str], now: datetime) -> list[SerpItem]:
        hour = now.strftime("%Y%m%d%H")
        day = now.toordinal()
        seed = int(hashlib.sha256(f"{site_slug}|{keyword}|{page}|{hour}".encode()).hexdigest()[:12], 16)
        rnd = random.Random(seed)
        # forza di ogni marchio: stabile per sito, con una lenta oscillazione nei giorni
        weights = {}
        for b in brands:
            base = int(hashlib.sha256(f"{site_slug}|{b}".encode()).hexdigest()[:6], 16) % 100 + 20
            drift = (int(hashlib.sha256(f"{b}|{day // 3}".encode()).hexdigest()[:4], 16) % 30) - 15
            weights[b] = max(5, base + drift)
        items: list[SerpItem] = []
        word = keyword.title() if keyword else "Prodotto"
        for slot in range(1, 21):
            if rnd.random() < 0.1:  # risultato non pertinente
                items.append(SerpItem(asin=_pid(site_slug, f"x{slot}{seed % 97}"), slot=slot,
                                      title="Borraccia sportiva 750 ml", brand_raw="Generico", sponsored=False,
                                      placement="organic"))
                continue
            brand = rnd.choices(list(weights), weights=list(weights.values()))[0]
            variant = rnd.randrange(3)
            sponsored = rnd.random() < (0.25 if slot <= 4 else 0.08)
            items.append(SerpItem(
                asin=_pid(site_slug, f"{brand}|{variant}"),
                slot=slot,
                title=f"{brand} {word} {_FORMS[variant]}",
                brand_raw=brand,
                sponsored=sponsored,
                placement="sponsored" if sponsored else "organic",
                price=round(rnd.uniform(7, 35), 2),
                rating=round(rnd.uniform(3.8, 4.9), 1),
                reviews=rnd.randint(20, 15000),
            ))
        return items


def _pid(site: str, key: str) -> str:
    return "D" + hashlib.sha256(f"{site}|{key}".encode()).hexdigest()[:9].upper()


def get_provider(name: str) -> Provider:
    if name == "demo":
        return DemoProvider()
    if name in ("none", ""):
        return NoProvider()
    raise ProviderError(
        f"Fonte dati '{name}' non disponibile. Le fonti a pagamento (fornitori di dati SERP) si aggiungono qui "
        "implementando Provider.fetch."
    )
