"""Test schema_builder.build_record() for a camera product."""
import sys, json
sys.path.insert(0, r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\parser')
import rule_extractor, schema_builder

PDF = r'D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\Camera\1.0 Datasheet\1.0 USB 2.0\EV2U-LOM1-RHCF_Datasheet_2026_Q1.pdf'

raw    = rule_extractor.extract(PDF)
record = schema_builder.build_record(PDF, raw)

print(json.dumps(record, indent=2, ensure_ascii=False))
