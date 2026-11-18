from pathlib import Path

from amazon_sov.config import DEFAULT_WEB_EXCLUDE, config_from_dict
from amazon_sov.pipeline import SerpRow
from amazon_sov.products import annotate_products, same_company, verify_brands
from amazon_sov.websearch import detect_google_block, extract_companies, google_url, results_text

FIX = Path(__file__).parent / "fixtures"


def test_results_text_keeps_only_results_and_side_panel():
    text = results_text((FIX / "google_sideral.html").read_text(encoding="utf-8"))
    assert "PharmaNutra S.p.A." in text and "Sede: Pisa" in text
    assert "Google LLC" not in text and "Google Ireland" not in text and "Script Srl" not in text


def test_most_cited_company_wins_and_shops_are_ignored():
    text = results_text((FIX / "google_sideral.html").read_text(encoding="utf-8"))
    candidates = extract_companies(text, "Sideral", DEFAULT_WEB_EXCLUDE)
    assert candidates[0].name == "PharmaNutra S.p.A."
    assert candidates[0].mentions == 3  # S.p.A. ×2 + «Produttore: PHARMANUTRA SPA», «Il Gruppo» unito
    names = [c.name for c in candidates]
    assert any(n.endswith("Junia Pharma S.r.l.") for n in names)  # a volte con la parola prima
    assert not any("Amazon" in n or "Farmacia" in n for n in names)


def test_company_patterns():
    found = [c.name for c in extract_companies(
        "Nutravita Ltd, 1 Apsley Way. Ferro by Nutravita Ltd. Vitabiotics Ltd. Marco sa che. Salus Haus GmbH & Co. KG",
        "Nutravita", DEFAULT_WEB_EXCLUDE)]
    assert found[0] == "Nutravita Ltd"
    assert "Vitabiotics Ltd" in found and "Salus Haus GmbH & Co. KG" in found
    assert not any("Marco" in n for n in found)


def test_google_block_and_url():
    assert detect_google_block("<form id='captcha-form'>", "https://www.google.com/sorry/index") == "captcha"
    assert detect_google_block("<div id='rso'></div>", "https://www.google.com/search?q=x") is None
    assert google_url('"Sideral" integratori') == "https://www.google.com/search?q=%22Sideral%22+integratori&hl=it&gl=it&num=10"


def test_same_company():
    assert same_company("PharmaNutra S.p.A.", "PHARMANUTRA SPA")
    assert same_company("PharmaNutra S.p.A.", "PharmaNutra Group")
    assert not same_company("PharmaNutra S.p.A.", "Junia Pharma S.r.l.")


def row(asin, brand):
    return SerpRow(
        keyword="k", page=1, slot=1, rank=1, organic_rank=1, asin=asin, title=f"{brand} ferro 30 capsule",
        brand_raw=brand, brand=brand, brand_source="serp", sponsored=False, placement="organic", widget=None,
        price=None, list_price=None, rating=None, reviews=None, bought_last_month=None, badges="", relevant=True,
    )


def test_verification_and_google_fallback():
    cfg = config_from_dict({"keywords": [{"term": "k"}]})
    rows = [row("B0A", "Sideral"), row("B0B", "Nutravita"), row("B0C", "Acme"), row("B0D", "Zeta"), row("B0E", "Mai")]
    infos = {"B0A": {"manufacturer": "PharmaNutra S.p.A."}, "B0B": {"manufacturer": "Nutravita Ltd"},
             "B0D": {"manufacturer": "Zeta Srl"}}
    web = {
        "sideral": {"manufacturer": "PHARMANUTRA SPA", "mentions": 4},
        "nutravita": {"manufacturer": "Altro Ltd", "mentions": 2},
        "acme": {"manufacturer": "Acme Pharma S.r.l.", "mentions": 3},
        "zeta": {"manufacturer": None, "mentions": 0},
    }
    annotate_products(rows, cfg, infos, web)
    acme = next(r for r in rows if r.brand == "Acme")
    assert (acme.manufacturer, acme.manufacturer_source) == ("Acme Pharma S.r.l.", "google")
    brands = [{"brand": b} for b in ("Sideral", "Nutravita", "Acme", "Zeta", "Mai")]
    verify_brands(brands, rows, web)
    got = {b["brand"]: b["verification"] for b in brands}
    assert got == {
        "Sideral": "confermato", "Nutravita": "diverso", "Acme": "solo Google",
        "Zeta": "solo Amazon", "Mai": "da cercare su Google",
    }
