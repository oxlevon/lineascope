"""
main.py -- FastAPI application for LineaScope.

Run locally:
    uvicorn src.api.main:app --reload --port 8000

Docs at:
    http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from src.api import services, db
from src.api.schemas import (
    HealthResponse,
    DatasetResponse,
    DetectRequest,
    DetectResponse,
    MetricsResponse,
    ReferenceResponse,
    RunHistoryResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    services.load_all()
    yield


app = FastAPI(
    title="LineaScope API",
    description="AI-Based Geological Lineament Detection System",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------- CORS ----------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ---------- /api/health ----------

@app.get("/api/health", response_model=HealthResponse)
def health():
    if not services.state.loaded:
        raise HTTPException(503, "service not ready")
    return HealthResponse(
        status="ok",
        model_version=services.state.model_version,
        data_loaded=services.state.loaded,
        n_candidates=len(services.state.candidates),
        n_reference=len(services.state.reference),
        n_detected_at_default=len(services.filter_candidates(0.70, 400)),
    )


# ---------- /api/dataset ----------

@app.get("/api/dataset", response_model=DatasetResponse)
def dataset():
    return DatasetResponse(**services.get_dataset_info())


# ---------- /api/detect ----------

@app.post("/api/detect", response_model=DetectResponse)
def detect(req: DetectRequest):
    result = services.detect(req.threshold, req.min_length_m)
    return DetectResponse(**result)


# ---------- /api/reference ----------

@app.get("/api/reference", response_model=ReferenceResponse)
def reference():
    return ReferenceResponse(**services.get_reference_geojson())


# ---------- /api/metrics ----------

@app.get("/api/metrics", response_model=MetricsResponse)
def metrics():
    return MetricsResponse(**services.get_metrics())


# ---------- /api/runs ----------

@app.get("/api/runs", response_model=RunHistoryResponse)
def runs(limit: int = 10):
    """Return the most recent detection runs from the SQLite log."""
    items = db.list_runs(limit=limit)
    return RunHistoryResponse(count=db.count_runs(), runs=items)


# ---------- /api/download ----------

@app.get("/api/download")
def download(
    threshold: float = Query(0.70, ge=0.0, le=1.0),
    min_length_m: int = Query(400, ge=0),
    format: str = Query("geojson", pattern="^(geojson|csv)$"),
):
    det = services.filter_candidates(threshold, min_length_m)

    if format == "geojson":
        gdf_wgs = det.to_crs("EPSG:4326")[
            ["candidate_id", "length_m", "azimuth", "probability", "geometry"]
        ]
        body = gdf_wgs.to_json()
        return Response(
            content=body,
            media_type="application/geo+json",
            headers={
                "Content-Disposition": "attachment; filename=lineascope_detections.geojson"
            },
        )
    else:
        df = det.drop(columns="geometry")
        body = df.to_csv(index=False)
        return Response(
            content=body,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=lineascope_detections.csv"
            },
        )