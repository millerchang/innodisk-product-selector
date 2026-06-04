import { useState, useMemo } from 'react';
import { useSpecMatrix } from './hooks/useSpecMatrix';
import { queryProductSelector } from './utils/claudeApi';
import { filterProducts, sortProducts } from './utils/filter';
import { buildSolution } from './utils/solution';
import SearchBar from './components/SearchBar';
import ProductList from './components/ProductList';
import SolutionPanel from './components/SolutionPanel';
import ComparisonPanel from './components/ComparisonPanel';
import CompetitorMode from './components/CompetitorMode';
import SettingsModal from './components/SettingsModal';
import './App.css';

const MODE_SELECT = 'select';
const MODE_COMPETE = 'compete';

export default function App() {
  const { products, hosts, epCards, loading: matrixLoading, error: matrixError } = useSpecMatrix();

  const [mode, setMode] = useState(MODE_SELECT);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [aiResult, setAiResult] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [showComparison, setShowComparison] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [forcedHost, setForcedHost] = useState(null); // part_no of user-picked alt host
  const [lastQuery, setLastQuery] = useState('');     // RFQ text for quote export

  // Solution bundle: pick host + fill I/O gaps with EP cards.
  const solution = useMemo(() => {
    if (!aiResult || !hosts.length) return null;
    const rec = forcedHost
      ? [forcedHost, ...(aiResult.recommended_part_nos || [])]
      : aiResult.recommended_part_nos || [];
    return buildSolution(
      aiResult.structured_criteria,
      aiResult.required_functions,
      hosts,
      epCards,
      rec,
    );
  }, [aiResult, hosts, epCards, forcedHost]);

  // Filtered + sorted display list (browse view shows compute hosts)
  const displayProducts = useMemo(() => {
    if (!products.length) return [];
    if (!aiResult) return products;
    const filtered = filterProducts(hosts, aiResult.structured_criteria);
    return sortProducts(filtered, aiResult.recommended_part_nos);
  }, [products, hosts, aiResult]);

  const compareProducts = useMemo(
    () => products.filter(p => selectedForCompare.includes(p.meta.part_no)),
    [products, selectedForCompare]
  );

  const handleSearch = async query => {
    const apiKey = localStorage.getItem('claude_api_key');
    if (!apiKey) {
      setShowSettings(true);
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    setAiResult(null);
    setForcedHost(null);
    setLastQuery(query);
    setHasSearched(true);

    try {
      const result = await queryProductSelector(query, products, apiKey);
      setAiResult(result);
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleToggleSelect = partNo => {
    setSelectedForCompare(prev => {
      if (prev.includes(partNo)) return prev.filter(id => id !== partNo);
      if (prev.length >= 4) return prev; // max 4
      return [...prev, partNo];
    });
  };

  const handleRemoveFromCompare = partNo => {
    const next = selectedForCompare.filter(id => id !== partNo);
    setSelectedForCompare(next);
    if (next.length === 0) setShowComparison(false);
  };

  // ---- Loading / Error screens ----
  if (matrixLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Loading product catalog…</p>
      </div>
    );
  }

  if (matrixError) {
    return (
      <div className="error-screen">
        <div className="error-icon">⚠</div>
        <h2>Cannot load product data</h2>
        <p>{matrixError}</p>
        <p className="error-hint">
          Run <code>copy_data.ps1</code> to copy <code>spec_matrix.json</code> into the <code>public/</code> folder,
          then restart the dev server.
        </p>
      </div>
    );
  }

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-inner">
          <div className="header-brand">
            <span className="brand-hexagon">⬡</span>
            <div>
              <span className="brand-name">Innodisk</span>
              <span className="brand-sub"> Product Selector</span>
            </div>
          </div>

          <nav className="header-nav">
            <button
              className={`nav-btn ${mode === MODE_SELECT ? 'nav-active' : ''}`}
              onClick={() => setMode(MODE_SELECT)}
            >
              Product Selection
            </button>
            <button
              className={`nav-btn ${mode === MODE_COMPETE ? 'nav-active' : ''}`}
              onClick={() => setMode(MODE_COMPETE)}
            >
              Competitor Compare
            </button>
          </nav>

          <div className="header-actions">
            <span className="catalog-count">{products.length} products</span>
            {selectedForCompare.length > 0 && (
              <button
                className="btn btn-compare"
                onClick={() => setShowComparison(true)}
              >
                Compare ({selectedForCompare.length})
              </button>
            )}
            <button
              className="btn btn-icon"
              onClick={() => setShowSettings(true)}
              title="Settings (API Key)"
            >
              ⚙
            </button>
          </div>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="app-main">

        {mode === MODE_SELECT ? (
          <>
            {/* AI Result Summary */}
            {aiResult && (
              <div className="ai-summary-card">
                <div className="ai-icon">🤖</div>
                <div className="ai-summary-text">
                  <p className="ai-recommendation">{aiResult.recommendation_summary}</p>
                  {aiResult.key_tradeoffs && (
                    <p className="ai-tradeoffs">💡 {aiResult.key_tradeoffs}</p>
                  )}
                </div>
                <button
                  className="clear-btn"
                  onClick={() => { setAiResult(null); setHasSearched(false); }}
                  title="Clear results"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Search Error */}
            {searchError && (
              <div className="error-banner">
                <strong>⚠ Error:</strong> {searchError}
                {searchError.includes('API key') && (
                  <button className="btn-link" onClick={() => setShowSettings(true)}>
                    Open Settings →
                  </button>
                )}
              </div>
            )}

            {/* Search Bar */}
            <SearchBar onSearch={handleSearch} loading={searchLoading} />

            {/* Solution Bundle (host + EP add-on cards) */}
            {!searchLoading && solution && (
              <SolutionPanel
                solution={solution}
                rfqText={lastQuery}
                selectedForCompare={selectedForCompare}
                onToggleSelect={handleToggleSelect}
                onSelectHost={h => setForcedHost(h.meta.part_no)}
              />
            )}

            {/* Product List */}
            {!searchLoading && (
              <ProductList
                products={displayProducts}
                recommendedPartNos={aiResult?.recommended_part_nos}
                selectedForCompare={selectedForCompare}
                onToggleSelect={handleToggleSelect}
                totalCount={products.length}
                hasSearched={hasSearched}
              />
            )}

            {searchLoading && (
              <div className="loading-results">
                <div className="loading-spinner" />
                <p>Analyzing requirements with Claude AI…</p>
              </div>
            )}
          </>
        ) : (
          <CompetitorMode products={products} />
        )}
      </main>

      {/* ── Comparison Overlay ── */}
      {showComparison && compareProducts.length > 0 && (
        <ComparisonPanel
          products={compareProducts}
          onClose={() => setShowComparison(false)}
          onRemove={handleRemoveFromCompare}
        />
      )}

      {/* ── Settings Modal ── */}
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}
