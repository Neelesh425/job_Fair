"""Update the sk field in data.json for Broadridge JDs to use pipe-separated full phrases."""
import sys, json, shutil
sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\data\data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    d = json.load(f)

JD_SK = {
    100: "react|reactjs|node|nodejs|express|expressjs|postgresql|javascript|sql|rest api|rest|git|ci/cd|devops|database|fullstack|full stack|typescript|docker|aws",
    101: "procurement|purchase order|purchase|purchasing|sourcing|supplier|vendor|supply chain|inventory|oracle|wms|excel|logistics|reconciliation|rebates|erp|sap",
    102: "fixed asset|depreciation|general ledger|accounting|reconciliation|finance|financial reporting|accounts|capex|capitalization|oracle fusion|oracle|blackline|power bi|excel|month-end|ifrs|audit",
    103: "accounts receivable|cash application|order to cash|o2c|invoice|reconciliation|ar|accounting|finance|accounts|oracle|highradius|excel|ageing|unapplied|bfsi|collection",
    104: "procurement|purchase order|purchase|purchasing|sourcing|supplier|vendor|supply chain|operations|inventory|oracle|wms|excel|logistics|reconciliation|erp|sap|warehouse",
}

for jd in d["jds"]:
    if jd["id"] in JD_SK:
        jd["sk"] = JD_SK[jd["id"]]
        print(f"Updated JD {jd['id']}: {jd['t']}")

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, separators=(",",":"))

print("Done!")
