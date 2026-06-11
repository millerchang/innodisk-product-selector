/**
 * Claude API integration for product selection.
 * Called at query time only — not during parsing.
 * Model: claude-haiku-3-5 (fastest + cheapest; ~$0.003/query)
 */

const CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-haiku-4-5';
// Competitor comparison uses Sonnet: needs web_search tool + large structured JSON output
const COMPARISON_MODEL = 'claude-sonnet-4-6';

/**
 * Build a compressed one-line summary per product for the prompt.
 * Keeps token count low while giving Claude enough context to rank.
 */
function buildProductSummary(products) {
  return products
    .map(p => {
      const line = p.meta.product_line;
      if (line === 'computing_aiot' || line === 'computing_ipa') {
        const cs = p.computing_spec || {};
        const co = p.common || {};
        const parts = [
          p.meta.part_no,
          cs.processor_model || cs.platform_brand || '?',
          cs.ai_tops != null ? `${cs.ai_tops}T` : null,
          cs.tdp_watt != null ? `${cs.tdp_watt}W` : null,
          co.op_temp_min_c != null ? `${co.op_temp_min_c}~${co.op_temp_max_c}°C` : null,
          cs.os_support?.join('/') || null,
          cs.connectivity?.slice(0, 6).join(',') || null,
          line, p.meta.bu_owner,
        ];
        return parts.filter(Boolean).join(' | ');
      }
      // Camera module one-liner
      if (line === 'camera') {
        const cam = p.camera_spec || {};
        return [
          p.meta.part_no,
          'Camera',
          cam.interface_bus ? `via ${cam.interface_bus}` : null,
          cam.resolution_mp != null ? `${cam.resolution_mp}MP` : null,
          cam.fps != null ? `${cam.fps}fps` : null,
          line,
        ].filter(Boolean).join(' | ');
      }
      // EP / add-on card one-liner (io / networking / air_sensor)
      const spec = p.networking_spec || p.io_spec || p.air_sensor_spec || {};
      const parts = [
        p.meta.part_no,
        spec.subcategory || line,
        spec.host_interface ? `via ${spec.host_interface}` : null,
        spec.speed_gbps != null ? `${spec.speed_gbps}Gbps` : null,
        spec.port_count != null ? `${spec.port_count}port` : null,
        line,
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

  // Detect RFQ file input (wrapped by rfqParser.wrapRfqText)
  const isRfqFile = requirement.startsWith('[RFQ_FILE:');
  const rfqFilename = isRfqFile
    ? requirement.match(/\[RFQ_FILE:\s*(.+?)\]/)?.[1] || 'document'
    : null;
  const rfqBody = isRfqFile
    ? requirement.replace(/^\[RFQ_FILE:[^\]]*\]\n/, '')
    : null;

  const systemPrompt = `You are a product selector assistant for Innodisk, an industrial edge AI computing company.
Match customer requirements to products from the catalog. Always respond with valid JSON only — no markdown fences, no explanation outside the JSON.
You understand English, Traditional Chinese (繁體中文), Simplified Chinese (简体中文), and Japanese (日本語) equally.`;

  const requirementBlock = isRfqFile
    ? `Customer RFQ document (filename: "${rfqFilename}"):
<rfq_document>
${rfqBody}
</rfq_document>

Extract all technical requirements from the above RFQ document (may be in English, Chinese, or Japanese).
Focus on: product category, compute performance, AI TOPS, operating temperature, OS, I/O requirements, dimensions, power budget.`
    : `Customer RFQ / requirement: "${requirement}"`;

  const userPrompt = `${requirementBlock}

Catalog. Compute hosts are lines computing_aiot / computing_ipa.
Add-on EP cards are lines io / networking / air_sensor (they expand a host's I/O).
Format: PART_NO | spec... | line
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
  "required_functions": [{ "function": "", "count": 1 }],
  "recommended_part_nos": [],
  "recommendation_summary": "",
  "key_tradeoffs": ""
}

Rules:
- required_functions: list every I/O / connectivity function the customer asks for,
  as objects {"function": <key>, "count": <number>}, using ONLY these canonical
  keys: ["ethernet","can","serial","wifi","gnss","usb","storage","poe","display","air_sensor","camera"].
  count = how many ports/units the customer needs (default 1 if unspecified).
  Example: "需要 4 個網口、10 個 USB 接相機、CAN bus 和 GPS" →
    [{"function":"ethernet","count":4},{"function":"usb","count":10},{"function":"can","count":1},{"function":"gnss","count":1}].
  Empty array if no I/O functions stated.
- structured_criteria: hard COMPUTE constraints ONLY. Leave every numeric field
  null unless the customer states an EXPLICIT number for THAT field. Do NOT infer
  or estimate values from CPU class, GPU model, "edge"/"industrial" wording, or
  any other soft cue.
    • min_ai_tops: null unless an explicit TOPS figure is given (e.g. "≥40 TOPS").
    • max_tdp_watt: null unless an explicit power/wattage limit is given
      (e.g. "under 25W"). A CPU/GPU model is NOT a wattage spec → keep null.
    • min_op_temp_c / max_op_temp_c: null unless an explicit temperature range is
      given (e.g. "-20~60°C"). "industrial"/"rugged" alone → keep null.
    • os_required: only OS names the customer actually names.
  When unsure, prefer null — an over-tight constraint wrongly drops good hosts.
- product_lines: array from ["computing_aiot","computing_ipa"] or null. Pick the
  compute host line(s); the system fills I/O gaps with EP cards automatically.
- recommended_part_nos: 3–5 best COMPUTE HOSTS, sorted by relevance (best first). Your single best pick must be first.
- recommendation_summary: 2–3 sentences explaining WHY recommended_part_nos[0] (your first-listed host) is the best match. Must name that exact part number.
- key_tradeoffs: one sentence on tradeoffs vs. the alternatives, or null`;

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
      temperature: 0, // deterministic extraction — same RFQ → same criteria
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
/**
 * Build a concise spec dict for an Innodisk computing product.
 * Used to feed actual verified specs into the competitor comparison prompt.
 */
/**
 * Build a verified spec summary string for one Innodisk product.
 * @param {object}  product       - spec_matrix product object
 * @param {boolean} hasEpCanBus   - true when catalog contains a CAN Bus EP card for this platform
 * @param {boolean} hasDinRail    - true when catalog has DIN-rail compatible products
 */
function buildInnodiskSpecSummary(product, hasEpCanBus = false) {
  const line = product.meta.product_line;
  const co   = product.common || {};

  // ── Camera module ─────────────────────────────────────────────────────────
  if (line === 'camera') {
    const cam = product.camera_spec || {};
    const resStr = cam.resolution_mp
      ? `${cam.resolution_mp}MP${cam.resolution_px ? ` (${cam.resolution_px})` : ''}`
      : null;
    // Dynamic range: prefer numeric dB value; fall back to HDR flag; if HDR=false omit entirely
    const drStr = cam.dynamic_range_db
      ? `${cam.dynamic_range_db} dB`
      : (cam.hdr ? 'HDR' : null);
    const dimCam = cam.dimensions
      ? [cam.dimensions.width_mm, cam.dimensions.depth_mm, cam.dimensions.height_mm]
          .filter(v => v != null).join('×') + ' mm'
      : null;

    const fields = [
      `part_no: ${product.meta.part_no}`,
      cam.interface_bus          ? `interface: ${cam.interface_bus}` : null,
      resStr                     ? `resolution: ${resStr}` : null,
      cam.sensor_model           ? `sensor: ${cam.sensor_model}` : null,
      cam.sensor_size            ? `sensor_size: ${cam.sensor_size}` : null,
      cam.pixel_size_um != null  ? `pixel_size: ${cam.pixel_size_um} µm` : null,
      cam.chroma_type            ? `chroma: ${cam.chroma_type}` : null,
      cam.fps != null            ? `fps: ${cam.fps}` : null,
      cam.shutter_type           ? `shutter: ${cam.shutter_type}` : null,
      drStr                      ? `dynamic_range: ${drStr}` : null,
      // NOTE: do NOT add a separate hdr: field — dynamic_range already captures it.
      // Sending both causes Claude to produce two conflicting rows.
      cam.low_light != null      ? `low_light: ${cam.low_light ? 'Yes' : 'No'}` : null,
      cam.lens_type              ? `lens_type: ${cam.lens_type}` : null,
      cam.lens_fov_deg != null   ? `fov: ${cam.lens_fov_deg}°` : null,
      cam.video_format           ? `video_format: ${cam.video_format}` : null,
      cam.power_w != null        ? `power: ${cam.power_w} W` : null,
      cam.os_support?.length     ? `os_support: ${cam.os_support.join(', ')}` : null,
      dimCam                     ? `dimensions: ${dimCam}` : null,
      co.op_temp_min_c != null   ? `op_temp: ${co.op_temp_min_c}~${co.op_temp_max_c}°C` : null,
      co.certifications?.length  ? `certs: ${co.certifications.join(', ')}` : null,
    ].filter(Boolean);

    return fields.join(' | ');
  }

  // ── Computing platform (AIoT / IPA) ──────────────────────────────────────
  const cs    = product.computing_spec || {};
  const ports = cs.io_ports || {};

  // USB: total count + highest standard
  const usbTotal = ports.usb?.reduce((s, u) => s + u.count, 0) ?? null;
  const usbStds  = ports.usb?.length
    ? (() => {
        const ORDER = ['USB4','USB3.2 Gen2','USB3.2 Gen1','USB2.0'];
        const best  = ports.usb
          .map(u => u.standard)
          .sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b))[0];
        return best || null;
      })()
    : null;
  const usbStr = usbTotal != null
    ? `${usbTotal} ports${usbStds ? ` (up to ${usbStds})` : ''}`
    : null;

  const gbeList = ports.gbe?.map(g => `${g.count}×${g.speed_gbps}GbE`).join(', ') || null;
  const serList = ports.serial?.map(s => `${s.count}×${s.standard}`).join(', ') || null;

  const ownCanBus = ports.can_bus_count != null && ports.can_bus_count > 0;
  const canBusStr = ownCanBus
    ? `${ports.can_bus_count} port${ports.can_bus_count > 1 ? 's' : ''}`
    : (hasEpCanBus ? 'Optional (EP add-on)' : null);

  const dimParts = cs.dimensions
    ? [cs.dimensions.width_mm, cs.dimensions.depth_mm, cs.dimensions.height_mm]
        .filter(v => v != null && v !== 0)
    : [];
  const dims = dimParts.length >= 2 ? dimParts.join('×') + ' mm' : null;

  const coreStr = cs.cpu_cores != null
    ? (cs.cpu_p_cores != null
        ? `${cs.cpu_cores} (${cs.cpu_p_cores}P+${cs.cpu_e_cores}E)`
        : `${cs.cpu_cores}`)
    : null;

  const mem = cs.memory_spec;
  const memStr = mem
    ? [mem.type, mem.speed_mhz ? `${mem.speed_mhz}MHz` : null,
       mem.max_capacity_gb ? `max ${mem.max_capacity_gb}GB` : null]
        .filter(Boolean).join(' ')
    : null;

  const m2Str = cs.m2_slots?.length
    ? cs.m2_slots
        .map(s => `${s.count}×M.2 ${s.size} ${s.key}-key(${(s.interface || []).join('/')})`)
        .join(', ')
    : null;

  const fields = [
    `part_no: ${product.meta.part_no}`,
    cs.processor_model        ? `processor: ${cs.processor_model}` : null,
    coreStr                   ? `cpu_cores: ${coreStr}` : null,
    cs.ai_tops != null        ? `ai_tops: ${cs.ai_tops}` : 'ai_tops: N/A',
    cs.tdp_watt != null       ? `tdp_w: ${cs.tdp_watt}` : null,
    cs.ram_gb != null         ? `ram_gb: ${cs.ram_gb}` : null,
    memStr                    ? `memory_spec: ${memStr}` : null,
    co.op_temp_min_c != null  ? `op_temp: ${co.op_temp_min_c}~${co.op_temp_max_c}°C` : null,
    cs.os_support?.length     ? `os: ${cs.os_support.join('/')}` : null,
    usbStr                    ? `usb: ${usbStr}` : null,
    gbeList                   ? `gbe: ${gbeList}` : null,
    serList                   ? `serial: ${serList}` : null,
    canBusStr                 ? `can_bus: ${canBusStr}` : null,
    m2Str                     ? `m2_slots: ${m2Str}` : null,
    dims                      ? `dimensions: ${dims}` : null,
    cs.power_input            ? `power_input: ${cs.power_input}` : null,
    co.certifications?.length ? `certs: ${co.certifications.join(', ')}` : null,
    cs.form_factor            ? `form_factor: ${cs.form_factor}` : null,
    cs.display_outputs?.length ? `display: ${cs.display_outputs.join(', ')}` : null,
    cs.sdk?.length             ? `sdk: ${cs.sdk.join('/')}` : null,
  ].filter(Boolean);

  return fields.join(' | ');
}


/**
 * Competitor comparison: unified side-by-side table.
 *
 * Search mode (pdfData=null):     competitor model names / URL → Claude uses web_search for live specs.
 * File mode   (pdfData=object):   competitor spec PDF/TXT uploaded → sent as a document content block;
 *                                 no web search needed (specs are in the file).
 *
 * @param {string}        competitorInput  - Model names / URL for search mode; ignored in file mode
 * @param {object[]}      innodiskProducts - Selected Innodisk product objects from spec_matrix (may be empty)
 * @param {object[]}      allProducts      - Full catalog (for fallback auto-suggest when nothing selected)
 * @param {string}        apiKey
 * @param {object|null}   pdfData          - { base64, filename, mediaType } for file mode; null = search mode
 */
export async function queryCompetitorComparison(
  competitorInput,
  innodiskProducts,
  allProducts,
  apiKey,
  pdfData = null,
) {
  // ── Catalog-level context flags ─────────────────────────────────────────
  const hasEpCanBus = (allProducts || []).some(p =>
    p.networking_spec?.subcategory === 'CAN-Bus'
  );
  const hasDinRail = (allProducts || []).some(p => {
    const ff      = (p.computing_spec?.form_factor || '').toLowerCase();
    const summary = (p.search?.text_summary || '').toLowerCase();
    return ff.includes('din') || summary.includes('din-rail') || summary.includes('din rail');
  });

  // ── Detect dominant product type from selected products ─────────────────
  const hasSelected = innodiskProducts && innodiskProducts.length > 0;
  const selectedLines = hasSelected
    ? [...new Set(innodiskProducts.map(p => p.meta.product_line))]
    : [];
  const isCameraSession  = selectedLines.length > 0 && selectedLines.every(l => l === 'camera');
  const isComputeSession = selectedLines.length > 0 && selectedLines.every(l =>
    l === 'computing_aiot' || l === 'computing_ipa'
  );

  // ── Build Innodisk spec block ───────────────────────────────────────────
  const innodiskBlock = hasSelected
    ? innodiskProducts.map(p => buildInnodiskSpecSummary(p, hasEpCanBus)).join('\n')
    : buildProductSummary(allProducts);

  // ── Column keys ─────────────────────────────────────────────────────────
  const innodiskKeys = hasSelected
    ? innodiskProducts.map(p => p.meta.part_no)
    : [];

  // ── DEBUG ────────────────────────────────────────────────────────────────
  console.group('[CompetitorAPI] queryCompetitorComparison debug');
  console.log('selectedLines:', selectedLines);
  console.log('isCameraSession:', isCameraSession, '| isComputeSession:', isComputeSession);
  console.log('innodiskBlock:\n' + innodiskBlock);
  console.groupEnd();

  // ── Prompt ──────────────────────────────────────────────────────────────
  const isFileMode = pdfData != null;

  const systemPrompt = isFileMode
    ? `You are a competitive intelligence assistant for Innodisk, an industrial edge computing company.
A competitor product datasheet has been provided as a document. Extract all technical specifications from it.
For any spec fields the document does not explicitly state, provide best-estimate values and prefix with "~".
CRITICAL: Respond with raw JSON only. Do NOT wrap in markdown code fences (\`\`\`json or \`\`\`). Do NOT include any text before or after the JSON object. The very first character of your response must be '{' and the last must be '}'.`
    : `You are a competitive intelligence assistant for Innodisk, an industrial edge computing company.
Your job: produce a rigorous side-by-side comparison table using live web data.
IMPORTANT: Use the web_search tool to look up official specs for each competitor product from the vendor's official website or authoritative spec pages. Always search first — do not guess from training data alone.
After searching and gathering specs, respond with raw JSON only. Do NOT wrap in markdown code fences (\`\`\`json or \`\`\`). Do NOT include any text before or after the JSON object. The very first character of your response must be '{' and the last must be '}'.`;

  const competitorSource = isFileMode
    ? `Competitor product datasheet: "${pdfData.filename}". Extract competitor specs from the attached document.`
    : `Search for the official specs of the following competitor product(s) and compare:\n${competitorInput}`;

  const innodiskSection = hasSelected
    ? `Innodisk products selected by the user (VERIFIED specs from our database — copy field values VERBATIM):
${innodiskBlock}`
    : `No specific Innodisk products selected. Choose the 1–2 best Innodisk matches from this catalog:
${innodiskBlock}`;

  // Context notes injected into the prompt
  const epCanBusNote = hasEpCanBus
    ? `NOTE: Innodisk offers a dedicated CAN Bus expansion card (EP module). If a product shows "can_bus: Optional (EP add-on)", use that exact text in the table — it means CAN Bus is available as a platform add-on, not built-in.`
    : '';

  const dinRailNote = hasDinRail
    ? `NOTE: Innodisk catalog includes DIN-rail compatible products. If any competitor uses DIN-rail mount form factor, add a talking point explicitly stating that Innodisk also offers DIN-rail compatible models.`
    : '';

  const userPrompt = `${competitorSource}

${innodiskSection}
${epCanBusNote ? '\n' + epCanBusNote : ''}
${dinRailNote ? '\n' + dinRailNote : ''}

Return ONLY this JSON (no markdown):
{
  "columns": [],
  "competitor_notes": { "<name>": { "confidence": "high|medium|low", "note": "optional caveat" } },
  "rows": [
    {
      "spec": "",
      "category": "",
      "values": { "<col_key>": "short string value ≤60 chars" },
      "best": "<col_key of winner or null if tie/N/A>",
      "higher_is_better": true
    }
  ],
  "innodisk_advantages": [],
  "talking_points": []
}

Rules:
- columns: list ALL product keys in order — Innodisk part_nos FIRST, then competitor names exactly as given.
  ${hasSelected ? `Innodisk columns MUST be: ${innodiskKeys.join(', ')}` : 'Pick 1–2 best Innodisk matches and add their part_nos first.'}
- rows: cover ALL these specs relevant to the product type (skip only if every product is genuinely N/A):
${isCameraSession ? `  CAMERA MODULE specs:
  Interface, Resolution, Chroma Type, Sensor Model, Sensor Size, Pixel Size,
  Frame Rate, Shutter Type, Dynamic Range, Low Light, Lens Type, FOV,
  Video Format, Power Consumption, OS Support, Dimensions,
  Operating Temperature, Certifications` : isComputeSession ? `  COMPUTING PLATFORM specs:
  Processor, Core Count, AI TOPS, TDP (W), RAM, Memory Type & Speed,
  Operating Temperature, OS Support, USB Ports, GbE (Ethernet), Serial / COM,
  CAN Bus, M.2 Storage, Display Outputs, Dimensions, Power Input, Fanless Design,
  Certifications, Form Factor, AI SDK` : `  AUTO-DETECT appropriate spec rows based on the products being compared.
  For camera modules use: Interface, Resolution, Sensor Model, Sensor Size, Pixel Size, Frame Rate, Dynamic Range, HDR, Low Light, Operating Temperature, Certifications.
  For computing platforms use: Processor, Core Count, AI TOPS, TDP (W), RAM, Memory Type & Speed, Operating Temperature, OS Support, USB Ports, GbE, Serial/COM, CAN Bus, M.2 Storage, Dimensions, Power Input, Fanless Design, Certifications, Form Factor, AI SDK.`}
- values: short strings (≤60 chars).
  For INNODISK products: copy the verified spec field value VERBATIM. NEVER output "—"
  when the data block provides a value.
  For COMPETITOR products: use your training knowledge to provide best estimates.
    • Prefix uncertain estimates with "~" (e.g. "~13MP", "~30fps", "~15W").
    • Only output "—" when the product GENUINELY LACKS that feature.
    • NEVER output "—" just because you are unsure — always provide your best estimate with "~".
- best: the col_key of the objectively best product for that spec. null = tie or N/A.
- higher_is_better: true for resolution/fps/dynamic range/cores/RAM; false for TDP/pixel size (smaller = better).
- category: one of ${isCameraSession ? 'Imaging | Sensor | Optical | Features | Mechanical | Certifications' : 'Compute | Memory | Thermal | I/O | Mechanical | Certifications | Features'}
- innodisk_advantages: 3–5 concrete advantages vs the competitors (short bullets)
- talking_points: 3–5 sales talking points (short bullets)
  ${hasDinRail && !isCameraSession ? '  Include DIN-rail availability if relevant vs competitor form factors.' : ''}`;

  // ── Build request body ───────────────────────────────────────────────────
  // File mode: send PDF/TXT as a native document content block so Claude reads it directly.
  // Search mode: plain text message + web_search tool.
  const userMessage = isFileMode
    ? {
        role: 'user',
        content: [
          {
            type: 'document',
            source: {
              type: 'base64',
              media_type: pdfData.mediaType || 'application/pdf',
              data: pdfData.base64,
            },
            title: pdfData.filename,
          },
          { type: 'text', text: userPrompt },
        ],
      }
    : { role: 'user', content: userPrompt };

  const requestBody = {
    model: COMPARISON_MODEL,
    max_tokens: 8192,   // increased: 3+ products × 20 rows can exceed 4096
    temperature: 0,
    system: systemPrompt,
    messages: [userMessage],
  };

  // Enable server-side web_search only for search mode (not needed when spec file is provided)
  if (!isFileMode) {
    requestBody.tools = [{ type: 'web_search_20250305', name: 'web_search' }];
  }

  // ── Send request + handle pause_turn continuation ────────────────────────
  // web_search runs server-side (Anthropic infrastructure) — no client-side
  // tool execution loop needed.  Only need to handle pause_turn (server-side
  // loop hit its 10-iteration cap) by appending the partial assistant turn
  // and re-sending.
  const HEADERS = {
    'Content-Type': 'application/json',
    'x-api-key': apiKey,
    'anthropic-version': '2023-06-01',
    'anthropic-dangerous-direct-browser-access': 'true',
  };

  let data;
  let continueCount = 0;
  const MAX_CONTINUE = 3;

  do {
    const response = await fetch(CLAUDE_API_URL, {
      method: 'POST',
      headers: HEADERS,
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error?.message || `API error ${response.status}`);
    }

    data = await response.json();
    console.log('[CompetitorAPI] stop_reason:', data.stop_reason, '| content blocks:', data.content?.length);

    if (data.stop_reason === 'pause_turn' && continueCount < MAX_CONTINUE) {
      // Server-side tool loop hit its cap — append partial assistant turn and retry
      continueCount++;
      console.log(`[CompetitorAPI] pause_turn — continuing (attempt ${continueCount}/${MAX_CONTINUE})`);
      requestBody.messages = [
        ...requestBody.messages,
        { role: 'assistant', content: data.content },
      ];
    }
  } while (data.stop_reason === 'pause_turn' && continueCount <= MAX_CONTINUE);

  // Extract the LAST text block — web_search responses have multiple text blocks:
  // the first is Claude's preamble ("I'll search for..."), the last is the JSON result.
  const textBlocks = data.content.filter(b => b.type === 'text');
  const textBlock = textBlocks[textBlocks.length - 1];
  const text = textBlock?.text || '';
  console.log('[CompetitorAPI] text length:', text.length);
  console.log('[CompetitorAPI] raw response (first 800):\n', text.slice(0, 800));

  // Strip markdown code fences if Claude wrapped the JSON (e.g. ```json ... ```)
  const stripped = text
    .replace(/^```(?:json)?\s*/i, '')   // remove opening fence
    .replace(/\s*```\s*$/,      '')     // remove closing fence
    .trim();

  try {
    return JSON.parse(stripped);
  } catch (e1) {
    console.error('[CompetitorAPI] JSON.parse failed after fence-strip:', e1.message);
    console.error('[CompetitorAPI] stop_reason:', data.stop_reason, '| stripped length:', stripped.length);
    console.error('[CompetitorAPI] stripped text (first 300):', stripped.slice(0, 300));

    if (data.stop_reason === 'max_tokens') {
      throw new Error('Comparison response was too long (max tokens reached). Try selecting fewer products.');
    }

    throw new Error('Failed to parse competitor comparison response. Check the browser console for details.');
  }
}
