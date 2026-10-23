import json, re

d = json.load(open('data/data.json', encoding='utf-8'))

# Check why Thanvi Uthappa is in Agentic AI
for j in d['jds']:
    if j.get('t') == 'Agentic AI Professional':
        jid = j['id']
        break

rows = [(row[1], row[2], row[3]) for row in d['pl'] if row[0] == jid]
print('Agentic AI candidates:')
for pid, sc, rs in rows:
    p = d['people'][pid]
    print(f'PID={pid} {p["n"]} | Exp={p.get("e","")} | SK={p.get("sk","")}')
    print(f'  Reason: {rs}')
    print()

# Now check people with agentic AI skills in the candidate pool
print()
print('=== Looking for agentic AI candidates in entire pool ===')
agentic_kws = ['agentic', 'ai agent', 'langchain', 'langgraph', 'langraph', 'llm', 'llms',
               'rag', 'retrieval-augmented', 'multi-agent', 'crewai', 'autogen', 'mcp',
               'agent framework']

def parse_exp(e):
    if not e: return 0
    e = str(e).strip().lower()
    if e in ['fresher','freshers','0','']: return 0
    m = re.search(r'(\d+)\s*year', e)
    if m:
        years = int(m.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        return years + (int(mm.group(1)) if mm else 0) / 12
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:yr|yrs)', e)
    if m: return float(m.group(1))
    m = re.search(r'^(\d+(?:\.\d+)?)$', e)
    if m: return float(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)', e)
    if m:
        v = float(m.group(1))
        return v if v <= 50 else 0
    return 0

found = []
for i, p in enumerate(d['people']):
    sk = (str(p.get('sk','')) + ' ' + str(p.get('des','')) + ' ' + str(p.get('role',''))).lower()
    exp_yrs = parse_exp(p.get('e',''))
    matches = [kw for kw in agentic_kws if kw in sk]
    if matches and exp_yrs > 1:
        vi = any(x in str(p.get('dt','')).lower() for x in ['visual','blind','vision'])
        if not vi:
            found.append((i, exp_yrs, p, matches))

print(f'Found {len(found)} candidates with agentic AI skills and >1yr exp:')
for pid, exp_yrs, p, matches in found:
    print(f'  PID={pid} {p["n"]} | Exp={p.get("e","")} ({exp_yrs:.1f}yr) | Matches: {matches}')
    print(f'    SK: {p.get("sk","")[:80]}')
