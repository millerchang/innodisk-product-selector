import {
  formatTemp, formatTops, formatRam, formatTdp, formatConnectivity, formatOS, formatDimensions,
  getPlatformIcon, getProductLineLabel, getMatchBadge, getLifecycleStyle,
} from '../utils/formatters';

export default function ProductCard({ product, recommendedPartNos, isSelected, onToggleSelect }) {
  const m = product.meta;
  const cs = product.computing_spec || {};
  const co = product.common || {};
  const badge = getMatchBadge(m.part_no, recommendedPartNos);
  const lifecycle = getLifecycleStyle(co.lifecycle_status);

  return (
    <div className={`product-card ${isSelected ? 'card-selected' : ''} ${badge ? 'card-matched' : ''}`}>

      {/* Match Badge */}
      {badge && (
        <div className="match-badge" style={{ background: badge.color }}>
          ✓ {badge.label}
        </div>
      )}

      {/* Card Header */}
      <div className="card-header">
        <div className="card-title-group">
          <span className="platform-icon" title={cs.platform_brand}>
            {getPlatformIcon(cs.platform_brand)}
          </span>
          <div className="card-title-text">
            <h3 className="card-part-no">{m.part_no}</h3>
            <div className="card-tags">
              <span className="tag tag-bu">{getProductLineLabel(m.product_line)}</span>
              <span className="tag" style={{ color: lifecycle.color, borderColor: lifecycle.color }}>
                {lifecycle.label}
              </span>
            </div>
          </div>
        </div>
        <label className="compare-toggle" title={isSelected ? 'Remove from comparison' : 'Add to comparison (max 4)'}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(m.part_no)}
          />
          <span>Compare</span>
        </label>
      </div>

      {/* Processor */}
      <div className="card-processor">
        {cs.processor_model || cs.platform_brand || '—'}
      </div>

      {/* Key Specs Grid */}
      <div className="spec-grid">
        <div className="spec-cell spec-highlight">
          <span className="spec-cell-label">AI TOPS</span>
          <span className="spec-cell-value tops-value">{formatTops(cs.ai_tops)}</span>
        </div>
        <div className="spec-cell">
          <span className="spec-cell-label">TDP</span>
          <span className="spec-cell-value">{formatTdp(cs.tdp_watt)}</span>
        </div>
        <div className="spec-cell">
          <span className="spec-cell-label">RAM</span>
          <span className="spec-cell-value">{formatRam(cs.ram_gb)}</span>
        </div>
        <div className="spec-cell spec-highlight-temp">
          <span className="spec-cell-label">Op Temp</span>
          <span className="spec-cell-value">{formatTemp(co.op_temp_min_c, co.op_temp_max_c)}</span>
        </div>
      </div>

      {/* Additional Info */}
      <div className="card-extra">
        <div className="extra-row">
          <span className="extra-label">OS</span>
          <span className="extra-value">{formatOS(cs.os_support)}</span>
        </div>
        <div className="extra-row">
          <span className="extra-label">I/O</span>
          <span className="extra-value small">{formatConnectivity(cs.connectivity)}</span>
        </div>
        {cs.dimensions && (cs.dimensions.width_mm || cs.dimensions.depth_mm) && (
          <div className="extra-row">
            <span className="extra-label">Size</span>
            <span className="extra-value">{formatDimensions(cs.dimensions)}</span>
          </div>
        )}
        {cs.power_input && (
          <div className="extra-row">
            <span className="extra-label">Power</span>
            <span className="extra-value">{cs.power_input}</span>
          </div>
        )}
      </div>

      {/* Certifications */}
      {co.certifications && co.certifications.length > 0 && (
        <div className="card-certs">
          {co.certifications.map(c => (
            <span key={c} className="cert-chip">{c}</span>
          ))}
        </div>
      )}

      {/* NRND Warning */}
      {co.lifecycle_status === 'NRND' && (
        <div className="nrnd-warning">⚠ Not Recommended for New Designs</div>
      )}
    </div>
  );
}
