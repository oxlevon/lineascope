import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";

/* ---------- Basemaps (all key-free) ---------- */

const BASEMAPS = {
  satellite: {
    label: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
    subdomains: "",
    maxZoom: 19,
  },
  streets: {
    label: "Streets",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    subdomains: "abc",
    maxZoom: 19,
  },
  topo: {
    label: "Terrain",
    url: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attribution: 'Map data &copy; OpenStreetMap contributors, SRTM | Style &copy; OpenTopoMap',
    subdomains: "abc",
    maxZoom: 17,
  },
  clean: {
    label: "Clean",
    url: "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
    attribution: '&copy; OpenStreetMap contributors — tiles by HOT',
    subdomains: "abc",
    maxZoom: 19,
  },
  esri_topo: {
    label: "Esri Topo",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, USGS",
    subdomains: "",
    maxZoom: 19,
  },
};

/* ---------- Helpers ---------- */

function FitToBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [30, 30] });
  }, [bounds, map]);
  return null;
}

function bboxToRectangle(bbox) {
  const { west, south, east, north } = bbox;
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { kind: "aoi" },
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [west, south],
              [east, south],
              [east, north],
              [west, north],
              [west, south],
            ],
          ],
        },
      },
    ],
  };
}

/* ---------- Main component ---------- */

export default function MapView({ dataset, reference, result }) {
  const [basemapKey, setBasemapKey] = useState("satellite");

  let bounds = null;
  let aoiGeojson = null;
  if (dataset?.bbox_wgs84) {
    const b = dataset.bbox_wgs84;
    bounds = [
      [b.south, b.west],
      [b.north, b.east],
    ];
    aoiGeojson = bboxToRectangle(b);
  }

  const basemap = BASEMAPS[basemapKey];

  return (
    <MapContainer
      center={[5.8, 6.15]}
      zoom={10}
      style={{ height: "100%", width: "100%" }}
      zoomControl={true}
    >
      <TileLayer
        key={basemapKey}
        url={basemap.url}
        attribution={basemap.attribution}
        subdomains={basemap.subdomains}
        maxZoom={basemap.maxZoom}
      />

      <FitToBounds bounds={bounds} />

      {aoiGeojson && (
        <GeoJSON
          data={aoiGeojson}
          style={{
            color: "#ffffff",
            weight: 2.4,
            opacity: 0.95,
            dashArray: "8,5",
            fill: false,
          }}
          interactive={false}
        />
      )}

      {reference?.geojson && (
        <GeoJSON
          data={reference.geojson}
          style={{
            color: "#eab308",
            weight: 1.8,
            opacity: 0.9,
            dashArray: "5,4",
          }}
          onEachFeature={(feature, layer) => {
            const p = feature.properties;
            layer.bindPopup(
              `<div style="font-family: inherit; font-size: 12.5px;">
                <b>Reference lineament</b><br/>
                ${p.confidence ? `Confidence: ${p.confidence}<br/>` : ""}
                ${p.azimuth != null ? `Azimuth: ${p.azimuth.toFixed(1)}°` : ""}
              </div>`
            );
          }}
        />
      )}

      {result?.geojson && (
        <GeoJSON
          key={`det-${result.statistics.count}`}
          data={result.geojson}
          style={{
            color: "#ff2d2d",
            weight: 2.4,
            opacity: 0.95,
          }}
          onEachFeature={(feature, layer) => {
            const p = feature.properties;
            layer.bindPopup(
              `<div style="font-family: inherit; font-size: 12.5px; min-width: 180px;">
                <div style="font-weight: 600; margin-bottom: 6px;">Detected lineament</div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color:#64748b;">ID</span><b>${p.candidate_id}</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color:#64748b;">Probability</span><b>${p.probability.toFixed(3)}</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color:#64748b;">Length</span><b>${p.length_m.toFixed(0)} m</b>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span style="color:#64748b;">Azimuth</span><b>${p.azimuth.toFixed(1)}°</b>
                </div>
              </div>`
            );
          }}
        />
      )}

      <BasemapSwitcher current={basemapKey} onChange={setBasemapKey} />

      <MapLegend
        hasDetections={!!result}
        hasReference={!!reference}
        hasAOI={!!aoiGeojson}
      />
    </MapContainer>
  );
}

/* ---------- Basemap switcher (top-right) ---------- */

function BasemapSwitcher({ current, onChange }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="basemap-switcher">
      <button
        type="button"
        className="basemap-toggle"
        onClick={() => setOpen((o) => !o)}
        title="Change base map"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{ width: 16, height: 16 }}
        >
          <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
          <line x1="8" y1="2" x2="8" y2="18" />
          <line x1="16" y1="6" x2="16" y2="22" />
        </svg>
      </button>

      {open && (
        <div className="basemap-menu">
          {Object.entries(BASEMAPS).map(([key, b]) => (
            <button
              key={key}
              type="button"
              className={`basemap-item ${current === key ? "active" : ""}`}
              onClick={() => {
                onChange(key);
                setOpen(false);
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Legend ---------- */

function MapLegend({ hasDetections, hasReference, hasAOI }) {
  return (
    <div className="map-legend">
      <div className="map-legend-title">Legend</div>

      {hasAOI && (
        <div className="map-legend-row">
          <span
            className="map-legend-swatch"
            style={{
              background: "transparent",
              borderTop: "2px dashed #ffffff",
              height: 0,
            }}
          />
          <span>Study area boundary</span>
        </div>
      )}

      {hasDetections && (
        <div className="map-legend-row">
          <span
            className="map-legend-swatch"
            style={{ background: "#ff2d2d" }}
          />
          <span>Detected lineament</span>
        </div>
      )}

      {hasReference && (
        <div className="map-legend-row">
          <span
            className="map-legend-swatch"
            style={{
              background: "transparent",
              borderTop: "2px dashed #eab308",
              height: 0,
            }}
          />
          <span>Reference lineament</span>
        </div>
      )}
    </div>
  );
}