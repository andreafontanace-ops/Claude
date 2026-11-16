"""The guide that comes with each ride: where to stop for photos, where to
eat, where to sleep, all placed on the route with their kilometre.

Restaurants and hotels are picked from Overture Maps places (compiled from
Meta, Microsoft, Foursquare, AllThePlaces and others, open licences), close
to the road and with a phone or email to book. They are a shortlist, not a
recommendation: a place becomes "Consigliato", with a review, only once the
author has been there and says so in reviews.json.
"""
import json
import os
import urllib.parse
from collections import defaultdict

import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")

# basic_category -> (Italian label, weight)
EAT = {"restaurant": ("Ristorante", 1.0), "casual_eatery": ("Trattoria e snack", 0.8),
       "cafe": ("Caffè", 0.6)}
SLEEP = {"hotel": ("Hotel", 1.0), "bed_and_breakfast": ("B&B", 0.85),
         "lodging": ("Alloggio", 0.7), "resort": ("Resort", 0.6)}
MAX_EAT, MAX_SLEEP = 6, 5
EAT_RADIUS, SLEEP_RADIUS = 250, 450   # metres from the road
MIN_CONFIDENCE = 0.8


def load_places(region):
    path = os.path.join(CACHE, f"places-{region}.parquet")
    return pq.read_table(path).to_pylist() if os.path.exists(path) else []


def load_reviews():
    path = os.path.join(HERE, "reviews.json")
    if not os.path.exists(path):
        return {"places": {}, "exclude": []}
    data = json.load(open(path, encoding="utf-8"))
    return {"places": data.get("places", {}), "exclude": data.get("exclude", [])}


class Track:
    """The ride resampled every 50 m, with a coarse grid for nearest lookups."""

    def __init__(self, samples, haversine):
        self.samples = samples              # (km, lon, lat, ele)
        self.hav = haversine
        self.grid = defaultdict(list)
        for i, s in enumerate(samples):
            self.grid[(int(s[1] * 200), int(s[2] * 200))].append(i)

    def nearest(self, lon, lat):
        gx, gy = int(lon * 200), int(lat * 200)
        best, best_d = None, float("inf")
        for r in range(0, 4):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    for i in self.grid.get((gx + dx, gy + dy), ()):
                        s = self.samples[i]
                        d = self.hav(lon, lat, s[1], s[2])
                        if d < best_d:
                            best, best_d = i, d
            if best is not None:
                break
        return best, best_d


def centre(p):
    b = p["bbox"]
    return (b["xmin"] + b["xmax"]) / 2, (b["ymin"] + b["ymax"]) / 2


def maps_link(name, locality, lat, lon):
    q = f"{name} {locality}".strip() if locality else f"{lat:.5f},{lon:.5f}"
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def pick_places(places, track, markers, kinds, radius, limit, reviews):
    """Shortlist places of the given kinds, spread along the route."""
    stops = [(m["km"]) for m in markers]
    excluded = set(reviews["exclude"])
    seen, cands = [], []
    for p in places:
        cat = p["basic_category"]
        if cat not in kinds or p["id"] in excluded:
            continue
        if p["operating_status"] == "permanently_closed":
            continue
        name = (p["names"] or {}).get("primary")
        if not name or not (p["phones"] or p["emails"]):
            continue
        review = reviews["places"].get(p["id"], {})
        if p["confidence"] < MIN_CONFIDENCE and not review:
            continue
        lon, lat = centre(p)
        i, d = track.nearest(lon, lat)
        if i is None or d > radius:
            continue
        km = track.samples[i][0]
        label, weight = kinds[cat]
        near_stop = any(abs(km - s) < 1.5 for s in stops)
        score = weight * p["confidence"] * (1.25 if p["emails"] else 1.0) \
            * (1.4 if near_stop else 1.0) - d / 2000
        if review.get("recommended"):
            score += 10
        cands.append((score, km, d, p, label, lon, lat, review))

    # Spread the shortlist: the best place in each stretch of road first,
    # then the best of the rest, never two within 2 km of each other.
    total = track.samples[-1][0]
    bins = defaultdict(list)
    for c in cands:
        bins[min(limit - 1, int(c[1] / total * limit))].append(c)
    chosen = []

    def clash(c):
        key = c[3]["names"]["primary"].lower()
        return any(key == o[3]["names"]["primary"].lower() or abs(o[1] - c[1]) < 2 for o in chosen)

    for b in sorted(bins):
        for c in sorted(bins[b], key=lambda c: -c[0]):
            if not clash(c):
                chosen.append(c)
                break
    for c in sorted(cands, key=lambda c: -c[0]):
        if len(chosen) >= limit:
            break
        if c not in chosen and not clash(c):
            chosen.append(c)
    chosen = sorted(chosen[:limit], key=lambda c: c[1])

    out = []
    for score, km, d, p, label, lon, lat, review in chosen:
        addr = (p["addresses"] or [{}])[0] or {}
        locality = addr.get("locality") or ""
        address = ", ".join(x for x in [addr.get("freeform"), " ".join(
            x for x in [addr.get("postcode"), locality] if x)] if x)
        out.append({
            "id": p["id"], "name": p["names"]["primary"], "type": label,
            "km": round(km, 1), "offRoad": int(round(d / 10) * 10),
            "lon": round(lon, 6), "lat": round(lat, 6),
            "address": address, "phone": (p["phones"] or [None])[0],
            "email": (p["emails"] or [None])[0], "website": (p["websites"] or [None])[0],
            "reviews": maps_link(p["names"]["primary"], locality, lat, lon),
            "recommended": bool(review.get("recommended")),
            "rating": review.get("rating"), "review": review.get("review", ""),
            "sources": sorted({s["dataset"] for s in (p["sources"] or []) if s["dataset"] != "Overture"}),
        })
    return out


def place_spots(ride, track, markers, places, road_points):
    """Resolve each panoramic stop to a point on the road."""
    out = []
    by_name = defaultdict(list)
    for p in places:
        n = (p["names"] or {}).get("primary")
        if n:
            by_name[n.lower()].append(p)
    for s in ride.get("spots", []):
        idx = None
        if s.get("pass"):
            m = next((m for m in markers if m["name"] == s["pass"]), None)
            if m:
                idx, _ = track.nearest(m["lon"], m["lat"])
        elif s.get("anchor"):
            best = None
            for p in by_name.get(s["anchor"].lower(), []):
                i, d = track.nearest(*centre(p))
                if i is not None and d < 700 and (best is None or d < best[1]):
                    best = (i, d)
            idx = best[0] if best else None
        elif s.get("roadTop"):
            # The highest point of a named road: the top of the Tremola.
            hits = [p for p in road_points if s["roadTop"].lower() in p[3].lower()]
            if hits:
                top = max(hits, key=lambda p: p[2])
                idx, _ = track.nearest(top[0], top[1])
        elif "lon" in s:
            i, d = track.nearest(s["lon"], s["lat"])
            idx = i if d < 600 else None
        if idx is None:
            print(f"  ! spot '{s['name']}' not placed on {ride['slug']}")
            continue
        km, lon, lat, ele = track.samples[idx]
        out.append({"name": s["name"], "text": s["text"], "km": round(km, 1),
                    "lon": round(lon, 6), "lat": round(lat, 6), "ele": int(round(ele)),
                    "map": f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"})
    return sorted(out, key=lambda x: x["km"])


def build(ride, samples, markers, road_points, region, haversine, cache={}):
    """road_points: (lon, lat, ele, road name) for every track point."""
    if region not in cache:
        cache[region] = load_places(region)
    places = cache[region]
    reviews = load_reviews()
    track = Track(samples, haversine)
    return {
        "season": ride.get("season", {}),
        "spots": place_spots(ride, track, markers, places, road_points),
        "eat": pick_places(places, track, markers, EAT, EAT_RADIUS, MAX_EAT, reviews),
        "sleep": pick_places(places, track, markers, SLEEP, SLEEP_RADIUS, MAX_SLEEP, reviews),
    }
