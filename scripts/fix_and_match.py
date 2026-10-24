"""
Fix Broadridge JD skill keywords to use full meaningful skills (not word fragments),
then re-match candidates properly. Removes old Broadridge pl entries first.
"""
import sys, json, re, shutil
sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\data\data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

# ─── Step 1: Update JD skill keyword lists (phrase-based, easier to match) ───

JD_SKILLS = {
    100: {  # Full Stack Developer
        "sk_list": [
            "react", "reactjs", "react.js",          # React
            "node", "nodejs", "node.js",               # Node
            "express", "expressjs",                    # Express
            "postgresql", "postgres", "sql",           # DB
            "javascript", "js",                        # JS
            "rest api", "restful", "rest",             # APIs
            "git", "github", "version control",        # VCS
            "ci/cd", "cicd", "devops", "jenkins",      # CI/CD
            "database", "mongodb", "mysql",            # DB generic
            "fullstack", "full stack", "full-stack",   # Role
        ],
        "q": ""
    },
    101: {  # Procurement Buyer
        "sk_list": [
            "procurement", "purchase", "purchasing",
            "purchase order", "po management",
            "supplier", "vendor", "sourcing",
            "inventory", "stock",
            "oracle", "oracle po", "wms",
            "excel", "ms excel",
            "reconciliation", "recon",
            "rebates", "supply chain",
            "logistics", "operations",
        ],
        "q": ""
    },
    102: {  # Fixed Asset Accountant
        "sk_list": [
            "fixed asset", "fixed assets",
            "general ledger", "gl accounting",
            "depreciation", "amortisation", "amortization",
            "asset reconciliation", "reconciliation",
            "capitalization", "capex",
            "oracle fusion", "oracle financials",
            "blackline",
            "power bi", "powerbi",
            "excel", "ms excel",
            "month end", "month-end closing", "financial reporting",
            "accounting", "finance", "accounts",
        ],
        "q": "bachelor commerce accounting finance"
    },
    103: {  # Cash Application Specialist
        "sk_list": [
            "accounts receivable", "ar",
            "cash application",
            "order to cash", "o2c", "otc",
            "invoice reconciliation", "reconciliation",
            "unapplied cash",
            "oracle", "highradius", "apro",
            "excel", "ms excel",
            "ageing report", "aging report",
            "customer payments", "remittance",
            "accounting", "finance", "accounts",
            "bfsi", "banking",
        ],
        "q": "commerce graduate postgraduate accounting"
    },
    104: {  # Procurement Operations Specialist
        "sk_list": [
            "procurement", "purchase", "purchasing",
            "purchase order", "po management",
            "supplier", "vendor", "sourcing",
            "inventory", "stock",
            "oracle", "oracle po", "wms",
            "excel", "ms excel",
            "reconciliation",
            "rebates", "supply chain",
            "logistics", "operations",
        ],
        "q": ""
    },
}

# Update JDs in data
for jd in d["jds"]:
    if jd["id"] in JD_SKILLS:
        info = JD_SKILLS[jd["id"]]
        jd["sk"] = "|".join(info["sk_list"])   # pipe-separated for phrase matching
        jd["q"]  = info["q"]

# ─── Step 2: Remove old Broadridge pl entries ─────────────────────────────────

broadridge_ids = {100, 101, 102, 103, 104}
old_count = len(d["pl"])
d["pl"] = [e for e in d["pl"] if e[0] not in broadridge_ids]
print(f"Removed {old_count - len(d['pl'])} old Broadridge entries")

# ─── helpers ─────────────────────────────────────────────────────────────────

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
    e = e.lower()
    m = re.search(r"(\d+)\s*[-]\s*(\d+)", e)
    if m: return (float(m.group(1)), float(m.group(2)))
    m = re.search(r"(\d+)\s*(\+|yr|year)", e)
    if m: return (float(m.group(1)), None)
    if re.search(r"fresher", e): return (0, 1)
    return None

def parse_dp(dp_str):
    if not dp_str: return None
    m = re.search(r"\d+(?:\.\d+)?", str(dp_str).strip())
    if not m: return None
    v = float(m.group())
    if v <= 1: v *= 100
    return v

def dis_ok(dt, dp):
    has_type = bool((dt or "").strip())
    pct = parse_dp(dp)
    return has_type and pct is not None and pct >= 40

def qual_ok(cand_q, jd_q):
    if not jd_q or not jd_q.strip(): return True
    q  = (cand_q or "").lower()
    jq = jd_q.lower()
    bcoms  = ["b.com","bcom","b com","bachelor of commerce","commerce"]
    mcom   = ["m.com","mcom","m com","master of commerce","postgraduate","pg"]
    btech  = ["b.tech","btech","b tech","b.e","be","bachelor of technology"]
    mba    = ["mba","master of business"]
    mca    = ["mca","master of computer"]
    anyg   = ["graduate","graduation","degree","bachelor"]
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

def skill_score_phrase(person, sk_list):
    """Score using phrase list — each phrase is an atomic match unit."""
    cand_text = " ".join([
        person.get("sk",""), person.get("q",""),
        person.get("role",""), person.get("org",""),
        person.get("note","")
    ]).lower()
    hits, hit_list, miss_list = 0, [], []
    for phrase in sk_list:
        phrase_l = phrase.lower()
        # Allow partial word match for single-word phrases
        matched = phrase_l in cand_text
        if not matched and " " not in phrase_l and len(phrase_l) >= 4:
            matched = bool(re.search(r"\b" + re.escape(phrase_l[:5]), cand_text))
        if matched: hits += 1; hit_list.append(phrase)
        else: miss_list.append(phrase)
    total = len(sk_list)
    pct   = round(hits/total*100) if total > 0 else 0
    return pct, hits, total, hit_list, miss_list

# ─── Step 3: Match candidates ─────────────────────────────────────────────────

people = d["people"]
thr    = d["thr"]
GREEN_THR  = thr[0]   # 66
YELLOW_THR = thr[1]   # 52

existing = {(e[0], e[1]) for e in d["pl"]}

new_pl_entries = []

for jd in d["jds"]:
    if jd["c"] != 13: continue
    jd_id    = jd["id"]
    jd_exp   = jd["e"]
    jd_title = jd["t"]
    jd_q     = jd.get("q","")
    sk_list  = JD_SKILLS[jd_id]["sk_list"]
    jd_rng   = parse_exp_range(jd_exp)

    found = []

    for pidx, p in enumerate(people):
        if (jd_id, pidx) in existing: continue

        cand_exp = p.get("e","")
        yrs = parse_yrs(cand_exp)

        # Experience gate
        if jd_rng and yrs is not None:
            lo, hi = jd_rng
            if yrs < lo - 0.5: continue
            if hi is not None and yrs > hi + 5: continue

        # Skill match
        pct, hits, total, hit_list, miss_list = skill_score_phrase(p, sk_list)

        # Minimum: at least 3 matching skill phrases
        if hits < 3 or pct < 12: continue

        # Compute score: 30 + (pct * 0.7) => range 30-100
        # Higher weight on pct to reach green (>=66) for strong matches
        s = 30 + round(pct * 0.7)
        reasons = [f"Skill match: {pct}% ({hits}/{total} skills)"]
        if hit_list:
            reasons.append("\u2713 " + ", ".join(hit_list[:8]))

        # Disability red-line
        ok_dis = dis_ok(p.get("dt",""), p.get("dp",""))
        if not ok_dis:
            reasons.append("\u26a0 Disability: no verified disability info")
            if s >= GREEN_THR: s = GREEN_THR - 1

        # Experience red-line
        exp_strict = False
        if jd_rng and yrs is not None:
            lo, hi = jd_rng
            exp_strict = not (yrs >= lo and (hi is None or yrs <= hi + 2))
        if exp_strict:
            reasons.append(f"[EXP RED-LINE] {yrs}yr vs JD {jd_exp}")
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

    zo = {"g":0,"y":1,"r":2}
    found.sort(key=lambda x: (zo[x["zone"]], -x["pct"], -x["hits"]))
    taken = found[:80]

    g = sum(1 for x in taken if x["zone"]=="g")
    y = sum(1 for x in taken if x["zone"]=="y")
    r = sum(1 for x in taken if x["zone"]=="r")
    print(f"\nJD {jd_id}: {jd_title}")
    print(f"  Found: {len(found)}  Taking: {len(taken)}  [G={g} Y={y} R={r}]")
    for x in taken[:6]:
        print(f"    [{x['zone'].upper()}] sc={x['score']}  sk={x['pct']}%  {x['yrs']}yr  {x['name'][:32]}")

    for x in taken:
        new_pl_entries.append([jd_id, x["pidx"], x["score"], x["reason"], 0])

print(f"\n=== Adding {len(new_pl_entries)} entries ===")

# Write backup + update
shutil.copy(DATA_PATH, DATA_PATH + ".backup_pre_broadridge_match2")
d["pl"].extend(new_pl_entries)
with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, separators=(",",":"))

print(f"Done! pl now has {len(d['pl'])} entries.")
