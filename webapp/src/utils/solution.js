/**
 * Solution builder: RFQ criteria → a complete product bundle.
 *
 * Flow:
 *   1. Filter hosts by the hard compute constraints (TOPS / TDP / temp / OS).
 *   2. Rank hosts; prefer ones that natively cover the most required functions.
 *   3. For the chosen host, diff required_functions against what it provides.
 *   4. Fill each gap with the best EP card that (a) provides that function and
 *      (b) has a host_interface fitting a still-available host slot.
 *   5. Report a bundle: host + add-on cards + any gaps that remain unfilled.
 */
import {
  getHostProvides, getHostSlots, getCardFunction, getCardInterface, findSlotFor,
  normalizeFunction, FUNCTIONS,
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

/** Canonicalize the function list coming out of the RFQ parser. */
export function normalizeRequiredFunctions(list) {
  const out = [];
  for (const item of list || []) {
    const f = normalizeFunction(item);
    if (f && !out.includes(f)) out.push(f);
  }
  return out;
}

/**
 * Score a host for ranking: more covered required-functions is better,
 * then higher TOPS as a tiebreaker. recommendedPartNos (from the AI) win first.
 */
function scoreHost(host, requiredFns, recommendedSet) {
  const provides = getHostProvides(host);
  const covered = requiredFns.filter(f => provides.has(f)).length;
  const isRec = recommendedSet.has(host.meta.part_no) ? 1 : 0;
  const tops = host.computing_spec?.ai_tops ?? 0;
  return { covered, isRec, tops };
}

/**
 * Pick the best EP card for a single required function, given the host's
 * remaining free slots. Returns { card, slot } or null.
 */
function pickCardForFunction(fn, epCards, freeSlots, usedPartNos) {
  let best = null;
  for (const card of epCards) {
    if (usedPartNos.has(card.meta.part_no)) continue;
    if (getCardFunction(card) !== fn) continue;
    const iface = getCardInterface(card);
    const slot = findSlotFor(iface, freeSlots);
    if (!slot) continue;
    // Prefer Active lifecycle, then lower slot footprint (USB < M.2 < PCIe).
    const lifeRank = card.common?.lifecycle_status === 'Active' ? 0 : 1;
    const slotRank = { USB: 0, 'M.2': 1, PCIe: 2 }[slot] ?? 3;
    const rank = lifeRank * 10 + slotRank;
    if (!best || rank < best.rank) best = { card, slot, rank };
  }
  return best ? { card: best.card, slot: best.slot } : null;
}

/**
 * Build a full solution bundle.
 *
 * @param criteria        structured_criteria from the AI (compute constraints)
 * @param requiredFnsRaw  required_functions from the AI (free text or canonical)
 * @param hosts           computing_* products
 * @param epCards         io / networking / air_sensor products
 * @param recommendedPartNos AI's recommended hosts (optional, biases host pick)
 */
export function buildSolution(criteria, requiredFnsRaw, hosts, epCards, recommendedPartNos = []) {
  const requiredFns = normalizeRequiredFunctions(requiredFnsRaw);
  const recommendedSet = new Set(recommendedPartNos || []);

  // 1. eligible hosts
  let eligible = hosts.filter(h => hostMeetsConstraints(h, criteria));
  if (criteria?.product_lines?.length) {
    const hostLines = criteria.product_lines.filter(l => l.startsWith('computing'));
    if (hostLines.length) eligible = eligible.filter(h => hostLines.includes(h.meta.product_line));
  }
  if (eligible.length === 0) {
    return { host: null, addOns: [], unfilledGaps: requiredFns, requiredFns, eligibleHosts: [] };
  }

  // 2. rank hosts
  const ranked = [...eligible].sort((a, b) => {
    const sa = scoreHost(a, requiredFns, recommendedSet);
    const sb = scoreHost(b, requiredFns, recommendedSet);
    if (sb.isRec !== sa.isRec) return sb.isRec - sa.isRec;
    if (sb.covered !== sa.covered) return sb.covered - sa.covered;
    return sb.tops - sa.tops;
  });
  const host = ranked[0];

  // 3. gap analysis
  const provides = getHostProvides(host);
  const nativelyCovered = requiredFns.filter(f => provides.has(f));
  const gaps = requiredFns.filter(f => !provides.has(f));

  // 4. fill gaps with EP cards
  const freeSlots = getHostSlots(host);
  const usedPartNos = new Set();
  const addOns = [];
  const unfilledGaps = [];

  for (const fn of gaps) {
    const pick = pickCardForFunction(fn, epCards, freeSlots, usedPartNos);
    if (pick) {
      freeSlots[pick.slot] -= 1;
      usedPartNos.add(pick.card.meta.part_no);
      addOns.push({ card: pick.card, fillsFunction: fn, slot: pick.slot });
    } else {
      unfilledGaps.push(fn);
    }
  }

  return {
    host,
    nativelyCovered,
    addOns,
    unfilledGaps,
    requiredFns,
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
