# Flash Storage 料號編碼原則

對應 product_line：`flash` ｜ bu_owner：`EM`（嵌入式記憶體事業群）

> SSD / NVMe / SATA / SATADOM 等
> **來源**：官方《EM Product Naming Rule_26-02-04.xls》工作表 `主類碼`。
> ⚠️ 目前 pipeline 尚未設定 flash datasheet 資料夾；本檔先作為參考文件。

## 已確認規則

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `D` + 系列碼 | flash | EM | （無） | 第 1 碼固定 `D` = Disk |

> **核心判斷**：第 1 碼 `D`（Disk）+ 第 2 碼系列碼 + 第 3~5 碼產品種類 → `flash`。

## 料號逐碼意義（主類碼）

樣式：`D E S25 - A28 D61 S C A E S n`（位 1 + 位 2 + 位 3~5 + 位 6 容量 + 位 7~9 controller + 位 10~12 flash mode …）

| 位置 | 名稱 | 範例 | 意義 |
|------|------|------|------|
| 1 | 固定碼 | `D` | Disk |
| 2 | 產品系列分類 | `E` | C=Customized / E=Embedded / G=EverGreen / H=H series(iSLC) / R=InnoRobust / S=Server&Edge / T=InnoAGE / U=InnoOSR / V=InnoREC |
| 3~5 | 產品種類 | `S25` | S25=SATA SSD 2.5" / S18=SATA SSD 1.8" / P25=PATA 2.5" / P18=PATA 1.8" / MLM=Slim SSD / F35=Fire Shield SSD 3.5" / CFA=CFast / CFS=CF-SATA / CFC=CF / CFX=CFexpress / SLM=SATA Slim / MSR=mSATA regular / MSM=mSATA mini |
| 6 | Capacity | — | 01G=1GB / 02G=2GB / … / 01T=1TB / 02T=2TB … |
| 7~9 | Controller | `A28` | 主控代碼（Alcor / SMI / JMicron / Hyperstone / ACard …） |
| 10~12 | Flash Mode | `D61` | iSLC / 3D TLC 層數 / 廠牌 |
| 13 | Temp. | `C` | C=Commercial(0~70°) / E=Extended / W=Industrial(-40~85°) / K,T=Coating |
| 14 | PCB Ver. | `C` | |
| 15 | Channel | `A` | S=Single / D=Dual / Q=Quad / E=Eight / H=16ch |
| 16 | Flash Vendor | `E` | Kioxia / Toshiba / Micron / Samsung / YMTC / Sandisk … |
| 17 | Customized | `S` | |

> 完整 controller / flash mode 對照表很長，需要時再展開（見 EM 命名規則表 `主類碼` 工作表）。
