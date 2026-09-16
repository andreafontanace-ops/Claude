"""Builds src/OltrepoTour/geoData.ts: the Oltrepo Pavese and the road from
Varzi up the Val Staffora to the Passo del Giovà.

Same pipeline as build_monginevro.py. One thing is specific to this route:
there is no routing service reachable from the render environment, so the
road is laid out over anchors rather than traced. The anchors are checked
against the ISTAT municipal boundaries rather than eyeballed - every place
on the road falls inside the comune it belongs to, the valley floor follows
the medial line of the Santa Margherita di Staffora comune (which is the
upper Staffora basin), and the Passo del Giovà and the Monte Chiappo sit on
exact boundary vertices, because in this part of the Apennines the comune
line is the watershed.

Regenerate with:  python3 scripts/geo/build_oltrepo.py
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "OltrepoTour", "geoData.ts")

MAP_WIDTH = 2000.0
LAT0 = 44.75  # the latitude band the road sits in: exact where it matters
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
provinces = load("italy_provinces.geojson")
municipalities = load("limits_IT_municipalities.geojson")

# The four regions that meet over this ridge. The frame is anchored on them:
# they are what the projection is scaled to, even though the film never pulls
# back far enough to hold all four at once.
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


def shapes(geojson, name_key, min_step, keep=None, window=None):
    """keep: predicate on properties. window: (lon0, lat0, lon1, lat1)."""
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


# Italy under everything, in greys. At the widest the film ever goes the
# regions are flat fields of colour rather than shapes you could name, so the
# colour is spent on the four provinces instead and the regions only carry
# the coastline that says where this is.
italy = shapes(regions, "reg_name", 0.6)

# The Quattro Province: Pavia, Alessandria, Piacenza and Genova, whose
# boundaries all meet on the Monte Chiappo at the head of this valley. The
# name is what the whole area between them is called.
QUATTRO = {"Pavia", "Alessandria", "Piacenza", "Genova"}
quattro = shapes(provinces, "prov_name", 0.25,
                 keep=lambda p: p["prov_name"] in QUATTRO)

# Comuni, for the final push-in: only the ones around the road.
WINDOW = (8.93, 44.47, 9.62, 45.08)
comuni = shapes(municipalities, "name", 0.06, window=WINDOW)

print("italy", len(italy), "province", len(quattro), "comuni", len(comuni))


# --- places -----------------------------------------------------------------

# The four provinces, labelled where their names fit rather than at their
# centroids: Genova runs along the coast, Pavia up towards the Po.
PROVINCE_LABELS = [
    ("pavia",       "PAVIA",       9.0600, 45.0200, 0),
    ("alessandria", "ALESSANDRIA", 8.7400, 44.8200, 0),
    ("piacenza",    "PIACENZA",    9.7000, 44.9000, 0),
    ("genova",      "GENOVA",      9.0000, 44.4400, 0),
]

# The route, in order. Elevations are the published ones for each place.
# Not on the road, but the reason the road is where it is: the Pavia,
# Alessandria and Piacenza boundaries meet on this summit, at the head of the
# Val Staffora. Genova, the fourth of the Quattro Province, stops 8 km short
# of it - the four are a cultural region, not a survey point.
LANDMARKS = [
    ("chiappo", "MONTE CHIAPPO", 9.2003, 44.6864, 1699),
]

PLACES = [
    ("varzi",     "VARZI",                        9.1994, 44.8222, 416),
    ("casanova",  "CASANOVA STAFFORA",            9.2225, 44.7748, 625),
    ("smargh",    "SANTA MARGHERITA DI STAFFORA", 9.2290, 44.7570, 700),
    ("casale",    "CASALE STAFFORA",              9.2205, 44.7235, 930),
    ("poggio",    "PIAN DEL POGGIO",              9.2245, 44.7070, 1150),
    ("giova",     "PASSO DEL GIOVÀ",              9.2347, 44.6983, 1310),
    ("colletta",  "CIMA COLLETTA",                9.2351, 44.7164, 1494),
    ("brallopass","PASSO DEL BRALLO",             9.2636, 44.7540, 951),
    ("brallo",    "BRALLO DI PREGOLA",            9.2745, 44.7515, 950),
]


def wp_literal(rows):
    return [
        f'  {{ id: "{i}", name: "{n}", subtitle: null, '
        f"x: {project(lo, la)[0]:.2f}, y: {project(lo, la)[1]:.2f}, elevation: {e} }},"
        for i, n, lo, la, e in rows
    ]


# --- the road ---------------------------------------------------------------

# Two legs. The valley: the SP461 out of Varzi and the Staffora road above it,
# following the river to the head of the valley and over the Giovà. The
# crinale: the SP88 along the watershed, which is where the municipal
# boundaries run, over the Cima Colletta and down to the Brallo.
# Split at Casale Staffora, where the road stops following the river and
# starts climbing: 4.5% average below it, 12% above. The two legs are the two
# halves of the ride, not an arbitrary cut for the animation.
VALLEY = [
    ("varzi",    9.1994, 44.8222),
    (None,       9.2043, 44.8140),
    (None,       9.2093, 44.8062),
    (None,       9.2170, 44.7930),
    ("casanova", 9.2225, 44.7748),
    (None,       9.2262, 44.7660),
    ("smargh",   9.2290, 44.7570),
    (None,       9.2258, 44.7470),
    (None,       9.2235, 44.7390),
    ("casale",   9.2205, 44.7235),
]

SALITA = [
    ("casale",   9.2205, 44.7235),
    (None,       9.2218, 44.7150),
    ("poggio",   9.2245, 44.7070),
    (None,       9.2290, 44.7020),
    ("giova",    9.2347, 44.6983),
]

# The continuation past the Giovà: the SP88 along the crinale over the Cima
# Colletta to the Passo del Brallo and Brallo di Pregola. Not in the current
# film, which stops at the pass, but kept here because it is not guesswork -
# these are the Brallo / Santa Margherita / Zerba comune boundaries, and in
# the Apennines the comune line is the watershed the ridge road rides. Put
# ("crinale", crinale) back into LEGS to bring the leg back.
CRINALE = [
    ("giova",     9.2347, 44.6983),
    (None,        9.2323, 44.7033),
    (None,        9.2330, 44.7076),
    (None,        9.2359, 44.7128),
    ("colletta",  9.2351, 44.7164),
    (None,        9.2330, 44.7220),
    (None,        9.2335, 44.7254),
    (None,        9.2356, 44.7289),
    (None,        9.2368, 44.7340),
    (None,        9.2375, 44.7401),
    (None,        9.2454, 44.7412),
    (None,        9.2545, 44.7456),
    (None,        9.2592, 44.7482),
    ("brallopass",9.2636, 44.7540),
    (None,        9.2690, 44.7534),
    ("brallo",    9.2745, 44.7515),
]


ANCHORS = {"valle": VALLEY, "salita": SALITA}
pts = {name: P(lon, lat) for rows in ANCHORS.values() for name, lon, lat in rows if name}
valley = [P(lon, lat) for _, lon, lat in VALLEY]
salita = [P(lon, lat) for _, lon, lat in SALITA]

# No hairpins drawn in. The other tours in this repo sit close enough to the
# road to need them; this one holds 13 km across the frame, where a real
# hairpin is a couple of pixels wide and a drawn one reads as a knot. The
# curve through the anchors carries the shape of the road on its own.


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


legs = [("valle", valley), ("salita", salita)]
lengths = {lid: path_length(p) for lid, p in legs}
print("leg lengths", {k: round(v, 1) for k, v in lengths.items()})

# Where each named place falls along its leg, by arc length: the pins are cued
# off these so a name lands as the line reaches it, not before or after.
marks = {}
for lid, line in legs:
    for name in (n for n, _, _ in ANCHORS[lid] if n):
        i = line.index(pts[name])
        marks[name] = (lid, path_length(line[: i + 1]) / lengths[lid])
print("marks", {k: (v[0], round(v[1], 3)) for k, v in marks.items()})


# --- the elevation profile --------------------------------------------------
# Distance along the road against height, so the shape of the ride - the long
# drag up the valley, the ridge, the drop into the Brallo - is readable at a
# glance. Distances come from the projected line, heights from PLACES.

KM_PER_UNIT = (LON1 - LON0) * K * 111.32 / MAP_WIDTH
elevations = {i: e for i, _, _, _, e in PLACES}
profile = []
travelled = 0.0
for lid, line in legs:
    names = [n for n, _, _ in ANCHORS[lid] if n]
    for name in names:
        if profile and profile[-1][0] == name:
            continue  # Casale Staffora closes one leg and opens the next
        i = line.index(pts[name])
        km = travelled + path_length(line[: i + 1]) * KM_PER_UNIT
        profile.append((name, km, elevations[name]))
    travelled += lengths[lid] * KM_PER_UNIT
print("profile", [(n, round(k, 1), e) for n, k, e in profile])


def bbox(points, pad, pad_top=None, pad_bottom=None):
    pad_top = pad if pad_top is None else pad_top
    pad_bottom = pad_top if pad_bottom is None else pad_bottom
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    return (min(xs) - pad, min(ys) - pad_top, max(xs) + pad, max(ys) + pad_bottom)


# 14 km of valley down the long axis of a 9:16 frame: 3 km wide, 14 km tall.
# The side padding is what makes the shot - it buys 290px of clear paper
# either side of the line, which is where every name in the film goes. The
# floor is padded far deeper than the ceiling, which lifts the road up the
# frame and leaves the bottom band clear for the elevation profile.
route_box = bbox(valley + salita, 18.6, 2.1, 17.0)
# The middle shot is the Oltrepo around the road; the opening one has to hold
# the four province names as well as the road, so it is built from both.
region_box = bbox(valley + salita, 62)
# The opening shot is the four provinces themselves, whole: they are the
# thing with a name, and the ridge this road rides is where they meet.
prov_pts = [
    project(lon, lat)
    for feat in provinces["features"]
    if feat["properties"]["prov_name"] in QUATTRO
    for ring in rings(feat["geometry"])
    for lon, lat in ring
]
wide_box = bbox(prov_pts, 18, 30, 30)


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit -------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_oltrepo.py - do not hand-edit.")
out.append("// Sources: openpolis/geojson-italy (regioni, province, comuni).")
out.append("// Equirectangular projection, longitude scaled by cos(44.75 deg).")
out.append('import { BBox, RegionShape, RouteSegment, Waypoint } from "../shared/types";')
out.append("")
out.append(f"export const MAP_WIDTH = {MAP_WIDTH:.2f};")
out.append(f"export const MAP_HEIGHT = {MAP_HEIGHT:.2f};")
out.append("")
for var, rows, note in [
    ("italy", italy, "The country in greys: context, not subject."),
    ("province", quattro, "Pavia, Alessandria, Piacenza, Genova - le Quattro Province."),
    ("comuni", comuni, "The comuni the road runs through, for the closest shot."),
]:
    out.append(f"// {note}")
    out.append(f"export const {var}: RegionShape[] = [")
    for name, d in rows:
        out.append(f'  {{ name: {json.dumps(name)}, d: "{d}" }},')
    out.append("];")
    out.append("")
out.append("export const provinceLabels: Waypoint[] = [")
out += wp_literal(PROVINCE_LABELS)
out.append("];")
out.append("")
out.append("export const landmarks: Waypoint[] = [")
out += wp_literal(LANDMARKS)
out.append("];")
out.append("")
out.append("export const places: Waypoint[] = [")
out += wp_literal(PLACES)
out.append("];")
out.append("")
out.append("// Two legs: up the valley to the pass, then the ridge road.")
out.append("export const roadLegs: RouteSegment[] = [")
for lid, line in legs:
    out.append(
        f'  {{ id: "{lid}", d: "{catmull_rom_to_bezier(line)}", '
        + "points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in line) + "] },"
    )
out.append("];")
out.append("")
out.append("// How far along its leg each place sits, by arc length: what the")
out.append("// timeline cues the names off.")
out.append("export const marks: Record<string, { leg: string; t: number }> = {")
for name, (lid, t) in marks.items():
    out.append(f'  {name}: {{ leg: "{lid}", t: {t:.3f} }},')
out.append("};")
out.append("")
out.append("export type ProfilePoint = { id: string; km: number; elevation: number };")
out.append("export const profile: ProfilePoint[] = [")
for name, km, e in profile:
    out.append(f'  {{ id: "{name}", km: {km:.2f}, elevation: {e} }},')
out.append("];")
out.append(f"export const TOTAL_KM = {profile[-1][1]:.2f};")
out.append("")
out.append(bbox_literal("WIDE_BBOX", wide_box))
out.append(bbox_literal("REGION_BBOX", region_box))
out.append(bbox_literal("ROUTE_BBOX", route_box))
out.append("")

os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(out))

print("map", round(MAP_WIDTH), "x", round(MAP_HEIGHT, 1))
for nm, b in [("wide", wide_box), ("region", region_box), ("route", route_box)]:
    w, h = b[2] - b[0], b[3] - b[1]
    sc = min(840 / w, 1250 / h)
    print(f"{nm:7s} {w:7.1f} x {h:7.1f} units  ({w*KM_PER_UNIT:5.1f} x {h*KM_PER_UNIT:5.1f} km)"
          f"  scale {sc:6.3f} px/unit  fills {w*sc:5.0f} x {h*sc:5.0f} px")
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
