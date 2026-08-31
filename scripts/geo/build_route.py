import math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_TS = os.path.join(REPO_ROOT, "src", "SwissTour", "geoData.ts")

# Projected waypoints (from previous script's output), map units (2000 x 1283.03)
W = {
    "airolo":    (1170.62, 825.75),
    "gotthard":  (1150.95, 807.94),
    "andermatt": (1162.32, 757.89),
    "furka":     (1083.57, 797.47),
    "oberwald":  (1054.91, 822.92),
    "ulrichen":  (1032.86, 844.19),
    "nufenen":   (1073.90, 858.32),
    "allacqua":  (1110.36, 852.62),
    "bedretto":  (1128.56, 844.19),
}

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
        x = ax + dx * t + px * side * a_amp
        y = ay + dy * t + py * side * a_amp
        pts.append((x, y))
    return pts

def catmull_rom_to_bezier(points):
    """points: list of (x,y). Returns SVG path 'd' string (M + C segments)."""
    pts = [points[0]] + points + [points[-1]]
    d = f"M{points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d += f"C{c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f}"
    return d

def path_length(points):
    total = 0.0
    for i in range(1, len(points)):
        total += math.hypot(points[i][0]-points[i-1][0], points[i][1]-points[i-1][1])
    return total

# Segment A: Airolo -> (Tremola zigzag) -> Gotthard -> Andermatt -> (Furka east ramp zigzag) -> Furka
segA_points = [W["airolo"]]
segA_points += zigzag(W["airolo"], W["gotthard"], 0.12, 0.6, 7, amp=7.5)
segA_points += [W["gotthard"], W["andermatt"]]
segA_points += zigzag(W["andermatt"], W["furka"], 0.5, 0.88, 6, amp=6.5)
segA_points += [W["furka"]]

# Segment B: Furka -> Oberwald -> Ulrichen -> (Nufenen north-ramp zigzag) -> Nufenenpass
segB_points = [W["furka"], W["oberwald"], W["ulrichen"]]
segB_points += zigzag(W["ulrichen"], W["nufenen"], 0.28, 0.85, 5, amp=5.5)
segB_points += [W["nufenen"]]

# Segment C: Nufenenpass -> (south-ramp zigzag) -> All'Acqua -> Bedretto -> Airolo.
# The Val Bedretto descent, which closes the loop back to where it started.
segC_points = [W["nufenen"]]
segC_points += zigzag(W["nufenen"], W["allacqua"], 0.12, 0.58, 5, amp=5.0)
segC_points += [W["allacqua"], W["bedretto"], W["airolo"]]

dA = catmull_rom_to_bezier(segA_points)
dB = catmull_rom_to_bezier(segB_points)
dC = catmull_rom_to_bezier(segC_points)

lenA = path_length(segA_points)
lenB = path_length(segB_points)
lenC = path_length(segC_points)

print("segA points", len(segA_points), "approx length (map units)", round(lenA, 1))
print("segB points", len(segB_points), "approx length (map units)", round(lenB, 1))
print("segC points", len(segC_points), "approx length (map units)", round(lenC, 1))

def points_literal(points):
    return "[" + ",".join(f"[{x:.2f},{y:.2f}]" for x, y in points) + "]"

out = []
out.append("\nexport type RouteSegment = {\n  id: string;\n  d: string;\n  points: [number, number][];\n};\n")
out.append("export const routeSegments: RouteSegment[] = [")
out.append(f'  {{ id: "airolo-furka", d: "{dA}", points: {points_literal(segA_points)} }},')
out.append(f'  {{ id: "furka-nufenen", d: "{dB}", points: {points_literal(segB_points)} }},')
out.append(f'  {{ id: "nufenen-airolo", d: "{dC}", points: {points_literal(segC_points)} }},')
out.append("];\n")

with open(OUT_TS, "a") as f:
    f.write("\n".join(out) + "\n")

print("appended route segments to geoData.ts")

all_route_pts = segA_points + segB_points + segC_points
xs = [p[0] for p in all_route_pts]
ys = [p[1] for p in all_route_pts]
pad = 30
bbox = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
print("region bbox", bbox)

with open(OUT_TS, "a") as f:
    f.write("\nexport type BBox = { x0: number; y0: number; x1: number; y1: number };\n")
    f.write(f"export const REGION_BBOX: BBox = {{ x0: {bbox[0]:.2f}, y0: {bbox[1]:.2f}, x1: {bbox[2]:.2f}, y1: {bbox[3]:.2f} }};\n")
    f.write(f"export const FULL_BBOX: BBox = {{ x0: 0, y0: 0, x1: {2000}, y1: {1283.03} }};\n")


# --- Fork composition -------------------------------------------------------
# Two ways out of Airolo that meet again in the Goms: over the Gotthard and
# the Furka down to Oberwald, or up the Val Bedretto and over the Novena to
# Ulrichen. Both are built from the same road geometry as the loop above,
# just re-cut so each branch starts at Airolo.

def reverse(points):
    return list(reversed(points))

branch_north_points = segA_points + [W["oberwald"]]

nufenen_north_ramp = (
    [W["ulrichen"]]
    + zigzag(W["ulrichen"], W["nufenen"], 0.28, 0.85, 5, amp=5.5)
    + [W["nufenen"]]
)
branch_novena_points = reverse(segC_points) + reverse(nufenen_north_ramp)[1:]

# The short valley road that ties the two arrival points together.
goms_link_points = [W["oberwald"], W["ulrichen"]]

fork_branches = [
    ("gottardo-furka", branch_north_points),
    ("novena", branch_novena_points),
    ("goms-link", goms_link_points),
]

fork_out = ["\nexport const forkBranches: RouteSegment[] = ["]
for bid, pts in fork_branches:
    fork_out.append(
        f'  {{ id: "{bid}", d: "{catmull_rom_to_bezier(pts)}", points: {points_literal(pts)} }},'
    )
fork_out.append("];\n")

fork_pts = branch_north_points + branch_novena_points
fxs = [p[0] for p in fork_pts]
fys = [p[1] for p in fork_pts]
fbox = (min(fxs) - pad, min(fys) - pad, max(fxs) + pad, max(fys) + pad)
fork_out.append(
    f"export const FORK_BBOX: BBox = {{ x0: {fbox[0]:.2f}, y0: {fbox[1]:.2f}, "
    f"x1: {fbox[2]:.2f}, y1: {fbox[3]:.2f} }};\n"
)

with open(OUT_TS, "a") as f:
    f.write("\n".join(fork_out) + "\n")

def cumfrac(points, idx):
    return path_length(points[: idx + 1]) / path_length(points)

print("branch north points", len(branch_north_points),
      "length", round(path_length(branch_north_points), 1))
for label, idx in [("gotthard", 8), ("andermatt", 9), ("furka", 16), ("oberwald", 17)]:
    print("  north", label, round(cumfrac(branch_north_points, idx), 3))

print("branch novena points", len(branch_novena_points),
      "length", round(path_length(branch_novena_points), 1))
for label, idx in [("bedretto", 1), ("allacqua", 2), ("nufenen", 8), ("ulrichen", 14)]:
    print("  novena", label, round(cumfrac(branch_novena_points, idx), 3))

print("fork bbox", fbox)
