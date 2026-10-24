import sys, json, re
sys.stdout.reconfigure(encoding="utf-8")
DATA_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\data\data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

# Understand the existing scoring across all JDs
thr = d["thr"]
print(f"Thresholds: Green>={thr[0]}  Yellow>={thr[1]}")
print()

# Score distribution across ALL pl entries
all_scores = [e[2] for e in d["pl"]]
green  = sum(1 for s in all_scores if s >= thr[0])
yellow = sum(1 for s in all_scores if thr[0] > s >= thr[1])
red    = sum(1 for s in all_scores if s < thr[1])
print(f"ALL pl entries ({len(all_scores)}):")
print(f"  Green (>={thr[0]}):  {green} ({green*100//len(all_scores)}%)")
print(f"  Yellow ({thr[1]}-{thr[0]-1}): {yellow} ({yellow*100//len(all_scores)}%)")
print(f"  Red (<{thr[1]}):    {red} ({red*100//len(all_scores)}%)")
print()

# Show score distribution histogram
buckets = {}
for s in all_scores:
    b = (s//10)*10
    buckets[b] = buckets.get(b,0)+1
for b in sorted(buckets):
    print(f"  {b}-{b+9}: {buckets[b]} entries")

print()
# Look at some green candidates to understand what score they have
green_entries = [e for e in d["pl"] if e[2] >= thr[0]]
print(f"Sample green entries (first 5):")
for e in green_entries[:5]:
    p = d["people"][e[1]]
    print(f"  sc={e[2]}  {p.get('n','?')[:30]:30s}  sk={p.get('sk','')[:60]}")
    print(f"    rs={e[3][:100]}")

# Now understand: for Broadridge JDs, how many have disability ok?
broadridge_pl = [e for e in d["pl"] if e[0] in [100,101,102,103,104]]
print(f"\nBroadridge: {len(broadridge_pl)} entries")
print("Score range:", min(e[2] for e in broadridge_pl) if broadridge_pl else "n/a",
      "-", max(e[2] for e in broadridge_pl) if broadridge_pl else "n/a")

# Check disability ok for broadridge candidates
def parse_dp(dp_str):
    if not dp_str: return None
    m = re.search(r"\d+(?:\.\d+)?", str(dp_str).strip())
    if not m: return None
    v = float(m.group())
    if v <= 1: v *= 100
    return v

dis_ok_count = 0
for e in broadridge_pl:
    p = d["people"][e[1]]
    dt = (p.get("dt","") or "").strip()
    pct = parse_dp(p.get("dp",""))
    if dt and pct is not None and pct >= 40:
        dis_ok_count += 1
print(f"Disability OK in Broadridge: {dis_ok_count}/{len(broadridge_pl)}")

# Check existing green candidates skill match score patterns
# For non-broadridge JD0 (Full Stack): what score did green candidates get?
jd0_green = [e for e in d["pl"] if e[0]==0 and e[2]>=thr[0]]
print(f"\nJD 0 (Enterprise Networking) green count: {len(jd0_green)}")
for e in jd0_green[:3]:
    p = d["people"][e[1]]
    print(f"  sc={e[2]}  rs={e[3][:80]}")
