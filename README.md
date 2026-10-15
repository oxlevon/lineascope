
# LineaScope

AI-based geological lineament detection using multisource remote-sensing data.

## Overview

LineaScope is a geospatial application designed to detect, classify, visualise, and map candidate geological lineaments using satellite imagery, digital elevation data, and OpenStreetMap features.

It combines image-processing techniques with a Random Forest machine-learning model to identify candidate lineaments and present the results through an interactive map.

## Features

- Automated candidate lineament detection
- Multisource remote-sensing data integration
- Machine-learning classification using Random Forest
- Interactive map visualisation
- Lineament orientation and length analysis
- Export results to GeoJSON and CSV
- REST API for detection and dataset information

## Technology Stack

- **Frontend:** React, Vite, Leaflet
- **Backend:** Python, FastAPI
- **Machine Learning:** Scikit-learn, Random Forest
- **Geospatial Processing:** Google Earth Engine, QGIS, GeoPandas
- **Database:** SQLite
- **Deployment:** Vercel and Render

## Data Sources

- Sentinel-1 SAR imagery
- Sentinel-2 optical imagery
- Copernicus DEM
- ESA WorldCover
- OpenStreetMap
- Manually digitised reference lineaments

## Project Structure

```text
LineaScope/
├── src/
│   ├── offline/
│   └── api/
├── web/
├── data/
├── models/
├── results/
├── scripts/
├── Dockerfile
├── requirements-deploy.txt
├── render.yaml
└── README.md
```

## Installation

### Backend

```bash
git clone https://github.com/YOUR_USERNAME/lineascope.git
cd lineascope

python -m venv venv
```

Activate the environment and install dependencies.

**Windows:**
```powershell
venv\Scripts\activate
pip install -r requirements-deploy.txt
```

**macOS/Linux:**
```bash
source venv/bin/activate
pip install -r requirements-deploy.txt
```

### Frontend

```bash
cd web
npm install
```

## Running Locally

Start the backend from the project root:

```bash
uvicorn src.api.main:app --reload --port 8000
```

Start the frontend in a separate terminal:

```bash
cd web
npm run dev
```

API documentation is available at:

`http://127.0.0.1:8000/docs`

## Usage

1. Open the web application.
2. View the study area and available data.
3. Adjust the detection probability threshold and minimum lineament length.
4. Run the detection process.
5. Explore candidate lineaments on the interactive map.
6. Export results as GeoJSON or CSV.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Check service status |
| GET | `/api/dataset` | Retrieve dataset information |
| POST | `/api/detect` | Run lineament detection |
| GET | `/api/reference` | Retrieve reference lineaments |
| GET | `/api/metrics` | Retrieve evaluation metrics |
| GET | `/api/runs` | Retrieve detection history |
| GET | `/api/download` | Export detection results |

## Research and Evaluation

The system supports experiments comparing DEM-derived features, Sentinel-1, Sentinel-2, and fused multisource features.

Model performance can be evaluated using precision, recall, F1 score, and Matthews correlation coefficient (MCC).

Detected features represent candidate geological lineaments and should be reviewed and validated before geological interpretation.

## Data Attribution

- Sentinel-1 and Sentinel-2: Copernicus Programme / European Space Agency
- Elevation data: Copernicus DEM
- Land cover: ESA WorldCover
- Map data: © OpenStreetMap contributors

## Author

Developed by Aguade Victoria Beke-ere.
