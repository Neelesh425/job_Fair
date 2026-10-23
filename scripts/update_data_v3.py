"""
update_data_v3.py - Final correct version with word-boundary safe matching.
"""
import json
import re
import shutil
import os

# Restore from pre-CGI-Hitachi backup
shutil.copy('data/data.json.backup_pre_cgi_hitachi', 'data/data.json')
print('Restored from backup')

with open('data/data.json', encoding='utf-8') as f:
    d = json.load(f)

print('Companies:', d['cos'])
print('JDs:', len(d['jds']))
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
    return parse_exp_years(p.get('e', '')) <= 0.6

def is_visually_impaired(p):
    dt = str(p.get('dt', '')).lower()
    # Exclude visually impaired. "Low vision" is a visual condition per disability classification.
    return any(x in dt for x in ['visual', 'blind', 'visually', 'low vision', 'low visi'])

def has_cv(p):
    return bool(str(p.get('cv', '')).strip())

def get_combined(p):
    """Get combined text for keyword matching. Normalize to help with word-boundary searches."""
    parts = [
        str(p.get('sk', '')),
        str(p.get('des', '')),
        str(p.get('role', '')),
        str(p.get('org', '')),
    ]
    return ' ' + ' '.join(parts).lower() + ' '  # pad with spaces for word boundary matching

def kw_match(text, keyword):
    """
    Safe keyword match. For multi-word phrases, just use substring.
    For single short words (<=3 chars), use word boundary.
    For longer single words, use substring (they're specific enough).
    """
    kw = keyword.lower()
    txt = text.lower()
    
    if ' ' in kw:
        # Multi-word phrase: substring match is fine
        return kw in txt
    
    if len(kw) <= 3:
        # Short word: must be a whole word
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', txt))
    
    # Longer word (>3 chars): substring is safe enough for specificity
    return kw in txt

def count_kw_matches(text, keywords):
    return [kw for kw in keywords if kw_match(text, kw)]

# ============================================================
# CGI Company Setup
# ============================================================
cgi_co_idx = len(d['cos'])
d['cos'].append('CGI')
print(f'\nAdded CGI at index {cgi_co_idx}')

old_cgi_jids = [78, 79, 80]
cgi_jd_map = {
    78: {'t': 'AI Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    79: {'t': 'IT Support', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    80: {'t': '.NET Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
}
for jid, updates in cgi_jd_map.items():
    d['jds'][jid].update(updates)
    d['jds'][jid]['c'] = cgi_co_idx

# Get original CGI candidate PIDs
cgi_pids_orig = set()
for row in d['pl']:
    if row[0] in set(old_cgi_jids):
        cgi_pids_orig.add(row[1])
print(f'CGI candidates: {len(cgi_pids_orig)}')

# Remove old pl entries
d['pl'] = [row for row in d['pl'] if row[0] not in set(old_cgi_jids)]

# CGI scoring
AI_FRESHER_KWS = ['python', 'machine learning', 'ml', 'artificial intelligence', 'deep learning',
                  'nlp', 'natural language', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
                  'llm', 'llms', 'generative ai', 'genai', 'gen ai', 'langchain', 'rag pipeline',
                  'neural network', 'cnn', 'hugging face', 'data science', 'computer vision',
                  'openai api', 'gemini api', 'agentic', 'langgraph', 'data analyst',
                  'machine learning model', 'deep learning model', 'ai model', 'scikit']

IT_SUPPORT_KWS = ['networking', 'network administration', 'hardware', 'troubleshoot',
                  'helpdesk', 'help desk', 'active directory', 'windows server', 'linux',
                  'sql server', 'it support', 'technical support', 'cloud computing',
                  'aws', 'azure', 'system administrator', 'database administration',
                  'cisco', 'tcp/ip', 'vpn', 'firewall', 'it infrastructure']

NET_FRESHER_KWS = ['.net', 'dotnet', 'asp.net', 'wpf', 'blazor', 'vb.net', '.net core',
                   'entity framework', 'ef core', 'xamarin', '.net maui', 'windows forms',
                   'winforms', 'net mvc', 'net developer']
# Also general programming that could fit .NET role (C# / Java are close)
NET_GENERAL_KWS = ['c#', 'java', 'javascript', 'python', 'react', 'sql', 'programming', 'developer', 'c++']

def score_cgi(p, role):
    if not is_btech(p):
        return 0, 'not B.E./B.Tech'
    if not is_fresher(p):
        return 0, 'experience > 6 months'

    sk = get_combined(p)
    score = 30
    reasons = ['B.E./B.Tech qualification']

    if has_cv(p):
        score += 10
        reasons.append('has CV')

    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc:
        score += 5
        reasons.append('Bangalore location')

    if role == 'ai':
        matches = count_kw_matches(sk, AI_FRESHER_KWS)
        if len(matches) >= 5:
            score += 35; reasons.append(f'expert AI skills: {", ".join(matches[:5])}')
        elif len(matches) >= 3:
            score += 25; reasons.append(f'strong AI skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 15; reasons.append(f'some AI skills: {", ".join(matches[:2])}')
        else:
            score += 3; reasons.append('B.E./B.Tech but limited AI skills listed')

    elif role == 'it':
        matches = count_kw_matches(sk, IT_SUPPORT_KWS)
        if len(matches) >= 4:
            score += 35; reasons.append(f'expert IT skills: {", ".join(matches[:4])}')
        elif len(matches) >= 2:
            score += 25; reasons.append(f'strong IT skills: {", ".join(matches[:2])}')
        elif len(matches) >= 1:
            score += 15; reasons.append(f'IT skills: {", ".join(matches)}')
        else:
            # Fall back to general IT skills (python, java, etc. are relevant for IT support)
            gen = [kw for kw in ['python', 'java', 'sql', 'linux', 'database'] if kw_match(sk, kw)]
            if gen:
                score += 8; reasons.append(f'general IT skills: {", ".join(gen[:2])}')
            else:
                score += 3; reasons.append('B.E./B.Tech but limited IT skills listed')

    elif role == 'net':
        net_matches = count_kw_matches(sk, NET_FRESHER_KWS)
        if 'c#' in sk or kw_match(sk, 'c#'):
            net_matches.append('c#')
        if len(net_matches) >= 2:
            score += 40; reasons.append(f'strong .NET skills: {", ".join(net_matches[:3])}')
        elif len(net_matches) >= 1:
            score += 30; reasons.append(f'.NET skills: {", ".join(net_matches)}')
        elif kw_match(sk, 'c#'):
            score += 25; reasons.append('C# skills (relevant for .NET)')
        else:
            gen = count_kw_matches(sk, NET_GENERAL_KWS)
            if gen:
                score += 8; reasons.append(f'general programming: {", ".join(gen[:2])} (no .NET specific)')
            else:
                score += 2; reasons.append('B.E./B.Tech, no .NET skills listed')

    return score, '; '.join(reasons)

new_cgi_pl = []
for pid in sorted(cgi_pids_orig):
    p = d['people'][pid]
    for jid_cgi, role_key in [(78, 'ai'), (79, 'it'), (80, 'net')]:
        sc, rs = score_cgi(p, role_key)
        if sc > 0:
            new_cgi_pl.append([jid_cgi, pid, sc, rs, False])

new_cgi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_cgi_pl)

for jid_cgi in [78, 79, 80]:
    count = sum(1 for e in new_cgi_pl if e[0] == jid_cgi)
    print(f'CGI JD[{jid_cgi}] {d["jds"][jid_cgi]["t"]}: {count} candidates')
print(f'Total CGI pl entries: {len(new_cgi_pl)}')

# ============================================================
# Hitachi Company Setup
# ============================================================
hitachi_co_idx = len(d['cos'])
d['cos'].append('Hitachi')
print(f'\nAdded Hitachi at index {hitachi_co_idx}')

hitachi_jds_info = [
    {'t': 'Java Developer',             'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Full Stack Developer',       'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': '.NET Developer',             'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Agentic AI Professional',    'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Generative AI Professional', 'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Software Developer',         'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Software Tester',            'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Finance',                    'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Human Resources (HR)',       'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Procurement',               'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
]

hitachi_jid_start = len(d['jds'])
hitachi_jid_map = {}
for i, jd_info in enumerate(hitachi_jds_info):
    new_jid = hitachi_jid_start + i
    d['jds'].append({'id': new_jid, 'c': hitachi_co_idx, **jd_info})
    hitachi_jid_map[jd_info['t']] = new_jid

print('Hitachi JDs added:', list(hitachi_jid_map.keys()))
print()

# Hitachi role keyword sets - designed with word-boundary awareness
HITACHI_ROLES = {
    'Java Developer': {
        'keywords': ['java', 'spring boot', 'spring mvc', 'hibernate', 'j2ee', 'springboot', 'jpa',
                     'microservices', 'java developer', 'core java', 'jsp', 'struts',
                     'servlet', 'junit', 'java backend', 'spring framework', 'spring cloud'],
        'min_match': 1,
    },
    'Full Stack Developer': {
        'keywords': ['full stack', 'fullstack', 'full-stack', 'react.js', 'react js', 'reactjs', 
                     'angular', 'angular js', 'vue.js', 'vuejs', 'node.js', 'nodejs', 'next.js', 'nextjs',
                     'javascript', 'typescript', 'express.js', 'expressjs', 'mongodb', 'rest api',
                     'graphql', 'django rest', 'flask api', 'fastapi', 'frontend backend',
                     'frontend developer', 'backend developer', 'mern', 'mean stack'],
        'min_match': 1,
    },
    '.NET Developer': {
        'keywords': ['.net developer', '.net core', 'asp.net', 'dotnet', 'wpf', 'blazor',
                     'vb.net', 'entity framework', 'ef core', 'xamarin', '.net maui',
                     'windows forms', 'winforms', 'net mvc', 'c# developer', '.net framework'],
        'extra_kws': ['c#'],  # c# matched with word boundary
        'min_match': 1,
    },
    'Agentic AI Professional': {
        'keywords': ['agentic ai', 'ai agent', 'langchain', 'langgraph', 'langraph', 'multi-agent',
                     'crewai', 'autogen', 'agent framework', 'agent workflow', 'agent orchestr',
                     'function calling', 'tool use', 'agentic workflow', 'autonomous agent',
                     'ai orchestration', 'retrieval augmented generation', 'rag pipeline',
                     'llm agent', 'ai pipeline'],
        'extra_kws': ['mcp'],  # model context protocol - short word, needs boundary matching
        'min_match': 1,
    },
    'Generative AI Professional': {
        'keywords': ['generative ai', 'genai', 'gen ai', 'gpt-4', 'gpt-3', 'openai', 'gemini api',
                     'prompt engineering', 'stable diffusion', 'hugging face', 'huggingface',
                     'fine-tuning', 'finetuning', 'text generation', 'image generation',
                     'diffusion model', 'midjourney', 'dall-e', 'claude api', 'anthropic',
                     'llm fine-tuning', 'rlhf', 'vector database', 'embedding model',
                     'transformer model', 'bert', 'gpt model', 'foundational model'],
        'extra_kws': ['llm', 'llms'],  # matched individually  
        'min_match': 1,
    },
    'Software Developer': {
        'keywords': ['software developer', 'software engineer', 'sde', 'software development',
                     'full stack developer', 'backend developer', 'frontend developer',
                     'python developer', 'java developer', 'golang', 'ruby on rails',
                     'ci/cd pipeline', 'devops engineer', 'agile development', 'scrum',
                     'microservices architecture', 'rest api development', 'api developer',
                     'application developer', 'web developer', 'mobile developer',
                     'android developer', 'ios developer', 'react developer', 'node developer'],
        'extra_kws': [],
        'min_match': 1,
    },
    'Software Tester': {
        'keywords': ['software testing', 'software tester', 'automation testing', 'manual testing',
                     'quality assurance', 'test automation', 'selenium webdriver', 'test engineer',
                     'qa engineer', 'qa analyst', 'jmeter', 'playwright', 'cypress',
                     'postman api', 'api testing', 'performance testing', 'load testing',
                     'cucumber bdd', 'testng', 'appium', 'functional testing',
                     'regression testing', 'test plan', 'test cases', 'defect tracking',
                     'bug tracking', 'qe engineer'],
        'extra_kws': [],
        'min_match': 1,
    },
    'Finance': {
        'keywords': ['finance manager', 'financial analyst', 'financial controller', 'financial reporting',
                     'accounts payable', 'accounts receivable', 'account executive', 'accounting',
                     'audit', 'financial audit', 'cost accounting', 'management accounting',
                     'budgeting', 'financial forecasting', 'tax planning', 'income tax',
                     'indirect tax', 'direct tax', 'treasury management', 'bookkeeping',
                     'tally prime', 'tally erp', 'sap finance', 'sap fico', 'sap fi', 'sap co',
                     'reconciliation', 'ledger', 'balance sheet', 'profit loss', 'p&l',
                     'payroll processing', 'gst filing', 'tds calculation',
                     'financial modelling', 'financial model', 'variance analysis'],
        'extra_kws': ['gst', 'tds', 'cfa'],  # short specific terms
        'min_match': 1,
    },
    'Human Resources (HR)': {
        'keywords': ['human resources', 'talent acquisition', 'recruitment specialist',
                     'hr manager', 'hr executive', 'hr generalist', 'hr business partner',
                     'onboarding', 'employee relations', 'performance management',
                     'learning and development', 'compensation and benefits', 'workforce planning',
                     'organizational development', 'employee engagement', 'hris', 'hrms', 'hcm',
                     'succession planning', 'attrition management', 'talent management',
                     'hr analytics', 'people operations', 'people ops'],
        'extra_kws': [],
        'min_match': 1,
    },
    'Procurement': {
        'keywords': ['procurement manager', 'purchase manager', 'supply chain', 'strategic sourcing',
                     'vendor management', 'supplier management', 'inventory management',
                     'logistics management', 'warehouse management', 'sap materials management',
                     'purchase executive', 'purchase officer', 'materials management',
                     'contract management', 'category management', 'spend analysis',
                     'procurement analytics', 'demand planning', 'supplier negotiation',
                     'rfq', 'rfp', 'purchase order', 'bill of materials'],
        'extra_kws': ['sap mm', 'sap wm'],
        'min_match': 1,
    },
}

def score_hitachi(p, role_title):
    exp_yrs = parse_exp_years(p.get('e', ''))
    
    # HARD REQUIREMENT 1: > 1 year exp (RED LINE)
    if exp_yrs <= 1:
        return 0, ''
    
    # HARD REQUIREMENT 2: Not visually impaired
    if is_visually_impaired(p):
        return 0, ''
    
    sk = get_combined(p)
    config = HITACHI_ROLES[role_title]
    
    # Check role-specific keyword matches
    matches = count_kw_matches(sk, config['keywords'])
    
    # Check extra keywords (short words needing boundary matching)
    extra_matches = []
    for kw in config.get('extra_kws', []):
        if kw_match(sk, kw):
            extra_matches.append(kw)
    
    all_matches = matches + extra_matches
    
    # HARD REQUIREMENT 3: Must have at least min_match skill keywords
    if len(all_matches) < config['min_match']:
        return 0, ''
    
    # Build score
    score = 20  # base for meeting all hard requirements
    reasons = []
    
    # Experience scoring
    if exp_yrs >= 10:
        score += 20; reasons.append(f'{exp_yrs:.0f}yr exp')
    elif exp_yrs >= 5:
        score += 15; reasons.append(f'{exp_yrs:.0f}yr exp')
    elif exp_yrs >= 3:
        score += 10; reasons.append(f'{exp_yrs:.0f}yr exp')
    elif exp_yrs >= 2:
        score += 8; reasons.append(f'{exp_yrs:.1f}yr exp')
    else:
        score += 5; reasons.append(f'{exp_yrs:.1f}yr exp')
    
    if has_cv(p):
        score += 5; reasons.append('has CV')
    
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc:
        score += 5; reasons.append('Bangalore')
    
    # Skill match scoring
    n = len(all_matches)
    if n >= 5:
        score += 35; reasons.append(f'expert: {", ".join(all_matches[:5])}')
    elif n >= 3:
        score += 25; reasons.append(f'strong: {", ".join(all_matches[:4])}')
    elif n >= 2:
        score += 18; reasons.append(f'good: {", ".join(all_matches[:3])}')
    else:
        score += 10; reasons.append(f'match: {", ".join(all_matches)}')
    
    return score, '; '.join(reasons)

# Score all candidates for all Hitachi JDs
all_pids = set(row[1] for row in d['pl'])
print(f'Total unique PIDs: {len(all_pids)}')

new_hitachi_pl = []
hitachi_counts = {rt: 0 for rt in hitachi_jid_map}

for pid in sorted(all_pids):
    p = d['people'][pid]
    exp_yrs = parse_exp_years(p.get('e', ''))
    
    # Quick filter
    if exp_yrs <= 1:
        continue
    if is_visually_impaired(p):
        continue
    
    for role_title, jid_hitachi in hitachi_jid_map.items():
        sc, rs = score_hitachi(p, role_title)
        if sc > 0:
            new_hitachi_pl.append([jid_hitachi, pid, sc, rs, False])
            hitachi_counts[role_title] += 1

print(f'Total Hitachi pl entries: {len(new_hitachi_pl)}')
for rt, count in hitachi_counts.items():
    print(f'  {rt}: {count}')

new_hitachi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_hitachi_pl)
d['pl'].sort(key=lambda x: (x[0], -x[2]))

# ============================================================
# Save
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
        top_rows = sorted([(row[2], d['people'][row[1]]['n'], row[3]) for row in d['pl'] if row[0] == j['id']], key=lambda x: -x[0])[:3]
        print(f"  [{j['id']}] {j['t']}: {count} candidates")
        for sc, nm, rs in top_rows:
            print(f"    ★ {nm} (score {sc}): {rs[:70]}")

print()
print('Hitachi JDs:')
for j in d['jds']:
    if d['cos'][j['c']] == 'Hitachi':
        count = sum(1 for row in d['pl'] if row[0] == j['id'])
        top_rows = sorted([(row[2], d['people'][row[1]]['n'], row[3]) for row in d['pl'] if row[0] == j['id']], key=lambda x: -x[0])[:3]
        print(f"  [{j['id']}] {j['t']}: {count} candidates")
        for sc, nm, rs in top_rows:
            print(f"    ★ {nm} (score {sc}): {rs[:70]}")

with open('data/data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

print(f'\ndata.json saved! Size: {os.path.getsize("data/data.json") / 1024:.1f} KB')
