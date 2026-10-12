"""
schemas.py -- Pydantic request and response models for the LineaScope API.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# ---------- /api/health ----------

class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    model_version: str = Field(..., example="E1_DEM_only")
    data_loaded: bool = Field(..., example=True)
    n_candidates: int
    n_reference: int
    n_detected_at_default: int


# ---------- /api/dataset ----------

class LayerInfo(BaseModel):
    name: str
    description: str


class DatasetResponse(BaseModel):
    study_area_name: str
    bbox_wgs84: Dict[str, float]
    crs: str
    resolution_m: float
    grid_size: List[int]        # [width, height]
    layers: List[LayerInfo]
    date_range: Dict[str, str]
    sentinel1_scenes: int
    sentinel2_scenes: int


# ---------- /api/detect ----------

class DetectRequest(BaseModel):
    threshold: float = Field(0.70, ge=0.0, le=1.0,
                             description="Classifier probability threshold")
    min_length_m: int = Field(400, ge=0,
                              description="Minimum lineament length in metres")


class LineamentFeature(BaseModel):
    """One GeoJSON feature."""
    type: str = "Feature"
    geometry: Dict
    properties: Dict


class FeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[LineamentFeature]


class DetectStatistics(BaseModel):
    count: int
    total_length_km: float
    mean_length_m: float
    median_length_m: float
    min_length_m: float
    max_length_m: float
    density_km_per_km2: float
    dominant_azimuth_deg: float
    secondary_azimuth_deg: Optional[float]
    azimuth_histogram: List[int]
    azimuth_histogram_bins: List[float]


class DetectResponse(BaseModel):
    params: DetectRequest
    geojson: FeatureCollection
    statistics: DetectStatistics
    runtime_s: float


# ---------- /api/metrics ----------

class FoldMetrics(BaseModel):
    fold: int
    n_test: int
    tp: int
    fp: int
    tn: int
    fn: int
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float


class PooledMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    mcc: float
    roc_auc: float
    pr_auc: float
    confusion_matrix: Dict[str, int]


class ExperimentResult(BaseModel):
    n_features: int
    feature_cols: List[str]
    folds: List[FoldMetrics]
    pooled: PooledMetrics


class MetricsResponse(BaseModel):
    E0_baseline: Dict
    E1_DEM_only: ExperimentResult
    E2_S2_only: ExperimentResult
    E3_S1_only: ExperimentResult
    E4_all_features: ExperimentResult
    best_experiment: str


# ---------- /api/reference ----------

class ReferenceResponse(BaseModel):
    count: int
    total_length_km: float
    geojson: FeatureCollection