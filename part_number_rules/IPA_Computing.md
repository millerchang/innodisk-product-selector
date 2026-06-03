# IPA BU — Computing 料號編碼原則

對應 product_line：`computing_ipa` ｜ bu_owner：`IPA`

> 涵蓋 Qualcomm 單主機板與 AMD-Xilinx FPGA。
> 資料夾：`IPA\EP\Computing`（Qualcomm 子資料夾、AMD 子資料夾）
> **來源**：官方《EP_Naming Rule_26-05-11.xls》工作表 `EP Namming`，Platform 區塊（第 47~62 列）。

## 已確認規則（依官方 EP 命名規則，2026-06 校正）

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `EX??-X??` | computing_ipa | IPA | AMD-Xilinx | 破折號後 MainChip 第 1 碼 = `X` → Xilinx FPGA |
| `EX??-Q??` | computing_ipa | IPA | Qualcomm | 破折號後 MainChip 第 1 碼 = `Q` → Qualcomm |
| `EXEC-Q911` | computing_ipa | IPA | Qualcomm | IQ-9075，EVK |
| `EXMP-Q911` | computing_ipa | IPA | Qualcomm | IQ-9075，SOM / COM-HPC Mini |
| `EXMU-X261` | computing_ipa | IPA | AMD-Xilinx | Kria K26，SOM |
| `EXOU-X261` | computing_ipa | IPA | AMD-Xilinx | Kria K26，BOX |

> **核心判斷**：料號為 `EX...`（第 1 碼 E、第 2 碼 X = Platform）即 `computing_ipa`；
> platform_brand 由破折號後 MainChip 第 1 碼決定（`X`=AMD-Xilinx、`Q`=Qualcomm）。

## 料號逐碼意義（Platform 區塊，共 17 碼）

樣式：`E X T F - M M M S - K K R - V V`（範例 `EXMU-X261-00A1-C1`）

| 位置 | 名稱 | 範例值 | 意義 |
|------|------|--------|------|
| 1 | Model | `E` | EP 事業群 |
| 2 | Product Line | `X` | **X = Platform（運算平台）→ computing_ipa** |
| 3 | Product Type | `M` | 產品型態（見下表） |
| 4 | Form Factor | `U` | 外型尺寸（見下表） |
| 5 | `-` | | 分隔 |
| 6~8 | MainChip | `X26` | **主晶片代碼（決定 platform_brand，見下表）** |
| 9 | Series | `1` | 系列 `1~9, A~Z` |
| 10 | （流水） | | `00~99, AA~ZZ` |
| 11 | `-` | | 分隔 |
| 12~13 | SKU | `00` | `A-Z` / `0-9` |
| 14~15 | Revision | `A1` | 版次 |
| 16 | `-` | | 分隔 |
| 17 | Version type | `C` | 工作溫度：`C`=0~70° / `S`=0~50° / `E`=-30~70° / `W`=-40~85° |

### 第 3 碼 Product Type（產品型態）
| 碼 | 意義 |
|----|------|
| `C` | Carrier（載板） |
| `E` | EVK（評估套件） |
| `F` | Fakra System |
| `M` | SOM（System on Module） |
| `N` | NVR / NAS |
| `O` | BOX（盒型系統） |
| `S` | SBC（單板電腦） |

### 第 4 碼 Form Factor（外型）
| 碼 | 意義 |
|----|------|
| `A` | 699pin Adapter Module |
| `B` | 2.5" Pico-ITX |
| `C` | 3.5" |
| `D` | 4" |
| `E` | Mini-ITX |
| `F` | Micro-ATX |
| `P` | COM-HPC Mini |
| `R` | COM-HPC Client |
| `S` | SMARC |
| `U` | Unstandard（非標準） |

### 第 6~8 碼 MainChip（主晶片 → platform_brand）
| 碼 | 晶片 | platform_brand |
|----|------|----------------|
| `X26` | Xilinx Kria K26 | AMD-Xilinx |
| `X24` | Xilinx Kria K24 | AMD-Xilinx |
| `XU3` | Xilinx Zynq UltraScale+ ZU3 | AMD-Xilinx |
| `XU4` | Xilinx Zynq UltraScale+ ZU4 | AMD-Xilinx |
| `XU5` | Xilinx Zynq UltraScale+ ZU5 | AMD-Xilinx |
| `Q30` | Qualcomm QCS5430 | Qualcomm |
| `Q60` | Qualcomm IQ-615 | Qualcomm |
| `Q80` | Qualcomm IQ-8275 | Qualcomm |
| `Q90` | Qualcomm QCS6490 | Qualcomm |
| `Q91` | Qualcomm IQ-9075（Dragonwing QCS9075） | Qualcomm |
| `QA0` | Qualcomm IQ10 | Qualcomm |
| `QX1` | Qualcomm IQ-X (Hamoa) | Qualcomm |

> 規則摘要：**第 1 碼 `X` → AMD-Xilinx；第 1 碼 `Q` → Qualcomm。**
