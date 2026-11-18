"""Report HTML autonomo (nessuna risorsa esterna): marchi, prodotti, keyword × marchi, metodo."""

from __future__ import annotations

from collections import defaultdict
from html import escape

from .config import Config
from .brands import UNKNOWN_BRAND
from .scoring import NON_RELEVANT, NOT_STATED, UNRANKED, SovResult

MANU_SOURCE_LABELS = {
    "product_page": "pagina prodotto («Dettagli prodotto» → Produttore)",
    "same_brand": "altro prodotto dello stesso marchio",
    "config": "configurazione (marchio → produttore)",
    "override": "correzione manuale",
    None: "non indicato",
}

SOURCE_LABELS = {
    "serp": "riga del marchio nella SERP",
    "product_page": "pagina prodotto",
    "override": "correzione manuale",
    "alias": "alias trovato nel titolo",
    "title_guess": "prima parola del titolo (stima)",
    "unknown": "sconosciuto",
}


def _num(x: float, digits: int = 1) -> str:
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def pct(x: float | None, digits: int = 1) -> str:
    return "–" if x is None else f"{_num(x * 100, digits)}%"


def delta(x: float | None) -> str:
    if x is None:
        return '<span class="muted">nuovo</span>'
    v = x * 100
    if abs(v) < 0.05:
        return '<span class="muted">=</span>'
    arrow = "▲" if v > 0 else "▼"
    return f'{arrow} {"+" if v > 0 else "−"}{_num(abs(v))} pp'


def _bar(total: float, ads_share: float, scale: float) -> str:
    if scale <= 0 or total <= 0:
        return '<div class="bar"></div>'
    org_w = total * (1 - ads_share) / scale * 100
    paid_w = total * ads_share / scale * 100
    tip = f"Organica {pct(total * (1 - ads_share))} · Ads {pct(total * ads_share)} (su {pct(total)} totale)"
    segs = ""
    if org_w > 0:
        segs += f'<span class="seg org" style="width:{org_w:.2f}%"></span>'
    if paid_w > 0:
        segs += f'<span class="seg paid" style="width:{paid_w:.2f}%"></span>'
    return f'<div class="bar" data-tip="{escape(tip)}">{segs}</div>'


def _heat_class(value: float, vmax: float) -> str:
    if value <= 0 or vmax <= 0:
        return "h0"
    return f"h{min(7, max(1, round(value / vmax * 7 + 0.4999)))}"


def render_report(
    result: SovResult,
    cfg: Config,
    keyword_weights: dict[str, float],
    run: dict,
    pages: list[dict],
    prev_run_id: str | None = None,
    top_products: int = 50,
) -> str:
    brands = [b for b in result.brands if b["brand"] not in UNRANKED]
    products = [p for p in result.products if p["relevant"]][:top_products]
    n_kw = len(result.keywords_scored)
    kw_total = len(keyword_weights)

    # ---- qualità del dato sui marchi
    by_source: dict[str, float] = defaultdict(float)
    rel_total = sum(p["sov_total"] for p in result.products if p["relevant"]) or 1.0
    for p in result.products:
        if p["relevant"]:
            by_source[p["brand_source"]] += p["sov_total"] / rel_total
    source_items = "".join(
        f"<li>{escape(SOURCE_LABELS.get(s, s))}: <b>{pct(v)}</b></li>"
        for s, v in sorted(by_source.items(), key=lambda kv: -kv[1])
    )

    # ---- marchi e produttori
    brand_rows = _group_rows(
        result.groups["brands"], n_kw, prev_run_id,
        lambda b: f'{escape(b["manufacturer"] or "produttore non indicato")} · {escape(_short(b["top_title"], 50))}',
    )
    manu_rows = _group_rows(
        result.groups["manufacturers"], n_kw, prev_run_id,
        lambda b: escape(", ".join(b["brands"][:4]) + (" …" if len(b["brands"]) > 4 else "")),
    )

    # ---- formulazioni
    form_rows = _mix_rows(result.groups["forms"])
    iron_rows = _mix_rows(result.groups["iron_types"])

    # ---- qualità del dato sui produttori
    by_manu_source: dict[str | None, float] = defaultdict(float)
    for p in result.products:
        if p["relevant"]:
            by_manu_source[p["manufacturer_source"]] += p["sov_total"] / rel_total
    manu_source_items = "".join(
        f"<li>{escape(MANU_SOURCE_LABELS.get(s, s or 'non indicato'))}: <b>{pct(v)}</b></li>"
        for s, v in sorted(by_manu_source.items(), key=lambda kv: -kv[1])
    )

    # ---- prodotti
    scale_p = max((p["sov_total"] for p in products), default=0.0)
    product_rows = []
    for i, p in enumerate(products, 1):
        rating = (
            f'{_num(p["rating"])}★ <span class="muted">({_num(p["reviews"], 0) if p["reviews"] else "–"})</span>'
            if p["rating"]
            else "–"
        )
        badges = " ".join(f'<span class="badge">{escape(x)}</span>' for x in (p["badges"] or "").split("|") if x)
        product_rows.append(
            f"""<tr>
<td class="num muted">{i}</td>
<td class="prod"><a href="https://{escape(cfg.domain)}/dp/{escape(p["asin"])}" target="_blank" rel="noopener">{escape(_short(p["title"], 90))}</a>
<div class="sub">{escape(p["brand"])} · {escape(p["manufacturer"] or "produttore non indicato")} · {escape(p["asin"])} {badges}</div></td>
<td class="form">{escape(p["form"] or "–")}<div class="sub">{escape(p["iron_type"] or "")}</div></td>
<td class="barcell">{_bar(p["sov_total"], p["ads_share"], scale_p)}</td>
<td class="num strong">{pct(p["sov_total"], 2)}</td>
<td class="num">{pct(p["sov_organic"], 2)}</td>
<td class="num">{p["best_organic_rank"] or "–"}</td>
<td class="num">{p["keywords_top10_organic"]}/{n_kw}</td>
<td class="num">{(_num(p["price"], 2) + " €") if p["price"] else "–"}</td>
<td class="num">{rating}</td>
<td class="num">{(_num(p["bought_last_month"], 0) + "+") if p["bought_last_month"] else "–"}</td>
{f'<td class="num delta">{delta(p.get("delta_pp"))}</td>' if prev_run_id else ""}
</tr>"""
        )

    # ---- keyword × marchi
    top_brands = [b["brand"] for b in brands[:8]]
    heat_head = "".join(f'<th class="num">{escape(b)}</th>' for b in top_brands) + '<th class="num">Altri marchi</th><th class="num">Non di ferro</th>'
    heat_rows = []
    cells_all = []
    matrix = []
    for kw in result.keywords_scored:
        shares = result.keyword_brand[kw]
        row = [shares.get(b, 0.0) for b in top_brands]
        others = sum(v for b, v in shares.items() if b not in top_brands and b != NON_RELEVANT)
        row += [others, shares.get(NON_RELEVANT, 0.0)]
        matrix.append((kw, row))
        cells_all += row[: len(top_brands)]
    vmax = max(cells_all, default=0.0)
    labels = top_brands + ["Altri marchi", "Non di ferro"]
    for kw, row in matrix:
        tds = []
        for j, v in enumerate(row):
            cls = _heat_class(v, vmax) if j < len(top_brands) else "plain"
            tip = escape(f"{kw} · {labels[j]}: {pct(v)}")
            tds.append(f'<td class="num heat {cls}" data-tip="{tip}">{pct(v, 0) if v > 0 else "–"}</td>')
        heat_rows.append(f'<tr><th class="kw">{escape(kw)}</th>{"".join(tds)}</tr>')

    # ---- marchi da verificare
    unsure = [p for p in result.products if p["relevant"] and p["brand_source"] in ("unknown", "title_guess")][:15]
    verify_html = ""
    if unsure:
        items = "".join(
            f'<li><a href="https://{escape(cfg.domain)}/dp/{escape(p["asin"])}" target="_blank" rel="noopener">{escape(p["asin"])}</a> '
            f'· {escape(_short(p["title"], 80))} → <b>{escape(p["brand"])}</b> '
            f'<span class="muted">({"stimato dal titolo" if p["brand_source"] == "title_guess" else "sconosciuto"}, '
            f'{"pagina prodotto già letta senza marchio" if p.get("page_checked") else "pagina prodotto da leggere"}, '
            f'SoV {pct(p["sov_total"], 2)})</span></li>'
            for p in unsure
        )
        verify_html = (
            '<section><h2>Marchi da verificare</h2><p class="note">Per questi prodotti il marchio non si legge nei risultati '
            "di ricerca. Lancia <code>amazon-sov brands</code> per leggerlo dalla pagina prodotto, oppure scrivilo tu in "
            f"<code>[brands.asin_overrides]</code> dentro <code>config.toml</code>.</p><ul>{items}</ul></section>"
        )

    # ---- pagine non lette
    failed = [p for p in pages if p["status"] not in ("ok", "empty")]
    failed_html = ""
    if failed or result.keywords_empty:
        items = "".join(f"<li>{escape(p['keyword'])} — pagina {p['page']}: {escape(p['status'])}</li>" for p in failed)
        items += "".join(f"<li>{escape(k)}: nessun risultato utilizzabile</li>" for k in result.keywords_empty)
        failed_html = f'<section><h2>Pagine non lette</h2><p class="note">Queste keyword sono escluse o incomplete: la SoV è calcolata sulle altre.</p><ul>{items}</ul></section>'

    kw_list = "".join(f"<li>{escape(k)} <span class='muted'>(peso {_num(w, 2)})</span></li>" for k, w in keyword_weights.items())
    meta = result.meta
    delta_th = '<th class="num">Δ vs prec.</th>' if prev_run_id else ""
    prev_note = f" · confronto con l'esecuzione {escape(prev_run_id)}" if prev_run_id else ""
    denom = "tutta la SERP (anche i prodotti non di ferro)" if meta["denominator"] == "all" else "i soli integratori di ferro"

    return f"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Share of voice ferro</title>
<style>
:root {{
  color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f3f2ef; --line: #e2e1dc;
  --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #7a7974;
  --org: #2a78d6; --paid: #eb6834; --track: #ecebe7;
  --h1: #cde2fb; --h2: #9ec5f4; --h3: #6da7ec; --h4: #3987e5; --h5: #256abf; --h6: #184f95; --h7: #0d366b;
  --hi1: #0b0b0b; --hi2: #0b0b0b; --hi3: #0b0b0b; --hi4: #ffffff; --hi5: #ffffff; --hi6: #ffffff; --hi7: #ffffff;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface: #1a1a19; --surface-2: #232321; --line: #383835;
    --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #9a998f;
    --org: #3987e5; --paid: #d95926; --track: #2c2c2a;
    --h1: #0d366b; --h2: #104281; --h3: #184f95; --h4: #256abf; --h5: #3987e5; --h6: #86b6ef; --h7: #cde2fb;
    --hi1: #f0efec; --hi2: #f0efec; --hi3: #f0efec; --hi4: #f0efec; --hi5: #0b0b0b; --hi6: #0b0b0b; --hi7: #0b0b0b;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface: #1a1a19; --surface-2: #232321; --line: #383835;
  --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #9a998f;
  --org: #3987e5; --paid: #d95926; --track: #2c2c2a;
  --h1: #0d366b; --h2: #104281; --h3: #184f95; --h4: #256abf; --h5: #3987e5; --h6: #86b6ef; --h7: #cde2fb;
  --hi1: #f0efec; --hi2: #f0efec; --hi3: #f0efec; --hi4: #f0efec; --hi5: #0b0b0b; --hi6: #0b0b0b; --hi7: #0b0b0b;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--surface); color: var(--ink); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width: 1240px; margin: 0 auto; padding: 32px 16px 64px; }}
h1 {{ font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }}
h2 {{ font-size: 18px; margin: 40px 0 6px; }}
.lede {{ color: var(--ink-2); margin: 0 0 24px; }}
.note {{ color: var(--ink-2); margin: 0 0 12px; max-width: 75ch; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
.kpi {{ background: var(--surface-2); border-radius: 10px; padding: 14px 16px; }}
.kpi .v {{ font-size: 24px; font-weight: 650; font-variant-numeric: tabular-nums; }}
.kpi .l {{ color: var(--ink-2); font-size: 13px; }}
.scroll {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: middle; }}
thead th {{ font-size: 12px; font-weight: 600; color: var(--ink-2); background: var(--surface-2); position: sticky; top: 0; white-space: nowrap; }}
tbody tr:last-child td, tbody tr:last-child th {{ border-bottom: 0; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.strong {{ font-weight: 650; }}
.muted {{ color: var(--ink-3); }}
.sub {{ color: var(--ink-2); font-size: 12px; margin-top: 2px; }}
.prod a {{ color: var(--ink); text-decoration: none; }}
.prod a:hover {{ text-decoration: underline; }}
.prod {{ min-width: 280px; }}
.form {{ white-space: nowrap; }}
.products th, .products td {{ padding: 8px 7px; }}
.products .barcell {{ min-width: 100px; width: 12%; }}
.products .prod {{ min-width: 230px; }}
h3 {{ font-size: 15px; margin: 16px 0 8px; }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr)); gap: 16px; }}
.badge {{ display: inline-block; font-size: 11px; padding: 0 6px; border-radius: 999px; border: 1px solid var(--line); color: var(--ink-2); margin-left: 4px; }}
.barcell {{ min-width: 160px; width: 22%; }}
.bar {{ display: flex; gap: 2px; height: 12px; align-items: stretch; }}
.seg {{ display: block; height: 100%; min-width: 2px; }}
.seg.org {{ background: var(--org); }}
.seg.paid {{ background: var(--paid); }}
.bar .seg:last-child {{ border-radius: 0 4px 4px 0; }}
.legend {{ display: flex; gap: 16px; color: var(--ink-2); font-size: 13px; margin: 0 0 10px; flex-wrap: wrap; }}
.legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }}
.nonrel td {{ color: var(--ink-2); background: var(--surface-2); }}
.delta {{ color: var(--ink-2); }}
th.kw {{ font-weight: 500; white-space: nowrap; }}
.heat {{ min-width: 64px; }}
.h0 {{ color: var(--ink-3); }}
.h1 {{ background: var(--h1); color: var(--hi1); }} .h2 {{ background: var(--h2); color: var(--hi2); }}
.h3 {{ background: var(--h3); color: var(--hi3); }} .h4 {{ background: var(--h4); color: var(--hi4); }}
.h5 {{ background: var(--h5); color: var(--hi5); }} .h6 {{ background: var(--h6); color: var(--hi6); }}
.h7 {{ background: var(--h7); color: var(--hi7); }}
td.heat {{ border-left: 2px solid var(--surface); }}
.plain {{ color: var(--ink-2); }}
ul {{ padding-left: 20px; }}
li {{ margin: 2px 0; }}
code {{ font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; background: var(--surface-2); padding: 1px 4px; border-radius: 4px; }}
#tip {{ position: fixed; pointer-events: none; background: var(--ink); color: var(--surface); font-size: 12px; padding: 6px 8px; border-radius: 6px; max-width: 320px; display: none; z-index: 10; }}
</style>
</head>
<body>
<main>
<h1>Share of voice degli integratori di ferro su Amazon.it</h1>
<p class="lede">Esecuzione {escape(run.get("run_id", ""))} del {escape((run.get("started_at") or "")[:16].replace("T", " "))} · {n_kw} keyword su {kw_total} · peso per posizione: {escape(meta["weighting"])}{prev_note}</p>

<div class="kpis">
  <div class="kpi"><div class="v">{n_kw}</div><div class="l">keyword analizzate</div></div>
  <div class="kpi"><div class="v">{meta["n_products"]}</div><div class="l">prodotti di ferro trovati</div></div>
  <div class="kpi"><div class="v">{meta["n_brands"]}</div><div class="l">marchi</div></div>
  <div class="kpi"><div class="v">{pct(meta["sponsored_slot_share"], 0)}</div><div class="l">slot sponsorizzati</div></div>
  <div class="kpi"><div class="v">{pct(1 - meta["relevant_visibility_share"], 0)}</div><div class="l">visibilità a prodotti non di ferro</div></div>
</div>

<h2>Marchi per share of voice</h2>
<p class="note">Quota della visibilità pesata per posizione, media sulle keyword. La barra divide la SoV totale tra posizioni organiche e annunci; è in scala rispetto al primo marchio.</p>
<div class="legend"><span><i style="background:var(--org)"></i>organica</span><span><i style="background:var(--paid)"></i>da annunci</span></div>
<div class="scroll"><table>
<thead><tr><th class="num">#</th><th>Marchio · prodotto di punta</th><th>SoV totale</th><th class="num">SoV tot.</th><th class="num">SoV organica</th><th class="num">SoV ads</th><th class="num">% da ads</th><th class="num">Top 10</th><th class="num">Keyword</th><th class="num">Prodotti</th>{delta_th}</tr></thead>
<tbody>{brand_rows}</tbody>
</table></div>

<h2>Produttori per share of voice</h2>
<p class="note">Come i marchi, ma sommando tutti i marchi della stessa azienda. Il produttore si legge nella pagina prodotto («Dettagli prodotto» → Produttore); per gli altri prodotti dello stesso marchio si usa lo stesso produttore.</p>
<div class="legend"><span><i style="background:var(--org)"></i>organica</span><span><i style="background:var(--paid)"></i>da annunci</span></div>
<div class="scroll"><table>
<thead><tr><th class="num">#</th><th>Produttore · marchi</th><th>SoV totale</th><th class="num">SoV tot.</th><th class="num">SoV organica</th><th class="num">SoV ads</th><th class="num">% da ads</th><th class="num">Top 10</th><th class="num">Keyword</th><th class="num">Prodotti</th>{delta_th}</tr></thead>
<tbody>{manu_rows}</tbody>
</table></div>

<h2>Formulazioni</h2>
<p class="note">Come si divide la visibilità dei soli prodotti di ferro per forma e per tipo di ferro. Entrambi sono ricavati dal titolo; la forma, se nel titolo manca, dalla pagina prodotto.</p>
<div class="two">
<div><h3>Forma</h3><div class="scroll"><table>
<thead><tr><th>Forma</th><th>Quota</th><th class="num">Quota</th><th class="num">% da ads</th><th class="num">Prodotti</th></tr></thead>
<tbody>{form_rows}</tbody></table></div></div>
<div><h3>Tipo di ferro</h3><div class="scroll"><table>
<thead><tr><th>Tipo di ferro</th><th>Quota</th><th class="num">Quota</th><th class="num">% da ads</th><th class="num">Prodotti</th></tr></thead>
<tbody>{iron_rows}</tbody></table></div></div>
</div>

<h2>Prodotti per share of voice</h2>
<p class="note">Primi {len(products)} integratori di ferro. «Miglior pos.» è la posizione organica più alta su tutte le keyword; «Top 10» conta le keyword in cui il prodotto è nei primi 10 organici.</p>
<div class="legend"><span><i style="background:var(--org)"></i>organica</span><span><i style="background:var(--paid)"></i>da annunci</span></div>
<div class="scroll"><table class="products">
<thead><tr><th class="num">#</th><th>Prodotto</th><th>Formulazione</th><th>SoV totale</th><th class="num">SoV tot.</th><th class="num">SoV organica</th><th class="num">Miglior pos.</th><th class="num">Top 10</th><th class="num">Prezzo</th><th class="num">Valutazione</th><th class="num">Acquisti/mese</th>{delta_th}</tr></thead>
<tbody>{"".join(product_rows)}</tbody>
</table></div>

<h2>Keyword × marchi</h2>
<p class="note">SoV totale di ogni marchio dentro la singola keyword. Più scuro = quota più alta (scala sui primi {len(top_brands)} marchi).</p>
<div class="scroll"><table>
<thead><tr><th>Keyword</th>{heat_head}</tr></thead>
<tbody>{"".join(heat_rows)}</tbody>
</table></div>

{verify_html}

{failed_html}

<section>
<h2>Come è calcolata</h2>
<p class="note">Per ogni keyword ogni risultato riceve un peso che scende con la posizione ({escape(meta["weighting"])}). La SoV di un prodotto è la somma dei pesi dei suoi risultati diviso il totale della keyword; la SoV complessiva è la media sulle keyword, pesata con il peso di ciascuna. Il denominatore è {denom}. «SoV organica» usa solo i risultati organici e la loro posizione organica; «SoV ads» solo i risultati sponsorizzati. «Top 10» è la quota dei primi dieci slot occupati.</p>
<p class="note">Da dove viene il marchio (quota della visibilità dei prodotti di ferro):</p>
<ul>{source_items}</ul>
<p class="note">Da dove viene il produttore:</p>
<ul>{manu_source_items}</ul>
<p class="note">Keyword e pesi:</p>
<ul>{kw_list}</ul>
<p class="note">I risultati dipendono da quando e da dove si cerca (annunci, località di consegna, personalizzazione): confronta esecuzioni fatte nelle stesse condizioni.</p>
</section>
</main>
<div id="tip" role="tooltip"></div>
<script>
(() => {{
  const tip = document.getElementById("tip");
  document.addEventListener("mouseover", (e) => {{
    const el = e.target.closest("[data-tip]");
    if (!el) {{ tip.style.display = "none"; return; }}
    tip.textContent = el.dataset.tip;
    tip.style.display = "block";
  }});
  document.addEventListener("mousemove", (e) => {{
    if (tip.style.display !== "block") return;
    const x = Math.min(e.clientX + 12, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + "px";
    tip.style.top = (e.clientY + 14) + "px";
  }});
}})();
</script>
</body>
</html>
"""


def _short(text: str | None, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _group_rows(items: list[dict], n_kw: int, prev_run_id: str | None, sub) -> str:
    """Righe della tabella marchi/produttori: classifica, poi «non indicato» e «non di ferro» in fondo."""
    ranked = [b for b in items if b["brand"] not in UNRANKED]
    scale = max((b["sov_total"] for b in ranked), default=0.0)
    out = []
    for i, b in enumerate(ranked, 1):
        out.append(
            f"""<tr>
<td class="num muted">{i}</td>
<td><b>{escape(b["brand"])}</b><div class="sub">{sub(b)}</div></td>
<td class="barcell">{_bar(b["sov_total"], b["ads_share"], scale)}</td>
<td class="num strong">{pct(b["sov_total"])}</td>
<td class="num">{pct(b["sov_organic"])}</td>
<td class="num">{pct(b["sov_paid"])}</td>
<td class="num">{pct(b["ads_share"], 0)}</td>
<td class="num">{pct(b["shelf_top10"])}</td>
<td class="num">{b["keywords_present"]}/{n_kw}</td>
<td class="num">{b["n_products"]}</td>
{f'<td class="num delta">{delta(b.get("delta_pp"))}</td>' if prev_run_id else ""}
</tr>"""
        )
    labels = {
        NOT_STATED: ("Produttore non indicato", "lancia <code>amazon-sov brands</code> per leggerlo dalle pagine prodotto"),
        UNKNOWN_BRAND: ("Marchio non identificato", "il titolo non lo dice: lancia <code>amazon-sov brands</code> per leggerlo dalle pagine prodotto"),
        NON_RELEVANT: ("Prodotti non di ferro", "occupano spazio nella SERP ma non entrano nella classifica"),
    }
    for b in items:
        if b["brand"] in labels:
            title, note = labels[b["brand"]]
            out.append(
                f"""<tr class="nonrel">
<td></td><td><i>{title}</i><div class="sub">{note}</div></td>
<td class="barcell"></td><td class="num">{pct(b["sov_total"])}</td><td class="num">{pct(b["sov_organic"])}</td>
<td class="num">{pct(b["sov_paid"])}</td><td class="num">{pct(b["ads_share"], 0)}</td>
<td class="num">{pct(b["shelf_top10"])}</td><td class="num">{b["keywords_present"]}/{n_kw}</td>
<td class="num">{b["n_products"]}</td>{'<td></td>' if prev_run_id else ""}
</tr>"""
            )
    return "".join(out)


def _mix_rows(items: list[dict]) -> str:
    """Quota tra i soli prodotti di ferro, per forma o tipo di ferro."""
    rel = [b for b in items if b["brand"] != NON_RELEVANT]
    total = sum(b["sov_total"] for b in rel) or 1.0
    scale = max((b["sov_total"] for b in rel if b["brand"] != NOT_STATED), default=0.0)
    out = []
    for b in rel:
        share = b["sov_total"] / total
        muted = b["brand"] == NOT_STATED
        name = "<i>non indicato nel titolo</i>" if muted else f"<b>{escape(b['brand'])}</b>"
        bar = "" if muted else _bar(b["sov_total"], b["ads_share"], scale)
        out.append(
            f"""<tr{' class="nonrel"' if muted else ""}><td>{name}</td><td class="barcell">{bar}</td>
<td class="num strong">{pct(share)}</td><td class="num">{pct(b["ads_share"], 0)}</td><td class="num">{b["n_products"]}</td></tr>"""
        )
    return "".join(out)
