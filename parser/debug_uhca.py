import sys
sys.path.insert(0, r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\parser')
import rule_extractor, schema_builder
from pathlib import Path

# Test the UHCA with trailing space in filename
pdf = r'D:\管理\Solution Architect\Camera\1.0 Datasheet\2.0 MIPI CSI-2\EV2M-OOM1-UHCA _Datasheet_2025_Q3.pdf'

# Show what the filename split gives
stem = Path(pdf).stem
print("stem:", repr(stem))
print("split:", repr(stem.split('_')))

raw = rule_extractor.extract(pdf)
print("part_no:", repr(raw['part_no']), " conf:", raw['_confidence'])

rec = schema_builder.build_record(pdf, raw)
print("product_line:", rec['meta']['product_line'])
print("cam iface:", rec['camera_spec']['interface_bus'])
