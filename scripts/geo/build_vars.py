"""Builds src/VarsTour/geoData.ts: the French base map, the Route des Grandes
Alpes passes, and the D902 over the Col de Vars.

Same pipeline as build_geo.py/build_route.py for Switzerland - equirectangular
projection with a cos(latitude) correction so the map is not stretched - just
pointed at France instead. Regenerate with:  python3 scripts/geo/build_vars.py
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "VarsTour", "geoData.ts")

MAP_WIDTH = 2000.0
LAT0 = 46.5  # France's mid-latitude: where the projection is exact
K = math.cos(math.radians(LAT0))


# --- projection -------------------------------------------------------------

def rings(geometry):
    """Yields every linear ring of a Polygon/MultiPolygon as a list of (lon, lat)."""
    t, coords = geometry["type"], geometry["coordinates"]
    polys = [coords] if t == "Polygon" else coords
    for poly in polys:
        for ring in poly:
            yield [(pt[0], pt[1]) for pt in ring]


def load(path):
    with open(os.path.join(HERE, path)) as f:
        return json.load(f)


france = load("france_departements.geojson")

# The map's coordinate system is anchored on mainland France + Corsica; the
# neighbours are drawn into the same frame and may fall outside it.
lons, lats = [], []
for feat in france["features"]:
    for ring in rings(feat["geometry"]):
        for lon, lat in ring:
            lons.append(lon); lats.append(lat)

LON0, LON1 = min(lons), max(lons)
LAT0_B, LAT1_B = min(lats), max(lats)
SCALE = MAP_WIDTH / ((LON1 - LON0) * K)
MAP_HEIGHT = (LAT1_B - LAT0_B) * SCALE


def project(lon, lat):
    return ((lon - LON0) * K * SCALE, (LAT1_B - lat) * SCALE)


# --- path emission ----------------------------------------------------------

def ring_to_path(ring, min_step):
    """Projects a ring, dropping points closer than `min_step` map units to the
    previous one. The source data is already generalised; this trims what is
    left so the generated module stays small enough to bundle comfortably."""
    out = []
    for lon, lat in ring:
        p = project(lon, lat)
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= min_step:
            out.append(p)
    if len(out) < 3:
        return None
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in out) + "Z"


def feature_path(feat, min_step):
    parts = [p for p in (ring_to_path(r, min_step) for r in rings(feat["geometry"])) if p]
    return "".join(parts) if parts else None


def shapes(geojson, name_key, min_step, keep=None):
    out = []
    for feat in geojson["features"]:
        name = feat["properties"].get(name_key) or ""
        if keep and not keep(feat):
            continue
        d = feature_path(feat, min_step)
        if d:
            out.append((name, d))
    return out


departments = shapes(france, "nom", min_step=0.4)

# Italy and Switzerland exist only so the Alpine close-ups do not open onto
# empty paper east of the border; they are drawn flat and unlabelled, and can
# be generalised much harder than France itself.
neighbours = []
for path, key in [("italy_regions.geojson", "reg_name"),
                  ("switzerland_cantons.geojson", "name")]:
    g = load(path)
    k = key if key in (g["features"][0]["properties"]) else \
        next(iter(g["features"][0]["properties"]))
    neighbours += shapes(g, k, min_step=1.6)

# The last stage pushes in ~25x, far past any detail a department outline
# carries: without a finer layer the frame becomes two flat fields of colour.
# The communes the road actually crosses keep the patchwork going all the way
# down to the pass.
communes = []
for path in ["communes-05-hautes-alpes.geojson",
             "communes-04-alpes-de-haute-provence.geojson"]:
    communes += shapes(load(path), "nom", min_step=0.25)

print("departments", len(departments), "neighbours", len(neighbours),
      "communes", len(communes))


# --- places -----------------------------------------------------------------

# The Route des Grandes Alpes' headline passes, north to south. Coordinates
# and heights from each pass's Wikipedia entry.
PASSES = [
    ("iseran",   "COL DE L'ISERAN",  7.03083, 45.41694, 2764),
    ("galibier", "COL DU GALIBIER",  6.40800, 45.06400, 2642),
    ("izoard",   "COL D'IZOARD",     6.73500, 44.81972, 2360),
    ("vars",     "COL DE VARS",      6.70275, 44.53890, 2108),
    ("cayolle",  "COL DE LA CAYOLLE",6.74389, 44.25889, 2326),
]
# Turini, the route's last pass, is left off on purpose: it sits so far south
# that including it stretches this frame into a thin ribbon and shrinks the
# five passes that lead to the Col de Vars.

# The three places the drawn road actually names.
PLACES = [
    ("guillestre", "GUILLESTRE",           6.64940, 44.65970, 1000),
    ("vars",       "COL DE VARS",          6.70275, 44.53890, 2108),
    ("saintpaul",  "SAINT-PAUL-SUR-UBAYE", 6.75220, 44.51580, 1470),
]


def wp_literal(rows):
    out = []
    for wid, name, lon, lat, elev in rows:
        x, y = project(lon, lat)
        out.append(
            f'  {{ id: "{wid}", name: "{name}", subtitle: null, '
            f'x: {x:.2f}, y: {y:.2f}, elevation: {elev} }},'
        )
    return out


# --- the D902 over the Col de Vars ------------------------------------------

def zigzag(a, b, t0, t1, n, amp, taper=0.35):
    """Procedural hairpins: n alternating kinks across the segment a->b,
    tapering off towards the top so the switchbacks tighten with the road."""
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


# Anchors along the real road, north to south: out of Guillestre, up the
# Chagne through the two Vars villages, over the pass, then down the Ubaye
# side. Hairpins are inserted between anchors rather than replacing them, so
# the road still passes through every place it is supposed to.
P = lambda lon, lat: project(lon, lat)
ANCHORS = [
    ("guillestre", 6.64940, 44.65970),
    (None,         6.65400, 44.64800),
    ("lacets",     6.66200, 44.63000),   # lacets de Peyre-Haute
    (None,         6.67100, 44.60800),
    (None,         6.68000, 44.59000),
    ("ste_marie",  6.68670, 44.57570),   # Sainte-Marie-de-Vars
    ("les_claux",  6.69060, 44.55560),   # Vars les Claux
    (None,         6.69600, 44.54800),
    ("col",        6.70275, 44.53890),
    (None,         6.70900, 44.53100),   # lacets de Sainte-Anne
    (None,         6.71800, 44.52500),
    (None,         6.73300, 44.51950),
    ("saintpaul",  6.75220, 44.51580),
]

pts = {name: P(lon, lat) for name, lon, lat in ANCHORS if name}
line = [P(lon, lat) for _, lon, lat in ANCHORS]

# Switchback amplitudes are in map units; ~0.35 is roughly the 400 m swing a
# real hairpin makes here, which is what the deepest frame actually shows.
def insert_hairpins(line, i, j, n, amp):
    return line[:i + 1] + zigzag(line[i], line[j], 0.15, 0.85, n, amp) + line[j:]

road = list(line)
road = insert_hairpins(road, 8, 10, 7, 0.30)   # Sainte-Anne, south side
road = insert_hairpins(road, 6, 8, 5, 0.18)    # last ramp to the pass
road = insert_hairpins(road, 1, 3, 7, 0.34)    # above Guillestre

col = pts["col"]
guillestre = pts["guillestre"]
saintpaul = pts["saintpaul"]


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
col_fraction = path_length(road[:road.index(col) + 1]) / path_length(road)
print("road points", len(road), "col at fraction", round(col_fraction, 3))


def bbox(points, pad):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


road_box = bbox(road, 10)
# The pass stage frames every Route des Grandes Alpes pin, with room around
# them for the names, which are wider than the pins themselves.
alps_box = bbox([P(lon, lat) for _, _, lon, lat, _ in PASSES], 30)


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit -------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_vars.py - do not hand-edit.")
out.append("// Sources: gregoiredavid/france-geojson (departements, simplified),")
out.append("// openpolis/geojson-italy (regions), click_that_hood (Swiss cantons).")
out.append("// Equirectangular projection, longitude scaled by cos(46.5 deg).")
out.append('import { BBox, RegionShape, RouteSegment, Waypoint } from "../shared/types";')
out.append("")
out.append(f"export const MAP_WIDTH = {MAP_WIDTH:.2f};")
out.append(f"export const MAP_HEIGHT = {MAP_HEIGHT:.2f};")
out.append("")
out.append("export const departments: RegionShape[] = [")
for name, d in departments:
    out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
out.append("];")
out.append("")
out.append("// Hautes-Alpes and Alpes-de-Haute-Provence at commune level: the")
out.append("// patchwork the final push-in needs, faded in as the camera arrives.")
out.append("export const communes: RegionShape[] = [")
for name, d in communes:
    out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
out.append("];")
out.append("")
out.append("// Drawn flat behind France so the Alpine frames have a far side.")
out.append("export const neighbours: RegionShape[] = [")
for name, d in neighbours:
    out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
out.append("];")
out.append("")
out.append("export const passes: Waypoint[] = [")
out += wp_literal([(i, n, lo, la, e) for i, n, lo, la, e in PASSES])
out.append("];")
out.append("")
out.append("export const places: Waypoint[] = [")
out += wp_literal([(i, n, lo, la, e) for i, n, lo, la, e in PLACES])
out.append("];")
out.append("")
out.append("export const varsRoad: RouteSegment = {")
out.append('  id: "d902",')
out.append(f'  d: "{road_d}",')
out.append("  points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in road) + "],")
out.append("};")
out.append("")
out.append("// How far along the road the pass itself sits, by arc length.")
out.append(f"export const COL_FRACTION = {col_fraction:.3f};")
out.append("")
out.append(bbox_literal("FRANCE_BBOX", (0, 0, MAP_WIDTH, MAP_HEIGHT)))
out.append(bbox_literal("ALPS_BBOX", alps_box))
out.append(bbox_literal("VARS_BBOX", road_box))
out.append("")

os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(out))

print("map", round(MAP_WIDTH), "x", round(MAP_HEIGHT, 1))
print("alps bbox", [round(v, 1) for v in alps_box])
print("vars bbox", [round(v, 1) for v in road_box])
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
