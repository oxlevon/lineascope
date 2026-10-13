const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json();
}

export const fetchHealth   = () => request("/api/health");
export const fetchDataset  = () => request("/api/dataset");
export const fetchMetrics  = () => request("/api/metrics");
export const fetchReference = () => request("/api/reference");

export const runDetect = (threshold, minLength) =>
  request("/api/detect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ threshold, min_length_m: minLength }),
  });

export const downloadUrl = (threshold, minLength, format) =>
  `${API_URL}/api/download?threshold=${threshold}&min_length_m=${minLength}&format=${format}`;