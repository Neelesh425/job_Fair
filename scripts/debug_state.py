import json, re
from collections import defaultdict

d = json.load(open('data/data.json', encoding='utf-8'))

# Check CGI - see what's happening
print('=== CGI Analysis ===')
cgi_co_idx = d['cos'].index('CGI')
for j in d['jds']:
    if j['c'] == cgi_co_idx:
        rows = [(row[1], row[2], row[3]) for row in d['pl'] if row[0] == j['id']]
        rows.sort(key=lambda x: -x[1])
        print(f"\nJD[{j['id']}] {j['t']}: {len(rows)} candidates")
        print("Top 10:")
        for pid, sc, rs in rows[:10]:
            p = d['people'][pid]
            print(f"  PID={pid} Score={sc} {p['n']} | SK={p.get('sk','')[:50]} | Reason={rs[:60]}")

print()
print('=== Hitachi Agentic AI ===')
hitachi_co_idx = d['cos'].index('Hitachi')
for j in d['jds']:
    if j['c'] == hitachi_co_idx and 'Agentic' in j['t']:
        rows = [(row[1], row[2], row[3]) for row in d['pl'] if row[0] == j['id']]
        rows.sort(key=lambda x: -x[1])
        print(f"JD[{j['id']}] {j['t']}: {len(rows)} candidates")
        for pid, sc, rs in rows:
            p = d['people'][pid]
            print(f"  PID={pid} Score={sc} {p['n']} | SK={p.get('sk','')[:80]}")

print()
print('=== Hitachi Finance (top 10) ===')
for j in d['jds']:
    if j['c'] == hitachi_co_idx and j['t'] == 'Finance':
        rows = [(row[1], row[2], row[3]) for row in d['pl'] if row[0] == j['id']]
        rows.sort(key=lambda x: -x[1])
        print(f"JD[{j['id']}] {j['t']}: {len(rows)} candidates")
        for pid, sc, rs in rows[:10]:
            p = d['people'][pid]
            print(f"  PID={pid} Score={sc} {p['n']} | SK={p.get('sk','')[:60]} | Reason={rs[:80]}")
