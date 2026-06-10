/**
 * Client-side filtering of spec_matrix products based on AI-parsed criteria.
 * This runs entirely in-browser — zero latency after spec_matrix.json is loaded.
 */
export function filterProducts(products, criteria) {
  if (!criteria) return products;

  return products.filter(p => {
    const cs = p.computing_spec || {};
    const co = p.common || {};

    // product_line filter
    if (criteria.product_lines && criteria.product_lines.length > 0) {
      if (!criteria.product_lines.includes(p.meta.product_line)) return false;
    }

    // AI TOPS minimum
    if (criteria.min_ai_tops != null) {
      if (cs.ai_tops == null || cs.ai_tops < criteria.min_ai_tops) return false;
    }

    // TDP maximum
    if (criteria.max_tdp_watt != null) {
      if (cs.tdp_watt != null && cs.tdp_watt > criteria.max_tdp_watt) return false;
    }

    // Operating temperature range (customer requirement ⊆ product range)
    if (criteria.min_op_temp_c != null) {
      if (co.op_temp_min_c == null || co.op_temp_min_c > criteria.min_op_temp_c) return false;
    }
    if (criteria.max_op_temp_c != null) {
      if (co.op_temp_max_c == null || co.op_temp_max_c < criteria.max_op_temp_c) return false;
    }

    // OS support (at least one of the required OSes must be supported)
    if (criteria.os_required && criteria.os_required.length > 0) {
      const osSupport = (cs.os_support || []).map(s => s.toLowerCase());
      const hasOS = criteria.os_required.some(req =>
        osSupport.some(sup => sup.includes(req.toLowerCase()))
      );
      if (!hasOS) return false;
    }

    return true;
  });
}

/**
 * Local search — part-number lookup and keyword match.
 * Runs entirely in-browser with no Claude API call.
 *
 * isLocalQuery(q): returns true when the query looks like a part-no or
 *   short model keyword, NOT a natural-language sentence.
 *
 * search(q, products): returns matched products sorted by relevance score.
 */
export const localSearch = {
  /**
   * Heuristic: treat as a local query when ALL of the following are true:
   *   - 40 chars or fewer
   *   - No sentence-like words (no 需要/need/support/with/under/above/for/temperature)
   *   - Looks like alphanumeric segments (part-no pattern OR brand+number)
   */
  isLocalQuery(query) {
    const q = query.trim();
    if (!q || q.length > 60) return false;
    // Reject if it contains sentence-structure keywords
    const sentenceWords = /\b(需要|support|need|with|under|above|for|temperature|windows|linux|industrial|wide|temp|°C|TOPS|watt|GbE|PCIe|USB\s+\d)\b/i;
    if (sentenceWords.test(q)) return false;
    // Accept if it looks like a product code or short brand+model string
    const partNoPattern = /^[A-Z]{2,6}[-_ ]?[\dA-Z]+([-_ ][\dA-Z]+)*$/i;
    const brandModel = /^[A-Za-z]{2,20}\s+[A-Z0-9][-A-Z0-9 ]+$/i;
    return partNoPattern.test(q) || brandModel.test(q) || q.split(/\s+/).length <= 3;
  },

  /**
   * Score and return matching products.
   * Scoring:
   *   100 — exact part_no match (case-insensitive)
   *    80 — part_no starts with query
   *    60 — part_no contains query
   *    40 — processor_model contains query
   *    20 — text_summary contains query
   */
  search(query, products) {
    const q = query.trim().toLowerCase();
    const scored = [];

    for (const p of products) {
      const partNo   = (p.meta.part_no   || '').toLowerCase();
      const procName = (p.computing_spec?.processor_model || '').toLowerCase();
      const summary  = (p.search?.text_summary || '').toLowerCase();

      let score = 0;
      if (partNo === q)              score = 100;
      else if (partNo.startsWith(q)) score =  80;
      else if (partNo.includes(q))   score =  60;
      else if (procName.includes(q)) score =  40;
      else if (summary.includes(q))  score =  20;

      if (score > 0) scored.push({ product: p, score });
    }

    return scored
      .sort((a, b) => b.score - a.score)
      .map(s => s.product);
  },
};

/**
 * Sort filtered products:
 *   1. AI-recommended products first (by recommendation rank)
 *   2. Then by AI TOPS descending as tiebreaker
 */
export function sortProducts(products, recommendedPartNos) {
  const recMap = new Map(
    (recommendedPartNos || []).map((id, idx) => [id, idx])
  );

  return [...products].sort((a, b) => {
    const aRank = recMap.has(a.meta.part_no) ? recMap.get(a.meta.part_no) : 999;
    const bRank = recMap.has(b.meta.part_no) ? recMap.get(b.meta.part_no) : 999;
    if (aRank !== bRank) return aRank - bRank;

    // Tiebreaker: TOPS descending
    const aTops = a.computing_spec?.ai_tops ?? 0;
    const bTops = b.computing_spec?.ai_tops ?? 0;
    return bTops - aTops;
  });
}
