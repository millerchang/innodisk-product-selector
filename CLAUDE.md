# Innodisk Product Selection Intelligence Tool

## Project Owner
- Role: Solution Architect / Pre-Sales (PSM), Innodisk
- Background: FAE Manager (7 years)

## Project Goal
Build an AI-powered product selection tool for the sales team.
Sales inputs customer requirements → tool parses & matches → recommends suitable products.

**Core constraint: zero cloud maintenance.**
- Heavy processing (PDF parsing + embedding) runs **locally only**
- Cloud stores only 2 static files: `spec_matrix.json` + `embeddings.bin`
- Query UI is a static web app (React / GitHub Pages)
- Claude API is called only at query time for NL understanding (~$0.006/query)

**Extended goal: Competitor Comparison Mode**
- Sales can input a competitor product name/model → tool fetches public specs via Claude API web_search
- Claude compares competitor specs against matched Innodisk products from spec_matrix.json
- Output: structured comparison table + sales talking points highlighting Innodisk advantages
- Fallback: if web_search fails (small vendor / no public page), UI prompts sales to paste competitor spec text manually → Claude still performs structured comparison
- Price comparison is explicitly out of scope (competitor pricing rarely public)

---

## Product Lines (Official Taxonomy from innodisk.com/cht/products)

| # | Line | BU | Source | Parser Priority |
|---|------|----|--------|-----------------|
| 1 | 嵌入式儲存 (Flash Storage) | — | Website + PDF | P6 |
| 2 | 記憶體模組 (DRAM Modules) | — | Website + PDF | P6 |
| 3 | 相機模組 (Camera) | — | Website + PDF | P2 |
| 4 | I/O 模組 (I/O Modules) | — | Website + PDF | P3 |
| 5 | 空氣感測 (Air Sensor) | — | Website + PDF | — |
| 6 | 通訊 (Networking) | — | Website + PDF | P4 |
| 7 | 運算平台 IPA (Qualcomm / AMD-Xilinx) | IPA BU | Website + PDF | P5 |
| 8 | 系統板 AIoT (Intel / NXP) | AIoT BU | **PDF only** (not on website) | **P1** |

### BU Notes
- **IPA BU**: Qualcomm / AMD-Xilinx platforms — visible on official website
- **AIoT BU**: Intel platform (主力) + NXP (少量) — NOT on website, datasheet is the only source
- Flash / DRAM are lower priority; included for bundled system recommendations (e.g. bootable SSD pairing)

---

## spec_matrix.json — Schema Design

Each product is one JSON record. Structure:

```json
{
  "meta": {
    "part_no": "string",
    "product_name": "string",
    "product_line": "flash|dram|camera|io|networking|air_sensor|computing_ipa|computing_aiot",
    "bu_owner": "IPA|AIoT|null",
    "source_file": "filename.pdf",
    "file_hash_md5": "string",
    "schema_version": "3.0",
    "last_updated": "YYYY-MM-DD",
    "embedding_id": "string"
  },

  "common": {
    "temp_grade": "Commercial|Industrial|Wide|Military",
    "op_temp_min_c": -40,
    "op_temp_max_c": 85,
    "mtbf_hours": 0,
    "warranty_years": 0,
    "certifications": ["CE", "FCC", "RoHS"],
    "lifecycle_status": "Active|EOL|NRND",
    "eol_date": "YYYY-MM-DD|null",
    "moq": 1,
    "lead_time_weeks": 0
  },

  "flash_spec": {
    "interface_bus": "PCIe|SATA|PATA|USB",
    "pcie_gen": "Gen3|Gen4|Gen5|null",
    "form_factor": "M.2|U.2|CFexpress|2.5inch|SATADOM|mSATA|CFast|nanoSSD|CompactFlash|SD|USB-EDC",
    "nand_type": "SLC|iSLC|MLC|TLC|3D-TLC",
    "capacity_gb": 0,
    "seq_read_mbps": 0,
    "seq_write_mbps": 0,
    "rand_read_iops": 0,
    "rand_write_iops": 0,
    "tbw": 0,
    "dwpd": 0,
    "power_loss_protection": true,
    "aes_encryption": false,
    "smart_support": true
  },

  "dram_spec": {
    "interface_bus": "DDR5|DDR4|DDR3|DDR2|DDR|SDRAM|CXL",
    "form_factor": "DIMM|SO-DIMM|LPDIMM|UDIMM",
    "capacity_gb": 0,
    "speed_mhz": 0,
    "voltage_v": 0,
    "ecc": false,
    "registered": false,
    "cas_latency": 0,
    "rank": 0,
    "low_profile": false,
    "ai_optimized": false
  },

  "camera_spec": {
    "interface_bus": "USB2.0|MIPI-CSI2|MIPI-TypeC|GMSL2",
    "resolution_mp": 0,
    "resolution_px": "e.g. 1920x1080",
    "fps": 0,
    "sensor_type": "CMOS|BSI",
    "sensor_size": "e.g. 1/2.7inch",
    "hdr": false,
    "low_light": false,
    "lens_fov_deg": 0,
    "ir_filter": false,
    "adapter_board_compatible": []
  },

  "io_spec": {
    "subcategory": "Storage|DiskArray|Display|OOB|InnoEx-VirtualIO|TestingTool",
    "host_interface": "PCIe|USB|M.2",
    "pcie_gen": "Gen3|Gen4|null",
    "pcie_lanes": 0,
    "port_type": [],
    "port_count": 0,
    "supported_os": [],
    "driver_required": true,
    "display_output": false
  },

  "networking_spec": {
    "subcategory": "LAN|CAN-Bus|Serial|PoE",
    "host_interface": "PCIe|USB|M.2",
    "pcie_gen": "Gen3|Gen4|null",
    "port_count": 0,
    "speed_gbps": 0,
    "protocol": ["RS-232", "RS-422", "RS-485"],
    "poe_watt": 0,
    "can_fd_support": false,
    "isolation": false
  },

  "air_sensor_spec": {
    "detected_pollutants": ["PM2.5", "CO2", "VOC", "Temp", "Humidity"],
    "interface_bus": "USB|UART|I2C",
    "accuracy_pm25_ug": 0,
    "measurement_range": "string",
    "response_time_s": 0,
    "sdk_support": [],
    "icap_compatible": true
  },

  "computing_spec": {
    // ── Identity ──────────────────────────────────────────────
    "bu_owner": "IPA|AIoT",
    "platform_brand": "Intel|NXP|Qualcomm|AMD-Xilinx",
    "processor_model": "string",
    "processor_series": "string",

    // ── CPU ───────────────────────────────────────────────────
    "cpu_cores":   0,       // total physical cores (P+E combined for Intel hybrid)
    "cpu_p_cores": null,    // Performance cores — Intel hybrid only; null for NXP/Qualcomm
    "cpu_e_cores": null,    // Efficiency cores (incl. LP-E for Meteor Lake) — Intel hybrid only

    // ── Performance ───────────────────────────────────────────
    "tdp_watt": 0,
    "ai_tops":  0,

    // ── Memory ────────────────────────────────────────────────
    "ram_gb": 0,            // KEPT for backward-compat filter; = memory_spec.max_capacity_gb
    "memory_spec": {
      "type":            "DDR5|DDR4|LPDDR5|LPDDR4|null",
      "speed_mhz":       0,      // e.g. 5600 for DDR5-5600; 3200 for DDR4-3200
      "slots":           0,      // physical SO-DIMM / DIMM slot count on board
      "max_capacity_gb": 0,      // maximum supported RAM
      "form_factor":     "SO-DIMM|DIMM|on-board",
      "ecc_support":     false
    },

    // ── System ────────────────────────────────────────────────
    "form_factor":      "string",
    "os_support":       ["Linux", "Windows", "Android", "RTOS", "Yocto"],
    "sdk":              ["OpenVINO", "SNPE", "QNN", "Vitis-AI"],
    "openvino_support": false,

    // ── Physical ──────────────────────────────────────────────
    "dimensions": {
      "width_mm":  null,   // shorter horizontal dimension
      "depth_mm":  null,   // longer horizontal dimension
      "height_mm": null    // vertical (thickness)
    },
    "power_input": "string",

    // ── PCIe Expansion Slots (full-size card slots; NOT M.2) ──
    // Empty array [] if no full-size PCIe slots (e.g. compact Box PC)
    "pcie_slots": [
      {
        "width": "x1|x4|x8|x16",
        "gen":   3,                // PCIe generation: 3 | 4 | 5
        "count": 1,
        "note":  null              // e.g. "electrical x4", "shared bandwidth with x1"
      }
    ],

    // ── M.2 Slots ─────────────────────────────────────────────
    "m2_slots": [
      {
        "size":      "2230|2242|2260|2280|22110|3052",
        "key":       "A|B|E|M|B+M|A+E",
        "interface": ["PCIe x4 Gen4", "SATA"],  // protocols supported on this slot
        "count":     1
      }
    ],

    // ── Detailed I/O Ports ────────────────────────────────────
    "io_ports": {
      "usb": [
        {
          "standard":  "USB4|USB3.2 Gen2|USB3.2 Gen1|USB2.0",
          "count":     0,
          "connector": "Type-A|Type-C|Internal"
        }
      ],
      "gbe": [
        {
          "speed_gbps":  1,         // 1 | 2.5 | 10
          "count":       0,
          "poe_support": false
        }
      ],
      "serial": [
        {
          "standard": "RS-232|RS-422|RS-485|RS-232/422/485",
          "count":    0,
          "note":     null          // e.g. "software selectable"
        }
      ],
      "gpio_pins":      null,       // total GPIO pin count; null if absent
      "can_bus_count":  null,       // CAN Bus port count; null if absent
      "sim_slot_count": null,       // SIM card slot count; null if absent
      "audio": {
        "line_out": null,
        "mic_in":   null,
        "spk_out":  null
      }
    },

    // ── Backward-compat flat lists (keep; used by filter + search) ──
    "connectivity":       ["GbE", "USB3", "HDMI", "PCIe", "CAN", "GPIO"],
    "display_outputs":    ["HDMI", "DP"],
    "storage_interfaces": ["M.2", "SATA"],
    "storage_gb":         null
  },

  "search": {
    "text_summary": "Full natural language description for embedding — include all key specs, use cases, differentiators",
    "searchable_tags": ["industrial", "wide-temp", "bootable", "AI-inference"],
    "target_applications": ["manufacturing", "transportation", "medical", "surveillance", "retail"]
  },

  "poc_sw_suggestions": [
    {
      "sw_name": "iVIT|iCAP",
      "poc_available": true,
      "bundle_required": false,
      "use_case": "string — specific POC scenario for this product"
    }
  ]
}
```

### Schema Rules
- Only populate the `_spec` block matching the product line; leave all others absent (do not include empty blocks)
- `interface_bus` is always product-line-specific — never in `common` (avoids Flash PCIe vs Camera MIPI false match)
- `poc_sw_suggestions` is empty `[]` for Flash, DRAM, I/O, Networking
- All nullable fields use `null`, not `""` or `0`
- `computing_spec` covers both IPA BU and AIoT BU — distinguished by `bu_owner` + `platform_brand`
- **v3.0 additions**: `memory_spec`, `dimensions`, `pcie_slots`, `m2_slots`, `io_ports` are new sub-objects. `ram_gb` kept for filter backward-compat. Old string fields `dimensions_mm` and `expansion_slots` are **removed**.
- `pcie_slots` = full-size PCIe card slots only (ATX/Mini-ITX style); M.2 slots go in `m2_slots`
- `io_ports.usb` / `io_ports.gbe` / `io_ports.serial` are arrays — one entry per distinct spec variant (e.g. separate entries for USB3.2 Gen2 Type-A vs USB-C)
- `connectivity` flat list is auto-generated from `io_ports` + `pcie_slots` + `m2_slots` by the parser — do not edit manually

---

## Local Toolchain

### Ollama (open-source, MIT License)
- Repo: github.com/ollama/ollama
- Runs LLM and embedding models fully locally — no API key, no cost, no data leaving the machine
- Used in this project for two tasks:

| Task | Model | Size | Purpose |
|------|-------|------|---------|
| Embedding | `nomic-embed-text` | 274 MB | Vectorize all product text_summary → embeddings.bin |
| text_summary generation | `qwen2.5:7b` (recommended) or `llama3.2:3b` | 4–8 GB | Generate NL summary per product from structured spec JSON |

- Install: `curl -fsSL https://ollama.com/install.sh | sh`
- Pull models: `ollama pull nomic-embed-text && ollama pull qwen2.5:7b`
- Hardware: nomic-embed-text runs on any laptop; qwen2.5:7b needs ≥8GB RAM

### Why not use Claude API for text_summary generation?
- The pipeline may process hundreds of PDFs at once during initial setup
- Using Claude API for batch generation would cost ~$0.50–2.00 per full run
- Local Ollama = $0 per run, can re-run freely as schema evolves

---

```
/output
  spec_matrix.json     # array of all product records
  embeddings.bin       # vector file (nomic-embed-text via Ollama)
  sw_compatibility_map.json   # manually maintained: sw → compatible hw parts
  parse_log.json       # per-file parse status, confidence score, warnings
```

## Update Pipeline (runs locally, triggered manually)

```
/datasheets/**/*.pdf
  → hash_check (skip unchanged files)
  → pdf_parser (rule-based + Claude Vision fallback for complex layouts)
  → field_extractor (per product line schema)
  → spec_matrix.json (diff + merge)
  → ollama embed (nomic-embed-text)
  → embeddings.bin
  → upload overwrite to Google Drive / GitHub
```

## Parser Strategy by Product Line

| Line | Strategy | Fallback |
|------|----------|----------|
| AIoT (Intel/NXP) | Claude Vision API (PDF → image → extract) | Manual field override |
| Camera | Rule-based table extraction (pdfplumber) | Claude Vision |
| I/O / Networking | Rule-based | Claude Vision |
| IPA (Qualcomm/Xilinx) | Rule-based + website scrape | Claude Vision |
| Flash / DRAM | Rule-based (most structured) | Rarely needed |

## Datasheet Folder Structure (expected)

```
/datasheets
  /aiot_bu          # AIoT BU: Intel / NXP — PDF only, P1 priority
  /camera           # Camera modules
  /io               # I/O modules
  /networking       # LAN, CAN-Bus, Serial, PoE
  /ipa_bu           # IPA BU: Qualcomm / AMD-Xilinx
  /flash            # Flash storage (lower priority)
  /dram             # DRAM modules (lower priority)
```

## Query Flow (runtime, static web app)

### Mode A — Standard Product Selection
1. Sales types customer requirement (natural language, Chinese or English)
2. Claude API: parse NL → structured filter (`product_line`, key spec requirements)
3. In-browser: load `embeddings.bin` → cosine similarity → top-N candidates
4. Apply hard filters from step 2 (e.g. `temp_grade = Industrial`, `interface_bus = PCIe`)
5. Return ranked product cards with match score
6. Intel-style side-by-side spec comparison for selected products
7. If result includes Camera or Computing → show `poc_sw_suggestions` sidebar (optional, non-blocking)

### Mode B — Competitor Comparison
1. Sales selects "競品比較模式" and inputs competitor product name or model number
2. Claude API + web_search tool: fetch competitor public specs from vendor website / datasheets
3. Match competitor specs → find closest Innodisk products from spec_matrix.json
4. Claude generates: comparison table (spec-by-spec) + Innodisk advantage narrative + sales talking points
5. **Fallback path**: if web_search returns no useful result → UI shows text input box → sales pastes competitor spec manually → Claude performs same structured comparison from pasted text
6. Output clearly labels data source: "from web search" vs "manually provided"

### Claude API Capabilities Used (query time only)
| Capability | Mode A | Mode B |
|------------|--------|--------|
| NL → structured filter | ✓ | ✓ |
| Recommendation reasoning | ✓ | ✓ |
| Gap analysis (customer need vs product spec) | ✓ | ✓ |
| Multi-turn follow-up (context retention) | ✓ | ✓ |
| web_search tool (competitor spec lookup) | — | ✓ |
| Comparison table + talking points generation | — | ✓ |
| Report export (Phase 3) | ✓ | ✓ |

---

## Parser Normalization Rules

> 本節記錄從 52 份 AIoT BU datasheet 實際觀察到的書寫不一致，以及 Parser 應如何將其重組為標準欄位值。
> **Parser 必須以此為依據，不得依靠 Claude 推測。**

---

### 1. CPU Model 重組規則（`processor_model`）

Innodisk datasheet 有四種 CPU 書寫格式，Parser 依序嘗試匹配：

| 格式 | 範例原文 | 重組結果 | 產品範例 |
|------|---------|---------|---------|
| **A — 完整 Intel 名稱**（含 ® ™） | `Intel® Core™ i7-13700E` | 原文保留 | ABOX-4020, ASBC-3040 |
| **B — APEX slash 多 SKU**（含 `Intel CPU` 前綴） | `Intel CPU Core i7-13700E` | `Intel Core i7-13700E` | APEX-X100-Q |
| **C — APEX Core Ultra 完整**（含 `Processor` 關鍵字） | `Intel CPU Core Ultra 7 Processor 265H` | `Intel Core Ultra 7 265H` | AXMB-D150 |
| **C — APEX Core Ultra 雙字母 suffix** | `Intel CPU Core Ultra 7 165HL` | `Intel Core Ultra 7 165HL` | APEX-E100 |
| **D — 裸短形**（無品牌前綴） | `CPU 155U 125U 165H` | `Intel Core Ultra 5 155U`（取第一個） | ABOX-4140/4150 |
| **D — Platform 短形** | `Platform CPU 255U 225U 265H` | `Intel Core Ultra 7 255U`（取第一個） | ASBC-3150 |

**注意事項：**
- 多 SKU 格式（如 `CPU i9-13900E/ i7-13700E/ i5-13500E`）→ **取第一個 SKU**（最高階）
- 格式 D 匹配後，需確認後方 60 字元內**不含** `LAN`、`USB`、`Display` 等關鍵字，否則為 Order Information 表格標題列，應忽略
- NXP 產品：`NXP i.MX 8M Plus Cortex-A53 Quad Core` → 原文保留，截至 Quad/Dual/Octa 之前

#### Core Ultra 型號族群對應（`processor_series`）

| 型號數字範圍 | 代表型號 | `processor_series` |
|------------|---------|-------------------|
| 200 系（≥ 200） | 265H, 255U | `Arrow Lake` |
| 100 系（< 200） | 165HL, 155U, 135HL, 125U | `Meteor Lake` |

#### Intel Classic Core 系列對應

| 型號特徵 | `processor_series` |
|---------|-------------------|
| `14xxxE` / `14xxxTE` | `Raptor Lake Refresh` |
| `13xxxE` / `13xxxTE` | `Raptor Lake` |
| `12xxxE` / `12xxxTE` | `Alder Lake` |
| `X6xxxE` / `J6xxx` | `Elkhart Lake` |
| `xxxxxRE` / `x7213RE` | `Elkhart Lake` |
| `N5xxx` / `N4xxx` | `Alder Lake-N` |
| NXP i.MX 8M Plus | `i.MX 8M Plus` |
| Qualcomm Cloud AI 100 | `Qualcomm Cloud AI` |

---

### 2. `processor_model` 族群推斷（`processor_series`）

當型號來自格式 B/C/D（無完整系列名），按上表透過數字範圍推斷：
- `Ultra N NNN[X]` → 先取三位數，≥200 → Arrow Lake，< 200 → Meteor Lake
- suffix 字母：`H`=高效能，`U`=輕薄，`HL`=Meteor Lake 低壓，`UL`=Meteor Lake 超低壓，`E`=工業，`TE`=工業低 TDP

---

### 3. `ai_tops` 解析規則

TOPS 數值在 datasheet 中有四種書寫方式，Parser 全部收錄：

| 原文書寫 | 說明 | 範例產品 |
|---------|------|---------|
| `22.4 TOPs`（小寫 s） | Intel NPU，正確 | ABOX-4140/4150 |
| `36 TOPS` | Intel AI Boost（CPU+GPU+NPU 合計） | APEX-E100 |
| `870 TOPS (INT8)` | Qualcomm Cloud AI100 Ultra | APEX-X100-Q |
| `97 TOPS via (CPU+GPU+NPU)` | Intel Core Ultra 265H | AXMB-D150 |
| `2.3 TOPS` | NXP i.MX 8M Plus 內建 NPU | ASBC-3M80, ABOX-1M80 |
| `200 TOPS` | Qualcomm Cloud AI100（非 Ultra 版） | APEX-A100 |

**規則：`ai_tops` 取文件中所有 TOPS 值的最大值（MAX）。** 因為 APEX 類產品可能同時列出 CPU NPU TOPS 和 GPU TOPS，取最大值代表該系統實際可用 AI 算力上限。

---

### 4. `form_factor` 正規化

| datasheet 原文 | 儲存值 |
|--------------|--------|
| `3.5" SBC` / `3.5' SBC` | `3.5" SBC` |
| `SMALL BOX PC` / `Box PC` | `Box PC` |
| `INDUSTRIAL MOTHERBOARD` | `Industrial Motherboard` |
| `Mini-ITX` / `Thin Mini-ITX` | `Mini-ITX` / `Thin Mini-ITX`（保留原文） |
| `EMBEDDED SYSTEM` | `Embedded System` |
| `COM Express` | `COM Express` |
| `APEX SERIES` | `null`（APEX 是系列名不是 form factor，改由 product_name 攜帶） |

---

### 5. `temp_grade` 推斷規則（當 datasheet 未明確標示時）

依 `op_temp_min_c` + `op_temp_max_c` 推斷：

| 條件 | `temp_grade` |
|------|-------------|
| min ≤ −40 AND max ≥ 85 | `Wide` |
| min ≤ −40 AND max ≥ 70 | `Wide` |
| min ≤ −20 AND max ≥ 60 | `Industrial` |
| min ≥ 0  AND max ≤ 70 | `Commercial` |
| 其他 | `Industrial`（預設保守值） |

**注意：** 部分產品同一份 datasheet 列出多個 SKU 的溫度範圍（如 `0~60°C` 和 `-40~85°C`）→ **取最寬範圍**（min 最小、max 最大），再套上表推斷。

---

### 6. OS 正規化規則（`os_support`）

儲存精簡標籤，不儲存版本號：

| datasheet 原文（各種寫法） | 儲存值 |
|------------------------|--------|
| `Microsoft Windows® 10/11 IoT Enterprise LTSC` | `Windows` |
| `Windows 11 IoT Enterprise 2024 LTSC` | `Windows` |
| `Linux® Ubuntu 22.04 / 20.04 / 24.04` | `Linux` |
| `Yocto Project 4.2 with Linux Kernel 6.1.55` | `Yocto` |
| `Android` | `Android` |
| 同時出現 Windows + Linux | `["Windows", "Linux"]` |

---

### 7. Certification 正規化規則（`certifications`）

datasheet 常以 `/` 分隔連寫，需拆分為陣列：

| 原文書寫範例 | 儲存值 |
|------------|--------|
| `CE/FCC Class B/RoHS/UKCA` | `["CE", "FCC", "RoHS", "UKCA"]` |
| `CE / FCC / UKCA` | `["CE", "FCC", "UKCA"]` |
| `CE/FCC Class B/RoHS` | `["CE", "FCC", "RoHS"]` |

**注意：** `FCC Class B` 標準化為 `FCC`（去掉 Class B 說明）。`UL` 若出現則保留。

---

### 8. `product_name` 正規化

`product_name` 儲存**品類 + 型號**組合，不儲存原始 category header：

| datasheet Header 原文 | `product_name` 儲存格式 |
|---------------------|----------------------|
| `SBC` + `ASBC-3150` | `SBC ASBC-3150` |
| `SMALL BOX PC` + `ABOX-4020` | `Box PC ABOX-4020` |
| `INDUSTRIAL MOTHERBOARD` + `AXMB-1130` | `Industrial Motherboard AXMB-1130` |
| `EMBEDDED SYSTEM` + `AIPC-4120` | `Embedded System AIPC-4120` |
| `APEX SERIES` + `APEX-X100` | `APEX APEX-X100` |

---

### 9. 已知特殊產品處理備忘

| 產品 | 特殊點 | 處理方式 |
|------|--------|---------|
| **APEX-X100-Q** | 主機 Intel i7-13700E + 外購 Qualcomm Cloud AI100 Ultra 加速卡（870 TOPS） | `platform_brand = Intel`，`bu_owner = AIoT`；`ai_tops = 870` |
| **APEX-A100** | IPA BU，Qualcomm 自研平台 | `platform_brand = Qualcomm`，`bu_owner = IPA` |
| **ASBC-3M80** | NXP i.MX 8M Plus，無 Windows，Yocto OS，有 CAN Bus 與 MIPI CSI | `platform_brand = NXP`；OS = `["Yocto"]` |
| **ABOX-1M80** | NXP i.MX 8M Plus Box PC 版 | 同 ASBC-3M80 |
| **AXMB-D150** | 含 Innodisk 自家記憶體 + SSD 的 reference BOM | `key_features` 保留 BOM 清單 |
| **AXMB-D160** | 附 `.svg` block diagram 和 `.pptx`，非 datasheet | 只解析 `.pdf`；`.svg` / `.pptx` 忽略 |
| **ABOX-4140/4150** | CPU 短形 `155U 125U 165H`（無 `Platform` 前綴）| 格式 D 處理，取第一個 SKU |
| **AIPC-4150** | 標題有 `initial version`，版本不成熟 | `lifecycle_status = NRND` |
| **Preliminary 產品** | 資料夾名稱含 `(Preliminary)` | `lifecycle_status = NRND` |

---

### 10. Parser 分流決策

| 條件 | 動作 |
|------|------|
| rule-based confidence ≥ 70% | 直接使用，不呼叫 Vision API |
| rule-based confidence < 70% + 有 API Key | 呼叫 Claude Vision；Vision 結果優先，rule-based 填補空白欄位 |
| rule-based confidence < 70% + 無 API Key | 保留 rule-based 結果，log 記錄 `vision_skipped` |
| `part_no = UNKNOWN` | 從資料夾名稱推斷（資料夾名 = 型號），log 記錄 warning |
| 檔案位於 `ODM/` 子資料夾 | 跳過（ODM 元件 datasheet，非標準產品） |

---

### 11. `cpu_cores` / `cpu_p_cores` / `cpu_e_cores` 解析規則

#### Intel Classic Core（13th / 14th Gen E-series）

| CPU 型號 | `cpu_cores` | `cpu_p_cores` | `cpu_e_cores` |
|---------|------------|--------------|--------------|
| i9-13900E / i9-14900E | 24 | 8 | 16 |
| i7-13700E / i7-14700E | 16 | 8 | 8 |
| i5-13500E / i5-14500E | 14 | 6 | 8 |
| i3-13100E / i3-14100E | 4  | 4 | 0 |
| i9-13900TE / i7-13700TE | 同上（低TDP版，核心數一樣） |

#### Intel Core Ultra（Meteor Lake — 100 系）

| CPU 型號 | `cpu_cores` | `cpu_p_cores` | `cpu_e_cores` |
|---------|------------|--------------|--------------|
| Core Ultra 7 165H / 165HL | 16 | 6 | 10（含 LP-E）|
| Core Ultra 7 155H / 155HL | 16 | 6 | 10 |
| Core Ultra 7 155U | 12 | 2 | 10 |
| Core Ultra 5 135H / 135HL | 14 | 4 | 10 |
| Core Ultra 5 125H | 14 | 4 | 10 |
| Core Ultra 5 125U | 12 | 2 | 10 |

#### Intel Core Ultra（Arrow Lake — 200 系）

| CPU 型號 | `cpu_cores` | `cpu_p_cores` | `cpu_e_cores` |
|---------|------------|--------------|--------------|
| Core Ultra 9 285H | 24 | 8 | 16 |
| Core Ultra 7 265H | 20 | 8 | 12 |
| Core Ultra 7 255U | 14 | 2 | 12 |
| Core Ultra 5 245H | 18 | 6 | 12 |
| Core Ultra 5 225U | 12 | 2 | 10 |

#### 其他平台

| 平台 | `cpu_cores` | `cpu_p_cores` | `cpu_e_cores` |
|-----|------------|--------------|--------------|
| NXP i.MX 8M Plus | 4 | null | null |
| NXP i.MX 8M Nano | 4 | null | null |
| Qualcomm Cloud AI100 | 依 datasheet 指定 | null | null |

**注意：** datasheet 若直接寫出核心數（如 `6-Core`、`Quad Core`），以原文為準，不依本表推算。

---

### 12. `memory_spec` 解析規則

#### 記憶體類型對應（依 CPU 系列推斷，優先以 datasheet 明確標示為準）

| CPU 系列 | `type` | 典型 `speed_mhz` |
|---------|--------|----------------|
| Core Ultra 200 (Arrow Lake) | `DDR5` | 5600 |
| Core Ultra 100 (Meteor Lake) | `DDR5` | 5200 or 5600 |
| 13th/14th Gen E-series | `DDR4` | 3200 |
| Elkhart Lake (J/X6000E, RE) | `DDR4` | 3200 |
| Alder Lake-N (N-series) | `DDR4` | 3200 |
| NXP i.MX 8M Plus | `LPDDR4` | 3200 |

#### `form_factor` 規則

| 機型類別 | `form_factor` |
|--------|-------------|
| Box PC（ABOX 系列）、SBC（ASBC 系列） | `SO-DIMM` |
| Industrial Motherboard（AXMB 系列） | `DIMM` |
| NXP SBC（ASBC-3M80, ABOX-1M80）| `on-board`（焊死，無插槽） |

#### `slots` 推斷規則

- datasheet 有寫 `2 x DDR5 SO-DIMM` → `slots: 2`
- 只寫 `DDR5 SO-DIMM，最大 64GB` 未說明數量 → `slots: 2`（ABOX/ASBC 系列預設）
- NXP on-board → `slots: 0`（無插槽）
- AXMB 工業主板 → 通常 `slots: 2` 或 `slots: 4`，以 datasheet 為準

---

### 13. `dimensions` 解析規則

Datasheet 常見書寫格式（Parser 依序嘗試匹配）：

| 原文格式 | 範例 | 解析方式 |
|--------|------|---------|
| `W × D × H mm` | `162 × 120 × 56 mm` | 直接對應三欄 |
| `L × W × H mm` | `290 × 200 × 44 mm` | L→depth, W→width, H→height |
| `Dimension: 162(W) × 120(D) × 56(H)` | 含括號標示 | 依括號字母對應 |
| `162 x 120 x 56` | 小寫 x | 同第一格式，順序 W×D×H |
| `Unit: mm` 分開列 | 三行各一數字 | 累積三個數字後組合 |

**儲存規則：**
- 取小兩個數字中**較大者**為 `depth_mm`、**較小者**為 `width_mm`，最後一個為 `height_mm`
- 尺寸含公差（如 `162±0.5`）→ 取標稱值 162
- 尺寸含不含散熱片的兩個高度（如 `H: 56 / 68 (with heatsink)`）→ 取無散熱片值 56

---

### 14. `pcie_slots` 解析規則（全尺寸 PCIe 擴充槽）

適用對象：工業主板（AXMB）、Embedded System（AIPC）等有全尺寸插槽的產品。
Box PC / SBC 若無全尺寸 PCIe 槽 → `pcie_slots: []`

| datasheet 原文 | 解析結果 |
|-------------|--------|
| `1 x PCIe x16 (Gen3)` | `{width:"x16", gen:3, count:1, note:null}` |
| `2 x PCIe x4 Gen3` | `{width:"x4", gen:3, count:2, note:null}` |
| `1 x PCIe x16 (Gen3, electrical x4)` | `{width:"x16", gen:3, count:1, note:"electrical x4"}` |
| `PCIe x16 slot (shared w/ mini-PCIe)` | `{width:"x16", gen:null, count:1, note:"shared with mini-PCIe"}` |
| `1 x Mini-PCIe` | `{width:"x1", gen:null, count:1, note:"Mini-PCIe"}` |

**注意：** `gen: null` 表示 datasheet 未明確標示世代。

---

### 15. `m2_slots` 解析規則

#### Size 正規化

| datasheet 原文 | `size` 儲存值 |
|-------------|-------------|
| `M.2 2280` | `"2280"` |
| `M.2 2242` | `"2242"` |
| `M.2 2230` | `"2230"` |
| `M.2 22110` | `"22110"` |
| `M.2 3052` | `"3052"` |
| `M.2 2230/2242/2260/2280 M-key` | `"2280"`（取最大支援尺寸） |

#### Key Type 正規化

| datasheet 原文（各種寫法） | `key` 儲存值 |
|----------------------|-----------|
| `M key` / `M-key` / `(M)` | `"M"` |
| `B key` / `B-key` / `(B)` | `"B"` |
| `E key` / `E-key` | `"E"` |
| `B+M key` / `B/M key` / `B&M key` | `"B+M"` |
| `A+E key` / `A/E key` | `"A+E"` |

#### Interface 正規化

| datasheet 原文 | `interface` 陣列 |
|-------------|----------------|
| `PCIe x4 Gen4 / SATA` | `["PCIe x4 Gen4", "SATA"]` |
| `PCIe x4 / SATA` (未標Gen) | `["PCIe x4", "SATA"]` |
| `PCIe x4 Gen3` | `["PCIe x4 Gen3"]` |
| `SATA III` | `["SATA"]` |
| `PCIe x1 Gen3` | `["PCIe x1 Gen3"]` |
| `USB 3.0` (某些 M.2 B-key) | `["USB3.0"]` |

#### 整體範例

```
"1 x M.2 2280 M-key (PCIe x4 Gen4 / SATA III)"
→ { "size":"2280", "key":"M", "interface":["PCIe x4 Gen4","SATA"], "count":1 }

"2 x M.2 2242 B+M key (SATA)"
→ { "size":"2242", "key":"B+M", "interface":["SATA"], "count":2 }

"1 x M.2 3052 B-key (PCIe x4 Gen3)"
→ { "size":"3052", "key":"B", "interface":["PCIe x4 Gen3"], "count":1 }
```

---

### 16. `io_ports` 解析規則

#### USB `standard` 正規化

| datasheet 原文 | `standard` 儲存值 |
|-------------|----------------|
| `USB 3.2 Gen 2` / `USB3.2 Gen2` / `USB 10Gbps` | `"USB3.2 Gen2"` |
| `USB 3.2 Gen 1` / `USB3.0` / `USB 5Gbps` | `"USB3.2 Gen1"` |
| `USB 2.0` | `"USB2.0"` |
| `USB4 40Gbps` / `USB4` | `"USB4"` |
| `USB Type-C` (未標速度) | 查 CPU 平台決定；Meteor Lake Type-C 通常為 `"USB3.2 Gen2"` |

#### GbE `speed_gbps` 正規化

| datasheet 原文 | `speed_gbps` |
|-------------|------------|
| `GbE` / `1GbE` / `Gigabit LAN` / `RJ45 x1` | `1` |
| `2.5GbE` / `2.5G LAN` | `2.5` |
| `10GbE` / `10G LAN` | `10` |

#### Serial `standard` 正規化

| datasheet 原文 | `standard` 儲存值 |
|-------------|----------------|
| `RS-232 only` | `"RS-232"` |
| `RS-485 only` | `"RS-485"` |
| `RS-232/RS-422/RS-485` / `software selectable` | `"RS-232/422/485"` |
| `2 x RS-232 + 4 x RS-232/422/485` | 兩筆分開：`[{"standard":"RS-232","count":2}, {"standard":"RS-232/422/485","count":4}]` |

#### GPIO、CAN Bus、SIM

- `8 x GPIO` / `GPIO x 8` / `8-bit DIO` → `gpio_pins: 8`
- `16-bit Digital I/O` → `gpio_pins: 16`
- `2 x CAN Bus` / `CAN 2.0` → `can_bus_count: 2`
- `1 x SIM Slot` / `nano-SIM` → `sim_slot_count: 1`

#### audio 解析

- `Line-out / Mic-in` → `{line_out:1, mic_in:1, spk_out:null}`
- `Speaker out + Mic` → `{line_out:null, mic_in:1, spk_out:1}`
- 無 audio 相關描述 → `{line_out:null, mic_in:null, spk_out:null}`

---

## Cross-BU Normalization Rules (Apply to ALL Product Lines)

> 本節規則適用於所有 BU 的 Parser，每個 BU 專屬規則在後續章節補充。

---

### C-1. `part_no` 偵測規則

依型號前綴判斷所屬 BU / 產品線：

| 前綴 | 產品線 / BU |
|------|------------|
| `ABOX-` | AIoT BU — Box PC |
| `ASBC-` | AIoT BU — SBC |
| `AXMB-` | AIoT BU — Industrial Motherboard |
| `AIPC-` | AIoT BU — Embedded System |
| `ARAK-` | AIoT BU — Rugged system |
| `APEX-` | AIoT BU（除 APEX-A100 屬 IPA BU）|
| `APEX-A` | IPA BU — Qualcomm APEX |
| `EGNN-` / `EG-` / `EGMN-` | Flash Storage — M.2 NVMe |
| `ES-` / `EDT-` | Flash Storage — 2.5" SATA |
| `EMO-` / `EMSN-` | Flash Storage — mSATA |
| `ESD-` | Flash Storage — SATA DOM |
| `SATA-` | Flash Storage — SATA |
| `DDRX-` / `M-` | DRAM Module |
| `EFSS-` | Flash Storage — CFast/SD |
| `EV-` / `EVCM-` | Camera Module |
| `EMPL-` / `EMAP-` | I/O Module (PCIe) |
| `EMPU-` | I/O Module (USB) |
| `EMCN-` / `EMCT-` | Networking — CAN Bus / Serial |
| `EMLN-` | Networking — LAN |
| `EMPOE-` | Networking — PoE |
| `EMSE-` | Air Sensor |

**規則：** `part_no` 由 datasheet 標題 / header 最大字體文字擷取；若無法擷取，由資料夾名稱推斷。`UNKNOWN` 時記錄 warning 到 `parse_log.json`。

---

### C-2. 共用 `certifications` 正規化

（同 AIoT BU Rule 7，適用全 BU）

| 原文書寫 | 儲存陣列 |
|---------|---------|
| `CE/FCC Class B/RoHS/UKCA` | `["CE","FCC","RoHS","UKCA"]` |
| `CE / FCC / RoHS` | `["CE","FCC","RoHS"]` |
| `UL/CE/FCC` | `["UL","CE","FCC"]` |
| `FCC Class B` → 統一為 | `"FCC"` |
| `RoHS 2.0` / `RoHS Compliant` → 統一為 | `"RoHS"` |
| `REACH` → 保留 | `"REACH"` |

---

### C-3. 共用 `temp_grade` 推斷（當未明確標示時）

（同 AIoT BU Rule 5）

| 條件 | `temp_grade` |
|------|-------------|
| op_min ≤ −40 AND op_max ≥ 70 | `"Wide"` |
| op_min ≤ −20 AND op_max ≥ 60 | `"Industrial"` |
| op_min ≥ 0  AND op_max ≤ 70 | `"Commercial"` |
| 其他 / 無資訊 | `"Industrial"`（保守預設） |

多 SKU 同頁 → 取最寬溫度範圍（min 最小、max 最大）。

---

### C-4. `lifecycle_status` 偵測規則

| 偵測條件 | 值 |
|---------|---|
| 資料夾 / 檔名含 `Preliminary` 或 `Pre-release` | `"NRND"` |
| datasheet 標題含 `Preliminary` / `Draft` | `"NRND"` |
| datasheet 含 `EOL` / `End of Life` / `Last-Time-Buy` | `"EOL"` |
| 否則 | `"Active"` |

---

### C-5. `product_name` 共用格式

格式：`{品類標籤} {型號}`

- 品類標籤來自 datasheet header（第一頁最大字體標題）
- 型號來自 `part_no`
- 範例：`"SBC ASBC-3150"`、`"NVMe SSD EGNN-25T128-B1"` 、`"Camera Module EV-C2M40-FF"`

---

### C-6. 共用 `op_temp` 解析格式

| 原文格式 | 解析結果 |
|---------|---------|
| `Operating Temperature: -40°C ~ 85°C` | `op_temp_min_c: -40, op_temp_max_c: 85` |
| `0 to 60°C` / `0°C to 60°C` | `min: 0, max: 60` |
| `-20°C to +70°C` | `min: -20, max: 70` |
| `Op. Temp.: 0 ~ 70 °C` | `min: 0, max: 70` |
| 表格行：`Operating Temperature` + 值欄 | 同上 |

**注意：** 儲存值型別為 `integer`，不是字串。若 datasheet 僅列出 `temp_grade`（如 `"Industrial Grade"`）而無確切數值，`op_temp_min_c / op_temp_max_c` 均為 `null`，然後套用 C-3 反向推斷 `temp_grade`。

---

## IPA BU Parser Rules（Qualcomm / AMD-Xilinx）

> 適用產品線：`computing_ipa`；`bu_owner = "IPA"`

---

### I-1. `platform_brand` 偵測

| datasheet 關鍵字 | `platform_brand` |
|----------------|----------------|
| `Qualcomm` / `Snapdragon` / `Cloud AI` | `"Qualcomm"` |
| `AMD` / `Xilinx` / `Kria` / `Zynq` / `Versal` | `"AMD-Xilinx"` |
| `NVIDIA` / `Jetson` | `"NVIDIA"`（若未來新增） |

---

### I-2. Qualcomm `processor_model` 正規化

| datasheet 原文 | `processor_model` | `processor_series` |
|-------------|-----------------|-----------------|
| `Qualcomm® Cloud AI 100 Ultra` | `Qualcomm Cloud AI 100 Ultra` | `"Qualcomm Cloud AI"` |
| `Qualcomm Cloud AI 100` | `Qualcomm Cloud AI 100` | `"Qualcomm Cloud AI"` |
| `Snapdragon X Elite` | `Snapdragon X Elite` | `"Snapdragon X"` |
| `Snapdragon 865` | `Snapdragon 865` | `"Snapdragon 800"` |

去除 `®` / `™` 符號後原文保留。

---

### I-3. Qualcomm `ai_tops` 解析

| datasheet 原文 | `ai_tops` |
|-------------|---------|
| `200 TOPS` | `200` |
| `870 TOPS (INT8)` | `870` |
| `30 TOPS (INT8) per card` | `30`（單卡值）|
| 多卡描述（如 `2 × 200 TOPS`）| 取**單卡最大值** `200`（非加總） |

**規則：** `ai_tops` 代表單一運算模組的最大可用 AI 算力。多卡加速器架構取單卡 TOPS，不加總。

---

### I-4. AMD-Xilinx `processor_model` 正規化

| datasheet 原文 | `processor_model` | `processor_series` |
|-------------|-----------------|-----------------|
| `Kria K26 SOM` | `AMD Kria K26` | `"Kria"` |
| `Zynq UltraScale+ MPSoC ZU4EV` | `Zynq UltraScale+ ZU4EV` | `"Zynq UltraScale+"` |
| `Versal AI Core Series VC1902` | `Versal VC1902` | `"Versal"` |

去除型號中的 `MPSoC` / `Series` 冗詞；保留核心型號識別符。

---

### I-5. AMD-Xilinx `ai_tops` 解析

| datasheet 原文 | `ai_tops` |
|-------------|---------|
| `26 TOPS (INT8)` | `26` |
| `1.4 TFLOPS` | `null`（TFLOPS ≠ TOPS；記錄 warning）|
| `DSP: 1,968 slices` | `null`（DSP slice 非 TOPS）|

若 datasheet 只提供 TFLOPS / GFLOPS，`ai_tops` 設 `null` 並在 `key_features` 記錄原始算力描述。

---

### I-6. IPA BU `sdk` 正規化

| datasheet 關鍵字 | `sdk` 值 |
|---------------|---------|
| `SNPE` / `Snapdragon Neural Processing Engine` | `"SNPE"` |
| `QNN` / `Qualcomm AI Engine Direct` | `"QNN"` |
| `Vitis AI` / `Vitis-AI` | `"Vitis-AI"` |
| `OpenVINO` | `"OpenVINO"`（Qualcomm 通常無此項）|
| `TFLite` / `TensorFlow Lite` | `"TFLite"` |
| `ONNX Runtime` | `"ONNX"` |

多個 SDK 同時出現 → 儲存為陣列，如 `["SNPE","QNN"]`。

---

### I-7. IPA BU CPU cores 規則

- Qualcomm Cloud AI 100 系列：本身是 PCIe 加速卡，無 CPU → `cpu_cores / cpu_p_cores / cpu_e_cores` 均為 `null`
- APEX-A100（含主機 CPU）：以 host CPU 型號查表（同 AIoT BU Rule 11）
- AMD-Xilinx SoC：以 datasheet 明確標示為準（如 `Cortex-A53 Quad` → `cpu_cores: 4`）；`cpu_p_cores / cpu_e_cores = null`

---

## Camera Module Parser Rules

> 適用產品線：`camera`；填入 `camera_spec` 欄位

---

### CAM-1. `interface_bus` 正規化

| datasheet 關鍵字 | `interface_bus` |
|---------------|---------------|
| `USB 2.0` / `UVC` | `"USB2.0"` |
| `USB 3.0` / `USB 3.2` | `"USB3.0"`（統一用此值）|
| `MIPI CSI-2` / `MIPI CSI2` / `4-lane MIPI` | `"MIPI-CSI2"` |
| `MIPI Type-C` / `USB Type-C (MIPI)` | `"MIPI-TypeC"` |
| `GMSL2` / `GMSL 2` / `Gigabit Multimedia Serial Link` | `"GMSL2"` |

---

### CAM-2. `resolution_mp` 與 `resolution_px` 解析

| datasheet 原文 | `resolution_mp` | `resolution_px` |
|-------------|--------------|--------------|
| `2 MP` / `2.0 Megapixel` | `2.0` | 由解析度計算或同行讀取 |
| `1920 × 1080` / `1080p` | `2.1` | `"1920x1080"` |
| `3840 × 2160` / `4K` | `8.3` | `"3840x2160"` |
| `2592 × 1944` | `5.0` | `"2592x1944"` |
| `640 × 480` / `VGA` | `0.3` | `"640x480"` |

**規則：** `×` / `x` / `X` 統一替換為小寫 `x` 儲存。若 MP 數字和像素解析度同時出現，以 MP 為主；若只有像素，計算 `(W × H) / 1,000,000` 四捨五入至一位小數。

---

### CAM-3. `fps` 解析

| datasheet 原文 | `fps` |
|-------------|-----|
| `30fps` / `30 FPS` / `30Hz` | `30` |
| `Up to 60fps` / `Max. 60fps` | `60` |
| `60fps @ 1080p / 30fps @ 4K` | `60`（取最大值）|

---

### CAM-4. `sensor_type` 與 `sensor_size`

| datasheet 原文 | `sensor_type` | `sensor_size` |
|-------------|-------------|-------------|
| `CMOS Sensor` | `"CMOS"` | — |
| `BSI CMOS` / `Back-Illuminated` | `"BSI"` | — |
| `1/2.7"` / `1/2.7 inch` | — | `"1/2.7inch"` |
| `1/3"` | — | `"1/3inch"` |
| `Type 1/3` | — | `"1/3inch"` |

**規則：** `sensor_size` 格式統一為 `"{分子}/{分母}inch"`（去除空格，補上 `inch`）。

---

### CAM-5. `lens_fov_deg` 解析

| datasheet 原文 | `lens_fov_deg` |
|-------------|-------------|
| `FOV: 80°` / `80° FOV` | `80` |
| `HFOV: 90°` | `90`（若無標示 H/V，預設 HFOV）|
| `D-FOV: 120°` | `120`（對角視角）|
| `Wide Angle (90°)` | `90` |

---

### CAM-6. `hdr` / `ir_filter` / `low_light` 偵測

| 關鍵字 | 欄位 | 值 |
|------|------|---|
| `HDR` / `Wide Dynamic Range` / `WDR` | `hdr` | `true` |
| `IR Cut Filter` / `IR Filter` / `Night Vision` | `ir_filter` | `true` |
| `Low Light` / `Starlight` / `F1.8` 以下光圈 | `low_light` | `true` |
| 無上述關鍵字 | 以上三欄 | `false` |

---

### CAM-7. `adapter_board_compatible` 解析

- 掃描 datasheet 的 "Compatible" / "Works with" / "Supported Platform" 段落
- 匹配已知型號前綴（ABOX、ASBC、Jetson、Raspberry Pi 等）
- 範例：`"Compatible with NVIDIA Jetson AGX Orin"` → `["Jetson AGX Orin"]`
- 若無明確描述 → 空陣列 `[]`

---

## I/O Module Parser Rules

> 適用產品線：`io`；填入 `io_spec` 欄位

---

### IO-1. `subcategory` 偵測

| 產品名稱 / 功能關鍵字 | `subcategory` |
|--------------------|-------------|
| `Storage Expander` / `RAID` / `JBod` | `"Storage"` |
| `Disk Array` / `HBA` | `"DiskArray"` |
| `Display Adapter` / `HDMI Output` / `GPU-less Display` | `"Display"` |
| `OOB` / `Out-of-Band` / `IPMI` / `BMC` | `"OOB"` |
| `InnoEx` / `Virtual I/O` / `SR-IOV` | `"InnoEx-VirtualIO"` |
| `Testing` / `Diagnostic` / `Signal Generator` | `"TestingTool"` |

---

### IO-2. `host_interface` 與 `pcie_gen` 正規化

| datasheet 原文 | `host_interface` | `pcie_gen` |
|-------------|--------------|----------|
| `PCIe x4 Gen3` / `PCIe 3.0 x4` | `"PCIe"` | `"Gen3"` |
| `PCIe x4 Gen4` / `PCIe 4.0 x4` | `"PCIe"` | `"Gen4"` |
| `PCIe Gen 3 x1` | `"PCIe"` | `"Gen3"` |
| `USB 3.2` / `USB 3.0` | `"USB"` | `null` |
| `M.2 M-key` / `M.2 B+M key` | `"M.2"` | 依 M.2 slot 介面標示 |

---

### IO-3. `port_type` 陣列正規化

`port_type` 儲存該卡對外提供的 Port 類型列表。

| datasheet 原文 | `port_type` 值 |
|-------------|-------------|
| `SATA 6Gb/s` | `"SATA"` |
| `NVMe` | `"NVMe"` |
| `HDMI 2.0` | `"HDMI"` |
| `DisplayPort 1.4` | `"DP"` |
| `USB 3.2 Gen2 Type-A` | `"USB3.2 Gen2"` |
| `RJ45 (GbE)` | `"GbE"` |
| `M.2 B+M Key` (擴充出) | `"M.2"` |

多種 port → `["SATA","NVMe"]` 等陣列。

---

### IO-4. `port_count` 規則

- `port_count` = 同類 port 的**總數量**（加總所有速度階段）
- 範例：`2 x SATA + 4 x SATA` → `port_count: 6`
- 若不同速度 / 規格混用，以**最高速**的 count 為主，其餘記入 `key_features`

---

### IO-5. PCIe Card 物理規格推斷

| 關鍵字 | 推斷 |
|------|------|
| `Half-Height Half-Length` / `HHHL` | `key_features` 加入 `"HHHL form factor"` |
| `Full-Height Full-Length` / `FHFL` | `key_features` 加入 `"FHFL form factor"` |
| `Low Profile` | `key_features` 加入 `"Low Profile"` |
| `M.2` host interface | 無此推斷（M.2 無物理尺寸規格） |

---

## Networking Module Parser Rules

> 適用產品線：`networking`；填入 `networking_spec` 欄位

---

### NET-1. `subcategory` 偵測

| 產品名稱 / 功能關鍵字 | `subcategory` |
|--------------------|-------------|
| `LAN` / `GbE` / `Ethernet` / `NIC` | `"LAN"` |
| `CAN Bus` / `CAN FD` / `CAN 2.0` | `"CAN-Bus"` |
| `RS-232` / `RS-485` / `Serial` / `COM` | `"Serial"` |
| `PoE` / `Power over Ethernet` | `"PoE"` |

---

### NET-2. `speed_gbps` 正規化（同 AIoT BU GbE 規則）

| datasheet 原文 | `speed_gbps` |
|-------------|------------|
| `GbE` / `1GbE` / `1000Mbps` | `1` |
| `2.5GbE` / `2500Mbps` | `2.5` |
| `10GbE` / `10000Mbps` / `10G` | `10` |
| `25GbE` | `25` |
| `100GbE` | `100` |

---

### NET-3. `protocol` 陣列（Serial 子類）

| datasheet 原文 | `protocol` 值 |
|-------------|-------------|
| `RS-232` only | `["RS-232"]` |
| `RS-422` only | `["RS-422"]` |
| `RS-485` only | `["RS-485"]` |
| `RS-232/422/485` / software selectable | `["RS-232","RS-422","RS-485"]` |
| 同一卡有 2x RS-232 + 4x RS-232/422/485 | `["RS-232","RS-422","RS-485"]`（聯集）|

---

### NET-4. PoE 功率規則

| datasheet 原文 | `poe_watt` | 備注 |
|-------------|----------|------|
| `IEEE 802.3af` / `15W PoE` | `15` | |
| `IEEE 802.3at` / `30W PoE+` | `30` | |
| `IEEE 802.3bt` / `60W PoE++` / `90W` | `60` or `90` | 以 datasheet 明確值為準 |
| 只寫 `PoE` 未標準 | `15`（保守預設）| 記錄 warning |

---

### NET-5. CAN Bus 規則

| datasheet 原文 | `can_fd_support` | `port_count` |
|-------------|----------------|------------|
| `CAN FD` / `CAN Flexible Data Rate` | `true` | 以 port count 為準 |
| `CAN 2.0` / `CAN 2.0A/2.0B` | `false` | |
| `CAN Bus` (未標版本) | `false`（保守預設）| |
| `ISO 11898` | `false`（ISO 11898 = CAN 2.0）| |
| `ISO 11898-1:2015` (CAN FD 標準) | `true` | |

`isolation` 欄位：datasheet 含 `Galvanic Isolation` / `Isolated` / `2500V isolation` → `true`，否則 `false`。

---

## Flash Storage Parser Rules

> 適用產品線：`flash`；填入 `flash_spec` 欄位

---

### FL-1. `interface_bus` 與 `pcie_gen` 正規化

| datasheet 原文 | `interface_bus` | `pcie_gen` |
|-------------|--------------|----------|
| `PCIe Gen3` / `PCIe 3.0 NVMe` | `"PCIe"` | `"Gen3"` |
| `PCIe Gen4` / `PCIe 4.0 NVMe` | `"PCIe"` | `"Gen4"` |
| `SATA 6Gb/s` / `SATA III` / `SATA 3.0` | `"SATA"` | `null` |
| `USB 3.2` / `USB 3.0` | `"USB"` | `null` |
| `PATA` / `IDE` | `"PATA"` | `null` |

---

### FL-2. `form_factor` 正規化

| datasheet 原文 / 型號前綴 | `form_factor` |
|----------------------|-------------|
| `M.2 2280` / `M.2 2242` 等 | `"M.2"` |
| `U.2` / `U.3` / `2.5" U.2` | `"U.2"` |
| `CFexpress Type B` | `"CFexpress"` |
| `2.5"` / `2.5-inch` / `SFF` | `"2.5inch"` |
| `SATA DOM` / `DOM` / `Disk on Module` | `"SATADOM"` |
| `mSATA` / `Mini-SATA` | `"mSATA"` |
| `CFast` | `"CFast"` |
| `nanoSSD` | `"nanoSSD"` |
| `CompactFlash` / `CF Card` | `"CompactFlash"` |
| `SD` / `microSD` | `"SD"` |
| `USB Flash` / `USB EDC` / `USB Disk` | `"USB-EDC"` |

---

### FL-3. `nand_type` 正規化

| datasheet 原文 | `nand_type` |
|-------------|-----------|
| `SLC` / `Single-Level Cell` | `"SLC"` |
| `iSLC` / `Industrial SLC` / `pSLC` | `"iSLC"` |
| `MLC` / `Multi-Level Cell` | `"MLC"` |
| `TLC` / `Triple-Level Cell` / `3D TLC` | `"TLC"` |
| `3D TLC NAND` | `"3D-TLC"` |
| `QLC` | `"QLC"` |

---

### FL-4. `capacity_gb` 正規化

| datasheet 原文 | `capacity_gb` |
|-------------|-------------|
| `128GB` / `128 GB` | `128` |
| `512GB` | `512` |
| `1TB` / `1 TB` | `1024` |
| `2TB` | `2048` |
| `256MB` | `0.256`（或記錄 warning，Flash < 1GB 少見）|

**規則：** TB → 乘以 1024；GB → 直接取數字。型號中多個容量（如 `128G/256G/512G`）→ 以**最大容量**解析，其他容量記入 `key_features`。

---

### FL-5. 性能數值解析（`seq_read_mbps` / `seq_write_mbps`）

| datasheet 原文 | 欄位 | 值 |
|-------------|------|---|
| `Sequential Read: 3,500 MB/s` | `seq_read_mbps` | `3500` |
| `Read Up to 3.5 GB/s` | `seq_read_mbps` | `3500`（GB/s → MB/s × 1000）|
| `Write: 1,800 MB/s` | `seq_write_mbps` | `1800` |
| `R/W: 550/520 MB/s` | read: `550`, write: `520` | 斜線分隔 |

---

### FL-6. IOPS 解析（`rand_read_iops` / `rand_write_iops`）

| datasheet 原文 | 欄位 | 值 |
|-------------|------|---|
| `Random Read: 400K IOPS` / `400,000 IOPS` | `rand_read_iops` | `400000` |
| `Random Write: 60K IOPS` | `rand_write_iops` | `60000` |
| `R/W: 85K / 20K IOPS` | read: `85000`, write: `20000` | |

**規則：** `K` = × 1000；`M` = × 1,000,000（極少見）；儲存為整數。

---

### FL-7. 耐久度解析（`tbw` / `dwpd`）

| datasheet 原文 | 欄位 | 值 |
|-------------|------|---|
| `TBW: 300 TB` / `300TBW` | `tbw` | `300` |
| `1 DWPD` / `1.0 DWPD (5-year)` | `dwpd` | `1.0` |
| `DWPD: 0.3` | `dwpd` | `0.3` |

若只有 TBW，`dwpd` 設 `null`；若只有 DWPD，`tbw` 設 `null`。

---

### FL-8. 功能旗標偵測

| datasheet 關鍵字 | 欄位 | 值 |
|---------------|------|---|
| `Power Loss Protection` / `PLP` / `Capacitor backup` | `power_loss_protection` | `true` |
| `AES 256` / `AES-256` / `Hardware Encryption` | `aes_encryption` | `true` |
| `S.M.A.R.T.` / `SMART Support` | `smart_support` | `true` |
| 無以上關鍵字 | 以上三欄 | `false` |

---

## DRAM Module Parser Rules

> 適用產品線：`dram`；填入 `dram_spec` 欄位

---

### DR-1. `interface_bus` 正規化

| datasheet 原文 | `interface_bus` |
|-------------|---------------|
| `DDR5` / `LPDDR5` | `"DDR5"` |
| `DDR4` / `LPDDR4` | `"DDR4"` |
| `DDR3` / `DDR3L` | `"DDR3"` |
| `DDR2` | `"DDR2"` |
| `DDR` (不含數字) | `"DDR"` |
| `SDRAM` | `"SDRAM"` |
| `CXL` / `CXL 2.0` | `"CXL"` |

---

### DR-2. `form_factor` 正規化

| datasheet 原文 | `form_factor` |
|-------------|-------------|
| `SO-DIMM` / `SODIMM` / `204-pin` (DDR3) | `"SO-DIMM"` |
| `DIMM` / `UDIMM` / `288-pin` (DDR4/5) | `"DIMM"` |
| `LPDIMM` / `LP-DIMM` | `"LPDIMM"` |
| `UDIMM` (Unbuffered DIMM) | `"UDIMM"`（若需與 RDIMM 區分則保留）|
| `RDIMM` / `Registered DIMM` | `"DIMM"`（registered=true）|

---

### DR-3. `capacity_gb` 正規化

（同 FL-4 Flash，TB = 1024 GB）

| 原文 | 值 |
|-----|---|
| `8GB` | `8` |
| `16GB` | `16` |
| `32GB` | `32` |
| `64GB` | `64` |
| `128GB` | `128` |

型號中多容量（如 `4G/8G/16G`）→ 取最大值 `16`。

---

### DR-4. `speed_mhz` 解析

| datasheet 原文 | `speed_mhz` |
|-------------|-----------|
| `DDR4-3200` / `PC4-25600` | `3200` |
| `DDR5-4800` | `4800` |
| `DDR5-5600` | `5600` |
| `3200 MHz` / `3200MT/s` | `3200` |
| `2400MHz` (DDR4) | `2400` |
| `DDR3-1600` / `PC3-12800` | `1600` |

**規則：** 若標示 `MT/s`（Mega-transfers/second），數值直接等於 `speed_mhz`（DDR 是雙倍速率，MT/s = effective MHz × 2，但業界習慣直接取 MT/s 數字）。

---

### DR-5. `ecc` / `registered` 偵測

| datasheet 關鍵字 | `ecc` | `registered` |
|---------------|-----|------------|
| `ECC` / `Error Correction Code` | `true` | — |
| `Registered` / `RDIMM` | — | `true` |
| `Unbuffered` / `UDIMM` | — | `false` |
| `Non-ECC` | `false` | — |
| 無標示 → 預設 | `false` | `false` |

---

### DR-6. `voltage_v` 解析

| datasheet 原文 | `voltage_v` |
|-------------|-----------|
| `1.2V` (DDR4/DDR5 標準) | `1.2` |
| `1.1V` (DDR5 低壓) | `1.1` |
| `1.35V` (DDR3L) | `1.35` |
| `1.5V` (DDR3) | `1.5` |
| `1.8V` (DDR2) | `1.8` |

---

### DR-7. `low_profile` 偵測

| 關鍵字 | `low_profile` |
|------|-------------|
| `Low Profile` / `LP` / `Height: 30mm` 以下 | `true` |
| 標準高度 / `31.25mm` (DDR4 SO-DIMM) / 無標示 | `false` |

---

### DR-8. `ai_optimized` 偵測

| 關鍵字 | `ai_optimized` |
|------|--------------|
| `AI Optimized` / `AI Memory` / `High Bandwidth` / `HBM` | `true` |
| 一般 commodity DRAM | `false` |

---

## Key Design Decisions (do not revert without discussion)

1. **No cloud server** — static files only; all indexing is local
2. **`interface_bus` is product-line specific** — not in `common` block
3. **Software (iVIT/iCAP) is optional POC suggestion** — `bundle_required: false` always
4. **AIoT BU products are not on the website** — parser must rely 100% on PDF
5. **`bu_owner` field** distinguishes IPA vs AIoT inside `computing_spec` — one unified block, not split
6. **Hash-diff on update** — only re-parse PDFs whose MD5 has changed
7. **Competitor comparison uses web_search + manual fallback** — never assume web_search succeeds; always offer paste-text fallback
8. **text_summary generated by local Ollama** — not Claude API; keeps update pipeline cost at $0
9. **Price comparison is out of scope** — competitor pricing not reliably public
10. **Schema v3.0 migration** — `dimensions_mm` (string) and `expansion_slots` (string) removed; replaced by `dimensions` (object), `pcie_slots` (array), `m2_slots` (array), `io_ports` (object). `ram_gb` kept as backward-compat shorthand. Requires full re-parse of all 52 AIoT BU datasheets.
11. **`connectivity` flat list is auto-generated** — Parser derives it from `io_ports` + `pcie_slots` + `m2_slots`; never populated manually. Used only for quick keyword search in text_summary embeddings.
