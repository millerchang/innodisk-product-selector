# IPA BU — Networking 料號編碼原則

對應 product_line：`networking` ｜ bu_owner：`IPA`

> 資料夾：`IPA\EP\Networking`
> **來源**：官方《EP_Naming Rule_26-05-11.xls》+ 實際 datasheet 檔名分析。

## 已確認規則

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `EGPC-` | networking | IPA | （N/A） | Innodisk PoE / GbE 網路擴充卡（PCIe） |
| `FARO-` | networking | IPA | （N/A） | 子公司 安捷科(Antzertech) 路由 / 網通品牌 |
| `GADN-` | networking | IPA | （N/A） | 子公司 安捷科(Antzertech) 網通模組品牌 |

> **核心判斷**：
> - `EGPC-` → Innodisk 自有網通卡 → `networking`
> - `FARO-` / `GADN-` → 安捷科子公司網通品牌（在 EP 表中歸「外購品 / 代銷品」ET2 體系）→ `networking`
> 網通卡無晶片平台屬性，platform_brand 留空。

## 補充：子公司 / 外購品命名（EP 表第 105~124 列）

子公司製成品與代銷品料號樣式：`E T n - 客供料號`
- 第 1 碼 `E` = EP
- 第 2 碼 `T` = 外購品（`A` = 自製品）
- 第 3 碼 = 子公司代碼：`1`巽晨 / `2`安捷科(Antzertech) / `3`維新 / `4`安提 / `5`尚茂智能 / `6`祥景電子 / `7`建騰創達 / `8`聯發光電 / `9`欣普羅 / `A`Sunrich / `B`先進國際 / `C`瑞嘉國際 / `D`FUHO / `E`創維 / `F`VCA(TECOSTAR)
- `-` 之後沿用該子公司自有料號（如 `FARO-FD700`、`GADN-FG7U0`），不照 Innodisk 位碼規則。

> 註：`FARO` / `GADN` 為安捷科(子公司#2)的對外品牌名稱，故 datasheet 檔名直接用品牌料號，
> 而非 `ET2-...` 內部料號。分類時以品牌前綴 `FARO-` / `GADN-` 判斷。
