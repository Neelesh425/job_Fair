import json, re

d = json.load(open('data/data.json.backup_pre_cgi_hitachi', encoding='utf-8'))

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

def is_vi(p):
    return any(x in str(p.get('dt','')).lower() for x in ['visual','blind','visually'])

# Search for AI/agentic candidates with experience
agentic_broad = ['langchain', 'langgraph', 'llm', 'llms', 'rag', 'agent', 'agentic', 
                 'crewai', 'autogen', 'openai', 'generative', 'genai', 'gpt', 'bert',
                 'hugging face', 'huggingface', 'transformer', 'prompt']

print('=== Candidates with LLM/AI keywords AND >1yr exp ===')
found = []
seen = set()
for i, p in enumerate(d['people']):
    if i in seen: continue
    exp = parse_exp(p.get('e',''))
    if exp <= 1: continue
    if is_vi(p): continue
    sk = (str(p.get('sk','')) + ' ' + str(p.get('des','')) + ' ' + str(p.get('role',''))).lower()
    matches = [kw for kw in agentic_broad if kw in sk]
    if matches:
        seen.add(i)
        found.append((i, exp, p, matches))

found.sort(key=lambda x: -x[1])
print(f'Found {len(found)} candidates:')
for pid, exp, p, matches in found:
    print(f'PID={pid} {p["n"]} | Exp={p.get("e","")} ({exp:.1f}yr) | DT={p.get("dt","")}')
    print(f'  SK: {p.get("sk","")[:80]}')
    print(f'  Matches: {matches}')
    print()

# Also check HR
print()
print('=== HR Candidates ===')
hr_kws = ['hr', 'human resource', 'human resources', 'recruitment', 'talent acquisition', 
          'onboarding', 'payroll', 'employee relations', 'training']

hr_found = []
seen2 = set()
for i, p in enumerate(d['people']):
    if i in seen2: continue
    exp = parse_exp(p.get('e',''))
    if exp <= 1: continue
    if is_vi(p): continue
    sk = (str(p.get('sk','')) + ' ' + str(p.get('des','')) + ' ' + str(p.get('role','')) + ' ' + str(p.get('org',''))).lower()
    
    # For "hr", need word boundary to avoid "chrome", "archery", etc.
    hr_matches = []
    for kw in hr_kws:
        if kw == 'hr':
            if re.search(r'\bhr\b', sk):
                hr_matches.append('hr')
        elif kw in sk:
            hr_matches.append(kw)
    
    if hr_matches:
        seen2.add(i)
        hr_found.append((i, exp, p, hr_matches))

hr_found.sort(key=lambda x: -x[1])
print(f'Found {len(hr_found)} HR candidates:')
for pid, exp, p, matches in hr_found[:20]:
    print(f'PID={pid} {p["n"]} | Exp={p.get("e","")} ({exp:.1f}yr) | DT={p.get("dt","")}')
    print(f'  SK: {p.get("sk","")[:80]}')
    print(f'  Matches: {matches}')
    print()
