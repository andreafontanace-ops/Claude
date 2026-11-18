"""Dalle pagine analizzate alle righe SERP: posizioni assolute, marchio, pertinenza."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .brands import BrandResolver, RelevanceFilter
from .parser import ParsedPage

log = logging.getLogger(__name__)


@dataclass
class SerpRow:
    keyword: str
    page: int
    slot: int
    rank: int | None  # posizione assoluta tra i risultati (organici + sponsorizzati), su tutte le pagine
    organic_rank: int | None  # posizione tra i soli risultati organici
    asin: str
    title: str
    brand_raw: str | None
    brand: str
    brand_source: str
    sponsored: bool
    placement: str
    widget: str | None
    price: float | None
    list_price: float | None
    rating: float | None
    reviews: int | None
    bought_last_month: int | None
    badges: str
    relevant: bool
    # calcolati al momento del report (vedi products.annotate_products)
    manufacturer: str | None = None
    manufacturer_source: str | None = None
    form: str | None = None
    iron_type: str | None = None


def consecutive_pages(pages: list[ParsedPage]) -> list[ParsedPage]:
    """Tiene le pagine 1..n senza buchi: con una pagina mancante le posizioni successive sarebbero sbagliate."""
    by_no = {p.page: p for p in pages if not p.blocked}
    out = []
    n = 1
    while n in by_no:
        out.append(by_no[n])
        n += 1
    dropped = sorted(set(by_no) - {p.page for p in out})
    if dropped:
        log.warning("Keyword '%s': ignoro le pagine %s perché manca una pagina precedente", pages[0].keyword, dropped)
    return out


def build_rows(
    keyword: str,
    pages: list[ParsedPage],
    resolver: BrandResolver,
    relevance: RelevanceFilter,
) -> list[SerpRow]:
    rows: list[SerpRow] = []
    rank = 0
    organic_rank = 0
    for page in consecutive_pages(pages):
        for item in page.items:
            if item.placement == "widget":
                r = o = None
            else:
                rank += 1
                r = rank
                if item.sponsored:
                    o = None
                else:
                    organic_rank += 1
                    o = organic_rank
            brand, source = resolver.resolve(item.asin, item.brand_raw, item.title)
            rows.append(
                SerpRow(
                    keyword=keyword,
                    page=page.page or 1,
                    slot=item.slot,
                    rank=r,
                    organic_rank=o,
                    asin=item.asin,
                    title=item.title,
                    brand_raw=item.brand_raw,
                    brand=brand,
                    brand_source=source,
                    sponsored=item.sponsored,
                    placement=item.placement,
                    widget=item.widget,
                    price=item.price,
                    list_price=item.list_price,
                    rating=item.rating,
                    reviews=item.reviews,
                    bought_last_month=item.bought_last_month,
                    badges="|".join(item.badges),
                    relevant=relevance(item.title),
                )
            )
    return rows


def reclassify(rows: list[SerpRow], resolver: BrandResolver, relevance: RelevanceFilter) -> list[SerpRow]:
    """Ricalcola marchio e pertinenza con la configurazione attuale (alias, correzioni, cache)."""
    for row in rows:
        row.brand, row.brand_source = resolver.resolve(row.asin, row.brand_raw, row.title)
        row.relevant = relevance(row.title)
    return rows
