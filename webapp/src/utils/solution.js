/**
 * Solution builder: RFQ criteria → a complete, quantity-aware product bundle.
 *
 * Flow:
 *   1. Filter hosts by the hard compute constraints (TOPS / TDP / temp / OS).
 *   2. Rank hosts; prefer ones that natively cover the most required functions
 *      *at the requested quantity* (e.g. 10 USB ports), then by TOPS.
 *   3. For the chosen host, for each required function compute how many ports it
 *      provides natively vs. how many are needed.
 *   4. Top up any shortfall with EP cards (each contributes its port_count) until
 *      the quantity is met or no compatible card/slot remains.
 *   5. Report per-function coverage + the flattened bundle (host + add-on cards).
 */
import {
  getHostProvides, getHostSlots, getCardFunction, getCardInterface, findSlotFor,
  getHostFunctionCount, getCardCapacity, normalizeFunction, FUNCTIONS,
  osFamily, osVersion, osFamilyLabel,
} from './capabilities';

/** Does a host satisfy the hard compute constraints? */
function hostMeetsConstraints(host, c) {
  if (!c) return true;
  const cs = host.computing_spec || {};
  const co = host.common || {};

  if (c.min_ai_tops != null && (cs.ai_tops == null || cs.ai_tops < c.min_ai_tops)) return false;
  if (c.max_tdp_watt != null && cs.tdp_watt != null && cs.tdp_watt > c.max_tdp_watt) return false;
  if (c.min_op_temp_c != null && (co.op_temp_min_c == null || co.op_temp_min_c > c.min_op_temp_c)) return false;
  if (c.max_op_temp_c != null && (co.op_temp_max_c == null || co.op_temp_max_c < c.max_op_temp_c)) return false;

  if (c.os_required && c.os_required.length > 0) {
    // Family-level match: a host listing "Windows" satisfies "Windows 11".
    // An OS string we can't classify into a family is not used to gate.
    const hostFamilies = new Set((cs.os_support || []).map(osFamily).filter(Boolean));
    const ok = c.os_required.some(r => {
      const fam = osFamily(r);
      return fam ? hostFamilies.has(fam) : true;
    });
    if (!ok) return false;
  }
  return true;
}

/**
 * OS version caveats: when the RFQ asks for a specific version (e.g. Windows 11,
 * Ubuntu 22.04) and the host supports that family, surface a note to verify the
 * exact version with the Product PM — the catalog records the family, not the
 * tested minor version, so we flag rather than silently assume compatibility.
 */
export function buildOsNotes(host, criteria) {
  if (!host || !criteria?.os_required?.length) return [];
  const cs = host.computing_spec || {};
  const hostFamilies = new Set((cs.os_support || []).map(osFamily).filter(Boolean));
  const notes = [];
  const seen = new Set();
  for (const req of criteria.os_required) {
    const fam = osFamily(req);
    const ver = osVersion(req);
    if (!fam || !ver || !hostFamilies.has(fam)) continue;
    const key = `${fam}:${ver}`;
    if (seen.has(key)) continue;
    seen.add(key);
    notes.push(
      `${host.meta.part_no} 支援 ${osFamilyLabel(fam)} 系統；型錄未記錄已驗證的細部版本，` +
      `請與 Product PM 確認是否已測試 ${req}。`
    );
  }
  return notes;
}

/**
 * Canonicalize required functions into [{ fn, count }].
 * Accepts plain strings ("usb"), {function, count} objects, or "usb x10" phrases.
 */
export function normalizeRequiredFunctions(list) {
  const map = new Map();
  for (const item of list || []) {
    let fnRaw, count = 1;
    if (item && typeof item === 'object') {
      fnRaw = item.function ?? item.fn ?? item.name;
      count = Number(item.count ?? item.qty ?? 1) || 1;
    } else {
      const s = String(item);
      const m = s.match(/x\s*(\d+)/i) || s.match(/(\d+)/);
      if (m) count = Number(m[1]) || 1;
      fnRaw = s;
    }
    const fn = normalizeFunction(fnRaw);
    if (!fn) continue;
    map.set(fn, Math.max(map.get(fn) || 0, count)); // keep the larger ask if dup
  }
  return [...map.entries()].map(([fn, count]) => ({ fn, count }));
}

/**
 * Pick the best EP card for a function given remaining slots, biased toward the
 * `remaining` shortfall we still need to fill; or null.
 *
 * Priority: Active lifecycle → cover as much of the shortfall as possible per
 * card (fewest cards) → lighter slot footprint (USB before PCIe) → least wasted
 * capacity. This makes serial×8 grab one 8-port PCIe card, but a small ×2 gap
 * still prefer a 2-port USB dongle over burning a PCIe slot.
 */
function pickCardForFunction(fn, epCards, freeSlots, usedPartNos, remaining = 1) {
  let best = null;
  for (const card of epCards) {
    if (usedPartNos.has(card.meta.part_no)) continue;
    if (getCardFunction(card) !== fn) continue;
    const iface = getCardInterface(card);
    const slot = findSlotFor(iface, freeSlots);
    if (!slot) continue;
    const lifeRank = card.common?.lifecycle_status === 'Active' ? 0 : 1;
    const rankMap = fn === 'camera'
      ? { MIPI: 0, GMSL: 1, USB: 2, 'M.2': 2, PCIe: 3 }
      : { USB: 0, MIPI: 1, 'M.2': 1, GMSL: 2, PCIe: 2 };
    const slotRank = rankMap[slot] ?? 3;
    const cap = getCardCapacity(card, fn);
    const eff = Math.min(cap, remaining);          // ports this card actually contributes
    const waste = Math.max(0, cap - remaining);    // unused capacity
    // Lower rank = better. Lifecycle dominates, then effective coverage,
    // then slot footprint, then waste.
    const rank = lifeRank * 10000 - eff * 100 + slotRank * 10 + Math.min(waste, 9);
    if (!best || rank < best.rank) best = { card, slot, cap, rank };
  }
  return best ? { card: best.card, slot: best.slot, capacity: best.cap } : null;
}

/**
 * Simulate filling every required function on a single host with EP cards.
 * Pure: takes a fresh slot map per call, never mutates the host or shared state.
 * Returns the per-function coverage plus the flattened add-on list.
 */
function simulateFill(host, requirements, epCards) {
  const freeSlots = getHostSlots(host);
  const usedPartNos = new Set();
  const coverage = [];
  const addOns = [];
  const unfilledGaps = [];
  const nativelyCovered = [];

  for (const { fn, count } of requirements) {
    const hostHave = getHostFunctionCount(host, fn);
    const cards = [];
    let total = hostHave;

    while (total < count) {
      const pick = pickCardForFunction(fn, epCards, freeSlots, usedPartNos, count - total);
      if (!pick) break;
      freeSlots[pick.slot] -= 1;
      usedPartNos.add(pick.card.meta.part_no);
      cards.push(pick);
      total += pick.capacity;
      addOns.push({ card: pick.card, fillsFunction: fn, slot: pick.slot, capacity: pick.capacity });
    }

    const covered = total >= count;
    if (covered && cards.length === 0) nativelyCovered.push(fn);
    if (!covered) unfilledGaps.push(fn);
    coverage.push({
      fn, need: count, hostHave,
      fromCards: total - hostHave, total, covered,
      shortfall: Math.max(0, count - total),
      cards,
    });
  }

  return { freeSlots, coverage, addOns, unfilledGaps, nativelyCovered };
}

/**
 * Build a full, quantity-aware solution bundle.
 *
 * @param criteria        structured_criteria from the AI (compute constraints)
 * @param requiredFnsRaw  required_functions ([{function,count}] or strings)
 * @param hosts           computing_* products
 * @param epCards         io / networking / air_sensor / camera products
 * @param recommendedPartNos AI's recommended hosts (optional, biases host pick)
 */
export function buildSolution(criteria, requiredFnsRaw, hosts, epCards, recommendedPartNos = []) {
  const requirements = normalizeRequiredFunctions(requiredFnsRaw);
  const recommendedSet = new Set(recommendedPartNos || []);

  // 1. eligible hosts
  let eligible = hosts.filter(h => hostMeetsConstraints(h, criteria));
  if (criteria?.product_lines?.length) {
    const hostLines = criteria.product_lines.filter(l => l.startsWith('computing'));
    if (hostLines.length) eligible = eligible.filter(h => hostLines.includes(h.meta.product_line));
  }

  // Always keep AI-recommended hosts in the running, even if a numeric-criteria
  // artifact (e.g. an over-tight TDP/TOPS cap inferred from the RFQ) would
  // otherwise drop them. The AI reasoned about both the criteria *and* the
  // recommendation from the same RFQ, so when they conflict we trust the
  // explicit, holistic pick rather than silently swapping in a different board.
  if (recommendedSet.size) {
    const present = new Set(eligible.map(h => h.meta.part_no));
    for (const h of hosts) {
      if (recommendedSet.has(h.meta.part_no) && !present.has(h.meta.part_no)) eligible.push(h);
    }
  }

  if (eligible.length === 0) {
    return {
      host: null, addOns: [], coverage: [], nativelyCovered: [],
      unfilledGaps: requirements.map(r => r.fn), requirements,
      requiredFns: requirements.map(r => r.fn), eligibleHosts: [], alternativeHosts: [],
      osNotes: [],
    };
  }

  // 2 + 3 + 4. Rank hosts by *achievable* coverage. For each eligible host we
  // actually simulate filling the I/O gaps with EP cards, so a host that can't
  // physically host the cards (e.g. no PCIe slot for a PCIe serial card) is not
  // credited for that function. Ranking: most requirements fully covered →
  // AI-recommended → fewest add-on cards (prefer native / simpler bundle) → TOPS.
  const evaluated = eligible.map(h => {
    const fill = simulateFill(h, requirements, epCards);
    return {
      host: h,
      ...fill,
      coveredCount: fill.coverage.filter(c => c.covered).length,
      isRec: recommendedSet.has(h.meta.part_no) ? 1 : 0,
      tops: h.computing_spec?.ai_tops ?? 0,
    };
  });
  evaluated.sort((a, b) => {
    if (b.coveredCount !== a.coveredCount) return b.coveredCount - a.coveredCount;
    if (b.isRec !== a.isRec) return b.isRec - a.isRec;
    if (a.addOns.length !== b.addOns.length) return a.addOns.length - b.addOns.length;
    return b.tops - a.tops;
  });

  const best = evaluated[0];
  const host = best.host;
  const ranked = evaluated.map(e => e.host);

  return {
    host,
    coverage: best.coverage,
    nativelyCovered: best.nativelyCovered,
    addOns: best.addOns,
    unfilledGaps: best.unfilledGaps,
    requirements,
    requiredFns: requirements.map(r => r.fn),
    remainingSlots: best.freeSlots,
    eligibleHosts: ranked,
    alternativeHosts: ranked.slice(1, 4),
    osNotes: buildOsNotes(host, criteria),
  };
}

/** Human label for a function key. */
export function functionLabel(fn) {
  return FUNCTIONS[fn]?.label || fn;
}
export function functionIcon(fn) {
  return FUNCTIONS[fn]?.icon || '•';
}
