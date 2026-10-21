"""
TARGETED FIX for data.json: Cap green-zone scores for candidates whose
experience clearly doesn't match the JD requirement.

This does NOT re-score from scratch. It keeps the original ingest.py scores
but applies an experience gate: if a candidate's years of experience fall
outside the JD's required range, their score is capped at GREEN-1 (65).

This also correctly handles:
- "Fresher and experienced" JDs -> parse_exp_range returns None (no restriction)
- Overqualified candidates (e.g., 22yrs for 2-4yr role) -> penalized
- Underqualified candidates (e.g., 1yr for 4yr role) -> penalized
"""
import json, re, sys, io, shutil, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'data.json')
BACKUP_PATH = DATA_PATH + '.backup_original'

d = json.load(open(DATA_PATH, 'r', encoding='utf-8'))
GREEN, YELLOW = d['thr']  # 66, 52

# Save a backup of the truly original data
if not os.path.exists(BACKUP_PATH):
    shutil.copy2(DATA_PATH, BACKUP_PATH)
    print(f"Original backed up to {BACKUP_PATH}")

# --- experience parsing (mirrors ingest.py logic) ---
def parse_yrs(t):
    if not t:
        return None
    t = t.lower().strip()
    if 'fresh' in t or t.startswith('no exp') or t == '0':
        return 0
    ym = re.search(r'(\d+)\s*year', t)
    mm = re.search(r'(\d+)\s*month', t)
    if ym and mm:
        return round(int(ym.group(1)) + int(mm.group(1)) / 12, 1)
    v = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', t)[:2]]
    if not v or v[0] > 40:
        return None
    if 'month' in t and 'year' not in t and len(v) == 1:
        return round(v[0] / 12, 1)
    if len(v) == 2 and re.search(r'\d\s*(-|–|to)\s*\d', t):
        return sum(v) / 2
    return v[0]

def parse_exp_range(e, title=''):
    """Parse JD experience requirement string into (min, max) tuple.
    Returns None if no strict range can be determined."""
    if not e:
        e = ''
    e_lower = e.lower()
    title_lower = (title or '').lower()
    
    # "Fresher and experienced" or "Freshers and experienced" -> accepts both, no restriction
    if 'fresher' in e_lower and 'experience' in e_lower:
        return None
    # Just "Fresher" or title says fresher and no exp field
    if 'fresher' in e_lower or ('fresher' in title_lower and not e_lower.strip()):
        return (0, 1)
    # Range like "4-10 years"
    m = re.search(r'(\d+)\s*[–\-]\s*(\d+)', e_lower)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    # Open-ended like "8+ years"
    m = re.search(r'(\d+)\s*(\+|yr|year)', e_lower)
    if m:
        return (float(m.group(1)), None)
    return None


# --- Apply targeted corrections ---
changes = []
total_green_before = sum(1 for pl in d['pl'] if pl[2] >= GREEN)

for i, pl in enumerate(d['pl']):
    jid, pid, score, reason, is_pool = pl
    
    if score < GREEN:
        continue  # only fix green-zone candidates
    
    j = d['jds'][jid]
    p = d['people'][pid]
    
    rg = parse_exp_range(j['e'], j['t'])
    if rg is None:
        continue  # JD has no strict experience requirement
    
    y = parse_yrs(p['e'])
    if y is None:
        continue  # can't determine candidate experience, leave as-is
    
    lo, hi = rg
    # Check if candidate is WITHIN the acceptable range
    # Allow tolerance: up to 2 years above max is OK (original ingest logic)
    if hi is not None:
        in_range = y >= lo and y <= hi + 2
    else:
        in_range = y >= lo
    
    if in_range:
        continue  # candidate meets the requirement, score is fine
    
    # MISMATCH FOUND: candidate should NOT be green
    new_score = GREEN - 1  # cap at 65 (yellow zone)
    
    # Add experience mismatch note to reason
    if y < lo:
        mismatch_note = f'EXP MISMATCH: {y:g}yrs < required {lo:g}'
        if hi is not None:
            mismatch_note += f'-{hi:g}yrs'
    else:
        mismatch_note = f'EXP MISMATCH: {y:g}yrs > max {hi:g}+2yrs'
    
    new_reason = reason + '; ' + mismatch_note if reason else mismatch_note
    
    changes.append({
        'name': p['n'],
        'jd': j['t'][:50],
        'cand_exp': p.get('e', ''),
        'jd_exp': j.get('e', ''),
        'parsed_yrs': y,
        'jd_range': rg,
        'old_score': score,
        'new_score': new_score,
    })
    
    d['pl'][i] = [jid, pid, new_score, new_reason, is_pool]

# Re-sort placements
d['pl'].sort(key=lambda r: (r[0], -r[2]))

# Write corrected data
with open(DATA_PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

total_green_after = sum(1 for pl in d['pl'] if pl[2] >= GREEN)

print(f"\n{'='*60}")
print(f"TARGETED EXPERIENCE FIX RESULTS")
print(f"{'='*60}")
print(f"Total placements: {len(d['pl'])}")
print(f"Green BEFORE fix: {total_green_before}")
print(f"Green AFTER fix:  {total_green_after}")
print(f"Candidates moved out of green: {len(changes)}")
print()

print(f"=== ALL CORRECTIONS ({len(changes)}) ===")
for ch in sorted(changes, key=lambda x: x['old_score'], reverse=True):
    lo, hi = ch['jd_range']
    range_str = f"{lo:g}-{hi:g}" if hi else f"{lo:g}+"
    print(f"  {ch['name'][:30]:30s} | {ch['old_score']}->{ch['new_score']} | has {ch['parsed_yrs']:g}yrs, JD needs {range_str}yrs | JD: {ch['jd']}")

# Final verification
print(f"\n=== VERIFICATION ===")
remaining = 0
for pl in d['pl']:
    jid, pid, score, reason, is_pool = pl
    if score < GREEN:
        continue
    j = d['jds'][jid]
    p = d['people'][pid]
    rg = parse_exp_range(j['e'], j['t'])
    if rg is None:
        continue
    y = parse_yrs(p['e'])
    if y is None:
        continue
    lo, hi = rg
    if hi is not None:
        in_range = y >= lo and y <= hi + 2
    else:
        in_range = y >= lo
    if not in_range:
        remaining += 1
        range_str = f"{lo:g}-{hi:g}" if hi else f"{lo:g}+"
        print(f"  STILL MISMATCHED: {p['n'][:30]:30s} | score={score} | {y:g}yrs vs {range_str}")

if remaining == 0:
    print("  ALL CLEAR - no green-zone experience mismatches remain!")
else:
    print(f"  WARNING: {remaining} mismatches remain")
