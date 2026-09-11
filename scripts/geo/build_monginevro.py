"""Builds src/MonginevroTour/geoData.ts: Italy and France side by side, the
Italy-France passes, and the SS24/N94 over the Colle del Monginevro.

Same pipeline as build_vars.py, with two differences: the base map is two
countries rather than one, both in pastel, and the national border itself is
extracted so the crossing can be staged.

Regenerate with:  python3 scripts/geo/build_monginevro.py
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "MonginevroTour", "geoData.ts")

MAP_WIDTH = 2000.0
LAT0 = 44.5  # the latitude band the road sits in: exact where it matters
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


france = load("france_departements.geojson")
italy = load("italy_provinces.geojson")

# The frame is anchored on France alone: the opening shot is France and
# nothing else, and Italy is drawn into the same projection behind it.
lons, lats = [], []
for src in (france,):
    for feat in src["features"]:
        for ring in rings(feat["geometry"]):
            for lon, lat in ring:
                lons.append(lon); lats.append(lat)

LON0, LON1 = min(lons), max(lons)
LATMIN, LATMAX = min(lats), max(lats)
SCALE = MAP_WIDTH / ((LON1 - LON0) * K)
MAP_HEIGHT = (LATMAX - LATMIN) * SCALE


def project(lon, lat):
    return ((lon - LON0) * K * SCALE, (LATMAX - lat) * SCALE)


P = lambda lon, lat: project(lon, lat)


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


def shapes(geojson, name_key, min_step, window=None):
    """window: (lon0, lat0, lon1, lat1) - keeps only features that touch it."""
    out = []
    for feat in geojson["features"]:
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


# France carries the patchwork; everything beyond it is drawn flat and grey,
# so the border reads as the line where the colour stops.
departments = shapes(france, "nom", 0.4)
beyond = shapes(italy, "prov_name", 0.4)
beyond += shapes(load("switzerland_cantons.geojson"), "name", 1.6)

# Communes, for the final push-in. Only the ones around the road: the whole of
# Italy at this resolution would be tens of megabytes.
WINDOW = (6.45, 44.72, 7.15, 45.20)
communes_it = shapes(load("limits_IT_municipalities.geojson"), "name", 0.12, WINDOW)
communes_fr = shapes(load("communes-05-hautes-alpes.geojson"), "nom", 0.12, WINDOW)

print("departments", len(departments), "beyond", len(beyond),
      "communes", len(communes_fr), "+", len(communes_it))


# --- places -----------------------------------------------------------------

# The great Italy-France passes, north to south. The Monginevro is deliberately
# absent: it belongs in the gap these leave, and the push-in fills it.
PASSES = [
    ("moncenisio", "COLLE DEL MONCENISIO", 6.90530, 45.25360, 2083),
    ("agnello",    "COLLE DELL'AGNELLO",   6.97963, 44.68394, 2744),
    ("maddalena",  "COLLE DELLA MADDALENA",6.88920, 44.41920, 1996),
]

PLACES = [
    ("cesana",   "CESANA TORINESE",       6.79250, 44.95250, 1354),
    ("claviere", "CLAVIERE",              6.75540, 44.93090, 1760),
    ("col",      "COLLE DEL MONGINEVRO",  6.72950, 44.93120, 1860),
    ("briancon", "BRIANÇON",         6.64000, 44.89940, 1326),
]


def wp_literal(rows):
    return [
        f'  {{ id: "{i}", name: "{n}", subtitle: null, '
        f"x: {project(lo, la)[0]:.2f}, y: {project(lo, la)[1]:.2f}, elevation: {e} }},"
        for i, n, lo, la, e in rows
    ]


# --- the SS24 / N94 ---------------------------------------------------------

def zigzag(a, b, t0, t1, n, amp, taper=0.35):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    pts = []
    for i in range(n):
        t = t0 + (t1 - t0) * i / (n - 1)
        side = 1 if i % 2 == 0 else -1
        a_amp = amp * (1 - taper * (i / (n - 1)))
        pts.append((ax + dx * t + px * side * a_amp,
                    ay + dy * t + py * side * a_amp))
    return pts


# East to west: up the Val di Susa from Cesana, through Claviere, over the
# border and the pass, then the long descent into Brianรงon.
ANCHORS = [
    ("cesana",   6.79250, 44.95250),
    (None,       6.78200, 44.94600),
    (None,       6.77000, 44.93700),
    ("claviere", 6.75540, 44.93090),
    ("border",   6.74450, 44.93010),
    ("col",      6.72950, 44.93120),
    (None,       6.72050, 44.93250),   # the village of Montgenèvre
    (None,       6.70600, 44.92700),
    (None,       6.68600, 44.91800),
    (None,       6.66300, 44.90700),
    ("briancon", 6.64000, 44.89940),
]

pts = {name: P(lon, lat) for name, lon, lat in ANCHORS if name}
line = [P(lon, lat) for _, lon, lat in ANCHORS]


def insert_hairpins(line, i, j, n, amp):
    return line[:i + 1] + zigzag(line[i], line[j], 0.15, 0.85, n, amp) + line[j:]


road = list(line)
road = insert_hairpins(road, 7, 9, 7, 0.20)   # the bends above Briançon
road = insert_hairpins(road, 1, 3, 5, 0.11)   # the climb out of Cesana

col = pts["col"]
border_pt = pts["border"]


def catmull_rom_to_bezier(points):
    pts = [points[0]] + points + [points[-1]]
    d = f"M{points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        d += (f"C{p1[0] + (p2[0]-p0[0])/6:.2f},{p1[1] + (p2[1]-p0[1])/6:.2f} "
              f"{p2[0] - (p3[0]-p1[0])/6:.2f},{p2[1] - (p3[1]-p1[1])/6:.2f} "
              f"{p2[0]:.2f},{p2[1]:.2f}")
    return d


def path_length(points):
    return sum(math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1])
               for i in range(1, len(points)))


road_d = catmull_rom_to_bezier(road)
border_fraction = path_length(road[:road.index(border_pt) + 1]) / path_length(road)
col_fraction = path_length(road[:road.index(col) + 1]) / path_length(road)
print("road points", len(road),
      "border at", round(border_fraction, 3), "col at", round(col_fraction, 3))


# --- the national border ----------------------------------------------------
# Around the pass, the eastern edge of the Hautes-Alpes department IS the
# Italy-France border, so it can be lifted straight out of the map data
# instead of being drawn by hand.

def border_near(col_xy, radius):
    best = []
    for feat in france["features"]:
        if feat["properties"].get("nom") != "Hautes-Alpes":
            continue
        for ring in rings(feat["geometry"]):
            pts = ring_to_points(ring, 0.0)
            n = len(pts)
            inside = [i for i, p in enumerate(pts)
                      if math.hypot(p[0] - col_xy[0], p[1] - col_xy[1]) <= radius]
            if not inside:
                continue
            # The ring is closed, so walk it as a cycle to find the longest
            # unbroken run of points near the pass.
            run, runs = [], []
            prev = None
            for i in inside:
                if prev is not None and i != prev + 1:
                    runs.append(run); run = []
                run.append(i); prev = i
            runs.append(run)
            if inside[0] == 0 and inside[-1] == n - 1 and len(runs) > 1:
                runs[0] = runs[-1] + runs[0]; runs.pop()
            longest = max(runs, key=len)
            if len(longest) > len(best):
                best = [pts[i % n] for i in longest]
    return best


# The whole frontier, not just the stretch by the pass: it is what the film
# opens on. France and Italy come from different surveys, so the shared
# boundary is found by proximity rather than by matching coordinates - every
# point of a French department outline that has an Italian province outline
# within a few km of it.
def full_frontier(eps=0.05, cell=0.05):
    index = {}
    for feat in italy["features"]:
        for ring in rings(feat["geometry"]):
            for lon, lat in ring:
                index.setdefault((int(lon / cell), int(lat / cell)), []).append((lon, lat))

    def near(lon, lat):
        cx, cy = int(lon / cell), int(lat / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for a, b in index.get((cx + dx, cy + dy), ()):
                    if abs(a - lon) < eps and abs(b - lat) < eps:
                        return True
        return False

    runs = []
    for feat in france["features"]:
        for ring in rings(feat["geometry"]):
            if max(p[0] for p in ring) < 5.5:
                continue  # nowhere near Italy
            run = []
            for lon, lat in ring:
                if near(lon, lat):
                    run.append(project(lon, lat))
                else:
                    if len(run) >= 3:
                        runs.append(run)
                    run = []
            if len(run) >= 3:
                runs.append(run)
    return runs


frontier_runs = full_frontier()
frontier_d = "".join(
    "M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in r) for r in frontier_runs
)
frontier_pts = [p for r in frontier_runs for p in r]
print("frontier runs", len(frontier_runs), "points", len(frontier_pts))


def bbox(points, pad, pad_top=None, pad_bottom=None):
    pad_top = pad if pad_top is None else pad_top
    pad_bottom = pad_top if pad_bottom is None else pad_bottom
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return (min(xs) - pad, min(ys) - pad_top, max(xs) + pad, max(ys) + pad_bottom)


# Cesana to Briancon runs east-west, across the short axis of a 9:16 frame.
# Padding the box out vertically stops the road being a thin streak with dead
# space above and below, and leaves that space to the names instead.
# Every name on this leg sits above the road, so the box carries more
# headroom than floor: that visual weight is what gets centred, not the
# line on its own.
route_box = bbox(road, 3.0, 13.5, 8.3)
# The middle stage reads as a region rather than three dots, so it is
# framed wider than the passes strictly need.
passes_box = bbox([P(lon, lat) for _, _, lon, lat, _ in PASSES], 34)


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit -------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_monginevro.py - do not hand-edit.")
out.append("// Sources: gregoiredavid/france-geojson (departements, communes 05),")
out.append("// openpolis/geojson-italy (province, comuni), click_that_hood (cantoni).")
out.append("// Equirectangular projection, longitude scaled by cos(44.5 deg).")
out.append('import { BBox, RegionShape, RouteSegment, Waypoint } from "../shared/types";')
out.append("")
out.append(f"export const MAP_WIDTH = {MAP_WIDTH:.2f};")
out.append(f"export const MAP_HEIGHT = {MAP_HEIGHT:.2f};")
out.append("")
for var, rows, note in [
    ("departments", departments, "France: one pastel tile each, revealed as the camera descends."),
    ("beyond", beyond, "Italy and Switzerland: grey, and only in frame once the camera has dropped."),
    ("communesFr", communes_fr, "The French communes around the road."),
    ("communesIt", communes_it, "The Italian ones, which take the grey."),
]:
    out.append(f"// {note}")
    out.append(f"export const {var}: RegionShape[] = [")
    for name, d in rows:
        out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
    out.append("];")
    out.append("")
out.append("export const passes: Waypoint[] = [")
out += wp_literal(PASSES)
out.append("];")
out.append("")
out.append("export const places: Waypoint[] = [")
out += wp_literal(PLACES)
out.append("];")
out.append("")
# Two legs rather than one line, split at the frontier, so the crossing can
# be given a beat of its own instead of flashing past mid-draw.
bi = road.index(border_pt)
legs = [("italia", road[: bi + 1]), ("francia", road[bi:])]
out.append("export const roadLegs: RouteSegment[] = [")
for lid, pts_ in legs:
    out.append(
        f'  {{ id: "{lid}", d: "{catmull_rom_to_bezier(pts_)}", '
        + "points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in pts_) + "] },"
    )
out.append("];")
print("leg lengths", [round(path_length(p_), 1) for _, p_ in legs])
out.append("")
out.append("// How far along the road the border and the pass sit, by arc length.")
out.append(f"export const BORDER_FRACTION = {border_fraction:.3f};")
out.append(f"export const COL_FRACTION = {col_fraction:.3f};")
out.append("")
out.append("// The whole Italy-France frontier, Mont Blanc down to the sea.")
out.append(f'export const FRONTIER_D = "{frontier_d}";')
out.append(f"export const BORDER_POINT = {{ x: {border_pt[0]:.2f}, y: {border_pt[1]:.2f} }};")
out.append("")
# The opening frames the frontier itself rather than a country.
out.append(bbox_literal("WIDE_BBOX", bbox(frontier_pts, 114, 70, 70)))
out.append(bbox_literal("REGION_BBOX", passes_box))
out.append(bbox_literal("ROUTE_BBOX", route_box))
out.append("")

os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(out))

print("map", round(MAP_WIDTH), "x", round(MAP_HEIGHT, 1))
print("passes bbox", [round(v, 1) for v in passes_box])
print("route bbox", [round(v, 1) for v in route_box])
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
