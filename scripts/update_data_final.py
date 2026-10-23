"""
update_data_final.py - Final version with:
- Correct keyword matching (word boundaries for short terms)
- Broader Agentic AI matching (includes "agent", "llm" etc as primary signals)
- "Low Vision" excluded from Hitachi per visual impairment policy
- GenAI broadened to include actual candidates 
- Proper CGI candidate sorting per JD
"""
import json
import re
import shutil
import os

# Restore from backup
shutil.copy('data/data.json.backup_pre_cgi_hitachi', 'data/data.json')

with open('data/data.json', encoding='utf-8') as f:
    d = json.load(f)

print('Loaded. Companies:', d['cos'])
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
    m = re.search(r'(\d+)\s*[-]\s*(\d+)\s*(?:years?|yrs?)', e)
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
    # E.g. "7 plus"
    m = re.search(r'(\d+(?:\.\d+)?)\s*plus', e)
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
    """Exclude visually impaired candidates from Hitachi (including low vision)."""
    dt = str(p.get('dt', '')).lower()
    return any(x in dt for x in ['visual', 'blind', 'visually', 'low vision', 'low visi'])

def has_cv(p):
    return bool(str(p.get('cv', '')).strip())

def get_text(p):
    """Get all relevant text for keyword matching, padded for word boundaries."""
    parts = [str(p.get('sk', '')), str(p.get('des', '')),
             str(p.get('role', '')), str(p.get('org', ''))]
    return ' ' + ' '.join(parts).lower() + ' '

def kw_in(text, kw):
    """Safe keyword match with word boundary protection for short terms."""
    kw = kw.lower()
    if len(kw) <= 4 and ' ' not in kw:
        # Use word boundary for short terms to avoid partial matches
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
    return kw in text

def count_matches(text, keywords):
    return [kw for kw in keywords if kw_in(text, kw)]

# ============================================================
# CGI COMPANY
# ============================================================
cgi_co_idx = len(d['cos'])
d['cos'].append('CGI')

old_cgi_jids = [78, 79, 80]
cgi_jd_defs = {
    78: {'t': 'AI Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    79: {'t': 'IT Support', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    80: {'t': '.NET Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
}
for jid, upd in cgi_jd_defs.items():
    d['jds'][jid].update(upd)
    d['jds'][jid]['c'] = cgi_co_idx

# Collect original CGI PIDs
cgi_pids = set()
for row in d['pl']:
    if row[0] in set(old_cgi_jids):
        cgi_pids.add(row[1])

d['pl'] = [row for row in d['pl'] if row[0] not in set(old_cgi_jids)]

AI_KWS = ['python', 'machine learning', 'ml', 'artificial intelligence', 'deep learning',
           'natural language processing', 'nlp', 'tensorflow', 'pytorch', 'scikit-learn',
           'scikit', 'pandas', 'numpy', 'langchain', 'llm', 'llms', 'generative ai',
           'gen ai', 'genai', 'rag pipeline', 'retrieval augmented', 'neural network',
           'hugging face', 'huggingface', 'data science', 'computer vision',
          'langgraph', 'agentic ai', 'large language model', 'gpt', 'gemini', 'bert',
          'transformer', 'fine-tuning', 'openai', 'ai model', 'ml model']
IT_KWS = ['networking', 'network administration', 'hardware support', 'troubleshoot',
           'helpdesk', 'active directory', 'windows server', 'linux administration',
           'sql server', 'it support', 'technical support', 'cloud computing', 'aws',
           'azure', 'system administrator', 'database administration', 'cisco', 'tcpip',
           'vpn', 'firewall', 'it infrastructure', 'python', 'java', 'sql', 'linux']
NET_MAIN_KWS = ['.net', 'dotnet', 'asp.net', 'wpf', 'blazor', 'vb.net', '.net core',
                'entity framework', 'ef core', 'xamarin', '.net maui', 'winforms', 'net mvc']
NET_CSHARP_KW = 'c#'
NET_GEN_KWS = ['java', 'javascript', 'python', 'react', 'sql', 'programming', 'developer']

def score_cgi(p, role):
    if not is_btech(p):
        return 0, 'not B.E./B.Tech'
    if not is_fresher(p):
        return 0, 'experience >6 months'
    
    txt = get_text(p)
    score = 30
    reasons = ['B.E./B.Tech']
    if has_cv(p): score += 10; reasons.append('has CV')
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc: score += 5; reasons.append('Bangalore')
    
    if role == 'ai':
        m = count_matches(txt, AI_KWS)
        if len(m) >= 5: score += 35; reasons.append('expert AI: ' + ', '.join(m[:5]))
        elif len(m) >= 3: score += 25; reasons.append('strong AI: ' + ', '.join(m[:3]))
        elif len(m) >= 1: score += 15; reasons.append('AI skills: ' + ', '.join(m[:2]))
        else: score += 3; reasons.append('limited AI skills listed')
    
    elif role == 'it':
        m = count_matches(txt, IT_KWS)
        if len(m) >= 4: score += 35; reasons.append('expert IT: ' + ', '.join(m[:4]))
        elif len(m) >= 2: score += 25; reasons.append('IT skills: ' + ', '.join(m[:2]))
        elif len(m) >= 1: score += 15; reasons.append('IT: ' + ', '.join(m))
        else: score += 3; reasons.append('limited IT skills listed')
    
    elif role == 'net':
        main_m = count_matches(txt, NET_MAIN_KWS)
        has_cs = kw_in(txt, NET_CSHARP_KW)
        if has_cs: main_m.append('c#')
        if len(main_m) >= 2: score += 40; reasons.append('.NET expert: ' + ', '.join(main_m[:3]))
        elif len(main_m) >= 1: score += 30; reasons.append('.NET skills: ' + ', '.join(main_m))
        else:
            gen = count_matches(txt, NET_GEN_KWS)
            if gen: score += 8; reasons.append('general programming: ' + ', '.join(gen[:2]))
            else: score += 2; reasons.append('no .NET skills listed')
    
    return score, '; '.join(reasons)

new_cgi_pl = []
for pid in sorted(cgi_pids):
    p = d['people'][pid]
    for jid_c, role in [(78, 'ai'), (79, 'it'), (80, 'net')]:
        sc, rs = score_cgi(p, role)
        if sc > 0:
            new_cgi_pl.append([jid_c, pid, sc, rs, False])

new_cgi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_cgi_pl)

print('\nCGI:')
for jid_c in [78, 79, 80]:
    cnt = sum(1 for r in new_cgi_pl if r[0] == jid_c)
    print(f'  JD[{jid_c}] {d["jds"][jid_c]["t"]}: {cnt} candidates')

# ============================================================
# HITACHI COMPANY
# ============================================================
hitachi_co_idx = len(d['cos'])
d['cos'].append('Hitachi')

hitachi_jds = [
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

h_jid_start = len(d['jds'])
h_jid_map = {}
for i, jd in enumerate(hitachi_jds):
    nid = h_jid_start + i
    d['jds'].append({'id': nid, 'c': hitachi_co_idx, **jd})
    h_jid_map[jd['t']] = nid

# Role scoring functions - return (score, reason) or (0, '') if not matching
def score_hitachi(p, role):
    exp = parse_exp_years(p.get('e', ''))
    
    # EXPERIENCE RED LINE: must be > 1 year
    if exp <= 1:
        return 0, ''
    
    # Visual impairment exclusion
    if is_visually_impaired(p):
        return 0, ''
    
    txt = get_text(p)
    score = 20  # base
    reasons = [f'{exp:.1f}yr exp']
    if has_cv(p): score += 5; reasons.append('has CV')
    loc = str(p.get('loc','')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc: score += 5; reasons.append('Bangalore')
    # Experience bonus
    if exp >= 10: score += 20; reasons.append('senior')
    elif exp >= 5: score += 15
    elif exp >= 3: score += 10
    elif exp >= 2: score += 8
    else: score += 5
    
    def skill_score(matches, label):
        n = len(matches)
        if n == 0: return 0, ''
        if n >= 5: s = 35; lbl = 'expert ' + label + ': ' + ', '.join(matches[:5])
        elif n >= 3: s = 25; lbl = 'strong ' + label + ': ' + ', '.join(matches[:4])
        elif n >= 2: s = 18; lbl = label + ': ' + ', '.join(matches[:3])
        else: s = 10; lbl = label + ': ' + ', '.join(matches)
        return s, lbl
    
    if role == 'Java Developer':
        kws = ['java', 'spring boot', 'spring mvc', 'spring framework', 'hibernate', 'j2ee', 'springboot',
               'jpa', 'microservices', 'java developer', 'core java', 'java backend', 'spring cloud',
               'java ee', 'java se', 'rest api with java']
        m = count_matches(txt, kws)
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'Java')
        score += ss; reasons.append(lbl)
    
    elif role == 'Full Stack Developer':
        kws = ['full stack', 'fullstack', 'full-stack', 'react', 'angular', 'vue',
               'nodejs', 'node.js', 'next.js', 'nextjs', 'javascript', 'typescript',
               'expressjs', 'express.js', 'mongodb', 'rest api', 'graphql',
               'django rest', 'fastapi', 'mern stack', 'mean stack', 'frontend developer',
               'backend developer', 'web developer']
        m = count_matches(txt, kws)
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'Full Stack')
        score += ss; reasons.append(lbl)
    
    elif role == '.NET Developer':
        kws = ['.net developer', '.net core', 'asp.net', 'dotnet', 'wpf', 'blazor',
               'vb.net', 'entity framework', 'ef core', 'xamarin', '.net framework',
               'net mvc', 'windows forms', '.net maui']
        m = count_matches(txt, kws)
        has_cs = kw_in(txt, 'c#')
        if has_cs: m.append('c#')
        if not m: return 0, ''
        ss, lbl = skill_score(m, '.NET')
        score += ss; reasons.append(lbl)
    
    elif role == 'Agentic AI Professional':
        # Broader: include anyone with LLM/Agent/AI-agent experience
        kws = ['agentic ai', 'ai agent', 'langchain', 'langgraph', 'langraph', 'multi-agent',
               'crewai', 'autogen', 'agent workflow', 'agent framework', 'autonomous agent',
               'rag pipeline', 'retrieval augmented generation', 'llm agent', 'ai pipeline',
               'tool calling', 'function calling', 'orchestration', 'ai orchestration',
               'ai-agents', 'ai agents']
        # Extra short-word matches
        extra = []
        for kw in ['mcp', 'rag', 'llm', 'llms']:
            if kw_in(txt, kw): extra.append(kw)
        m = count_matches(txt, kws) + extra
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'Agentic AI')
        score += ss; reasons.append(lbl)
    
    elif role == 'Generative AI Professional':
        kws = ['generative ai', 'gen ai', 'genai', 'prompt engineering', 'stable diffusion',
               'hugging face', 'huggingface', 'fine-tuning', 'finetuning', 'text generation',
               'image generation', 'midjourney', 'anthropic', 'foundational model',
               'text-to-image', 'diffusion model', 'rlhf', 'transformer model',
               'vector database', 'embedding model', 'large language model', 'llm finetuning',
               'ai tools', 'chatgpt', 'openai', 'gpt-4', 'gpt-3', 'gemini api', 'claude api']
        extra = []
        for kw in ['gpt', 'bert', 'llm', 'llms']:
            if kw_in(txt, kw): extra.append(kw)
        m = count_matches(txt, kws) + extra
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'GenAI')
        score += ss; reasons.append(lbl)
    
    elif role == 'Software Developer':
        kws = ['software developer', 'software engineer', 'application developer',
               'backend developer', 'frontend developer', 'web developer',
               'python developer', 'java developer', 'golang', 'ruby on rails',
               'devops engineer', 'microservices architecture', 'rest api development',
               'mobile developer', 'android developer', 'ios developer',
               'react developer', 'node developer', 'software development',
               'ci/cd pipeline', 'cloud developer']
        # Also match broad programming skills as secondary
        broad = ['python', 'java', 'sql', 'git', 'agile', 'scrum', 'api', 'database']
        m = count_matches(txt, kws)
        if not m:
            # Check broad - need at least 2 broad matches
            bm = count_matches(txt, broad)
            if len(bm) < 2: return 0, ''
            ss, lbl = skill_score(bm, 'Software Dev (general)')
            score += ss; reasons.append(lbl)
        else:
            bm = count_matches(txt, broad)
            all_m = m + [x for x in bm if x not in m]
            ss, lbl = skill_score(all_m, 'Software Dev')
            score += ss; reasons.append(lbl)
    
    elif role == 'Software Tester':
        kws = ['software testing', 'software tester', 'automation testing', 'manual testing',
               'quality assurance', 'test automation', 'selenium webdriver', 'test engineer',
               'qa engineer', 'qa analyst', 'jmeter', 'playwright', 'cypress',
               'api testing', 'performance testing', 'load testing', 'cucumber',
               'testng', 'appium', 'functional testing', 'regression testing', 'test plan',
               'test cases', 'defect tracking', 'qe engineer', 'testing tools']
        m = count_matches(txt, kws)
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'Testing')
        score += ss; reasons.append(lbl)
    
    elif role == 'Finance':
        kws = ['finance manager', 'financial analyst', 'financial controller', 'financial reporting',
               'accounts payable', 'accounts receivable', 'accounting', 'audit',
               'cost accounting', 'management accounting', 'budgeting', 'financial forecasting',
               'income tax', 'indirect tax', 'direct tax', 'treasury management', 'bookkeeping',
               'tally prime', 'tally erp', 'sap finance', 'sap fico', 'reconciliation',
               'balance sheet', 'p&l', 'payroll processing', 'financial modelling',
               'variance analysis', 'accounts executive', 'finance executive',
               'ledger management', 'journal entry', 'month-end closing']
        extra = []
        for kw in ['gst', 'tds', 'cfa']:
            if kw_in(txt, kw): extra.append(kw)
        m = count_matches(txt, kws) + extra
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'Finance')
        score += ss; reasons.append(lbl)
    
    elif role == 'Human Resources (HR)':
        kws = ['human resources', 'human resource', 'talent acquisition', 'hr manager',
               'hr executive', 'hr generalist', 'hr business partner', 'onboarding',
               'employee relations', 'performance management', 'learning and development',
               'compensation and benefits', 'workforce planning', 'talent management',
               'hr analytics', 'people operations', 'hrms', 'hris', 'hcm',
               'organizational development', 'employee engagement', 'attrition management',
               'payroll management', 'recruitment specialist', 'staffing']
        extra = []
        if kw_in(txt, 'hr'): extra.append('hr')
        m = count_matches(txt, kws) + extra
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'HR')
        score += ss; reasons.append(lbl)
    
    elif role == 'Procurement':
        kws = ['procurement manager', 'purchase manager', 'supply chain', 'strategic sourcing',
               'vendor management', 'supplier management', 'inventory management',
               'logistics management', 'warehouse management', 'purchase executive',
               'purchase officer', 'materials management', 'contract management',
               'category management', 'spend analysis', 'demand planning',
               'supplier negotiation', 'purchase order', 'bill of materials',
               'sourcing specialist', 'supply chain management', 'logistics coordinator']
        extra = []
        for kw in ['sap mm', 'sap wm', 'rfq', 'rfp']:
            if kw_in(txt, kw): extra.append(kw)
        m = count_matches(txt, kws) + extra
        if not m: return 0, ''
        ss, lbl = skill_score(m, 'Procurement')
        score += ss; reasons.append(lbl)
    
    return score, '; '.join(reasons)

# Match all candidates to Hitachi JDs
all_pids = set(row[1] for row in d['pl'])
new_hitachi_pl = []
h_counts = {rt: 0 for rt in h_jid_map}

for pid in sorted(all_pids):
    p = d['people'][pid]
    exp = parse_exp_years(p.get('e', ''))
    if exp <= 1: continue
    if is_visually_impaired(p): continue
    
    for role_t, jid_h in h_jid_map.items():
        sc, rs = score_hitachi(p, role_t)
        if sc > 0:
            new_hitachi_pl.append([jid_h, pid, sc, rs, False])
            h_counts[role_t] += 1

print('\nHitachi candidates per role:')
for rt, cnt in h_counts.items():
    print(f'  {rt}: {cnt}')

new_hitachi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_hitachi_pl)
d['pl'].sort(key=lambda x: (x[0], -x[2]))

# Save
with open('data/data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

print(f'\nSaved! Companies: {d["cos"]}')
print(f'Total JDs: {len(d["jds"])}, Total pl: {len(d["pl"])}')
print(f'File size: {os.path.getsize("data/data.json")/1024:.1f} KB')

# Quick verification
print('\n=== VERIFICATION ===')
for j in d['jds']:
    co = d['cos'][j['c']]
    if co in ['CGI', 'Hitachi']:
        cnt = sum(1 for r in d['pl'] if r[0] == j['id'])
        top3 = [d['people'][r[1]]['n'] for r in sorted([r for r in d['pl'] if r[0] == j['id']], key=lambda x: -x[2])[:3]]
        print(f'  [{j["id"]}] {co} | {j["t"]}: {cnt} candidates | Top: {top3}')
