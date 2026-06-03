# Camera 相機模組 料號編碼原則

對應 product_line：`camera` ｜ bu_owner：`（無，相機 BU）`

> EV* 相機模組、EB* Capture Card；資料夾 `Camera\1.0 Datasheet`
> **來源**：官方《EP_Naming Rule_26-05-11.xls》工作表 `EP Namming`，Camera/Vision 區塊（第 29~44 列）。

## 已確認規則

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| `EV??` | camera | （無） | （無） | Vision 相機模組（第 2 碼 V = Vision） |
| `EI??` | camera | （無） | （無） | Image Sensor Board（第 2 碼 I = 影像感測板） |

> **核心判斷**：第 1 碼 `E` + 第 2 碼 ∈ {V, I} → `camera`。
> （現有 parser 另以 `EB*` 處理 Capture Card；EB 不在 EP 官方表內，沿用既有 catalog。）

## 料號逐碼意義（共 17 碼）

樣式：`E P R I - VS L S - SS C L - E V`（範例 `EV2U-SGM1-RTCF-11`）

| 位置 | 名稱 | 範例 | 意義 |
|------|------|------|------|
| 1 | Model | `E` | EP 事業群 |
| 2 | Product Line | `V` | **I=Image Sensor Board / V=Vision → camera** |
| 3 | Resolution | `2` | 0=<1M / 1=1M / 2=2M / 3=3M / 5=5M / 8=8M / D=13MP / K=20MP |
| 4 | Interface | `U` | A=AHD / C=MIPI over Type-C / E=GigE / F=FAKRA Cable / M=Mipi / S=USB3.0 / U=USB2.0 |
| 5 | `-` | | 分隔 |
| 6 | Mainchip Vendor | `S` | C=iCatch / G=Genesys Logic / I=SOI / L=SunplusIT / M=OmniVision / N=Nextchip / O=Onsemi / P=GeneralPlus / R=Realtek / S=Sonix / T=Techpoint / X=None / Z=Other |
| 7 | Sensor Vendor | `G` | G=GlaxyCore / I=SOI / M=OmniVision / O=Onsemi / P=Pixart / S=Sony |
| 8 | Lens Type | `M` | M=S-Mount M12 / N=S-Mount M5 / R=Other / S=CS-Mount |
| 9 | Series | `1` | `1~9, A~Z` |
| 10 | `-` | | 分隔 |
| 11 | Shutter Type | `R` | R=Rolling Shutter / G=Global Shutter |
| 12 | Sensor Feature | `T` | F=LFM / H=HDR / L=Low light(STARVIS) / N=Night Vision / S=Standard / T=H+L / X=H+L+F |
| 13 | Color | `C` | C=Color(RGB) / M=Mono |
| 14 | Lens Function | `F` | A=Auto Focus / F=Fixed Focus / N=Night Vision / O=Fisheye / V=Varifocal |
| 15 | `-` | | 分隔 |
| 16 | Enclosure | `1` | 1=Standard / 2=Enclosure / 3=IP67 |
| 17 | Version | `1` | 1=Standard / 2=DMIC |
