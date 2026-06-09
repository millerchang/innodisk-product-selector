import {
  formatTemp, formatTops, formatRam, formatTdp, formatConnectivity, formatOS, formatDimensions,
  getPlatformIcon, getProductLineLabel, getMatchBadge, getLifecycleStyle,
} from '../utils/formatters';

const COMPUTING_LINES = ['computing_aiot', 'computing_ipa'];

export default function ProductCard({ product, recommendedPartNos, isSelected, onToggleSelect, onCardClick }) {
  const m = product.meta;
  const co = product.common || {};
  const badge = getMatchBadge(m.part_no, recommendedPartNos);
  const lifecycle = getLifecycleStyle(co.lifecycle_status);
  const isComputing = COMPUTING_LINES.includes(m.product_line);
  const cs = product.computing_spec || {};

  return (
    <div
      className={`product-card ${isSelected ? 'card-selected' : ''} ${badge ? 'card-matched' : ''} ${onCardClick ? 'card-clickable' : ''}`}
      onClick={onCardClick ? () => onCardClick(product) : undefined}
    >

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
            {isComputing ? getPlatformIcon(cs.platform_brand) : '🧩'}
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
        <label className="compare-toggle" title={isSelected ? 'Remove from comparison' : 'Add to comparison (max 4)'}
          onClick={e => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(m.part_no)}
          />
          <span>Compare</span>
        </label>
      </div>

      {isComputing ? <ComputingBody cs={cs} co={co} /> : <EpBody product={product} co={co} />}

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

      {/* Preview note — new / in-development product */}
      {co.lifecycle_status === 'Preview' && (
        <div className="preview-note">🆕 Preview — new product, preliminary datasheet</div>
      )}
    </div>
  );
}

function ComputingBody({ cs, co }) {
  return (
    <>
      <div className="card-processor">
        {cs.processor_model || cs.platform_brand || '—'}
      </div>

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
    </>
  );
}

/** EP add-on cards (io / networking / air_sensor) + camera. */
function EpBody({ product, co }) {
  const line = product.meta.product_line;
  const spec = product.networking_spec || product.io_spec || product.air_sensor_spec || product.camera_spec || {};
  const rows = [];

  if (spec.subcategory) rows.push(['Type', spec.subcategory]);
  if (spec.host_interface) rows.push(['Host I/F', spec.host_interface]);
  if (spec.pcie_gen) rows.push(['PCIe', `Gen${spec.pcie_gen}${spec.pcie_lanes ? ` x${spec.pcie_lanes}` : ''}`]);
  if (spec.port_count != null) rows.push(['Ports', `${spec.port_count}${spec.port_type?.length ? ` (${spec.port_type.join('/')})` : ''}`]);
  if (spec.speed_gbps != null) rows.push(['Speed', `${spec.speed_gbps} Gbps`]);
  if (Array.isArray(spec.protocol) && spec.protocol.length) rows.push(['Protocol', spec.protocol.join(', ')]);
  if (spec.poe_watt != null) rows.push(['PoE', `${spec.poe_watt} W`]);
  if (spec.can_fd_support != null) rows.push(['CAN FD', spec.can_fd_support ? 'Yes' : 'No']);
  if (Array.isArray(spec.detected_pollutants) && spec.detected_pollutants.length) rows.push(['Detects', spec.detected_pollutants.join(', ')]);
  if (spec.interface_bus) rows.push(['Bus', spec.interface_bus]);
  if (Array.isArray(spec.supported_os) && spec.supported_os.length) rows.push(['OS', spec.supported_os.join(', ')]);
  if (spec.sourcing && spec.sourcing !== 'in-house') {
    rows.push(['Sourcing', spec.source_vendor ? `${spec.sourcing} (${spec.source_vendor})` : spec.sourcing]);
  }

  return (
    <>
      <div className="card-processor">{getProductLineLabel(line)}{spec.subcategory ? ` · ${spec.subcategory}` : ''}</div>
      <div className="card-extra">
        {rows.length === 0 && <div className="extra-row"><span className="extra-value small">No structured specs available</span></div>}
        {rows.map(([label, value]) => (
          <div className="extra-row" key={label}>
            <span className="extra-label">{label}</span>
            <span className="extra-value small">{value}</span>
          </div>
        ))}
        {(co.op_temp_min_c != null || co.op_temp_max_c != null) && (
          <div className="extra-row">
            <span className="extra-label">Op Temp</span>
            <span className="extra-value">{formatTemp(co.op_temp_min_c, co.op_temp_max_c)}</span>
          </div>
        )}
      </div>
    </>
  );
}
