import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('data/data.json', encoding='utf-8'))
ppl = d['people']
by_jd = {}
for row in d['pl']:
    jid, pid, sc = row[0], row[1], row[2]
    if jid not in by_jd: by_jd[jid] = []
    by_jd[jid].append((pid, sc))

def parse_exp(e):
    if not e: return 0.0
    e = str(e).strip().lower()
    if re.match(r'^(fresher|0|na|nil|no exp|none)$', e): return 0.0
    m = re.search(r'(\d+)\s*month', e)
    if m and not re.search(r'year|yr', e): return int(m.group(1)) / 12
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

targets = [
    ('SDE2 Fullstack CRM', 'GoHighLevel 3-5yr'),
    ('AI Engineer', 'Allstate 4yr'),
    ('Data Engineering', 'Dell 5-8yr'),
    ('Corporate Jobs for PwD', 'Indigo 4-6yr'),
    ('AI Fresher', 'CGI freshers only'),
    ('Java Developer', 'Hitachi >1yr'),
    ('Finance', 'Hitachi Finance >1yr'),
    ('Procurement', 'Hitachi Procurement >1yr'),
]

print("=" * 70)
print("SPOT CHECK — Real candidates in key JDs")
print("=" * 70)

for search_term, label in targets:
    for j in d['jds']:
        if search_term.lower() in j['t'].lower():
            co = d['cos'][j['c']]
            rows = sorted(by_jd.get(j['id'], []), key=lambda x: -x[1])
            if not rows:
                print(f"\n[{co}] {j['t'][:55]} — NO CANDIDATES")
                break
            exp_vals = [parse_exp(ppl[pid].get('e', '')) for pid, sc in rows]
            mn = min(exp_vals)
            mx = max(exp_vals)
            zeros = sum(1 for v in exp_vals if v < 0.1)
            lt1 = sum(1 for v in exp_vals if v < 1.0)
            print(f"\n[{co}] {j['t'][:55]}")
            print(f"  Expected: {label}")
            print(f"  JD says:  '{j.get('e', 'NOT SET')}'")
            print(f"  Candidates: {len(rows)} | Exp: {mn:.1f} - {mx:.1f} yr | Freshers(0): {zeros} | <1yr: {lt1}")
            if zeros > 0:
                print(f"  *** FRESHERS FOUND — potential issue ***")
            print(f"  Top 5 candidates:")
            for pid, sc in rows[:5]:
                p = ppl[pid]
                exp = parse_exp(p.get('e', ''))
                flag = " <-- FRESHER!" if exp < 0.1 else (" <-- LOW EXP!" if exp < 1.0 else "")
                print(f"    {p['n']:<35} exp='{p.get('e','?')[:25]}' ({exp:.1f}yr){flag}")
            break

print()
print("=" * 70)
# Final stat
total_freshers_in_exp_jds = 0
for j in d['jds']:
    e_raw = j.get('e', '')
    if not e_raw or 'fresher' in e_raw.lower(): continue
    rows = by_jd.get(j['id'], [])
    for pid, sc in rows:
        if parse_exp(ppl[pid].get('e', '')) < 0.1:
            total_freshers_in_exp_jds += 1
print(f"Total freshers (0 exp) found in non-fresher JDs: {total_freshers_in_exp_jds}")
print("=" * 70)
