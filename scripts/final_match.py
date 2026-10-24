"""
Final Broadridge matching script.
Scores are calibrated to match the existing scale (60-85 range for good matches).
Green = genuinely relevant candidates with right skills AND experience.
Yellow = partial match or disability/qual issues.
Red = some skill overlap but clear gaps.
"""
import sys, json, re, shutil
sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\data\data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

thr = d["thr"]   # [66, 52]
GREEN_THR  = thr[0]   # 66
YELLOW_THR = thr[1]   # 52

# ── Remove old Broadridge pl entries ────────────────────────────────────────
broadridge_ids = {100, 101, 102, 103, 104}
before = len(d["pl"])
d["pl"] = [e for e in d["pl"] if e[0] not in broadridge_ids]
print(f"Removed {before - len(d['pl'])} old Broadridge entries")

# ── Skill definitions per JD ─────────────────────────────────────────────────
# Organized by TIER:
# tier1 = core skills (must have several of these to be green)
# tier2 = nice-to-have skills
JD_CONFIG = {
    100: {  # Full Stack Developer (4-6 yrs, Hyderabad)
        "tier1": ["react", "node", "javascript", "express", "postgresql",
                  "sql", "fullstack", "full stack", "full-stack", "reactjs",
                  "nodejs", "next.js", "nextjs"],
        "tier2": ["rest api", "rest", "api", "git", "github", "ci/cd", "cicd",
                  "devops", "database", "mongodb", "mysql", "typescript",
                  "html", "css", "python", "backend", "frontend", "angular",
                  "vue", "graphql", "docker", "aws", "cloud"],
        "q": "",
        "exp": "4-6 years",
    },
    101: {  # Procurement Buyer (2-4 yrs, Bengaluru)
        "tier1": ["procurement", "purchase order", "sourcing", "vendor",
                  "supplier", "purchase", "purchasing", "supply chain"],
        "tier2": ["inventory", "oracle", "wms", "excel", "ms excel", "logistics",
                  "reconciliation", "rebates", "operations", "stock", "erp",
                  "sap", "ariba", "negotiation", "rfq", "rfo", "contract"],
        "q": "",
        "exp": "2-4 years",
    },
    102: {  # Fixed Asset Accountant (1-5 yrs, Hyderabad)
        "tier1": ["fixed asset", "depreciation", "general ledger", "accounting",
                  "reconciliation", "finance", "financial reporting", "accounts",
                  "ledger", "asset", "capex", "capitalization"],
        "tier2": ["oracle fusion", "oracle", "blackline", "power bi", "excel",
                  "ms excel", "month end", "month-end", "ifrs", "ind as",
                  "tally", "sap", "erp", "audit", "gst", "tax", "balance sheet",
                  "profit loss", "intercompany", "journal"],
        "q": "bachelor commerce accounting finance",
        "exp": "1-5 years",
    },
    103: {  # Cash Application Specialist (2-5 yrs, Bengaluru)
        "tier1": ["accounts receivable", "cash application", "order to cash",
                  "o2c", "invoice", "reconciliation", "ar", "receivable",
                  "accounting", "finance", "accounts"],
        "tier2": ["oracle", "highradius", "apro", "excel", "ageing", "aging",
                  "unapplied", "remittance", "customer payment", "bfsi",
                  "erp", "sap", "tally", "billing", "collection", "debtors",
                  "ledger", "credit control", "cash flow"],
        "q": "commerce graduate postgraduate accounting",
        "exp": "2-5 years",
    },
    104: {  # Procurement Operations Specialist (2-4 yrs, Bengaluru)
        "tier1": ["procurement", "purchase order", "sourcing", "vendor",
                  "supplier", "purchase", "purchasing", "supply chain",
                  "operations"],
        "tier2": ["inventory", "oracle", "wms", "excel", "ms excel", "logistics",
                  "reconciliation", "rebates", "stock", "erp", "sap",
                  "negotiation", "rfq", "contract", "warehouse", "dispatch"],
        "q": "",
        "exp": "2-4 years",
    },
}

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

def parse_exp_range(e):
    if not e: return None
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
    btech  = ["b.tech","btech","b tech","b.e ","be ","bachelor of technology"]
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

def match_keywords(cand_text, tier):
    """Return (hits, total, hit_list)."""
    hits, hit_list = 0, []
    for kw in tier:
        if kw.lower() in cand_text:
            hits += 1; hit_list.append(kw)
    return hits, len(tier), hit_list

def compute_score(person, jd_id):
    """
    Compute a score in the same range as existing system (50-85).
    Scoring:
      - t1_hits: each tier1 match = 8 pts (core skills)
      - t2_hits: each tier2 match = 3 pts (supporting)
      - Base: 50 (if any skills match at all)
      - Max raw: 50 + 8*N_t1 + 3*N_t2 (capped at 90)
    Then apply red-line penalties.
    """
    cfg = JD_CONFIG[jd_id]
    cand_text = " ".join([
        person.get("sk",""), person.get("q",""), person.get("role",""),
        person.get("org",""), person.get("note","")
    ]).lower()

    t1_hits, t1_total, t1_list = match_keywords(cand_text, cfg["tier1"])
    t2_hits, t2_total, t2_list = match_keywords(cand_text, cfg["tier2"])
    total_hits = t1_hits + t2_hits

    if total_hits == 0: return None, [], []

    raw = 50 + t1_hits*8 + t2_hits*3
    s   = min(raw, 90)

    reason_parts = []
    reason_parts.append(f"{t1_hits} core + {t2_hits} support skills matched")
    if t1_list: reason_parts.append("\u2713 Core: " + ", ".join(t1_list[:6]))
    if t2_list: reason_parts.append("+ " + ", ".join(t2_list[:4]))

    return s, t1_list, t2_list, reason_parts

# ── Main matching loop ────────────────────────────────────────────────────────

people  = d["people"]
existing = {(e[0], e[1]) for e in d["pl"]}
new_pl_entries = []

for jd_id, cfg in JD_CONFIG.items():
    jd = next(j for j in d["jds"] if j["id"] == jd_id)
    jd_rng = parse_exp_range(cfg["exp"])
    found  = []

    for pidx, p in enumerate(people):
        if (jd_id, pidx) in existing: continue

        # ── Experience gate ───────────────────────────────────────────────
        yrs = parse_yrs(p.get("e",""))
        if jd_rng and yrs is not None:
            lo, hi = jd_rng
            if yrs < lo - 0.5: continue            # below minimum → skip
            if hi is not None and yrs > hi + 5: continue  # way over max → skip

        # ── Skill scoring ─────────────────────────────────────────────────
        result = compute_score(p, jd_id)
        if result[0] is None: continue
        s, t1_list, t2_list, reason_parts = result

        # Require at least 1 tier1 (core) skill hit to be considered at all
        if len(t1_list) == 0: continue

        reasons = reason_parts[:]

        # ── Disability red-line ───────────────────────────────────────────
        ok_dis = dis_ok(p.get("dt",""), p.get("dp",""))
        if not ok_dis:
            reasons.append("\u26a0 Disability: no verified disability info (>=40%)")
            if s >= GREEN_THR: s = GREEN_THR - 1

        # ── Experience red-line ───────────────────────────────────────────
        exp_strict = False
        if jd_rng and yrs is not None:
            lo, hi = jd_rng
            exp_strict = not (yrs >= lo and (hi is None or yrs <= hi + 2))
        if exp_strict:
            reasons.append(f"[EXP RED-LINE] {yrs}yr vs JD {cfg['exp']}")
            if s >= GREEN_THR: s = GREEN_THR - 1
            s = min(s, YELLOW_THR - 1)

        # ── Qualification red-line ────────────────────────────────────────
        ok_qual = qual_ok(p.get("q",""), cfg["q"])
        if not ok_qual:
            reasons.append("\u274c Qual red-line: Commerce/Finance degree required")
            if s >= GREEN_THR: s = GREEN_THR - 1

        zone = "g" if s >= GREEN_THR else ("y" if s >= YELLOW_THR else "r")
        found.append({
            "pidx":  pidx, "score": s, "zone": zone,
            "t1":    len(t1_list), "t2": len(t2_list),
            "yrs":   yrs, "reason": "; ".join(reasons),
            "name":  p.get("n","?")
        })

    zo = {"g":0,"y":1,"r":2}
    found.sort(key=lambda x: (zo[x["zone"]], -x["score"]))
    taken = found[:80]

    g = sum(1 for x in taken if x["zone"]=="g")
    y = sum(1 for x in taken if x["zone"]=="y")
    r = sum(1 for x in taken if x["zone"]=="r")
    print(f"\nJD {jd_id}: {jd['t']}")
    print(f"  Found: {len(found)}  Taking: {len(taken)}  [G={g} Y={y} R={r}]")
    for x in taken[:8]:
        print(f"    [{x['zone'].upper()}] sc={x['score']}  t1={x['t1']}+t2={x['t2']}  {x['yrs']}yr  {x['name'][:32]}")

    for x in taken:
        new_pl_entries.append([jd_id, x["pidx"], x["score"], x["reason"], 0])

print(f"\n=== Adding {len(new_pl_entries)} entries ===")

shutil.copy(DATA_PATH, DATA_PATH + ".backup_pre_broadridge_final")
d["pl"].extend(new_pl_entries)
with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, separators=(",",":"))

print(f"Done! pl now has {len(d['pl'])} entries.")
