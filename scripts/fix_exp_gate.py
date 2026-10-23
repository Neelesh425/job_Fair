"""
fix_exp_gate.py
Enforces experience minimum gating across ALL JDs.
A candidate whose parsed experience < JD minimum experience is removed from that JD's placement list.
"""
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('data/data.json', encoding='utf-8'))

# ─── Experience parsers ────────────────────────────────────────────────────────

def parse_cand_exp(e):
    """Parse candidate experience — returns years as float."""
    if not e: return 0.0
    e = str(e).strip().lower()
    if re.match(r'^(fresher|0|na|nil|no exp|none|n/a)$', e): return 0.0
    # months only (no years)
    m = re.search(r'(\d+)\s*month', e)
    if m and not re.search(r'year|yr', e):
        return int(m.group(1)) / 12
    # years (+ optional months)
    m2 = re.search(r'(\d+)\s*(?:year|yr)', e)
    if m2:
        y = int(m2.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        return y + (int(mm.group(1)) / 12 if mm else 0)
    # bare number
    nums = re.findall(r'\d+(?:\.\d+)?', e)
    for n in nums:
        v = float(n)
        if 0 <= v <= 50: return v
    return 0.0


def parse_jd_min_exp(e):
    """
    Parse the MINIMUM experience requirement from a JD e-field.
    Examples:
        '2–5 years'                -> 2.0
        '3-5 years'                -> 3.0
        '5+ years'                 -> 5.0
        '8–12 years (analytics)'   -> 8.0
        'More than 1 year'         -> 1.0
        'Fresher (0-6 months)'     -> 0.0
        'Freshers and experienced' -> 0.0   (open to all)
        '12+ years'                -> 12.0
        '1–2 yrs'                  -> 1.0
        'Internships: BTech ...'   -> None  (special case, skip)
        ''                         -> None  (no requirement)
    Returns None if the requirement cannot be determined or should not be enforced.
    """
    if not e: return None
    e_low = str(e).strip().lower()

    # Skip special / ambiguous entries
    skip_phrases = [
        'freshers and experienced', 'fresh graduates only', 'fresher or experienced',
        'open to freshers', 'internship', 'btech student', 'any graduate',
        'final year', 'immediate joiner'
    ]
    if any(p in e_low for p in skip_phrases): return 0.0  # treat as 0 min

    # Explicit fresher-only
    if re.match(r'^fresher', e_low): return 0.0

    # 'More than X year'
    mt = re.search(r'more than\s+(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if mt: return float(mt.group(1))

    # 'at least X year'
    al = re.search(r'at least\s+(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if al: return float(al.group(1))

    # Range: 'X–Y years' or 'X-Y years' — take X as minimum
    rng = re.search(r'(\d+(?:\.\d+)?)\s*[–\-–]\s*\d+(?:\.\d+)?\s*(?:year|yr)', e_low)
    if rng: return float(rng.group(1))

    # 'X+ years'
    plus = re.search(r'(\d+(?:\.\d+)?)\s*\+\s*(?:year|yr)', e_low)
    if plus: return float(plus.group(1))

    # 'X years' (no range, no plus)
    bare = re.search(r'(\d+(?:\.\d+)?)\s*(?:year|yr)', e_low)
    if bare: return float(bare.group(1))

    # months only range
    mo_rng = re.search(r'(\d+)\s*[–\-]\s*\d+\s*month', e_low)
    if mo_rng: return int(mo_rng.group(1)) / 12

    return None  # can't parse, don't enforce


# ─── Build placements by JD ────────────────────────────────────────────────────
by_jd = {}
for i, row in enumerate(d['pl']):
    jid, pid, sc, rs = row[0], row[1], row[2], row[3]
    pool = row[4] if len(row) > 4 else None
    if jid not in by_jd: by_jd[jid] = []
    by_jd[jid].append((i, pid, sc, rs, pool))

# ─── Enforce experience gate across all JDs ────────────────────────────────────
removed_indices = set()
total_removed = 0
log = {}

for jd in d['jds']:
    jid = jd['id']
    co = d['cos'][jd['c']]
    title = jd['t']
    min_exp = parse_jd_min_exp(jd.get('e', ''))

    if min_exp is None or min_exp <= 0:
        continue  # no enforceable minimum

    rows = by_jd.get(jid, [])
    jd_removed = []

    for idx, pid, sc, rs, pool in rows:
        p = d['people'][pid]
        cand_exp = parse_cand_exp(p.get('e', ''))
        if cand_exp < min_exp:
            removed_indices.add(idx)
            jd_removed.append(p['n'])
            total_removed += 1

    if jd_removed:
        key = f"[{co}] {title}"
        log[key] = {
            'min_exp': min_exp,
            'jd_exp_raw': jd.get('e', ''),
            'removed_count': len(jd_removed),
            'removed_names': jd_removed[:5]
        }
        print(f"Removed {len(jd_removed):3d} from [{co}] {title[:50]} (min {min_exp:.1f}yr)")

# ─── Rebuild placement list without removed entries ────────────────────────────
new_pl = [row for i, row in enumerate(d['pl']) if i not in removed_indices]

print()
print(f"Total removed: {total_removed}")
print(f"Original placements: {len(d['pl'])}")
print(f"New placements: {len(new_pl)}")

d['pl'] = new_pl

# ─── Save updated data ─────────────────────────────────────────────────────────
with open('data/data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False)

print()
print("data/data.json updated — experience gate enforced on all JDs.")
