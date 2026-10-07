"""
LineaScope project configuration.
All constants, paths, and parameters live here.
Every other module imports from this file.
"""

from pathlib import Path

# ---------- Paths ----------

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
OSM = DATA / "osm"
REFERENCE = DATA / "reference"
DERIVED = DATA / "derived"
METADATA = DATA / "metadata"
MODELS = ROOT / "models"
RESULTS = ROOT / "results"
SCRIPTS = ROOT / "scripts"

# ---------- Study area (from SDP v2.0, Table 1) ----------

BBOX_WGS84 = {
    "west":  6.00,
    "south": 5.65,
    "east":  6.30,
    "north": 5.95,
}

CRS_PROJECTED = "EPSG:32632"
CRS_WGS84     = "EPSG:4326"

GRID = {
    "x_min": 167620,
    "y_min": 625200,
    "x_max": 201060,
    "y_max": 658580,
    "res":   20,
}

GRID_WIDTH  = (GRID["x_max"] - GRID["x_min"]) // GRID["res"]
GRID_HEIGHT = (GRID["y_max"] - GRID["y_min"]) // GRID["res"]

# ---------- Data acquisition window ----------

DATE_START = "2025-11-01"
DATE_END   = "2026-04-01"

S1_ASC_ORBIT  = 103
S1_DESC_ORBIT = 22

# ---------- Feature stack layers ----------

S1_LAYERS = ["VV_mean", "VH_mean", "VV_std", "VH_std"]

S2_LAYERS = ["B02", "B03", "B04", "B08", "B11", "B12",
             "NDVI", "B11_B12_ratio"]

DEM_LAYERS = ["elevation", "slope",
              "aspect_sin", "aspect_cos",
              "hillshade_000", "hillshade_045",
              "hillshade_090", "hillshade_135",
              "curvature", "tpi"]

ANCILLARY_LAYERS = ["dist_road", "dist_waterway", "builtup_fraction"]

ALL_LAYERS = S1_LAYERS + S2_LAYERS + DEM_LAYERS + ANCILLARY_LAYERS

# ---------- Candidate generation ----------

CANNY_SIGMA       = 1.5
CANNY_LOW         = 0.05
CANNY_HIGH        = 0.15
HOUGH_MIN_LENGTH  = 15
HOUGH_MAX_GAP     = 3
MERGE_ANGLE_DEG   = 10
MERGE_GAP_PIXELS  = 3
MIN_LENGTH_M      = 400

# ---------- Labelling ----------

POSITIVE_BUFFER_M   = 60
POSITIVE_ANGLE_DEG  = 15
NEGATIVE_DISTANCE_M = 200

# ---------- Random Forest ----------

RF_PARAMS = {
    "n_estimators":     500,
    "max_depth":        None,
    "min_samples_leaf": 2,
    "class_weight":     "balanced",
    "random_state":     42,
    "n_jobs":           -1,
}

SPATIAL_FOLDS = 5

# ---------- API ----------

API_DEFAULT_THRESHOLD    = 0.70
API_DEFAULT_MIN_LENGTH_M = 400
API_MAX_RUNTIME_S        = 10.0

# ---------- Display ----------

AZIMUTH_BINS = 18