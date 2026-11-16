"""Download places (restaurants, hotels, viewpoints...) around each ride.

Same approach as fetch_roads.py, on Overture's places theme: names, contact
details (phone, email, website), category and an operating status, compiled
from several open sources.

    python scripts/tracks/fetch_places.py

Writes scripts/tracks/.cache/places-<region>.parquet (git-ignored).
"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq

from fetch_roads import CACHE, REGIONS, RELEASE, BUCKET, overlaps

PREFIX = f"release/{RELEASE}/theme=places/type=place/"
COLUMNS = ["id", "names", "basic_category", "taxonomy", "confidence", "operating_status",
           "phones", "emails", "websites", "addresses", "sources", "geometry", "bbox"]

s3 = pafs.S3FileSystem(anonymous=True, region="us-west-2")


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
        st = {k: (rg.column(j).statistics.min if k in ("xmin", "ymin") else rg.column(j).statistics.max)
              for k, j in cols.items()}
        if overlaps(st, box):
            hits.append(i)
    return hits


def read_region(path, groups, box):
    t = pq.ParquetFile(path, filesystem=s3).read_row_groups(groups, columns=COLUMNS)
    x0, y0, x1, y1 = box
    b = t.column("bbox")
    mask = pc.and_(
        pc.and_(pc.greater_equal(pc.struct_field(b, "xmin"), x0), pc.less_equal(pc.struct_field(b, "xmax"), x1)),
        pc.and_(pc.greater_equal(pc.struct_field(b, "ymin"), y0), pc.less_equal(pc.struct_field(b, "ymax"), y1)))
    return t.filter(mask)


def main():
    os.makedirs(CACHE, exist_ok=True)
    infos = s3.get_file_info(pafs.FileSelector(f"{BUCKET}/{PREFIX}"))
    files = sorted(i.path for i in infos if i.path.endswith(".parquet"))
    for region, box in REGIONS.items():
        out = os.path.join(CACHE, f"places-{region}.parquet")
        if os.path.exists(out) and "--force" not in sys.argv:
            print(f"{region}: cached")
            continue
        with ThreadPoolExecutor(16) as ex:
            groups = list(ex.map(lambda p: row_groups_for(p, box), files))
        jobs = [(p, g) for p, g in zip(files, groups) if g]
        with ThreadPoolExecutor(8) as ex:
            parts = list(ex.map(lambda j: read_region(j[0], j[1], box), jobs))
        table = pa.concat_tables(parts)
        pq.write_table(table, out, compression="zstd")
        print(f"{region}: {table.num_rows} places -> {out}")


if __name__ == "__main__":
    main()
