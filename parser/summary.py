import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data = json.loads(Path(r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\output\spec_matrix.json").read_text(encoding="utf-8"))
print(f"Total records: {len(data)}\n")
print(f"{'Part No':<16} {'BU':<5} {'Platform':<8} {'CPU':<32} {'TOPS':<6} {'Temp':<14} {'OS'}")
print("-" * 105)
for r in sorted(data, key=lambda x: x["meta"]["part_no"]):
    m  = r["meta"]
    c  = r["computing_spec"]
    cm = r["common"]
    cpu   = (c.get("processor_model") or "?")[:30]
    tops  = c.get("ai_tops")
    tops_s = f"{tops}T" if tops else "-"
    t_min = cm.get("op_temp_min_c", "?")
    t_max = cm.get("op_temp_max_c", "?")
    temp  = f"{t_min}~{t_max}C"
    os_l  = ",".join(r["search"].get("searchable_tags", [])[:2])
    print(f"{m['part_no']:<16} {(m['bu_owner'] or '-'):<5} {c['platform_brand']:<8} {cpu:<32} {tops_s:<6} {temp:<14} {os_l}")

# Stats
methods = [json.loads(Path(r"D:\Claude\Miller_Workspace\Work\Innodisk_Product_Selector\output\parse_log.json").read_text())
           [i].get("method","?") for i in range(len(data))]
from collections import Counter
print(f"\nParser method breakdown: {dict(Counter(methods))}")
