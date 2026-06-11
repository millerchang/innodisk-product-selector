import { useState } from 'react';
import { queryCompetitorComparison } from '../utils/claudeApi';

// Computing platform categories + Camera module categories
// Any category Claude returns that isn't listed here gets appended at the end automatically
const CATEGORY_ORDER = [
  'Imaging', 'Sensor', 'Optical',                // Camera first
  'Compute', 'Memory', 'Thermal', 'I/O',         // Computing
  'Mechanical', 'Certifications', 'Features',
];

// inputMode: 'search' | 'paste'
// search = Claude uses web_search to find live specs; accepts model names, part nos, or product page URLs
// paste  = user pastes raw spec text directly; no web search performed
export default function CompetitorMode({ selectedInnodiskProducts = [], allProducts = [] }) {
  const [input, setInput] = useState('');
  const [inputMode, setInputMode] = useState('search');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const hasSelected = selectedInnodiskProducts.length > 0;
  const innodiskKeys = new Set(selectedInnodiskProducts.map(p => p.meta.part_no));

  const handleCompare = async () => {
    const apiKey = localStorage.getItem('claude_api_key');
    if (!apiKey) { setError('API key not set — open Settings first.'); return; }
    if (!input.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const isManualPaste = inputMode === 'paste';
      const res = await queryCompetitorComparison(
        input.trim(),
        selectedInnodiskProducts,
        allProducts,
        apiKey,
        isManualPaste,
      );
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Group rows by category.
  // Known categories follow CATEGORY_ORDER; any extra categories Claude returns are appended.
  function groupRows(rows) {
    const grouped = {};
    for (const row of rows) {
      const cat = row.category || 'Other';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(row);
    }
    const knownFirst = CATEGORY_ORDER.filter(c => grouped[c]);
    const extras = Object.keys(grouped).filter(c => !CATEGORY_ORDER.includes(c));
    return [...knownFirst, ...extras].map(c => ({ category: c, rows: grouped[c] }));
  }

  return (
    <div className="competitor-mode">

      {/* ── Input section ── */}
      <div className="competitor-input-section">

        {/* Selected Innodisk products chips */}
        {hasSelected ? (
          <div className="cmp-selected-products">
            <span className="cmp-selected-label">Innodisk products:</span>
            {selectedInnodiskProducts.map(p => (
              <span key={p.meta.part_no} className="cmp-product-chip">
                {p.meta.part_no}
              </span>
            ))}
          </div>
        ) : (
          <div className="cmp-no-selection">
            <span className="cmp-hint-icon">💡</span>
            Tip: check products in the list above to include them in the comparison.
            If none selected, Claude will auto-pick the closest Innodisk match.
          </div>
        )}

        {/* Mode toggle */}
        <div className="mode-toggle">
          <button
            className={`mode-toggle-btn ${inputMode === 'search' ? 'active' : ''}`}
            onClick={() => { setInputMode('search'); setInput(''); setError(null); }}
          >
            🔍 Search (Model / URL)
          </button>
          <button
            className={`mode-toggle-btn ${inputMode === 'paste' ? 'active' : ''}`}
            onClick={() => { setInputMode('paste'); setInput(''); setError(null); }}
          >
            📋 Paste Specs
          </button>
        </div>

        <textarea
          className="search-textarea"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={
            inputMode === 'paste'
              ? 'Paste competitor product specs here…'
              : 'Enter competitor model name(s) or product page URL, e.g.:\nMOXA DRP-A100\nhttps://www.advantech.com/products/...'
          }
          rows={inputMode === 'paste' ? 8 : 3}
        />
        {inputMode === 'search' && (
          <p className="manual-note">🔍 Claude will search the web for live specs — accepts model names, part numbers, or product page URLs.</p>
        )}
        {inputMode === 'paste' && (
          <p className="manual-note">📌 Specs are taken directly from the text above — no web search performed.</p>
        )}

        {error && <div className="search-error">{error}</div>}

        <button
          className="btn btn-primary"
          onClick={handleCompare}
          disabled={loading || !input.trim()}
        >
          {loading
            ? <><span className="spinner-inline" /> Comparing…</>
            : '⇄ Compare →'}
        </button>
      </div>

      {/* ── Comparison Result ── */}
      {result && (() => {
        const columns = result.columns || [];
        const groups  = groupRows(result.rows || []);

        // Tally wins per column
        const wins = {};
        for (const col of columns) wins[col] = 0;
        for (const row of result.rows || []) {
          if (row.best && wins[row.best] != null) wins[row.best]++;
        }
        const totalRows = (result.rows || []).filter(r => r.best).length || 1;

        return (
          <div className="competitor-result">

            {/* Result header */}
            <div className="comp-result-header">
              <h3>Side-by-Side Comparison</h3>
              <div className="comp-result-meta">
                {Object.entries(result.competitor_notes || {}).map(([name, info]) => (
                  <span key={name} className="data-source-badge" title={info.note || ''}>
                    {name}: {info.confidence === 'high' ? '🟢' : info.confidence === 'medium' ? '🟡' : '🔴'} {info.confidence}
                    {info.note ? ` — ${info.note}` : ''}
                  </span>
                ))}
              </div>
            </div>

            {/* Win score summary */}
            <div className="cmp-score-bar">
              {columns.map(col => (
                <div
                  key={col}
                  className={`cmp-score-card ${innodiskKeys.has(col) ? 'score-innodisk' : 'score-competitor'}`}
                >
                  <span className="score-name">{col}</span>
                  <span className="score-tag">{innodiskKeys.has(col) ? 'Innodisk' : 'Competitor'}</span>
                  <span className="score-wins">{wins[col]}<span className="score-denom">/{totalRows} wins</span></span>
                  <div
                    className="score-bar-fill"
                    style={{ width: `${Math.round((wins[col] / totalRows) * 100)}%` }}
                  />
                </div>
              ))}
            </div>

            {/* Main comparison table */}
            <div className="cmp-table-wrapper">
              <table className="cmp-unified-table">
                <thead>
                  <tr>
                    <th className="cmp-spec-header">Specification</th>
                    {columns.map(col => (
                      <th
                        key={col}
                        className={`cmp-col-header ${innodiskKeys.has(col) ? 'cmp-col-innodisk' : 'cmp-col-competitor'}`}
                      >
                        <div className="cmp-col-header-inner">
                          <span className="cmp-col-name">{col}</span>
                          <span className={`cmp-col-tag ${innodiskKeys.has(col) ? 'tag-innodisk' : 'tag-competitor'}`}>
                            {innodiskKeys.has(col) ? 'Innodisk ✓' : 'Competitor'}
                          </span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {groups.map(({ category, rows }) => (
                    <>
                      {/* Category divider */}
                      <tr key={`cat-${category}`} className="cmp-category-row">
                        <td colSpan={columns.length + 1} className="cmp-category-label">
                          {category}
                        </td>
                      </tr>

                      {rows.map((row, ri) => {
                        const isInnodiskWin = row.best && innodiskKeys.has(row.best);
                        return (
                          <tr
                            key={`${category}-${ri}`}
                            className={`cmp-data-row ${isInnodiskWin ? 'row-innodisk-wins' : ''}`}
                          >
                            <td className="cmp-spec-label">{row.spec}</td>
                            {columns.map(col => {
                              const val = row.values?.[col] ?? '—';
                              const isWinner = row.best === col;
                              const isEmpty = val === '—' || val === 'N/A';
                              return (
                                <td
                                  key={col}
                                  className={[
                                    'cmp-cell',
                                    innodiskKeys.has(col) ? 'cmp-cell-innodisk' : 'cmp-cell-competitor',
                                    isWinner ? 'cmp-cell-winner' : '',
                                    isEmpty ? 'cmp-cell-empty' : '',
                                  ].filter(Boolean).join(' ')}
                                >
                                  <span className="cmp-cell-val">{val}</span>
                                  {isWinner && (
                                    <span
                                      className={`cmp-winner-badge ${innodiskKeys.has(col) ? 'badge-innodisk' : 'badge-competitor'}`}
                                      title="Best in this spec"
                                    >
                                      ✓
                                    </span>
                                  )}
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Advantages + Talking Points */}
            {(result.innodisk_advantages?.length > 0 || result.talking_points?.length > 0) && (
              <div className="comp-bottom-grid">
                {result.innodisk_advantages?.length > 0 && (
                  <div className="comp-section comp-section-green">
                    <h4>💪 Innodisk Advantages</h4>
                    <ul>
                      {result.innodisk_advantages.map((a, i) => <li key={i}>{a}</li>)}
                    </ul>
                  </div>
                )}
                {result.talking_points?.length > 0 && (
                  <div className="comp-section comp-section-blue">
                    <h4>🗣 Sales Talking Points</h4>
                    <ol>
                      {result.talking_points.map((t, i) => <li key={i}>{t}</li>)}
                    </ol>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
