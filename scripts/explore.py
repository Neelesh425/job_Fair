import json
d = json.load(open('data/data.json'))

print('=== Companies ===')
for i, c in enumerate(d['cos']):
    print(f"  {i}: {c}")

print('\n=== All JDs ===')
for j in d['jds']:
    print(f"  JD {j['id']:3d} | Co={d['cos'][j['c']]:30s} | {j['t']:50s} | type={j['ty']:12s} | exp={j['e']:40s} | loc={j['l']}")

print('\n=== Sample people with disability info ===')
for p in d['people'][:10]:
    print(f"  {p['n']:30s} | dt={p.get('dt',''):30s} | dp={p.get('dp',''):8s} | exp={p['e']:40s} | loc={p['loc']}")

# Check how many people have disability info
dt_count = sum(1 for p in d['people'] if p.get('dt'))
dp_count = sum(1 for p in d['people'] if p.get('dp'))
print(f"\nPeople with disability type: {dt_count}/{len(d['people'])}")
print(f"People with disability %: {dp_count}/{len(d['people'])}")

# Check candidates in multiple JDs
from collections import Counter
person_jds = {}
for pl in d['pl']:
    jid, pid = pl[0], pl[1]
    key = pid
    if key not in person_jds:
        person_jds[key] = []
    person_jds[key].append(jid)
multi = {k: v for k, v in person_jds.items() if len(set(v)) > 1}
print(f"\nCandidates matching multiple JDs: {len(multi)}")
for pid, jids in list(multi.items())[:5]:
    p = d['people'][pid]
    print(f"  {p['n']} -> JDs: {[d['jds'][j]['t'][:40] for j in set(jids)]}")
