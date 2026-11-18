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


def _card(inner):
    return (
        '<div class="s-main-slot"><div data-asin="B0TEST0001" data-component-type="s-search-result">'
        f"{inner}</div></div>"
    )


def test_brand_row_without_heading():
    html = _card(
        '<div data-cy="title-recipe"><div class="a-row a-color-secondary">'
        '<span class="a-size-base-plus a-color-base">Pharma Uno</span></div>'
        '<a class="a-link-normal a-text-normal" href="/dp/B0TEST0001"><h2><span>Ferro Bisglicinato 30 mg</span></h2></a></div>'
    )
    assert parse_search_page(html).results[0].brand_raw == "Pharma Uno"


def test_brand_from_di_row():
    html = _card(
        '<h2><a class="a-text-normal" href="/dp/B0TEST0001"><span>Ferro gocce 30 ml</span></a></h2>'
        '<div class="a-row"><span>di</span> <span>Laboratori Rossi</span></div>'
        '<div class="a-row"><span>di 4,5 stelle</span></div>'
    )
    assert parse_search_page(html).results[0].brand_raw == "Laboratori Rossi"


def test_product_brand_from_detail_tables():
    bullets = '<div id="detailBullets_feature_div"><ul><li><span>Marca ‏ : ‎ Pharma Uno</span></li></ul></div>'
    assert parse_product_brand(bullets) == "Pharma Uno"
    table = '<table class="prodDetTable"><tr><th>Marca</th><td>‎Acme</td></tr></table>'
    assert parse_product_brand(table) == "Acme"


def test_compact_html_keeps_structure_only():
    from amazon_sov.parser import compact_html

    html = (FIX / "integratore-ferro__p1.html").read_text(encoding="utf-8")
    out = compact_html(html, "B0GENERIC1")
    assert 'data-cy="title-recipe"' in out and "Ferro Liposomiale" in out
    assert "<img" not in out and compact_html(html, "B0NOTHERE0") == ""


def test_brand_recovered_from_full_title_in_image():
    html = _card(
        '<img class="s-image" alt="WeightWorld Ferro Integratore - 400 Compresse - Vitamina C">'
        '<div data-cy="title-recipe"><a class="a-link-normal a-text-normal" href="/dp/B0TEST0001">'
        '<h2><span>Ferro Integratore - 400 Compresse - Vitamina C</span></h2></a></div>'
    )
    item = parse_search_page(html).results[0]
    assert item.brand_raw == "WeightWorld"
    assert item.title == "WeightWorld Ferro Integratore - 400 Compresse - Vitamina C"


def test_same_title_in_image_gives_no_brand():
    html = _card(
        '<img class="s-image" alt="Ferro Integratore - 400 Compresse">'
        '<a class="a-text-normal" href="/dp/B0TEST0001"><h2><span>Ferro Integratore - 400 Compresse</span></h2></a>'
    )
    assert parse_search_page(html).results[0].brand_raw is None
