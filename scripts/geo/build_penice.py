"""Builds src/PeniceTour/geoData.ts: Bobbio - Passo del Penice - Varzi.

The SS461 del Passo del Penice the whole way: out of Bobbio, up the Emilian
side to the pass at 1149 m on the Lombardia border, and down the Val Staffora
side to Varzi. 28 km.

Unlike the earlier films the road is not traced off a screenshot: it is
OpenStreetMap's own geometry, from Overture Maps, routed along the SS461 by
overture_route.py (tracks/penice.json). The pass, Monte Penice and Varzi are
Overture's points too; Bobbio is where the Brallo - Bobbio film ends, so the
two films join on one point.

Regenerate with:
    python3 scripts/geo/overture_route.py scripts/geo/tracks/penice.json \\
        --bbox 9.12,44.70,9.45,44.86 --prefer 461 \\
        --stop bobbio=9.381797,44.769745 --stop penice=9.3283,44.79729 \\
        --stop varzi=9.1969,44.82354
    python3 scripts/geo/build_penice.py
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "PeniceTour", "geoData.ts")
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


def ring_to_path(ring, min_step):
    pts = []
    for lon, lat in ring:
        p = project(lon, lat)
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) >= min_step:
            pts.append(p)
    if len(pts) < 3:
        return None
    return "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


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
        parts = [p for p in (ring_to_path(r, min_step) for r in rings(feat["geometry"])) if p]
        if parts:
            out.append((feat["properties"].get(name_key) or "", "".join(parts)))
    return out


home = shapes(regions, "reg_name", 0.35, keep=lambda p: p["reg_name"] in HOME_REGIONS)
beyond = shapes(regions, "reg_name", 0.9, keep=lambda p: p["reg_name"] not in HOME_REGIONS)
# 16 km east-west, 6 north-south: the frame is width-limited, and a portrait
# frame shows far more above and below the road than beside it.
WINDOW = (9.08, 44.60, 9.50, 45.00)
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
        sys.exit(f"missing {path}: see the header of this script")
    return json.load(open(path))


track_t = read_track("penice")
track = [tuple(p) for p in track_t["lonlat"]]
stops = {k: tuple(v) for k, v in track_t["stops"].items()}
split = track.index(stops["penice"])
climb, descent = track[: split + 1], track[split:]
km_climb = sum(metres(p, q) for p, q in zip(climb, climb[1:])) / 1000
km_descent = sum(metres(p, q) for p, q in zip(descent, descent[1:])) / 1000
print(f"climb {km_climb:.1f} km, descent {km_descent:.1f} km, "
      f"{track_t['km_on_preferred']:.1f} of {track_t['km']:.1f} km on the SS461")

# The Brallo - Bobbio film ends where its screenshot put Bobbio; this road
# starts on the mapped SS461 nearest to it. They should be the same place.
BOBBIO = tuple(read_track("bobbio")["lonlat"][-1])
gap = metres(BOBBIO, track[0])
print(f"the road starts {gap:.0f} m from where the last film ends")
if gap > 150:
    sys.exit("more than 150 m - check the stops")


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


def region_of(p):
    for f in regions["features"]:
        if any(inside(p, r) for r in rings(f["geometry"])):
            return f["properties"]["reg_name"]
    return "?"


# Overture Maps points: the pass and the peak are OSM's saddle and peak nodes,
# Varzi its town node. Elevations are OSM's; Bobbio's as in the last film.
PENICE = (9.3283, 44.79729)
MONTE_PENICE = (9.31786, 44.78489)
VARZI = (9.1969, 44.82354)
PLACES = [
    ("bobbio", "BOBBIO", track[0], 272),
    ("penice", "PASSO DEL PENICE", PENICE, 1149),
    ("varzi", "VARZI", VARZI, 416),
]
for pid, _, ll, _ in PLACES:
    print(f"  {pid:7s} {ll[0]:.5f}, {ll[1]:.5f}  ({comune_of(ll)}, {region_of(ll)})")
for pid, ll, want in [("bobbio", track[0], "Bobbio"), ("varzi", VARZI, "Varzi")]:
    if comune_of(ll) != want:
        sys.exit(f"{pid} is not in the comune of {want}")
if metres(track[split], PENICE) > 50:
    sys.exit("the road misses the pass")

# Where the road crosses from Emilia-Romagna into Lombardia.
crossings = [i for i in range(1, len(track))
             if region_of(track[i - 1]) != region_of(track[i])]
for i in crossings:
    print(f"  border crossed at {track[i][0]:.5f}, {track[i][1]:.5f}, "
          f"{metres(track[i], PENICE):.0f} m from the pass")

# The regions' names on their own ground, for the close framing the camera
# rides in: Emilia-Romagna around Bobbio and up to the pass, Lombardia from
# the border down to Varzi. Each one has to fall inside its region.
# Those by the pass only arrive as the climb nears it: from Bobbio they would
# sit half off the left edge of the frame.
CLOSE_TAGS = [
    ("EMILIA-ROMAGNA", (9.3620, 44.7520), "Emilia-Romagna", False),
    ("EMILIA-ROMAGNA", (9.3380, 44.7720), "Emilia-Romagna", True),
    ("LOMBARDIA", (9.3060, 44.8215), "Lombardia", True),
    ("LOMBARDIA", (9.2350, 44.8000), "Lombardia", True),
]
for name, ll, want, _ in CLOSE_TAGS:
    if region_of(ll) != want:
        sys.exit(f"the {name} tag at {ll} is not in {want}")

climb_xy = [project(*p) for p in climb]
descent_xy = [project(*p) for p in descent]


def path_length(points):
    return sum(math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1])
               for i in range(1, len(points)))


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

xy = climb_xy + descent_xy
xs = [p[0] for p in xy]; ys = [p[1] for p in xy]
# Width-limited, like the Bobbio film: a little slack either side for the end
# names, more above and below for the pass label and the plates.
route_box = (min(xs) - 3.0, min(ys) - 6.0, max(xs) + 3.0, max(ys) + 6.0)

# The closing framing is route_box fitted to the safe area (x 60-900,
# y 250-1500). Its region names are placed where they read on screen - clear
# of the names, the road and the closing card - and then checked to be on
# the right side of the border.
SAFE = (60, 250, 840, 1250)
fit = min(SAFE[2] / (route_box[2] - route_box[0]), SAFE[3] / (route_box[3] - route_box[1]))
fit_tx = SAFE[0] + SAFE[2] / 2 - fit * (route_box[0] + route_box[2]) / 2
fit_ty = SAFE[1] + SAFE[3] / 2 - fit * (route_box[1] + route_box[3]) / 2


def unproject(x, y):
    return (x / (K * SCALE) + LON0, LATMAX - y / SCALE)


WIDE_TAGS = [
    ("LOMBARDIA", (280, 620), "Lombardia"),
    ("EMILIA-ROMAGNA", (690, 1150), "Emilia-Romagna"),
]
wide_tags = []
for name, (sx, sy), want in WIDE_TAGS:
    x, y = (sx - fit_tx) / fit, (sy - fit_ty) / fit
    if region_of(unproject(x, y)) != want:
        sys.exit(f"the closing {name} tag is not in {want}")
    wide_tags.append((name, x, y))


def bbox_literal(name, b):
    return (f"export const {name}: BBox = {{ x0: {b[0]:.2f}, y0: {b[1]:.2f}, "
            f"x1: {b[2]:.2f}, y1: {b[3]:.2f} }};")


# --- emit --------------------------------------------------------------------------

out = []
out.append("// Auto-generated by scripts/geo/build_penice.py - do not hand-edit.")
out.append("// Road: OpenStreetMap via Overture Maps, routed by scripts/geo/overture_route.py.")
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
mx, my = project(*MONTE_PENICE)
out.append("// Monte Penice, 1460 m, the summit above the pass.")
out.append(f"export const MONTE_PENICE = {{ x: {mx:.2f}, y: {my:.2f}, elevation: 1460 }};")
out.append("")
out.append("// Region names on their own ground: `wide` ones for the closing whole-road")
out.append("// framing, the rest for the close framing the camera rides in.")
out.append("export const regionTags = [")
for name, ll, _, at_pass in CLOSE_TAGS:
    x, y = project(*ll)
    out.append(f'  {{ name: "{name}", x: {x:.2f}, y: {y:.2f}, wide: false, '
               f'atPass: {"true" if at_pass else "false"} }},')
for name, x, y in wide_tags:
    out.append(f'  {{ name: "{name}", x: {x:.2f}, y: {y:.2f}, wide: true, atPass: false }},')
out.append("];")
out.append("")
for var, pts, km in [("climb", climb_xy, km_climb), ("descent", descent_xy, km_descent)]:
    out.append(f"// {km:.1f} km.")
    out.append(f"export const {var}: RouteSegment = {{")
    out.append(f'  id: "{var}", d: "{catmull_rom_to_bezier(pts)}",')
    out.append("  points: [" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in pts) + "],")
    out.append("};")
    out.append("")
out.append(f"export const KM_TOTAL = {km_climb + km_descent:.0f};")
out.append(f"export const KM_CLIMB = {km_climb:.1f};")
out.append(f"export const KM_DESCENT = {km_descent:.1f};")
out.append("")
out.append(bbox_literal("ROUTE_BBOX", route_box))
out.append("")

os.makedirs(os.path.dirname(OUT_TS), exist_ok=True)
with open(OUT_TS, "w") as f:
    f.write("\n".join(out))

for nm, b in [("route", route_box)]:
    w, h = b[2] - b[0], b[3] - b[1]
    sc = min(840 / w, 1250 / h)
    print(f"{nm:6s} {w:6.1f} x {h:6.1f} units ({w*KM_PER_UNIT:4.1f} x {h*KM_PER_UNIT:4.1f} km)"
          f"  {KM_PER_UNIT*1000/sc:5.1f} m/px  fills {w*sc:4.0f} x {h*sc:4.0f} px")
print("wrote", OUT_TS, os.path.getsize(OUT_TS), "bytes")
