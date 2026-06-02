import { useState } from 'react';

const EXAMPLE_QUERIES = [
  { label: 'Wide-temp AI Box PC', text: '我需要工業電腦支援 -40~70°C，有Windows，AI推理能力30+ TOPS' },
  { label: 'High TOPS inference', text: 'High-performance edge AI system, 800+ TOPS, for LLM and generative AI at the edge' },
  { label: 'Compact AIoT SBC', text: 'Compact SBC for AMR/AGV with Intel processor, wide voltage input, Linux support' },
  { label: 'Intel Core Ultra box', text: 'Box PC with Intel Core Ultra processor, low TDP under 28W, M.2 NVMe storage' },
];

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('');

  const handleSubmit = e => {
    e.preventDefault();
    const q = query.trim();
    if (q) onSearch(q);
  };

  const handleExample = q => {
    setQuery(q);
    onSearch(q);
  };

  return (
    <div className="search-section">
      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-input-wrapper">
          <textarea
            className="search-textarea"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="描述客戶需求 / Describe customer requirements in any language…&#10;e.g. industrial AI box PC, -40°C wide temp, Windows, PCIe expansion"
            rows={3}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const q = query.trim();
                if (q) onSearch(q);
              }
            }}
          />
          <button
            type="submit"
            className="btn btn-primary search-submit-btn"
            disabled={loading || !query.trim()}
          >
            {loading ? (
              <span className="spinner-inline" />
            ) : (
              '→'
            )}
          </button>
        </div>
        <p className="search-hint">Press Enter to search · Shift+Enter for new line</p>
      </form>

      <div className="example-queries">
        <span className="examples-label">Quick examples:</span>
        {EXAMPLE_QUERIES.map((ex, i) => (
          <button
            key={i}
            className="example-chip"
            onClick={() => handleExample(ex.text)}
            disabled={loading}
          >
            {ex.label}
          </button>
        ))}
      </div>
    </div>
  );
}
