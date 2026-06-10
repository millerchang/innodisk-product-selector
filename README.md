# Innodisk Golden Bros — Intelligent Product Selection Guide

> AI-powered product selector and competitive intelligence tool for Innodisk sales & FAE teams.

---

## Overview

This tool helps sales and FAE engineers quickly match customer requirements to Innodisk products and perform competitive analysis. It consists of two parts:

| Part | Description |
|------|-------------|
| **Parser** (local) | Extracts structured specs from product datasheets (PDF) into `spec_matrix.json` |
| **Web App** (static) | React SPA that loads `spec_matrix.json` and provides search, filter, comparison, and competitor analysis |

**Architecture principle: zero cloud maintenance.**
- All heavy processing (PDF parsing) runs locally on the engineer's machine
- The webapp is a fully static site — only two files need to be hosted: `spec_matrix.json` + the compiled React app
- Claude API is called only at query time (~$0.003–0.006 per query)

---

## Product Catalog

Current `spec_matrix.json` covers **276 products** across 6 product lines:

| Product Line | Count | Description |
|---|---|---|
| Networking | 135 | LAN, CAN Bus, Serial, PoE, GNSS, WiFi modules |
| Computing AIoT | 53 | Intel / NXP embedded computing platforms |
| I/O | 46 | Storage expanders, display adapters, OOB modules |
| Camera | 21 | USB, MIPI-CSI2, GMSL2 industrial camera modules |
| Air Sensor | 16 | PM2.5, CO₂, VOC, temperature/humidity sensors |
| Computing IPA | 5 | Qualcomm / AMD-Xilinx AI accelerator platforms |

---

## Repository Structure

```
innodisk-product-selector/
│
├── parser/                     # Local PDF parsing pipeline
│   ├── pipeline.py             # Main entry point (run this to re-parse datasheets)
│   ├── rule_extractor.py       # Rule-based field extraction per product line
│   ├── schema_builder.py       # Normalizes extracted fields into spec_matrix schema
│   └── vision_extractor.py     # Claude Vision fallback for complex PDF layouts
│
├── output/                     # Parser output (not all files committed)
│   ├── spec_matrix.json        # ✅ Committed — main product database
│   ├── parse_log.json          # ✅ Committed — per-file parse status & confidence scores
│   └── parse_hash_cache.json   # ❌ Not committed — local cache to skip unchanged PDFs
│
├── webapp/                     # React frontend (Vite)
│   ├── public/
│   │   ├── spec_matrix.json    # Copy of output/spec_matrix.json (served statically)
│   │   ├── notes.json          # PM-maintained product notes (editable directly)
│   │   └── logo.png            # Innodisk logo
│   ├── src/
│   │   ├── App.jsx             # Main layout, state management, filter logic
│   │   ├── components/
│   │   │   ├── SearchBar.jsx           # NL query input + RFQ file upload
│   │   │   ├── ProductList.jsx         # Product card grid
│   │   │   ├── ProductCard.jsx         # Individual product card
│   │   │   ├── FilterBar.jsx           # Category checkbox filter
│   │   │   ├── ProductDetailModal.jsx  # Full spec detail popup
│   │   │   ├── ComparisonPanel.jsx     # Side-by-side product comparison (up to 6)
│   │   │   ├── CompetitorMode.jsx      # Competitor analysis table
│   │   │   ├── SolutionPanel.jsx       # AI-recommended solution bundle
│   │   │   └── SettingsModal.jsx       # Claude API key configuration
│   │   └── utils/
│   │       ├── claudeApi.js    # Claude API calls (product selector + competitor comparison)
│   │       ├── filter.js       # Client-side product filtering & sorting
│   │       ├── rfqParser.js    # RFQ document pre-processing (Word/PDF upload)
│   │       └── solution.js     # Solution bundle builder (host + EP cards)
│   └── package.json
│
├── part_number_rules/          # Part number decode rules per product line (reference docs)
└── README.md                   # This file
```

---

## Prerequisites

### Local Machine (Parser)

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Must be in PATH |
| pdfplumber | latest | `pip install pdfplumber` |
| anthropic | latest | `pip install anthropic` (for Vision fallback only) |

### Development (Web App)

| Requirement | Version |
|---|---|
| Node.js | 18+ |
| npm | 9+ |

### Runtime (End Users)

- A modern web browser (Chrome / Edge / Firefox)
- A **Claude API key** (set in the web app Settings — stored in `localStorage` only, never sent to any server other than Anthropic)

---

## Setup & First Run

### 1. Clone the repository

```bash
git clone <repo-url>
cd innodisk-product-selector
```

### 2. Parse datasheets (first time or when new datasheets are added)

Place datasheets in a folder, then run:

```bash
cd parser

# Windows — set Python path if not in PATH
$env:PATH = "C:\Users\<username>\AppData\Local\Programs\Python\Python311;" + $env:PATH

# Parse all datasheets in a folder
python pipeline.py --datasheets "<path-to-datasheets-folder>" --output "../output"

# Force re-parse all (ignore hash cache)
python pipeline.py --datasheets "<path-to-datasheets-folder>" --output "../output" --force
```

After parsing, copy the output to the webapp:

```bash
# Windows PowerShell
Copy-Item "output\spec_matrix.json" "webapp\public\spec_matrix.json"
```

### 3. Run the web app (development)

```bash
cd webapp
npm install
npm run dev
# → http://localhost:5173
```

### 4. Build for production / deployment

```bash
cd webapp
npm run build
# Output in webapp/dist/ — deploy this folder to any static host
```

---

## Web App Features

### Product Search
- **Natural language query** — describe requirements in English or Chinese; Claude AI parses and matches
- **Direct part number / model name lookup** — works without an API key (local search)
- **RFQ document upload** — upload a Word (.docx) or PDF RFQ; the tool extracts requirements automatically

### Category Filter
- Checkbox filter bar below the search input
- **All** master checkbox (default: all checked = show all 276 products)
- Uncheck a category to hide it; re-check to restore

### Product Comparison
- Check up to **6 products** and click **⇄ Compare** to open a side-by-side spec panel (slides in from the right)

### Competitor Comparison
- Click **⚔ Compare with Competitors** to expand the competitor analysis section
- Enter competitor model names → Claude fetches public specs and generates a side-by-side table with:
  - Spec-by-spec comparison
  - Win/loss scoring per product
  - Innodisk advantages summary
  - Sales talking points
- **Paste Specs mode** — for small vendors with no public spec page, paste raw spec text manually

### PM Notes
- Each product can have a PM-maintained note shown as a yellow callout in the detail modal
- Edit `webapp/public/notes.json` directly — key = part number, value = note text:
  ```json
  {
    "APEX-E100": "New flagship AIoT platform — target industrial AI inference use cases.",
    "EV2U-RMR1-UMCB": "Compact USB camera for Jetson / RPi platforms."
  }
  ```

---

## Parser — How It Works

```
PDF Datasheets
     │
     ▼
pipeline.py          ← entry point; handles file discovery, hash caching, orchestration
     │
     ├─ rule_extractor.py   ← fast rule-based extraction (regex + pdfplumber table parsing)
     │                         confidence ≥ 0.70 → use directly
     │
     └─ vision_extractor.py ← Claude Vision API fallback for complex / non-standard layouts
                               confidence < 0.70 AND API key present → call Vision
     │
     ▼
schema_builder.py    ← normalizes raw extracted fields into the final spec_matrix schema
     │
     ▼
output/spec_matrix.json
```

**Key design decisions:**
- Hash-based caching: unchanged PDFs are skipped on re-runs (fast incremental updates)
- Parser confidence score: 0.0–1.0 per product, logged in `parse_log.json`
- Rule-based handles ~80% of datasheets; Vision fallback handles complex table layouts
- Camera modules use a dedicated extraction pipeline (`_parse_camera_spec`)

---

## Configuration

### Claude API Key

Set your Claude API key in the web app via **⚙ Settings** (top-right corner). The key is stored in `localStorage` and is never transmitted anywhere except directly to the Anthropic API.

For the parser's Vision fallback:

```bash
# Windows — set before running pipeline.py
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Or create a `.env` file in the project root (already in `.gitignore`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Updating the Product Catalog

When new datasheets are available:

1. Add PDF files to the datasheets folder
2. Run `python pipeline.py --datasheets <folder> --output ../output`
3. Copy `output/spec_matrix.json` → `webapp/public/spec_matrix.json`
4. Commit both files
5. Deploy (or re-run `npm run build` for a static deployment update)

Only changed files are re-parsed (hash cache). A full re-parse of 276 products takes ~3–5 minutes.

---

## Deployment

The webapp is a fully static site. Any static hosting works:

| Option | Command |
|---|---|
| GitHub Pages | Push `webapp/dist/` to `gh-pages` branch |
| Nginx / IIS | Serve `webapp/dist/` as document root |
| Local (no internet) | `npm run preview` in `webapp/` |

> **Note:** `spec_matrix.json` (~2–3 MB) is fetched at startup. Ensure it is accessible at the same origin as the app, or update the fetch URL in `webapp/src/hooks/useSpecMatrix.js`.

---

## Maintainers

| Role | Contact |
|---|---|
| Tool owner / FAE | Miller Chang — Innodisk FAE Manager |
| Product data (notes.json) | PM team |
| MIS / Deployment | MIS team |
