import csv
import shutil
from pathlib import Path

from amazon_sov.brands import UNKNOWN_BRAND, BrandResolver, RelevanceFilter, normalize
from amazon_sov.cli import main
from amazon_sov.config import load_config
from amazon_sov.parser import parse_search_page
from amazon_sov.pipeline import build_rows
from amazon_sov.storage import Store

ROOT = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures"
CFG = load_config(ROOT / "config.toml")


def parsed(name):
    return parse_search_page((FIX / name).read_text(encoding="utf-8"))


def test_normalize():
    assert normalize("Nature’s Bounty®") == "nature's bounty"
    assert normalize("  FÉRRO   Bisglicinato ") == "ferro bisglicinato"


def test_relevance_filter():
    rel = RelevanceFilter(CFG.relevance_include, CFG.relevance_exclude)
    assert rel("Ferro Bisglicinato 28 mg")
    assert rel("Gentle Iron 25 mg")
    assert not rel("Multivitaminico Uomo Senza Ferro")
    assert not rel("Ferrovia giocattolo")  # solo parole intere
    assert not rel("Vitamina D3")


def test_brand_resolution_precedence():
    cfg = load_config(ROOT / "config.toml")
    cfg.asin_overrides["B0OVERRIDE"] = "Marchio Corretto"
    res = BrandResolver(cfg, product_page_brands={"B0PAGE0001": "Ferrolip"})
    assert res.resolve("B0OVERRIDE", "Sideral", "Sideral Forte") == ("Marchio Corretto", "override")
    assert res.resolve("B0X", "SIDERAL", "qualcosa") == ("Sideral", "serp")
    assert res.resolve("B0PAGE0001", None, "Ferro liposomiale") == ("Ferrolip", "product_page")
    assert res.resolve("B0X", None, "Gentle Iron by Solgar") == ("Solgar", "alias")
    assert res.resolve("B0X", None, "Ferrolip® gocce") == ("Ferrolip", "title_guess")
    assert res.resolve("B0X", None, "Integratore di Ferro 60 compresse") == (UNKNOWN_BRAND, "unknown")
    # stesso marchio sconosciuto scritto in modi diversi -> un nome solo
    assert res.canonical("ACME Labs") == res.canonical("Acme labs") == "ACME Labs"


def test_build_rows_continues_ranks_across_pages():
    resolver = BrandResolver(CFG)
    rel = RelevanceFilter(CFG.relevance_include, CFG.relevance_exclude)
    rows = build_rows("integratore ferro", [parsed("integratore-ferro__p2.html"), parsed("integratore-ferro__p1.html")], resolver, rel)
    slots = [r for r in rows if r.placement != "widget"]
    assert [r.rank for r in slots] == list(range(1, 12))
    assert [r.organic_rank for r in slots] == [None, 1, 2, 3, None, 4, 5, 6, 7, None, 8]
    p2_first = slots[8]
    assert (p2_first.asin, p2_first.page, p2_first.brand) == ("B08NUTRAV9", 2, "Nutravita")
    widgets = [r for r in rows if r.placement == "widget"]
    assert all(r.rank is None and r.organic_rank is None for r in widgets)


def test_build_rows_drops_pages_after_a_gap():
    resolver = BrandResolver(CFG)
    rel = RelevanceFilter(CFG.relevance_include, CFG.relevance_exclude)
    assert build_rows("integratore ferro", [parsed("integratore-ferro__p2.html")], resolver, rel) == []


def test_parse_command_end_to_end(tmp_path, capsys):
    html_dir = tmp_path / "pagine"
    html_dir.mkdir()
    for name in ("integratore-ferro__p1.html", "integratore-ferro__p2.html", "captcha.html", "product_ferrolip.html"):
        shutil.copy(FIX / name, html_dir / name)

    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data")]
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])

    store = Store(tmp_path / "data" / "sov.sqlite")
    run_id = store.latest_run_id()
    out = tmp_path / "reports" / run_id
    for name in ("report.html", "serp.csv", "sov_prodotti.csv", "sov_marchi.csv", "sov_keyword_marchi.csv"):
        assert (out / name).exists(), name

    with open(out / "sov_marchi.csv", encoding="utf-8-sig") as fh:
        brands = list(csv.DictReader(fh, delimiter=";"))
    names = [b["marchio"] for b in brands]
    assert names[0] == "Sideral"  # annuncio in posizione 1
    assert names[-1] == "(non pertinenti)" and brands[-1]["posizione"] == ""
    assert "," in brands[0]["sov_totale_%"]  # virgola decimale per Excel italiano
    total = sum(float(b["sov_totale_%"].replace(",", ".")) for b in brands)
    assert abs(total - 100) < 0.01

    html = (out / "report.html").read_text(encoding="utf-8")
    assert "Sideral" in html and "integratore ferro" in html
    assert "nessun risultato utilizzabile" not in html  # contano solo le keyword di questa esecuzione

    # seconda esecuzione: il report mostra il confronto con la precedente
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])
    latest = Store(tmp_path / "data" / "sov.sqlite").latest_run_id()
    html2 = (tmp_path / "reports" / latest / "report.html").read_text(encoding="utf-8")
    assert "Δ vs prec." in html2

    main(args + ["runs"])
    assert "html" in capsys.readouterr().out


class FakeFetcher:
    """Sostituisce il browser: serve le pagine di esempio e simula un blocco su 'ferritina'."""

    interactive = True

    def __init__(self, *args, **kwargs):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def fetch_search(self, keyword, page):
        from amazon_sov.fetcher import BlockedError

        self.calls.append((keyword, page))
        if keyword == "ferritina":
            raise BlockedError("Amazon ha mostrato una verifica (captcha)")
        return (FIX / f"integratore-ferro__p{page}.html").read_text(encoding="utf-8")

    def fetch_google(self, query):
        self.calls.append(("google", query))
        brand = query.split('"')[1]
        company = {"Sideral": "PharmaNutra S.p.A.", "Nutravita": "Nutravita Ltd", "Solgar": "Solgar Italia S.r.l."}.get(brand)
        snippet = f"{brand} è un marchio di {company}. Prodotto da {company}." if company else "Nessuna azienda qui."
        return f'<div id="search"><div id="rso"><div class="g">{snippet}</div></div></div>'

    def fetch_product(self, asin):
        self.calls.append(("dp", asin))
        if asin == "B0FERROLIP":
            return (FIX / "product_ferrolip.html").read_text(encoding="utf-8")
        return "<html><body><span id='productTitle'>Senza marchio</span></body></html>"


def test_crawl_command_with_fake_browser(tmp_path, monkeypatch):
    import amazon_sov.fetcher as fetcher_mod

    monkeypatch.setattr(fetcher_mod, "BrowserFetcher", FakeFetcher)
    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data")]
    main(args + ["crawl", "--keyword", "integratore ferro", "--keyword", "ferritina", "--pages", "2",
                 "--out", str(tmp_path / "reports")])

    store = Store(tmp_path / "data" / "sov.sqlite")
    run_id = store.latest_run_id()
    pages = {(p["keyword"], p["page"]): p["status"] for p in store.pages(run_id)}
    assert pages == {("integratore ferro", 1): "ok", ("integratore ferro", 2): "ok", ("ferritina", 1): "blocked"}
    assert (tmp_path / "data" / "html" / run_id / "integratore-ferro__p2.html").exists()
    assert len([r for r in store.rows(run_id) if r.placement != "widget"]) == 11
    # pagine prodotto: i due senza marchio sicuro + il prodotto più visibile di ogni marchio
    info = store.product_info()
    assert set(info) == {"B0GENERIC1", "B0FERROLIP", "B07SIDERAL", "B08NUTRAV1", "B000SOLGAR", "B01FEROGLO", "B0FLORADIX"}
    assert info["B0FERROLIP"]["brand"] == "Ferrolip"
    assert info["B0FERROLIP"]["manufacturer"] == "Ferrolip Pharma S.r.l."
    assert info["B0FERROLIP"]["item_form"] == "Liquido"
    assert info["B0GENERIC1"]["brand"] is None and info["B0GENERIC1"]["checked_at"]
    # poi una ricerca Google per ogni marchio di ferro
    web = store.brand_web()
    assert web["sideral"]["manufacturer"] == "PharmaNutra S.p.A." and web["sideral"]["mentions"] == 2
    assert web["floradix"]["manufacturer"] is None
    assert UNKNOWN_BRAND not in {w["brand"] for w in web.values()}

    html = (tmp_path / "reports" / run_id / "report.html").read_text(encoding="utf-8")
    assert "Pagine non lette" in html and "ferritina — pagina 1: blocked" in html
    assert "1 keyword su 2" in html


def test_resolver_ignores_pages_without_brand():
    res = BrandResolver(CFG, product_page_brands={"B0GENERIC1": ""})
    assert res.resolve("B0GENERIC1", None, "Ferro Liposomiale 30 mg") == (UNKNOWN_BRAND, "unknown")


MAKERS = {"B07SIDERAL": "PharmaNutra S.p.A.", "B08NUTRAV1": "Nutravita Ltd", "B000SOLGAR": "Solgar Italia Srl",
          "B01FEROGLO": "Vitabiotics Ltd", "B0FLORADIX": "Salus Haus GmbH", "B0GENERIC1": "Pharma Uno S.r.l."}


class BrandFetcher(FakeFetcher):
    def fetch_product(self, asin):
        self.calls.append(("dp", asin))
        if asin == "B0FERROLIP":
            return (FIX / "product_ferrolip.html").read_text(encoding="utf-8")
        byline = '<div id="bylineInfo">Marca: Pharma Uno</div>' if asin == "B0GENERIC1" else ""
        maker = MAKERS.get(asin, "")
        return f'{byline}<div id="detailBullets_feature_div"><ul><li>Produttore \u200f : \u200e {maker}</li></ul></div>'


def test_brands_command_fills_unknown_brands(tmp_path, monkeypatch, capsys):
    import amazon_sov.fetcher as fetcher_mod

    html_dir = tmp_path / "pagine"
    html_dir.mkdir()
    for name in ("integratore-ferro__p1.html", "integratore-ferro__p2.html"):
        shutil.copy(FIX / name, html_dir / name)
    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data")]
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])
    run_id = Store(tmp_path / "data" / "sov.sqlite").latest_run_id()
    before = (tmp_path / "reports" / run_id / "report.html").read_text(encoding="utf-8")
    assert "Marchi da verificare" in before and "B0GENERIC1" in before

    monkeypatch.setattr(fetcher_mod, "BrowserFetcher", BrandFetcher)
    main(args + ["brands", "--out", str(tmp_path / "reports")])

    out = tmp_path / "reports" / run_id
    with open(out / "sov_marchi.csv", encoding="utf-8-sig") as fh:
        brands = {r["marchio"]: r for r in csv.DictReader(fh, delimiter=";")}
    assert "Pharma Uno" in brands and "(sconosciuto)" not in brands
    assert brands["Sideral"]["produttore"] == "PharmaNutra S.p.A."
    with open(out / "sov_produttori.csv", encoding="utf-8-sig") as fh:
        makers = {r["produttore"]: r for r in csv.DictReader(fh, delimiter=";")}
    assert {"PharmaNutra S.p.A.", "Nutravita Ltd", "Ferrolip Pharma S.r.l.", "Pharma Uno S.r.l."} <= set(makers)
    assert makers["Nutravita Ltd"]["n_prodotti"] == "2"  # il secondo prodotto Nutravita eredita il produttore
    with open(out / "sov_prodotti.csv", encoding="utf-8-sig") as fh:
        products = {r["asin"]: r for r in csv.DictReader(fh, delimiter=";")}
    assert (products["B0FERROLIP"]["forma"], products["B0FERROLIP"]["tipo_ferro"]) == ("Gocce", "Liposomiale")
    assert products["B08NUTRAV9"]["fonte_produttore"] == "same_brand"
    for name in ("sov_forme.csv", "sov_tipi_ferro.csv"):
        assert (out / name).exists()
    after = (out / "report.html").read_text(encoding="utf-8")
    assert "Marchi da verificare" not in after
    assert "Produttori per share of voice" in after and "Tipo di ferro" in after

    # seconda volta: niente da controllare, nessuna pagina riaperta
    main(args + ["brands", "--out", str(tmp_path / "reports")])
    assert "Niente da controllare" in capsys.readouterr().out


def test_inspect_latest_page_with_html(tmp_path, capsys):
    run_dir = tmp_path / "data" / "html" / "20990101-000000"
    run_dir.mkdir(parents=True)
    shutil.copy(FIX / "integratore-ferro__p2.html", run_dir / "integratore-ferro__p2.html")
    shutil.copy(FIX / "integratore-ferro__p1.html", run_dir / "integratore-ferro__p1.html")
    main(["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data"), "inspect", "--html"])
    out = capsys.readouterr().out
    assert "file: integratore-ferro__p1.html" in out
    assert "[B000SOLGAR]" in out and 'data-cy="title-recipe"' in out


def test_update_command_replaces_code_and_backs_up_config(tmp_path, capsys):
    import zipfile

    # ZIP come quello di GitHub: <repo>-<branch>/amazon-sov/...
    archive = tmp_path / "branch.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Claude-x/README.md", "altro progetto")
        zf.writestr("Claude-x/amazon-sov/amazon_sov/__init__.py", "__version__ = '9.9'\n")
        zf.writestr("Claude-x/amazon-sov/amazon_sov/nuovo.py", "X = 1\n")
        zf.writestr("Claude-x/amazon-sov/amazon_sov/__pycache__/cli.cpython-313.pyc", b"junk")
        zf.writestr("Claude-x/amazon-sov/config.toml", "# nuova\n")
    project = tmp_path / "amazon-sov"
    (project / "amazon_sov").mkdir(parents=True)
    (project / "amazon_sov" / "__init__.py").write_text("__version__ = '0.1'\n")
    (project / "config.toml").write_text("# mia\n")
    (project / "data").mkdir()
    (project / "data" / "sov.sqlite").write_text("dati")

    main(["update", "--url", archive.resolve().as_uri(), "--target", str(project)])

    assert (project / "amazon_sov" / "__init__.py").read_text() == "__version__ = '9.9'\n"
    assert (project / "amazon_sov" / "nuovo.py").exists()
    assert not (project / "amazon_sov" / "__pycache__").exists()
    assert (project / "config.toml").read_text() == "# nuova\n"
    assert (project / "config.backup.toml").read_text() == "# mia\n"
    assert (project / "data" / "sov.sqlite").read_text() == "dati"
    assert not (project / "README.md").exists()
    assert "Aggiornato (2 file)" in capsys.readouterr().out


import pytest


@pytest.mark.parametrize(
    "title, expected",
    [
        ("WeightWorld Ferro Bisglicinato 28mg", ("WeightWorld", "title_guess")),
        ("Ferro WeightWorld 180 compresse", ("WeightWorld", "title_guess")),  # seconda parola
        ("Ferrolip® Ferro Liposomiale", ("Ferrolip", "title_guess")),  # inizia con "ferr" ma è un marchio
        ("Dr. Giorgini Ferro gocce", ("Dr Giorgini", "title_guess")),
        ("Ferro Integratore - 400 Compresse - Vitamina C", (UNKNOWN_BRAND, "unknown")),
        ("Ferro Alto Dosaggio 30 mg", (UNKNOWN_BRAND, "unknown")),
        ("Integratore Ferro Bisglicinato Vegano", (UNKNOWN_BRAND, "unknown")),
        ("Ferro 28mg Vegano", (UNKNOWN_BRAND, "unknown")),  # oltre la seconda parola non si cerca
        ("Pharma Nord Bio-Ferro 30 compresse", ("Pharma Nord", "title_guess")),  # prime due parole
        ("Named Sport Iron 30 cpr", ("Named Sport", "title_guess")),
        ("Bio Nutrition Ferro", ("Bio Nutrition", "title_guess")),
        ("BrandX Gentle Iron", ("BrandX", "title_guess")),  # «Gentle» descrive il prodotto
    ],
)
def test_brand_guess_first_or_second_word(title, expected):
    assert BrandResolver(CFG).resolve("B0X", None, title) == expected


def test_product_page_with_hidden_error_text_is_not_blocked():
    from amazon_sov.parser import detect_block

    product = '<span id="productTitle">Ferro</span><div style="display:none">Siamo spiacenti, si è verificato un errore. Amazon</div>'
    assert detect_block(product) is None
    dog = "<html><title>Amazon.it</title><body>Siamo spiacenti. Indirizzo non valido. Amazon</body></html>"
    assert detect_block(dog) == "error"


def test_unknown_brand_is_listed_last_without_rank(tmp_path):
    html_dir = tmp_path / "pagine"
    html_dir.mkdir()
    shutil.copy(FIX / "integratore-ferro__p1.html", html_dir / "integratore-ferro__p1.html")
    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data")]
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])
    run_id = Store(tmp_path / "data" / "sov.sqlite").latest_run_id()
    with open(tmp_path / "reports" / run_id / "sov_marchi.csv", encoding="utf-8-sig") as fh:
        brands = list(csv.DictReader(fh, delimiter=";"))
    unknown = next(b for b in brands if b["marchio"] == UNKNOWN_BRAND)
    assert unknown["posizione"] == ""
    assert brands.index(unknown) > max(i for i, b in enumerate(brands) if b["posizione"])
    html = (tmp_path / "reports" / run_id / "report.html").read_text(encoding="utf-8")
    assert "Marchio da verificare" in html and "pagina prodotto da leggere" in html


def test_lookup_starts_with_products_without_brand(tmp_path):
    from amazon_sov.cli import lookup_targets

    store = Store(tmp_path / "s.sqlite")
    resolver = BrandResolver(CFG)
    rel = RelevanceFilter(CFG.relevance_include, CFG.relevance_exclude)
    rows = build_rows("integratore ferro", [parsed("integratore-ferro__p1.html")], resolver, rel)
    targets = lookup_targets(store, rows, CFG)
    assert targets[:2] == ["B0GENERIC1", "B0FERROLIP"]  # senza marchio sicuro, dal più visibile
    assert set(targets[2:]) == {"B07SIDERAL", "B08NUTRAV1", "B000SOLGAR", "B01FEROGLO"}


def test_google_command_fills_verification(tmp_path, monkeypatch, capsys):
    import amazon_sov.fetcher as fetcher_mod

    html_dir = tmp_path / "pagine"
    html_dir.mkdir()
    shutil.copy(FIX / "integratore-ferro__p1.html", html_dir / "integratore-ferro__p1.html")
    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data")]
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])
    monkeypatch.setattr(fetcher_mod, "BrowserFetcher", BrandFetcher)
    main(args + ["brands", "--out", str(tmp_path / "reports")])
    main(args + ["google", "--out", str(tmp_path / "reports")])

    run_id = Store(tmp_path / "data" / "sov.sqlite").latest_run_id()
    with open(tmp_path / "reports" / run_id / "sov_marchi.csv", encoding="utf-8-sig") as fh:
        brands = {r["marchio"]: r for r in csv.DictReader(fh, delimiter=";")}
    assert brands["Sideral"]["produttore_google"] == "PharmaNutra S.p.A."
    assert brands["Sideral"]["verifica_google"] == "confermato"
    assert brands["Feroglobin"]["verifica_google"] == "solo Amazon"
    html = (tmp_path / "reports" / run_id / "report.html").read_text(encoding="utf-8")
    assert "Verifica dei produttori" in html and "✓ Google" in html

    main(args + ["google", "--out", str(tmp_path / "reports")])
    assert "già stati cercati" in capsys.readouterr().out


def test_brand_from_product_page_maker_or_none():
    from amazon_sov.brands import GENERIC_BRAND, brand_from_company

    assert brand_from_company("WeightWorld Ltd") == "WeightWorld"
    assert brand_from_company("Salus Haus GmbH & Co. KG") == "Salus Haus"
    assert brand_from_company("PharmaNutra S.p.A.") == "PharmaNutra"
    infos = {
        "B0GENERICO": {"brand": "Generico", "checked_at": "x"},
        "B0MAKER001": {"brand": None, "manufacturer": "Acme Labs S.r.l.", "checked_at": "x"},
        "B0NOTHING1": {"brand": None, "manufacturer": None, "checked_at": "x"},
    }
    res = BrandResolver(CFG, product_info=infos)
    assert res.resolve("B0GENERICO", None, "WeightWorld Ferro") == (GENERIC_BRAND, "product_page")
    assert res.resolve("B0MAKER001", None, "Ferro Integratore 400 compresse") == ("Acme Labs", "product_page_maker")
    assert res.resolve("B0NOTHING1", None, "Ferro Integratore 400 compresse") == (GENERIC_BRAND, "product_page")
    assert res.resolve("B0NOTHING1", None, "Zenement Ferro") == ("Zenement", "title_guess")
    assert res.resolve("B0NEVER001", None, "Ferro Integratore 400 compresse") == (UNKNOWN_BRAND, "unknown")


def test_report_reads_missing_brands_then_has_no_unknown(tmp_path, monkeypatch):
    import amazon_sov.fetcher as fetcher_mod

    html_dir = tmp_path / "pagine"
    html_dir.mkdir()
    shutil.copy(FIX / "integratore-ferro__p1.html", html_dir / "integratore-ferro__p1.html")
    args = ["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data")]
    main(args + ["parse", str(html_dir), "--out", str(tmp_path / "reports")])

    calls = []

    class GenericFetcher(FakeFetcher):
        def fetch_product(self, asin):
            calls.append(asin)
            return '<span id="productTitle">x</span><a id="bylineInfo">Marca: Generico</a>'

    monkeypatch.setattr(fetcher_mod, "BrowserFetcher", GenericFetcher)
    main(args + ["report", "--completa", "--out", str(tmp_path / "reports")])
    assert sorted(calls) == ["B0FERROLIP", "B0GENERIC1"]  # solo i prodotti senza marchio sicuro

    run_id = Store(tmp_path / "data" / "sov.sqlite").latest_run_id()
    with open(tmp_path / "reports" / run_id / "sov_marchi.csv", encoding="utf-8-sig") as fh:
        names = [r["marchio"] for r in csv.DictReader(fh, delimiter=";")]
    assert UNKNOWN_BRAND not in names and "(senza marchio)" in names

    # senza --completa e senza terminale non apre il browser
    calls.clear()
    main(args + ["report", "--out", str(tmp_path / "reports")])
    assert calls == []
