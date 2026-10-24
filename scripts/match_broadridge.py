"""
Match existing people in data.json to Broadridge JDs (100-104).
Strict matching: experience + skill criteria enforced.
Only adds relevant candidates. No irrelevant ones.
"""
import sys, json, re, shutil
sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\data\data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

people = d["people"]
jds    = d["jds"]
pl     = d["pl"]
thr    = d["thr"]   # [66, 52]
GREEN_THR  = thr[0]   # 66
YELLOW_THR = thr[1]   # 52

# ── helpers ──────────────────────────────────────────────────────────────────

def parse_yrs(t):
    if not t: return None
    t = t.lower().strip()
    if re.search(r"fresh|no exp|nil|n\.?a\.?|not applicable|^0$|intern", t): return 0
    ym = re.search(r"(\d+)\s*year", t)
    mm = re.search(r"(\d+)\s*month", t)
    if ym and mm:
        return round((int(ym.group(1)) + int(mm.group(1))/12)*10)/10
    v = re.findall(r"\d+(?:\.\d+)?", t)
    if not v: return None
    first = float(v[0])
    if first > 40: return None
    if "month" in t and "year" not in t and len(v)==1:
        return round(first/12*10)/10
    if len(v) >= 2 and re.search(r"\d\s*[-to]\s*\d", t):
        return (first + float(v[1])) / 2
    return first

def parse_exp_range(e, title=""):
    if not e: e = ""
    e = e.lower(); title = (title or "").lower()
    if re.search(r"fresher", e) and re.search(r"experience", e): return None
    if re.search(r"fresher", e) or (re.search(r"fresher", title) and not e): return (0, 1)
    m = re.search(r"(\d+)\s*[-]\s*(\d+)", e)
    if m: return (float(m.group(1)), float(m.group(2)))
    m = re.search(r"(\d+)\s*(\+|yr|year)", e)
    if m: return (float(m.group(1)), None)
    return None

def parse_dp(dp_str):
    """Safely parse disability percentage. Returns float or None."""
    if not dp_str: return None
    s = str(dp_str).strip()
    # Extract first valid number (ignore lone dots)
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m: return None
    v = float(m.group())
    if v <= 1: v *= 100   # 0.4 -> 40%
    return v

def dis_ok(dt, dp):
    has_type = bool((dt or "").strip())
    pct = parse_dp(dp)
    has_pct  = pct is not None
    meets_min = has_pct and pct >= 40
    return has_type and meets_min

def qual_ok(cand_q, jd_q):
    if not jd_q or not jd_q.strip(): return True
    q  = (cand_q or "").lower()
    jq = jd_q.lower()
    bcoms = ["b.com","bcom","b com","bachelor of commerce","commerce"]
    mcom  = ["m.com","mcom","m com","master of commerce","postgraduate","pg"]
    btech = ["b.tech","btech","b tech","b.e","be","bachelor of technology"]
    mba   = ["mba","master of business"]
    mca   = ["mca","master of computer"]
    anyg  = ["graduate","graduation","degree","bachelor"]
    needs_commerce = any(k in jq for k in bcoms) or "account" in jq or "finance" in jq
    has_bcom    = any(k in q for k in bcoms)
    has_mcom    = any(k in q for k in mcom)
    has_related = (has_bcom or has_mcom or "commerce" in q or "account" in q
                   or "finance" in q or "financial" in q or any(k in q for k in mba))
    has_grad    = (any(k in q for k in anyg) or has_bcom or has_mcom
                   or any(k in q for k in btech) or any(k in q for k in mba)
                   or any(k in q for k in mca) or "bsc" in q or "b.sc" in q)
    if needs_commerce: return has_related
    if "graduate" in jq or "bachelor" in jq: return has_grad
    return True

def skill_score(person, jd_sk):
    if not jd_sk: return 0, 0, 0, [], []
    cand_text = " ".join([
        person.get("sk",""), person.get("q",""),
        person.get("role",""), person.get("org",""),
        person.get("note","")
    ]).lower()
    keywords = [w for w in re.split(r"[\s,/.\-]+", jd_sk.lower()) if len(w) > 2]
    unique   = list(dict.fromkeys(keywords))
    hits, hit_list, miss_list = 0, [], []
    for kw in unique:
        matched = (kw in cand_text
                   or (len(kw) > 5 and kw[:5] in cand_text)
                   or (len(kw) > 4 and kw[:-2] in cand_text))
        if matched: hits += 1; hit_list.append(kw)
        else: miss_list.append(kw)
    total = len(unique)
    pct   = round(hits/total*100) if total > 0 else 0
    return pct, hits, total, hit_list, miss_list

# ── Broadridge JDs ────────────────────────────────────────────────────────────

broadridge_jds = [j for j in jds if j["c"] == 13]

# Already-assigned pairs (jd_id, person_idx)
existing = {(e[0], e[1]) for e in pl}

# Tuning parameters
MIN_HITS = 2      # must match at least 2 skill keywords
MIN_PCT  = 8      # must match at least 8% of keywords
MAX_PER_JD = 80   # cap per JD to keep the view manageable

new_pl_entries = []

for jd in broadridge_jds:
    jd_id    = jd["id"]
    jd_exp   = jd["e"]
    jd_title = jd["t"]
    jd_sk    = jd.get("sk","")
    jd_q     = jd.get("q","")
    jd_rng   = parse_exp_range(jd_exp, jd_title)

    found = []

    for pidx, p in enumerate(people):
        if (jd_id, pidx) in existing:
            continue

        cand_exp = p.get("e","")
        yrs = parse_yrs(cand_exp)

        # Experience gate: skip if clearly below minimum or way over maximum
        if jd_rng and yrs is not None:
            lo, hi = jd_rng
            if yrs < lo - 0.5: continue            # below min → out
            if hi is not None and yrs > hi + 5: continue  # way over max → out

        # Skill match
        pct, hits, total, hit_list, miss_list = skill_score(p, jd_sk)
        if hits < MIN_HITS or pct < MIN_PCT: continue

        # Compute score (mirrors JS ai() for pool candidates)
        s = 30 + round(pct * 0.6)
        reasons = [f"Skill match: {pct}% ({hits}/{total} keywords)"]
        if hit_list:
            reasons.append("\u2713 " + ", ".join(hit_list[:6]))

        # Disability red-line
        ok_dis = dis_ok(p.get("dt",""), p.get("dp",""))
        if not ok_dis:
            reasons.append("\u26a0 Disability flag")
            if s >= GREEN_THR: s = GREEN_THR - 1

        # Experience red-line (strict: candidate yrs < lo by any amount)
        exp_strict = False
        if jd_rng and yrs is not None:
            lo, hi = jd_rng
            in_range = yrs >= lo and (hi is None or yrs <= hi + 2)
            exp_strict = not in_range
        if exp_strict:
            reasons.append(f"[EXP RED-LINE] {yrs}yrs vs JD {jd_exp}")
            if s >= GREEN_THR: s = GREEN_THR - 1
            s = min(s, YELLOW_THR - 1)

        # Qualification red-line
        ok_qual = qual_ok(p.get("q",""), jd_q)
        if not ok_qual:
            reasons.append("\u274c Qual red-line: Commerce/Finance degree required")
            if s >= GREEN_THR: s = GREEN_THR - 1

        zone = "g" if s >= GREEN_THR else ("y" if s >= YELLOW_THR else "r")
        found.append({"pidx": pidx, "score": s, "zone": zone, "pct": pct,
                      "hits": hits, "yrs": yrs, "reason": "; ".join(reasons),
                      "name": p.get("n","?")})

    # Sort: greens first, then yellows, reds; within zone by skill pct desc
    zone_order = {"g": 0, "y": 1, "r": 2}
    found.sort(key=lambda x: (zone_order[x["zone"]], -x["pct"]))
    taken = found[:MAX_PER_JD]

    g = sum(1 for x in taken if x["zone"]=="g")
    y = sum(1 for x in taken if x["zone"]=="y")
    r = sum(1 for x in taken if x["zone"]=="r")
    print(f"\nJD {jd_id}: {jd_title}")
    print(f"  Found: {len(found)}  Taking: {len(taken)}  [G={g} Y={y} R={r}]")
    for x in taken[:8]:
        print(f"    {x['name'][:32]:32s}  {str(x['yrs'])+'yr':6s}  sk={x['pct']}%  [{x['zone'].upper()}] sc={x['score']}")

    for x in taken:
        new_pl_entries.append([jd_id, x["pidx"], x["score"], x["reason"], 0])

print(f"\n=== Total new entries to add: {len(new_pl_entries)} ===")

# Write back
shutil.copy(DATA_PATH, DATA_PATH + ".backup_pre_broadridge_match")
d["pl"].extend(new_pl_entries)

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, separators=(",", ":"))

print(f"data.json updated: pl now has {len(d['pl'])} entries (added {len(new_pl_entries)})")
