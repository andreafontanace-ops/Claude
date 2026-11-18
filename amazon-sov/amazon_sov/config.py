"""Caricamento e validazione della configurazione TOML."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Keyword:
    term: str
    weight: float = 1.0


@dataclass
class CrawlConfig:
    pages: int = 2
    delay_seconds: tuple[float, float] = (8.0, 15.0)
    max_pages_total: int = 60
    headless: bool = False
    browser_channel: str = "chromium"


@dataclass
class ScoringConfig:
    weighting: str = "zipf"
    zipf_exponent: float = 1.0
    table: list[float] = field(default_factory=lambda: [1.0])
    table_decay: float = 0.93
    max_rank: int = 0
    widget_weight: float = 0.0


@dataclass
class Config:
    domain: str
    keywords: list[Keyword]
    crawl: CrawlConfig
    scoring: ScoringConfig
    relevance_include: list[str]
    relevance_exclude: list[str]
    brand_aliases: dict[str, list[str]]
    generic_words: list[str]
    asin_overrides: dict[str, str]
    csv_dialect: str = "excel-it"

    @property
    def keyword_weights(self) -> dict[str, float]:
        return {k.term: k.weight for k in self.keywords}


WEIGHTINGS = {"zipf", "dcg", "flat", "table"}


def load_config(path: str | Path) -> Config:
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    return config_from_dict(raw)


def config_from_dict(raw: dict) -> Config:
    crawl_raw = raw.get("crawl", {})
    delay = crawl_raw.get("delay_seconds", [8, 15])
    if len(delay) != 2 or delay[0] > delay[1] or delay[0] < 0:
        raise ValueError("crawl.delay_seconds deve essere [min, max] con 0 <= min <= max")
    crawl = CrawlConfig(
        pages=int(crawl_raw.get("pages", 2)),
        delay_seconds=(float(delay[0]), float(delay[1])),
        max_pages_total=int(crawl_raw.get("max_pages_total", 60)),
        headless=bool(crawl_raw.get("headless", False)),
        browser_channel=str(crawl_raw.get("browser_channel", "chromium")),
    )
    if crawl.pages < 1:
        raise ValueError("crawl.pages deve essere almeno 1")

    sc_raw = raw.get("scoring", {})
    scoring = ScoringConfig(
        weighting=str(sc_raw.get("weighting", "zipf")),
        zipf_exponent=float(sc_raw.get("zipf_exponent", 1.0)),
        table=[float(x) for x in sc_raw.get("table", [1.0])],
        table_decay=float(sc_raw.get("table_decay", 0.93)),
        max_rank=int(sc_raw.get("max_rank", 0)),
        widget_weight=float(sc_raw.get("widget_weight", 0.0)),
    )
    if scoring.weighting not in WEIGHTINGS:
        raise ValueError(f"scoring.weighting deve essere uno tra {sorted(WEIGHTINGS)}")
    if scoring.weighting == "table" and not scoring.table:
        raise ValueError("scoring.table non può essere vuota con weighting = 'table'")

    keywords = []
    seen = set()
    for item in raw.get("keywords", []):
        term = " ".join(str(item["term"]).split())
        if not term or term.lower() in seen:
            continue
        seen.add(term.lower())
        weight = float(item.get("weight", 1.0))
        if weight <= 0:
            raise ValueError(f"keyword '{term}': weight deve essere > 0")
        keywords.append(Keyword(term=term, weight=weight))
    if not keywords:
        raise ValueError("Nessuna keyword in configurazione ([[keywords]])")

    rel = raw.get("relevance", {})
    brands = raw.get("brands", {})
    return Config(
        domain=str(raw.get("marketplace", {}).get("domain", "www.amazon.it")),
        keywords=keywords,
        crawl=crawl,
        scoring=scoring,
        relevance_include=list(rel.get("include", ["ferro", "ferritina", "iron"])),
        relevance_exclude=list(rel.get("exclude", [])),
        brand_aliases={str(k): list(v) for k, v in brands.get("aliases", {}).items()},
        generic_words=list(brands.get("generic_words", [])),
        asin_overrides={str(k).upper(): str(v) for k, v in brands.get("asin_overrides", {}).items()},
        csv_dialect=str(raw.get("output", {}).get("csv_dialect", "excel-it")),
    )
