/**
 * Claude API integration for product selection.
 * Called at query time only — not during parsing.
 * Model: claude-haiku-3-5 (fastest + cheapest; ~$0.003/query)
 */

const CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-haiku-4-5';

/**
 * Build a compressed one-line summary per product for the prompt.
 * Keeps token count low while giving Claude enough context to rank.
 */
function buildProductSummary(products) {
  return products
    .map(p => {
      const cs = p.computing_spec || {};
      const co = p.common || {};
      const parts = [
        p.meta.part_no,
        cs.processor_model || cs.platform_brand || '?',
        cs.ai_tops != null ? `${cs.ai_tops}T` : null,
        cs.tdp_watt != null ? `${cs.tdp_watt}W` : null,
        co.op_temp_min_c != null ? `${co.op_temp_min_c}~${co.op_temp_max_c}°C` : null,
        cs.os_support?.join('/') || null,
        cs.connectivity?.slice(0, 5).join(',') || null,
        p.meta.product_line,
        p.meta.bu_owner,
      ];
      return parts.filter(Boolean).join(' | ');
    })
    .join('\n');
}

/**
 * Query Claude API with a natural-language requirement.
 * Returns { structured_criteria, recommended_part_nos, recommendation_summary, key_tradeoffs }
 */
export async function queryProductSelector(requirement, products, apiKey) {
  const productSummary = buildProductSummary(products);

  const systemPrompt = `You are a product selector assistant for Innodisk, an industrial edge AI computing company.
Match customer requirements to products from the catalog. Always respond with valid JSON only — no markdown fences, no explanation outside the JSON.`;

  const userPrompt = `Customer requirement: "${requirement}"

Product catalog (PART_NO | Processor | TOPS | TDP | Temp | OS | Connectivity | line | BU):
${productSummary}

Return exactly this JSON structure (no extra fields, no markdown):
{
  "structured_criteria": {
    "product_lines": null,
    "min_ai_tops": null,
    "max_tdp_watt": null,
    "min_op_temp_c": null,
    "max_op_temp_c": null,
    "os_required": [],
    "keywords": []
  },
  "recommended_part_nos": [],
  "recommendation_summary": "",
  "key_tradeoffs": ""
}

Rules:
- recommended_part_nos: 3–5 best matches, sorted by relevance (best first)
- structured_criteria: extract hard constraints only (null = not specified)
- product_lines: array from ["computing_aiot","computing_ipa"] or null
- recommendation_summary: 2–3 sentences explaining the top recommendation
- key_tradeoffs: one sentence on tradeoffs or null`;

  const response = await fetch(CLAUDE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 1024,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  });

  if (!response.ok) {
    let errMsg = `API error ${response.status}`;
    try {
      const err = await response.json();
      errMsg = err.error?.message || errMsg;
      if (response.status === 401) errMsg = 'Invalid API key — check Settings.';
    } catch {}
    throw new Error(errMsg);
  }

  const data = await response.json();
  const text = data.content[0]?.text || '';

  try {
    return JSON.parse(text);
  } catch {
    // Fallback: extract first JSON object from text
    const match = text.match(/\{[\s\S]*\}/);
    if (match) {
      try { return JSON.parse(match[0]); } catch {}
    }
    throw new Error('Failed to parse API response. Please try again.');
  }
}

/**
 * Competitor comparison mode: fetch competitor specs via web search and compare.
 * Returns { comparison_table, innodisk_advantages, talking_points }
 */
export async function queryCompetitorComparison(competitorInput, products, apiKey, isManualPaste = false) {
  const productSummary = buildProductSummary(products);

  const systemPrompt = `You are a competitive intelligence assistant for Innodisk sales team.
Compare competitor products against Innodisk's portfolio. Always respond with valid JSON only.`;

  const source = isManualPaste
    ? `Competitor specs (manually provided):\n${competitorInput}`
    : `Competitor product: "${competitorInput}"`;

  const userPrompt = `${source}

Innodisk product catalog:
${productSummary}

Return this JSON:
{
  "competitor_name": "",
  "competitor_specs_summary": "",
  "closest_innodisk_matches": [],
  "comparison_table": [
    { "spec": "", "competitor": "", "innodisk": "", "innodisk_wins": true }
  ],
  "innodisk_advantages": [],
  "talking_points": [],
  "data_source": "${isManualPaste ? 'manually_provided' : 'inferred_from_model_name'}"
}`;

  const response = await fetch(CLAUDE_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 2048,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error?.message || `API error ${response.status}`);
  }

  const data = await response.json();
  const text = data.content[0]?.text || '';

  try {
    return JSON.parse(text);
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (match) {
      try { return JSON.parse(match[0]); } catch {}
    }
    throw new Error('Failed to parse competitor comparison response.');
  }
}
