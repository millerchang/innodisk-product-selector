# Innodisk Product Selector — 電腦交接文件

**日期**：2026-06-01
**作者**：Miller Chang（Innodisk FAE Manager）
**GitHub Repo**：`https://github.com/millerchang/innodisk-product-selector`（Private）

---

## 🔖 接手補充（2026-06-08）— 換帳號 / 換電腦繼續開發

> 此段為最新狀態，與下方 2026-06-01 原文若有出入，**以此段為準**。

### 進度狀態
- 最新 commit：`64d8702` "Fix RFQ solution accuracy and refine selector UX"，**已 push 到 origin/main**。
- 工作目錄 clean，從 GitHub clone 即是最新進度。
- **主力 App 已改為 `webapp/src/` 的 React + Vite 版**（含 AI RFQ 解決方案組合 / solution builder），不再是 standalone.html（standalone.html 仍可當作免 Node 的 demo 備案）。

### 換帳號 / 換電腦的標準起手式
```powershell
git clone https://github.com/millerchang/innodisk-product-selector.git
cd innodisk-product-selector\webapp
.\copy_data.ps1     # 從 git 內的 output/spec_matrix.json 還原到 public/
npm install         # node_modules 重裝，勿沿用複製過去的（平台 binary 問題）
npm run dev
```
最後到 App 右上角 **⚙ Settings** 重新貼一次 Anthropic API Key 即可繼續。

### ⚠️ git 沒帶走、接手要自行還原的東西
| 項目 | 是否在 git | 還原方式 |
|------|-----------|---------|
| `output/spec_matrix.json` | ✅ 有追蹤 | 已在 repo 內 |
| `webapp/public/spec_matrix.json` | ❌ gitignore | clone 後跑 `webapp\copy_data.ps1` |
| `webapp/node_modules` | ❌ gitignore | `npm install` |
| `webapp/dist`（已 build 成品）| ❌ gitignore | `npm run build`，或直接用 dev |
| `.env`（secrets / API key）| ❌ gitignore | **手動從舊電腦複製**，不會在 GitHub 上 |
| 瀏覽器 API Key（localStorage）| ❌ 不在資料夾 | 新機器 ⚙ Settings 重貼 |

### Demo（不開發、只展示）最省事的方式
```powershell
cd webapp\dist
python -m http.server 3000   # 開 http://localhost:3000，免 Node、免 build
```
記得：**demo 機要能上網**（App 直接呼叫 api.anthropic.com）+ 到 Settings 貼 API key。

### 切換 GitHub 帳號 push 時
- remote 走 HTTPS：`https://github.com/millerchang/innodisk-product-selector.git`
- 新帳號需有此 repo 的權限，並用該帳號的 **PAT（Personal Access Token）** 認證。
- 若要改推到不同 repo：`git remote set-url origin <新網址>`。

---

## TL;DR — 在新電腦重新跑起來需要做的事

1. Clone repo
2. 安裝 Python 3.11 + pip 套件
3. 確認 Datasheet PDF 路徑（或複製過來）
4. 執行 `pipeline.py` 重新 parse（如有新 datasheet）
5. 用 Python HTTP server 開 `webapp/` 預覽 UI

---

## 1. 專案架構說明

```
Innodisk_Product_Selector/
├── parser/                    ← 核心 Python 程式
│   ├── pipeline.py            ← 主要入口：執行整個 parse 流程
│   ├── rule_extractor.py      ← PDF → raw fields（rule-based + regex）
│   ├── schema_builder.py      ← raw → 標準 JSON schema
│   ├── product_catalog.py     ← 已知產品目錄（part_no → product_line 對應）
│   ├── ark_fetcher.py         ← 抓取 Intel ARK 網站資料更新 cpu_library
│   ├── vision_extractor.py    ← Claude Vision API fallback（低信心產品）
│   └── debug_*.py / test_*.py ← 除錯用腳本
├── output/
│   ├── spec_matrix.json       ← 74 筆產品資料（主要輸出）
│   ├── cpu_library.json       ← Intel/NXP/Qualcomm CPU 規格查找表
│   └── parse_log.json         ← 每次 parse 的信心分數與 warning
├── webapp/
│   ├── standalone.html        ← ✅ 目前主要使用的 UI（單一 HTML 無需 build）
│   ├── public/spec_matrix.json ← standalone.html 讀取的資料（從 output/ 複製）
│   ├── src/                   ← React + Vite 版 webapp（未來擴充用）
│   └── copy_data.ps1          ← 將 output/spec_matrix.json 同步至 public/
├── CLAUDE.md                  ← 完整 Schema 規範與 Parser 規則（AI 使用）
└── HANDOVER.md                ← 本文件
```

---

## 2. Datasheet PDF 路徑（不在 repo 內）

> ⚠️ PDF 檔案留在原始路徑，**沒有上傳到 GitHub**。新電腦需要另外複製或重新確認路徑。

| 產品線 | 原路徑 |
|--------|--------|
| AIoT BU（Intel/NXP） | `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\AIoT\1.Datasheet\` |
| Camera Module | `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\Camera\1.0 Datasheet\` |
| IPA BU（Qualcomm）| `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\IPA\EP\Computing\` |
| IPA EP — Air Sensor | `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\IPA\EP\Air Sensor\` |
| IPA EP — IO Modules | `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\IPA\EP\IO Modules\` |
| IPA EP — Networking | `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\IPA\EP\Networking\` |
| Naming Rules | `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\Innodisk Product Naming Rule\` |

**在新電腦操作方式：**
- Datasheet 根目錄已統一放在 `D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\` 下對應子資料夾
- `parser/pipeline.py` 的 `DATASHEET_ROOTS` 已對應此路徑，無需額外修改

---

## 3. 環境安裝

### Python 套件（必裝）

```powershell
pip install pdfplumber anthropic
```

| 套件 | 用途 |
|------|------|
| `pdfplumber` | PDF 文字萃取 |
| `anthropic` | Claude Vision API fallback（低信心產品用） |

### Python 版本

- **Python 3.11**（推薦）
- 下載：https://www.python.org/downloads/release/python-3110/

### 選項：安裝 Node.js（若要用 Vite webapp）

```bash
npm install   # 在 webapp/ 目錄下執行
npm run dev   # 啟動開發伺服器
```

> standalone.html **不需要 Node.js**，直接用 Python HTTP server 即可。

---

## 4. 執行流程

### 4-1. 啟動 UI（最簡單）

```powershell
# 在 webapp/ 目錄下執行
cd webapp
python -m http.server 3000
# 開瀏覽器 http://localhost:3000/standalone.html
```

### 4-2. 重新 parse 所有 datasheet

```powershell
cd parser
python pipeline.py
```

輸出寫入 `output/spec_matrix.json` 與 `output/parse_log.json`。

### 4-3. 更新 webapp 資料

```powershell
# 執行 webapp/copy_data.ps1 或手動複製
Copy-Item output\spec_matrix.json webapp\public\spec_matrix.json
```

### 4-4. 更新 cpu_library（抓 Intel ARK 資料）

```powershell
cd parser
python ark_fetcher.py
```

---

## 5. 目前已處理的產品（74 筆）

| 產品線 | 數量 | 說明 |
|--------|------|------|
| AIoT BU（Intel/NXP） | 52 | ABOX / ASBC / AXMB / AIPC / APEX / ARAK |
| IPA BU（Qualcomm） | 1 | APEX-A100 |
| Camera Module | 21 | EV* USB/MIPI/GMSL2 + EB* Capture Card |
| **合計** | **74** | |

---

## 6. 尚未處理的產品線

| 產品線 | 狀態 |
|--------|------|
| Flash Storage（SSD/NVMe/SATA） | Parser 規則已寫在 CLAUDE.md，尚未實際執行 |
| DRAM Module | 同上 |
| I/O Module | 同上 |
| Networking（LAN/CAN/Serial/PoE） | 同上 |
| Air Sensor | 同上 |

---

## 7. Claude API 設定（查詢功能）

UI 的「自然語言查詢」功能需要 Anthropic API Key：

1. 取得 API Key：https://console.anthropic.com/
2. 在 webapp UI 右上角 ⚙ 設定圖示 → 輸入 API Key
3. Key 只儲存在瀏覽器 localStorage（不上傳）

---

## 8. 已知問題與 TODO

| 項目 | 說明 |
|------|------|
| Capture Card（EB*）規格 | interface_bus 顯示 PCIe 但缺少 port_count 等詳細規格，需 Vision API |
| Camera sensor_type | 多數為 null（PDF 文字不明確標示 CMOS） |
| AXMB-L120 | 尚未解析（新產品），需重新執行 pipeline |
| ABOX-V140 / AXMB-3120 | dimensions 為 null，需重新確認 datasheet |
| Flash/DRAM/IO/Networking | 尚未執行 parse，待後續 Sprint |

---

## 9. Git 操作備忘

```bash
# Clone
git clone https://github.com/millerchang/innodisk-product-selector.git

# 確認當前狀態
git status

# 新增修改並 commit
git add -A
git commit -m "描述修改內容"

# Push（需要 GitHub PAT）
git push origin main
```

---

## 10. 重要設計決策（不要輕易更改）

1. **無雲端伺服器** — `spec_matrix.json` 是靜態檔案，query 只呼叫 Claude API
2. `interface_bus` 欄位在各 `_spec` block 內，**不在** `common` block（避免 Flash PCIe 和 Camera MIPI 混淆）
3. Camera 產品的 `interface_bus` 由**資料夾路徑**判斷（最可靠），文字 regex 為 fallback
4. `text_summary` 由**本機 Ollama**（qwen2.5:7b）生成，不用 Claude API（維持 $0 更新成本）
5. `parse_hash_cache.json` 記錄每個 PDF 的 MD5，未變更的 PDF 跳過重新 parse

---

*文件由 Claude AI 協助產生，最終由 Miller Chang 審閱*
