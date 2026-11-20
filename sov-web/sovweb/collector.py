"""Raccolta dei dati di un feed (categoria × sito) e calcolo della share of voice.

Il calcolo è quello di amazon-sov: stesse regole per marchio, pertinenza, formulazione e pesi
per posizione. Dopo ogni esecuzione si salva una sintesi per marchio e per prodotto, così la
dashboard legge poche righe già pronte.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from amazon_sov.brands import BrandResolver, RelevanceFilter
from amazon_sov.config import Config, config_from_dict
from amazon_sov.parser import ParsedPage, SerpItem
from amazon_sov.pipeline import SerpRow, build_rows
from amazon_sov.products import annotate_products
from amazon_sov.scoring import UNRANKED, compute_sov
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BrandSov, Feed, ProductSov, Run, SerpResult, Subscription, WorkspaceBrand, utcnow
from .plans import get_plan
from .providers import Provider

log = logging.getLogger(__name__)
DEFAULT_INTERVAL = 1440


def feed_config(feed: Feed) -> Config:
    return config_from_dict(feed.category.config)


def known_brands(session: Session, feed: Feed) -> list[str]:
    """Marchi indicati dai clienti per questa categoria (servono ai dati dimostrativi)."""
    names = session.scalars(
        select(WorkspaceBrand.name).where(WorkspaceBrand.category_id == feed.category_id).distinct()
    ).all()
    return sorted(set(names))


def update_feed_interval(session: Session, feed: Feed) -> None:
    """La frequenza di un feed è la più alta tra i piani di chi lo segue."""
    subs = session.scalars(select(Subscription).where(Subscription.feed_id == feed.id)).all()
    intervals = [get_plan(s.workspace.plan).interval_minutes for s in subs]
    new = min(intervals) if intervals else DEFAULT_INTERVAL
    if new < feed.interval_minutes and feed.last_run_at is not None:
        feed.next_run_at = min(feed.next_run_at, feed.last_run_at + timedelta(minutes=new))
    feed.interval_minutes = new


def run_feed(session: Session, feed: Feed, provider: Provider, now: datetime | None = None) -> Run:
    now = now or utcnow()
    cfg = feed_config(feed)
    run = Run(feed_id=feed.id, started_at=now, source=provider.name)
    session.add(run)
    session.flush()
    try:
        if not provider.supports(feed.site.slug):
            raise RuntimeError(f"La fonte dati '{provider.name}' non copre {feed.site.name}")
        brands = list(dict.fromkeys(list(feed.category.demo_brands or []) + known_brands(session, feed)))
        pages = 1 if provider.name == "demo" else cfg.crawl.pages
        per_keyword = {
            kw.term: [ParsedPage(kw.term, p, provider.fetch(feed.site.slug, kw.term, p, brands, now)) for p in range(1, pages + 1)]
            for kw in cfg.keywords
        }
        _save_run(session, run, cfg, per_keyword)
    except Exception as exc:  # una fonte che fallisce non deve fermare le altre
        log.exception("Raccolta fallita per il feed %s", feed.id)
        run.status = "error"
        run.error = str(exc)[:1000]
    run.finished_at = utcnow()
    feed.last_run_at = now
    feed.next_run_at = now + timedelta(minutes=feed.interval_minutes)
    session.commit()
    _alerts(session, run)
    return run


def ingest_run(session: Session, feed: Feed, results: dict[str, list[SerpItem]], now: datetime | None = None) -> Run:
    """Esecuzione con risultati caricati dall'esterno (es. crawler locale), una lista per keyword."""
    now = now or utcnow()
    run = Run(feed_id=feed.id, started_at=now, source="ingest")
    session.add(run)
    session.flush()
    cfg = feed_config(feed)
    _save_run(session, run, cfg, {kw: [ParsedPage(kw, 1, items)] for kw, items in results.items()})
    run.finished_at = utcnow()
    feed.last_run_at = now
    session.commit()
    _alerts(session, run)
    return run


def _alerts(session: Session, run: Run) -> None:
    from .alerts import evaluate

    try:
        evaluate(session, run)
    except Exception:  # un problema negli avvisi non deve far perdere i dati raccolti
        log.exception("Valutazione degli avvisi fallita per l'esecuzione %s", run.id)
        session.rollback()


def _save_run(session: Session, run: Run, cfg: Config, per_keyword: dict[str, list[ParsedPage]]) -> None:
    resolver = BrandResolver(cfg)
    relevance = RelevanceFilter(cfg.relevance_include, cfg.relevance_exclude)
    rows: list[SerpRow] = []
    for kw, pages in per_keyword.items():
        rows += build_rows(kw, pages, resolver, relevance)
    session.add_all(
        SerpResult(run_id=run.id, keyword=r.keyword, page=r.page, slot=r.slot, rank=r.rank,
                   organic_rank=r.organic_rank, product_id=r.asin, title=r.title[:600], brand_raw=r.brand_raw,
                   sponsored=r.sponsored, placement=r.placement, price=r.price, rating=r.rating, reviews=r.reviews)
        for r in rows
    )
    annotate_products(rows, cfg, {}, {})
    weights = {kw: cfg.keyword_weights.get(kw, 1.0) for kw in per_keyword}
    result = compute_sov(rows, weights, cfg.scoring)
    rank = 0
    for b in result.brands:
        ranked = b["brand"] not in UNRANKED
        rank += ranked
        session.add(BrandSov(
            run_id=run.id, brand=b["brand"], rank=rank if ranked else None, sov_total=b["sov_total"],
            sov_organic=b["sov_organic"], sov_paid=b["sov_paid"], ads_share=b["ads_share"],
            shelf_top10=b["shelf_top10"], n_products=b["n_products"], manufacturer=b.get("manufacturer"),
        ))
    for i, p in enumerate((p for p in result.products if p["relevant"]), 1):
        if i > 100:
            break
        session.add(ProductSov(
            run_id=run.id, rank=i, product_id=p["asin"], title=p["title"][:600], brand=p["brand"], form=p["form"],
            variant=p["iron_type"], sov_total=p["sov_total"], sov_organic=p["sov_organic"],
            best_organic_rank=p["best_organic_rank"], price=p["price"], rating=p["rating"], reviews=p["reviews"],
        ))
    run.keywords_scored = len(result.keywords_scored)
    run.sponsored_slot_share = result.meta["sponsored_slot_share"]
    run.status = "ok" if rows else "error"
    if not rows:
        run.error = "Nessun risultato ricevuto"


def run_due(session: Session, provider: Provider, now: datetime | None = None, limit: int = 20) -> int:
    """Esegue i feed scaduti che hanno almeno un cliente. Con Postgres più worker non si pestano i piedi."""
    now = now or utcnow()
    feeds = session.scalars(
        select(Feed)
        .where(Feed.next_run_at <= now, Feed.subscriptions.any())
        .order_by(Feed.next_run_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    for feed in feeds:
        run_feed(session, feed, provider, now)
    return len(feeds)
