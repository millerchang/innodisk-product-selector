import json

with open('../output/spec_matrix.json', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 70)
print("Products with missing processor_model")
print("=" * 70)
nulls = [p for p in data if not p.get('computing_spec', {}).get('processor_model')]
for p in nulls:
    cs  = p.get('computing_spec', {})
    m   = p['meta']
    print("")
    print("  part_no   : {}".format(m['part_no']))
    print("  product   : {}".format(m.get('product_name', '')))
    print("  source    : {}".format(m.get('source_file', '')))
    print("  tdp       : {}".format(cs.get('tdp_watt')))
    print("  series    : {}".format(cs.get('processor_series')))
    print("  temp      : {} ~ {}".format(cs.get('op_temp_min_c'), cs.get('op_temp_max_c')))
    print("  lifecycle : {}".format(p.get('common', {}).get('lifecycle_status')))

print("")
print("=" * 70)
print("Also: model extracted but wrong")
print("=" * 70)
weird = [p for p in data
         if p.get('computing_spec', {}).get('processor_model')
         and p.get('computing_spec', {}).get('cpu_cores') is None]
for p in weird:
    cs = p.get('computing_spec', {})
    print("  {:20s}  model={}".format(p['meta']['part_no'], cs.get('processor_model')))
