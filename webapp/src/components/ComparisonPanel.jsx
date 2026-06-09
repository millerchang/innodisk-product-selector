import {
  formatTemp, formatTops, formatRam, formatTdp, formatConnectivity, formatOS,
  formatDimensions, getProductLineLabel,
} from '../utils/formatters';

/** The EP / add-on spec block for a product, whichever line it belongs to. */
function epSpec(p) {
  return p.networking_spec || p.io_spec || p.air_sensor_spec || {};
}

const EMPTY = new Set([null, undefined, '', '—', 'N/A']);
const isEmpty = v => EMPTY.has(v) || (Array.isArray(v) && v.length === 0);

// Candidate rows across ALL product lines. A row is rendered only if at least
// one selected product yields a non-empty value, so a comparison of pure EP
// cards hides the computing rows and vice-versa.
const ALL_ROWS = [
  // ── Always-relevant ────────────────────────────────────────────────
  { label: 'Product Line',   always: true, fn: p => getProductLineLabel(p.meta.product_line) },
  { label: 'BU Owner',       fn: p => p.meta.bu_owner || '—' },
  { label: 'Lifecycle',      always: true, fn: p => p.common?.lifecycle_status || '—' },
  { label: 'Op Temp',        highlight: true, fn: p => formatTemp(p.common?.op_temp_min_c, p.common?.op_temp_max_c) },
  { label: 'Temp Grade',     fn: p => p.common?.temp_grade || '—' },
  { label: 'Certifications', fn: p => (p.common?.certifications || []).join(', ') || '—' },

  // ── Computing hosts ────────────────────────────────────────────────
  { label: 'Platform',       fn: p => p.computing_spec?.platform_brand || '—' },
  { label: 'Processor',      wide: true, fn: p => p.computing_spec?.processor_model || p.computing_spec?.platform_brand || '—' },
  { label: 'AI TOPS',        highlight: true, fn: p => formatTops(p.computing_spec?.ai_tops, p.computing_spec?.ai_tops_basis) },
  { label: 'TDP',            fn: p => formatTdp(p.computing_spec?.tdp_watt) },
  { label: 'RAM',            fn: p => formatRam(p.computing_spec?.ram_gb) },
  { label: 'OS Support',     fn: p => formatOS(p.computing_spec?.os_support) },
  { label: 'Connectivity',   wide: true, fn: p => formatConnectivity(p.computing_spec?.connectivity) },
  { label: 'Display Output', fn: p => (p.computing_spec?.display_outputs || []).join(', ') || '—' },
  { label: 'Storage I/F',    fn: p => (p.computing_spec?.storage_interfaces || []).join(', ') || '—' },
  { label: 'Dimensions',     fn: p => formatDimensions(p.computing_spec?.dimensions) },
  { label: 'Power Input',    fn: p => p.computing_spec?.power_input || '—' },

  // ── Camera ────────────────────────────────────────────────────────
  { label: 'Interface',      fn: p => p.camera_spec?.interface_bus || '—' },
  { label: 'Resolution',     highlight: true, fn: p => { const c = p.camera_spec; if (!c) return '—'; return c.resolution_mp ? `${c.resolution_mp}MP (${c.resolution_px || '—'})` : '—'; } },
  { label: 'Sensor',         fn: p => p.camera_spec?.sensor_model || '—' },
  { label: 'Sensor Size',    fn: p => p.camera_spec?.sensor_size || '—' },
  { label: 'Pixel Size',     fn: p => p.camera_spec?.pixel_size_um != null ? `${p.camera_spec.pixel_size_um} µm` : '—' },
  { label: 'Frame Rate',     fn: p => p.camera_spec?.fps != null ? `${p.camera_spec.fps} fps` : '—' },
  { label: 'Dynamic Range',  fn: p => p.camera_spec?.dynamic_range_db != null ? `${p.camera_spec.dynamic_range_db} dB` : (p.camera_spec?.hdr ? 'HDR' : '—') },
  { label: 'Lens Type',      fn: p => p.camera_spec?.lens_type || '—' },
  { label: 'HDR',            fn: p => p.camera_spec == null ? '—' : (p.camera_spec.hdr ? 'Yes' : 'No') },
  { label: 'Low Light',      fn: p => p.camera_spec == null ? '—' : (p.camera_spec.low_light ? 'Yes' : 'No') },

  // ── Computing — USB (總數 + 明細，供比對用) ──────────────────────
  { label: 'USB Total',      highlight: true, fn: p => { const usb = p.computing_spec?.io_ports?.usb; if (!usb?.length) return '—'; return `×${usb.reduce((s,u)=>s+u.count,0)}`; } },
  { label: 'USB Detail',     wide: true, fn: p => { const usb = p.computing_spec?.io_ports?.usb; if (!usb?.length) return '—'; return usb.map(u => u.connector ? `${u.count}× ${u.standard} (${u.connector})` : `${u.count}× ${u.standard}`).join(', '); } },

  // ── EP / add-on cards (io / networking / air_sensor) ───────────────
  { label: 'Category',       fn: p => epSpec(p).subcategory || '—' },
  { label: 'Host Interface', fn: p => epSpec(p).host_interface || '—' },
  { label: 'PCIe',           fn: p => { const s = epSpec(p); return s.pcie_gen ? `Gen${s.pcie_gen}${s.pcie_lanes ? ` x${s.pcie_lanes}` : ''}` : '—'; } },
  { label: 'Ports',          fn: p => { const s = epSpec(p); if (s.port_count == null) return '—'; return `${s.port_count}${s.port_type?.length ? ` (${s.port_type.join('/')})` : ''}`; } },
  { label: 'Speed',          highlight: true, fn: p => { const s = epSpec(p); return s.speed_gbps != null ? `${s.speed_gbps} Gbps` : '—'; } },
  { label: 'Protocol',       wide: true, fn: p => (epSpec(p).protocol || []).join(', ') || '—' },
  { label: 'PoE',            fn: p => { const s = epSpec(p); return s.poe_watt != null ? `${s.poe_watt} W` : '—'; } },
  { label: 'CAN FD',         fn: p => { const s = epSpec(p); return s.can_fd_support == null ? '—' : (s.can_fd_support ? 'Yes' : 'No'); } },
  { label: 'Isolation',      fn: p => { const s = epSpec(p); return s.isolation == null ? '—' : (s.isolation ? 'Yes' : 'No'); } },
  { label: 'Detects',        wide: true, fn: p => (p.air_sensor_spec?.detected_pollutants || []).join(', ') || '—' },
  { label: 'Sensor Bus',     fn: p => p.air_sensor_spec?.interface_bus || '—' },
  { label: 'PM2.5 Accuracy', fn: p => { const a = p.air_sensor_spec?.accuracy_pm25_ug; return a != null ? `±${a} µg/m³` : '—'; } },
  { label: 'EP OS Support',  fn: p => (epSpec(p).supported_os || []).join(', ') || '—' },
  { label: 'Driver',         fn: p => { const s = epSpec(p); return s.driver_required == null ? '—' : (s.driver_required ? 'Required' : 'Built-in'); } },
  { label: 'Sourcing',       fn: p => { const s = epSpec(p); if (!s.sourcing) return '—'; return s.source_vendor ? `${s.sourcing} (${s.source_vendor})` : s.sourcing; } },
];

export default function ComparisonPanel({ products, onClose, onRemove }) {
  if (!products.length) return null;

  // Keep only rows that at least one product has a value for (or always-rows).
  const rows = ALL_ROWS.filter(
    r => r.always || products.some(p => !isEmpty(r.fn(p)))
  );

  return (
    <div className="comparison-overlay" onClick={onClose}>
      <div className="comparison-panel" onClick={e => e.stopPropagation()}>
        <div className="comparison-header">
          <h2>Side-by-Side Comparison</h2>
          <div className="comparison-header-actions">
            <span className="comparison-count">{products.length} products</span>
            <button className="btn btn-secondary" onClick={onClose}>Close ✕</button>
          </div>
        </div>

        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th className="spec-col-header">Specification</th>
                {products.map(p => (
                  <th key={p.meta.part_no} className="product-col-header">
                    <div className="col-header-inner">
                      <div className="col-header-text">
                        <strong>{p.meta.part_no}</strong>
                        <span className="col-header-line">{getProductLineLabel(p.meta.product_line)}</span>
                      </div>
                      <button
                        className="remove-col-btn"
                        onClick={() => onRemove(p.meta.part_no)}
                        title="Remove"
                      >✕</button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.label} className={row.highlight ? 'row-highlight' : ''}>
                  <td className="spec-row-label">{row.label}</td>
                  {products.map(p => {
                    const v = row.fn(p);
                    return (
                      <td key={p.meta.part_no} className={`spec-row-value ${row.highlight ? 'value-highlight' : ''}`}>
                        {isEmpty(v) ? '—' : v}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
