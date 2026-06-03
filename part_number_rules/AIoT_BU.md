# AIoT BU — Intel / NXP 系統板 料號編碼原則

對應 product_line：`computing_aiot` ｜ bu_owner：`AIoT`

> ABOX / ASBC / ASOM / AXMB / AIPC / APPC / ARAK / APEX / APAC；資料夾 `AIoT\1.Datasheet`
> **來源**：官方《AIOT_Naming Rule_2024-05-16.xlsx》（各 series 一個工作表）。

## 已確認規則（依官方 AIOT 命名規則）

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `ABOX-` | computing_aiot | AIoT | Intel / NXP | Box PC（盒型工業電腦） |
| `ASBC-` | computing_aiot | AIoT | Intel / NXP | SBC 單板電腦 |
| `ASOM-` | computing_aiot | AIoT | Intel / NXP | SOM 模組 |
| `AXMB-` | computing_aiot | AIoT | Intel / NXP | Industrial Motherboard 工業主機板 |
| `AIPC-` | computing_aiot | AIoT | Intel / NXP | Industrial PC |
| `APPC-` | computing_aiot | AIoT | Intel / NXP | Panel PC |
| `ARAK-` | computing_aiot | AIoT | Intel / NXP | Rackmount Barebone / System |
| `APEX-` | computing_aiot | AIoT | Intel / NXP | AI Solution Barebone / System（注意：責任歸屬 IPA BU，但放 AIoT 資料夾） |
| `APAC-` | computing_aiot | AIoT | Intel / NXP | Peripheral & Accessory Card |

> **核心判斷**：第 1 碼 `A` = AIoT BU；第 2~4 碼為 series 代碼（BOX/SBC/SOM/XMB/IPC/PPC/RAK/PEX/PAC）。
> platform_brand（Intel vs NXP）**無法由料號判斷**，需看 datasheet 內容（CPU 型號）。
> ⚠️ APEX 系列責任歸屬為 IPA BU；若要區分，需在 catalog 另行標記。

## 料號逐碼意義（共 13 碼）

樣式：`A S S S - F M M M - V V V`（範例 `ABOX-S000-A00`）

| 位置 | 名稱 | 範例 | 意義 |
|------|------|------|------|
| 1 | BU | `A` | AIoT 事業群 |
| 2~4 | Series name | `BOX` | 產品系列（見下表） |
| 5 | `-` | | 分隔 |
| 6 | Family | `S` | 子分類 / 外型（依 series 不同，見下表） |
| 7~9 | model name | `000` | 機種編號 `0~Z` |
| 10 | `-` | | 分隔 |
| 11 | Version | `A` | 版次 `A~Z` |
| 12~13 | Variation | `00` | 流水碼 `00~99` |

### 第 6 碼 Family（依 series 不同）
| Series | 第 6 碼選項 |
|--------|------------|
| `ASBC`（SBC） | 1=1.8" Femto-ITX / 2=2.5" Pico-ITX / 3=3.5" SBC / 4=4" EPIC / U=非標準 / D=ODM；`00`=no CPU |
| `ASOM`（SOM） | 1=Type10 / 2=Type6 Compact / 3=Type6 Basic / 4=Type7 / 5=COM-HPC / 6=SMARC / 7=Q7 / D=ODM |
| `ABOX`（Box PC） | 0~9=Fanless System / A~Z=Special Vertical / D=ODM |
| `AXMB`（Motherboard） | 1=mini-ITX / 3=micro-ATX / 5=ATX / 7=EATX / 9=Server Board / U=非標準 / D=ODM |
| `AIPC`（Industrial PC） | 2=mini-ITX chassis / 4=micro-ATX / 6=ATX / 8=EATX / D=ODM System |
| `APPC`（Panel PC） | D=ODM System |
| `ARAK`/`APEX` | 1~4=1U~4U Barebone/System / 9=Tower / C=Chassis / D=ODM / E/P/S/X=效能分級 |
| `APAC`（Accessory） | 第 4 碼即 model，無 Family 欄（型式 `APAC-0000-A00`） |

> platform_brand 仍需由 datasheet CPU 型號判定（Intel Core/Atom/Celeron vs NXP i.MX）。
