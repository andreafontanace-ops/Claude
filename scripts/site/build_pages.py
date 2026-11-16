"""Write one static HTML page per ride, plus sitemap.xml and robots.txt.

    python scripts/site/build_pages.py

Static pages give every pass its own address and its own title for search
engines ("Colle dell'Agnello in moto: traccia GPX"); app.js then adds the
map, the elevation profile and the buy button on top. The Pages workflow
runs this before every deploy, so prices in the structured data always match
site/store.json. Standard library only.
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITE = os.path.join(ROOT, "site")


def fmt_num(v, d=0):
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_km(v):
    return f"{fmt_num(v, 1 if v < 100 else 0)} km"


def fmt_m(v):
    return f"{fmt_num(v)} m"


def fmt_dur(minutes):
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if h and m else f"{h} h" if h else f"{m} min"


def fmt_eur(v):
    return f"{fmt_num(v, 2)} €"


def top_of(ride):
    passes = [m["ele"] for m in ride["markers"] if m["kind"] == "pass"]
    return max(passes) if passes else ride["maxEle"]


def guide_section(ride, free, e):
    """The sales pitch for the guide: what is inside, when to go, and the
    photo stops by name as a teaser. Restaurants and hotels stay in the
    guide; the page only says how many there are."""
    g = ride.get("guide")
    if not g:
        return ""
    season = g.get("season") or {}
    pages = f" di {g['pages']} pagine" if g.get("pages") else ""
    reco = (f" {g['recommended']} li abbiamo provati di persona e sono segnati come consigliati."
            if g.get("recommended") else "")
    spots = "".join(f"<li><strong>{e(s['name'])}</strong><span>km {fmt_num(s['km'], 1)}</span></li>"
                    for s in g.get("spots", []))
    items = [
        ("Traccia GPX", f"{fmt_num(ride['trackPoints'])} punti con quota, percorso per Garmin e TomTom, "
                        "e tutti i punti della guida come waypoint nel navigatore."),
        (f"Guida PDF{pages}", "Mappa con i punti numerati, tabella chilometrica, profilo altimetrico, "
                              "istruzioni per caricare la traccia."),
        (f"{len(g.get('spots', []))} punti panoramici", "Dove fermarsi per la vista e le foto, con chilometro e coordinate."),
        (f"{g.get('eat', 0)} ristoranti", "Lungo il percorso o a pochi metri, con telefono, email e sito per prenotare."),
        (f"{g.get('sleep', 0)} hotel e B&B", "Con i contatti diretti e il link alle recensioni pubbliche di ogni struttura." + reco),
        ("Quando andare", "Periodo consigliato, apertura dei passi e chiusure invernali."),
    ]
    lis = "".join(f"<li><b>{e(t)}</b><span>{e(d)}</span></li>" for t, d in items)
    label = "Inclusa gratis" if free else "Inclusa nell'acquisto"
    return f"""
    <section class="guide" aria-labelledby="guide-title">
      <div>
        <p class="eyebrow">{label}</p>
        <h2 id="guide-title">Cosa c'è nella guida</h2>
        <p class="guide-lead">Non solo la traccia: tutto quello che serve per organizzare il giro, in un PDF da tenere sul telefono.</p>
        <ul class="guide-list">{lis}</ul>
      </div>
      <aside class="guide-side">
        <div class="season-box">
          <p class="eyebrow">Quando andare</p>
          <p class="season-best">{e(season.get('best', ''))}</p>
          <p>{e(season.get('note', ''))}</p>
        </div>
        <div class="spots-box">
          <p class="eyebrow">I punti foto della guida</p>
          <ul>{spots}</ul>
        </div>
      </aside>
    </section>"""


def page(ride, store):
    e = html.escape
    brand = store["brand"]
    prod = store["products"].get(ride["slug"], {})
    free = prod.get("free", False)
    passes = [m for m in ride["markers"] if m["kind"] == "pass"]
    stops = [m for m in ride["markers"] if m["kind"] == "stop"]
    title = f"{ride['title']} in moto: traccia GPX e guida · {brand}"
    desc = (f"{ride['subtitle']}. {fmt_km(ride['km'])}, {fmt_m(ride['ascent'])} di salita, "
            f"quota massima {fmt_m(top_of(ride))}. "
            + ("Traccia GPX e guida gratuite." if free else f"Traccia GPX e guida PDF con ristoranti, hotel e punti foto a {fmt_eur(prod.get('price', 0))}."))

    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": f"{ride['title']}: traccia GPX per moto",
        "description": ride["description"],
        "brand": {"@type": "Brand", "name": brand},
        "category": "Tracce GPX",
        "offers": {"@type": "Offer", "priceCurrency": "EUR",
                   "price": "0.00" if free else f"{prod.get('price', 0):.2f}",
                   "availability": "https://schema.org/InStock"
                   if free or prod.get("checkout") else "https://schema.org/PreOrder"},
    }
    if store.get("siteUrl"):
        ld["url"] = f"{store['siteUrl'].rstrip('/')}/tracce/{ride['slug']}.html"

    if len(ride["closures"]) > 1:
        closures = " o ".join(ride["closures"]) + ", a seconda del passo"
    elif ride["closures"]:
        closures = ride["closures"][0]
    else:
        closures = "non segnalata in OpenStreetMap"
    roads_row = (f"<dt>Strade principali</dt><dd>{e(', '.join(ride['roads']))}</dd>"
                 if ride["roads"] else "")
    route = " → ".join(m["name"] for m in sorted(ride["markers"], key=lambda m: m["km"]))
    highlights = "".join(f"<li>{e(h)}</li>" for h in ride["highlights"])
    pass_list = "".join(f"<li>{e(m['name'])}, {fmt_m(m['ele'])}, al km {fmt_num(m['km'], 1)}</li>"
                        for m in passes)
    guide = guide_section(ride, free, e)

    return f"""<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:type" content="product">
  <link rel="icon" href="../favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="../vendor/leaflet/leaflet.css">
  <link rel="stylesheet" href="../style.css">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body data-page="ride" data-base="../" data-slug="{e(ride['slug'])}">
  <header class="top">
    <div class="wrap">
      <a class="brand" href="../" aria-label="{e(brand)}, home">
        <svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="15" fill="#231f16"/><path d="M9 25c6 0 13-1.5 13-4s-12-2-12-5 12-2.5 12-5-7-4-13-4" fill="none" stroke="#c0392b" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>
        {e(brand)}
      </a>
      <nav class="nav" aria-label="Sezioni">
        <a href="../#tracce" class="nav-key">Tracce</a>
        <a href="../#pacchetti">Pacchetti</a>
        <a href="../#domande">Domande</a>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <p class="crumbs"><a href="../#tracce">Tracce</a> / {e(ride['area'])}</p>
    <div class="ride-head">
      <div>
        <p class="eyebrow">{e(ride['area'])} · {'Traccia gratuita' if free else 'Traccia GPX'}</p>
        <h1>{e(ride['title'])}</h1>
        <p class="sub">{e(ride['subtitle'])}</p>
      </div>
      <div class="buybox" id="buybox">
        <div class="price">{'Gratis' if free else e(fmt_eur(prod.get('price', 0)))}</div>
      </div>
    </div>

    <dl class="big-stats">
      <div><dt>Distanza</dt><dd>{fmt_km(ride['km'])}</dd></div>
      <div><dt>Salita</dt><dd>{fmt_m(ride['ascent'])}</dd></div>
      <div><dt>Discesa</dt><dd>{fmt_m(ride['descent'])}</dd></div>
      <div><dt>Quota max</dt><dd>{fmt_m(top_of(ride))}</dd></div>
      <div><dt>Guida</dt><dd>{fmt_dur(ride['minutes'])}</dd></div>
    </dl>

    <div class="ride-map" id="ride-map" role="region" aria-label="Mappa del percorso"></div>

    <div class="ride-body">
      <div>
        <h2 style="margin-bottom:12px">Il giro</h2>
        <p>{e(ride['description'])}</p>
        <ul>{highlights}</ul>
        <div id="bundle-hint"></div>
      </div>
      <dl class="facts">
        <dt>Percorso</dt><dd>{e(route)}</dd>
        <dt>Passi</dt><dd><ul style="margin:0;padding-left:18px">{pass_list}</ul></dd>
        {roads_row}
        <dt>Chiusura invernale</dt><dd>{e(closures)}</dd>
        <dt>Tempo di guida</dt><dd>{fmt_dur(ride['minutes'])}, soste escluse (indicativo)</dd>
        <dt>Tappe</dt><dd>{len(stops)} tappe e {len(passes)} {'passo' if len(passes) == 1 else 'passi'}</dd>
      </dl>
    </div>

    {guide}

    <section class="profile" aria-labelledby="profile-title">
      <h2 id="profile-title">Profilo altimetrico</h2>
      <div id="profile-chart"></div>
    </section>

    <p class="callout" style="margin-top:24px">Traccia indicativa calcolata sulla rete stradale di OpenStreetMap. Prima di partire verifica aperture, chiusure e lavori; in strada vale sempre la segnaletica.</p>
  </main>

  <footer class="foot">
    <div class="wrap">
      <div>
        <p><strong>{e(brand)}</strong> · Tracce GPX dei passi alpini in moto.</p>
        <p class="muted">Le tracce sono indicative. Guida con prudenza e rispetta il codice della strada.</p>
      </div>
      <div>
        <nav aria-label="Informazioni">
          <a href="../condizioni.html">Condizioni di vendita</a>
          <a href="../privacy.html">Privacy</a>
        </nav>
        <p class="muted" style="margin-top:10px">Dati stradali © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> (ODbL), distribuiti da <a href="https://overturemaps.org">Overture Maps</a>. Quote: SRTM via AWS Terrain Tiles.</p>
      </div>
    </div>
  </footer>

  <script src="../vendor/leaflet/leaflet.js"></script>
  <script src="../app.js"></script>
</body>
</html>
"""


def main():
    store = json.load(open(os.path.join(SITE, "store.json"), encoding="utf-8"))
    rides = json.load(open(os.path.join(SITE, "data", "rides.json"), encoding="utf-8"))["rides"]
    out = os.path.join(SITE, "tracce")
    os.makedirs(out, exist_ok=True)
    for ride in rides:
        with open(os.path.join(out, f"{ride['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(page(ride, store))
    print(f"{len(rides)} ride pages -> site/tracce/")

    base = (store.get("siteUrl") or "").rstrip("/")
    robots = "User-agent: *\nAllow: /\n"
    if base:
        urls = [f"{base}/"] + [f"{base}/tracce/{r['slug']}.html" for r in rides]
        sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        sitemap += [f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls]
        sitemap.append("</urlset>\n")
        with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write("\n".join(sitemap))
        robots += f"Sitemap: {base}/sitemap.xml\n"
        print(f"sitemap.xml with {len(urls)} urls")
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)


if __name__ == "__main__":
    main()
