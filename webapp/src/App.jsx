import { useState, useMemo } from 'react';
import { useSpecMatrix } from './hooks/useSpecMatrix';
import { queryProductSelector } from './utils/claudeApi';
import { filterProducts, sortProducts, localSearch } from './utils/filter';
import { buildSolution } from './utils/solution';
import SearchBar from './components/SearchBar';
import ProductList from './components/ProductList';
import SolutionPanel from './components/SolutionPanel';
import ComparisonPanel from './components/ComparisonPanel';
import CompetitorMode from './components/CompetitorMode';
import SettingsModal from './components/SettingsModal';
import ProductDetailModal from './components/ProductDetailModal';
import FilterBar, { EMPTY_FILTERS, applyFilters } from './components/FilterBar';
import './App.css';

export default function App() {
  const { products, hosts, epCards, cameras, loading: matrixLoading, error: matrixError } = useSpecMatrix();

  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [aiResult, setAiResult] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState([]);
  const [showComparison, setShowComparison] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showCompetitor, setShowCompetitor] = useState(false);
  const [forcedHost, setForcedHost] = useState(null);
  const [lastQuery, setLastQuery] = useState('');
  const [detailProduct, setDetailProduct] = useState(null);
  const [activeFilters, setActiveFilters] = useState(EMPTY_FILTERS);

  // Solution bundle
  const solution = useMemo(() => {
    if (!aiResult || !hosts.length) return null;
    const rec = forcedHost
      ? [forcedHost, ...(aiResult.recommended_part_nos || [])]
      : aiResult.recommended_part_nos || [];
    return buildSolution(
      aiResult.structured_criteria,
      aiResult.required_functions,
      hosts,
      [...epCards, ...cameras],
      rec,
    );
  }, [aiResult, hosts, epCards, cameras, forcedHost]);

  // Filtered + sorted display list
  const aiFilteredProducts = useMemo(() => {
    if (!products.length) return [];
    if (!aiResult) return products;
    const filtered = filterProducts(hosts, aiResult.structured_criteria);
    return sortProducts(filtered, aiResult.recommended_part_nos);
  }, [products, hosts, aiResult]);

  const displayProducts = useMemo(
    () => applyFilters(aiFilteredProducts, activeFilters),
    [aiFilteredProducts, activeFilters],
  );

  // Counts per category — always computed on the full AI-filtered pool
  // (not affected by exclusions, so chips always show the correct total)
  const filterCounts = useMemo(() => {
    const byLine = {};
    for (const p of aiFilteredProducts) {
      const l = p.meta.product_line;
      byLine[l] = (byLine[l] || 0) + 1;
    }
    return { byLine };
  }, [aiFilteredProducts]);

  const compareProducts = useMemo(
    () => products.filter(p => selectedForCompare.includes(p.meta.part_no)),
    [products, selectedForCompare]
  );

  const handleSearch = async query => {
    setSearchError(null);
    setAiResult(null);
    setForcedHost(null);
    setLastQuery(query);
    setHasSearched(true);

    // ── Local search: part-no / model-name lookup (no API key needed) ──────
    // Trigger when query looks like a part number or short keyword (≤40 chars,
    // no sentence structure). Skips Claude API entirely.
    if (localSearch.isLocalQuery(query)) {
      const hits = localSearch.search(query, products);
      if (hits.length > 0) {
        // Synthesise a minimal aiResult so the product list sorts correctly
        setAiResult({
          structured_criteria: {},
          required_functions: [],
          recommended_part_nos: hits.map(p => p.meta.part_no),
          recommendation_summary: `Found ${hits.length} product${hits.length > 1 ? 's' : ''} matching "${query}".`,
          key_tradeoffs: null,
          _source: 'local',
        });
        return;
      }
      // No local hits — fall through to Claude
    }

    // ── Claude AI search ─────────────────────────────────────────────────────
    const apiKey = localStorage.getItem('claude_api_key');
    if (!apiKey) { setShowSettings(true); return; }
    setSearchLoading(true);
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
      if (prev.length >= 6) return prev; // max 6
      return [...prev, partNo];
    });
    // Do NOT auto-open — user clicks the Compare button when ready
  };

  const handleRemoveFromCompare = partNo => {
    const next = selectedForCompare.filter(id => id !== partNo);
    setSelectedForCompare(next);
    if (next.length === 0) setShowComparison(false);
  };

  const handleClearCompare = () => {
    setSelectedForCompare([]);
    setShowComparison(false);
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
            <img src="/logo.png" alt="Innodisk" className="brand-logo" />
            <div>
              <span className="brand-name">Golden Bros</span>
              <span className="brand-sub"> Intelligent Product Selection Guide</span>
            </div>
          </div>

          <div className="header-spacer" />

          <div className="header-actions">
            <span className="catalog-count">{products.length} products</span>

            {/* Competitor Compare toggle */}
            <button
              className={`btn btn-ghost competitor-toggle-btn ${showCompetitor ? 'active' : ''}`}
              onClick={() => {
                setShowCompetitor(v => {
                  // If opening, scroll to section after state update
                  if (!v) {
                    setTimeout(() => {
                      document.getElementById('competitor-section')
                        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 50);
                  }
                  return !v;
                });
              }}
              title="Compare with Competitors"
            >
              ⚔ Compare with Competitors
            </button>

            {/* Compare badge */}
            {selectedForCompare.length > 0 && (
              <>
                <button
                  className={`btn btn-compare ${showComparison ? 'btn-compare-active' : ''}`}
                  onClick={() => setShowComparison(v => !v)}
                >
                  ⇄ Compare ({selectedForCompare.length})
                </button>
                <button
                  className="btn btn-clear-compare"
                  onClick={handleClearCompare}
                  title="Clear all comparison selections"
                >
                  ✕
                </button>
              </>
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

        {/* ── Competitor Compare Section (right below search) ── */}
        <section id="competitor-section" className={`competitor-section ${showCompetitor ? 'open' : ''}`}>
          <button
            className="competitor-section-toggle"
            onClick={() => setShowCompetitor(v => !v)}
          >
            <span className="competitor-section-icon">⚔</span>
            <span className="competitor-section-title">Compare with Competitors</span>
            <span className="competitor-section-desc">
              {compareProducts.length > 0
                ? `${compareProducts.length} Innodisk product${compareProducts.length > 1 ? 's' : ''} selected — add competitor model(s) to compare`
                : 'Compare competitor products side-by-side against Innodisk'}
            </span>
            <span className="competitor-section-arrow">{showCompetitor ? '▲' : '▼'}</span>
          </button>

          {showCompetitor && (
            <div className="competitor-section-body">
              <CompetitorMode
                selectedInnodiskProducts={compareProducts}
                allProducts={products}
              />
            </div>
          )}
        </section>

        {/* Solution Bundle + AI summary */}
        {!searchLoading && solution && (
          <div className="solution-row">
            <div className="solution-row-main">
              <SolutionPanel
                solution={solution}
                rfqText={lastQuery}
                selectedForCompare={selectedForCompare}
                onToggleSelect={handleToggleSelect}
                onSelectHost={h => setForcedHost(h.meta.part_no)}
              />
            </div>
            {aiResult && (aiResult.recommendation_summary || aiResult.key_tradeoffs) && (
              <aside className="ai-summary-card ai-summary-side">
                <div className="ai-summary-head">
                  <span className="ai-icon" aria-hidden="true">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 3 13.9 8.6 19.5 10.5 13.9 12.4 12 18 10.1 12.4 4.5 10.5 10.1 8.6 12 3Z" />
                      <path d="M19 15l.6 1.8L21.4 17.4 19.6 18 19 19.8 18.4 18 16.6 17.4 18.4 16.8 19 15Z" />
                    </svg>
                  </span>
                  <span className="ai-summary-title">
                    {aiResult?._source === 'local' ? '🔍 Local Search' : 'Claude AI Analysis'}
                  </span>
                  <button
                    className="clear-btn"
                    onClick={() => { setAiResult(null); setHasSearched(false); }}
                    title="Clear results"
                  >
                    ✕
                  </button>
                </div>
                <div className="ai-summary-text">
                  <p className="ai-recommendation">{aiResult.recommendation_summary}</p>
                  {aiResult.key_tradeoffs && (
                    <p className="ai-tradeoffs">💡 {aiResult.key_tradeoffs}</p>
                  )}
                </div>
              </aside>
            )}
          </div>
        )}

        {/* Filter Bar */}
        {!searchLoading && (
          <FilterBar
            filters={activeFilters}
            onChange={setActiveFilters}
            counts={filterCounts}
          />
        )}

        {/* Product List */}
        {!searchLoading && (
          <ProductList
            products={displayProducts}
            recommendedPartNos={aiResult?.recommended_part_nos}
            selectedForCompare={selectedForCompare}
            onToggleSelect={handleToggleSelect}
            onCardClick={p => setDetailProduct(p)}
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


      </main>

      {/* ── Right-side Comparison Panel ── */}
      {showComparison && compareProducts.length > 0 && (
        <div className="comparison-side-overlay" onClick={() => setShowComparison(false)} />
      )}
      <aside className={`comparison-side-panel ${showComparison && compareProducts.length > 0 ? 'panel-open' : ''}`}>
        <ComparisonPanel
          products={compareProducts}
          onClose={() => setShowComparison(false)}
          onRemove={handleRemoveFromCompare}
        />
      </aside>

      {/* ── Settings Modal ── */}
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}

      {/* ── Product Detail Modal ── */}
      {detailProduct && <ProductDetailModal product={detailProduct} onClose={() => setDetailProduct(null)} />}
    </div>
  );
}
