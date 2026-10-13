import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import MapView from "./components/MapView";
import DatasetPanel from "./components/DatasetPanel";
import ParameterPanel from "./components/ParameterPanel";
import MetricsPanel from "./components/MetricsPanel";
import DownloadPanel from "./components/DownloadPanel";
import AnalysisPanel from "./components/AnalysisPanel";
import {
  fetchHealth,
  fetchDataset,
  fetchMetrics,
  fetchReference,
  runDetect,
} from "./api";
import "./App.css";

export default function App() {
  const [health, setHealth] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [reference, setReference] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [threshold, setThreshold] = useState(0.5);
  const [minLength, setMinLength] = useState(500);

  // Load static data once on mount
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [h, d, m, r] = await Promise.all([
          fetchHealth(),
          fetchDataset(),
          fetchMetrics(),
          fetchReference(),
        ]);
        if (!mounted) return;
        setHealth(h);
        setDataset(d);
        setMetrics(m);
        setReference(r);
      } catch (e) {
        if (mounted) setError(e.message);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleDetect = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runDetect(threshold, minLength);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [threshold, minLength]);

  return (
    <div className="app">
      <Header health={health} />

      {error && (
        <div className="global-error">
          <span className="error-dot" />
          <span>{error}</span>
        </div>
      )}

      <div className={`app-body ${result ? "with-analysis" : ""}`}>
        {/* Column 1: Controls */}
        <aside className="sidebar">
          <DatasetPanel dataset={dataset} />
          <ParameterPanel
            threshold={threshold}
            setThreshold={setThreshold}
            minLength={minLength}
            setMinLength={setMinLength}
            onDetect={handleDetect}
            loading={loading}
          />
          <DownloadPanel
            threshold={threshold}
            minLength={minLength}
            enabled={!!result}
          />
          <MetricsPanel metrics={metrics} />
        </aside>

        {/* Column 2: Map */}
        <main className="main-map">
          <div className="map-wrap">
            <MapView
              dataset={dataset}
              reference={reference}
              result={result}
            />
          </div>

          {!result && !loading && (
            <div className="empty-state-inline">
              <p className="empty-title">No detections yet</p>
              <p className="empty-sub">
                Adjust the parameters on the left and click{" "}
                <b>Run Detection</b> to analyse the study area.
              </p>
            </div>
          )}

          {loading && (
            <div className="empty-state-inline">
              <p className="empty-sub">Running detection…</p>
            </div>
          )}
        </main>

        {/* Column 3: Analysis (only after detection) */}
        {result && <AnalysisPanel stats={result.statistics} />}
      </div>
    </div>
  );
}