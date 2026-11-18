"""Esportazione CSV (formato adatto a Excel italiano di default)."""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from .pipeline import SerpRow
from .scoring import NON_RELEVANT, SovResult

PCT_KEYS = {"sov_total", "sov_organic", "sov_paid", "ads_share", "shelf_top10", "delta_pp"}

PRODUCT_COLUMNS = [
    ("rank", "posizione"),
    ("asin", "asin"),
    ("brand", "marchio"),
    ("title", "titolo"),
    ("sov_total", "sov_totale_%"),
    ("sov_organic", "sov_organica_%"),
    ("sov_paid", "sov_ads_%"),
    ("ads_share", "quota_da_ads_%"),
    ("shelf_top10", "presenza_top10_%"),
    ("keywords_present", "keyword_presenti"),
    ("keywords_top10_organic", "keyword_top10_organico"),
    ("best_organic_rank", "miglior_pos_organica"),
    ("avg_organic_rank", "pos_organica_media"),
    ("organic_hits", "apparizioni_organiche"),
    ("sponsored_hits", "apparizioni_sponsorizzate"),
    ("price", "prezzo_eur"),
    ("rating", "valutazione"),
    ("reviews", "n_valutazioni"),
    ("bought_last_month", "acquisti_mese_scorso"),
    ("badges", "badge"),
    ("brand_source", "fonte_marchio"),
    ("delta_pp", "delta_vs_precedente_pp"),
]

BRAND_COLUMNS = [
    ("rank", "posizione"),
    ("brand", "marchio"),
    ("sov_total", "sov_totale_%"),
    ("sov_organic", "sov_organica_%"),
    ("sov_paid", "sov_ads_%"),
    ("ads_share", "quota_da_ads_%"),
    ("shelf_top10", "presenza_top10_%"),
    ("keywords_present", "keyword_presenti"),
    ("keywords_top10_organic", "keyword_top10_organico"),
    ("best_organic_rank", "miglior_pos_organica"),
    ("n_products", "n_prodotti"),
    ("top_asin", "asin_di_punta"),
    ("top_title", "prodotto_di_punta"),
    ("delta_pp", "delta_vs_precedente_pp"),
]


def _fmt(value, key: str, dialect: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if key in PCT_KEYS and isinstance(value, (int, float)):
        value = round(value * 100, 3)
    if isinstance(value, float):
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return text.replace(".", ",") if dialect == "excel-it" else text
    return str(value)


def write_table(path: Path, rows: list[dict], columns: list[tuple[str, str]], dialect: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    delimiter = ";" if dialect == "excel-it" else ","
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=delimiter)
        w.writerow([header for _, header in columns])
        for row in rows:
            w.writerow([_fmt(row.get(key), key, dialect) for key, _ in columns])


def write_all(out_dir: Path, rows: list[SerpRow], result: SovResult, dialect: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "serp": out_dir / "serp.csv",
        "prodotti": out_dir / "sov_prodotti.csv",
        "marchi": out_dir / "sov_marchi.csv",
        "keyword_marchi": out_dir / "sov_keyword_marchi.csv",
    }
    serp_dicts = [asdict(r) for r in rows]
    serp_cols = [(k, k) for k in serp_dicts[0]] if serp_dicts else [("keyword", "keyword")]
    write_table(paths["serp"], serp_dicts, serp_cols, dialect)

    products = [dict(p, rank=i) for i, p in enumerate((p for p in result.products if p["relevant"]), 1)]
    write_table(paths["prodotti"], products, PRODUCT_COLUMNS, dialect)

    brands, n = [], 0
    for b in result.brands:
        n += b["brand"] != NON_RELEVANT
        brands.append(dict(b, rank=n if b["brand"] != NON_RELEVANT else None))
    write_table(paths["marchi"], brands, BRAND_COLUMNS, dialect)

    brand_names = [b["brand"] for b in result.brands]
    matrix = [
        {"keyword": kw, **{b: result.keyword_brand[kw].get(b, 0.0) * 100 for b in brand_names}}
        for kw in result.keywords_scored
    ]
    write_table(
        paths["keyword_marchi"],
        matrix,
        [("keyword", "keyword")] + [(b, f"{b} %") for b in brand_names],
        dialect,
    )
    return paths
