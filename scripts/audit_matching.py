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
    return any(x in str(p.get('dt','')).lower() for x in ['visual','blind','visually impaired','low vis','colour blind','color blind'])

# Build JD lookup
jd_map = {j['id']: j for j in d['jds']}

# Build candidate lookup
ppl = d['people']

# Build placements per JD
by_jd = {}
for row in d['pl']:
    jid, pid, sc, rs = row[0], row[1], row[2], row[3]
    if jid not in by_jd:
        by_jd[jid] = []
    by_jd[jid].append((pid, sc, rs))

hitachi_idx = d['cos'].index('Hitachi')
cgi_idx = d['cos'].index('CGI')

issues = []
warnings = []

print("=" * 70)
print("COMPREHENSIVE CANDIDATE-JD MATCHING AUDIT")
print("=" * 70)

for jd in d['jds']:
    jid = jd['id']
    co = d['cos'][jd['c']]
    title = jd['t']
    rows = sorted(by_jd.get(jid, []), key=lambda x: -x[1])
    
    if not rows:
        continue
    
    is_hitachi = jd['c'] == hitachi_idx
    is_cgi = jd['c'] == cgi_idx
    
    # Determine domain from JD title
    it_jd_keywords = ['developer','engineer','programmer','software','java','net','dotnet','.net','python',
                       'fullstack','full stack','qa','tester','testing','devops','cloud','ai','ml',
                       'machine learning','data science','support','it support','cyber','network',
                       'agentic','generative','sap','erp','salesforce']
    nonit_jd_keywords = ['finance','account','procure','purchase','supply chain','hr','human resource',
                          'marketing','sales','analyst','legal','compliance','admin','operations']
    
    title_l = title.lower()
    jd_is_it = any(k in title_l for k in it_jd_keywords)
    jd_is_nonit = any(k in title_l for k in nonit_jd_keywords)
    
    # Fresher JDs (CGI)
    is_fresher_jd = is_cgi
    
    jd_issues = []
    
    for pid, sc, rs in rows[:20]:  # Check top 20 per JD
        p = ppl[pid]
        exp = parse_exp(p.get('e', ''))
        vi = is_vi(p)
        sk = str(p.get('sk', '')).lower()
        role = str(p.get('role', '')).lower()
        
        # Candidate domain detection
        it_cand_keywords = ['developer','engineer','programmer','software','java','.net','dotnet','python',
                             'fullstack','full stack','qa','tester','testing','devops','cloud','ai','ml',
                             'machine learning','data science','support','it','cyber','network']
        nonit_cand_keywords = ['finance','account','procure','purchase','supply chain','hr','human resource',
                                'marketing','sales','analyst','legal','compliance','admin']
        
        cand_is_it = any(k in sk or k in role for k in it_cand_keywords)
        cand_is_nonit = any(k in sk or k in role for k in nonit_cand_keywords)
        
        # Rule checks
        
        # 1. Hitachi: exp must be > 1 year
        if is_hitachi and exp <= 1.0:
            jd_issues.append(f"  ❌ EXP VIOLATION: {p['n']} exp={p.get('e','?')} parsed={exp:.2f}yr for Hitachi JD (needs >1yr)")
        
        # 2. Hitachi: no visual impairment
        if is_hitachi and vi:
            jd_issues.append(f"  ❌ VI VIOLATION: {p['n']} disability='{p.get('dt','')}' cannot be placed in Hitachi JD")
        
        # 3. CGI: must be fresher (≤6 months)
        if is_cgi and exp > 0.5:
            jd_issues.append(f"  ❌ CGI FRESHER VIOLATION: {p['n']} exp={p.get('e','?')} parsed={exp:.2f}yr (CGI requires 0-6mo)")
        
        # 4. Domain mismatch: IT candidate in Non-IT JD
        if jd_is_nonit and not jd_is_it and cand_is_it and not cand_is_nonit:
            jd_issues.append(f"  ⚠ DOMAIN MISMATCH: {p['n']} (IT: {p.get('role','?')}) in non-IT JD '{title}'")
        
        # 5. Domain mismatch: Non-IT candidate in IT JD
        if jd_is_it and not jd_is_nonit and cand_is_nonit and not cand_is_it:
            jd_issues.append(f"  ⚠ DOMAIN MISMATCH: {p['n']} (NonIT: {p.get('role','?')}) in IT JD '{title}'")
    
    if jd_issues:
        print(f"\n🔴 [{co}] {title} ({len(rows)} candidates)")
        for iss in jd_issues:
            print(iss)
            issues.append(iss)
    else:
        # Quick summary for clean JDs
        top3 = [ppl[r[0]]['n'] for r in rows[:3]]
        exp_vals = [parse_exp(ppl[r[0]].get('e','')) for r in rows[:5]]
        print(f"✅ [{co}] {title} | {len(rows)} cands | exp range: {min(exp_vals):.1f}-{max(exp_vals):.1f}yr | top: {top3}")

print()
print("=" * 70)
print(f"SUMMARY: {len(issues)} VIOLATIONS found")
if not issues:
    print("✅ ALL RULES SATISFIED - Candidate matching is clean!")
else:
    print(f"❌ {len(issues)} violations need to be fixed")
print("=" * 70)
