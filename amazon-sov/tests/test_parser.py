from pathlib import Path

import pytest

from amazon_sov.parser import (
    detect_block,
    parse_count,
    parse_price,
    parse_product_brand,
    parse_rating,
    parse_search_page,
)

FIX = Path(__file__).parent / "fixtures"


def page(name):
    return parse_search_page((FIX / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "text, expected",
    [("19,90\xa0€", 19.9), ("1.024,00 €", 1024.0), ("€12.90", 12.9), ("1.234", 1234.0), ("", None), ("gratis", None)],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("(3.512)", 3512),
        ("12.345 valutazioni", 12345),
        ("1K+ acquistati il mese scorso", 1000),
        ("(1,2K)", 1200),
        ("Più di 1000 acquisti nel mese scorso", 1000),
        ("3 mila", 3000),
        ("nessuno", None),
    ],
)
def test_parse_count(text, expected):
    assert parse_count(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [("4,6 su 5 stelle", 4.6), ("4.5 out of 5 stars", 4.5), ("valutazione dettagliata", None)],
)
def test_parse_rating(text, expected):
    assert parse_rating(text) == expected


def test_page1_results_in_order_with_sponsored_flags():
    p = page("integratore-ferro__p1.html")
    assert p.keyword == "integratore ferro"
    assert p.page == 1
    assert p.blocked is None
    assert "risultati" in p.result_count_text
    assert [i.asin for i in p.results] == [
        "B07SIDERAL", "B08NUTRAV1", "B000SOLGAR", "B09NATELEM",
        "B01FEROGLO", "B0DOPPEL01", "B0GENERIC1", "B0FERROLIP",
    ]
    assert [i.slot for i in p.results] == list(range(1, 9))
    assert [i.sponsored for i in p.results] == [True, False, False, False, True, False, False, False]


def test_page1_fields():
    items = {i.asin: i for i in page("integratore-ferro__p1.html").results}
    sideral = items["B07SIDERAL"]
    assert sideral.brand_raw == "Sideral"
    assert sideral.title == "Sideral Forte Integratore di Ferro Sucrosomiale con Vitamina C, 30 Capsule"
    assert (sideral.price, sideral.rating, sideral.reviews, sideral.bought_last_month) == (19.9, 4.6, 3512, 1000)

    nutra = items["B08NUTRAV1"]
    assert nutra.brand_raw == "Nutravita"
    assert (nutra.price, nutra.list_price, nutra.reviews, nutra.bought_last_month) == (15.99, 19.99, 12345, 1000)
    assert nutra.badges == ["Scelta Amazon"]

    solgar = items["B000SOLGAR"]  # markup meno recente
    assert solgar.brand_raw is None
    assert solgar.title == "Solgar Gentle Iron 25 mg, 90 Capsule Vegetali"
    assert (solgar.rating, solgar.reviews) == (4.7, 2104)

    assert items["B01FEROGLO"].badges == ["Bestseller"]


def test_widgets_only_from_results_area():
    p = page("integratore-ferro__p1.html")
    widgets = [i for i in p.items if i.placement == "widget"]
    assert [(w.asin, w.widget) for w in widgets] == [
        ("B0SBWIDG01", "sponsored_brand"),
        ("B0SBWIDG02", "sponsored_brand"),
    ]
    all_asins = {i.asin for i in p.items}
    # varianti annidate, header e "visti di recente" non sono risultati né widget
    assert not all_asins & {"B08NUTRAV2", "B0HEADER01", "B0HISTORY1"}


def test_page2_detects_page_number_and_new_sponsored_label():
    p = page("integratore-ferro__p2.html")
    assert p.page == 2
    assert [(i.asin, i.sponsored) for i in p.results] == [
        ("B08NUTRAV9", False), ("B000SOLGAR", True), ("B0FLORADIX", False),
    ]
    assert p.results[2].price == 1024.0


def test_blocked_pages():
    p = page("captcha.html")
    assert p.blocked == "captcha" and p.items == []
    interstitial = '<html><head><meta http-equiv="refresh" content="5; URL=\'/s?k=x&bm-verify=AAQ\'"></head></html>'
    assert detect_block(interstitial) == "interstitial"
    assert detect_block((FIX / "integratore-ferro__p1.html").read_text()) is None


def test_product_brand():
    assert parse_product_brand((FIX / "product_ferrolip.html").read_text()) == "Ferrolip"
    assert parse_product_brand('<div id="bylineInfo">Marca: Pharma Uno</div>') == "Pharma Uno"
    table_only = '<table><tr class="po-brand"><td>Marca</td><td><span>Acme</span></td></tr></table>'
    assert parse_product_brand(table_only) == "Acme"
    assert parse_product_brand("<html></html>") is None
