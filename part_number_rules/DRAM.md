# DRAM Module 料號編碼原則

對應 product_line：`dram` ｜ bu_owner：`DRAM`

> DDR5 / DDR4 / SO-DIMM / DIMM 等
> **來源**：官方《DRAM_Product Naming Rule_26-05-28.xlsx》工作表 `Module`。
> ⚠️ 目前 pipeline 尚未設定 DRAM datasheet 資料夾；本檔先作為參考文件。

## 已確認規則

| 料號前綴 / 樣式 | product_line | bu_owner | platform_brand | 說明 |
|----------------|--------------|----------|----------------|------|
| 第 1 碼 `0~5` 或 `iDIMM` | dram | DRAM | （無） | 第 1 碼 = 記憶體世代（0=SDRAM…5=DDR5） |

> **核心判斷**：第 1 碼為記憶體世代碼（`0`SDRAM / `1`DDR1 / `2`DDR2 / `3`DDR3 / `4`DDR4 / `5`DDR5；或 `iDIMM`）。

## 料號逐碼意義（Module）

| 位置 | 名稱 | 意義 |
|------|------|------|
| 1 | Module（記憶體世代） | iDIMM / 0=SDRAM / 1=DDR1 / 2=DDR2 / 3=DDR3 / 4=DDR4 / 5=DDR5 |
| 2 | Memory Type（DIMM 型式） | A=FB-DIMM(Apple) / B=32bit Unbuffered SO-DIMM / C=ECC Unbuffered DIMM / D=ECC Unbuffered SO-DIMM / E=Fully Buffer DIMM / L=LR-DIMM / M=Mini DIMM / R=Registered DIMM / S=Unbuffered SO-DIMM / U=Unbuffered DIMM …（完整見原表） |
| 3 | DIMM Type / IC Data Rate | SDR / DDR / DDR2 / DDR3 各速率碼 |
| 4 | IC Data Rate | 同上速率分級 |
| 6~7 | DIMM Density | 08=8MB / 1G=1GB / 2G=2GB / 4G=4GB / 8G=8GB / AG=16GB / BG=32GB / CG=64GB … |
| 8 | IC Brand | A=Elpida / G=Samsung(ST) / H=Hynix / M=Micron / N=Nanya / S=Samsung / T=CXMT … |
| 9 | IC Config. | 16Mx16 / 32Mx16 / 64Mx8 / 8Gbx4 … |
| 10 | PCB SN | |
| 11 | Grade | A=Wide Temp.-40~105°(Tc) / C=Comm. / W=Wide Temp.-40~85° / M=Military …（含寬溫 / 低電壓 / coating 變化） |
| 12 | DIMM Datarate | PC100 / PC133 / DDR266 … |
| 13 | CL | CL2~CL18 |
| 15 | Die Version | |
| 16~17 | Reserve Code | B=Back / C=Coating / F=Front / T=Thermal Sensor |

> 其他工作表：`LPCAMM2`、`CXL`、`Actica` 另有專屬規則，需要時再展開。
