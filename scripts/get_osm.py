"""
get_osm.py -- download OpenStreetMap roads, waterways, buildings for the AOI.

Usage:
    python scripts/get_osm.py

Requires: osmnx >= 2.0
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import osmnx as ox

from src.config import BBOX_WGS84, CRS_PROJECTED, OSM

# osmnx 2.x uses (west, south, east, north) order
BBOX = (
    BBOX_WGS84["west"],
    BBOX_WGS84["south"],
    BBOX_WGS84["east"],
    BBOX_WGS84["north"],
)

LAYERS = {
    "roads":     {"highway": True},
    "waterways": {"waterway": True},
    "buildings": {"building": True},
}


def download() -> None:
    OSM.mkdir(parents=True, exist_ok=True)

    for name, tags in LAYERS.items():
        print(f"Downloading {name}...")
        try:
            gdf = ox.features_from_bbox(BBOX, tags=tags)
        except Exception as e:
            print(f"  ! Failed to download {name}: {e}")
            continue

        if name == "buildings":
            gdf = gdf[gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
        else:
            gdf = gdf[gdf.geom_type.isin(["LineString", "MultiLineString"])]

        keep = [c for c in ("highway", "waterway", "name") if c in gdf.columns]
        gdf = gdf[keep + ["geometry"]].reset_index(drop=True)
        gdf = gdf.to_crs(CRS_PROJECTED)

        out = OSM / f"osm_{name}.gpkg"
        gdf.to_file(out, driver="GPKG")
        print(f"  saved {len(gdf)} features to {out}")

    print("\nDone. OSM files are in", OSM)


if __name__ == "__main__":
    download()