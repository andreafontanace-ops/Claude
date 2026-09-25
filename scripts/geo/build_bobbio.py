"""Builds src/BobbioTour/geoData.ts: the road from Brallo di Pregola to Bobbio.

North out of Brallo on the SP186 and SP89, east for most of the way on the
SP69 past Ceci and Ca' di Sopra, then the SS461 down into Bobbio and the Val
Trebbia, arriving at the Castello Malaspina Dal Verme. 17 km by Google.

The road comes from a Google Maps route screenshot through
screenshot_track.py (tracks/bobbio.json), fitted to the official region
boundaries like the others. Its start is Brallo, the same place the Giovà -
Brallo film ends on, which makes a free check: the two fits put it 113 m apart,
inside the method's ~100-150 m. The start is eased onto the earlier film's
Brallo so the two films join on one point.

Regenerate with:  python3 scripts/geo/build_bobbio.py
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "BobbioTour", "geoData.ts")
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

# Same projection as the other Oltrepò films, so a map unit means the same
# thing in all of them.
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


def ring_to_points(ring, min_step):
    out = []
    for lon, lat in ring:
        p = project(lon, lat)
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= min_step:
            out.append(p)
    return out


def ring_to_path(ring, min_step):
    pts = ring_to_points(ring, min_step)
    if len(pts) < 3:
        return None
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


def feature_path(feat, min_step):
    parts = [p for p in (ring_to_path(r, min_step) for r in rings(feat["geometry"])) if p]
    return "".join(parts) if parts else None


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
        d = feature_path(feat, min_step)
        if d:
            out.append((feat["properties"].get(name_key) or "", d))
    return out


home = shapes(regions, "reg_name", 0.35, keep=lambda p: p["reg_name"] in HOME_REGIONS)
beyond = shapes(regions, "reg_name", 0.9, keep=lambda p: p["reg_name"] not in HOME_REGIONS)
# The route is 8 km east-west and 3.5 north-south; a portrait frame shows a
# good deal more above and below it than beside it, hence the tall window.
WINDOW = (9.20, 44.62, 9.48, 44.90)
comuni = shapes(municipalities, "name", 0.05, window=WINDOW)
print("home", len(home), "beyond", len(beyond), "comuni", len(comuni))


# --- the road ------------------------------------------------------------------

def metres(p, q):
    lon1, lat1, lon2, lat2 = map(math.radians, (*p, *q))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(h))


def read_track(name):
    path = os.path.join(TRACKS, f"{name}.json")
    if not os.path.exists(path):
        sys.exit(f"missing {path}: run screenshot_track.py on the {name} screenshot")
    return json.load(open(path))


track_t = read_track("bobbio")
track = [tuple(p) for p in track_t["lonlat"]]

# Brallo as the Giovà - Brallo film has it: where its two roads' ends meet.
prev_ends = [tuple(read_track(n)["lonlat"][-1]) for n in ("facile", "crinale")]
BRALLO = tuple(sum(v) / 2 for v in zip(*prev_ends))
gap = metres(track[0], BRALLO)
print(f"this screenshot puts Brallo {gap:.0f} m from where the last film ends")
if gap > 250:
    sys.exit("more than 250 m - check the georeference")

# Ease the start onto that point, the shift fading to nothing at Bobbio, so
# the two films join without a kink.
ds = [0.0]
for p, q in zip(track, track[1:]):
    ds.append(ds[-1] + metres(p, q))
shift = (BRALLO[0] - track[0][0], BRALLO[1] - track[0][1])
track = [(lon + shift[0] * (1 - d / ds[-1]), lat + shift[1] * (1 - d / ds[-1]))
         for (lon, lat), d in zip(track, ds)]
km = sum(metres(p, q) for p, q in zip(track, track[1:])) / 1000
print(f"drawn length {km:.1f} km (Google: 17 - the tightest bends merge in the screenshot)")


# --- places ----------------------------------------------------------------------

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


BOBBIO = track[-1]
PLACES = [
    ("brallo", "BRALLO DI PREGOLA", BRALLO, 950),
    ("bobbio", "BOBBIO", BOBBIO, 272),
]
for pid, _, ll, _ in PLACES:
    print(f"  {pid:7s} {ll[0]:.5f}, {ll[1]:.5f}  ({comune_of(ll)})")
if comune_of(BOBBIO) != "Bobbio":
    sys.exit("the arrival is not in the comune of Bobbio - check the screenshot fit")

line = [project(*p) for p in track]


def path_length(points):
    return sum(math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1])
               for i in range(1, len(points)))


def nearest_index(pts_, p):
    return min(range(len(pts_)), key=lambda i: math.hypot(pts_[i][0] - p[0], pts_[i][1] - p[1]))


total = path_length(line)


def arc_at(ll):
    i = nearest_index(line, project(*ll))
    return path_length(line[: i + 1]) / total


# Road plates sit on the stretch the screenshot labels with that number; the
# valley name sits in the Trebbia floor just south of the castle.
pois = track_t["pois"]
SHIELDS = [("SP69", arc_at(pois["sp69"])), ("SS461", arc_at(pois["ss461"]))]
TREBBIA = project(*pois["trebbia"])
print("plates", [(n, round(t, 3)) for n, t in SHIELDS])


def catmull_rom_to_bezier(points):
    pts_ = [points[0]] + points + [points[-1]]
    d = f"M{points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(pts_) - 2):
        p0, p1, p2, p3 = pts_[i - 1], pts_[i], pts_[i + 1], pts_[i + 2]
        d += (f"C{p1[0] + (p2[0]-p0[0])/6:.2f},{p1[1] + (p2[1]-p0[1])/6:.2f} "
              f"{p2[0] - (p3[0]-p1[0])/6:.2f},{p2[1] - (p3[1]-p1[1])/6:.2f} "
              f"{p2[0]:.2f},{p2[1]:.2f}")
    return d


# --- framing -----------------------------------------------------------------------

xs = [p[0] for p in line]; ys = [p[1] for p in line]
# Width-limited: the road runs across the frame. A little slack either side,
# since the end names sit above and below their pins and are nudged inwards.
PAD_X = 3.0
route_box = (min(xs) - PAD_X, min(ys) - 4.0, max(xs) + PAD_X, max(ys) + 4.0)
cx, cy = (route_box[0] + route_box[2]) / 2, (route_box[1] + route_box[3]) / 2
hw, hh = (route_box[2] - route_box[0]) / 2 * 1.25, (route_box[3] - route_box[1]) / 2 * 1.25
open_box = (cx - hw, cy - hh, cx + hw, cy + hh)


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit --------------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_bobbio.py - do not hand-edit.")
out.append("// Road: Google Maps route screenshot via scripts/geo/screenshot_track.py.")
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
out.append("export const places: Waypoint[] = [")
for pid, name, (lo, la), e in PLACES:
    x, y = project(lo, la)
    out.append(f'  {{ id: "{pid}", name: "{name}", subtitle: null, '
               f"x: {x:.2f}, y: {y:.2f}, elevation: {e} }},")
out.append("];")
out.append("")
out.append("export const road: RouteSegment = {")
out.append(f'  id: "bobbio", d: "{catmull_rom_to_bezier(line)}",')
out.append("  points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in line) + "],")
out.append("};")
out.append("")
out.append("// Road numbers, and where along the road (0..1 by arc length) each sits.")
out.append("export const shields: { label: string; at: number }[] = [")
for name, t in SHIELDS:
    out.append(f'  {{ label: "{name}", at: {t:.3f} }},')
out.append("];")
out.append("")
out.append("// The floor of the Val Trebbia, just south of the castle.")
out.append(f"export const TREBBIA = {{ x: {TREBBIA[0]:.2f}, y: {TREBBIA[1]:.2f} }};")
out.append("")
out.append(bbox_literal("OPEN_BBOX", open_box))
out.append(bbox_literal("ROUTE_BBOX", route_box))
out.append("")

os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(out))

for nm, b in [("open", open_box), ("route", route_box)]:
    w, h = b[2] - b[0], b[3] - b[1]
    sc = min(840 / w, 1250 / h)
    print(f"{nm:6s} {w:6.1f} x {h:6.1f} units ({w*KM_PER_UNIT:4.1f} x {h*KM_PER_UNIT:4.1f} km)"
          f"  {KM_PER_UNIT*1000/sc:5.1f} m/px  fills {w*sc:4.0f} x {h*sc:4.0f} px")
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
