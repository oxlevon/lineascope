"""
check_grid.py -- verify all downloaded rasters are on the same grid.

Usage:
    python scripts/check_grid.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import glob
import numpy as np
import rasterio

from src.config import GRID, CRS_PROJECTED, RAW

EXPECT_BOUNDS = (GRID["x_min"], GRID["y_min"], GRID["x_max"], GRID["y_max"])
EXPECT_EPSG = int(CRS_PROJECTED.split(":")[1])


def check() -> int:
    problems = 0
    files = sorted(glob.glob(str(RAW / "*.tif")))

    if not files:
        print("No .tif files found in", RAW)
        print("Download them from Google Drive first.")
        return 1

    for f in files:
        with rasterio.open(f) as r:
            res = r.res[0]
            b = tuple(round(v) for v in r.bounds)
            arr = r.read(masked=True)
            empty = float(np.mean(arr.mask)) if np.ma.is_masked(arr) else 0.0

            print(Path(f).name)
            print(f"  CRS: {r.crs} | pixel: {res} m | "
                  f"size: {r.width} x {r.height} | bands: {r.count}")
            print(f"  bounds: {b} | empty pixels: {100 * empty:.1f} %")

            if r.crs.to_epsg() != EXPECT_EPSG:
                print("  ! wrong CRS")
                problems += 1
            if b != EXPECT_BOUNDS:
                print("  ! bounds differ from plan")
                problems += 1
            if empty > 0.05:
                print("  ! more than 5% empty")
                problems += 1

    print()
    if problems == 0:
        print("All good")
    else:
        print(f"{problems} problem(s) found")
    return problems


if __name__ == "__main__":
    sys.exit(check())