"""Builds src/TrebeccoTour/geoData.ts: Varzi - Zavattarello - Trebecco.

The SP207 north-east out of Varzi, over the Passo di Pietragavina (730 m) and
down past Crociglia to Zavattarello and its castle; then off the provincial
road a little after the village, by Valle di Sotto and San Silverio to
Trebecco, across the line into Emilia-Romagna. 20 km.

Everything on the map is OpenStreetMap by way of Overture Maps: the road
(routed by overture_route.py into tracks/trebecco.json), the road network
drawn under it, the Lago di Trebecco and the torrents, the villages along
the way and the Castello Dal Verme. Regions and comuni are openpolis/ISTAT.

Regenerate with:
    python3 scripts/geo/overture_route.py scripts/geo/tracks/trebecco.json \\
        --bbox 9.14,44.79,9.36,44.94 --prefer 207 \\
        --stop varzi=9.1969,44.82354 --stop zavattarello=9.26523,44.86848 \\
        --stop trebecco=9.30044,44.89461
    python3 scripts/geo/build_trebecco.py
"""
import json, math, os, sys

import pyarrow.dataset as ds
import shapely

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from overture_route import BUCKET, RELEASE, in_box, s3  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "TrebeccoTour", "geoData.ts")
TRACKS = os.path.join(HERE, "tracks")

MAP_WIDTH = 2000.0
LAT0 = 44.75
K = math.cos(math.radians(LAT0))


def rings(geometry):
    t, coords = geometry["type"], geometry["coordinates"]
    polys = [coords] if t == "Polygon" else coords
    for poly in polys:
        for ring in poly:
            yield [(pt[0], pt[1]) for pt in ring]


def load(path):
    with open(os.path.join(HERE, path)) as f:
        return json.load(f)


regions = load("italy_regions.geojson")
municipalities = load("limits_IT_municipalities.geojson")

# Same projection as the other Oltrepò films.
HOME_REGIONS = {"Lombardia", "Piemonte", "Emilia-Romagna", "Liguria"}
lons, lats = [], []
for feat in regions["features"]:
    if feat["properties"]["reg_name"] in HOME_REGIONS:
        for ring in rings(feat["geometry"]):
            for lon, lat in ring:
                lons.append(lon); lats.append(lat)
LON0, LON1 = min(lons), max(lons)
LATMIN, LATMAX = min(lats), max(lats)
SCALE = MAP_WIDTH / ((LON1 - LON0) * K)
MAP_HEIGHT = (LATMAX - LATMIN) * SCALE
KM_PER_UNIT = (LON1 - LON0) * K * 111.32 / MAP_WIDTH


def project(lon, lat):
    return ((lon - LON0) * K * SCALE, (LATMAX - lat) * SCALE)


def points_to_path(coords, min_step, close):
    pts = []
    for lon, lat in coords:
        p = project(lon, lat)
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) >= min_step:
            pts.append(p)
    if len(pts) < (3 if close else 2):
        return None
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + ("Z" if close else "")


def shapes(geojson, name_key, min_step, keep=None, window=None):
    out = []
    for feat in geojson["features"]:
        if keep and not keep(feat["properties"]):
            continue
        if window:
            xs = [p[0] for r in rings(feat["geometry"]) for p in r]
            ys = [p[1] for r in rings(feat["geometry"]) for p in r]
            if max(xs) < window[0] or min(xs) > window[2] or \
               max(ys) < window[1] or min(ys) > window[3]:
                continue
        parts = [p for p in (points_to_path(r, min_step, True) for r in rings(feat["geometry"])) if p]
        if parts:
            out.append((feat["properties"].get(name_key) or "", "".join(parts)))
    return out


home = shapes(regions, "reg_name", 0.35, keep=lambda p: p["reg_name"] in HOME_REGIONS)
beyond = shapes(regions, "reg_name", 0.9, keep=lambda p: p["reg_name"] not in HOME_REGIONS)
WINDOW = (9.06, 44.70, 9.44, 45.02)
comuni = shapes(municipalities, "name", 0.05, window=WINDOW)
print("home", len(home), "beyond", len(beyond), "comuni", len(comuni))


def metres(p, q):
    lon1, lat1, lon2, lat2 = map(math.radians, (*p, *q))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(h))


def inside(pt, ring):
    x, y = pt
    n = len(ring); hit = False; j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            hit = not hit
        j = i
    return hit


def comune_of(p):
    for f in municipalities["features"]:
        if f["properties"].get("prov_acr") in ("PV", "PC") and \
                any(inside(p, r) for r in rings(f["geometry"])):
            return f["properties"]["name"]
    return "?"


def region_of(p):
    for f in regions["features"]:
        if any(inside(p, r) for r in rings(f["geometry"])):
            return f["properties"]["reg_name"]
    return "?"


# --- the road ------------------------------------------------------------------

track_t = json.load(open(os.path.join(TRACKS, "trebecco.json")))
track = [tuple(p) for p in track_t["lonlat"]]
stops = {k: tuple(v) for k, v in track_t["stops"].items()}
cum = [0.0]
for p, q in zip(track, track[1:]):
    cum.append(cum[-1] + metres(p, q))


z_i = track.index(stops["zavattarello"])
leg1, leg2 = track[: z_i + 1], track[z_i:]
km1, km2 = cum[z_i] / 1000, (cum[-1] - cum[z_i]) / 1000
print(f"Varzi - Zavattarello {km1:.1f} km, Zavattarello - Trebecco {km2:.1f} km")

crossings = [i for i in range(1, len(track)) if region_of(track[i - 1]) != region_of(track[i])]
for i in crossings:
    print(f"  {region_of(track[i - 1])} -> {region_of(track[i])} at km {cum[i] / 1000:.1f}")
if len(crossings) != 1:
    sys.exit("expected the road to cross one regional border")


# --- places ----------------------------------------------------------------------

# Overture Maps points (OSM). No elevations: only the pass has a mapped one.
CASTLE = (9.26269, 44.86988)   # Castello Dal Verme
PLACES = [
    ("varzi", "VARZI", stops["varzi"], 416),
    ("zavattarello", "ZAVATTARELLO", stops["zavattarello"], 0),
    ("trebecco", "TREBECCO", stops["trebecco"], 0),
]
for pid, want in [("varzi", "Varzi"), ("zavattarello", "Zavattarello"), ("trebecco", "Alta Val Tidone")]:
    got = comune_of(stops[pid])
    print(f"  {pid:12s} in {got}, {region_of(stops[pid])}")

# Villages and the pass the road goes through, as the line reaches them.
# (name, lon, lat, label side: 1 = right of the road, -1 = left)
ALONG = [
    ("Pavione", 9.21205, 44.82279, 1),
    ("Passo di Pietragavina", 9.2416, 44.83794, -1),
    ("Crociglia", 9.25669, 44.85762, -1),
    ("Valle di Sotto", 9.27666, 44.87281, 1),
    ("San Silverio", 9.28281, 44.88557, -1),
]
PASS_ELEV = 730

ll1 = [project(*p) for p in leg1]
ll2 = [project(*p) for p in leg2]


def arc_on(points_ll, ll):
    c = [0.0]
    for p, q in zip(points_ll, points_ll[1:]):
        c.append(c[-1] + metres(p, q))
    i = min(range(len(points_ll)), key=lambda k: metres(points_ll[k], ll))
    return c[i] / c[-1], metres(points_ll[i], ll)


along = []
for name, lon, lat, side in ALONG:
    on1, d1 = arc_on(leg1, (lon, lat))
    on2, d2 = arc_on(leg2, (lon, lat))
    leg, at, d = ("leg1", on1, d1) if d1 <= d2 else ("leg2", on2, d2)
    if d > 400:
        sys.exit(f"{name} is {d:.0f} m off the road")
    x, y = project(lon, lat)
    along.append((name, x, y, leg, at, side))
    print(f"  {name:22s} {leg} at {at:.2f} ({d:.0f} m off)")


# --- the map under the road: other roads, the lake, the torrents -------------------

fs = s3()
BOX = (9.10, 44.76, 9.42, 44.97)
seg = ds.dataset(f"{BUCKET}/release/{RELEASE}/theme=transportation/type=segment/", filesystem=fs, format="parquet")
roads = []
for r in seg.to_table(columns=["class", "subtype", "geometry"], filter=in_box(BOX)).to_pylist():
    if r["subtype"] == "road" and r["class"] in ("primary", "secondary", "tertiary"):
        d = points_to_path(shapely.from_wkb(r["geometry"]).coords, 0.15, False)
        if d:
            roads.append((r["class"], d))
water_ds = ds.dataset(f"{BUCKET}/release/{RELEASE}/theme=base/type=water/", filesystem=fs, format="parquet")
lakes, rivers = [], []
LAKE_NAME = "Lago di Trebecco"
lake_centre = None
for r in water_ds.to_table(columns=["subtype", "class", "names", "geometry"], filter=in_box(BOX)).to_pylist():
    g = shapely.from_wkb(r["geometry"])
    name = (r.get("names") or {}).get("primary") or ""
    if g.geom_type in ("Polygon", "MultiPolygon") and r["subtype"] in ("lake", "reservoir") and g.area > 2e-6:
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        d = "".join(p for p in (points_to_path(pg.exterior.coords, 0.05, True) for pg in polys) if p)
        lakes.append(d)
        if name == LAKE_NAME:
            lake_centre = project(*g.representative_point().coords[0])
    elif g.geom_type == "LineString" and r["class"] == "river":
        d = points_to_path(g.coords, 0.1, False)
        if d:
            rivers.append(d)
if lake_centre is None:
    sys.exit("no Lago di Trebecco in the water theme")
print(f"map: {len(roads)} roads, {len(lakes)} lakes, {len(rivers)} river pieces")


def catmull_rom_to_bezier(points):
    pts_ = [points[0]] + points + [points[-1]]
    d = f"M{points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(pts_) - 2):
        p0, p1, p2, p3 = pts_[i - 1], pts_[i], pts_[i + 1], pts_[i + 2]
        d += (f"C{p1[0] + (p2[0]-p0[0])/6:.2f},{p1[1] + (p2[1]-p0[1])/6:.2f} "
              f"{p2[0] - (p3[0]-p1[0])/6:.2f},{p2[1] - (p3[1]-p1[1])/6:.2f} "
              f"{p2[0]:.2f},{p2[1]:.2f}")
    return d


# Where the opening zoom is headed: the middle of the road.
mid = project(*track[len(track) // 2])

# --- framing -----------------------------------------------------------------------

xy = ll1 + ll2
xs = [p[0] for p in xy]; ys = [p[1] for p in xy]
route_box = (min(xs) - 5.0, min(ys) - 6.0, max(xs) + 5.0, max(ys) + 6.0)
cx, cy = (route_box[0] + route_box[2]) / 2, (route_box[1] + route_box[3]) / 2
# The opening: the four regions round the Oltrepò, the road a speck in the
# middle - 150 km across.
half = 150 / KM_PER_UNIT / 2
region_box = (cx - half, cy - half, cx + half, cy + half)
kx, ky = project(*CASTLE)

# Region names for the opening, checked to sit in their own region.
REGION_NAMES = [
    ("LOMBARDIA", (9.25, 45.30), "Lombardia"),
    ("EMILIA-ROMAGNA", (9.72, 44.72), "Emilia-Romagna"),
    ("PIEMONTE", (8.86, 44.88), "Piemonte"),
    ("LIGURIA", (9.05, 44.42), "Liguria"),
]
for name, ll, want in REGION_NAMES:
    if region_of(ll) != want:
        sys.exit(f"{name} label is not in {want}")
# And the two the road runs between, for the close framing.
# Close up, Emilia-Romagna is only the corner round the lake, top right, so
# its name goes there on two lines to keep clear of the like/share rail.
CLOSE_TAGS = [
    ("LOMBARDIA", (9.2050, 44.8920), "Lombardia"),
    ("EMILIA-|ROMAGNA", (9.2921, 44.9232), "Emilia-Romagna"),
]
for name, ll, want in CLOSE_TAGS:
    if region_of(ll) != want:
        sys.exit(f"{name} tag is not in {want}")


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit --------------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_trebecco.py - do not hand-edit.")
out.append("// Road, road network, water, villages, castle: OpenStreetMap via Overture Maps.")
out.append("// Map: openpolis/geojson-italy (regioni, comuni).")
out.append("// Equirectangular projection, longitude scaled by cos(44.75 deg).")
out.append('import { BBox, RegionShape, RouteSegment, Waypoint } from "../shared/types";')
out.append("")
out.append(f"export const MAP_WIDTH = {MAP_WIDTH:.2f};")
out.append(f"export const MAP_HEIGHT = {MAP_HEIGHT:.2f};")
out.append("")
for var, rows, note in [
    ("home", home, "Lombardia, Piemonte, Emilia-Romagna, Liguria."),
    ("beyond", beyond, "The rest of the country, in greys."),
    ("comuni", comuni, "The comuni around the road."),
]:
    out.append(f"// {note}")
    out.append(f"export const {var}: RegionShape[] = [")
    for name, d in rows:
        out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
    out.append("];")
    out.append("")
out.append("// The main roads round about (primary, secondary, tertiary).")
out.append("export const roadNet: { cls: string; d: string }[] = [")
for cls, d in roads:
    out.append(f'  {{ cls: "{cls}", d: "{d}" }},')
out.append("];")
out.append("")
out.append("export const lakes: string[] = [")
for d in lakes:
    out.append(f'  "{d}",')
out.append("];")
out.append("export const rivers: string[] = [")
for d in rivers:
    out.append(f'  "{d}",')
out.append("];")
out.append(f"export const LAKE_LABEL = {{ name: \"{LAKE_NAME}\", x: {lake_centre[0]:.2f}, y: {lake_centre[1]:.2f} }};")
out.append("")
out.append("export const places: Waypoint[] = [")
for pid, name, (lo, la), e in PLACES:
    x, y = project(lo, la)
    out.append(f'  {{ id: "{pid}", name: "{name}", subtitle: null, '
               f"x: {x:.2f}, y: {y:.2f}, elevation: {e} }},")
out.append("];")
out.append("")
out.append(f"export const CASTLE = {{ name: \"CASTELLO DAL VERME\", x: {kx:.2f}, y: {ky:.2f} }};")
out.append("")
out.append("// Villages and the pass along the road: which leg, and where on it (0..1).")
out.append("export const along: { name: string; x: number; y: number; leg: \"leg1\" | \"leg2\"; at: number; side: number }[] = [")
for name, x, y, leg, at, side in along:
    out.append(f'  {{ name: "{name}", x: {x:.2f}, y: {y:.2f}, leg: "{leg}", at: {at:.3f}, side: {side} }},')
out.append("];")
out.append(f"export const PASS_ELEVATION = {PASS_ELEV};")
out.append("")
out.append("export const regionNames = [")
for name, ll, _ in REGION_NAMES:
    x, y = project(*ll)
    out.append(f'  {{ name: "{name}", x: {x:.2f}, y: {y:.2f} }},')
out.append("];")
out.append("export const regionTags = [")
for name, ll, _ in CLOSE_TAGS:
    x, y = project(*ll)
    out.append(f'  {{ lines: {json.dumps(name.split("|"))}, x: {x:.2f}, y: {y:.2f} }},')
out.append("];")
out.append("")
for var, pts, km in [("leg1", ll1, km1), ("leg2", ll2, km2)]:
    out.append(f"// {km:.1f} km.")
    out.append(f"export const {var}: RouteSegment = {{")
    out.append(f'  id: "{var}", d: "{catmull_rom_to_bezier(pts)}",')
    out.append("  points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in pts) + "],")
    out.append("};")
    out.append("")
out.append("")
out.append(f"export const TARGET = {{ x: {mid[0]:.2f}, y: {mid[1]:.2f} }};")
out.append(bbox_literal("REGION_BBOX", region_box))
out.append(bbox_literal("ROUTE_BBOX", route_box))
out.append("")

os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(out))
for nm, b in [("region", region_box), ("route", route_box)]:
    w, h = b[2] - b[0], b[3] - b[1]
    sc = min(840 / w, 1250 / h)
    print(f"{nm:7s} {w*KM_PER_UNIT:6.1f} x {h*KM_PER_UNIT:5.1f} km  {KM_PER_UNIT*1000/sc:6.1f} m/px")
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
