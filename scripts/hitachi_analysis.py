import json
import re

d = json.load(open('data/data.json', encoding='utf-8'))

# Hitachi requirements:
# - More than 1 year of relevant experience
# - IT: Java Dev, Full Stack Dev, .NET Dev, Agentic AI, Gen AI, Software Dev, Software Tester
# - Non-IT: Finance, HR, Procurement
# - Open to candidates with disabilities EXCLUDING visually impaired
# - Must attend in-person in Bangalore on 30 Oct 2026

def parse_exp_years(exp_str):
    """Return approximate years of experience from string, or None if unknown."""
    if not exp_str:
        return None
    e = str(exp_str).strip().lower()
    
    # Common fresher terms
    if e in ['fresher', 'freshers', 'fresh', '0', 'no experience', 'nil', 'n/a', '']:
        return 0
    
    # "N Year(s) M Month(s)" format
    m = re.search(r'(\d+)\s*year', e)
    if m:
        years = int(m.group(1))
        months_m = re.search(r'(\d+)\s*month', e)
        months = int(months_m.group(1)) if months_m else 0
        return years + months / 12
    
    # "N-M years" format - take average
    m = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)', e)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    
    # "N+ years"
    m = re.search(r'(\d+)\+\s*(?:years?|yrs?)', e)
    if m:
        return float(m.group(1))
    
    # "N years"
    m = re.search(r'^(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)', e)
    if m:
        return float(m.group(1))
    
    # Just a number
    m = re.search(r'^(\d+(?:\.\d+)?)$', e)
    if m:
        return float(m.group(1))
    
    # "NYrs" format
    m = re.search(r'^(\d+(?:\.\d+)?)yrs?$', e)
    if m:
        return float(m.group(1))
    
    # Try extracting any number
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)', e)
    if m:
        return float(m.group(1))
    
    # Number only
    m = re.search(r'(\d+(?:\.\d+)?)', e)
    if m:
        return float(m.group(1))
    
    return None

def get_skills(p):
    return str(p.get('sk', '')).lower()

def get_role(p):
    return str(p.get('role', '')).lower() + ' ' + str(p.get('des', '')).lower()

def is_visually_impaired(p):
    dt = str(p.get('dt', '')).lower()
    return any(x in dt for x in ['visual', 'blind', 'vision', 'visually'])

def check_hitachi_role(p):
    """Return best-matching Hitachi IT or Non-IT role based on skills/experience."""
    sk = get_skills(p)
    role = get_role(p)
    combined = sk + ' ' + role
    
    roles = {
        # IT roles
        'Java Developer': ['java', 'spring boot', 'spring', 'hibernate', 'j2ee', 'springboot', 'jpa'],
        'Full Stack Developer': ['full stack', 'fullstack', 'react', 'angular', 'vue', 'nodejs', 'node.js', 'frontend', 'backend', 'html', 'css', 'javascript', 'typescript', 'next.js', 'nextjs'],
        '.NET Developer': ['.net', 'dotnet', 'c#', 'asp.net', 'wpf', 'blazor'],
        'Agentic AI Professional': ['agentic ai', 'ai agent', 'langchain', 'langgraph', 'langraph', 'llm', 'llms', 'rag', 'retrieval', 'agent', 'mcp', 'multi-agent', 'crewai', 'autogen'],
        'Generative AI Professional': ['generative ai', 'genai', 'gen ai', 'gpt', 'openai', 'gemini', 'llm', 'prompt engineering', 'stable diffusion', 'huggingface', 'hugging face', 'transformers', 'fine-tuning', 'langchain', 'vector'],
        'Software Developer': ['software developer', 'software development', 'python', 'java', 'c++', 'golang', 'ruby', 'php', 'developer'],
        'Software Tester': ['testing', 'qa', 'quality assurance', 'selenium', 'automation testing', 'manual testing', 'test', 'jira', 'bug'],
        # Non-IT roles
        'Finance': ['finance', 'accounting', 'financial', 'accounts', 'audit', 'gst', 'taxation', 'tds', 'ledger', 'balance sheet', 'ca', 'cpa', 'cfa', 'controller', 'reconciliation', 'procurement', 'purchase', 'payroll'],
        'Human Resources (HR)': ['hr', 'human resource', 'recruitment', 'talent acquisition', 'onboarding', 'payroll', 'hris', 'people ops', 'people operations', 'employee relations', 'training', 'learning and development'],
        'Procurement': ['procurement', 'purchase', 'supply chain', 'sourcing', 'vendor', 'supplier', 'inventory', 'logistics', 'warehouse'],
    }
    
    best_role = None
    best_score = 0
    
    for role_name, keywords in roles.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_role = role_name
    
    return best_role, best_score

# Find Hitachi-eligible candidates:
# 1. More than 1 year experience
# 2. Not visually impaired
# 3. Have relevant skills

print('=== HITACHI ELIGIBLE CANDIDATES ===')
print('Requirement: >1 year experience, not visually impaired')
print()

hitachi_candidates = []

# Search through all people (not just specific JDs)
# Look through pl entries to find candidates with good experience
already_seen = set()
for row in d['pl']:
    jid, pid, score, reason, is_pool = row
    if pid in already_seen:
        continue
    already_seen.add(pid)
    
    p = d['people'][pid]
    exp = parse_exp_years(p.get('e', ''))
    
    # Must have > 1 year experience
    if exp is None or exp <= 1:
        continue
    
    # Must not be visually impaired
    if is_visually_impaired(p):
        continue
    
    # Must have some skills
    sk = get_skills(p)
    
    # Find best matching Hitachi role
    hitachi_role, role_score = check_hitachi_role(p)
    
    hitachi_candidates.append({
        'pid': pid,
        'name': p.get('n', ''),
        'exp': exp,
        'exp_raw': p.get('e', ''),
        'loc': p.get('loc', ''),
        'sk': p.get('sk', ''),
        'q': p.get('q', ''),
        'dt': p.get('dt', ''),
        'dp': p.get('dp', ''),
        'org': p.get('org', ''),
        'des': p.get('des', ''),
        'hitachi_role': hitachi_role,
        'role_score': role_score,
        'jid': jid,
        'score': score,
        'cv': p.get('cv', ''),
    })

# Sort by role_score desc, then exp desc
hitachi_candidates.sort(key=lambda x: (-x['role_score'], -x['exp']))

print('Total eligible candidates:', len(hitachi_candidates))
print()

# Group by Hitachi role
from collections import defaultdict
by_role = defaultdict(list)
for c in hitachi_candidates:
    if c['hitachi_role']:
        by_role[c['hitachi_role']].append(c)
    else:
        by_role['Software Developer'].append(c)

print('=== BY ROLE ===')
for role, candidates in sorted(by_role.items()):
    print()
    print(f"--- {role} ({len(candidates)} candidates) ---")
    for c in candidates[:10]:
        print(f"  PID={c['pid']} {c['name']} | Exp={c['exp_raw']} ({c['exp']:.1f}yr) | Role score={c['role_score']}")
        print(f"    Skills: {c['sk'][:80]}")
        print(f"    Loc: {c['loc']} | DT: {c['dt']} | DP: {c['dp']}")
