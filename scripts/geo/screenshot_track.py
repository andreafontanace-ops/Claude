"""Turn a Google Maps route screenshot into a lon/lat track.

    python3 scripts/geo/screenshot_track.py SHOT.png OUT.json \
        --apex X,Y --start X,Y --end X,Y [--via X,Y ...] [--poi NAME=X,Y ...]
        [--check CHECK.png]

No routing service is reachable from the render environment, so the real
roads come in as screenshots of a Google Maps route. Two steps:

1. Georeference. Google draws region boundaries as dashed white lines, and
   those are the same boundaries as openpolis/ISTAT italy_regions.geojson. The
   screenshot is fitted to them: Web Mercator, north up, so three parameters
   (scale and two offsets), found by chamfer matching the official boundary
   lines against the detected dashes. --apex is a rough pixel for the Santa
   Margherita / Brallo / Zerba tripoint - the tip of the Emilia-Romagna wedge
   that pokes north between the two - which seeds the search.

2. Extract. The route is the saturated blue-violet line. It is broken wherever
   a label, the time callout or a marker sits on it, so the pieces are
   skeletonised and bridged across gaps (only between different pieces, so a
   bridge can never cut a hairpin off one piece), and the path is found start
   to end through --via: the white-ring markers of the stops the route was
   built through, which are on the road by construction.

Known limit: at ~8 m/px, with Google's line about 8 px wide, switchbacks whose
legs are closer than ~65 m merge into one blob and their tips come out
shortened. The track is shorter than Google's distance for that reason; use
Google's figure for distances. The film draws at about the same scale, so it
could not show those tips either.
"""
import argparse, heapq, json, math, os

import numpy as np
from PIL import Image
from scipy import ndimage, optimize
from scipy.spatial import cKDTree
from skimage import measure
from skimage.morphology import closing, disk, skeletonize

HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = os.path.join(HERE, "italy_regions.geojson")
TRIPOINT = (9.2351, 44.7164)  # Santa Margherita / Brallo di Pregola / Zerba


def xy(s):
    return tuple(float(v) for v in s.split(","))


ap = argparse.ArgumentParser()
ap.add_argument("shot"); ap.add_argument("out")
ap.add_argument("--apex", type=xy, required=True)
ap.add_argument("--start", type=xy, required=True)
ap.add_argument("--end", type=xy, required=True)
ap.add_argument("--via", type=xy, nargs="*", default=[])
ap.add_argument("--via-names", nargs="*", default=[])
# Places that are not on the line - a summit icon beside it, say - converted
# through the same georeference but not snapped to the road.
ap.add_argument("--poi", nargs="*", default=[])
ap.add_argument("--check")
args = ap.parse_args()

img = np.asarray(Image.open(args.shot).convert("RGB")).astype(int)
H, W = img.shape[:2]
R, G, B = img[..., 0], img[..., 1], img[..., 2]


# --- 1. georeference -------------------------------------------------------

# Dashes: small, near-white, unsaturated specks. Labels are white too but come
# in bigger connected blobs, so a size cap drops them.
white = (img.min(-1) > 175) & (img.max(-1) - img.min(-1) < 45)
lab = measure.label(white, connectivity=2)
sizes = np.bincount(lab.ravel())
small = np.zeros_like(sizes, bool)
small[1:] = sizes[1:] <= 10
dash = small[lab]
dist = np.minimum(ndimage.distance_transform_edt(~dash), 12.0)


def rings(g):
    t, c = g["type"], g["coordinates"]
    for poly in ([c] if t == "Polygon" else c):
        for r in poly:
            yield [tuple(p) for p in r]


feats = {f["properties"]["reg_name"]: list(rings(f["geometry"]))
         for f in json.load(open(REGIONS))["features"]}
WIN = (9.05, 44.58, 9.45, 44.86)
segs = []
for a, b in [("Lombardia", "Emilia-Romagna"), ("Lombardia", "Piemonte"),
             ("Piemonte", "Emilia-Romagna")]:
    Bset = {(round(x, 4), round(y, 4)) for r in feats[b] for x, y in r}
    for r in feats[a]:
        for p, q in zip(r, r[1:]):
            if ((round(p[0], 4), round(p[1], 4)) in Bset and (round(q[0], 4), round(q[1], 4)) in Bset
                    and WIN[0] <= p[0] <= WIN[2] and WIN[1] <= p[1] <= WIN[3]):
                segs.append((p, q))
bpts = []
for (x1, y1), (x2, y2) in segs:
    n = max(1, int(math.hypot(x2 - x1, y2 - y1) / 0.00005))  # ~5 m
    bpts += [(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n) for k in range(n)]
bpts = np.array(bpts)


def merc(lat):
    return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)))


def unmerc(my):
    return math.degrees(2 * math.atan(math.exp(math.radians(my))) - math.pi / 2)


BLON, BMY = bpts[:, 0], merc(bpts[:, 1])


def project(p, lon, my):
    s, lon0, my0 = p
    return s * (lon - lon0), s * (my0 - my)


SAMPLE_M = 5.0  # ground spacing of the boundary samples above
M_PER_DEG = 111320 * math.cos(math.radians(44.72))


def score(p):
    """Length, in screen pixels, of official boundary that lands on a dash.

    Not a mean distance: that rewards zooming out, because squeezing more
    boundary into the frame lowers the average even when none of it lines up -
    which is how an earlier version fitted both screenshots at twice their real
    scale. Counting coincident length cannot be gamed that way. At the right fit
    hundreds of pixels of dashed line lie on the boundary; at a wrong one only
    chance hits do, a few percent of whatever boundary is in frame, and the
    frame is too small for chance to add up to a real fit.

    A soft count (full credit on a dash, fading to none 3 px away) keeps it
    smooth enough for the local refinement."""
    x, y = project(p, BLON, BMY)
    inside = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    if not inside.any():
        return 0.0
    d = dist[np.round(y[inside]).astype(int), np.round(x[inside]).astype(int)]
    hits = np.clip(1.0 - d / 3.0, 0.0, 1.0).sum()
    px_per_sample = SAMPLE_M * p[0] / M_PER_DEG
    return hits * px_per_sample


def seeded(s, ax, ay):
    return (s, TRIPOINT[0] - ax / s, float(merc(TRIPOINT[1])) + ay / s)


# Wide enough for anything from a whole-province view to a close-up: Google's
# fractional zooms put these screenshots anywhere from ~5 to ~15 m/px.
best = (-1.0, None)
for s in np.arange(4000, 18000, 150):
    for dx in range(-40, 41, 5):
        for dy in range(-40, 41, 5):
            p = seeded(s, args.apex[0] + dx, args.apex[1] + dy)
            sc = score(p)
            if sc > best[0]:
                best = (sc, p)
geo = optimize.minimize(lambda p: -score(p), best[1], method="Nelder-Mead",
                        options=dict(xatol=1e-8, fatol=1e-3, maxiter=4000)).x
m_per_px = 111320 * math.cos(math.radians(44.72)) / geo[0]

# Quality: how far the dashes that belong to a boundary sit from it. Measured
# image-to-model (dash pixels within 6 px of the fitted line), so label and
# road clutter elsewhere in the frame does not flatter the number.
bx, by = project(geo, BLON, BMY)
tree = cKDTree(np.column_stack([bx, by]))
dys, dxs = np.nonzero(dash)
dd, _ = tree.query(np.column_stack([dxs, dys]))
on_line = dd < 6
resid_px = float(np.median(dd[on_line])) if on_line.any() else float("nan")
print(f"georeference: {m_per_px:.2f} m/px, {score(geo):.0f} px of boundary on dashes, "
      f"median residual {resid_px:.2f} px = {resid_px * m_per_px:.0f} m")


def to_lonlat(x, y):
    return (geo[1] + x / geo[0], unmerc(geo[2] - y / geo[0]))


# --- 2. extract ------------------------------------------------------------

route = (B > 190) & (G < 120) & (B - R > 80)
route = closing(route, disk(2))
rl, n = ndimage.label(route)
sz = ndimage.sum(route, rl, range(1, n + 1))
keep = np.zeros(n + 1, bool)
keep[1:] = sz >= 15
skel = skeletonize(keep[rl])
comp, npieces = ndimage.label(skel, structure=np.ones((3, 3)))
pix = set(zip(*[a.tolist() for a in np.nonzero(skel)]))
arr = np.array(sorted(pix))
ktree = cKDTree(arr)


def nbrs(u):
    return [(u[0] + dy, u[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            if (dy or dx) and (u[0] + dy, u[1] + dx) in pix]


GAP = 45
bridges = {}
for u in pix:
    if len(nbrs(u)) == 1:
        for j in ktree.query_ball_point(u, GAP):
            v = tuple(arr[j])
            if comp[v] != comp[u]:
                d = math.hypot(v[0] - u[0], v[1] - u[1])
                bridges.setdefault(u, []).append((v, d))
                bridges.setdefault(v, []).append((u, d))


def nearest(p):
    _, j = ktree.query((p[1], p[0]))
    return tuple(arr[j])


def shortest(s, e):
    best_d = {s: 0.0}; prev = {}; pq = [(0.0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == e:
            break
        if d > best_d.get(u, 1e18):
            continue
        steps = [(v, 1.4142 if (v[0] - u[0]) and (v[1] - u[1]) else 1.0) for v in nbrs(u)]
        # a jump costs more than walking, so it is only taken across a real gap
        steps += [(v, w * 1.5) for v, w in bridges.get(u, [])]
        for v, w in steps:
            if d + w < best_d.get(v, 1e18):
                best_d[v] = d + w; prev[v] = u
                heapq.heappush(pq, (d + w, v))
    if e not in best_d:
        raise SystemExit(f"no path along the route from {s} to {e}")
    seg = [e]
    while seg[-1] != s:
        seg.append(prev[seg[-1]])
    return seg[::-1]


stops = [nearest(args.start)] + [nearest(v) for v in args.via] + [nearest(args.end)]
path = [stops[0]]
for a, b in zip(stops, stops[1:]):
    path += shortest(a, b)[1:]

# A light moving average takes the pixel staircase off without shaving the
# bends, then Ramer-Douglas-Peucker drops the redundant points.
P = np.array([(x, y) for y, x in path], float)
K = 1
sm = np.array([P[max(0, i - K): i + K + 1].mean(0) for i in range(len(P))])
sm[0], sm[-1] = P[0], P[-1]


def rdp(points, eps):
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = abs(dy * points[i][0] - dx * points[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(points[: idx + 1], eps)[:-1] + rdp(points[idx:], eps)
    return [points[0], points[-1]]


simp = rdp([tuple(p) for p in sm], 0.6)
track = [to_lonlat(x, y) for x, y in simp]


def metres(p, q):
    lon1, lat1, lon2, lat2 = map(math.radians, (*p, *q))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(h))


km = sum(metres(p, q) for p, q in zip(track, track[1:])) / 1000
names = ["start"] + (args.via_names or [f"via{i}" for i in range(len(args.via))]) + ["end"]
stop_ll = {nm: to_lonlat(p[1], p[0]) for nm, p in zip(names, stops)}
pois = {}
for spec in args.poi:
    name, pos = spec.split("=")
    pois[name] = to_lonlat(*xy(pos))
print(f"track: {len(track)} points, {km:.2f} km; {npieces} line pieces bridged")
for nm, (lo, la) in list(stop_ll.items()) + [(f"{k} (poi)", v) for k, v in pois.items()]:
    print(f"  {nm:18s} {lo:.5f}, {la:.5f}")

os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
json.dump({
    "source": "Google Maps route screenshot, georeferenced to openpolis/ISTAT "
              "region boundaries by scripts/geo/screenshot_track.py",
    "m_per_px": round(m_per_px, 3),
    "georef_residual_m": round(resid_px * m_per_px, 1),
    "km_extracted": round(km, 2),
    "stops": {k: [round(v[0], 6), round(v[1], 6)] for k, v in stop_ll.items()},
    "pois": {k: [round(v[0], 6), round(v[1], 6)] for k, v in pois.items()},
    "lonlat": [[round(lo, 6), round(la, 6)] for lo, la in track],
}, open(args.out, "w"), indent=1)

if args.check:
    vis = (img * 0.4).astype(np.uint8)
    vis[dash] = [255, 255, 0]
    for xx, yy in zip(bx, by):
        if 0 <= xx < W - 1 and 0 <= yy < H - 1:
            vis[int(yy), int(xx)] = [0, 255, 255]
    for x, y in simp:
        xi, yi = int(round(x)), int(round(y))
        vis[max(0, yi - 1):yi + 2, max(0, xi - 1):xi + 2] = [255, 80, 0]
    Image.fromarray(vis).save(args.check)
    print("check image:", args.check)
