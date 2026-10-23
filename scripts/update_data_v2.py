"""
update_data_v2.py - Fixed version with proper role-specific filtering for Hitachi.

Key fix: A candidate should only appear in a Hitachi JD if they have RELEVANT SKILLS for that role.
The base 20-point "meets requirements" score should NOT put every candidate in every JD.
"""
import json
import re
import shutil
import os

# Restore from pre-CGI-Hitachi backup to start fresh
shutil.copy('data/data.json.backup_pre_cgi_hitachi', 'data/data.json')
print('Restored from backup')

with open('data/data.json', encoding='utf-8') as f:
    d = json.load(f)

print('Companies:', d['cos'])
print('JDs:', len(d['jds']))
print()

GREEN, YELLOW = d['thr']

# ============================================================
# HELPERS
# ============================================================
def parse_exp_years(exp_str):
    if not exp_str:
        return 0
    e = str(exp_str).strip().lower()
    if e in ['fresher', 'freshers', 'fresh', '0', 'no experience', 'nil', 'n/a', '']:
        return 0
    m = re.search(r'(\d+)\s*year', e)
    if m:
        years = int(m.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        months = int(mm.group(1)) if mm else 0
        return years + months / 12
    m = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)', e)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    m = re.search(r'(\d+)\+\s*(?:years?|yrs?)', e)
    if m:
        return float(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)', e)
    if m:
        return float(m.group(1))
    m = re.search(r'^(\d+(?:\.\d+)?)$', e)
    if m:
        return float(m.group(1))
    m = re.search(r'(\d+(?:\.\d+)?)', e)
    if m:
        v = float(m.group(1))
        return v if v <= 50 else 0
    return 0

def is_btech(p):
    q = str(p.get('q', '')).lower()
    return any(x in q for x in ['b.e', 'be/', 'b.tech', 'btech', 'b tech', 'b.e.', 'engineering'])

def is_fresher(p):
    exp_yrs = parse_exp_years(p.get('e', ''))
    return exp_yrs <= 0.6

def is_visually_impaired(p):
    dt = str(p.get('dt', '')).lower()
    return any(x in dt for x in ['visual', 'blind', 'vision', 'visually', 'low vision'])
    # Note: "Low vision" should NOT be excluded - "visually impaired" is different from "low vision"
    # But since the requirement says "excluding visually impaired", low vision may be borderline
    # Let's be careful: exclude 'visually impaired' but not generic 'low vision' 
    # Actually, let's include all vision-related conditions per Hitachi policy
    # The field says "low vission" in at least one case - that IS a visual condition

def has_cv(p):
    return bool(str(p.get('cv', '')).strip())

def has_skills(p):
    sk = str(p.get('sk', '')).strip().lower()
    return sk and sk not in ['yes', 'no', 'na', 'n/a', '-', 'experience']

def get_combined(p):
    return (str(p.get('sk', '')) + ' ' + str(p.get('des', '')) + ' ' + str(p.get('role', '')) + ' ' + str(p.get('org', ''))).lower()

# ============================================================
# CGI Setup
# ============================================================
cgi_co_idx = len(d['cos'])
d['cos'].append('CGI')
print(f'Added CGI at index {cgi_co_idx}')

old_cgi_jids = [78, 79, 80]
cgi_jd_map = {
    78: {'t': 'AI Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    79: {'t': 'IT Support', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    80: {'t': '.NET Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
}
for jid, updates in cgi_jd_map.items():
    d['jds'][jid].update(updates)
    d['jds'][jid]['c'] = cgi_co_idx

# Get CGI candidate PIDs from original data
cgi_pids_orig = set()
for row in d['pl']:
    if row[0] in set(old_cgi_jids):
        cgi_pids_orig.add(row[1])

print(f'CGI candidates: {len(cgi_pids_orig)}')

# Remove old CGI pl entries
d['pl'] = [row for row in d['pl'] if row[0] not in set(old_cgi_jids)]

def score_cgi_candidate(p, role):
    """Score a CGI candidate. Returns (score, reason). Score 0 = disqualified."""
    if not is_btech(p):
        return 0, 'not B.E./B.Tech'
    if not is_fresher(p):
        return 0, 'experience exceeds 6 months'
    
    sk = get_combined(p)
    score = 30  # base for meeting requirements
    reasons = ['B.E./B.Tech qualification']
    
    if has_cv(p):
        score += 10
        reasons.append('has CV')
    
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc:
        score += 5
        reasons.append('Bangalore')
    
    if role == 'ai_fresher':
        kws = ['python', 'machine learning', 'ml', 'ai', 'artificial intelligence', 'deep learning',
               'dl', 'nlp', 'natural language', 'tensorflow', 'pytorch', 'scikit', 'pandas', 'numpy',
               'llm', 'generative', 'genai', 'langchain', 'rag', 'neural', 'cnn', 'transformers',
               'hugging face', 'data science', 'computer vision', 'openai', 'gemini', 'agentic',
               'langgraph', 'data analyst', 'big data', 'spark']
        matches = [kw for kw in kws if kw in sk]
        if len(matches) >= 5:
            score += 35; reasons.append(f'strong AI skills: {", ".join(matches[:4])}')
        elif len(matches) >= 3:
            score += 25; reasons.append(f'good AI skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 15; reasons.append(f'some AI skills: {", ".join(matches[:2])}')
        else:
            score += 5; reasons.append('B.E./B.Tech, limited AI skills listed')
    
    elif role == 'it_support':
        kws = ['networking', 'hardware', 'troubleshoot', 'helpdesk', 'active directory', 'windows',
               'linux', 'sql', 'python', 'java', 'c#', 'network', 'server', 'cloud', 'aws', 'azure',
               'system admin', 'it support', 'technical support', 'database', 'cisco', 'tcp/ip']
        matches = [kw for kw in kws if kw in sk]
        if len(matches) >= 4:
            score += 35; reasons.append(f'strong IT skills: {", ".join(matches[:4])}')
        elif len(matches) >= 2:
            score += 25; reasons.append(f'good IT skills: {", ".join(matches[:2])}')
        elif len(matches) >= 1:
            score += 15; reasons.append(f'some IT skills: {", ".join(matches[:2])}')
        else:
            score += 5; reasons.append('B.E./B.Tech, limited IT skills listed')
    
    elif role == 'net_fresher':
        net_kws = ['.net', 'dotnet', 'c#', 'asp.net', 'wpf', 'blazor', 'vb.net', '.net core', 'entity framework', 'ef core', 'maui']
        net_matches = [kw for kw in net_kws if kw in sk]
        if len(net_matches) >= 3:
            score += 40; reasons.append(f'strong .NET skills: {", ".join(net_matches[:3])}')
        elif len(net_matches) >= 1:
            score += 30; reasons.append(f'.NET skills: {", ".join(net_matches)}')
        else:
            # General programming
            gen_kws = ['python', 'java', 'javascript', 'react', 'sql', 'programming', 'developer', 'c++']
            gen = [kw for kw in gen_kws if kw in sk]
            if gen:
                score += 10; reasons.append(f'general programming skills: {", ".join(gen[:2])} (no .NET specific)')
            else:
                score += 2; reasons.append('B.E./B.Tech, no .NET or programming skills listed')
    
    return score, '; '.join(reasons)

# Score and assign CGI candidates
new_cgi_pl = []
for pid in sorted(cgi_pids_orig):
    p = d['people'][pid]
    
    scores = {}
    for jid_cgi, jd_info in [(78, 'ai_fresher'), (79, 'it_support'), (80, 'net_fresher')]:
        sc, rs = score_cgi_candidate(p, jd_info)
        scores[jid_cgi] = (sc, rs)
    
    # Only add to each JD where score > 0
    for jid_cgi, (sc, rs) in scores.items():
        if sc > 0:
            new_cgi_pl.append([jid_cgi, pid, sc, rs, False])

# Sort and dedupe per JD
from collections import defaultdict
cgi_by_jid = defaultdict(dict)
for entry in new_cgi_pl:
    jid, pid, sc, rs, pool = entry
    if pid not in cgi_by_jid[jid] or sc > cgi_by_jid[jid][pid][0]:
        cgi_by_jid[jid][pid] = (sc, rs)

final_cgi_pl = []
for jid_cgi in [78, 79, 80]:
    for pid, (sc, rs) in sorted(cgi_by_jid[jid_cgi].items(), key=lambda x: -x[1][0]):
        final_cgi_pl.append([jid_cgi, pid, sc, rs, False])
    count = len(cgi_by_jid[jid_cgi])
    print(f'CGI JD[{jid_cgi}] {d["jds"][jid_cgi]["t"]}: {count} candidates')

d['pl'].extend(final_cgi_pl)
print(f'Total new CGI pl entries: {len(final_cgi_pl)}')
print()

# ============================================================
# Hitachi Setup
# ============================================================
hitachi_co_idx = len(d['cos'])
d['cos'].append('Hitachi')
print(f'Added Hitachi at index {hitachi_co_idx}')

hitachi_jds_info = [
    # IT roles (7)
    {'t': 'Java Developer',            'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Full Stack Developer',      'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': '.NET Developer',            'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Agentic AI Professional',   'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Generative AI Professional','ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Software Developer',        'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Software Tester',           'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    # Non-IT roles (3)
    {'t': 'Finance',                   'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Human Resources (HR)',      'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Procurement',               'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
]

hitachi_jid_start = len(d['jds'])
hitachi_jid_map = {}
for i, jd_info in enumerate(hitachi_jds_info):
    new_jid = hitachi_jid_start + i
    d['jds'].append({'id': new_jid, 'c': hitachi_co_idx, **jd_info})
    hitachi_jid_map[jd_info['t']] = new_jid
    print(f'Added JD[{new_jid}]: {jd_info["t"]}')

print()

# Role keyword sets for Hitachi - candidates MUST match at least 1 keyword to be included
# (or have strong signals from role/designation field)
HITACHI_ROLE_KEYWORDS = {
    'Java Developer': {
        'required': [],  # No single keyword strictly required
        'skills': ['java', 'spring boot', 'spring', 'hibernate', 'j2ee', 'springboot', 'jpa',
                   'spring mvc', 'microservices', 'java developer', 'core java', 'jsp', 'struts',
                   'servlet', 'junit', 'maven', 'gradle', 'kafka', 'java backend'],
        'min_match': 1,  # Must have at least 1 skill keyword
    },
    'Full Stack Developer': {
        'required': [],
        'skills': ['full stack', 'fullstack', 'react', 'angular', 'vue', 'nodejs', 'node.js',
                   'javascript', 'typescript', 'next.js', 'nextjs', 'express', 'mongodb',
                   'django', 'flask', 'fastapi', 'rest api', 'restapi', 'graphql', 'html', 'css',
                   'bootstrap', 'tailwind', 'webpack', 'redux', 'full-stack'],
        'min_match': 1,
    },
    '.NET Developer': {
        'required': [],
        'skills': ['.net', 'dotnet', 'c#', 'asp.net', 'wpf', 'blazor', 'vb.net', '.net core',
                   'entity framework', 'ef core', 'maui', 'xamarin', 'net developer', 'net core',
                   'windows forms', 'winforms', 'net mvc'],
        'min_match': 1,
    },
    'Agentic AI Professional': {
        'required': [],
        'skills': ['agentic ai', 'ai agent', 'langchain', 'langgraph', 'langraph', 'llm', 'llms',
                   'rag', 'retrieval-augmented', 'multi-agent', 'crewai', 'autogen', 'agentic',
                   'agent framework', 'mcp', 'tool use', 'function calling', 'agent orchestr',
                   'agent workflow'],
        'min_match': 1,
    },
    'Generative AI Professional': {
        'required': [],
        'skills': ['generative ai', 'genai', 'gen ai', 'gpt', 'openai', 'gemini', 'llm', 'llms',
                   'prompt engineering', 'stable diffusion', 'huggingface', 'hugging face',
                   'transformers', 'fine-tuning', 'finetuning', 'langchain', 'vector database',
                   'vector store', 'embeddings', 'text generation', 'image generation',
                   'dall-e', 'midjourney', 'claude', 'anthropic', 'diffusion model'],
        'min_match': 1,
    },
    'Software Developer': {
        'required': [],
        'skills': ['software developer', 'software development', 'developer', 'python', 'java',
                   'c++', 'golang', 'ruby', 'php', 'programming', 'coding', 'git', 'agile',
                   'scrum', 'ci/cd', 'devops', 'sql', 'database', 'software engineer', 'sde',
                   'backend', 'frontend', 'api', 'microservices'],
        'min_match': 2,  # Must match 2+ for this broad role (to avoid everyone landing here)
    },
    'Software Tester': {
        'required': [],
        'skills': ['testing', 'qa', 'quality assurance', 'selenium', 'automation testing',
                   'manual testing', 'test plan', 'test case', 'jmeter', 'playwright', 'cypress',
                   'postman', 'api testing', 'performance testing', 'load testing', 'cucumber',
                   'bdd', 'testng', 'junit testing', 'appium', 'functional testing',
                   'regression testing', 'software tester', 'qe'],
        'min_match': 1,
    },
    'Finance': {
        'required': [],
        'skills': ['finance', 'accounting', 'financial', 'accounts', 'audit', 'gst', 'taxation',
                   'tds', 'ledger', 'balance sheet', 'ca', 'cpa', 'cfa', 'controller', 'reconciliation',
                   'tally', 'sap fi', 'sap co', 'accounts payable', 'accounts receivable',
                   'budgeting', 'forecasting', 'p&l', 'cost accounting', 'financial analysis',
                   'income tax', 'indirect tax', 'direct tax', 'treasury', 'bookkeeping'],
        'min_match': 1,
    },
    'Human Resources (HR)': {
        'required': [],
        'skills': ['hr', 'human resource', 'human resources', 'recruitment', 'talent acquisition',
                   'onboarding', 'payroll', 'hris', 'people ops', 'employee relations', 'training',
                   'learning and development', 'l&d', 'performance management', 'hrms', 'hcm',
                   'compensation and benefits', 'attrition', 'workforce planning', 'hr manager',
                   'hr executive', 'hr generalist', 'talent management'],
        'min_match': 1,
    },
    'Procurement': {
        'required': [],
        'skills': ['procurement', 'purchase', 'supply chain', 'sourcing', 'vendor management',
                   'supplier', 'inventory', 'logistics', 'warehouse', 'sap mm', 'sap wm',
                   'materials management', 'buying', 'contract management', 'rfq', 'rfp',
                   'strategic sourcing', 'category management', 'purchase executive',
                   'purchase officer', 'store', 'material planning'],
        'min_match': 1,
    },
}

def score_hitachi_candidate(p, role_title):
    """
    Score a Hitachi candidate. Returns (score, reason).
    Score 0 = disqualified (doesn't meet hard requirements or no skill match).
    """
    exp_yrs = parse_exp_years(p.get('e', ''))
    
    # HARD REQUIREMENT 1: > 1 year experience (EXPERIENCE IS A RED LINE)
    if exp_yrs <= 1:
        return 0, f'experience {exp_yrs:.1f}yr - does not meet >1yr requirement'
    
    # HARD REQUIREMENT 2: Not visually impaired
    if is_visually_impaired(p):
        return 0, 'visually impaired - excluded per Hitachi policy'
    
    sk = get_combined(p)
    role_config = HITACHI_ROLE_KEYWORDS[role_title]
    skill_keywords = role_config['skills']
    min_match = role_config['min_match']
    
    matches = [kw for kw in skill_keywords if kw in sk]
    
    # HARD REQUIREMENT 3: Must have at least min_match role-specific keywords
    if len(matches) < min_match:
        return 0, f'insufficient skill match for {role_title} (matched {len(matches)}/{min_match} required keywords)'
    
    # Base score for meeting ALL requirements
    score = 20
    reasons = []
    
    # Experience score
    if exp_yrs >= 10:
        score += 20; reasons.append(f'{exp_yrs:.0f}yr exp (senior)')
    elif exp_yrs >= 5:
        score += 15; reasons.append(f'{exp_yrs:.0f}yr exp')
    elif exp_yrs >= 3:
        score += 10; reasons.append(f'{exp_yrs:.0f}yr exp')
    elif exp_yrs >= 2:
        score += 8; reasons.append(f'{exp_yrs:.1f}yr exp')
    else:
        score += 5; reasons.append(f'{exp_yrs:.1f}yr exp (minimum)')
    
    # CV bonus
    if has_cv(p):
        score += 5; reasons.append('has CV')
    
    # Location bonus
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc:
        score += 5; reasons.append('Bangalore')
    
    # Skill match scoring
    if len(matches) >= 5:
        score += 35; reasons.append(f'expert skill match: {", ".join(matches[:5])}')
    elif len(matches) >= 3:
        score += 25; reasons.append(f'strong skill match: {", ".join(matches[:4])}')
    elif len(matches) >= 2:
        score += 18; reasons.append(f'good skill match: {", ".join(matches[:3])}')
    else:
        score += 10; reasons.append(f'skill match: {", ".join(matches)}')
    
    return score, '; '.join(reasons)

# Get all unique PIDs from pl
all_pids = set(row[1] for row in d['pl'])
print(f'Total unique PIDs in pl: {len(all_pids)}')

# Score all candidates for all Hitachi roles
print('Scoring candidates for Hitachi roles...')
new_hitachi_pl = []

for pid in sorted(all_pids):
    p = d['people'][pid]
    exp_yrs = parse_exp_years(p.get('e', ''))
    
    # Quick filter: skip freshers and visually impaired upfront
    if exp_yrs <= 1:
        continue
    if is_visually_impaired(p):
        continue
    
    for role_title, jid_hitachi in hitachi_jid_map.items():
        sc, rs = score_hitachi_candidate(p, role_title)
        if sc > 0:
            new_hitachi_pl.append([jid_hitachi, pid, sc, rs, False])

print(f'Total new Hitachi pl entries: {len(new_hitachi_pl)}')

# Sort by (jid, -score) and add to pl
new_hitachi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_hitachi_pl)
d['pl'].sort(key=lambda x: (x[0], -x[2]))

# ============================================================
# Report
# ============================================================
print()
print('=== FINAL STATE ===')
print('Companies:', d['cos'])
print('Total JDs:', len(d['jds']))
print('Total pl:', len(d['pl']))
print()
print('CGI JDs:')
for j in d['jds']:
    if d['cos'][j['c']] == 'CGI':
        count = sum(1 for row in d['pl'] if row[0] == j['id'])
        top = [d['people'][row[1]]['n'] for row in d['pl'] if row[0] == j['id']][:3]
        print(f"  [{j['id']}] {j['t']}: {count} candidates (top 3: {top})")
print()
print('Hitachi JDs:')
for j in d['jds']:
    if d['cos'][j['c']] == 'Hitachi':
        count = sum(1 for row in d['pl'] if row[0] == j['id'])
        top = [d['people'][row[1]]['n'] for row in d['pl'] if row[0] == j['id']][:3]
        print(f"  [{j['id']}] {j['t']}: {count} candidates (top 3: {top})")

# Save
with open('data/data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

print(f'\ndata.json saved! Size: {os.path.getsize("data/data.json") / 1024:.1f} KB')
