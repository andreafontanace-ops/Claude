#!/usr/bin/env python3
"""Real road geometry from Overture Maps, routed through a list of stops.

Overture's transportation theme is OpenStreetMap's road network, published
as GeoParquet on a public S3 bucket - which this environment can reach when
the OSM servers themselves are blocked. This reads the road segments inside a
box, builds the road graph from their connectors and finds the shortest drive
through the stops, favouring the road named by --prefer (so a route "over the
SS461" stays on it rather than cutting across on a lane). The curves are the
mapped ones: nothing is smoothed or invented.

    python3 scripts/geo/overture_route.py OUT.json \\
        --bbox 9.12,44.70,9.45,44.86 --prefer 461 \\
        --stop bobbio=9.3818,44.7697 --stop penice=9.3283,44.7973 \\
        --stop varzi=9.1969,44.8235

Writes the same JSON shape screenshot_track.py does (lonlat, stops, km), so
the film build scripts read either. Needs pyarrow and shapely.
"""
import argparse, collections, heapq, json, math, os, sys

import pyarrow.dataset as ds
import pyarrow.fs as fs
import shapely
import shapely.ops

BUCKET = "overturemaps-us-west-2"
RELEASE = "2026-09-23.1"
DRIVABLE = {"motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
            "residential", "living_street", "service", "unknown"}
MAJOR = {"motorway", "trunk", "primary", "secondary", "tertiary"}


def metres(p, q):
    lon1, lat1, lon2, lat2 = map(math.radians, (*p, *q))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(h))


def s3():
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    ca = "/root/.ccr/ca-bundle.crt"
    kw = dict(anonymous=True, region="us-west-2")
    if proxy:
        kw["proxy_options"] = proxy
    if os.path.exists(ca):
        kw["tls_ca_file_path"] = ca
    return fs.S3FileSystem(**kw)


def in_box(box):
    x0, y0, x1, y1 = box
    return ((ds.field("bbox", "xmin") > x0) & (ds.field("bbox", "xmax") < x1)
            & (ds.field("bbox", "ymin") > y0) & (ds.field("bbox", "ymax") < y1))


def fetch_segments(box, release):
    d = ds.dataset(f"{BUCKET}/release/{release}/theme=transportation/type=segment/",
                   filesystem=s3(), format="parquet")
    t = d.to_table(columns=["id", "subtype", "class", "routes", "connectors", "geometry"],
                   filter=in_box(box) & (ds.field("subtype") == "road"))
    return t.to_pylist()


def route_names(seg):
    return " ".join((r.get("ref") or "") + " " + (r.get("name") or "") for r in (seg["routes"] or []))


def build_graph(segments, prefer):
    adj = collections.defaultdict(list)
    where = {}
    for seg in segments:
        if seg["class"] not in DRIVABLE or not seg["connectors"]:
            continue
        g = shapely.from_wkb(seg["geometry"])
        preferred = bool(prefer) and prefer in route_names(seg)
        # Staying on the named road is free; other main roads cost a little
        # more, lanes and tracks a lot, so a detour has to be a real saving.
        cost = 1.0 if preferred else (1.3 if seg["class"] in MAJOR else 3.0)
        cons = sorted(seg["connectors"], key=lambda c: c["at"])
        for a, b in zip(cons, cons[1:]):
            piece = shapely.ops.substring(g, a["at"] * g.length, b["at"] * g.length)
            pts = list(piece.coords) if piece.geom_type == "LineString" else [piece.coords[0]] * 2
            length = sum(metres(p, q) for p, q in zip(pts, pts[1:]))
            ia, ib = a["connector_id"], b["connector_id"]
            where[ia], where[ib] = pts[0], pts[-1]
            adj[ia].append((ib, length * cost, length, pts, preferred))
            adj[ib].append((ia, length * cost, length, pts[::-1], preferred))
    return adj, where


def shortest(adj, s, t):
    dist, prev, heap = {s: 0.0}, {}, [(0.0, s)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == t:
            break
        if d > dist[u]:
            continue
        for v, w, length, pts, pref in adj[u]:
            if d + w < dist.get(v, math.inf):
                dist[v] = d + w
                prev[v] = (u, length, pts, pref)
                heapq.heappush(heap, (d + w, v))
    if t not in prev and s != t:
        sys.exit("no road connects two of the stops inside the box - widen --bbox")
    legs, n = [], t
    while n != s:
        u, length, pts, pref = prev[n]
        legs.append((length, pts, pref))
        n = u
    return legs[::-1]


def rdp(points, eps_m):
    """Drops points closer than eps_m to the chord - the mapped bends stay."""
    if len(points) < 3:
        return points
    lat0 = math.radians(points[0][1])
    xy = [(p[0] * 111320 * math.cos(lat0), p[1] * 110540) for p in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = xy[i], xy[j]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1e-9
        best, k = -1.0, None
        for m in range(i + 1, j):
            d = abs(dy * (xy[m][0] - x1) - dx * (xy[m][1] - y1)) / n
            if d > best:
                best, k = d, m
        if k is not None and best > eps_m:
            keep[k] = True
            stack += [(i, k), (k, j)]
    return [p for p, kp in zip(points, keep) if kp]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--bbox", required=True, help="lon0,lat0,lon1,lat1")
    ap.add_argument("--stop", action="append", required=True, help="NAME=LON,LAT, in driving order")
    ap.add_argument("--prefer", default="", help="text in the route ref/name to stay on, e.g. 461")
    ap.add_argument("--release", default=RELEASE)
    ap.add_argument("--simplify", type=float, default=3.0, help="RDP tolerance in metres")
    args = ap.parse_args()

    box = tuple(float(v) for v in args.bbox.split(","))
    stops = []
    for s in args.stop:
        name, ll = s.split("=")
        stops.append((name, tuple(float(v) for v in ll.split(","))))

    segments = fetch_segments(box, args.release)
    adj, where = build_graph(segments, args.prefer)
    print(f"{len(segments)} road segments, {len(where)} junctions")

    snapped = []
    for name, ll in stops:
        node = min(where, key=lambda n: metres(where[n], ll))
        print(f"  {name:10s} snapped {metres(where[node], ll):5.0f} m onto the road")
        snapped.append((name, node))

    lonlat, stop_at, km, km_pref = [], {}, 0.0, 0.0
    for (na, a), (nb, b) in zip(snapped, snapped[1:]):
        stop_at.setdefault(na, len(lonlat))
        leg_km = leg_pref = 0.0
        for length, pts, pref in shortest(adj, a, b):
            lonlat += pts if not lonlat else pts[1:]
            leg_km += length / 1000
            leg_pref += length / 1000 if pref else 0
        print(f"  {na} -> {nb}: {leg_km:.2f} km, {leg_pref:.2f} on '{args.prefer}'")
        km += leg_km; km_pref += leg_pref
        stop_at[nb] = len(lonlat) - 1

    # Simplify each leg on its own so every stop stays an exact vertex.
    order = [stop_at[n] for n, _ in snapped]
    simple, stops_out = [], {}
    for (n, _), i, j in zip(snapped, order, order[1:]):
        leg = rdp(lonlat[i:j + 1], args.simplify)
        stops_out[n] = list(leg[0])
        simple += leg if not simple else leg[1:]
    stops_out[snapped[-1][0]] = list(simple[-1])

    out = {
        "source": f"Overture Maps {args.release} transportation segments (OpenStreetMap), "
                  f"routed by scripts/geo/overture_route.py",
        "km": round(km, 2),
        "km_on_preferred": round(km_pref, 2),
        "prefer": args.prefer,
        "stops": {k: [round(v[0], 6), round(v[1], 6)] for k, v in stops_out.items()},
        "lonlat": [[round(x, 6), round(y, 6)] for x, y in simple],
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {args.out}: {km:.2f} km, {len(simple)} points (from {len(lonlat)})")


if __name__ == "__main__":
    main()
