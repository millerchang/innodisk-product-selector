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
    const os = (cs.os_support || []).map(s => s.toLowerCase());
    const ok = c.os_required.some(r => os.some(s => s.includes(r.toLowerCase())));
    if (!ok) return false;
  }
  return true;
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
 * Score a host for ranking: more requirements met natively at the requested
 * quantity is best, then higher native coverage ratio, then TOPS. AI-recommended
 * hosts win the first tiebreak.
 */
function scoreHost(host, requirements, recommendedSet) {
  let fullyMet = 0;
  let ratioSum = 0;
  for (const { fn, count } of requirements) {
    const have = getHostFunctionCount(host, fn);
    if (have >= count) fullyMet += 1;
    ratioSum += Math.min(have, count) / count;
  }
  return {
    isRec: recommendedSet.has(host.meta.part_no) ? 1 : 0,
    fullyMet,
    ratio: ratioSum,
    tops: host.computing_spec?.ai_tops ?? 0,
  };
}

/** Pick the best EP card for a function given remaining slots; or null. */
function pickCardForFunction(fn, epCards, freeSlots, usedPartNos) {
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
    // For quantity fills, prefer higher-capacity cards (fewer cards/slots used).
    const cap = getCardCapacity(card, fn);
    const rank = lifeRank * 100 + slotRank * 10 - Math.min(cap, 9);
    if (!best || rank < best.rank) best = { card, slot, cap, rank };
  }
  return best ? { card: best.card, slot: best.slot, capacity: best.cap } : null;
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
  if (eligible.length === 0) {
    return {
      host: null, addOns: [], coverage: [], nativelyCovered: [],
      unfilledGaps: requirements.map(r => r.fn), requirements,
      requiredFns: requirements.map(r => r.fn), eligibleHosts: [], alternativeHosts: [],
    };
  }

  // 2. rank hosts
  const ranked = [...eligible].sort((a, b) => {
    const sa = scoreHost(a, requirements, recommendedSet);
    const sb = scoreHost(b, requirements, recommendedSet);
    if (sb.fullyMet !== sa.fullyMet) return sb.fullyMet - sa.fullyMet;
    if (sb.isRec !== sa.isRec) return sb.isRec - sa.isRec;
    if (sb.ratio !== sa.ratio) return sb.ratio - sa.ratio;
    return sb.tops - sa.tops;
  });
  const host = ranked[0];

  // 3 + 4. per-function quantity coverage
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
      const pick = pickCardForFunction(fn, epCards, freeSlots, usedPartNos);
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

  return {
    host,
    coverage,
    nativelyCovered,
    addOns,
    unfilledGaps,
    requirements,
    requiredFns: requirements.map(r => r.fn),
    remainingSlots: freeSlots,
    eligibleHosts: ranked,
    alternativeHosts: ranked.slice(1, 4),
  };
}

/** Human label for a function key. */
export function functionLabel(fn) {
  return FUNCTIONS[fn]?.label || fn;
}
export function functionIcon(fn) {
  return FUNCTIONS[fn]?.icon || '•';
}
