import json

with open('../output/spec_matrix.json', encoding='utf-8') as f:
    data = json.load(f)

covered    = [p for p in data if p.get('computing_spec',{}).get('cpu_cores') is not None]
null_cores = [p for p in data if p.get('computing_spec',{}).get('cpu_cores') is None]

print("cpu_cores covered: {}/{}".format(len(covered), len(data)))
print()
print("--- Still NULL cpu_cores ---")
for p in null_cores:
    cs = p.get('computing_spec', {})
    model = cs.get('processor_model') or '(none)'
    tdp   = cs.get('tdp_watt')
    print("  {:20s}  model={:35s}  tdp={}".format(p['meta']['part_no'], model[:35], tdp))

print()
print("--- Sample covered ---")
for p in covered[:10]:
    cs    = p.get('computing_spec', {})
    total = cs['cpu_cores']
    p_c   = cs.get('cpu_p_cores', '?')
    e_c   = cs.get('cpu_e_cores', '?')
    m     = (cs.get('processor_model') or '').replace('®','').replace('™','')[:35]
    print("  {:20s}  {}C ({}/{}P+E)  {}".format(p['meta']['part_no'], total, p_c, e_c, m))
