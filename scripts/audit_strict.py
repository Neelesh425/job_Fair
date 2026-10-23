import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('data/data.json', encoding='utf-8'))

def parse_exp(e):
    if not e: return 0
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
    return 0

def is_vi(p):
    return any(x in str(p.get('dt','')).lower() for x in ['visual','blind','visually impaired','low vis'])

hitachi_idx = d['cos'].index('Hitachi')
cgi_idx = d['cos'].index('CGI')
ppl = d['people']

by_jd = {}
for row in d['pl']:
    jid, pid, sc, rs = row[0], row[1], row[2], row[3]
    if jid not in by_jd: by_jd[jid] = []
    by_jd[jid].append((pid, sc, rs))

# Only audit the key companies: CGI and Hitachi (the ones with strict rules)
print("=" * 70)
print("STRICT RULE AUDIT: CGI and Hitachi")
print("=" * 70)

hard_violations = []

for jd in d['jds']:
    jid = jd['id']
    co_idx = jd['c']
    co = d['cos'][co_idx]
    title = jd['t']
    rows = sorted(by_jd.get(jid, []), key=lambda x: -x[1])

    if co_idx not in (hitachi_idx, cgi_idx):
        continue

    is_hitachi = co_idx == hitachi_idx
    is_cgi = co_idx == cgi_idx

    # Determine if this is a Non-IT Hitachi JD
    nonit_hitachi_jds = ['finance', 'human resources', 'hr', 'procurement']
    title_l = title.lower()
    is_hitachi_nonit = is_hitachi and any(k in title_l for k in nonit_hitachi_jds)
    is_hitachi_it = is_hitachi and not is_hitachi_nonit

    print(f"\n--- [{co}] {title} ({len(rows)} candidates) ---")

    jd_issues = []
    sample = []

    for pid, sc, rs in rows:
        p = ppl[pid]
        exp = parse_exp(p.get('e', ''))
        vi = is_vi(p)
        sk = str(p.get('sk', '')).lower()
        role = str(p.get('role', '')).lower()

        issues_for_cand = []

        # --- HITACHI HARD RULES ---
        if is_hitachi:
            # Exp must be > 1 year
            if exp <= 1.0:
                issues_for_cand.append(f"EXP {exp:.2f}yr <= 1yr required")
            # No visual impairment
            if vi:
                issues_for_cand.append(f"VI EXCLUDED ({p.get('dt', '')})")

        # --- HITACHI NON-IT JD: Must not be pure IT developer ---
        if is_hitachi_nonit:
            pure_dev_keywords = ['java developer','full stack','software developer','python developer',
                                  '.net developer','dotnet','react developer','angular','node js',
                                  'devops','cloud engineer','data engineer','mobile developer',
                                  'android developer','ios developer']
            if any(k in sk or k in role for k in pure_dev_keywords):
                issues_for_cand.append(f"IT Developer in Non-IT JD (role: {p.get('role','?')[:40]})")

        # --- HITACHI IT JD: Must not be non-IT domain ---
        if is_hitachi_it:
            pure_nonit_keywords = ['chartered accountant','ca final','cost accountant','cma',
                                    'accounts payable','accounts receivable','procurement manager',
                                    'purchase manager','supply chain manager','hr manager','hr executive',
                                    'hr recruiter','human resource manager']
            if any(k in sk or k in role for k in pure_nonit_keywords):
                issues_for_cand.append(f"Non-IT candidate in IT JD (role: {p.get('role','?')[:40]})")

        # --- CGI HARD RULES ---
        if is_cgi:
            # Must be fresher (0-6 months)
            if exp > 0.5:
                issues_for_cand.append(f"EXP {exp:.2f}yr > 6months allowed for CGI fresher")

        if issues_for_cand:
            jd_issues.append((p['n'], p.get('e','?'), p.get('role','?'), issues_for_cand))
            hard_violations.append(f"[{co}:{title}] {p['n']}: {', '.join(issues_for_cand)}")
        else:
            sample.append(f"{p['n']} ({p.get('e','?')} exp)")

    if jd_issues:
        print(f"  *** {len(jd_issues)} VIOLATIONS ***")
        for name, exp_raw, role, issues_list in jd_issues[:10]:
            print(f"  FAIL: {name} | exp='{exp_raw}' | role='{role[:40]}' | {'; '.join(issues_list)}")
        if len(jd_issues) > 10:
            print(f"  ... and {len(jd_issues)-10} more violations")
    else:
        print(f"  CLEAN - no violations")
        print(f"  Sample: {', '.join(sample[:5])}")

print()
print("=" * 70)
print(f"TOTAL HARD VIOLATIONS: {len(hard_violations)}")
if not hard_violations:
    print("ALL CLEAN - CGI and Hitachi matching is correct!")
else:
    print("VIOLATIONS:")
    for v in hard_violations:
        print(f"  {v}")
print("=" * 70)
