"""Diagnose EV3F-ZSM1-RXCF-41 parse failure."""
import sys, traceback
sys.path.insert(0, r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\parser')
import rule_extractor, schema_builder

PDF = r'D:\管理\Solution Architect\Camera\1.0 Datasheet\4.0 GMSL2\EV3F-ZSM1-RXCF-41_Datasheet_2025_Q4.pdf'

print("=== Step 1: rule_extractor.extract ===")
try:
    raw = rule_extractor.extract(PDF)
    print(f"OK  part_no={raw['part_no']}  conf={raw['_confidence']}")
    cam = raw.get('camera_spec', {})
    print(f"    iface={cam.get('interface_bus')}  res={cam.get('resolution_mp')}  fps={cam.get('fps')}")
except Exception:
    traceback.print_exc()
    sys.exit(1)

print("\n=== Step 2: schema_builder.build_record ===")
try:
    rec = schema_builder.build_record(PDF, raw)
    print(f"OK  part_no={rec['meta']['part_no']}  product_line={rec['meta']['product_line']}")
except Exception:
    traceback.print_exc()
