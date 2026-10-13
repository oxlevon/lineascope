export default function ParameterPanel({
  threshold, setThreshold, minLength, setMinLength, onDetect, loading,
}) {
  return (
    <div className="card">
      <div className="card-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v20M2 12h20" strokeLinecap="round" />
        </svg>
        Detection Parameters
      </div>

      <div className="param-field">
        <div className="param-head">
          <label htmlFor="threshold">Probability threshold</label>
          <span className="param-value">{threshold.toFixed(2)}</span>
        </div>
        <input
          id="threshold" type="range" min="0" max="1" step="0.05"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value))}
          className="slider"
        />
        <div className="param-range"><span>0.00</span><span>1.00</span></div>
      </div>

      <div className="param-field">
        <div className="param-head">
          <label htmlFor="minLength">Minimum length</label>
          <span className="param-value">{minLength} m</span>
        </div>
        <input
          id="minLength" type="number" min="0" step="50"
          value={minLength}
          onChange={(e) => setMinLength(parseInt(e.target.value) || 0)}
          className="number-input"
        />
      </div>

      <button className="btn-primary" onClick={onDetect} disabled={loading}>
        {loading ? (
          <><span className="btn-spinner" /> Running…</>
        ) : (
          <>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2.4" style={{ width: 14, height: 14 }}>
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Run Detection
          </>
        )}
      </button>
    </div>
  );
}