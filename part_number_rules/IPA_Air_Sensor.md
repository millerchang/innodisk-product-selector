# IPA BU — Air Sensor 料號編碼原則

對應 product_line：`air_sensor` ｜ bu_owner：`IPA`

> 資料夾：`IPA\EP\Air Sensor`
> **來源**：官方《EP_Naming Rule_26-05-11.xls》+ 實際 datasheet 檔名分析。

## 已確認規則

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `IAG` | air_sensor | IPA | （無） | Innodisk 氣體感測模組（Innodisk Air Gas + 氣體種類） |
| `ET3-IAERIS` | air_sensor | IPA | （無） | 子公司 維新(#3) iAeris 空氣品質產品（外購 / 代銷） |
| `EZ??` | air_sensor | IPA | （無） | EP「Others(Z)」體系感測相關模組（如 `EZU2-I301`） |

> **核心判斷**：
> - 前綴 `IAG` → Innodisk 氣體感測模組 → `air_sensor`
> - 前綴 `ET3-IAERIS` → iAeris（維新子公司）空品產品 → `air_sensor`

## IAG 氣體感測模組命名

樣式：`IAG` + 氣體種類，例如：
| 料號 | 氣體 / 量測 |
|------|------------|
| `IAGCO2` | CO₂（二氧化碳） |
| `IAGCO` | CO（一氧化碳） |
| `IAGM1` | HCHO（甲醛） |
| `IAGM2` | PM（懸浮微粒 PM2.5/PM10） |
| `IAGNO2` | NO₂（二氧化氮） |
| `IAGO3` | O₃（臭氧） |
| `IAGSO2` | SO₂（二氧化硫） |
| `IAGVOC` | TVOC（總揮發性有機物） |

## ET3-IAERIS 子公司產品（EP 表第 105~124 列）

樣式：`E T 3 - 客供料號`
- `E` = EP，`T` = 外購品，`3` = 子公司「維新」
- `-` 之後為 iAeris 自有料號（`IAERIS1`、`IAERIS2`、`IAERIS3`、`IAERIS5` …）
- iAeris 為空氣品質偵測 / 監測整機產品線。

> 註：iAeris 資料夾中含 user manual / datasheet 兩類，pipeline 已用 `User Manual` 關鍵字過濾非 datasheet PDF。
