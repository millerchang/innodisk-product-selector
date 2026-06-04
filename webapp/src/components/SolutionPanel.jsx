import { functionLabel, functionIcon } from '../utils/solution';
import { downloadQuoteCSV, printQuote } from '../utils/exportSolution';
import { getProductLineLabel, getPlatformIcon, formatTops, formatTdp, formatTemp } from '../utils/formatters';

/**
 * Renders a complete RFQ solution bundle:
 *   host board  +  EP add-on cards (one per I/O gap)  +  unfilled-gap warnings.
 */
export default function SolutionPanel({ solution, onSelectHost, onToggleSelect, selectedForCompare = [], rfqText = '' }) {
  if (!solution) return null;
  const { host, addOns = [], unfilledGaps = [], requiredFns = [], coverage = [], alternativeHosts = [], osNotes = [] } = solution;

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

  // Only surface requirements that need attention: those topped up by EP cards,
  // and those that can't be met. Natively-covered functions are not shown.
  const cardFilled = coverage.filter(c => c.covered && c.fromCards > 0);
  const missing = coverage.filter(c => !c.covered);

  // Smooth-scroll to the matching add-on card and briefly highlight it.
  const jumpToCard = partNo => {
    const el = document.getElementById(`addon-${partNo}`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.add('addon-flash');
    setTimeout(() => el.classList.remove('addon-flash'), 1400);
  };

  return (
    <div className="solution-panel">
      <div className="solution-head">
        <h3 className="solution-title">
          <svg className="solution-title-icon" width="20" height="20" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2 2 7l10 5 10-5-10-5Z" />
            <path d="m2 17 10 5 10-5" />
            <path d="m2 12 10 5 10-5" />
          </svg>
          Recommended Solution Bundle
        </h3>
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

      {/* Coverage notes — only functions that need an add-on card, or can't be met.
          Natively-covered functions are intentionally not listed. */}
      {(cardFilled.length > 0 || missing.length > 0) && (
        <div className="solution-reqs">
          {cardFilled.map(c => {
            const qty = c.need > 1 ? ` ×${c.need}` : '';
            return (
              <div key={c.fn} className="req-row req-card">
                <span className="req-row-label">
                  {functionIcon(c.fn)} {functionLabel(c.fn)}{qty}
                </span>
                <span className="req-row-detail">
                  {c.hostHave > 0
                    ? `${c.hostHave} built-in + ${c.fromCards} via add-on card:`
                    : `${c.fromCards} via add-on card:`}
                </span>
                <span className="req-row-cards">
                  {c.cards.map(x => (
                    <button
                      key={x.card.meta.part_no}
                      className="req-card-link"
                      onClick={() => jumpToCard(x.card.meta.part_no)}
                      title="Jump to this add-on card"
                    >
                      {x.card.meta.part_no}
                    </button>
                  ))}
                </span>
              </div>
            );
          })}
          {missing.map(c => {
            const qty = c.need > 1 ? ` ×${c.need}` : '';
            return (
              <div key={c.fn} className="req-row req-missing">
                <span className="req-row-label">
                  ⚠ {functionIcon(c.fn)} {functionLabel(c.fn)}{qty}
                </span>
                <span className="req-row-detail">
                  Customer needs {c.need}; only {c.total} available — short {c.shortfall}.
                  No compatible add-on card / slot to make up the gap.
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* OS version compatibility caveats */}
      {osNotes.length > 0 && (
        <div className="solution-os-notes">
          {osNotes.map((n, i) => (
            <p key={i} className="os-note">ℹ {n}</p>
          ))}
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
              <div key={card.meta.part_no} id={`addon-${card.meta.part_no}`} className="bundle-card addon-card">
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
