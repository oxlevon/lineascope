FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-deploy.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-deploy.txt

COPY src/ ./src/
COPY models/rf_final.joblib ./models/
COPY data/derived/candidates.geojson ./data/derived/
COPY data/derived/candidate_features.parquet ./data/derived/
COPY data/derived/metrics.json ./data/derived/
COPY data/reference/reference_lineaments.geojson ./data/reference/

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]