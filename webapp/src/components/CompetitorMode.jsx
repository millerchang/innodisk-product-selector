import { useState } from 'react';
import { queryCompetitorComparison } from '../utils/claudeApi';

export default function CompetitorMode({ products }) {
  const [input, setInput] = useState('');
  const [isManualPaste, setIsManualPaste] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCompare = async () => {
    const apiKey = localStorage.getItem('claude_api_key');
    if (!apiKey) { setError('API key not set — open Settings first.'); return; }
    if (!input.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await queryCompetitorComparison(input.trim(), products, apiKey, isManualPaste);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="competitor-mode">
      <div className="competitor-input-section">
        <h3>Competitor Comparison</h3>
        <p className="section-desc">Enter a competitor product model, or paste spec sheet text to compare against Innodisk products.</p>

        <div className="mode-toggle">
          <button
            className={`mode-toggle-btn ${!isManualPaste ? 'active' : ''}`}
            onClick={() => setIsManualPaste(false)}
          >
            Model Name
          </button>
          <button
            className={`mode-toggle-btn ${isManualPaste ? 'active' : ''}`}
            onClick={() => setIsManualPaste(true)}
          >
            Paste Specs
          </button>
        </div>

        <textarea
          className="search-textarea"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={
            isManualPaste
              ? 'Paste competitor product specs here...'
              : 'Enter competitor model number (e.g. "Advantech MIC-720AI", "ADLINK ROScube RQX-58G")'
          }
          rows={isManualPaste ? 8 : 2}
        />

        {isManualPaste && (
          <p className="manual-note">
            📌 Data source will be labeled "manually provided" in the output.
          </p>
        )}

        {error && <div className="search-error">{error}</div>}

        <button
          className="btn btn-primary"
          onClick={handleCompare}
          disabled={loading || !input.trim()}
        >
          {loading ? <><span className="spinner-inline" /> Comparing...</> : 'Compare →'}
        </button>
      </div>

      {/* Comparison Results */}
      {result && (
        <div className="competitor-result">
          <div className="comp-result-header">
            <h3>Comparison: {result.competitor_name || input}</h3>
            <span className="data-source-badge">
              Source: {result.data_source === 'manually_provided' ? '📋 Manual input' : '🤖 AI inferred'}
            </span>
          </div>

          {result.competitor_specs_summary && (
            <div className="comp-summary">
              <strong>Competitor Summary:</strong> {result.competitor_specs_summary}
            </div>
          )}

          {result.closest_innodisk_matches?.length > 0 && (
            <div className="comp-matches">
              <strong>Closest Innodisk Matches:</strong> {result.closest_innodisk_matches.join(', ')}
            </div>
          )}

          {/* Comparison Table */}
          {result.comparison_table?.length > 0 && (
            <div className="comp-table-wrapper">
              <table className="comp-table">
                <thead>
                  <tr>
                    <th>Specification</th>
                    <th>{result.competitor_name || 'Competitor'}</th>
                    <th>Innodisk</th>
                    <th>Winner</th>
                  </tr>
                </thead>
                <tbody>
                  {result.comparison_table.map((row, i) => (
                    <tr key={i} className={row.innodisk_wins ? 'row-innodisk-win' : ''}>
                      <td>{row.spec}</td>
                      <td>{row.competitor}</td>
                      <td className="innodisk-val">{row.innodisk}</td>
                      <td>{row.innodisk_wins ? '✅ Innodisk' : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Advantages */}
          {result.innodisk_advantages?.length > 0 && (
            <div className="comp-section">
              <h4>Innodisk Advantages</h4>
              <ul>
                {result.innodisk_advantages.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}

          {/* Talking Points */}
          {result.talking_points?.length > 0 && (
            <div className="comp-section">
              <h4>Sales Talking Points</h4>
              <ol>
                {result.talking_points.map((t, i) => <li key={i}>{t}</li>)}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
