import {
  formatTemp, formatTops, formatRam, formatTdp, formatConnectivity, formatOS,
  formatDimensions, getProductLineLabel,
} from '../utils/formatters';

const SPEC_ROWS = [
  { label: 'Product Line',   fn: p => getProductLineLabel(p.meta.product_line) },
  { label: 'BU Owner',       fn: p => p.meta.bu_owner || '—' },
  { label: 'Platform',       fn: p => p.computing_spec?.platform_brand || '—' },
  { label: 'Processor',      fn: p => p.computing_spec?.processor_model || p.computing_spec?.platform_brand || '—', wide: true },
  { label: 'AI TOPS',        fn: p => formatTops(p.computing_spec?.ai_tops, p.computing_spec?.ai_tops_basis), highlight: true },
  { label: 'TDP',            fn: p => formatTdp(p.computing_spec?.tdp_watt) },
  { label: 'RAM',            fn: p => formatRam(p.computing_spec?.ram_gb) },
  { label: 'Op Temp',        fn: p => formatTemp(p.common?.op_temp_min_c, p.common?.op_temp_max_c), highlight: true },
  { label: 'Temp Grade',     fn: p => p.common?.temp_grade || '—' },
  { label: 'OS Support',     fn: p => formatOS(p.computing_spec?.os_support) },
  { label: 'Connectivity',   fn: p => formatConnectivity(p.computing_spec?.connectivity), wide: true },
  { label: 'Display Output', fn: p => (p.computing_spec?.display_outputs || []).join(', ') || '—' },
  { label: 'Storage I/F',    fn: p => (p.computing_spec?.storage_interfaces || []).join(', ') || '—' },
  { label: 'Dimensions',     fn: p => formatDimensions(p.computing_spec?.dimensions) },
  { label: 'Power Input',    fn: p => p.computing_spec?.power_input || '—' },
  { label: 'Certifications', fn: p => (p.common?.certifications || []).join(', ') || '—' },
  { label: 'Lifecycle',      fn: p => p.common?.lifecycle_status || '—' },
];

export default function ComparisonPanel({ products, onClose, onRemove }) {
  if (!products.length) return null;

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
                      <strong>{p.meta.part_no}</strong>
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
              {SPEC_ROWS.map(row => (
                <tr key={row.label} className={row.highlight ? 'row-highlight' : ''}>
                  <td className="spec-row-label">{row.label}</td>
                  {products.map(p => (
                    <td key={p.meta.part_no} className={`spec-row-value ${row.highlight ? 'value-highlight' : ''}`}>
                      {row.fn(p)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
