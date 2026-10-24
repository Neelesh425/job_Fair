"""
Analyze what is blocking candidates from green in Broadridge JDs.
"""
import sys, json, re
sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\data\data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

people = d["people"]
thr    = d["thr"]
GREEN_THR  = thr[0]   # 66

def parse_dp(dp_str):
    if not dp_str: return None
    m = re.search(r"\d+(?:\.\d+)?", str(dp_str).strip())
    if not m: return None
    v = float(m.group())
    if v <= 1: v *= 100
    return v

# Sample the first 200 people and see disability distribution
ok_dis = 0
no_type = 0
low_pct = 0
no_pct = 0
for p in people:
    dt = (p.get("dt","") or "").strip()
    dp = p.get("dp","")
    pct = parse_dp(dp)
    has_type = bool(dt)
    meets_min = pct is not None and pct >= 40
    if has_type and meets_min:
        ok_dis += 1
    elif not has_type:
        no_type += 1
    elif pct is None:
        no_pct += 1
    else:
        low_pct += 1

print(f"Total people: {len(people)}")
print(f"  Disability OK (type + >=40%): {ok_dis}")
print(f"  No disability type:           {no_type}")
print(f"  Has type, no pct:             {no_pct}")
print(f"  Has type, pct <40%:           {low_pct}")

# Now look at the Broadridge pl entries
broadridge_pl = [e for e in d["pl"] if e[0] in [100,101,102,103,104]]
print(f"\nBroadridge pl entries: {len(broadridge_pl)}")

# Score distribution
scores = [e[2] for e in broadridge_pl]
green = sum(1 for s in scores if s >= GREEN_THR)
yellow= sum(1 for s in scores if GREEN_THR > s >= thr[1])
red   = sum(1 for s in scores if s < thr[1])
print(f"  Green (>={GREEN_THR}):  {green}")
print(f"  Yellow ({thr[1]}-{GREEN_THR-1}): {yellow}")
print(f"  Red (<{thr[1]}):    {red}")

# Look at the disability flag in reasons
dis_flagged = sum(1 for e in broadridge_pl if "Disability flag" in (e[3] or ""))
exp_flagged = sum(1 for e in broadridge_pl if "EXP RED-LINE" in (e[3] or ""))
qual_flagged= sum(1 for e in broadridge_pl if "Qual red-line" in (e[3] or ""))
print(f"\nRed-line flags:")
print(f"  Disability: {dis_flagged}")
print(f"  Experience: {exp_flagged}")
print(f"  Qual:       {qual_flagged}")

# Show top 3 for JD 100 (Full Stack)
print("\n=== JD 100 (Full Stack) top candidates ===")
jd100 = sorted([e for e in broadridge_pl if e[0]==100], key=lambda x: -x[2])
for e in jd100[:5]:
    p = people[e[1]]
    print(f"  {p.get('n','?')[:30]:30s} sc={e[2]}  sk={p.get('sk','')[:70]}")
    print(f"    reason: {e[3][:100]}")
    print(f"    dt={p.get('dt','?')}  dp={p.get('dp','?')}")
