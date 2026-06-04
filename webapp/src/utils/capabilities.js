/**
 * Capability model for solution bundling.
 *
 * Two questions this module answers:
 *   1. What I/O "functions" does a host board provide natively?
 *   2. What function does an EP (expansion) card add, and which host slot does it consume?
 *
 * A "function" is a canonical capability key (ethernet, can, wifi, …). The RFQ
 * parser emits these same keys as `required_functions`, so the solution builder
 * can diff "required" against "host provides" to find the gap, then fill each
 * gap with an EP card whose host_interface fits an available host slot.
 */

// ── Canonical function registry ──────────────────────────────────────────────
export const FUNCTIONS = {
  ethernet:   { label: 'Ethernet / LAN', icon: '🔌' },
  can:        { label: 'CAN Bus',        icon: '🚌' },
  serial:     { label: 'Serial (RS-232/422/485)', icon: '🔁' },
  wifi:       { label: 'Wi-Fi',          icon: '📶' },
  gnss:       { label: 'GNSS / GPS',     icon: '🛰️' },
  usb:        { label: 'USB',            icon: '🔵' },
  storage:    { label: 'Storage (SATA/NVMe)', icon: '💾' },
  poe:        { label: 'PoE',            icon: '⚡' },
  display:    { label: 'Display (HDMI/DP)', icon: '🖥️' },
  air_sensor: { label: 'Air Quality Sensing', icon: '🌫️' },
  camera:     { label: 'Camera / MIPI',  icon: '📷' },
};

// Free-text / keyword → canonical function key.
const FUNCTION_ALIASES = [
  ['ethernet',  ['ethernet', 'lan', 'gbe', 'gigabit', 'rj45', 'rj-45', '10gbe', '2.5gbe', 'nic', 'network port']],
  ['can',       ['can', 'canbus', 'can-bus', 'can bus', 'can fd', 'canfd']],
  ['serial',    ['serial', 'rs232', 'rs-232', 'rs422', 'rs-422', 'rs485', 'rs-485', 'com port', 'uart']],
  ['wifi',      ['wifi', 'wi-fi', 'wlan', 'wireless', '802.11']],
  ['gnss',      ['gnss', 'gps', 'glonass', 'galileo', 'beidou', 'positioning']],
  ['usb',       ['usb', 'type-c', 'type-a', 'usb3', 'usb2']],
  ['storage',   ['storage', 'sata', 'nvme', 'ssd', 'm.2 storage', 'disk']],
  ['poe',       ['poe', 'power over ethernet', 'poe+']],
  ['display',   ['display', 'hdmi', 'displayport', 'dp', 'vga', 'monitor', 'lvds', 'edp']],
  ['air_sensor',['air sensor', 'air quality', 'pm2.5', 'pm25', 'gas', 'co2', 'tvoc', 'pollutant']],
  ['camera',    ['camera', 'mipi', 'csi', 'gmsl', 'image sensor', 'vision']],
];

// ── OS family matching ───────────────────────────────────────────────────────
// Match on OS *family* (Windows / Linux), NOT the version number. Versions like
// Windows 10/11 or Ubuntu 18.04–24.04 are treated as compatible within the
// family and are surfaced as a textual caveat instead of a hard gate, because
// minor-version support is usually compatible but may need PM verification.
const OS_FAMILY_RULES = [
  ['windows', ['windows', 'win10', 'win11', 'win 10', 'win 11']],
  ['linux',   ['linux', 'ubuntu', 'debian', 'yocto', 'red hat', 'redhat', 'rhel', 'centos', 'fedora', 'android']],
];

/** Canonical OS family for a free-text OS string ('windows' | 'linux' | null). */
export function osFamily(str) {
  if (!str) return null;
  const t = String(str).toLowerCase();
  for (const [fam, kw] of OS_FAMILY_RULES) {
    if (kw.some(k => t.includes(k))) return fam;
  }
  return null;
}

/** Extract a version token from an OS string ("Windows 11"→"11", "Ubuntu 22.04"→"22.04"), or null. */
export function osVersion(str) {
  if (!str) return null;
  const m = String(str).match(/(\d+(?:\.\d+)?)/);
  return m ? m[1] : null;
}

/** Human label for an OS family key. */
export function osFamilyLabel(fam) {
  return fam === 'windows' ? 'Windows' : fam === 'linux' ? 'Linux' : fam || '';
}

/** Normalize a single free-text token/phrase to a canonical function key, or null. */
export function normalizeFunction(token) {
  if (!token) return null;
  const t = String(token).toLowerCase().trim();
  if (FUNCTIONS[t]) return t; // already canonical
  for (const [key, aliases] of FUNCTION_ALIASES) {
    if (aliases.some(a => t === a || t.includes(a))) return key;
  }
  return null;
}

// ── Host capabilities ────────────────────────────────────────────────────────

/** Set of canonical functions a host board provides natively. */
export function getHostProvides(host) {
  const cs = host.computing_spec || {};
  const provides = new Set();

  // From the connectivity token list (DP, GbE, CAN, USB3, SATA, MIPI, WiFi…)
  for (const tok of cs.connectivity || []) {
    const f = normalizeFunction(tok);
    if (f) provides.add(f);
  }

  // From structured io_ports (more authoritative than the token list)
  const io = cs.io_ports || {};
  if (nonEmpty(io.gbe)) provides.add('ethernet');
  if (nonEmpty(io.usb)) provides.add('usb');
  if (nonEmpty(io.serial)) provides.add('serial');
  if (countOf(io.can_bus_count) > 0 || nonEmpty(io.can)) provides.add('can');
  if (nonEmpty(io.display_outputs) || nonEmpty(cs.display_outputs)) provides.add('display');

  // Camera is never "onboard": it always needs a physical module. The host only
  // exposes an *interface* for it — so we don't mark camera as natively provided;
  // it is satisfied by pairing a compatible camera module (see getHostSlots).
  provides.delete('camera');

  return provides;
}

/** Sum a `count` field across an io_ports array (or accept a bare number). */
function sumPorts(v) {
  if (Array.isArray(v)) return v.reduce((n, x) => n + countOf(x?.count, 1), 0);
  return countOf(v);
}

/**
 * How many ports/units of a canonical function the host provides natively.
 * Port-type functions (usb/ethernet/serial/can/display) return real counts;
 * boolean-ish functions (wifi/gnss/poe/storage/camera) return 1 if present.
 */
export function getHostFunctionCount(host, fn) {
  const cs = host.computing_spec || {};
  const io = cs.io_ports || {};
  switch (fn) {
    case 'usb':      return sumPorts(io.usb);
    case 'ethernet': return sumPorts(io.gbe);
    case 'serial':   return sumPorts(io.serial);
    case 'can':      return countOf(io.can_bus_count) || (sumPorts(io.can));
    case 'display':  return (cs.display_outputs || io.display_outputs || []).length
                          || (cs.connectivity || []).filter(t => /HDMI|DP|VGA|DISPLAY/i.test(t)).length;
    case 'camera':   return 0; // always needs a module
    default:         return getHostProvides(host).has(fn) ? 1 : 0;
  }
}

/**
 * Infer an EP card's port count from its 12-char part number.
 * Position 7 ("Output items", per EP_Naming_Rule) = the digit right after the
 * dash in the 2nd segment: `EMP2-X801`→8, `EMU2-X1S1`→1, `EGP2-X4S1`→4.
 * Returns null when that position is a letter (F/I/L/N/P/R/S/W — a type code,
 * not a count) or the part number doesn't match the pattern.
 */
export function inferCardPortCount(partNo) {
  if (!partNo) return null;
  const seg = String(partNo).split('-')[1];
  if (!seg || seg.length < 2) return null;
  const ch = seg[1];
  if (!/[0-9]/.test(ch)) return null;
  const n = Number(ch);
  return n > 0 ? n : null;
}

/** How many ports/units of `fn` a single EP/camera card contributes. */
export function getCardCapacity(card, fn) {
  if (card.meta.product_line === 'camera') return 1;
  const spec = card.networking_spec || card.io_spec || {};
  if (spec.port_count != null) return countOf(spec.port_count, 1);
  // port_count is often missing in the catalog — recover it from the part number.
  const inferred = inferCardPortCount(card.meta.part_no);
  return inferred || 1;
}

/**
 * Camera interfaces a host can drive (MIPI / USB / PCIe / GMSL), as a count map.
 * USB and PCIe are shared with the general slot pool; MIPI/GMSL are camera-only.
 */
export function getHostCameraInterfaces(host) {
  const cs = host.computing_spec || {};
  const tokens = (cs.connectivity || []).map(t => String(t).toUpperCase());
  return {
    MIPI: tokens.some(t => t.includes('MIPI') || t.includes('CSI')) ? 4 : 0,
    GMSL: tokens.some(t => t.includes('GMSL')) ? 4 : 0,
  };
}

/**
 * Available expansion slots on a host, as a consumable count map.
 * EP cards are placed by decrementing these.
 */
export function getHostSlots(host) {
  const cs = host.computing_spec || {};
  const slots = { 'M.2': 0, 'PCIe': 0, 'USB': 0 };

  for (const s of cs.m2_slots || []) slots['M.2'] += countOf(s.count, 1);
  for (const s of cs.pcie_slots || []) slots['PCIe'] += countOf(s.count, 1);

  // USB ports can host USB EP cards/dongles (WiFi, GNSS, USB cameras, some I/O)
  const usb = (cs.io_ports || {}).usb;
  if (Array.isArray(usb)) {
    slots['USB'] += usb.reduce((n, u) => n + countOf(u.count, 1), 0);
  } else if (countOf(usb) > 0) {
    slots['USB'] += countOf(usb);
  }

  // Camera-only interfaces (MIPI / GMSL). USB/PCIe cameras reuse the slots above.
  Object.assign(slots, getHostCameraInterfaces(host));
  return slots;
}

// ── EP card capabilities ─────────────────────────────────────────────────────

const SUBCAT_TO_FUNCTION = {
  'CAN-Bus': 'can',
  'LAN': 'ethernet',
  'PoE': 'poe',
  'Serial': 'serial',
  'GNSS': 'gnss',
  'WiFi': 'wifi',
  'Storage': 'storage',
  'Virtual IO': 'usb',
};

/** The primary canonical function an EP card provides (or null). */
export function getCardFunction(card) {
  const line = card.meta.product_line;
  if (line === 'air_sensor') return 'air_sensor';
  if (line === 'camera') return 'camera';

  const spec = card.networking_spec || card.io_spec || {};
  const sub = spec.subcategory;
  if (sub && SUBCAT_TO_FUNCTION[sub]) return SUBCAT_TO_FUNCTION[sub];

  // Fallback: infer from part description / module tags
  for (const tok of card.meta.module_tags || card.search?.tags || []) {
    const f = normalizeFunction(tok);
    if (f) return f;
  }
  // Last resort: line-level default
  if (line === 'networking') return 'ethernet';
  if (line === 'io') return 'usb';
  return null;
}

/** The host slot/interface type a card consumes: 'M.2'|'PCIe'|'USB'|'MIPI'|'GMSL'|null. */
export function getCardInterface(card) {
  const line = card.meta.product_line;

  // Camera modules consume a camera interface derived from interface_bus.
  if (line === 'camera') {
    const bus = String(card.camera_spec?.interface_bus || '').toUpperCase();
    if (bus.includes('GMSL')) return 'GMSL';
    if (bus.includes('MIPI') || bus.includes('CSI')) return 'MIPI';
    if (bus.includes('USB')) return 'USB';
    if (bus.includes('PCIE') || bus.includes('PCI')) return 'PCIe';
    return null;
  }

  const spec = card.networking_spec || card.io_spec || {};
  const hi = spec.host_interface;
  if (!hi) return line === 'air_sensor' ? 'USB' : null;
  const h = String(hi).toUpperCase();
  if (h.includes('M.2') || h.includes('M2')) return 'M.2';
  if (h.includes('PCIE') || h.includes('PCI')) return 'PCIe';
  if (h.includes('USB')) return 'USB';
  return null;
}

/**
 * Can a slot of `cardIface` be satisfied by an available host slot map?
 * PCIe cards can also drop into a free PCIe slot only; M.2 into M.2; USB into USB.
 * We allow a small fallback: an M.2 (key M, PCIe) card may use a PCIe slot.
 */
export function findSlotFor(cardIface, slots) {
  if (!cardIface) return null;
  if (slots[cardIface] > 0) return cardIface;
  // graceful fallback chains
  if (cardIface === 'M.2' && slots['PCIe'] > 0) return 'PCIe';
  return null;
}

// ── small helpers ────────────────────────────────────────────────────────────
function nonEmpty(v) {
  if (v == null) return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === 'object') return Object.keys(v).length > 0;
  if (typeof v === 'number') return v > 0;
  return Boolean(v);
}
function countOf(v, dflt = 0) {
  const n = Number(v);
  if (Number.isFinite(n) && n > 0) return n;
  return dflt;
}
