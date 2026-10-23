"""
final_audit.py — Complete experience gate verification across all JDs
"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('data/data.json', encoding='utf-8'))
ppl = d['people']

def parse_cand_exp(e):
    if not e: return 0.0
    e = str(e).strip().lower()
    if re.match(r'^(fresher|0|na|nil|no exp|none|n/a)$', e): return 0.0
    m = re.search(r'(\d+)\s*month', e)
    if m and not re.search(r'year|yr', e):
        return int(m.group(1)) / 12
    m2 = re.search(r'(\d+)\s*(?:year|yr)', e)
    if m2:
        y = int(m2.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        return y + (int(mm.group(1)) / 12 if mm else 0)
    nums = re.findall(r'\d+(?:\.\d+)?', e)
    for n in nums:
        v = float(n)
        if 0 <= v <= 50: return v
    return 0.0

def parse_jd_min_exp(e):
    if not e: return None
    e_low = str(e).strip().lower()
    skip = ['freshers and experienced', 'fresh graduates only', 'open to freshers',
            'internship', 'btech student', 'any graduate', 'final year', 'immediate joiner',
            'fresher or experienced']
    if any(p in e_low for p in skip): return 0.0
    if re.match(r'^fresher', e_low): return 0.0
    mt = re.search(r'more than\s+(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if mt: return float(mt.group(1))
    rng = re.search(r'(\d+(?:\.\d+)?)\s*[–\-]\s*\d+(?:\.\d+)?\s*(?:year|yr)', e_low)
    if rng: return float(rng.group(1))
    plus = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*(?:year|yr)', e_low)
    if plus: return float(plus.group(1))
    bare = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if bare: return float(bare.group(1))
    return None

by_jd = {}
for row in d['pl']:
    jid, pid, sc, rs = row[0], row[1], row[2], row[3]
    if jid not in by_jd: by_jd[jid] = []
    by_jd[jid].append(pid)

hitachi_idx = d['cos'].index('Hitachi')
cgi_idx = d['cos'].index('CGI')

all_violations = []
jd_results = []

for j in d['jds']:
    jid = j['id']
    co = d['cos'][j['c']]
    title = j['t']
    e_raw = j.get('e', '')
    min_exp = parse_jd_min_exp(e_raw)
    rows = by_jd.get(jid, [])

    if not rows:
        continue

    # Also enforce Hitachi-specific >1yr rule
    if j['c'] == hitachi_idx and (min_exp is None or min_exp < 1.0):
        min_exp = 1.0

    violations = []
    for pid in rows:
        p = ppl[pid]
        cand_exp = parse_cand_exp(p.get('e', ''))
        if min_exp and cand_exp < min_exp:
            violations.append((p['n'], p.get('e', '?'), cand_exp))

    if violations:
        all_violations.extend(violations)
        jd_results.append((co, title, min_exp, e_raw, violations, len(rows)))
        print(f"FAIL [{co}] {title[:50]} | min={min_exp:.1f}yr | {len(violations)}/{len(rows)} violations")
        for name, raw, parsed in violations[:3]:
            print(f"       - {name}: '{raw}' => {parsed:.2f}yr")
    else:
        exp_vals = [parse_cand_exp(ppl[pid].get('e','')) for pid in rows]
        min_c = min(exp_vals)
        max_c = max(exp_vals)
        jd_results.append((co, title, min_exp, e_raw, [], len(rows)))

print()
print("=" * 70)
print(f"TOTAL VIOLATIONS: {len(all_violations)}")
if not all_violations:
    print("ALL CLEAN - Experience gate is 100% enforced across all JDs!")
else:
    print(f"STILL {len(jd_results)} JDs with violations — need another fix pass")
print("=" * 70)

# Summary by company
print("\nSUMMARY BY COMPANY:")
company_counts = {}
for co, title, min_exp, e_raw, viols, total in jd_results:
    if co not in company_counts:
        company_counts[co] = {'jds': 0, 'violations': 0, 'total_cands': 0}
    company_counts[co]['jds'] += 1
    company_counts[co]['violations'] += len(viols)
    company_counts[co]['total_cands'] += total

for co, stats in sorted(company_counts.items()):
    status = "CLEAN" if stats['violations'] == 0 else f"{stats['violations']} VIOLATIONS"
    print(f"  {co:<35} {stats['jds']} JDs, {stats['total_cands']} cands => {status}")
