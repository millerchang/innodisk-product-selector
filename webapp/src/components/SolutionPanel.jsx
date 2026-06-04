import { functionLabel, functionIcon } from '../utils/solution';
import { downloadQuoteCSV, printQuote } from '../utils/exportSolution';
import { getProductLineLabel, getPlatformIcon, formatTops, formatTdp, formatTemp } from '../utils/formatters';

/**
 * Renders a complete RFQ solution bundle:
 *   host board  +  EP add-on cards (one per I/O gap)  +  unfilled-gap warnings.
 */
export default function SolutionPanel({ solution, onSelectHost, onToggleSelect, selectedForCompare = [], rfqText = '' }) {
  if (!solution) return null;
  const { host, addOns = [], unfilledGaps = [], requiredFns = [], coverage = [], alternativeHosts = [] } = solution;

  if (!host) {
    return (
      <div className="solution-panel solution-empty">
        <h3>⚠ No compute host meets the hard constraints</h3>
        <p>Relax the TOPS / TDP / temperature / OS requirements, or rephrase the RFQ.</p>
        {requiredFns.length > 0 && (
          <p className="solution-req">
            Requested functions: {requiredFns.map(f => `${functionIcon(f)} ${functionLabel(f)}`).join(' · ')}
          </p>
        )}
      </div>
    );
  }

  const cs = host.computing_spec || {};
  const co = host.common || {};
  const fullyCovered = unfilledGaps.length === 0;

  return (
    <div className="solution-panel">
      <div className="solution-head">
        <h3 className="solution-title">📦 Recommended Solution Bundle</h3>
        <div className="solution-head-right">
          <span className={`solution-status ${fullyCovered ? 'ok' : 'warn'}`}>
            {fullyCovered
              ? '✓ All requested functions covered'
              : `⚠ ${unfilledGaps.length} function(s) not covered`}
          </span>
          <button className="export-btn" onClick={() => downloadQuoteCSV(solution, rfqText)} title="Download BOM as CSV">
            ⬇ CSV
          </button>
          <button className="export-btn" onClick={() => printQuote(solution, rfqText)} title="Print / Save as PDF">
            🖨 Print
          </button>
        </div>
      </div>

      {/* Requested function checklist — quantity-aware */}
      {coverage.length > 0 && (
        <div className="solution-reqs">
          {coverage.map(c => {
            const status = !c.covered ? 'missing' : c.fromCards > 0 ? 'card' : 'native';
            const qty = c.need > 1 ? ` ×${c.need}` : '';
            let detail;
            if (status === 'native') detail = ` · onboard (${c.hostHave})`;
            else if (status === 'card') detail = ` · host ${c.hostHave} + ${c.cards.length} card${c.cards.length > 1 ? 's' : ''} = ${c.total}`;
            else detail = ` · ✗ short ${c.shortfall} (got ${c.total})`;
            return (
              <span key={c.fn} className={`req-chip req-${status}`} title={c.cards.map(x => x.card.meta.part_no).join(', ')}>
                {functionIcon(c.fn)} {functionLabel(c.fn)}{qty}{detail}
              </span>
            );
          })}
        </div>
      )}

      {/* Host board */}
      <div className="solution-host">
        <div className="bundle-row-label">HOST</div>
        <div className="bundle-card host-card" onClick={() => onSelectHost?.(host)}>
          <span className="platform-icon">{getPlatformIcon(cs.platform_brand)}</span>
          <div className="bundle-card-body">
            <div className="bundle-card-title">{host.meta.part_no}</div>
            <div className="bundle-card-sub">
              {cs.processor_model || cs.platform_brand || '—'} · {getProductLineLabel(host.meta.product_line)}
            </div>
            <div className="bundle-card-specs">
              <span>{formatTops(cs.ai_tops)}</span>
              <span>{formatTdp(cs.tdp_watt)}</span>
              <span>{formatTemp(co.op_temp_min_c, co.op_temp_max_c)}</span>
            </div>
          </div>
          <label className="compare-toggle" onClick={e => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={selectedForCompare.includes(host.meta.part_no)}
              onChange={() => onToggleSelect?.(host.meta.part_no)}
            />
            <span>Compare</span>
          </label>
        </div>
      </div>

      {/* Add-on EP cards */}
      {addOns.length > 0 && (
        <div className="solution-addons">
          <div className="bundle-row-label">ADD-ON EP CARDS</div>
          {addOns.map(({ card, fillsFunction, slot }) => {
            const isCam = card.meta.product_line === 'camera';
            const cam = card.camera_spec || {};
            const spec = card.networking_spec || card.io_spec || card.air_sensor_spec || {};
            const sub = isCam
              ? (cam.interface_bus ? `Camera · ${cam.interface_bus}` : 'Camera')
              : (spec.subcategory || getProductLineLabel(card.meta.product_line));
            return (
              <div key={card.meta.part_no} className="bundle-card addon-card">
                <span className="addon-fn-icon">{functionIcon(fillsFunction)}</span>
                <div className="bundle-card-body">
                  <div className="bundle-card-title">{card.meta.part_no}</div>
                  <div className="bundle-card-sub">
                    {sub}
                    {' · fills '}<strong>{functionLabel(fillsFunction)}</strong>
                  </div>
                  <div className="bundle-card-specs">
                    <span className="slot-badge">uses {slot} {slot === 'MIPI' || slot === 'GMSL' ? 'interface' : 'slot'}</span>
                    {isCam && cam.resolution_mp != null && <span>{cam.resolution_mp} MP</span>}
                    {isCam && cam.fps != null && <span>{cam.fps} fps</span>}
                    {!isCam && spec.port_count != null && <span>{spec.port_count} port</span>}
                    {!isCam && spec.speed_gbps != null && <span>{spec.speed_gbps} Gbps</span>}
                  </div>
                </div>
                <label className="compare-toggle" onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedForCompare.includes(card.meta.part_no)}
                    onChange={() => onToggleSelect?.(card.meta.part_no)}
                  />
                  <span>Compare</span>
                </label>
              </div>
            );
          })}
        </div>
      )}

      {/* Unfilled gaps (with quantity shortfall) */}
      {unfilledGaps.length > 0 && (
        <div className="solution-unfilled">
          <div className="bundle-row-label warn">UNFILLED</div>
          <p>
            Could not meet the requested quantity for:{' '}
            {coverage.filter(c => !c.covered).map(c =>
              `${functionIcon(c.fn)} ${functionLabel(c.fn)} (need ${c.need}, got ${c.total})`
            ).join(' · ')}.
            Consider a host with more of these ports onboard, or an external module.
          </p>
        </div>
      )}

      {/* Alternative hosts */}
      {alternativeHosts.length > 0 && (
        <div className="solution-alts">
          <span className="alts-label">Alternative hosts:</span>
          {alternativeHosts.map(h => (
            <button key={h.meta.part_no} className="alt-chip" onClick={() => onSelectHost?.(h)}>
              {h.meta.part_no}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
