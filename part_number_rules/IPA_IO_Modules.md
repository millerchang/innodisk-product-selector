# IPA BU — I/O Modules 料號編碼原則

對應 product_line：`io` ｜ bu_owner：`IPA`

> 資料夾：`IPA\EP\IO Modules`
> **來源**：官方《EP_Naming Rule_26-05-11.xls》工作表 `EP Namming`，I/O 區塊（第 1~22 列）。

## 已確認規則

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `E2??` | io | IPA | （N/A） | 2.5" SSD 介面卡 |
| `E3??` | io | IPA | （N/A） | DDR3 DIMM |
| `ED??` | io | IPA | （N/A） | Dongle |
| `EG??` | io | IPA | （N/A） | NGFF / M.2 |
| `EH??` | io | IPA | （N/A） | mPCIe Half |
| `EL??` | io | IPA | （N/A） | PCIe Low profile |
| `EM??` | io | IPA | （N/A） | mPCIe |
| `ES??` | io | IPA | （N/A） | PCIe Standard |
| `EY??` | io | IPA | （N/A） | Daughterboard |
| `EZ??` | io | IPA | （N/A） | Others |

> **核心判斷**：第 1 碼 `E` + 第 2 碼 ∈ {2,3,D,G,H,L,M,S,Y,Z} → `io`。
> （第 2 碼 = `X` 為 Platform → computing_ipa；`V`/`I` 為 Camera。見各自規則檔。）
> I/O 模組無晶片平台屬性，platform_brand 留空。

## 料號逐碼意義（共 12 碼）

樣式：`E P I O - G N F S - V V`（範例 `EMSS-3201-C1`）

| 位置 | 名稱 | 範例 | 意義 |
|------|------|------|------|
| 1 | Model | `E` | EP 事業群 |
| 2 | Product Line / Form Factor | `M` | 介面外型（見下表） |
| 3 | Input signal | `S` | 輸入訊號（見訊號表） |
| 4 | Output signal | `S` | 輸出訊號（見訊號表） |
| 5 | `-` | | 分隔 |
| 6 | Gen for output | `3` | 0=Original / 1~3=Gen1~3 / X=Multi |
| 7 | Output items | `2` | 0~9=埠數量 / F=Fiber / I=IMU / L=LAN / N=Non-daughterboard(LAN) / P=PoE / R=RAID / S=isolate / W=WiFi |
| 8 | Feature | `0` | 0~9=normal |
| 9 | Series | `1` | `1~9, A~Z` |
| 10 | `-` | | 分隔 |
| 11 | Version type | `C` | C=Commercial(0~70°) / K=Coating(0~70°) / T=Coating(-40~85°) / W=Industrial(-40~85°) / V=Commercial p2p controller |
| 12 | Version | `1` | `1~9, A~Z` |

### 第 2 碼 Product Line / Form Factor
| 碼 | 意義 | 分類 |
|----|------|------|
| `2` | 2.5" SSD | io |
| `3` | DDR3 DIMM | io |
| `D` | Dongle | io |
| `G` | NGFF, M.2 | io |
| `H` | mPCIe Half | io |
| `L` | PCIe Low profile | io |
| `M` | mPCIe | io |
| `S` | PCIe Standard | io |
| `Y` | Daughterboard | io |
| `Z` | Others | io |
| `A`/`B`/`C`/`I`/`Q`/`T`/`V`/`X` | 參考專屬命名規則（Platform / Camera 等） | 非 io |

### 第 3、4 碼 訊號代碼（Input / Output signal）
`2`=Serial(232/422/485) / `4`=IDE/PATA / `A`=SAS / `B`=Bluetooth / `C`=CAN Bus / `D`=SD / `G`=GPS / `I`=GPIO/DIO / `L`=LAN / `N`=Networking / `P`=PCIe / `S`=SATA / `U`=USB / `V`=VGA/Display / `T`=Power/Voltage / `W`=Wifi / `X`=Multi / `Z`=Others
