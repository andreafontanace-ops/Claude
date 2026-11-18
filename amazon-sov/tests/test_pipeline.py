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
    # marchi mancanti letti dalla pagina prodotto; "" = controllato ma non trovato
    assert store.product_brands() == {"B0GENERIC1": "", "B0FERROLIP": "Ferrolip"}

    html = (tmp_path / "reports" / run_id / "report.html").read_text(encoding="utf-8")
    assert "Pagine non lette" in html and "ferritina — pagina 1: blocked" in html
    assert "1 keyword su 2" in html


def test_resolver_ignores_pages_without_brand():
    res = BrandResolver(CFG, product_page_brands={"B0GENERIC1": ""})
    assert res.resolve("B0GENERIC1", None, "Ferro Liposomiale 30 mg") == (UNKNOWN_BRAND, "unknown")


class BrandFetcher(FakeFetcher):
    def fetch_product(self, asin):
        self.calls.append(("dp", asin))
        return {"B0GENERIC1": '<div id="bylineInfo">Marca: Pharma Uno</div>',
                "B0FERROLIP": (FIX / "product_ferrolip.html").read_text(encoding="utf-8")}.get(asin, "<html></html>")


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

    with open(tmp_path / "reports" / run_id / "sov_marchi.csv", encoding="utf-8-sig") as fh:
        brands = {r["marchio"]: r for r in csv.DictReader(fh, delimiter=";")}
    assert "Pharma Uno" in brands and "(sconosciuto)" not in brands
    after = (tmp_path / "reports" / run_id / "report.html").read_text(encoding="utf-8")
    assert "Marchi da verificare" not in after

    # seconda volta: niente da controllare, nessuna pagina riaperta
    main(args + ["brands", "--out", str(tmp_path / "reports")])
    assert "hanno già un marchio" in capsys.readouterr().out


def test_inspect_latest_page_with_html(tmp_path, capsys):
    run_dir = tmp_path / "data" / "html" / "20990101-000000"
    run_dir.mkdir(parents=True)
    shutil.copy(FIX / "integratore-ferro__p2.html", run_dir / "integratore-ferro__p2.html")
    shutil.copy(FIX / "integratore-ferro__p1.html", run_dir / "integratore-ferro__p1.html")
    main(["-c", str(ROOT / "config.toml"), "--data-dir", str(tmp_path / "data"), "inspect", "--html"])
    out = capsys.readouterr().out
    assert "file: integratore-ferro__p1.html" in out
    assert "[B000SOLGAR]" in out and 'data-cy="title-recipe"' in out
