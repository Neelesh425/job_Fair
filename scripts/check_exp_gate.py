import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open('data/data.json', encoding='utf-8'))

def parse_exp(e):
    if not e: return None
    e = str(e).strip().lower()
    if re.match(r'^(fresher|0|na|nil|no exp|none)$', e): return 0
    m = re.search(r'(\d+)\s*month', e)
    months_only = m and not re.search(r'year|yr', e)
    if months_only: return int(m.group(1)) / 12
    m2 = re.search(r'(\d+)\s*(?:year|yr)', e)
    if m2:
        y = int(m2.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        return y + (int(mm.group(1))/12 if mm else 0)
    nums = re.findall(r'\d+(?:\.\d+)?', e)
    for n in nums:
        v = float(n)
        if 0 <= v <= 50: return v
    return None

print("=== ALL JD EXPERIENCE REQUIREMENTS ===")
jds_with_exp = []
jds_without_exp = []
for j in d['jds']:
    co = d['cos'][j['c']]
    e_raw = j.get('e', '')
    if e_raw:
        jds_with_exp.append((co, j['t'], e_raw))
        print(f"[{co}] {j['t'][:55]:55} => '{e_raw}'")
    else:
        jds_without_exp.append((co, j['t']))

print(f"\nJDs WITH exp requirement: {len(jds_with_exp)}")
print(f"JDs WITHOUT exp requirement: {len(jds_without_exp)}")

# Now check: for JDs that have a min exp, are freshers appearing?
print()
print("=== EXP GATE VIOLATIONS: Freshers in Experience-Required JDs ===")

by_jd = {}
for row in d['pl']:
    jid, pid, sc, rs = row[0], row[1], row[2], row[3]
    if jid not in by_jd: by_jd[jid] = []
    by_jd[jid].append((pid, sc, rs))

violations = []
for j in d['jds']:
    jid = j['id']
    co = d['cos'][j['c']]
    min_exp_raw = j.get('e', '')
    if not min_exp_raw:
        continue
    min_exp = parse_exp(min_exp_raw)
    if min_exp is None or min_exp <= 0:
        continue  # no meaningful minimum

    rows = sorted(by_jd.get(jid, []), key=lambda x: -x[1])
    for pid, sc, rs in rows:
        p = d['people'][pid]
        cand_exp = parse_exp(p.get('e', ''))
        if cand_exp is None: cand_exp = 0
        if cand_exp < min_exp:
            violations.append({
                'company': co, 'jd': j['t'], 'jd_min_exp': min_exp_raw,
                'candidate': p['n'], 'cand_exp_raw': p.get('e','?'),
                'cand_exp_parsed': cand_exp, 'jd_min_parsed': min_exp
            })

if violations:
    print(f"FOUND {len(violations)} VIOLATIONS:")
    for v in violations[:20]:
        print(f"  [{v['company']}] {v['jd'][:40]:40} "
              f"needs >={v['jd_min_parsed']:.1f}yr | "
              f"{v['candidate']} has {v['cand_exp_parsed']:.1f}yr (raw: '{v['cand_exp_raw']}')")
    if len(violations) > 20:
        print(f"  ... and {len(violations)-20} more")
else:
    print("NO VIOLATIONS - Experience gate is enforced correctly!")

print()
print("=== SAMPLE: What does 'e' field in a JD look like? ===")
for j in d['jds'][:3]:
    print(f"  JD id={j['id']} t='{j['t'][:40]}' e='{j.get('e','')}' keys={list(j.keys())}")
