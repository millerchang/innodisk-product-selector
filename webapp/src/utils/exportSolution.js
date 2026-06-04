/**
 * Export a solution bundle as a quote / BOM:
 *   - downloadQuoteCSV(): a spreadsheet-friendly CSV file
 *   - printQuote():       a formatted, print-to-PDF view in a new window
 */
import { functionLabel } from './solution';
import { getProductLineLabel } from './formatters';

/** Flatten a solution into BOM line items (host first, then add-on cards). */
export function solutionToLineItems(solution) {
  const items = [];
  if (!solution?.host) return items;

  const h = solution.host;
  const hcs = h.computing_spec || {};
  items.push({
    role: 'Host',
    part_no: h.meta.part_no,
    line: getProductLineLabel(h.meta.product_line),
    description: hcs.processor_model || hcs.platform_brand || '—',
    fills: '',
    slot: '',
    qty: 1,
    lifecycle: h.common?.lifecycle_status || '—',
  });

  for (const { card, fillsFunction, slot } of solution.addOns || []) {
    const isCam = card.meta.product_line === 'camera';
    const spec = card.networking_spec || card.io_spec || card.air_sensor_spec || {};
    const description = isCam
      ? `Camera ${card.camera_spec?.resolution_mp != null ? `${card.camera_spec.resolution_mp}MP ` : ''}${card.camera_spec?.interface_bus || ''}`.trim()
      : (spec.subcategory || getProductLineLabel(card.meta.product_line));
    items.push({
      role: 'Add-on',
      part_no: card.meta.part_no,
      line: getProductLineLabel(card.meta.product_line),
      description,
      fills: functionLabel(fillsFunction),
      slot,
      qty: 1,
      lifecycle: card.common?.lifecycle_status || '—',
    });
  }
  return items;
}

function csvCell(v) {
  const s = String(v ?? '');
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function timestamp() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
}

/** Build the CSV text for a solution. */
export function buildQuoteCSV(solution, rfqText = '') {
  const items = solutionToLineItems(solution);
  const lines = [];

  lines.push(['Innodisk Product Selector — Solution Quote']);
  lines.push(['Generated', new Date().toLocaleString()]);
  if (rfqText) lines.push(['Customer RFQ', rfqText]);
  if (solution?.requirements?.length) {
    lines.push(['Requested Functions', solution.requirements
      .map(r => `${functionLabel(r.fn)}${r.count > 1 ? ` x${r.count}` : ''}`).join('; ')]);
  }
  const unmet = (solution?.coverage || []).filter(c => !c.covered);
  if (unmet.length) {
    lines.push(['UNFILLED', unmet
      .map(c => `${functionLabel(c.fn)} (need ${c.need}, got ${c.total})`).join('; ')]);
  }
  lines.push([]); // blank row
  lines.push(['#', 'Role', 'Part No', 'Product Line', 'Description', 'Fills Function', 'Slot', 'Qty', 'Lifecycle']);
  items.forEach((it, i) => {
    lines.push([i + 1, it.role, it.part_no, it.line, it.description, it.fills, it.slot, it.qty, it.lifecycle]);
  });

  return lines.map(row => row.map(csvCell).join(',')).join('\r\n');
}

/** Trigger a CSV file download. */
export function downloadQuoteCSV(solution, rfqText = '') {
  const csv = '﻿' + buildQuoteCSV(solution, rfqText); // BOM for Excel UTF-8
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const pn = solution?.host?.meta.part_no || 'solution';
  a.href = url;
  a.download = `quote_${pn}_${timestamp()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function esc(s) {
  return String(s ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

/** Open a formatted, printable quote in a new window and invoke print. */
export function printQuote(solution, rfqText = '') {
  const items = solutionToLineItems(solution);
  const rows = items.map((it, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><span class="role role-${it.role === 'Host' ? 'host' : 'addon'}">${esc(it.role)}</span></td>
      <td class="pn">${esc(it.part_no)}</td>
      <td>${esc(it.line)}</td>
      <td>${esc(it.description)}</td>
      <td>${esc(it.fills)}</td>
      <td>${esc(it.slot)}</td>
      <td>${it.qty}</td>
      <td>${esc(it.lifecycle)}</td>
    </tr>`).join('');

  const reqLine = solution?.requirements?.length
    ? `<p><strong>Requested functions:</strong> ${esc(solution.requirements.map(r => `${functionLabel(r.fn)}${r.count > 1 ? ` ×${r.count}` : ''}`).join(' · '))}</p>` : '';
  const unmet = (solution?.coverage || []).filter(c => !c.covered);
  const gapLine = unmet.length
    ? `<p class="warn"><strong>⚠ Unfilled:</strong> ${esc(unmet.map(c => `${functionLabel(c.fn)} (need ${c.need}, got ${c.total})`).join(' · '))}</p>` : '';
  const rfqLine = rfqText ? `<p><strong>Customer RFQ:</strong> ${esc(rfqText)}</p>` : '';

  const html = `<!doctype html><html><head><meta charset="utf-8"><title>Innodisk Solution Quote</title>
  <style>
    body { font-family: -apple-system, 'Segoe UI', system-ui, sans-serif; color: #1E293B; margin: 32px; }
    h1 { font-size: 20px; margin: 0 0 4px; }
    .sub { color: #64748B; font-size: 12px; margin-bottom: 16px; }
    p { font-size: 13px; margin: 4px 0; }
    .warn { color: #B45309; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }
    th, td { border: 1px solid #E2E8F0; padding: 6px 8px; text-align: left; }
    th { background: #F1F5F9; }
    .pn { font-weight: 700; }
    .role { font-size: 11px; padding: 1px 8px; border-radius: 999px; }
    .role-host { background: #DBEAFE; color: #1D4ED8; }
    .role-addon { background: #F1F5F9; color: #475569; }
    .foot { margin-top: 18px; color: #94A3B8; font-size: 11px; }
    @media print { body { margin: 12mm; } }
  </style></head><body>
    <h1>Innodisk Product Selector — Solution Quote</h1>
    <div class="sub">Generated ${esc(new Date().toLocaleString())}</div>
    ${rfqLine}${reqLine}${gapLine}
    <table>
      <thead><tr>
        <th>#</th><th>Role</th><th>Part No</th><th>Product Line</th><th>Description</th>
        <th>Fills Function</th><th>Slot</th><th>Qty</th><th>Lifecycle</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div class="foot">This is a configuration proposal, not a price quotation. Verify availability with your Innodisk sales contact.</div>
  </body></html>`;

  const w = window.open('', '_blank');
  if (!w) {
    alert('Pop-up blocked. Please allow pop-ups to print the quote.');
    return;
  }
  w.document.open();
  w.document.write(html);
  w.document.close();
  w.focus();
  // Give the new window a tick to render before printing.
  setTimeout(() => w.print(), 250);
}
