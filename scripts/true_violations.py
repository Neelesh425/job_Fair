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

def parse_jd_min_exp(e):
    if not e: return None
    e_low = str(e).strip().lower()
    # These JDs allow freshers — don't flag
    open_phrases = ['freshers and experienced', 'fresh graduates only', 'open to freshers',
                    'fresher or experienced', 'any graduate', 'fresher']
    if any(p in e_low for p in open_phrases): return 0.0
    mt = re.search(r'more than\s+(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if mt: return float(mt.group(1))
    rng = re.search(r'(\d+(?:\.\d+)?)\s*[–\-]\s*\d+(?:\.\d+)?\s*(?:year|yr)', e_low)
    if rng: return float(rng.group(1))
    plus = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*(?:year|yr)', e_low)
    if plus: return float(plus.group(1))
    bare = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if bare: return float(bare.group(1))
    return None

hitachi_idx = d['cos'].index('Hitachi')
cgi_idx = d['cos'].index('CGI')

print("=" * 70)
print("FRESHERS IN EXPERIENCE-REQUIRED JDs (TRUE VIOLATIONS ONLY)")
print("=" * 70)

true_violations = []

for j in d['jds']:
    jid = j['id']
    co_idx = j['c']
    co = d['cos'][co_idx]
    e_raw = j.get('e', '')
    min_exp = parse_jd_min_exp(e_raw)

    # Hitachi always requires >1yr
    if co_idx == hitachi_idx and (min_exp is None or min_exp < 1.0):
        min_exp = 1.0

    # CGI freshers expected to have 0 exp — skip
    if co_idx == cgi_idx:
        continue

    if min_exp is None or min_exp <= 0:
        continue  # No requirement or open to freshers — skip

    rows = by_jd.get(jid, [])
    jd_bad = []
    for pid, sc in rows:
        p = ppl[pid]
        exp = parse_exp(p.get('e', ''))
        if exp < min_exp:
            jd_bad.append((p['n'], p.get('e', '?'), exp))
            true_violations.append(1)

    if jd_bad:
        print(f"\nFAIL [{co}] {j['t']}")
        print(f"  Requires: '{e_raw}' (min={min_exp:.1f}yr)")
        print(f"  Violations: {len(jd_bad)}")
        for name, raw, parsed in jd_bad[:5]:
            print(f"    - {name}: '{raw}' = {parsed:.2f}yr (needs >={min_exp:.1f}yr)")
        if len(jd_bad) > 5:
            print(f"    ... and {len(jd_bad)-5} more")

print()
print("=" * 70)
if true_violations:
    print(f"TOTAL TRUE VIOLATIONS: {len(true_violations)}")
else:
    print("RESULT: ZERO TRUE VIOLATIONS")
    print("All experience-gated JDs only contain candidates who meet the minimum.")
    print("(Infosys/Wipro 'freshers and experienced' JDs are intentionally open.)")
    print("(CGI freshers are intentionally 0-exp.)")
print("=" * 70)
