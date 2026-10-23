import json, re

d = json.load(open('data/data.json', encoding='utf-8'))
hitachi_idx = d['cos'].index('Hitachi')
cgi_idx = d['cos'].index('CGI')

def parse_exp_strict(e):
    if not e: return 0
    e = str(e).strip().lower()
    if re.match(r'^(fresher|0|na|nil)$', e): return 0
    m = re.search(r'(\d+)\s*month', e)
    months_only = m and not re.search(r'year', e)
    if months_only: return int(m.group(1)) / 12
    m2 = re.search(r'(\d+)\s*year', e)
    if m2:
        y = int(m2.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        return y + (int(mm.group(1))/12 if mm else 0)
    m3 = re.search(r'(\d+(?:\.\d+)?)\s*(yr|yrs)', e)
    if m3: return float(m3.group(1))
    m4 = re.match(r'^(\d+(?:\.\d+)?)$', e)
    if m4: return float(m4.group(1))
    nums = re.findall(r'\d+(?:\.\d+)?', e)
    for n in nums:
        v = float(n)
        if 0 <= v <= 50: return v
    return 0

print('=== HITACHI VERIFICATION ===')
issues = []
for j in d['jds']:
    if j['c'] != hitachi_idx: continue
    rows = [(r[1], r[2], r[3]) for r in d['pl'] if r[0] == j['id']]
    rows.sort(key=lambda x: -x[1])
    cnt = len(rows)
    top3 = [d['people'][r[0]]['n'] for r in rows[:3]]
    print(f"{j['t']}: {cnt} candidates | top: {top3}")
    for pid, sc, rs in rows:
        p = d['people'][pid]
        exp = parse_exp_strict(p.get('e',''))
        vi = any(x in str(p.get('dt','')).lower() for x in ['visual','blind','visually','low vis'])
        if exp <= 1:
            issues.append(f'EXP VIOLATION: JD={j["t"]} {p["n"]} exp={p.get("e","")} parsed={exp:.2f}yr')
        if vi:
            issues.append(f'VI VIOLATION: JD={j["t"]} {p["n"]} dt={p.get("dt","")}')

print()
print('=== CGI VERIFICATION ===')
multi_jd_pids = {}
for j in d['jds']:
    if j['c'] != cgi_idx: continue
    rows = [(r[1], r[2], r[3]) for r in d['pl'] if r[0] == j['id']]
    print(f"{j['t']}: {len(rows)} candidates")
    for pid, sc, rs in rows:
        if pid not in multi_jd_pids: multi_jd_pids[pid] = []
        multi_jd_pids[pid].append(j['t'])

multi = {pid: jds for pid, jds in multi_jd_pids.items() if len(jds) > 1}
print(f"Candidates in multiple CGI JDs: {len(multi)}")

print()
if issues:
    print(f'VIOLATIONS FOUND ({len(issues)}):')
    for iss in issues[:10]: print(' ', iss)
else:
    print('NO VIOLATIONS - All hard rules satisfied!')
