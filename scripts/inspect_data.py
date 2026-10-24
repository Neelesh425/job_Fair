import sys, json
sys.stdout.reconfigure(encoding="utf-8")
with open("data/data.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("=== Broadridge JDs ===")
for jd in d["jds"]:
    if jd["c"] == 13:
        print(f"  JD {jd['id']}: {jd['t']}  exp={jd['e']}  q={jd.get('q','-')[:40]}")
        print(f"       sk={jd.get('sk','')[:80]}")

print()
print("=== D.pl sample (first 3 entries) ===")
for p in d["pl"][:3]:
    print(" ", p)

print()
print("Total people:", len(d["people"]))
print("Total pl entries:", len(d["pl"]))

p0 = d["people"][0]
print()
print("Sample person keys:", list(p0.keys()))
print("sk sample:", str(p0.get("sk",""))[:100])
print("q sample:", str(p0.get("q",""))[:60])
print("e sample:", str(p0.get("e",""))[:40])
