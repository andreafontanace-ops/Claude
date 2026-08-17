import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
CTH_PATH = os.path.join(HERE, "switzerland_cantons.geojson")
OUT_TS = os.path.join(REPO_ROOT, "src", "SwissTour", "geoData.ts")

d = json.load(open(CTH_PATH))
features = d["features"]

# Collect all coordinates to compute bbox (country-wide)
all_pts = []
for f in features:
    geom = f["geometry"]
    polys = geom["coordinates"]  # MultiPolygon: list of polygons, each a list of rings
    for poly in polys:
        for ring in poly:
            for lon, lat in ring:
                all_pts.append((lon, lat))

lon_min = min(p[0] for p in all_pts)
lon_max = max(p[0] for p in all_pts)
lat_min = min(p[1] for p in all_pts)
lat_max = max(p[1] for p in all_pts)
lat0 = (lat_min + lat_max) / 2
cos0 = math.cos(math.radians(lat0))

MAP_WIDTH = 2000

def raw_xy(lon, lat):
    X = (lon - lon_min) * cos0
    Y = (lat - lat_min)
    return X, Y

Xmin, Ymin = raw_xy(lon_min, lat_min)
Xmax, Ymax = raw_xy(lon_max, lat_max)
scale = MAP_WIDTH / (Xmax - Xmin)
MAP_HEIGHT = (Ymax - Ymin) * scale

def project(lon, lat):
    X, Y = raw_xy(lon, lat)
    px = (X - Xmin) * scale
    py = MAP_HEIGHT - (Y - Ymin) * scale
    return px, py

def ring_to_path(ring):
    parts = []
    for i, (lon, lat) in enumerate(ring):
        x, y = project(lon, lat)
        cmd = "M" if i == 0 else "L"
        parts.append(f"{cmd}{x:.2f},{y:.2f}")
    parts.append("Z")
    return "".join(parts)

canton_entries = []
for f in features:
    name = f["properties"]["name"]
    geom = f["geometry"]
    subpaths = []
    for poly in geom["coordinates"]:
        for ring in poly:
            subpaths.append(ring_to_path(ring))
    dattr = "".join(subpaths)
    canton_entries.append((name, dattr))

with open(OUT_TS, "w") as out:
    out.write("// Auto-generated from Swiss canton boundary data (click_that_hood, CC0/public domain style open dataset).\n")
    out.write("// Equirectangular projection, longitude corrected by cos(latitude) for correct aspect ratio.\n")
    out.write("// Do not hand-edit; regenerate via scripts/build_geo.py if source data changes.\n\n")
    out.write(f"export const MAP_WIDTH = {MAP_WIDTH};\n")
    out.write(f"export const MAP_HEIGHT = {MAP_HEIGHT:.2f};\n\n")
    out.write("export type CantonShape = {\n  name: string;\n  d: string;\n};\n\n")
    out.write("export const cantons: CantonShape[] = [\n")
    for name, dattr in canton_entries:
        safe_name = name.replace("\\", "\\\\").replace('"', '\\"')
        out.write(f'  {{ name: "{safe_name}", d: "{dattr}" }},\n')
    out.write("];\n\n")

    out.write("export type Waypoint = {\n  id: string;\n  name: string;\n  subtitle?: string;\n  lon: number;\n  lat: number;\n  x: number;\n  y: number;\n  elevation: number;\n};\n\n")

    waypoints = [
        ("airolo", "Airolo", None, 8.612375, 46.528607, 1142),
        ("gotthard", "Passo del San Gottardo", None, 8.56778, 46.55625, 2106),
        ("andermatt", "Andermatt", None, 8.593563, 46.633912, 1436),
        ("furka", "Furkapass", None, 8.41500, 46.57250, 2429),
        ("oberwald", "Oberwald", None, 8.350, 46.533, 1370),
        ("ulrichen", "Ulrichen", None, 8.300, 46.500, 1345),
        ("nufenen", "Nufenenpass", "Passo della Novena", 8.39306, 46.47806, 2478),
    ]
    out.write("export const waypoints: Waypoint[] = [\n")
    for wid, name, sub, lon, lat, elev in waypoints:
        x, y = project(lon, lat)
        sub_field = f'"{sub}"' if sub else "undefined"
        out.write(f'  {{ id: "{wid}", name: "{name}", subtitle: {sub_field}, lon: {lon}, lat: {lat}, x: {x:.2f}, y: {y:.2f}, elevation: {elev} }},\n')
    out.write("];\n")

print("lon range", lon_min, lon_max)
print("lat range", lat_min, lat_max)
print("MAP_HEIGHT", MAP_HEIGHT)
for wid, name, sub, lon, lat, elev in waypoints:
    print(name, project(lon, lat))
