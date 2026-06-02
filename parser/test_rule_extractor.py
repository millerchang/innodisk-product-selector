"""
Quick test: run rule_extractor on 6 representative PDFs and print results.
No API key needed — purely local pdfplumber-based.
Run: python test_rule_extractor.py
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import rule_extractor

TEST_FILES = {
    "SBC (Intel Ultra)":      r"D:\管理\Solution Architect\AIoT\1.Datasheet\SBC\ASBC-3150\ASBC-3150_251003.pdf",
    "Box PC (Elkhart Lake)":  r"D:\管理\Solution Architect\AIoT\1.Datasheet\Box PC\ABOX-4020\ABOX-4020.pdf",
    "ABOX-4140 (Ultra short)":r"D:\管理\Solution Architect\AIoT\1.Datasheet\Box PC\ABOX-4140\ABOX-4140_251205.pdf",
    "APEX-E100 (Ultra HL)":   r"D:\管理\Solution Architect\AIoT\1.Datasheet\APEX series\APEX-E100\Datasheet_APEX-E100_20250814.pdf",
    "APEX-X100-Q (Qualcomm)": r"D:\管理\Solution Architect\AIoT\1.Datasheet\APEX series\APEX-X100-Q\Datasheet_APEX-X100-Q_20250903.pdf",
    "AXMB-D150 (Ultra 265H)": r"D:\管理\Solution Architect\AIoT\1.Datasheet\Industrial Board\AXMB-D150_Mini ITX\Datasheet_AXMB-D150_20251008.pdf",
    "IndBoard (13th Gen)":    r"D:\管理\Solution Architect\AIoT\1.Datasheet\Industrial Board\AXMB-1130\AXMB-1130_20250807.pdf",
    "NXP SBC":                r"D:\管理\Solution Architect\AIoT\1.Datasheet\SBC\ASBC-3M80\ASBC-3M80_251014.pdf",
}

DISPLAY_FIELDS = [
    "part_no", "product_name", "processor_model", "processor_series",
    "tdp_watt", "ai_tops", "ram_gb", "form_factor",
    "op_temp_min_c", "op_temp_max_c",
    "os_support", "connectivity", "display_outputs",
    "storage_interfaces", "certifications", "key_features",
    "_confidence", "_method",
]

for label, path in TEST_FILES.items():
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  {path.split(chr(92))[-1]}")
    print("=" * 60)
    result = rule_extractor.extract(path)
    for f in DISPLAY_FIELDS:
        val = result.get(f)
        if val is not None and val != [] and val != "":
            print(f"  {f:<22} {val}")
    conf = result.get("_confidence", 0)
    status = "✓ PASS" if conf >= 0.70 else "✗ NEEDS VISION"
    print(f"  {'':22} → {status} (confidence={conf:.0%})")
