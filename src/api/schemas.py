"""
schemas.py -- Pydantic request and response models for the LineaScope API.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# ---------- /api/health ----------

class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    model_version: str = Field(..., examples=["E1_DEM_only"])
    data_loaded: bool = Field(..., examples=[True])
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
    grid_size: List[int]
    layers: List[LayerInfo]
    date_range: Dict[str, str]
    sentinel1_scenes: int
    sentinel2_scenes: int


# ---------- /api/detect ----------

class DetectRequest(BaseModel):
    threshold: float = Field(0.70, ge=0.0, le=1.0)
    min_length_m: int = Field(400, ge=0)


class LineamentFeature(BaseModel):
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


# ---------- /api/reference ----------

class ReferenceResponse(BaseModel):
    count: int
    total_length_km: float
    geojson: FeatureCollection


# ---------- /api/metrics ----------

class MetricsResponse(BaseModel):
    model_config = {"extra": "allow"}


# ---------- /api/runs ----------

class RunRecord(BaseModel):
    run_id: str
    started_at: str
    threshold: float
    min_length_m: int
    n_lineaments: int
    total_length_km: float
    runtime_s: float
    git_commit: str


class RunHistoryResponse(BaseModel):
    count: int
    runs: List[RunRecord]