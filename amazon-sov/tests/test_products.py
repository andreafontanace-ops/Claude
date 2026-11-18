import sqlite3

import pytest

from amazon_sov.config import config_from_dict
from amazon_sov.parser import clean_manufacturer, parse_product_page
from amazon_sov.pipeline import SerpRow
from amazon_sov.products import FormulationClassifier, ManufacturerResolver, annotate_products, manufacturer_key
from amazon_sov.config import DEFAULT_FORMS, DEFAULT_IRON_TYPES, ScoringConfig
from amazon_sov.scoring import NOT_STATED, compute_sov
from amazon_sov.storage import Store

CLF = FormulationClassifier(DEFAULT_FORMS, DEFAULT_IRON_TYPES)


@pytest.mark.parametrize(
    "title, form, iron",
    [
        ("Sideral Forte Integratore di Ferro Sucrosomiale con Vitamina C, 30 Capsule", "Capsule", "Sucrosomiale"),
        ("Nutravita Ferro Bisglicinato 28 mg con Vitamina C – 180 Compresse Vegane", "Compresse", "Bisglicinato"),
        ("Ferrolip® Ferro Liposomiale Gocce 30 ml", "Gocce", "Liposomiale"),
        ("Feroglobin Liquido, Ferro e Vitamine del Gruppo B, 200 ml", "Liquido/sciroppo", None),
        ("Ferro Pirofosfato Stick Orosolubili gusto arancia", "Bustine/stick", "Pirofosfato"),
        ("Ferro per bambini – Gummies alla fragola", "Gommose/masticabili", None),
        ("Ferro chelato bisglicinato + Lattoferrina 60 cps", "Capsule", "Bisglicinato + Lattoferrina"),
        ("Ferro 14 mg 200ml", "Liquido/sciroppo", None),
        ("Ferro alto dosaggio", None, None),
    ],
)
def test_formulation_from_title(title, form, iron):
    assert CLF.form(title) == form
    assert CLF.iron_type(title) == iron


def test_form_falls_back_to_product_page():
    assert CLF.form("Ferro alto dosaggio", "Capsula") == "Capsule"
    assert CLF.form("Ferro alto dosaggio", None) is None


def test_custom_rules_from_config():
    cfg = config_from_dict({
        "keywords": [{"term": "ferro"}],
        "formulation": {"forms": {"Fiale bevibili": ["fiale"]}, "iron_types": {"Marino": ["alga"]}},
    })
    clf = FormulationClassifier.from_config(cfg)
    assert clf.form("Ferro 10 fiale") == "Fiale bevibili"
    assert clf.form("Ferro 30 capsule") is None  # le regole della config sostituiscono quelle di default
    assert clf.iron_type("Ferro da alga marina") == "Marino"


@pytest.mark.parametrize(
    "raw, clean",
    [
        ("Ferrolip Pharma S.r.l., Via Roma 1, 20100 Milano MI", "Ferrolip Pharma S.r.l."),
        ("PharmaNutra S.p.A.", "PharmaNutra S.p.A."),
        ("Salus Haus GmbH & Co. KG; Bahnhofstr. 24, 83052 Bruckmühl", "Salus Haus GmbH & Co. KG"),
        ("Vitabiotics Ltd, 1 Apsley Way, London", "Vitabiotics Ltd"),
        ("Pharma Srl, Vianello Group", "Pharma Srl, Vianello Group"),
        ("Pharma Srl, Via Verdi", "Pharma Srl"),
        ("", None),
    ],
)
def test_clean_manufacturer(raw, clean):
    assert clean_manufacturer(raw) == clean


def test_product_page_tech_table():
    html = '<table class="prodDetTable"><tr><th>Produttore</th><td>‎Acme Srl</td></tr><tr><th>Forma</th><td>Compressa</td></tr></table>'
    info = parse_product_page(html)
    assert (info.manufacturer, info.item_form, info.brand) == ("Acme Srl", "Compressa", None)


def test_same_manufacturer_written_differently():
    assert manufacturer_key("PharmaNutra S.p.A.") == manufacturer_key("PHARMANUTRA SPA") == "pharmanutra"
    assert manufacturer_key("Salus Haus GmbH & Co. KG") == "salus haus"


def row(asin, brand, rank, title="Ferro 30 capsule"):
    return SerpRow(
        keyword="k", page=1, slot=rank, rank=rank, organic_rank=rank, asin=asin, title=title, brand_raw=brand,
        brand=brand, brand_source="serp", sponsored=False, placement="organic", widget=None, price=None,
        list_price=None, rating=None, reviews=None, bought_last_month=None, badges="", relevant=True,
    )


def test_manufacturer_precedence_and_brand_inheritance():
    cfg = config_from_dict({
        "keywords": [{"term": "k"}],
        "manufacturers": {"by_brand": {"Sideral": "PharmaNutra S.p.A."}, "asin_overrides": {"B0OVERRIDE": "Mano Srl"}},
    })
    infos = {
        "B0SIDERAL1": {"manufacturer": "Altro nome"},  # la config per marchio vince sulla pagina
        "B0NUTRA001": {"manufacturer": "Nutravita Ltd"},
        "B0NUTRA003": {"manufacturer": "NUTRAVITA LTD."},
    }
    rows = [
        row("B0SIDERAL1", "Sideral", 1), row("B0NUTRA001", "Nutravita", 2), row("B0NUTRA002", "Nutravita", 3),
        row("B0NUTRA003", "Nutravita", 4), row("B0OVERRIDE", "Nutravita", 5), row("B0NOBODY01", "Ignoto", 6),
    ]
    ManufacturerResolver(cfg, infos).apply(rows)
    got = {r.asin: (r.manufacturer, r.manufacturer_source) for r in rows}
    assert got["B0SIDERAL1"] == ("PharmaNutra S.p.A.", "config")
    assert got["B0NUTRA001"] == ("Nutravita Ltd", "product_page")
    assert got["B0NUTRA003"] == ("Nutravita Ltd", "product_page")  # stesso produttore, un solo nome
    assert got["B0NUTRA002"] == ("Nutravita Ltd", "same_brand")
    assert got["B0OVERRIDE"] == ("Mano Srl", "override")
    assert got["B0NOBODY01"] == (None, None)


def test_sov_by_manufacturer_and_form():
    cfg = config_from_dict({"keywords": [{"term": "k"}]})
    rows = [row("B0A0000001", "A", 1, "A ferro 30 capsule"), row("B0B0000001", "B", 2, "B ferro gocce"),
            row("B0C0000001", "C", 3, "C ferro")]
    annotate_products(rows, cfg, {"B0A0000001": {"manufacturer": "Gruppo X"}, "B0B0000001": {"manufacturer": "Gruppo X"}})
    res = compute_sov(rows, {"k": 1.0}, ScoringConfig())
    makers = {g["brand"]: g for g in res.groups["manufacturers"]}
    assert makers["Gruppo X"]["sov_total"] == pytest.approx((1 + 1 / 2) / (1 + 1 / 2 + 1 / 3))
    assert makers["Gruppo X"]["brands"] == ["A", "B"]
    assert [g["brand"] for g in res.groups["manufacturers"]][-1] == NOT_STATED
    forms = {g["brand"]: g["sov_total"] for g in res.groups["forms"]}
    assert set(forms) == {"Capsule", "Gocce", NOT_STATED}


def test_old_database_is_migrated(tmp_path):
    path = tmp_path / "sov.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE serp (run_id TEXT, keyword TEXT, asin TEXT);"
        "INSERT INTO serp VALUES ('r1', 'k', 'B0A0000001');"
        "CREATE TABLE product_brands (asin TEXT PRIMARY KEY, brand TEXT NOT NULL, updated_at TEXT);"
        "INSERT INTO product_brands VALUES ('B0A0000001', 'Acme', 'x'), ('B0B0000001', '', 'x');"
    )
    conn.commit()
    conn.close()
    store = Store(path)
    cols = {r["name"] for r in store.conn.execute("PRAGMA table_info(serp)")}
    assert {"manufacturer", "form", "iron_type", "manufacturer_source"} <= cols
    info = store.product_info()
    assert info["B0A0000001"]["brand"] == "Acme" and info["B0A0000001"]["checked_at"] is None
    assert info["B0B0000001"]["brand"] is None
    assert store.product_brands() == {"B0A0000001": "Acme"}
