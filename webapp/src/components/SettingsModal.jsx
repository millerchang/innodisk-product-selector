import { useState } from 'react';

export default function SettingsModal({ onClose }) {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('claude_api_key') || '');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    const trimmed = apiKey.trim();
    if (trimmed) {
      localStorage.setItem('claude_api_key', trimmed);
    } else {
      localStorage.removeItem('claude_api_key');
    }
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 800);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label className="form-label" htmlFor="api-key-input">
              Anthropic API Key
            </label>
            <p className="form-hint">
              Required for AI-powered product matching. Key is stored in your browser only — never sent to any server except Anthropic's API.
            </p>
            <input
              id="api-key-input"
              type="password"
              className="form-input"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-ant-api03-..."
              autoComplete="off"
              spellCheck={false}
            />
          </div>

          <div className="form-info">
            <h4>Cost estimate</h4>
            <ul>
              <li>Model: <code>claude-haiku-4-5</code></li>
              <li>~$0.003 per product selection query</li>
              <li>~$0.008 per competitor comparison</li>
            </ul>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button
            className={`btn btn-primary ${saved ? 'btn-saved' : ''}`}
            onClick={handleSave}
          >
            {saved ? '✓ Saved' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
