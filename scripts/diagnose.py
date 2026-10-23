"""
diagnose.py - Find exactly what's wrong across all JDs
"""
import json, re

d = json.load(open('data/data.json', encoding='utf-8'))

def parse_exp(e):
    if not e: return 0
    e = str(e).strip().lower()
    if e in ['fresher','freshers','0','']: return 0
    m = re.search(r'(\d+)\s*year', e)
    if m:
        y = int(m.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        return y + (int(mm.group(1)) if mm else 0) / 12
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:yr|yrs)', e)
    if m: return float(m.group(1))
    m = re.search(r'^(\d+(?:\.\d+)?)$', e)
    if m: return float(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)', e)
    if m:
        v = float(m.group(1))
        return v if v <= 50 else 0
    return 0

def is_vi(p):
    dt = str(p.get('dt', '')).lower()
    return any(x in dt for x in ['visual', 'blind', 'visually', 'low vision', 'low visi'])

hitachi_co_idx = d['cos'].index('Hitachi')
cgi_co_idx = d['cos'].index('CGI')

hitachi_jds = {j['id']: j['t'] for j in d['jds'] if j['c'] == hitachi_co_idx}
cgi_jds = {j['id']: j['t'] for j in d['jds'] if j['c'] == cgi_co_idx}

print('=== HITACHI JD ANALYSIS ===')
print()

for jid, jt in sorted(hitachi_jds.items()):
    rows = sorted([(row[1], row[2], row[3]) for row in d['pl'] if row[0] == jid], key=lambda x: -x[1])
    print(f'--- {jt} (JD {jid}): {len(rows)} candidates ---')
    
    # Check for visual impairment violations
    vi_violations = []
    exp_violations = []
    skill_mismatches = []
    
    for pid, sc, rs in rows:
        p = d['people'][pid]
        
        if is_vi(p):
            vi_violations.append((pid, p['n'], p.get('dt',''), sc))
        
        exp = parse_exp(p.get('e',''))
        if exp <= 1:
            exp_violations.append((pid, p['n'], p.get('e',''), exp, sc))
    
    if vi_violations:
        print(f'  !! VISUAL IMPAIRMENT VIOLATIONS ({len(vi_violations)}):')
        for pid, nm, dt, sc in vi_violations[:5]:
            print(f'     PID={pid} {nm} | DT={dt} | Score={sc}')
    
    if exp_violations:
        print(f'  !! EXPERIENCE VIOLATIONS (exp<=1yr) ({len(exp_violations)}):')
        for pid, nm, exp_raw, exp, sc in exp_violations[:5]:
            print(f'     PID={pid} {nm} | Exp={exp_raw} ({exp:.1f}yr) | Score={sc}')
    
    print(f'  Top 5 by score:')
    for pid, sc, rs in rows[:5]:
        p = d['people'][pid]
        print(f'    PID={pid} Score={sc} {p["n"]} | Exp={p.get("e","")[:20]} | SK={p.get("sk","")[:60]}')
    print()

print()
print('=== CGI JD ANALYSIS ===')
for jid, jt in sorted(cgi_jds.items()):
    rows = sorted([(row[1], row[2], row[3]) for row in d['pl'] if row[0] == jid], key=lambda x: -x[1])
    
    # Count unique PIDs in all CGI JDs
    all_cgi_pids = set()
    for j_id in cgi_jds:
        for row in d['pl']:
            if row[0] == j_id:
                all_cgi_pids.add(row[1])
    
    # Count how many PIDs appear in multiple CGI JDs
    pid_to_jds = {}
    for j_id in cgi_jds:
        for row in d['pl']:
            if row[0] == j_id:
                if row[1] not in pid_to_jds:
                    pid_to_jds[row[1]] = []
                pid_to_jds[row[1]].append(j_id)
    
    multi_jd = {pid: jds for pid, jds in pid_to_jds.items() if len(jds) > 1}
    print(f'{jt} (JD {jid}): {len(rows)} candidates')
    print(f'  Candidates in multiple CGI JDs: {len(multi_jd)}')
    print(f'  Top 5:')
    for pid, sc, rs in rows[:5]:
        p = d['people'][pid]
        print(f'    Score={sc} {p["n"]} | SK={p.get("sk","")[:60]} | Reason={rs[:60]}')
    print()
