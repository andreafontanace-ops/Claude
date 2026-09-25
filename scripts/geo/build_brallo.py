"""Builds src/BralloTour/geoData.ts: two roads from the Passo del Giovà to
Brallo di Pregola, and the ridge between them.

The easy one drops back to Pian del Poggio and contours north-east along the
Staffora flank, heading down towards the Penice, before crossing to the Brallo.
The hard one is the SP88 over the Cima Colletta and along the crinale. The film
draws the easy one, crosses it out, then draws the ridge.

Same pipeline as build_oltrepo.py, and the same caveat: no routing service is
reachable from the render environment, so the roads are laid out over anchors.
What keeps that honest here is the watershed. The Santa Margherita / Brallo di
Pregola comune boundary IS the ridge:

  - the crinale road is that boundary, lifted straight out of the ISTAT data;
  - the easy road has to stay on the Staffora side of it until the pass, and the
    build fails if a single point of it - bends included - strays into Brallo
    di Pregola before then. Its anchors are checked the same way.

The easy road's bends are built, not traced (see add_bends). It passes several
villages on the way; they are deliberately not named in the film.

Regenerate with:  python3 scripts/geo/build_brallo.py
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "BralloTour", "geoData.ts")

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
# map unit means the same thing in both films.
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


P = lambda lon, lat: project(lon, lat)


def unproject(x, y):
    return (x / (K * SCALE) + LON0, LATMAX - y / SCALE)


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

# Only the comuni around the two roads: the whole film stays inside 12 km.
WINDOW = (9.10, 44.62, 9.40, 44.84)
comuni = shapes(municipalities, "name", 0.05, window=WINDOW)
print("home", len(home), "beyond", len(beyond), "comuni", len(comuni))


# --- the watershed ---------------------------------------------------------

def inside(pt, ring):
    x, y = pt
    n = len(ring)
    hit = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            hit = not hit
        j = i
    return hit


def comune_rings(name):
    for feat in municipalities["features"]:
        if feat["properties"].get("name") == name and feat["properties"].get("prov_acr") == "PV":
            return list(rings(feat["geometry"]))
    sys.exit(f"comune not found: {name}")


BRALLO_RINGS = comune_rings("Brallo di Pregola")


def in_brallo(lon, lat):
    return any(inside((lon, lat), r) for r in BRALLO_RINGS)


# --- places ----------------------------------------------------------------

PLACES = [
    ("giova",      "PASSO DEL GIOVÀ",   9.2347, 44.6983, 1310),
    ("poggio",     "PIAN DEL POGGIO",   9.2245, 44.7070, 1150),
    ("colletta",   "CIMA COLLETTA",     9.2351, 44.7164, 1494),
    ("brallopass", "PASSO DEL BRALLO",  9.2636, 44.7540, 951),
    ("brallo",     "BRALLO DI PREGOLA", 9.2745, 44.7515, 950),
]


def wp_literal(rows):
    return [
        f'  {{ id: "{i}", name: "{n}", subtitle: null, '
        f"x: {project(lo, la)[0]:.2f}, y: {project(lo, la)[1]:.2f}, elevation: {e} }},"
        for i, n, lo, la, e in rows
    ]


# --- the two roads ---------------------------------------------------------

# The easy one. Back down from the Giovà to Pian del Poggio, then north-east
# along the Staffora flank, a few hundred metres below the ridge the whole way,
# and over to the Brallo at the pass. Every anchor here has been checked
# against the comune polygons: all in Santa Margherita di Staffora until the
# pass, which sits on the boundary vertex itself.
FACILE = [
    ("giova",      9.2347, 44.6983),
    (None,         9.2290, 44.7020),
    ("poggio",     9.2245, 44.7070),
    (None,         9.2270, 44.7160),
    (None,         9.2285, 44.7260),
    (None,         9.2310, 44.7370),
    (None,         9.2400, 44.7470),
    (None,         9.2500, 44.7515),
    (None,         9.2580, 44.7562),
    ("brallopass", 9.2636, 44.7540),
    (None,         9.2690, 44.7534),
    ("brallo",     9.2745, 44.7515),
]

# The hard one: the SP88 over the Cima Colletta and along the crinale. The
# Brallo / Santa Margherita / Zerba comune boundaries - in the Apennines the
# comune line is the watershed, and the watershed is what this road rides.
# The line between these vertices is ISTAT's simplification, not the road; see
# BENDS for what is done about that.
CRINALE = [
    ("giova",      9.2347, 44.6983),
    (None,         9.2323, 44.7033),
    (None,         9.2330, 44.7076),
    (None,         9.2359, 44.7128),
    ("colletta",   9.2351, 44.7164),
    (None,         9.2330, 44.7220),
    (None,         9.2335, 44.7254),
    (None,         9.2356, 44.7289),
    (None,         9.2368, 44.7340),
    (None,         9.2375, 44.7401),
    (None,         9.2454, 44.7412),
    (None,         9.2545, 44.7456),
    (None,         9.2592, 44.7482),
    ("brallopass", 9.2636, 44.7540),
    (None,         9.2690, 44.7534),
    ("brallo",     9.2745, 44.7515),
]

# Every anchor up to the pass must be on the Staffora side. Past the pass the
# road is in Brallo di Pregola by definition, so the check stops there.
for name, lon, lat in FACILE:
    if name == "brallopass":
        break
    if in_brallo(lon, lat):
        sys.exit(f"easy-road anchor on the wrong side of the ridge: {name} {lon},{lat}")


# --- bends -------------------------------------------------------------------
# Built, not traced: offset(t) = amp * (sin(2 pi c t) + w2 sin(4 pi c t) +
# w3 sin(6 pi c t)) across the local normal, `c` a whole number, so the offset
# is zero at both ends of every span and each named place stays exactly on its
# own coordinate. Same generator as the Val Staffora film.
#
# The easy road is the one "ricca di curve": six full cycles on the long
# traverse from Pian del Poggio to the pass. The ridge road gets bends too, but
# a third of the size: the ISTAT boundary it comes from is a simplified
# polyline, straight between vertices, and a crest road is not a ruler - but
# the contrast between the two roads is the film, so the ridge stays the
# calmer line. The last kilometre into Brallo is shared by both, so it gets no
# bends at all - two lines on one road would split visibly.

# per road: span end -> (cycles, amplitude km, w2, w3)
BENDS = {
    "facile": {
        "poggio": (2, 0.10, 0.30, -0.15),
        "brallopass": (6, 0.15, -0.32, 0.18),
        "brallo": (0, 0.0, 0.0, 0.0),
    },
    "crinale": {
        "colletta": (2, 0.04, 0.25, 0.0),
        "brallopass": (4, 0.06, -0.28, 0.14),
        "brallo": (0, 0.0, 0.0, 0.0),
    },
}


def spline_resample(points, step):
    """Sample a centripetal Catmull-Rom spline through `points` every ~`step`.

    Straight segments between anchors leave a hard corner at every anchor,
    and on the ridge - where the anchors are ISTAT boundary vertices - those
    corners are the most visible thing in the frame. The spline passes through
    every anchor exactly, so named places stay put; it only rounds the turns.
    Centripetal (alpha 0.5) rather than uniform, because uniform overshoots
    into loops where anchors are unevenly spaced, as these are."""
    ext = [points[0]] + list(points) + [points[-1]]

    def tj(ti, a, b):
        return ti + max(math.hypot(b[0] - a[0], b[1] - a[1]), 1e-9) ** 0.5

    out = [points[0]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        n = max(1, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for k in range(1, n + 1):
            t = t1 + (t2 - t1) * k / n
            def lerp(a, b, ta, tb):
                if tb - ta < 1e-12:
                    return a
                w = (t - ta) / (tb - ta)
                return (a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w)
            a1 = lerp(p0, p1, t0, t1); a2 = lerp(p1, p2, t1, t2); a3 = lerp(p2, p3, t2, t3)
            b1 = lerp(a1, a2, t0, t2); b2 = lerp(a2, a3, t1, t3)
            out.append(lerp(b1, b2, t1, t2))
    return out


def nearest_index(line, p):
    return min(range(len(line)),
               key=lambda i: math.hypot(line[i][0] - p[0], line[i][1] - p[1]))


def add_bends(points, named, bends, step=0.25):
    dense = spline_resample(points, step)
    marks_i = [(name, nearest_index(dense, points[i])) for name, i in named]
    out = list(dense)
    for (_, ia), (name_b, ib) in zip(marks_i, marks_i[1:]):
        cycles, amp_km, w2, w3 = bends.get(name_b, (0, 0.0, 0.0, 0.0))
        if not cycles or ib - ia < 4:
            continue
        amp = amp_km / KM_PER_UNIT
        for i in range(ia + 1, ib):
            t = (i - ia) / (ib - ia)
            ax, ay = dense[max(ia, i - 1)]
            bx, by = dense[min(ib, i + 1)]
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / length, dx / length
            k = amp * (
                math.sin(2 * math.pi * cycles * t)
                + w2 * math.sin(2 * math.pi * 2 * cycles * t)
                + w3 * math.sin(2 * math.pi * 3 * cycles * t)
            )
            out[i] = (dense[i][0] + nx * k, dense[i][1] + ny * k)
    return out


def build_leg(rows, bends):
    line = [P(lon, lat) for _, lon, lat in rows]
    named = [(name, i) for i, (name, _, _) in enumerate(rows) if name]
    return add_bends(line, named, bends)


pts = {name: P(lon, lat) for rows in (FACILE, CRINALE) for name, lon, lat in rows if name}
facile = build_leg(FACILE, BENDS["facile"])
crinale = build_leg(CRINALE, BENDS["crinale"])

# Named places must land exactly on both roads - the spline and the bends are
# both built to guarantee it, and this makes sure they did.
for road, line in (("facile", facile), ("crinale", crinale)):
    for name, lon, lat in (FACILE if road == "facile" else CRINALE):
        if not name:
            continue
        p = P(lon, lat)
        gap = math.hypot(*(a - b for a, b in zip(line[nearest_index(line, p)], p)))
        if gap > 1e-6:
            sys.exit(f"{name} is {gap:.4f} units off the {road} road")

# The guarantee: bends and all, the easy road never crosses the ridge before
# the pass. Checked on every drawn point, not just the anchors.
pass_i = nearest_index(facile, pts["brallopass"])
strays = [unproject(*p) for p in facile[:pass_i - 2] if in_brallo(*unproject(*p))]
if strays:
    sys.exit(f"{len(strays)} easy-road points cross the ridge early, e.g. {strays[0]}")
print("easy road stays on the Staffora side of the ridge up to the pass:",
      pass_i, "points checked")


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


legs = [("facile", facile, FACILE), ("crinale", crinale, CRINALE)]
lengths = {lid: path_length(line) for lid, line, _ in legs}
print("leg lengths (units)", {k: round(v, 1) for k, v in lengths.items()},
      "km", {k: round(v * KM_PER_UNIT, 1) for k, v in lengths.items()})

# Where each named place falls along each leg, by arc length. Keyed by leg,
# because the Giovà, the pass and Brallo are on both roads.
marks = {}
for lid, line, rows in legs:
    for name in (n for n, _, _ in rows if n):
        i = nearest_index(line, pts[name])
        marks.setdefault(lid, {})[name] = path_length(line[: i + 1]) / lengths[lid]
print("marks", {lid: {k: round(v, 3) for k, v in m.items()} for lid, m in marks.items()})


# --- where the X goes --------------------------------------------------------
# The two roads run close for most of their length - the easy one contours a
# few hundred metres below the ridge - so an X dropped at the easy road's
# midpoint would half-land on the ridge road too. It goes where they are
# furthest apart instead, searched over the middle of the easy road (the ends
# are shared ground: the Giovà at one, the Brallo at the other).

def dist_to_polyline(p, line):
    best = float("inf")
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy or 1e-12
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / seg2))
        best = min(best, math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy)))
    return best


n = len(facile)
window_i = range(int(n * 0.25), int(n * 0.85))
x_i = max(window_i, key=lambda i: dist_to_polyline(facile[i], crinale))
x_point = facile[x_i]
print("X at facile index", x_i, "of", n,
      f"- {dist_to_polyline(x_point, crinale) * KM_PER_UNIT * 1000:.0f} m from the ridge road")


# --- framing -----------------------------------------------------------------

def bbox(points, pad_x, pad_top, pad_bottom):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return (min(xs) - pad_x, min(ys) - pad_top, max(xs) + pad_x, max(ys) + pad_bottom)


# 4 km across and 6.6 km tall. The side padding is where the names go.
route_box = bbox(facile + crinale, 7.0, 3.0, 4.0)

# The opening framing: the same box, 35% wider about its centre. The camera
# drifts from one to the other over the whole film - a slow push rather than a
# drop, since there is nothing to establish that the first frame does not.
cx, cy = (route_box[0] + route_box[2]) / 2, (route_box[1] + route_box[3]) / 2
hw, hh = (route_box[2] - route_box[0]) / 2 * 1.35, (route_box[3] - route_box[1]) / 2 * 1.35
open_box = (cx - hw, cy - hh, cx + hw, cy + hh)


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit --------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_brallo.py - do not hand-edit.")
out.append("// Sources: openpolis/geojson-italy (regioni, comuni).")
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
out.append("// The easy road, crossed out; then the ridge.")
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
out.append("// Where the X lands: the point of the easy road furthest from the ridge.")
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
