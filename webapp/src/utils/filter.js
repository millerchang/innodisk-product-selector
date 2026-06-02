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
