import json, openpyxl

# Read the master sheet for disability criteria in JDs
wb = openpyxl.load_workbook('Job Fair Master Sheet.xlsx')
print("Sheets:", wb.sheetnames)

ws = wb['JDs Overview ']
print("\nHeaders in JDs Overview:")
headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
for i, h in enumerate(headers):
    print(f"  Col {i}: {h}")

print("\nFirst 10 JD rows (all columns):")
for r in list(ws.iter_rows(min_row=2, max_row=12)):
    vals = [str(cell.value or '')[:50] for cell in r]
    for i, v in enumerate(vals):
        if v and v != 'None':
            print(f"  Col {i} ({headers[i]}): {v}")
    print("  ---")
