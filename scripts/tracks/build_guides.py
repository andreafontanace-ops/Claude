"""Print the PDF guide that comes with every ride, and pack the bundles.

    python scripts/tracks/build_guides.py

Reads private-tracks/guides/<slug>.json (written by build_tracks.py) and the
ride's GPX, lays the guide out as HTML in the site's paper-and-ink style and
prints it to A4 PDF with the preinstalled Chromium (Playwright). Free rides
go to site/tracks/, paid ones to private-tracks/, next to their GPX.
"""
import html
import json
import math
import os
import re
import subprocess
import tempfile
import zipfile
from datetime import date
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SITE = os.path.join(ROOT, "site")
PRIVATE = os.path.join(ROOT, "private-tracks")
NS = {"g": "http://www.topografix.com/GPX/1/1"}
e = html.escape

INK, PAPER, ROUTE, SKY, LINE = "#231f16", "#faf6ec", "#c0392b", "#3d8fc4", "#ddd3bd"
KIND = {"spot": ("F", SKY), "eat": ("R", ROUTE), "sleep": ("H", INK)}


def num(v, d=0):
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def dur(minutes):
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if h and m else f"{h} h" if h else f"{m} min"


def phone(raw):
    """+33492453286 -> +33 4 92 45 32 86; Swiss and Italian numbers grouped too."""
    d = "".join(c for c in raw if c.isdigit() or c == "+")
    if d.startswith("+33") and len(d) == 12:
        r = d[3:]
        return "+33 " + r[0] + " " + " ".join(r[i:i + 2] for i in range(1, 9, 2))
    if d.startswith("+41") and len(d) == 12:
        r = d[3:]
        return f"+41 {r[:2]} {r[2:5]} {r[5:7]} {r[7:]}"
    if d.startswith("+39"):
        r = d[3:]
        if r.startswith("3") and len(r) == 10:
            return f"+39 {r[:3]} {r[3:6]} {r[6:]}"
        return f"+39 {r}"
    return raw


def track_points(path):
    root = ET.parse(path).getroot()
    return [(float(p.get("lon")), float(p.get("lat"))) for p in root.iterfind(".//g:trkpt", NS)]


# --- static route map -----------------------------------------------------------

def route_map(points, g, ride, w=700, h=520, pad=46):
    lat0 = sum(p[1] for p in points) / len(points)
    k = math.cos(math.radians(lat0))
    xs = [p[0] * k for p in points]
    ys = [-p[1] for p in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0))
    ox, oy = (w - (x1 - x0) * s) / 2, (h - (y1 - y0) * s) / 2

    def P(lon, lat):
        return ox + (lon * k - x0) * s, oy + (-lat - y0) * s

    step = max(1, len(points) // 1500)
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (P(*p) for p in points[::step] + [points[-1]]))
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="map">',
           f'<rect width="{w}" height="{h}" fill="{PAPER}"/>',
           f'<path d="{d}" fill="none" stroke="#fff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>',
           f'<path d="{d}" fill="none" stroke="{ROUTE}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>']
    sx, sy = P(*points[0])
    out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="6" fill="{INK}" stroke="#fff" stroke-width="2"/>')

    # Scale bar: a round number of km close to a fifth of the width.
    m_per_px = 1 / s * 111320
    target = (w / 5) * m_per_px / 1000
    bar_km = min([1, 2, 5, 10, 20], key=lambda v: abs(v - target))
    bar_px = bar_km * 1000 / m_per_px
    out.append(f'<g font-family="Helvetica, Arial, sans-serif" font-size="12" fill="{INK}">'
               f'<rect x="{w - 24 - bar_px:.1f}" y="{h - 26}" width="{bar_px:.1f}" height="5" fill="{INK}"/>'
               f'<text x="{w - 24:.1f}" y="{h - 32}" text-anchor="end">{bar_km} km</text>'
               f'<text x="24" y="30" font-weight="800">N &#8593;</text></g>')

    # Numbered stops, nudged apart when two would sit on top of each other.
    placed = []
    for kind, items in (("spot", g["spots"]), ("eat", g["eat"]), ("sleep", g["sleep"])):
        letter, color = KIND[kind]
        for i, it in enumerate(items, 1):
            x, y = P(it["lon"], it["lat"])
            bx, by = x, y
            tries = 0
            while any(math.hypot(bx - px, by - py) < 20 for px, py in placed) and tries < 12:
                ang = tries * 0.9
                bx, by = x + 22 * math.cos(ang), y + 22 * math.sin(ang)
                tries += 1
            if (bx, by) != (x, y):
                out.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{INK}" stroke-width="1"/>')
            placed.append((bx, by))
            out.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="10" fill="{color}" stroke="#fff" stroke-width="2"/>'
                       f'<text x="{bx:.1f}" y="{by + 4:.1f}" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
                       f'font-size="10" font-weight="800" fill="#fff">{letter}{i}</text>')
    # Pass and town labels.
    for m in ride["markers"]:
        x, y = P(m["lon"], m["lat"])
        if m["kind"] == "pass":
            out.append(f'<path d="M{x:.1f},{y - 9:.1f}l8,12h-16z" fill="{INK}" stroke="#fff" stroke-width="1.5"/>')
        label = f"{m['name'].upper()} {num(m['ele'])}" if m["kind"] == "pass" else m["name"].upper()
        anchor = "end" if x > w * 0.7 else "start"
        dx = -16 if anchor == "end" else 16
        out.append(f'<text x="{x + dx:.1f}" y="{y + 4:.1f}" text-anchor="{anchor}" font-family="Helvetica, Arial, sans-serif" '
                   f'font-size="12" font-weight="800" fill="{INK}" stroke="{PAPER}" stroke-width="4" '
                   f'paint-order="stroke">{e(label)}</text>')

    out.append("</svg>")
    return "".join(out)


def profile_svg(ride, g, w=700, h=200):
    pts = ride["profile"]
    kmax = pts[-1][0]
    lo = math.floor((min(p[1] for p in pts) - 80) / 250) * 250
    hi = math.ceil((max([p[1] for p in pts] + [m["ele"] for m in ride["markers"]]) + 150) / 250) * 250
    L0, R0, T0, B0 = 46, 10, 26, 26
    X = lambda k: L0 + k / kmax * (w - L0 - R0)
    Y = lambda v: T0 + (1 - (v - lo) / (hi - lo)) * (h - T0 - B0)
    out = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" class="profile" '
           f'font-family="Helvetica, Arial, sans-serif">']
    stepm = 500 if hi - lo > 1500 else 250
    for v in range(lo, hi + 1, stepm):
        out.append(f'<line x1="{L0}" x2="{w - R0}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{LINE}"/>'
                   f'<text x="{L0 - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="10" fill="#8a8170">{num(v)}</text>')
    kstep = 20 if kmax > 80 else 10 if kmax > 40 else 5
    for kv in range(0, int(kmax) + 1, kstep):
        out.append(f'<text x="{X(kv):.1f}" y="{h - 8}" text-anchor="middle" font-size="10" fill="#8a8170">{kv} km</text>')
    line = "L".join(f"{X(p[0]):.1f},{Y(p[1]):.1f}" for p in pts)
    out.append(f'<path d="M{line}L{X(kmax):.1f},{Y(lo):.1f}L{X(0):.1f},{Y(lo):.1f}Z" fill="{ROUTE}" fill-opacity="0.12"/>'
               f'<path d="M{line}" fill="none" stroke="{ROUTE}" stroke-width="2"/>')
    for m in ride["markers"]:
        if m["kind"] != "pass":
            continue
        x, y = X(m["km"]), Y(m["ele"])
        anchor = "end" if x > w - 120 else "start" if x < 100 else "middle"
        out.append(f'<path d="M{x:.1f},{y - 5:.1f}l5,8h-10z" fill="{INK}"/>'
                   f'<text x="{x:.1f}" y="{y - 9:.1f}" text-anchor="{anchor}" font-size="10.5" font-weight="800" '
                   f'fill="{INK}">{e(m["name"].upper())} {num(m["ele"])}</text>')
    # Ticks along the base for every numbered stop.
    for kind, items in (("spot", g["spots"]), ("eat", g["eat"]), ("sleep", g["sleep"])):
        letter, color = KIND[kind]
        for i, it in enumerate(items, 1):
            x = X(it["km"])
            out.append(f'<circle cx="{x:.1f}" cy="{h - B0:.1f}" r="3.5" fill="{color}"/>')
    out.append("</svg>")
    return "".join(out)


# --- the guide ------------------------------------------------------------------

CSS = f"""
@page {{ size: A4; margin: 14mm 14mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 10.5pt/1.45 "Helvetica Neue", Helvetica, Arial, sans-serif; color: {INK}; }}
h1 {{ font-size: 30pt; line-height: 1.05; margin: 2mm 0 2mm; letter-spacing: -0.01em; }}
h2 {{ font-size: 17pt; margin: 0 0 3mm; }}
h3 {{ font-size: 12pt; margin: 0; }}
p {{ margin: 0 0 2.5mm; }}
a {{ color: {INK}; }}
.eyebrow {{ font-size: 8pt; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: {ROUTE}; margin: 0; }}
.brand {{ font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; font-size: 10pt; }}
.sub {{ font-size: 12.5pt; color: #5d5546; margin: 0 0 4mm; }}
.page {{ break-before: page; }}
.map {{ width: 100%; border: 1px solid {LINE}; border-radius: 3mm; }}
.stats {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 2mm; margin: 4mm 0; }}
.stats div {{ border: 1px solid {LINE}; border-radius: 2mm; padding: 2mm 3mm; }}
.stats dt {{ font-size: 7pt; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #8a8170; }}
.stats dd {{ margin: 0; font-size: 13pt; font-weight: 800; }}
.season {{ display: grid; grid-template-columns: 34mm 1fr; gap: 1mm 4mm; padding: 3mm 4mm; background: #f2ebd9; border-radius: 3mm; }}
.season b {{ font-size: 8pt; letter-spacing: 0.08em; text-transform: uppercase; color: #5d5546; }}
.legend {{ display: flex; gap: 5mm; font-size: 9pt; margin: 2mm 0 0; color: #5d5546; }}
.dot {{ display: inline-block; width: 3.2mm; height: 3.2mm; border-radius: 50%; vertical-align: -0.5mm; margin-right: 1mm; }}
table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; }}
th {{ text-align: left; font-size: 7.5pt; letter-spacing: 0.08em; text-transform: uppercase; color: #8a8170; border-bottom: 1.5px solid {INK}; padding: 1.5mm 2mm; }}
td {{ border-bottom: 1px solid {LINE}; padding: 1.6mm 2mm; vertical-align: top; }}
td.km {{ font-weight: 800; white-space: nowrap; }}
.tag {{ display: inline-block; min-width: 7mm; text-align: center; border-radius: 2mm; color: #fff; font-size: 8pt; font-weight: 800; padding: 0.3mm 1mm; }}
.cards {{ display: grid; gap: 3mm; grid-template-columns: 1fr 1fr; }}
.cards.one {{ grid-template-columns: 1fr; }}
.card {{ border: 1px solid {LINE}; border-radius: 3mm; padding: 3mm 4mm; break-inside: avoid; }}
.card .head {{ display: flex; gap: 3mm; align-items: baseline; }}
.card .meta {{ color: #5d5546; font-size: 9pt; margin: 1mm 0; }}
.card .contacts {{ display: grid; grid-template-columns: auto 1fr; gap: 0.5mm 3mm; font-size: 9pt; margin-top: 1.5mm; overflow-wrap: anywhere; }}
.card .contacts span {{ color: #8a8170; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.06em; padding-top: 0.6mm; }}
.reco {{ background: {ROUTE}; color: #fff; font-size: 7.5pt; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; padding: 0.4mm 2mm; border-radius: 2mm; }}
.review {{ margin-top: 2mm; padding: 2mm 3mm; background: #f2ebd9; border-radius: 2mm; font-style: italic; }}
.note {{ font-size: 9pt; color: #5d5546; padding: 2.5mm 3.5mm; border-left: 3px solid {ROUTE}; background: rgba(192,57,43,0.08); margin: 0 0 4mm; }}
.small {{ font-size: 8.5pt; color: #5d5546; }}
.profile {{ width: 100%; margin-top: 3mm; }}
"""


def place_card(p, letter, i, color):
    contacts = []
    if p["address"]:
        contacts.append(("Indirizzo", e(p["address"])))
    if p["phone"]:
        tel = p["phone"].replace(" ", "")
        contacts.append(("Telefono", f'<a href="tel:{e(tel)}">{e(phone(p["phone"]))}</a>'))
    if p["email"]:
        contacts.append(("Email", f'<a href="mailto:{e(p["email"])}">{e(p["email"])}</a>'))
    if p["website"]:
        url = p["website"] if p["website"].startswith("http") else "https://" + p["website"]
        contacts.append(("Sito", f'<a href="{e(url)}">{e(p["website"].replace("https://", "").replace("http://", "").rstrip("/"))}</a>'))
    contacts.append(("Recensioni", f'<a href="{e(p["reviews"])}">Leggi le recensioni su Google Maps</a>'))
    rows = "".join(f"<span>{k}</span><div>{v}</div>" for k, v in contacts)
    reco = '<span class="reco">Consigliato</span>' if p["recommended"] else ""
    rating = f" · {'★' * int(p['rating'])}{'☆' * (5 - int(p['rating']))}" if p.get("rating") else ""
    review = f'<div class="review">«{e(p["review"])}»</div>' if p.get("review") else ""
    off = "sulla strada" if p["offRoad"] <= 30 else f"{p['offRoad']} m dalla strada"
    return (f'<div class="card"><div class="head"><span class="tag" style="background:{color}">{letter}{i}</span>'
            f'<h3>{e(p["name"])}</h3>{reco}</div>'
            f'<div class="meta">{e(p["type"])} · km {num(p["km"], 1)} · {off}{rating}</div>'
            f'<div class="contacts">{rows}</div>{review}</div>')


def guide_html(slug, g, points, brand):
    ride = g["ride"]
    season = g["season"]
    closures = (" o ".join(ride["closures"]) + (", a seconda del passo" if len(ride["closures"]) > 1 else "")
                if ride["closures"] else "non segnalata")
    top = max([m["ele"] for m in ride["markers"] if m["kind"] == "pass"] or [ride["maxEle"]])

    # Roadbook: every stop of every kind, in riding order.
    book = [(m["km"], "", m["name"], f"{num(m['ele'])} m",
             "Passo" if m["kind"] == "pass" else "Tappa") for m in ride["markers"]]
    for kind, items, what in (("spot", g["spots"], "Punto foto"), ("eat", g["eat"], "Mangiare"),
                              ("sleep", g["sleep"], "Dormire")):
        letter, color = KIND[kind]
        for i, it in enumerate(items, 1):
            book.append((it["km"], f'<span class="tag" style="background:{color}">{letter}{i}</span>',
                         it["name"], f"{num(it['ele'])} m" if "ele" in it else "", what))
    book.sort(key=lambda r: r[0])
    book_rows = "".join(f'<tr><td class="km">{num(km, 1)}</td><td>{tag}</td><td>{e(name)}</td>'
                        f'<td>{ele}</td><td>{what}</td></tr>' for km, tag, name, ele, what in book)

    spots = "".join(
        f'<div class="card"><div class="head"><span class="tag" style="background:{SKY}">F{i}</span>'
        f'<h3>{e(s["name"])}</h3></div><div class="meta">km {num(s["km"], 1)} · {num(s["ele"])} m · '
        f'{s["lat"]:.5f}, {s["lon"]:.5f} · <a href="{e(s["map"])}">apri sulla mappa</a></div>'
        f'<p style="margin:1mm 0 0">{e(s["text"])}</p></div>' for i, s in enumerate(g["spots"], 1))
    eat = "".join(place_card(p, "R", i, ROUTE) for i, p in enumerate(g["eat"], 1))
    sleep = "".join(place_card(p, "H", i, INK) for i, p in enumerate(g["sleep"], 1))
    sources = sorted({s for p in g["eat"] + g["sleep"] for s in p["sources"]})

    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<title>{e(ride['title'])} · Guida {e(brand)}</title><style>{CSS}</style></head><body>

<p class="brand">{e(brand)} · Guida al percorso</p>
<p class="eyebrow" style="margin-top:6mm">{e(ride['area'])}</p>
<h1>{e(ride['title'])}</h1>
<p class="sub">{e(ride['subtitle'])}</p>
{route_map(points, g, ride)}
<div class="legend"><span><i class="dot" style="background:{SKY}"></i>F · punti foto</span>
<span><i class="dot" style="background:{ROUTE}"></i>R · dove mangiare</span>
<span><i class="dot" style="background:{INK}"></i>H · dove dormire</span><span>▲ passi</span></div>
<dl class="stats">
<div><dt>Distanza</dt><dd>{num(ride['km'], 1)} km</dd></div>
<div><dt>Salita</dt><dd>{num(ride['ascent'])} m</dd></div>
<div><dt>Discesa</dt><dd>{num(ride['descent'])} m</dd></div>
<div><dt>Quota max</dt><dd>{num(top)} m</dd></div>
<div><dt>Guida</dt><dd>{dur(ride['minutes'])}</dd></div>
</dl>
<div class="season">
<b>Quando andare</b><div><strong>{e(season.get('best', ''))}</strong></div>
<b>Apertura</b><div>{e(season.get('note', ''))}</div>
<b>Chiusura OSM</b><div>{e(closures)}</div>
</div>

<section class="page">
<p class="eyebrow">Il percorso</p>
<h2>Il giro, chilometro per chilometro</h2>
<p>{e(ride['description'])}</p>
{profile_svg(ride, g)}
<table style="margin-top:4mm"><thead><tr><th>km</th><th></th><th>Luogo</th><th>Quota</th><th>Cosa</th></tr></thead>
<tbody>{book_rows}</tbody></table>
</section>

<section class="page">
<p class="eyebrow">Fermati qui</p>
<h2>Punti panoramici e foto</h2>
<p class="note">Fermati solo dove c'è spazio fuori dalla carreggiata e mai in curva o in galleria.</p>
<div class="cards one">{spots}</div>
</section>

<section class="page">
<p class="eyebrow">A tavola</p>
<h2>Dove mangiare</h2>
<p class="note">Locali lungo il percorso con i contatti per prenotare. Orari, giorni di chiusura e aperture stagionali cambiano spesso in montagna: chiama prima di partire. «Consigliato» indica solo i posti che abbiamo provato di persona.</p>
<div class="cards">{eat}</div>
</section>

<section class="page">
<p class="eyebrow">Per la notte</p>
<h2>Dove dormire</h2>
<p class="note">Strutture lungo il percorso con i contatti per prenotare direttamente. Chiedi sempre se c'è un posto coperto per la moto.</p>
<div class="cards">{sleep}</div>
</section>

<section class="page">
<p class="eyebrow">Prima di partire</p>
<h2>Caricare la traccia</h2>
<table><tbody>
<tr><td class="km">Garmin</td><td>Copia il file GPX nella cartella <i>Garmin/GPX</i> del navigatore, oppure importalo con l'app del tuo modello. Usa la <b>traccia</b> per seguire esattamente il percorso, il <b>percorso</b> se preferisci che il navigatore ricalcoli.</td></tr>
<tr><td class="km">TomTom</td><td>Importa il GPX in MyDrive e sincronizza il navigatore.</td></tr>
<tr><td class="km">App</td><td>Calimoto, Kurviger, OsmAnd e le altre app che leggono il formato GPX: apri il file dal telefono o usa la funzione di importazione.</td></tr>
</tbody></table>
<p style="margin-top:4mm">Nel file trovi la traccia completa con le quote, un percorso a punti di passaggio, i passi, i punti foto, i ristoranti e gli hotel di questa guida come waypoint.</p>

<h2 style="margin-top:8mm">Sicurezza</h2>
<p>La traccia è indicativa e calcolata sulla rete stradale di OpenStreetMap. Strade, aperture stagionali e divieti cambiano: verifica le condizioni prima di partire e, in strada, segui sempre la segnaletica e il codice della strada.</p>

<h2 style="margin-top:8mm">Fonti</h2>
<p class="small">Strade: © OpenStreetMap contributors, licenza ODbL, distribuite da Overture Maps. Quote: modello altimetrico SRTM via AWS Terrain Tiles. Locali: Overture Maps Places (licenza CDLA-Permissive-2.0, con dati {e(', '.join(sources))}, ciascuno con la propria licenza aperta). Recensioni pubbliche: Google Maps. Dati aggiornati al {date.today().strftime('%d/%m/%Y')}.</p>
<p class="small" style="margin-top:6mm">{e(brand)} · Guida personale: puoi usarla per i tuoi viaggi e condividerla con chi viaggia con te, ma non rivenderla né pubblicarla.</p>
</section>
</body></html>"""


def main():
    store = json.load(open(os.path.join(SITE, "store.json"), encoding="utf-8"))
    brand = store["brand"]
    jobs = []
    tmp = tempfile.mkdtemp(prefix="guides-")
    for name in sorted(os.listdir(os.path.join(PRIVATE, "guides"))):
        slug = name[:-5]
        g = json.load(open(os.path.join(PRIVATE, "guides", name), encoding="utf-8"))
        free = store["products"].get(slug, {}).get("free", False)
        folder = os.path.join(SITE, "tracks") if free else PRIVATE
        points = track_points(os.path.join(folder, f"{slug}.gpx"))
        src = os.path.join(tmp, f"{slug}.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(guide_html(slug, g, points, brand))
        jobs.append({"html": src, "pdf": os.path.join(folder, f"{slug}-guida.pdf")})

    manifest = os.path.join(tmp, "jobs.json")
    json.dump(jobs, open(manifest, "w"))
    subprocess.run(["node", os.path.join(HERE, "print_guides.cjs"), manifest], check=True)
    # The sales page says how long each guide is.
    data_path = os.path.join(SITE, "data", "rides.json")
    data = json.load(open(data_path, encoding="utf-8"))
    by_slug = {r["slug"]: r for r in data["rides"]}
    for j in jobs:
        raw = open(j["pdf"], "rb").read()
        pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
        slug = os.path.basename(j["pdf"])[:-len("-guida.pdf")]
        if slug in by_slug:
            by_slug[slug].setdefault("guide", {})["pages"] = pages
        print(f"{os.path.relpath(j['pdf'], ROOT)}: {pages} pages, {len(raw) // 1024} KB")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    # Each bundle: every ride's GPX and PDF guide in one archive.
    for b in store["bundles"]:
        path = os.path.join(PRIVATE, f"{b['slug']}.zip")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for slug in b["rides"]:
                z.write(os.path.join(PRIVATE, f"{slug}.gpx"), f"{slug}.gpx")
                z.write(os.path.join(PRIVATE, f"{slug}-guida.pdf"), f"{slug}-guida.pdf")
        print(f"bundle {b['slug']}: {len(b['rides'])} rides -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
