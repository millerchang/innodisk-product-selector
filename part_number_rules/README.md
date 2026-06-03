# 料號編碼原則（Part Number Coding Rules）

這個資料夾收集 Innodisk **各 BU / 產品線的料號編碼規則**。
目的：讓 parser 能**靠料號前綴規則自動判斷分類**，取代目前 `parser/product_catalog.py` 裡一筆一筆手寫的對照表。

---

## 為什麼需要這個

目前分類是 100% 靠 `PRODUCT_CATALOG`（part_no → product_line / bu_owner / platform_brand）寫死的。
新產品若不在表內，會被預設誤分成 `computing_aiot / Intel`。

若有清楚的料號編碼原則，parser 就能：
1. 用**前綴規則**自動判斷 `product_line`、`bu_owner`、`platform_brand`
2. 新料號免維護對照表
3. 規則衝突或無法判斷時，才回退到人工 catalog

---

## 怎麼放檔案

- **一個 BU / 產品線一個檔案**（見下方清單）
- 格式不限：可以是文字說明、表格、或直接貼公司內部文件
- 若有官方 PDF / Excel 編碼原則，也可直接丟進對應檔名的資料夾或附在旁邊
- 填好後告訴我，我會把規則轉成 parser 可用的邏輯

---

## 建議格式（填表版，最利於程式解析）

每條規則一列。範例：

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `EXEC-`, `EXMP-` | computing_ipa | IPA | Qualcomm | COM-HPC Mini 高通主機板 |
| `EXMU-`, `EXOU-` | computing_ipa | IPA | AMD-Xilinx | Kria K26 FPGA |
| `ABOX-` | computing_aiot | AIoT | Intel / NXP | Box PC |

> 若編碼有「位置含義」（例如第 N 碼代表系列、第 M 碼代表溫度等級），
> 請用文字說明每一碼的意義，我會寫成解析規則。

---

## 檔案清單

| 檔案 | 對應產品線 | 狀態 |
|------|-----------|------|
| `AIoT_BU.md` | computing_aiot（Intel / NXP 系統板） | ✅ 已依官方 AIOT 命名規則填寫 |
| `Camera.md` | camera（相機模組 / Capture Card） | ✅ 已依官方 EP 命名規則填寫 |
| `IPA_Computing.md` | computing_ipa（Qualcomm / AMD-Xilinx） | ✅ 已依官方 EP 命名規則填寫 |
| `IPA_IO_Modules.md` | io | ✅ 已依官方 EP 命名規則填寫 |
| `IPA_Networking.md` | networking | ✅ 已依 EP 規則 + 檔名分析填寫 |
| `IPA_Air_Sensor.md` | air_sensor | ✅ 已依 EP 規則 + 檔名分析填寫 |
| `Flash.md` | flash（SSD / NVMe / SATA） | ✅ 已依官方 EM 命名規則填寫（資料夾未設定） |
| `DRAM.md` | dram（記憶體模組） | ✅ 已依官方 DRAM 命名規則填寫（資料夾未設定） |

> 官方來源：`D:\Innodisk\Innodisk Product Selector\Innodisk Product Naming Rule`（依 BU 分：DRAM / EM / EP / AIOT）。
