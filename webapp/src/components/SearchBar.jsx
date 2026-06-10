import { useState, useRef } from 'react';
import { parseRfqFile, wrapRfqText } from '../utils/rfqParser';

const EXAMPLE_QUERIES = [
  { label: 'Wide-temp AI Box PC', text: '我需要工業電腦支援 -40~70°C，有Windows，AI推理能力30+ TOPS' },
  { label: 'High TOPS inference', text: 'High-performance edge AI system, 800+ TOPS, for LLM and generative AI at the edge' },
  { label: 'Compact AIoT SBC', text: 'Compact SBC for AMR/AGV with Intel processor, wide voltage input, Linux support' },
  { label: 'Intel Core Ultra box', text: 'Box PC with Intel Core Ultra processor, low TDP under 28W, M.2 NVMe storage' },
];

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('');
  const [rfqFile, setRfqFile] = useState(null);   // { name, parsing }
  const [rfqError, setRfqError] = useState(null);
  const fileInputRef = useRef(null);

  // ── Text submit ──────────────────────────────────────────────────────────
  const handleSubmit = e => {
    e.preventDefault();
    const q = query.trim();
    if (q) onSearch(q);
  };

  const handleExample = q => {
    setQuery(q);
    setRfqFile(null);
    onSearch(q);
  };

  // ── File upload ──────────────────────────────────────────────────────────
  const handleFileChange = async e => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset state
    setRfqError(null);
    setRfqFile({ name: file.name, parsing: true });
    setQuery('');

    try {
      const text = await parseRfqFile(file);
      if (!text.trim()) throw new Error('No readable text found in the file.');
      const wrapped = wrapRfqText(text, file.name);
      setRfqFile({ name: file.name, parsing: false });
      onSearch(wrapped);
    } catch (err) {
      setRfqFile(null);
      setRfqError(err.message);
    } finally {
      // Reset input so the same file can be re-uploaded
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const clearRfq = () => {
    setRfqFile(null);
    setRfqError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const isParsing = rfqFile?.parsing;

  return (
    <div className="search-section">
      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-input-wrapper">
          <textarea
            className="search-textarea"
            value={query}
            onChange={e => { setQuery(e.target.value); setRfqFile(null); setRfqError(null); }}
            placeholder="描述客戶需求 / Describe customer requirements in any language…&#10;e.g. industrial AI box PC, -40°C wide temp, Windows, PCIe expansion"
            rows={3}
            disabled={isParsing || loading}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const q = query.trim();
                if (q) onSearch(q);
              }
            }}
          />

          {/* RFQ file badge — shown when a file is loaded / parsing */}
          {rfqFile && (
            <div className="rfq-badge">
              {rfqFile.parsing
                ? <><span className="spinner-inline" /> Parsing {rfqFile.name}…</>
                : <><span className="rfq-badge-icon">📄</span>{rfqFile.name}</>
              }
              {!rfqFile.parsing && (
                <button type="button" className="rfq-badge-clear" onClick={clearRfq} title="Remove file">✕</button>
              )}
            </div>
          )}

          <div className="search-actions">
            {/* File upload button */}
            <button
              type="button"
              className="btn btn-ghost upload-btn"
              title="Upload RFQ (PDF or Word)"
              disabled={loading || isParsing}
              onClick={() => fileInputRef.current?.click()}
            >
              📎
            </button>

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />

            {/* Search submit */}
            <button
              type="submit"
              className="btn btn-primary search-submit-btn"
              disabled={loading || isParsing || !query.trim()}
            >
              {loading ? <span className="spinner-inline" /> : '→'}
            </button>
          </div>
        </div>

        {/* Error message */}
        {rfqError && (
          <p className="rfq-error">⚠ {rfqError}</p>
        )}

        <p className="search-hint">
          Press Enter to search · Shift+Enter for new line · 📎 to upload RFQ (PDF / Word)
        </p>
      </form>

      <div className="example-queries">
        <span className="examples-label">Quick examples:</span>
        {EXAMPLE_QUERIES.map((ex, i) => (
          <button
            key={i}
            className="example-chip"
            onClick={() => handleExample(ex.text)}
            disabled={loading || isParsing}
          >
            {ex.label}
          </button>
        ))}
      </div>
    </div>
  );
}
