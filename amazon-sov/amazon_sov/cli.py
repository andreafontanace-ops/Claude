"""Riga di comando: crawl, parse, report, inspect, runs."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

from . import export
from .brands import UNKNOWN_BRAND, BrandResolver, RelevanceFilter, normalize
from .config import Config, load_config
from .parser import ParsedPage, compact_html, parse_product_page, parse_search_page
from .pipeline import SerpRow, build_rows, reclassify
from .products import annotate_products
from .report import pct, render_report
from .scoring import NON_RELEVANT, compute_sov
from .storage import Store

log = logging.getLogger("amazon_sov")


def slug(text: str) -> str:
    return normalize(text).replace(" ", "-").replace("'", "") or "keyword"


def _filters(cfg: Config, store: Store) -> tuple[BrandResolver, RelevanceFilter]:
    return (
        BrandResolver(cfg, store.product_brands()),
        RelevanceFilter(cfg.relevance_include, cfg.relevance_exclude),
    )


# --------------------------------------------------------------------------- report


def make_report(store: Store, cfg: Config, run_id: str, out_root: Path, denominator: str, top: int) -> Path:
    resolver, relevance = _filters(cfg, store)
    infos = store.product_info()
    rows = annotate_products(reclassify(store.rows(run_id), resolver, relevance), cfg, infos)
    if not rows:
        raise SystemExit(f"L'esecuzione {run_id} non ha risultati: niente da calcolare.")
    run = store.run_info(run_id) or {"run_id": run_id}
    attempted = json.loads(run.get("keywords") or "[]") or sorted({r.keyword for r in rows})
    weights = {kw: cfg.keyword_weights.get(kw, 1.0) for kw in attempted}
    result = compute_sov(rows, weights, cfg.scoring, denominator)
    for p in result.products:
        p["page_checked"] = bool((infos.get(p["asin"]) or {}).get("checked_at"))

    prev_id = store.previous_run_id(run_id)
    if prev_id:
        prev_rows = annotate_products(reclassify(store.rows(prev_id), resolver, relevance), cfg, infos)
        prev = compute_sov(prev_rows, weights, cfg.scoring, denominator)
        prev_p = {p["asin"]: p["sov_total"] for p in prev.products}
        for p in result.products:
            p["delta_pp"] = p["sov_total"] - prev_p[p["asin"]] if p["asin"] in prev_p else None
        for g, items in result.groups.items():
            prev_g = {b["brand"]: b["sov_total"] for b in prev.groups[g]}
            for b in items:
                b["delta_pp"] = b["sov_total"] - prev_g[b["brand"]] if b["brand"] in prev_g else None

    out_dir = out_root / run_id
    export.write_all(out_dir, rows, result, cfg.csv_dialect)
    html = render_report(result, cfg, weights, run, store.pages(run_id), prev_id, top)
    report_path = out_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    _print_summary(result)
    print(f"\nReport: {report_path.resolve()}\nCSV:    {out_dir.resolve()}")
    return report_path


def _print_summary(result) -> None:
    brands = [b for b in result.brands if b["brand"] != NON_RELEVANT][:10]
    products = [p for p in result.products if p["relevant"]][:10]
    print(f"\nKeyword analizzate: {len(result.keywords_scored)}  ·  slot sponsorizzati: {pct(result.meta['sponsored_slot_share'], 0)}")
    if result.keywords_empty:
        print("Senza risultati: " + ", ".join(result.keywords_empty))
    print("\nMarchi                         SoV tot.  organica  ads    % da ads")
    for i, b in enumerate(brands, 1):
        print(f"{i:>2}. {b['brand'][:26]:<26} {pct(b['sov_total']):>8} {pct(b['sov_organic']):>9} {pct(b['sov_paid']):>6} {pct(b['ads_share'], 0):>8}")
    print("\nProdotti                                                    SoV tot.  miglior pos.")
    for i, p in enumerate(products, 1):
        label = f"{p['brand']} – {p['title']}"
        print(f"{i:>2}. {label[:55]:<55} {pct(p['sov_total'], 2):>8} {str(p['best_organic_rank'] or '–'):>8}")


# --------------------------------------------------------------------------- crawl


def cmd_crawl(args, cfg: Config) -> None:
    from .fetcher import BlockedError, BrowserFetcher

    data_dir = Path(args.data_dir)
    store = Store(data_dir / "sov.sqlite")
    resolver, relevance = _filters(cfg, store)
    keywords = cfg.keywords
    if args.keyword:
        wanted = {normalize(k) for k in args.keyword}
        keywords = [k for k in keywords if normalize(k.term) in wanted]
        if not keywords:
            raise SystemExit("Nessuna delle keyword indicate è in configurazione")
    pages = args.pages or cfg.crawl.pages

    run_id = store.create_run("crawl", cfg.domain, [k.term for k in keywords])
    html_dir = data_dir / "html" / run_id
    html_dir.mkdir(parents=True, exist_ok=True)
    print(f"Esecuzione {run_id}: {len(keywords)} keyword × fino a {pages} pagine")

    all_rows: list[SerpRow] = []
    stop = False
    try:
        with BrowserFetcher(cfg, data_dir / "browser-profile", headless=args.headless or None) as fetcher:
            for kw in keywords:
                if stop:
                    break
                parsed_pages: list[ParsedPage] = []
                for page_no in range(1, pages + 1):
                    try:
                        html = fetcher.fetch_search(kw.term, page_no)
                    except BlockedError as exc:
                        log.warning("%s", exc)
                        store.log_page(run_id, kw.term, page_no, "blocked", 0, None)
                        stop = "tetto" in str(exc) or not fetcher.interactive
                        break
                    path = html_dir / f"{slug(kw.term)}__p{page_no}.html"
                    path.write_text(html, encoding="utf-8")
                    parsed = parse_search_page(html, keyword=kw.term, page=page_no)
                    status = "ok" if parsed.results else (f"blocked:{parsed.blocked}" if parsed.blocked else "empty")
                    store.log_page(run_id, kw.term, page_no, status, len(parsed.results), str(path))
                    parsed_pages.append(parsed)
                    if not parsed.results:
                        break
                rows = build_rows(kw.term, parsed_pages, resolver, relevance)
                store.replace_rows(run_id, kw.term, rows)
                all_rows += rows
                n_sp = sum(1 for r in rows if r.sponsored and r.placement != "widget")
                n_res = sum(1 for r in rows if r.placement != "widget")
                print(f"  {kw.term:<28} {n_res:>3} risultati ({n_sp} sponsorizzati)")

            lookup = cfg.crawl.product_pages if args.product_pages is None else args.product_pages
            if lookup > 0 and not stop:
                _lookup_products(fetcher, store, all_rows, cfg, lookup, data_dir / "html" / "prodotti")
    except KeyboardInterrupt:
        print("\nInterrotto: calcolo la SoV su quanto già scaricato.")
    store.finish_run(run_id)
    if store.rows(run_id):
        make_report(store, cfg, run_id, Path(args.out), args.denominator, args.top)
    else:
        print("Nessun risultato scaricato: controlla le pagine salvate in", html_dir)


def lookup_targets(store: Store, rows: list[SerpRow], cfg: Config) -> list[str]:
    """Pagine prodotto da aprire, dal prodotto più visibile:
    - prodotti di ferro con marchio sconosciuto o stimato dal titolo;
    - per ogni marchio senza produttore noto, il suo prodotto più visibile (il produttore vale per tutto il marchio).
    """
    infos = store.product_info()
    checked = {a for a, i in infos.items() if i.get("checked_at")}
    best: dict[str, int] = {}
    brand_of: dict[str, str] = {}
    for r in rows:
        if r.relevant:
            best[r.asin] = min(best.get(r.asin, 10**6), r.rank or 10**5)
            brand_of[r.asin] = r.brand
    need_brand = {r.asin for r in rows if r.relevant and r.brand_source in ("title_guess", "unknown")}

    known = {normalize(b) for b in cfg.manufacturer_by_brand}
    misses: dict[str, int] = defaultdict(int)
    for asin, brand in brand_of.items():
        info = infos.get(asin) or {}
        if info.get("manufacturer"):
            known.add(normalize(brand))
        elif asin in checked:
            misses[brand] += 1
    per_brand: dict[str, str] = {}
    for asin in sorted(best, key=lambda a: (best[a], a)):
        brand = brand_of[asin]
        if brand == UNKNOWN_BRAND or normalize(brand) in known or misses[brand] >= 2 or asin in checked:
            continue  # dopo due pagine senza produttore per lo stesso marchio, lascia perdere
        per_brand.setdefault(brand, asin)
    # prima i prodotti senza marchio (cambiano la classifica), poi un prodotto per marchio senza produttore
    first = sorted(need_brand - checked, key=lambda a: (best.get(a, 10**6), a))
    then = sorted(set(per_brand.values()) - checked - need_brand, key=lambda a: (best.get(a, 10**6), a))
    return first + then


def _lookup_products(
    fetcher, store: Store, rows: list[SerpRow], cfg: Config, limit: int, debug_dir: Path | None = None
) -> int:
    """Apre le pagine prodotto e salva marchio, produttore e forma."""
    from .fetcher import BlockedError

    targets = lookup_targets(store, rows, cfg)
    todo = targets[:limit]
    if not todo:
        return 0
    print(f"\nLeggo marchio e produttore dalla pagina prodotto di {len(todo)} prodotti…")
    done = brands = makers = 0
    empty: list[str] = []
    blocked = False
    for asin in todo:
        try:
            html = fetcher.fetch_product(asin)
        except BlockedError as exc:
            log.warning("%s", exc)
            blocked = True
            break
        info = parse_product_page(html)
        store.set_product_info(asin, info.brand, info.manufacturer, info.item_form)
        done += 1
        brands += bool(info.brand)
        makers += bool(info.manufacturer)
        if not info.brand and not info.manufacturer:
            empty.append(asin)
            if debug_dir:
                debug_dir.mkdir(parents=True, exist_ok=True)
                (debug_dir / f"{asin}.html").write_text(html, encoding="utf-8")
        print(f"  {asin}: marchio {info.brand or '–'} · produttore {info.manufacturer or '–'} · forma {info.item_form or '–'}")
    print(f"\nPagine prodotto lette: {done} · marchio trovato: {brands} · produttore trovato: {makers}")
    if empty and debug_dir:
        print(f"Senza marchio né produttore: {len(empty)} (pagine salvate in {debug_dir})")
    if blocked:
        print("Interrotto da una verifica di Amazon: rilancia più tardi `amazon-sov brands`.")
    elif len(targets) > done:
        print(f"Restano {len(targets) - done} pagine da controllare: rilancia `amazon-sov brands`.")
    return done


def cmd_brands(args, cfg: Config) -> None:
    """Completa i marchi mancanti di un'esecuzione già fatta e rigenera il report."""
    from .fetcher import BrowserFetcher

    data_dir = Path(args.data_dir)
    store = Store(data_dir / "sov.sqlite")
    run_id = args.run or store.latest_run_id()
    if not run_id:
        raise SystemExit("Nessuna esecuzione nell'archivio: lancia prima `crawl` o `parse`.")
    resolver, relevance = _filters(cfg, store)
    rows = reclassify(store.rows(run_id), resolver, relevance)
    todo = lookup_targets(store, rows, cfg)
    if not todo:
        print("Niente da controllare: marchi e produttori sono già noti.")
    else:
        print(f"{len(todo)} pagine prodotto da controllare: ne apro {min(len(todo), args.max)}.")
        try:
            with BrowserFetcher(cfg, data_dir / "browser-profile", headless=args.headless or None) as fetcher:
                _lookup_products(fetcher, store, rows, cfg, args.max, data_dir / "html" / "prodotti")
        except KeyboardInterrupt:
            print("\nInterrotto: uso i marchi trovati finora.")
    make_report(store, cfg, run_id, Path(args.out), args.denominator, args.top)


# --------------------------------------------------------------------------- parse


_PAGE_IN_NAME = re.compile(r"__p(\d+)$")


def cmd_parse(args, cfg: Config) -> None:
    files = sorted(p for p in Path(args.html_dir).rglob("*") if p.suffix.lower() in (".html", ".htm"))
    if not files:
        raise SystemExit(f"Nessun file .html in {args.html_dir}")
    configured = {normalize(k.term): k.term for k in cfg.keywords}
    grouped: dict[str, dict[int, ParsedPage]] = defaultdict(dict)
    for path in files:
        html = path.read_text(encoding="utf-8", errors="replace")
        m = _PAGE_IN_NAME.search(path.stem)
        parsed = parse_search_page(html, page=int(m.group(1)) if m else None)
        kw = parsed.keyword or _PAGE_IN_NAME.sub("", path.stem).replace("-", " ").replace("_", " ")
        kw = configured.get(normalize(kw), " ".join(kw.split()))
        if parsed.blocked:
            log.warning("%s: pagina di verifica/captcha (%s), la salto", path.name, parsed.blocked)
            continue
        if not parsed.items and not parsed.keyword:
            log.warning("%s: non sembra una pagina di risultati di ricerca, la salto", path.name)
            continue
        if parsed.page in grouped[kw]:
            log.warning("%s: pagina %s di '%s' già letta, uso l'ultima", path.name, parsed.page, kw)
        parsed.keyword = kw
        grouped[kw][parsed.page] = parsed
        print(f"  {path.name}: '{kw}' pagina {parsed.page}, {len(parsed.results)} risultati")

    store = Store(Path(args.data_dir) / "sov.sqlite")
    resolver, relevance = _filters(cfg, store)
    run_id = store.create_run("html", cfg.domain, sorted(grouped))
    for kw, pages in grouped.items():
        for page_no, parsed in pages.items():
            store.log_page(run_id, kw, page_no, "ok" if parsed.results else "empty", len(parsed.results), None)
        store.replace_rows(run_id, kw, build_rows(kw, list(pages.values()), resolver, relevance))
    store.finish_run(run_id)
    make_report(store, cfg, run_id, Path(args.out), args.denominator, args.top)


# --------------------------------------------------------------------------- report / inspect / runs


def cmd_report(args, cfg: Config) -> None:
    store = Store(Path(args.data_dir) / "sov.sqlite")
    run_id = args.run or store.latest_run_id()
    if not run_id:
        raise SystemExit("Nessuna esecuzione nell'archivio: lancia prima `crawl` o `parse`.")
    make_report(store, cfg, run_id, Path(args.out), args.denominator, args.top)


def cmd_runs(args, cfg: Config) -> None:
    store = Store(Path(args.data_dir) / "sov.sqlite")
    runs = store.runs()
    if not runs:
        print("Nessuna esecuzione.")
    for r in runs:
        print(f"{r['run_id']}  {r['source']:<5}  {r['n_rows']:>5} righe  {r['n_failed']} pagine non lette")


def latest_html(data_dir: Path) -> Path | None:
    """Prima pagina di risultati dell'ultima esecuzione scaricata."""
    runs = sorted(d for d in (data_dir / "html").glob("*") if d.is_dir() and any(d.glob("*.html")))
    if not runs:
        return None
    files = sorted(runs[-1].glob("*.html"), key=lambda p: (not p.stem.endswith("__p1"), p.name))
    return files[0]


def cmd_inspect(args, cfg: Config) -> None:
    path = Path(args.file) if args.file else latest_html(Path(args.data_dir))
    if path is None:
        raise SystemExit("Nessuna pagina scaricata: indica un file .html")
    html = path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_search_page(html)
    print(f"file: {path.name}")
    resolver = BrandResolver(cfg)
    relevance = RelevanceFilter(cfg.relevance_include, cfg.relevance_exclude)
    print(f"keyword: {parsed.keyword!r}  pagina: {parsed.page}  blocco: {parsed.blocked}  {parsed.result_count_text or ''}")
    print(f"risultati: {len(parsed.results)}  widget: {len(parsed.items) - len(parsed.results)}\n")
    print(" #  tipo  ASIN        marchio (fonte)              ferro  prezzo   ★    recens.  acq/m  badge / titolo")
    for it in parsed.items:
        brand, source = resolver.resolve(it.asin, it.brand_raw, it.title)
        kind = {"organic": "org", "sponsored": "ADS"}.get(it.placement) or {"sponsored_brand": "SB", "sponsored_widget": "W-ADS"}.get(it.widget, "wid")
        print(
            f"{it.slot or '':>2}  {kind:<5} {it.asin}  {(brand + ' (' + source + ')')[:28]:<28} "
            f"{'sì' if relevance(it.title) else 'no':<5} {it.price if it.price is not None else '–':>7} "
            f"{it.rating if it.rating is not None else '–':>4} {it.reviews if it.reviews is not None else '–':>8} "
            f"{it.bought_last_month if it.bought_last_month is not None else '–':>6}  "
            f"{('[' + ', '.join(it.badges) + '] ') if it.badges else ''}{it.title[:70]}"
        )
    if args.html:
        missing = [it for it in parsed.results if not it.brand_raw and relevance(it.title)][:3]
        print(f"\n--- HTML dei primi {len(missing)} risultati senza riga del marchio ---")
        for it in missing:
            print(f"\n[{it.asin}]\n{compact_html(html, it.asin)}")


# --------------------------------------------------------------------------- update

UPDATE_URL = "https://github.com/andreafontanace-ops/Claude/archive/refs/heads/claude/bold-turing-uyee99.zip"


def _download(url: str, dest: Path) -> None:
    import shutil
    import subprocess
    import urllib.request

    if shutil.which("curl"):
        # curl usa i certificati del sistema (su Mac il Python di python.org a volte non li ha)
        subprocess.run(["curl", "-fsSL", url, "-o", str(dest)], check=True)
    else:
        with urllib.request.urlopen(url, timeout=180) as resp:
            dest.write_bytes(resp.read())


def cmd_update(args, cfg) -> None:
    """Scarica l'ultima versione da GitHub e sostituisce il codice (i dati in data/ e reports/ restano)."""
    import tempfile
    import zipfile

    project = Path(args.target) if args.target else Path(__file__).resolve().parent.parent
    print("Scarico l'ultima versione da GitHub…")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "update.zip"
        try:
            _download(args.url, archive)
        except Exception as exc:
            raise SystemExit(f"Download non riuscito: {exc}")
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            init = next((n for n in names if n.endswith("amazon-sov/amazon_sov/__init__.py")), None)
            if init is None:
                raise SystemExit("Nello ZIP scaricato non c'è il programma: niente è stato cambiato.")
            base = init[: -len("amazon_sov/__init__.py")]
            count = 0
            for name in names:
                rel = name[len(base):]
                if name.startswith(base + "amazon_sov/") and not name.endswith("/") and "__pycache__" not in rel:
                    target = project / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
                    count += 1
            new_cfg = zf.read(base + "config.toml") if base + "config.toml" in names else None
    cfg_path = project / "config.toml"
    if new_cfg is not None and (not cfg_path.exists() or cfg_path.read_bytes() != new_cfg):
        if cfg_path.exists():
            backup = project / "config.backup.toml"
            backup.write_bytes(cfg_path.read_bytes())
            print(f"Impostazioni aggiornate; le tue precedenti sono salvate in {backup.name}")
        cfg_path.write_bytes(new_cfg)
    print(f"Aggiornato ({count} file). Lancia `amazon-sov --help` per vedere i comandi.")


# --------------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="amazon-sov", description="Share of voice degli integratori di ferro su Amazon.it")
    ap.add_argument("-c", "--config", default="config.toml", help="file di configurazione (default: config.toml)")
    ap.add_argument("--data-dir", default="data", help="archivio SQLite, HTML scaricati, profilo browser")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def report_opts(p):
        p.add_argument("--out", default="reports", help="cartella dei report (default: reports)")
        p.add_argument("--denominator", choices=["all", "relevant"], default="all",
                       help="all = quota su tutta la SERP; relevant = quota sui soli integratori di ferro")
        p.add_argument("--top", type=int, default=50, help="prodotti nel report HTML")

    p = sub.add_parser("crawl", help="scarica le SERP con il browser e calcola la SoV")
    p.add_argument("--pages", type=int, help="pagine per keyword (sovrascrive la configurazione)")
    p.add_argument("--keyword", action="append", help="limita a questa keyword (ripetibile)")
    p.add_argument("--headless", action="store_true", help="browser invisibile (i captcha fermano il crawl)")
    p.add_argument("--product-pages", "--enrich-brands", dest="product_pages", type=int, default=None, metavar="N",
                   help="pagine prodotto da aprire per marchi e produttori (default: crawl.product_pages)")
    report_opts(p)
    p.set_defaults(func=cmd_crawl)

    p = sub.add_parser("brands", aliases=["prodotti"],
                       help="legge marchi e produttori dalle pagine prodotto e rigenera il report")
    p.add_argument("--run", help="esecuzione da completare (default: l'ultima)")
    p.add_argument("--max", type=int, default=80, help="pagine prodotto da aprire al massimo (default 80)")
    p.add_argument("--headless", action="store_true")
    report_opts(p)
    p.set_defaults(func=cmd_brands)

    p = sub.add_parser("parse", help="calcola la SoV da pagine HTML salvate a mano")
    p.add_argument("html_dir")
    report_opts(p)
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("report", help="rigenera report e CSV di un'esecuzione (default: l'ultima)")
    p.add_argument("--run")
    report_opts(p)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("inspect", help="mostra cosa viene estratto da una pagina HTML (default: l'ultima scaricata)")
    p.add_argument("file", nargs="?")
    p.add_argument("--html", action="store_true", help="aggiunge l'HTML ridotto dei risultati senza marchio, per la diagnosi")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("runs", help="elenca le esecuzioni in archivio")
    p.set_defaults(func=cmd_runs)

    p = sub.add_parser("update", aliases=["aggiorna"], help="scarica e installa l'ultima versione del programma")
    p.add_argument("--url", default=UPDATE_URL, help=argparse.SUPPRESS)
    p.add_argument("--target", help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_update, needs_config=False)
    return ap


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    if not getattr(args, "needs_config", True):
        args.func(args, None)  # l'aggiornamento deve funzionare anche con una configurazione rotta
        return
    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        sys.exit(f"File di configurazione non trovato: {args.config}")
    except ValueError as exc:
        sys.exit(f"Configurazione non valida: {exc}")
    args.func(args, cfg)
