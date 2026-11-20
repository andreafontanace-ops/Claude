"""Dati di un feed pronti da scaricare: Excel (xlsx), CSV e pagina HTML autonoma."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import BrandSov, Feed, ProductSov, Run, utcnow

BRAND_COLS = [("Posizione", "rank", None), ("Marchio", "brand", None), ("SoV totale %", "sov_total", "pct"),
              ("SoV organica %", "sov_organic", "pct"), ("SoV annunci %", "sov_paid", "pct"),
              ("Quota da annunci %", "ads_share", "pct"), ("Presenza nei primi 10 %", "shelf_top10", "pct"),
              ("Prodotti", "n_products", None), ("Mio marchio", "mine", None)]
PRODUCT_COLS = [("Posizione", "rank", None), ("Prodotto", "title", None), ("Marchio", "brand", None),
                ("Codice", "product_id", None), ("Forma", "form", None), ("Variante", "variant", None),
                ("SoV totale %", "sov_total", "pct"), ("SoV organica %", "sov_organic", "pct"),
                ("Miglior posizione organica", "best_organic_rank", None), ("Prezzo €", "price", None),
                ("Valutazione", "rating", None), ("Recensioni", "reviews", None)]
HISTORY_COLS = [("Data", "when", None), ("Marchio", "brand", None), ("Posizione", "rank", None),
                ("SoV totale %", "sov_total", "pct")]
TABLES = {"marchi": BRAND_COLS, "prodotti": PRODUCT_COLS, "andamento": HISTORY_COLS}


@dataclass
class FeedData:
    feed: Feed
    run: Run | None
    brands: list[dict]
    products: list[dict]
    history: list[dict]


def collect(session: Session, feed: Feed, own: set[str], history_days: int) -> FeedData:
    run = session.scalar(select(Run).where(Run.feed_id == feed.id, Run.status == "ok").order_by(Run.id.desc()))
    brands, products, history = [], [], []
    if run:
        for b in session.scalars(select(BrandSov).where(BrandSov.run_id == run.id)
                                 .order_by(BrandSov.rank.is_(None), BrandSov.rank)):
            brands.append({**_row(b), "mine": "sì" if b.brand.lower() in own else ""})
        products = [_row(p) for p in session.scalars(select(ProductSov).where(ProductSov.run_id == run.id)
                                                     .order_by(ProductSov.rank))]
        since = utcnow() - timedelta(days=history_days)
        for when, b in session.execute(
            select(Run.started_at, BrandSov).join(BrandSov, BrandSov.run_id == Run.id)
            .where(Run.feed_id == feed.id, Run.status == "ok", Run.started_at >= since, BrandSov.rank.isnot(None))
            .order_by(Run.started_at, BrandSov.rank)
        ):
            history.append({"when": when, "brand": b.brand, "rank": b.rank, "sov_total": b.sov_total})
    return FeedData(feed, run, brands, products, history)


def _row(obj) -> dict:
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns}


def _fmt_csv(value, kind):
    if value is None:
        return ""
    if kind == "pct":
        return f"{value * 100:.2f}".replace(".", ",")
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", ",")
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def to_csv(rows: list[dict], cols) -> str:
    """CSV per Excel italiano: separatore ';', virgola decimale, BOM UTF-8."""
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow([c[0] for c in cols])
    for r in rows:
        w.writerow([_fmt_csv(r.get(key), kind) for _, key, kind in cols])
    return "﻿" + out.getvalue()


def to_xlsx(data: FeedData) -> bytes:
    wb = Workbook()
    bold = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="F3F2EF")
    sheets = [("Marchi", data.brands, BRAND_COLS), ("Prodotti", data.products, PRODUCT_COLS),
              ("Andamento", data.history, HISTORY_COLS)]
    for i, (title, rows, cols) in enumerate(sheets):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = title
        ws.append([c[0] for c in cols])
        for cell in ws[1]:
            cell.font = bold
            cell.fill = head_fill
        for r in rows:
            ws.append([r.get(key) for _, key, _ in cols])
        for j, (_, key, kind) in enumerate(cols, 1):
            letter = get_column_letter(j)
            if kind == "pct":  # valori 0-1 mostrati come percentuale: restano numeri usabili nelle formule
                for cell in ws[letter][1:]:
                    cell.number_format = "0.00%"
            if key == "when":
                for cell in ws[letter][1:]:
                    cell.number_format = "dd/mm/yyyy hh:mm"
            width = max([len(str(c[0])) for c in cols if c[1] == key] + [len(str(r.get(key) or "")) for r in rows[:200]])
            ws.column_dimensions[letter].width = min(60, max(10, width + 2))
        ws.freeze_panes = "A2"
    info = wb.create_sheet("Info")
    info.append(["Categoria", data.feed.category.name])
    info.append(["Sito", data.feed.site.name])
    info.append(["Dati del", data.run.started_at if data.run else None])
    info.append(["Fonte", data.run.source if data.run else None])
    info["B3"].number_format = "dd/mm/yyyy hh:mm"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
