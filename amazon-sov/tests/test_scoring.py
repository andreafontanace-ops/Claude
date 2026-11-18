"""Calcoli della SoV verificati a mano su un caso piccolo.

Keyword A (peso 1), pesi zipf 1, 1/2, 1/3, 1/4 (totale 25/12):
  1 X sponsorizzato · 2 Y organico (org 1) · 3 X organico (org 2) · 4 Z non pertinente (org 3)
Keyword B (peso 3), pesi 1, 1/2 (totale 3/2):
  1 Y organico (org 1) · 2 Z non pertinente (org 2)
"""

import math

import pytest

from amazon_sov.config import ScoringConfig
from amazon_sov.pipeline import SerpRow
from amazon_sov.scoring import NON_RELEVANT, compute_sov, position_weight


def row(kw, rank, org, asin, brand, sponsored=False, relevant=True, placement=None):
    return SerpRow(
        keyword=kw, page=1, slot=rank or 0, rank=rank, organic_rank=org, asin=asin, title=f"{brand} ferro",
        brand_raw=brand, brand=brand, brand_source="serp", sponsored=sponsored,
        placement=placement or ("sponsored" if sponsored else "organic"), widget=None, price=None,
        list_price=None, rating=None, reviews=None, bought_last_month=None, badges="", relevant=relevant,
    )


ROWS = [
    row("A", 1, None, "X", "B1", sponsored=True),
    row("A", 2, 1, "Y", "B2"),
    row("A", 3, 2, "X", "B1"),
    row("A", 4, 3, "Z", "B3", relevant=False),
    row("B", 1, 1, "Y", "B2"),
    row("B", 2, 2, "Z", "B3", relevant=False),
]
WEIGHTS = {"A": 1.0, "B": 3.0}


def by(items, key, value):
    return next(i for i in items if i[key] == value)


def test_total_organic_paid_and_ads_share():
    res = compute_sov(ROWS, WEIGHTS, ScoringConfig())
    x, y, z = (by(res.products, "asin", a) for a in "XYZ")
    assert x["sov_total"] == pytest.approx(0.16)
    assert y["sov_total"] == pytest.approx(0.56)
    assert z["sov_total"] == pytest.approx(0.28)
    assert sum(p["sov_total"] for p in res.products) == pytest.approx(1.0)

    assert x["sov_organic"] == pytest.approx(3 / 11 / 4)
    assert y["sov_organic"] == pytest.approx(7 / 11)
    assert z["sov_organic"] == pytest.approx(13 / 44)

    assert x["sov_paid"] == pytest.approx(1.0)  # unico annuncio, solo nella keyword A
    assert x["ads_share"] == pytest.approx(0.75)
    assert y["ads_share"] == 0

    assert x["shelf_top10"] == pytest.approx(0.125)
    assert y["shelf_top10"] == pytest.approx(0.4375)
    assert (x["keywords_present"], y["keywords_present"]) == (1, 2)
    assert (x["best_organic_rank"], y["best_organic_rank"]) == (2, 1)
    assert y["avg_organic_rank"] == 1.0
    assert (x["organic_hits"], x["sponsored_hits"]) == (1, 1)


def test_brand_ranking_puts_non_relevant_bucket_last():
    res = compute_sov(ROWS, WEIGHTS, ScoringConfig())
    assert [b["brand"] for b in res.brands] == ["B2", "B1", NON_RELEVANT]
    assert by(res.brands, "brand", "B1")["sov_total"] == pytest.approx(0.16)
    assert res.keyword_brand["A"] == pytest.approx({"B1": 0.64, "B2": 0.24, NON_RELEVANT: 0.12})
    assert res.meta["relevant_visibility_share"] == pytest.approx(0.72)
    assert res.meta["sponsored_slot_share"] == pytest.approx(1 / 10)  # (1·1 annuncio) / (1·4 + 3·2 slot)


def test_relevant_denominator():
    res = compute_sov(ROWS, WEIGHTS, ScoringConfig(), denominator="relevant")
    assert by(res.products, "asin", "X")["sov_total"] == pytest.approx(2 / 11)
    assert by(res.products, "asin", "Y")["sov_total"] == pytest.approx(9 / 11)
    assert all(p["asin"] != "Z" for p in res.products)


def test_flat_and_max_rank():
    flat = compute_sov(ROWS, WEIGHTS, ScoringConfig(weighting="flat"))
    assert by(flat.products, "asin", "X")["sov_total"] == pytest.approx(0.125)
    top2 = compute_sov(ROWS, WEIGHTS, ScoringConfig(max_rank=2))
    assert by(top2.products, "asin", "X")["sov_total"] == pytest.approx(1 / 6)


def test_empty_keyword_is_reported_and_not_counted():
    res = compute_sov(ROWS, {**WEIGHTS, "C": 5.0}, ScoringConfig())
    assert res.keywords_empty == ["C"]
    assert by(res.products, "asin", "Y")["sov_total"] == pytest.approx(0.56)


def test_widgets_count_only_with_positive_weight():
    rows = ROWS + [row("A", None, None, "W", "B1", sponsored=True, placement="widget")]
    assert all(p["asin"] != "W" for p in compute_sov(rows, WEIGHTS, ScoringConfig()).products)
    res = compute_sov(rows, WEIGHTS, ScoringConfig(widget_weight=0.5))
    w = by(res.products, "asin", "W")
    # keyword A: totale pesi 25/12 + 1/2 = 31/12 -> W ha 0.5 / (31/12) = 6/31, media su peso 4
    assert w["sov_total"] == pytest.approx(6 / 31 / 4)
    assert w["ads_share"] == 1.0 and w["widget_hits"] == 1
    assert sum(p["sov_total"] for p in res.products) == pytest.approx(1.0)


def test_position_weights():
    assert position_weight(1, ScoringConfig()) == 1.0
    assert position_weight(4, ScoringConfig(zipf_exponent=0.5)) == pytest.approx(0.5)
    assert position_weight(3, ScoringConfig(weighting="dcg")) == pytest.approx(0.5)
    table = ScoringConfig(weighting="table", table=[1.0, 0.5], table_decay=0.8)
    assert position_weight(2, table) == 0.5
    assert position_weight(4, table) == pytest.approx(0.5 * 0.8**2)
    assert math.isclose(position_weight(10, ScoringConfig(weighting="flat")), 1.0)
