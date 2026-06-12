# Changelog

All notable changes to the Innodisk Product Selector are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [2.4.0] — 2026-06-12

### Changed — Competitor Comparison overhaul

#### Replaced Jina Reader with Claude `web_search` tool
- **Problem:** Jina Reader (`r.jina.ai`) could not render JavaScript-heavy SPAs. Fetching Advantech EPC-C301's product page returned only a cookie-consent banner, causing Claude to fall back to stale training data and produce wrong specs (wrong CPU, wrong RAM).
- **Fix:** Competitor search mode now uses Claude's server-side `web_search_20250305` tool. Anthropic's infrastructure executes the search; Claude receives Google-indexed spec content and extracts accurate data automatically. No client-side scraping.
- **Result:** EPC-C301 now correctly identifies Intel Core i7-8665UE, DDR4-2400, 4×GbE, 2×isolated CAN Bus (built-in), DIN-rail form factor — all confirmed accurate.

#### Replaced "Paste Specs" with "Upload Spec Sheet"
- **Old:** Users pasted raw text manually.
- **New:** Users upload a competitor PDF / TXT / CSV datasheet. Claude reads the document via the native `document` content block — no external PDF parser library required.
- Supports: `.pdf`, `.txt`, `.csv`
- Use case: sales receive a competitor PDF datasheet → upload → instant structured comparison table.

#### UI simplified from 3 modes → 2 modes
| Old | New |
|---|---|
| Model Name(s) | 🔍 Search (Model / URL) |
| Paste Specs | 📄 Upload Spec Sheet |
| 🔗 URL | *(merged into Search)* |

Search mode now accepts model names, part numbers, **and** product page URLs interchangeably.

### Fixed — JSON parsing robustness
- **Preamble prose:** Claude (especially with `web_search`) sometimes prefixes the JSON output with a sentence like "I now have comprehensive data. Let me compile...". Parser now finds the first `{` and slices from there, discarding any leading prose.
- **Multiple text blocks:** `web_search` responses contain multiple content blocks (search queries, results, final text). Parser now selects the **last** text block (the JSON result) instead of the first (which may be a preamble sentence).
- **`pause_turn` continuation:** If Claude's server-side tool loop hits the 10-iteration cap, the client now automatically appends the partial response and re-sends (up to 3 continuations).

### Fixed — API rate limit
- Reverted `COMPARISON_MODEL` from `claude-sonnet-4-6` back to `claude-haiku-4-5`.
- Reason: Sonnet has a 30k input TPM limit at lower API tiers vs Haiku's ~100k. The parsing robustness fixes (preamble-strip + last-text-block selection) resolve the instability that originally motivated the Sonnet upgrade.

### Changed — Hidden rows
- **AI SDK** row is now hidden from the competitor comparison table. Definition is inconsistent across product lines and models (Haiku misidentified Advantech management software as AI SDK). Will be re-enabled once AI SDK support policy is confirmed per product line.
- Implemented via `HIDDEN_SPECS` set in `CompetitorMode.jsx` — easy to extend or revert.

---

## [2.3.0] — 2026-06-11

### Fixed — ABOX-V140 lifecycle status
- Removed `ABOX-V140` from `PRELIMINARY_PARTS` in `parser/product_catalog.py`.
- ABOX-V140 datasheet dated 2026-06-08 is a full release (not preliminary). Product now correctly shows **Active** lifecycle badge instead of **Preview**.

---

## [2.2.0] — 2026-06-10

### Added — URL mode for competitor comparison (via Jina Reader)
- Added `🔗 URL` input mode: users could paste a competitor product page URL.
- Specs were fetched via Jina Reader (`r.jina.ai/{url}`) to bypass CORS restrictions.
- **Note:** Superseded in v2.4.0 due to Jina Reader failures on JS-heavy pages.

---

## [2.1.0] — 2026-05-xx

### Added — Major feature overhaul
- Camera module parser and camera-specific comparison rows
- Competitor comparison mode (initial implementation)
- FilterBar category checkboxes
- Product comparison expanded from 4 → **6 products** simultaneously
- Source datasheet clickable PDF link in product detail modal
- Serial / USB display improvements in detail modal

---

## [2.0.0] — 2026-05-xx

### Added — Direct part number / model name lookup
- Instant local search by exact part number or model name — **no Claude API key required**.
- Results appear immediately without calling the Claude API.

### Added — RFQ document upload
- Upload Word (.docx) or PDF RFQ documents.
- Tool extracts customer requirements automatically and passes to Claude for product matching.

---

## [1.0.0] — 2026-04-xx

### Initial release
- Natural language product search via Claude API
- `spec_matrix.json` covering 276 products across 6 product lines
- Side-by-side product comparison panel
- PM Notes support (`notes.json`)
- GitHub Pages deployment via GitHub Actions
