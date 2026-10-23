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
            'internship', 'btech student', 'any graduate', 'final year', 'immediate joiner']
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

# Check DevSecOps specifically
for j in d['jds']:
    if 'DevSecOps' in j['t']:
        print('JD:', j['t'])
        print('Min exp raw:', j.get('e', ''))
        min_exp = parse_jd_min_exp(j.get('e', ''))
        print('Min exp parsed:', min_exp)
        rows = by_jd.get(j['id'], [])
        print('Candidates remaining:', len(rows))
        violations = 0
        for pid in rows:
            p = ppl[pid]
            exp = parse_cand_exp(p.get('e', ''))
            if min_exp and exp < min_exp:
                violations += 1
                if violations <= 5:
                    print(f"  STILL VIOLATION: {p['n']} | exp='{p.get('e','?')}' parsed={exp:.2f}yr")
        print(f'Remaining violations: {violations}')
        print()
