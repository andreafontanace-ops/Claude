"""Download the road network around each ride from Overture Maps.

Overture's transportation theme is OpenStreetMap's road network, republished
as GeoParquet on a public S3 bucket. Each file carries per-row-group bounding
boxes, so only the few row groups that overlap a region are fetched: a couple
of hundred megabytes instead of the 70 GB of the whole planet.

    pip install -r scripts/tracks/requirements.txt
    python scripts/tracks/fetch_roads.py

Writes scripts/tracks/.cache/roads-<region>.parquet (git-ignored).
Data (c) OpenStreetMap contributors, ODbL; distributed by Overture Maps.
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, ".cache")
RELEASE = "2026-10-21.0"
BUCKET = "overturemaps-us-west-2"
PREFIX = f"release/{RELEASE}/theme=transportation/type=segment/"

# lon_min, lat_min, lon_max, lat_max: generous boxes around every ride.
REGIONS = {
    "svizzera": (8.15, 46.45, 8.70, 46.78),
    "alpi-sud": (6.55, 44.28, 7.35, 45.32),
}

# Roads a touring motorcycle would ride. Motorways are left out on purpose:
# the point of every ride is the pass road, never the tunnel under it.
CLASSES = ["trunk", "primary", "secondary", "tertiary", "unclassified",
           "residential", "living_street"]
COLUMNS = ["id", "names", "class", "connectors", "access_restrictions",
           "road_surface", "road_flags", "routes", "geometry", "bbox"]

s3 = pafs.S3FileSystem(anonymous=True, region="us-west-2")


def list_files():
    infos = s3.get_file_info(pafs.FileSelector(f"{BUCKET}/{PREFIX}"))
    return sorted(i.path for i in infos if i.path.endswith(".parquet"))


def overlaps(stats, box):
    x0, y0, x1, y1 = box
    return not (stats["xmax"] < x0 or stats["xmin"] > x1 or
                stats["ymax"] < y0 or stats["ymin"] > y1)


def row_groups_for(path, box):
    meta = pq.ParquetFile(path, filesystem=s3).metadata
    cols = {}
    for j in range(meta.num_columns):
        name = meta.row_group(0).column(j).path_in_schema
        if name in ("bbox.xmin", "bbox.xmax", "bbox.ymin", "bbox.ymax"):
            cols[name.split(".")[1]] = j
    hits = []
    for i in range(meta.num_row_groups):
        rg = meta.row_group(i)
        st = {}
        for key, j in cols.items():
            s = rg.column(j).statistics
            st[key] = s.min if key in ("xmin", "ymin") else s.max
        if overlaps(st, box):
            hits.append(i)
    return hits


def read_region(path, groups, box):
    f = pq.ParquetFile(path, filesystem=s3)
    t = f.read_row_groups(groups, columns=COLUMNS + ["subtype"])
    x0, y0, x1, y1 = box
    b = t.column("bbox")
    mask = pc.and_(
        pc.and_(pc.less_equal(pc.struct_field(b, "xmin"), x1),
                pc.greater_equal(pc.struct_field(b, "xmax"), x0)),
        pc.and_(pc.less_equal(pc.struct_field(b, "ymin"), y1),
                pc.greater_equal(pc.struct_field(b, "ymax"), y0)))
    mask = pc.and_(mask, pc.equal(t.column("subtype"), "road"))
    mask = pc.and_(mask, pc.is_in(t.column("class"), pa.array(CLASSES)))
    return t.filter(mask).drop_columns(["subtype"])


def main():
    os.makedirs(CACHE, exist_ok=True)
    files = list_files()
    print(f"{len(files)} segment files in release {RELEASE}")
    for region, box in REGIONS.items():
        out = os.path.join(CACHE, f"roads-{region}.parquet")
        if os.path.exists(out) and "--force" not in sys.argv:
            print(f"{region}: cached")
            continue
        with ThreadPoolExecutor(16) as ex:
            groups = list(ex.map(lambda p: row_groups_for(p, box), files))
        jobs = [(p, g) for p, g in zip(files, groups) if g]
        print(f"{region}: {sum(len(g) for _, g in jobs)} row groups in {len(jobs)} files")
        with ThreadPoolExecutor(8) as ex:
            parts = list(ex.map(lambda j: read_region(j[0], j[1], box), jobs))
        table = pa.concat_tables(parts)
        pq.write_table(table, out, compression="zstd")
        print(f"{region}: {table.num_rows} road segments -> {out}")


if __name__ == "__main__":
    main()
