"""Builds src/Seasons/geoData.ts: the maps for "4 stagioni, 4 tappe".

One projection for the whole Western Alps (equirectangular, longitude scaled
by cos 45 deg, 1 map unit = 1 km), so the three stages sit on one map:

  spring  Gorges du Verdon       - Alpes-de-Haute-Provence, France
  summer  Gole della Val Taleggio - the Enna's gorge, Bergamo, Lombardia
  autumn  Valle Staffora         - Oltrepò Pavese, Lombardia

For the opening, the countries (Natural Earth 1:50m). Close to each stage the
finer admin lines take over - the départements, the provinces, the regions -
with the rivers and lakes that make the place (the Verdon and the Lac de
Sainte-Croix, the Enna, the Staffora; OpenStreetMap via Overture Maps) and real
contour lines from the Terrarium elevation tiles (AWS Open Data).

    python3 scripts/geo/build_seasons.py NATURAL_EARTH_COUNTRIES.geojson
"""
import io, json, math, os, ssl, sys, time, urllib.request

import numpy as np
import pyarrow.dataset as ds
import shapely
import shapely.ops
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import box, shape
from shapely.ops import unary_union
from skimage import measure

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from overture_route import BUCKET, RELEASE, in_box, s3  # noqa: E402

OUT_TS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "src", "Seasons", "geoData.ts")
LON0, LON1, LAT0, LAT1 = 2.0, 15.5, 40.5, 49.5
K = math.cos(math.radians(45.0))
KM = 111.32


def project(lon, lat):
    return ((lon - LON0) * K * KM, (LAT1 - lat) * KM)


def geom_path(g, tol):
    """SVG path of a (multi)polygon or (multi)line in map units."""
    g = g.simplify(tol / KM, preserve_topology=True)
    out = []
    for part in getattr(g, "geoms", [g]):
        if part.is_empty:
            continue
        if part.geom_type == "Polygon":
            for ring in [part.exterior, *part.interiors]:
                pts = [project(*c) for c in ring.coords]
                if len(pts) >= 4:
                    out.append("M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + "Z")
        elif part.geom_type == "LineString":
            pts = [project(*c) for c in part.coords]
            if len(pts) >= 2:
                out.append("M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in pts))
    return "".join(out)


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


# --- countries ---------------------------------------------------------------------

ne = json.load(open(sys.argv[1]))
FRAME = box(LON0, LAT0, LON1, LAT1)
NAMES_IT = {"Italy": "ITALIA", "France": "FRANCIA", "Switzerland": "SVIZZERA", "Austria": "AUSTRIA",
            "Germany": "GERMANIA", "Slovenia": "SLOVENIA", "Spain": "SPAGNA", "Croatia": "CROAZIA",
            "Monaco": "", "Liechtenstein": "", "San Marino": "", "Vatican": "", "Andorra": "",
            "Luxembourg": "", "Belgium": "BELGIO", "Czechia": "", "Hungary": "", "Bosnia and Herz.": ""}
countries = []
for f in ne["features"]:
    n = f["properties"].get("NAME")
    g = shape(f["geometry"])
    if not g.intersects(FRAME):
        continue
    countries.append((n, NAMES_IT.get(n, ""), geom_path(g.intersection(FRAME.buffer(1)), 1.2)))
print("countries", [c[0] for c in countries])
# Placed inside the opening's frame (lon 4.6-11.4), each checked to fall in
# its own country.
COUNTRY_LABELS = [("FRANCIA", 5.6, 46.75), ("SVIZZERA", 7.95, 46.80), ("ITALIA", 10.9, 44.6),
                  ("AUSTRIA", 11.0, 47.25), ("GERMANIA", 9.6, 48.3)]
_shapes = {f["properties"].get("NAME"): shape(f["geometry"]) for f in ne["features"]}
for lab, lo, la in COUNTRY_LABELS:
    owner = next((n for n, it in NAMES_IT.items() if it == lab), None)
    if not _shapes[owner].contains(shapely.geometry.Point(lo, la)):
        sys.exit(f"{lab} label is not inside {owner}")

# --- the stages ----------------------------------------------------------------------

fs = s3()


def overture(theme, bbox, cols):
    d = ds.dataset(f"{BUCKET}/release/{RELEASE}/{theme}", filesystem=fs, format="parquet")
    return d.to_table(columns=[c for c in cols if c in d.schema.names], filter=in_box(bbox)).to_pylist()


def water(bbox, river_names, lake_min_km2=0.5):
    rivers, lakes = [], []
    for r in overture("theme=base/type=water/", bbox, ["subtype", "class", "names", "geometry"]):
        g = shapely.from_wkb(r["geometry"])
        n = (r.get("names") or {}).get("primary") or ""
        if g.geom_type in ("LineString", "MultiLineString") and n in river_names:
            rivers.append(g)
        elif g.geom_type in ("Polygon", "MultiPolygon") and r["subtype"] in ("lake", "reservoir"):
            if g.area * KM * KM * K > lake_min_km2:
                lakes.append(g)
    return unary_union(rivers) if rivers else None, lakes


TILE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None


def tile_xy(lon, lat, z):
    n = 2 ** z
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def contours(bbox, step, z=12, grid=700):
    fx0, fy0 = tile_xy(bbox[0], bbox[3], z)
    fx1, fy1 = tile_xy(bbox[2], bbox[1], z)
    tx, ty = range(int(fx0), int(fx1) + 1), range(int(fy0), int(fy1) + 1)

    def fetch(x, y):
        for attempt in range(5):  # the tile server drops the odd connection
            try:
                with urllib.request.urlopen(TILE.format(z=z, x=x, y=y), context=CTX, timeout=60) as r:
                    a = np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB")).astype(np.float64)
                return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)

    mosaic = np.vstack([np.hstack([fetch(x, y) for x in tx]) for y in ty])
    gx = np.linspace(fx0, fx1, grid) - tx[0]
    gy = np.linspace(fy0, fy1, grid) - ty[0]
    yy, xx = np.meshgrid(gy * 256, gx * 256, indexing="ij")
    elev = ndi.gaussian_filter(ndi.map_coordinates(mosaic, [yy, xx], order=1), 1.6)
    lon = np.linspace(bbox[0], bbox[2], grid)
    # Mercator y to latitude, row by row.
    lat = [math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (fy0 + (fy1 - fy0) * i / (grid - 1)) / 2 ** z))))
           for i in range(grid)]
    out = []
    for level in range(int(elev.min() // step + 1) * step, int(elev.max()) + 1, step):
        for c in measure.find_contours(elev, level):
            if len(c) < 25:
                continue
            ll = [(lon[0] + (lon[-1] - lon[0]) * p[1] / (grid - 1),
                   lat[int(round(p[0]))]) for p in c]
            line = shapely.geometry.LineString(ll)
            d = geom_path(line, 0.04)
            if d and line.length * KM > 1.0:
                out.append((level, level % (step * 5) == 0, d))
    print(f"  contours {len(out)} lines, {elev.min():.0f}-{elev.max():.0f} m")
    return out


regions = load("italy_regions.geojson")
provinces = load("italy_provinces.geojson")
departements = load("france_departements.geojson")


def admin(features, key, near, km):
    """Admin areas within `km` of a point: fills and names."""
    lon, lat = near
    win = box(lon - km / (KM * K), lat - km / KM, lon + km / (KM * K), lat + km / KM)
    out = []
    for f in features:
        g = shape(f["geometry"])
        if g.intersects(win):
            out.append((f["properties"][key], g))
    return out


STAGES = [
    dict(id="verdon", season="PRIMAVERA", n=1, name="GORGES DU VERDON",
         sub="Alpes-de-Haute-Provence · Francia", point=(6.40067, 43.79174), elevation=None,
         window_km=34, step=100, rivers=["Le Verdon", "Verdon"],
         admin=(departements["features"], "nom"),
         tags=[("ALPES-DE-HAUTE-PROVENCE", 6.30, 43.88), ("VAR", 6.38, 43.70)]),
    # The gorge is the Enna's, between Peghera and San Giovanni Bianco; the pin
    # is snapped onto the river at its middle.
    dict(id="taleggio", season="ESTATE", n=2, name="GOLE DELLA VAL TALEGGIO",
         sub="Prealpi Orobie · Bergamo · Lombardia", point=(9.615, 45.8835), snap=True, elevation=None,
         window_km=22, step=100, rivers=["Torrente Enna", "Fiume Brembo"],
         admin=(provinces["features"], "prov_name"),
         tags=[("BERGAMO", 9.73, 45.845), ("LECCO", 9.48, 45.93)],
         tag_areas={"BERGAMO": "Bergamo", "LECCO": "Lecco"}),
    dict(id="staffora", season="AUTUNNO", n=3, name="VALLE STAFFORA",
         sub="Oltrepò Pavese · Lombardia · Italia", point=(9.1969, 44.82354), elevation=None,
         window_km=34, step=100, rivers=["Torrente Staffora"],
         admin=(regions["features"], "reg_name"),
         tags=[("LOMBARDIA", 9.08, 44.90), ("EMILIA-ROMAGNA", 9.40, 44.78)]),
]

stage_out = []
for st in STAGES:
    print(st["id"])
    lon, lat = st["point"]
    w = st["window_km"]
    bb = (lon - w / (KM * K) * 0.75, lat - w / KM * 0.75, lon + w / (KM * K) * 0.75, lat + w / KM * 0.75)
    river, lakes = water((bb[0] - 0.2, bb[1] - 0.2, bb[2] + 0.2, bb[3] + 0.2), st["rivers"])
    if st.get("snap"):
        if river is None:
            sys.exit(f"{st['id']}: no river to snap the pin to")
        snapped = shapely.ops.nearest_points(river, shapely.geometry.Point(lon, lat))[0]
        print(f"  pin snapped {snapped.distance(shapely.geometry.Point(lon, lat)) * KM * 1000:.0f} m onto the river")
        lon, lat = snapped.x, snapped.y
        st["point"] = (lon, lat)
    feats, key = st["admin"]
    areas = [(n, g, True) for n, g in admin(feats, key, st["point"], w * 1.6)]
    if "neighbours" in st:
        nf, nk = st["neighbours"]
        areas += [(n, g, False) for n, g in admin(nf, nk, st["point"], w * 1.6)]
    cont = contours(bb, st["step"])
    x, y = project(lon, lat)
    hw = w / 2
    stage_out.append(dict(
        id=st["id"], season=st["season"], n=st["n"], name=st["name"], sub=st["sub"],
        elevation=st["elevation"], x=x, y=y,
        coords=f"{abs(lat):.4f}°{'N' if lat >= 0 else 'S'} {abs(lon):.4f}°{'E' if lon >= 0 else 'W'}",
        box=(x - hw, y - hw * 1.25, x + hw, y + hw * 1.25),
        areas=[(n, geom_path(g, 0.03), home) for n, g, home in areas],
        river=geom_path(river, 0.02) if river is not None else "",
        lakes=[geom_path(g, 0.02) for g in lakes],
        contours=cont,
        tags=[(t, *project(tl, ta)) for t, tl, ta in st["tags"]],
    ))
    home_country = {"verdon": "France", "taleggio": "Italy", "staffora": "Italy"}[st["id"]]
    for t, tl, ta in st["tags"]:
        pt = shapely.geometry.Point(tl, ta)
        if t in st.get("tag_areas", {}):
            want = st["tag_areas"][t]
            if not any(n == want and g.contains(pt) for n, g, _ in areas):
                sys.exit(f"{t} tag is not inside {want}")
        elif not _shapes["Italy" if t == "ITALIA" else home_country].contains(pt):
            sys.exit(f"{t} tag is not inside {home_country}")
    print(f"  {len(areas)} admin areas, river {'yes' if river is not None else 'no'}, {len(lakes)} lakes")


def dms(v, pos, neg):
    d = int(abs(v)); m = int((abs(v) - d) * 60); s = round(((abs(v) - d) * 60 - m) * 60)
    if s == 60:
        m, s = m + 1, 0
    return f"{d}°{m:02d}′{s:02d}″{pos if v >= 0 else neg}"


# --- emit ----------------------------------------------------------------------------

o = ["// Auto-generated by scripts/geo/build_seasons.py - do not hand-edit.",
     "// Countries: Natural Earth 1:50m. Admin: ISTAT/openpolis and IGN (via the repo's",
     "// geojson). Water: OpenStreetMap via Overture Maps. Contours: Terrarium tiles (AWS Open Data).",
     "// Equirectangular, longitude scaled by cos(45 deg); 1 unit = 1 km.", ""]
W, H = project(LON1, LAT0)
o.append(f"export const MAP_W = {W:.1f};")
o.append(f"export const MAP_H = {H:.1f};")
o.append("export const countries: { name: string; label: string; d: string }[] = [")
for n, lab, d in countries:
    o.append(f"  {{ name: {json.dumps(n)}, label: {json.dumps(lab)}, d: \"{d}\" }},")
o.append("];")
o.append("export const countryLabels = [")
for lab, lo, la in COUNTRY_LABELS:
    cx, cy = project(lo, la)
    o.append(f'  {{ label: "{lab}", x: {cx:.1f}, y: {cy:.1f} }},')
o.append("];")
o.append("")
o.append("export type Stage = {")
o.append("  id: string; season: string; n: number; name: string; sub: string; elevation: number | null;")
o.append("  x: number; y: number; coords: string; box: { x0: number; y0: number; x1: number; y1: number };")
o.append("  areas: { name: string; d: string; home: boolean }[]; river: string; lakes: string[];")
o.append("  contours: { level: number; index: boolean; d: string }[]; tags: { label: string; x: number; y: number }[];")
o.append("};")
o.append("export const stages: Stage[] = [")
for s in stage_out:
    lat = STAGES[[t["id"] for t in STAGES].index(s["id"])]["point"][1]
    lon = STAGES[[t["id"] for t in STAGES].index(s["id"])]["point"][0]
    o.append("  {")
    o.append(f'    id: "{s["id"]}", season: "{s["season"]}", n: {s["n"]}, name: "{s["name"]}", sub: {json.dumps(s["sub"])},')
    o.append(f'    elevation: {s["elevation"] if s["elevation"] else "null"}, x: {s["x"]:.2f}, y: {s["y"]:.2f},')
    o.append(f'    coords: "{dms(lat, "N", "S")} {dms(lon, "E", "W")}",')
    b = s["box"]
    o.append(f"    box: {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, x1: {b[2]:.2f}, y1: {b[3]:.2f} }},")
    o.append("    areas: [" + ",".join(f'{{ name: {json.dumps(n)}, d: "{d}", home: {"true" if h else "false"} }}'
                                      for n, d, h in s["areas"]) + "],")
    o.append(f'    river: "{s["river"]}",')
    o.append("    lakes: [" + ",".join(f'"{d}"' for d in s["lakes"]) + "],")
    o.append("    contours: [" + ",".join(f'{{ level: {lv}, index: {"true" if ix else "false"}, d: "{d}" }}'
                                         for lv, ix, d in s["contours"]) + "],")
    o.append("    tags: [" + ",".join(f'{{ label: "{t}", x: {tx:.2f}, y: {ty:.2f} }}' for t, tx, ty in s["tags"]) + "],")
    o.append("  },")
o.append("];")
o.append("")
os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(o))
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
