"""Builds src/BralloTour/geoData.ts: two real roads from the Passo del Giovà to
Brallo di Pregola.

The easy one, 19.2 km by Google: north from the Giovà on the SP48 to Pian del
Poggio, on through Casale Staffora and Pianostano, then the SP131 north and
east into Brallo. The hard one, 13.1 km: east from the Giovà on the SP88 along
the Lombardia / Emilia-Romagna boundary, north up the east flank of the Zerba
wedge past the Cima Colletta, and through the hairpins into Brallo. The film
draws the easy one, crosses it out, then draws the hard one.

Both come from Google Maps route screenshots, turned into lon/lat tracks by
screenshot_track.py (tracks/facile.json, tracks/crinale.json). Each screenshot
is georeferenced on its own, against the official region boundaries, so the
two are an independent check on each other: they must agree on where the
Giovà and the arrival are. They do to within ~150 m, and that remaining gap is
split evenly between them here (see reconcile) so both roads leave from one
point and arrive at one point.

Regenerate with:  python3 scripts/geo/build_brallo.py
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "BralloTour", "geoData.ts")
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

# Same projection as build_oltrepo.py, anchored on the same four regions, so a
# map unit means the same thing in every Oltrepò film.
HOME_REGIONS = {"Lombardia", "Piemonte", "Emilia-Romagna", "Liguria"}

lons, lats = [], []
for feat in regions["features"]:
    if feat["properties"]["reg_name"] not in HOME_REGIONS:
        continue
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
WINDOW = (9.10, 44.60, 9.40, 44.82)
comuni = shapes(municipalities, "name", 0.05, window=WINDOW)
print("home", len(home), "beyond", len(beyond), "comuni", len(comuni))


# --- the two roads -----------------------------------------------------------

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


facile_t = read_track("facile")
crinale_t = read_track("crinale")
facile_ll = [tuple(p) for p in facile_t["lonlat"]]
crinale_ll = [tuple(p) for p in crinale_t["lonlat"]]

# The two screenshots were georeferenced independently, so where they agree is
# a measure of both. Report it, refuse to go on if it is gross (a bad fit, not
# noise), and otherwise meet in the middle.
AGREE_M = 250
gap_start = metres(facile_ll[0], crinale_ll[0])
gap_end = metres(facile_ll[-1], crinale_ll[-1])
print(f"the two screenshots agree on the Giovà to {gap_start:.0f} m "
      f"and on the arrival to {gap_end:.0f} m")
if max(gap_start, gap_end) > AGREE_M:
    sys.exit(f"screenshots disagree by more than {AGREE_M} m - check the georeference")

START = tuple((a + b) / 2 for a, b in zip(facile_ll[0], crinale_ll[0]))
END = tuple((a + b) / 2 for a, b in zip(facile_ll[-1], crinale_ll[-1]))


def reconcile(track):
    """Move a track's ends onto the shared START and END, spreading the shift
    along its length by arc fraction, so there is no kink - at most half the
    gap above, ~75 m, fading to nothing towards the middle of the road."""
    ds = [0.0]
    for p, q in zip(track, track[1:]):
        ds.append(ds[-1] + metres(p, q))
    total = ds[-1]
    s0 = (START[0] - track[0][0], START[1] - track[0][1])
    s1 = (END[0] - track[-1][0], END[1] - track[-1][1])
    out = []
    for (lon, lat), d in zip(track, ds):
        t = d / total
        out.append((lon + s0[0] * (1 - t) + s1[0] * t, lat + s0[1] * (1 - t) + s1[1] * t))
    return out


facile_ll = reconcile(facile_ll)
crinale_ll = reconcile(crinale_ll)
km = {"facile": sum(metres(p, q) for p, q in zip(facile_ll, facile_ll[1:])) / 1000,
      "crinale": sum(metres(p, q) for p, q in zip(crinale_ll, crinale_ll[1:])) / 1000}
print("drawn length", {k: round(v, 1) for k, v in km.items()},
      "km (Google: facile 19.2, crinale 13.1 - the difference is the tightest "
      "switchbacks, which merge in the screenshots)")


# --- which comuni each road crosses -----------------------------------------
# Reported, not enforced. An earlier version of this script required the easy
# road to stay out of Brallo di Pregola until the pass; the real road goes up
# through Pianostano, at the tip of the Zerba wedge, and the assumption behind
# that check was simply wrong.

def inside(pt, ring):
    x, y = pt
    n = len(ring); hit = False; j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            hit = not hit
        j = i
    return hit


near = [f for f in municipalities["features"]
        if f["properties"].get("prov_acr") in ("PV", "PC", "AL")]


def comune_of(p):
    for f in near:
        if any(inside(p, r) for r in rings(f["geometry"])):
            return f["properties"]["name"]
    return "?"


for name, track in (("facile", facile_ll), ("crinale", crinale_ll)):
    seq = []
    for p in track:
        c = comune_of(p)
        if not seq or seq[-1] != c:
            seq.append(c)
    print(f"{name} crosses: " + " > ".join(seq))


# --- places ------------------------------------------------------------------

PLACES = [
    ("giova",    "PASSO DEL GIOVÀ",   START,                                    1310),
    ("poggio",   "PIAN DEL POGGIO",   tuple(facile_t["stops"]["poggio"]),       1150),
    ("colletta", "CIMA COLLETTA",     tuple(crinale_t["pois"]["colletta"]),     1494),
    ("brallo",   "BRALLO DI PREGOLA", END,                                      950),
]
for pid, _, ll, _ in PLACES:
    print(f"  {pid:9s} {ll[0]:.5f}, {ll[1]:.5f}  ({comune_of(ll)})")


def wp_literal(rows):
    out = []
    for i, n, (lo, la), e in rows:
        x, y = project(lo, la)
        out.append(f'  {{ id: "{i}", name: "{n}", subtitle: null, '
                   f"x: {x:.2f}, y: {y:.2f}, elevation: {e} }},")
    return out


# --- geometry for the film ---------------------------------------------------

facile = [project(*p) for p in facile_ll]
crinale = [project(*p) for p in crinale_ll]


def catmull_rom_to_bezier(points):
    pts_ = [points[0]] + points + [points[-1]]
    d = f"M{points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(pts_) - 2):
        p0, p1, p2, p3 = pts_[i - 1], pts_[i], pts_[i + 1], pts_[i + 2]
        d += (f"C{p1[0] + (p2[0]-p0[0])/6:.2f},{p1[1] + (p2[1]-p0[1])/6:.2f} "
              f"{p2[0] - (p3[0]-p1[0])/6:.2f},{p2[1] - (p3[1]-p1[1])/6:.2f} "
              f"{p2[0]:.2f},{p2[1]:.2f}")
    return d


def path_length(points):
    return sum(math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1])
               for i in range(1, len(points)))


def nearest_index(line, p):
    return min(range(len(line)),
               key=lambda i: math.hypot(line[i][0] - p[0], line[i][1] - p[1]))


legs = [("facile", facile, ["giova", "poggio", "brallo"]),
        ("crinale", crinale, ["giova", "colletta", "brallo"])]
place_xy = {pid: project(*ll) for pid, _, ll, _ in PLACES}

# Where each place falls along each road, by arc length. Cima Colletta is a
# summit beside the road, not on it, so it is cued off the nearest point of
# the road - when the drawn line passes it.
marks = {}
for lid, line, ids in legs:
    total = path_length(line)
    for pid in ids:
        i = nearest_index(line, place_xy[pid])
        marks.setdefault(lid, {})[pid] = path_length(line[: i + 1]) / total
print("marks", {lid: {k: round(v, 3) for k, v in m.items()} for lid, m in marks.items()})


# The X goes where the two roads are furthest apart, over the middle of the
# easy one (the ends are shared ground).
def dist_to_polyline(p, line):
    best = float("inf")
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy or 1e-12
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / seg2))
        best = min(best, math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy)))
    return best


n = len(facile)
x_i = max(range(int(n * 0.25), int(n * 0.85)), key=lambda i: dist_to_polyline(facile[i], crinale))
x_point = facile[x_i]
print(f"X at facile point {x_i} of {n}, "
      f"{dist_to_polyline(x_point, crinale) * KM_PER_UNIT * 1000:.0f} m from the other road")


# --- framing -----------------------------------------------------------------

def bbox(points, pad_x, pad_top, pad_bottom):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return (min(xs) - pad_x, min(ys) - pad_top, max(xs) + pad_x, max(ys) + pad_bottom)


route_box = bbox(facile + crinale + [place_xy["colletta"]], 5.0, 3.0, 4.0)
cx, cy = (route_box[0] + route_box[2]) / 2, (route_box[1] + route_box[3]) / 2
hw, hh = (route_box[2] - route_box[0]) / 2 * 1.35, (route_box[3] - route_box[1]) / 2 * 1.35
open_box = (cx - hw, cy - hh, cx + hw, cy + hh)


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit --------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_brallo.py - do not hand-edit.")
out.append("// Roads: Google Maps route screenshots via scripts/geo/screenshot_track.py.")
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
    ("comuni", comuni, "The comuni around the two roads."),
]:
    out.append(f"// {note}")
    out.append(f"export const {var}: RegionShape[] = [")
    for name, d in rows:
        out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
    out.append("];")
    out.append("")
out.append("export const places: Waypoint[] = [")
out += wp_literal(PLACES)
out.append("];")
out.append("")
out.append("// The easy road, crossed out; then the hard one.")
out.append("export const roads: RouteSegment[] = [")
for lid, line, _ in legs:
    out.append(
        f'  {{ id: "{lid}", d: "{catmull_rom_to_bezier(line)}", '
        + "points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in line) + "] },"
    )
out.append("];")
out.append("")
out.append("// How far along each road each place sits, by arc length.")
out.append("export const marks: Record<string, Record<string, number>> = {")
for lid, m in marks.items():
    inner = ", ".join(f"{k}: {v:.3f}" for k, v in m.items())
    out.append(f"  {lid}: {{ {inner} }},")
out.append("};")
out.append("")
out.append("// Where the X lands: the point of the easy road furthest from the other.")
out.append(f"export const X_POINT = {{ x: {x_point[0]:.2f}, y: {x_point[1]:.2f} }};")
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
          f"  scale {sc:6.2f} px/unit  fills {w*sc:4.0f} x {h*sc:4.0f} px")
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
