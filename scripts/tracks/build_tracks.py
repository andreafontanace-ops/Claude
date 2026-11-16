"""Turn the route recipes in rides.json into GPX tracks and site data.

    python scripts/tracks/fetch_roads.py     # once: road network from Overture
    python scripts/tracks/build_tracks.py

For every ride it routes between the recipe's via points on the real road
network, samples elevation from the SRTM-derived terrain tiles on AWS, and
writes:

  site/tracks/<slug>.gpx      free rides, served by the site as-is
  private-tracks/<slug>.gpx   paid rides: git-ignored, upload to Lemon Squeezy
  private-tracks/<bundle>.zip one archive per bundle in site/store.json
  site/data/rides.json        stats, pass markers, a coarse preview line and an
                              elevation profile for every ride

The preview line is simplified on purpose: enough to show where the ride goes,
not a track you could load into a navigator.
"""
import gzip
import heapq
import json
import math
import os
import struct
import urllib.request
import zipfile
from collections import defaultdict
from xml.sax.saxutils import escape

import numpy as np
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, ".cache")
SITE = os.path.join(ROOT, "site")
PRIVATE = os.path.join(ROOT, "private-tracks")

R_EARTH = 6371008.8

# Travel speeds (km/h) used only to choose between roads: between two via
# points the router takes the quickest road, which on a pass is the pass road.
SPEED = {"trunk": 70, "primary": 60, "secondary": 50, "tertiary": 40,
         "unclassified": 30, "residential": 20, "living_street": 8}
MOTOR_MODES = {"motor_vehicle", "motorcycle", "vehicle", "car", "moped", "mofa"}
UNPAVED = {"unpaved", "gravel", "dirt"}

MONTHS_IT = {"Jan": "gen", "Feb": "feb", "Mar": "mar", "Apr": "apr",
             "May": "mag", "Jun": "giu", "Jul": "lug", "Aug": "ago",
             "Sep": "set", "Oct": "ott", "Nov": "nov", "Dec": "dic"}


def haversine(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(a))


def parse_linestring(wkb):
    order = "<" if wkb[0] == 1 else ">"
    gtype = struct.unpack(order + "I", wkb[1:5])[0]
    dims = 3 if gtype in (1002, 0x80000002) else 2
    n = struct.unpack(order + "I", wkb[5:9])[0]
    vals = struct.unpack(order + "d" * (n * dims), wkb[9:9 + 8 * n * dims])
    return [(vals[i * dims], vals[i * dims + 1]) for i in range(n)]


def in_range(between, at):
    return not between or between[0] <= at <= between[1]


# --- road graph ---------------------------------------------------------------

class Graph:
    def __init__(self, region):
        rows = pq.read_table(os.path.join(CACHE, f"roads-{region}.parquet")).to_pylist()
        self.coord = {}                 # node -> (lon, lat)
        self.adj = defaultdict(list)    # node -> [(node, seconds, metres, edge)]
        self.edges = []                 # edge -> dict of what the GPX and site need
        self.node_seg = defaultdict(set)
        for row in rows:
            self._add_segment(row)
        self._grid = defaultdict(list)
        for node, (lon, lat) in self.coord.items():
            self._grid[(int(lon * 100), int(lat * 100))].append(node)
        print(f"{region}: {len(self.coord)} nodes, {len(self.edges)} edges")

    def _add_segment(self, row):
        pts = parse_linestring(row["geometry"])
        if len(pts) < 2:
            return
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + haversine(a[0], a[1], b[0], b[1]))
        total = cum[-1] or 1.0
        frac = [c / total for c in cum]
        names = row["names"] or {}
        name = names.get("primary") or ""
        refs = [r["ref"] for r in (row["routes"] or []) if r.get("ref")]
        label = " ".join([name] + refs).lower()

        node_at = {}
        for c in row["connectors"] or []:
            i = min(range(len(pts)), key=lambda k: abs(frac[k] - c["at"]))
            node_at[i] = "c:" + c["connector_id"]
        nodes = [node_at.get(i, f"s:{row['id']}:{i}") for i in range(len(pts))]
        for n, p in zip(nodes, pts):
            self.coord.setdefault(n, p)
            self.node_seg[n].add(label)

        rules = row["access_restrictions"] or []
        surfaces = row["road_surface"] or []
        flags = row["road_flags"] or []
        speed = SPEED[row["class"]]
        for i in range(len(pts) - 1):
            at = (frac[i] + frac[i + 1]) / 2
            fwd, bwd, closed_in = self._access(rules, at)
            if not fwd and not bwd:
                continue
            d = cum[i + 1] - cum[i]
            secs = d / (speed / 3.6)
            if any(s["value"] in UNPAVED and in_range(s.get("between"), at) for s in surfaces):
                secs *= 5
            tunnel = any("is_tunnel" in (f["values"] or []) and in_range(f.get("between"), at)
                         for f in flags)
            e = len(self.edges)
            self.edges.append({"name": name, "refs": refs, "tunnel": tunnel,
                               "closed": closed_in})
            if fwd:
                self.adj[nodes[i]].append((nodes[i + 1], secs, d, e))
            if bwd:
                self.adj[nodes[i + 1]].append((nodes[i], secs, d, e))

    @staticmethod
    def _access(rules, at):
        """(forward ok, backward ok, seasonal closure) for a motorcycle."""
        fwd = bwd = True
        closed = None
        live = []
        for r in rules:
            if not in_range(r.get("between"), at):
                continue
            w = r.get("when") or {}
            modes = w.get("mode") or []
            motor = not modes or any(m in MOTOR_MODES for m in modes)
            if r["access_type"] != "denied" or not motor or w.get("vehicle"):
                continue
            if w.get("using") or w.get("recognized"):
                continue
            if w.get("during"):
                closed = w["during"]
                continue
            live.append(w)
        for w in live:
            # A pass road closed for winter sometimes carries a bare "denied"
            # over the same stretch as its seasonal rule (the Agnello's French
            # side does): that is the winter closure again, not a ban.
            if closed and not w.get("heading"):
                continue
            if w.get("heading") == "backward":
                bwd = False
            elif w.get("heading") == "forward":
                fwd = False
            else:
                fwd = bwd = False
        return fwd, bwd, closed

    def snap(self, lon, lat, road=None):
        """Nearest routable node, optionally only on roads matching `road`."""
        cx, cy = int(lon * 100), int(lat * 100)
        best, best_d = None, float("inf")
        for radius in range(0, 8):
            for gx in range(cx - radius, cx + radius + 1):
                for gy in range(cy - radius, cy + radius + 1):
                    if max(abs(gx - cx), abs(gy - cy)) != radius:
                        continue
                    for n in self._grid.get((gx, gy), ()):
                        if not self.adj.get(n):
                            continue
                        if road and not any(road.lower() in s for s in self.node_seg[n]):
                            continue
                        p = self.coord[n]
                        d = haversine(lon, lat, p[0], p[1])
                        if d < best_d:
                            best, best_d = n, d
            if best is not None and best_d < radius * 700:
                break
        if best is None:
            raise RuntimeError(f"no road near {lon},{lat} ({road})")
        return best, best_d

    def route(self, a, b):
        """A* on travel time; returns [(node, edge-into-node)]."""
        vmax = max(SPEED.values()) / 3.6
        bx, by = self.coord[b]
        h = lambda n: haversine(self.coord[n][0], self.coord[n][1], bx, by) / vmax
        dist = {a: 0.0}
        prev = {}
        heap = [(h(a), 0.0, a)]
        while heap:
            _, g, n = heapq.heappop(heap)
            if n == b:
                break
            if g > dist.get(n, float("inf")):
                continue
            for m, secs, _, e in self.adj.get(n, ()):
                ng = g + secs
                if ng < dist.get(m, float("inf")):
                    dist[m] = ng
                    prev[m] = (n, e)
                    heapq.heappush(heap, (ng + h(m), ng, m))
        if b not in dist:
            raise RuntimeError(f"no route between {self.coord[a]} and {self.coord[b]}")
        path = [(b, None)]
        while path[-1][0] != a:
            n, e = prev[path[-1][0]]
            path[-1] = (path[-1][0], e)
            path.append((n, None))
        return path[::-1]


# --- elevation ----------------------------------------------------------------

class Terrain:
    """SRTM-based 1 arc-second tiles (Skadi format) from AWS Terrain Tiles."""
    URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi/{ns}/{name}.hgt.gz"

    def __init__(self):
        self.tiles = {}

    def _tile(self, lat0, lon0):
        key = (lat0, lon0)
        if key not in self.tiles:
            ns = f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}"
            name = f"{ns}{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}"
            path = os.path.join(CACHE, f"{name}.hgt.gz")
            if not os.path.exists(path):
                print(f"downloading terrain tile {name}")
                urllib.request.urlretrieve(self.URL.format(ns=ns, name=name), path)
            raw = gzip.open(path).read()
            n = int(math.sqrt(len(raw) // 2))
            self.tiles[key] = np.frombuffer(raw, ">i2").reshape(n, n).astype(float)
        return self.tiles[key]

    def at(self, lon, lat):
        lat0, lon0 = math.floor(lat), math.floor(lon)
        t = self._tile(lat0, lon0)
        n = t.shape[0] - 1
        y, x = (lat0 + 1 - lat) * n, (lon - lon0) * n
        i, j = min(int(y), n - 1), min(int(x), n - 1)
        fy, fx = y - i, x - j
        q = t[i:i + 2, j:j + 2]
        return float(q[0, 0] * (1 - fx) * (1 - fy) + q[0, 1] * fx * (1 - fy) +
                     q[1, 0] * (1 - fx) * fy + q[1, 1] * fx * fy)


# --- geometry helpers ---------------------------------------------------------

def simplify(points, tol_m):
    """Douglas-Peucker in metres on a local equirectangular projection."""
    if len(points) < 3:
        return points
    lat0 = math.radians(sum(p[1] for p in points) / len(points))
    xy = [(math.radians(p[0]) * math.cos(lat0) * R_EARTH, math.radians(p[1]) * R_EARTH)
          for p in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        s, e = stack.pop()
        (x1, y1), (x2, y2) = xy[s], xy[e]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        idx, dmax = None, tol_m
        for k in range(s + 1, e):
            x0, y0 = xy[k]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / norm
            if d > dmax:
                idx, dmax = k, d
        if idx is not None:
            keep[idx] = True
            stack += [(s, idx), (idx, e)]
    return [p for p, k in zip(points, keep) if k]


def resample(points, eles, step):
    """Points every `step` metres along the line: (km, lon, lat, ele)."""
    out = [(0.0, points[0][0], points[0][1], eles[0])]
    dist, carry = 0.0, 0.0
    for (a, ea), (b, eb) in zip(zip(points, eles), zip(points[1:], eles[1:])):
        seg = haversine(a[0], a[1], b[0], b[1])
        pos = step - carry
        while pos <= seg:
            t = pos / seg
            out.append(((dist + pos) / 1000, a[0] + (b[0] - a[0]) * t,
                        a[1] + (b[1] - a[1]) * t, ea + (eb - ea) * t))
            pos += step
        carry = (carry + seg) % step
        dist += seg
    out.append((dist / 1000, points[-1][0], points[-1][1], eles[-1]))
    return out


def smooth(values, window):
    half = window // 2
    out = []
    for i in range(len(values)):
        chunk = values[max(0, i - half): i + half + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def climb(values, threshold=10.0):
    """Total ascent, counting a rise only once it passes `threshold` metres.
    A 30 m terrain model is noisy in gorges, where the road hugs a cliff;
    summing every wiggle would overstate the climb by a third. Checked
    against signposted pass and town elevations, this lands within ~5%."""
    total, ref = 0.0, values[0]
    for v in values[1:]:
        if v - ref >= threshold:
            total += v - ref
            ref = v
        elif ref - v >= threshold:
            ref = v
    return total


def closure_label(raw):
    """'Oct-May' -> 'ott–mag'; anything else is shown as OSM has it."""
    parts = raw.replace(" ", "").split("-")
    if len(parts) == 2 and all(p in MONTHS_IT for p in parts):
        return f"{MONTHS_IT[parts[0]]}–{MONTHS_IT[parts[1]]}"
    return raw


def cut_spurs(path, graph, max_m=8000):
    """Drop out-and-back detours: a via point that snapped onto a side road
    makes the route ride in and straight back out. Any stretch that leaves a
    node and returns to it within `max_m` is removed; a whole loop ride, which
    returns to its start only at the very end, is far longer and is kept."""
    out, index, along = [], {}, [0.0]
    for node, edge in path:
        if node in index:
            j = index[node]
            if along[-1] - along[j] <= max_m:
                for n, _ in out[j + 1:]:
                    index.pop(n, None)
                del out[j + 1:]
                del along[j + 1:]
                continue
        if out:
            a, b = graph.coord[out[-1][0]], graph.coord[node]
            along.append(along[-1] + haversine(a[0], a[1], b[0], b[1]))
        index[node] = len(out)
        out.append((node, edge))
    return out


# --- one ride -----------------------------------------------------------------

def build_ride(ride, graph, terrain):
    snapped = []
    for v in ride["via"]:
        node, d = graph.snap(v["lon"], v["lat"], v.get("road"))
        if d > 400:
            print(f"  ! {v['name']} snapped {d:.0f} m away")
        snapped.append(node)

    path = [(snapped[0], None)]
    for a, b in zip(snapped, snapped[1:]):
        path += graph.route(a, b)[1:]
    path = cut_spurs(path, graph)

    pts =[graph.coord[n] for n, _ in path]
    edges = [graph.edges[e] if e is not None else None for _, e in path]
    tunnel = [bool(e and e["tunnel"]) for e in edges]

    # The terrain under a tunnel is the mountain above it: carry the road
    # straight through instead, from portal to portal.
    eles = [terrain.at(lon, lat) for lon, lat in pts]
    i = 0
    while i < len(pts):
        if tunnel[i]:
            s = i - 1
            while i < len(pts) and tunnel[i]:
                i += 1
            e = min(i, len(pts) - 1)
            if s >= 0:
                for k in range(s + 1, e):
                    t = (k - s) / (e - s)
                    eles[k] = eles[s] + (eles[e] - eles[s]) * t
        i += 1

    samples = resample(pts, eles, 25)
    sm = smooth([s[3] for s in samples], 9)
    ascent = climb(sm)
    descent = climb([-v for v in sm])
    km = samples[-1][0]

    # Riding time: a touring pace on mountain roads, slowed by the climbing.
    hours = km / 55 + ascent / 1000 * 0.4
    minutes = int(round(hours * 60 / 15) * 15)

    closures = sorted({closure_label(e["closed"]) for e in edges if e and e["closed"]})
    roads = []
    for e in edges:
        for ref in (e["refs"] if e else []):
            # Swiss main roads carry a bare number in OSM; on the signs and
            # in guides they are Hauptstrasse 2, written H2.
            ref = f"H{ref}" if ref.isdigit() else ref
            if ref not in roads:
                roads.append(ref)

    # Markers: every via point flagged as a pass or a stop, placed on the track.
    markers = []
    for v, node in zip(ride["via"], snapped):
        if not (v.get("pass") or v.get("stop")):
            continue
        lon, lat = graph.coord[node]
        k = min(range(len(samples)),
                key=lambda j: haversine(lon, lat, samples[j][1], samples[j][2]))
        markers.append({"name": v["name"], "lon": round(lon, 5), "lat": round(lat, 5),
                        "km": round(samples[k][0], 1),
                        "ele": v.get("pass") or int(round(sm[k])),
                        "kind": "pass" if v.get("pass") else "stop"})

    step = max(1, len(samples) // 160)
    # [km, metres, lon, lat]: the position lets the site move a marker along
    # the map as the pointer runs over the profile.
    def prof(j):
        return [round(samples[j][0], 2), int(round(sm[j])),
                round(samples[j][1], 4), round(samples[j][2], 4)]
    profile = [prof(j) for j in range(0, len(samples), step)]
    if profile[-1][0] != round(samples[-1][0], 2):
        profile.append(prof(len(samples) - 1))

    preview = [[round(p[0], 4), round(p[1], 4)] for p in simplify(pts, 60)]
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]

    return {
        "points": pts, "eles": eles, "via": ride["via"], "snapped":
            [graph.coord[n] for n in snapped],
        "data": {
            "slug": ride["slug"], "title": ride["title"], "subtitle": ride["subtitle"],
            "area": ride["area"], "description": ride["description"],
            "highlights": ride["highlights"],
            "km": round(km, 1), "ascent": int(round(ascent / 10) * 10),
            "descent": int(round(descent / 10) * 10),
            "maxEle": int(round(max(sm))), "minEle": int(round(min(sm))),
            "minutes": minutes, "roads": roads[:8], "closures": closures,
            "markers": markers, "bbox": [round(min(lons), 4), round(min(lats), 4),
                                         round(max(lons), 4), round(max(lats), 4)],
            "preview": preview, "profile": profile,
            "trackPoints": len(pts),
        },
    }


# --- GPX ----------------------------------------------------------------------

def gpx(ride, built, brand):
    d = built["data"]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<gpx version="1.1" creator="{escape(brand)}" '
           'xmlns="http://www.topografix.com/GPX/1/1" '
           'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 '
           'http://www.topografix.com/GPX/1/1/gpx.xsd">',
           "  <metadata>",
           f"    <name>{escape(d['title'])}</name>",
           f"    <desc>{escape(d['subtitle'])}. {d['km']} km, +{d['ascent']} m. "
           "Percorso pianificato: verifica sempre aperture e chiusure stradali prima "
           "di partire.</desc>",
           f"    <author><name>{escape(brand)}</name></author>",
           '    <copyright author="OpenStreetMap contributors">',
           "      <license>https://opendatacommons.org/licenses/odbl/1-0/</license>",
           "    </copyright>",
           '    <link href="https://www.openstreetmap.org/copyright">'
           "<text>Dati stradali (c) OpenStreetMap contributors, ODbL</text></link>",
           "  </metadata>"]
    for m in d["markers"]:
        sym = "Summit" if m["kind"] == "pass" else "Flag, Blue"
        out += [f'  <wpt lat="{m["lat"]:.6f}" lon="{m["lon"]:.6f}">',
                f"    <ele>{m['ele']}</ele>",
                f"    <name>{escape(m['name'])}</name>",
                f"    <desc>{escape(m['name'])}, {m['ele']} m, km {m['km']}</desc>",
                f"    <sym>{sym}</sym>",
                "  </wpt>"]
    # A route of shaping points for navigators that recalculate (Garmin Zumo,
    # TomTom Rider): every via point, so the recalculation keeps to the pass.
    out += ["  <rte>", f"    <name>{escape(d['title'])} (percorso)</name>"]
    for v, (lon, lat) in zip(built["via"], built["snapped"]):
        out += [f'    <rtept lat="{lat:.6f}" lon="{lon:.6f}"><name>{escape(v["name"])}</name></rtept>']
    out += ["  </rte>",
            "  <trk>", f"    <name>{escape(d['title'])}</name>",
            "    <type>motorcycling</type>", "    <trkseg>"]
    for (lon, lat), ele in zip(built["points"], built["eles"]):
        out.append(f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{ele:.0f}</ele></trkpt>')
    out += ["    </trkseg>", "  </trk>", "</gpx>", ""]
    return "\n".join(out)


def main():
    rides = json.load(open(os.path.join(HERE, "rides.json")))["rides"]
    store = json.load(open(os.path.join(SITE, "store.json")))
    brand = store["brand"]
    os.makedirs(os.path.join(SITE, "tracks"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    os.makedirs(PRIVATE, exist_ok=True)

    graphs, terrain, site_rides = {}, Terrain(), []
    for ride in rides:
        region = ride["region"]
        if region not in graphs:
            graphs[region] = Graph(region)
        built = build_ride(ride, graphs[region], terrain)
        d = built["data"]
        free = store["products"].get(ride["slug"], {}).get("free", False)
        folder = os.path.join(SITE, "tracks") if free else PRIVATE
        path = os.path.join(folder, f"{ride['slug']}.gpx")
        with open(path, "w", encoding="utf-8") as f:
            f.write(gpx(ride, built, brand))
        print(f"{d['title']}: {d['km']} km, +{d['ascent']} m, max {d['maxEle']} m, "
              f"{d['minutes']} min, {d['trackPoints']} pts, roads {d['roads']}, "
              f"closures {d['closures']} -> {os.path.relpath(path, ROOT)}")
        site_rides.append(d)

    with open(os.path.join(SITE, "data", "rides.json"), "w", encoding="utf-8") as f:
        json.dump({"rides": site_rides}, f, ensure_ascii=False, separators=(",", ":"))

    for b in store["bundles"]:
        path = os.path.join(PRIVATE, f"{b['slug']}.zip")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for slug in b["rides"]:
                z.write(os.path.join(PRIVATE, f"{slug}.gpx"), f"{slug}.gpx")
        print(f"bundle {b['slug']}: {len(b['rides'])} tracks -> {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
