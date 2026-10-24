import sys
sys.stdout.reconfigure(encoding="utf-8")

HTML_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\public\index.html"

with open(HTML_PATH, "r", encoding="utf-8") as f:
    content = f.read()

OLD = "  if(/account|finance/i.test(t))qs.push({cat:'Role-Specific',q:'Describe your experience with financial reporting, accounting software, or ERP systems.'});\n  if(/plant|engineering|automation/i.test(t))qs.push({cat:'Role-Specific',q:'What experience do you have with plant operations, automation systems, or industrial equipment?'});\n  return qs;\n}"

NEW = """  if(/account|finance/i.test(t))qs.push({cat:'Role-Specific',q:'Describe your experience with financial reporting, accounting software, or ERP systems.'});
  if(/plant|engineering|automation/i.test(t))qs.push({cat:'Role-Specific',q:'What experience do you have with plant operations, automation systems, or industrial equipment?'});
  if(/procurement|buyer|purchase/i.test(t))qs.push({cat:'Role-Specific',q:'Describe your experience managing purchase orders, supplier coordination and procurement operations. Which ERP systems (SAP, Oracle PO) have you used?'},{cat:'Role-Specific',q:'How do you handle supplier rebates, inventory valuation and WMS/ERP reconciliation?'});
  if(/fixed asset|asset accountant/i.test(t))qs.push({cat:'Role-Specific',q:'Walk us through your experience with fixed asset accounting: capitalization, depreciation, and asset reconciliation. Have you used Oracle Fusion Financials or BlackLine?'},{cat:'Role-Specific',q:'How do you handle month-end closing for fixed assets and what Power BI reports have you built?'});
  if(/cash application|accounts receivable|receivable/i.test(t))qs.push({cat:'Role-Specific',q:'Describe your Order-to-Cash (O2C) experience — how do you handle unapplied cash, invoice reconciliation, and customer query management?'},{cat:'Role-Specific',q:'Which cash application tools have you used: Oracle, HighRadius, APRO, or similar? How do you produce customer ageing reports?'});
  if(/full stack|fullstack/i.test(t))qs.push({cat:'Role-Specific',q:'Describe a full-stack project where you used React.js and Node.js/Express.js. How did you structure the PostgreSQL schema and REST APIs?'},{cat:'Role-Specific',q:'How do you approach CI/CD pipelines, production support, and database optimization in your current/previous role?'});
  return qs;
}"""

assert OLD in content, "OLD marker not found in file!"
out = content.replace(OLD, NEW, 1)
assert len(out) > len(content), "Content should have grown"

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(out)

# Verify
with open(HTML_PATH, "r", encoding="utf-8") as f:
    v = f.read()
assert "procurement|buyer|purchase" in v
assert "cash application|accounts receivable" in v
assert "fixed asset|asset accountant" in v
assert "full stack|fullstack" in v
print(f"Done! File is {len(v)} bytes. All checks passed.")
