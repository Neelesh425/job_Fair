"""
fix_matching.py - Complete rewrite of CGI and Hitachi matching logic.

KEY FIXES:
1. CGI: Each candidate assigned to PRIMARY role only (best match). 
   Secondary assignment only if they explicitly have .NET skills for .NET, or 
   specific IT support certs for IT support, etc.
   
2. Hitachi experience parsing FIXED: "6 month" was being parsed as 6yr. Must enforce >1yr strictly.

3. Hitachi IT vs Non-IT separation: Non-IT domain candidates cannot appear in IT JDs.

4. Stricter role-specific matching: candidates must have ROLE-DEFINING skills.
   - Java Developer: must have java + spring/hibernate/jpa or java developer explicitly
   - Full Stack: must have frontend + backend combo, or explicit fullstack terms
   - .NET: must have .net/.net core/asp.net/c#
   - Agentic AI: must have explicit agentic/agent/langchain/langgraph etc
   - GenAI: must have generative ai / llm / prompt engineering explicitly
   - Software Developer: must have explicit "software developer/engineer" title or 3+ tech stack keywords
   - Software Tester: must have explicit testing keywords
   - Finance: must have finance-specific domain keywords
   - HR: must have HR-specific keywords (hr word boundary, recruitment, talent)
   - Procurement: must have procurement/purchase/supply chain explicitly

5. Visual impairment strict exclusion for Hitachi (including Low Vision).

6. Experience STRICT: "6 month", "6 months intern" = 0.5yr = EXCLUDED from Hitachi.
"""

import json, re, shutil, os
from collections import defaultdict

# Restore to pre-CGI-Hitachi clean state
shutil.copy('data/data.json.backup_pre_cgi_hitachi', 'data/data.json')
with open('data/data.json', encoding='utf-8') as f:
    d = json.load(f)
print('Loaded from backup. Companies:', d['cos'])
print('JDs:', len(d['jds']))

GREEN, YELLOW = d['thr']

# ============================================================
# STRICT EXP PARSER — fixes "6 month" being misread as 6yr
# ============================================================
def parse_exp_strict(exp_str):
    """
    Strictly parse experience years. Returns float.
    Edge cases:
    - "6 month" -> 0.5
    - "6 months intern" -> 0.5
    - "6 Months intern" -> 0.5
    - "1-3 years" -> 2.0 (average)
    - "Fresher" -> 0.0
    - "" -> 0.0
    """
    if not exp_str:
        return 0.0
    e = str(exp_str).strip().lower()
    
    # Explicit fresher
    if re.match(r'^(fresher|freshers|fresh|no experience|nil|n/a|0|na)$', e):
        return 0.0
    
    # "N Year(s) M Month(s)" e.g. "2 Year(s) 6 Month(s)"
    m = re.match(r'(\d+)\s*year[s]?\s*\(?[s]?\)?\s*(\d+)?\s*month[s]?\s*\(?[s]?\)?', e)
    if m:
        years = int(m.group(1))
        months = int(m.group(2)) if m.group(2) else 0
        return years + months / 12.0

    # "N+ years" or "N plus"
    m = re.search(r'(\d+)\s*\+\s*(?:years?|yrs?)', e)
    if m:
        return float(m.group(1))
    
    # "More than N year/yr"
    m = re.search(r'more\s+than\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', e)
    if m:
        return float(m.group(1)) + 0.5

    # "N-M years" or "N–M years"
    m = re.search(r'(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', e)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2.0

    # "N.M years" or "NYrs" e.g. "3.5 years", "4Yrs"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)', e)
    if m:
        return float(m.group(1))

    # MONTHS ONLY — must check before bare number to avoid "6 months" -> 6
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:months?|mos?)', e)
    if m:
        return float(m.group(1)) / 12.0

    # Bare number only (e.g. "3", "4", "2.5") — interpret as years
    m = re.match(r'^(\d+(?:\.\d+)?)$', e)
    if m:
        v = float(m.group(1))
        return v if v <= 50 else 0.0

    # "N yrs" at start
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(?:yrs?|year)', e)
    if m:
        return float(m.group(1))

    # Fallback: find first plausible number
    nums = re.findall(r'\d+(?:\.\d+)?', e)
    for num_str in nums:
        v = float(num_str)
        if 0 <= v <= 50:
            # If "month" appears before the number in original string, interpret as months
            idx = e.find(num_str)
            before = e[:idx]
            after = e[idx+len(num_str):]
            if re.search(r'month', after[:20]):
                return v / 12.0
            return v
    return 0.0

def is_vi(p):
    """Exclude visually impaired (including low vision) per Hitachi policy."""
    dt = str(p.get('dt', '')).lower()
    return bool(re.search(r'visual|blind|visually|low\s*vis', dt))

def is_btech(p):
    q = str(p.get('q', '')).lower()
    return bool(re.search(r'b\.e|b\.tech|btech|b tech|engineering|be/', q))

def is_fresher(p):
    return parse_exp_strict(p.get('e', '')) <= 0.6

def has_cv(p):
    return bool(str(p.get('cv', '')).strip())

def get_text(p):
    """Combined text from skills, designation, role, org. Padded for word-boundary searches."""
    parts = [
        str(p.get('sk', '')),
        str(p.get('des', '')),
        str(p.get('role', '')),
        str(p.get('org', '')),
    ]
    return ' ' + ' '.join(parts).lower() + ' '

def kwb(text, kw):
    """Keyword match. Word-boundary for short words (<= 4 chars)."""
    kw = kw.lower()
    if len(kw) <= 4 and ' ' not in kw:
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))
    return kw in text

def count_kw(text, kws):
    return [kw for kw in kws if kwb(text, kw)]

# ============================================================
# CGI SETUP
# ============================================================
cgi_co_idx = len(d['cos'])
d['cos'].append('CGI')

old_cgi_jids = [78, 79, 80]
cgi_jd_defs = {
    78: {'t': 'AI Fresher',   'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    79: {'t': 'IT Support',   'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    80: {'t': '.NET Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
}
for jid, upd in cgi_jd_defs.items():
    d['jds'][jid].update(upd)
    d['jds'][jid]['c'] = cgi_co_idx

# Collect original CGI PIDs
cgi_pids_orig = set()
for row in d['pl']:
    if row[0] in set(old_cgi_jids):
        cgi_pids_orig.add(row[1])

d['pl'] = [row for row in d['pl'] if row[0] not in set(old_cgi_jids)]

# ---- CGI Role Keyword Sets ----
CGI_AI_KWS = [
    'machine learning', 'deep learning', 'natural language processing', 'nlp',
    'tensorflow', 'pytorch', 'scikit-learn', 'scikit', 'pandas', 'numpy',
    'langchain', 'llm', 'llms', 'generative ai', 'gen ai', 'genai',
    'rag pipeline', 'retrieval augmented', 'neural network', 'hugging face',
    'huggingface', 'data science', 'computer vision', 'openai', 'gemini',
    'agentic ai', 'large language model', 'gpt', 'bert', 'transformer',
    'fine-tuning', 'ai model', 'ml model', 'artificial intelligence',
    'langgraph', 'langraph'
]
CGI_AI_ALSO = ['python']  # Python alone is a weak signal but valid for AI fresher

CGI_IT_KWS = [
    'networking', 'network administration', 'hardware support', 'troubleshoot',
    'helpdesk', 'help desk', 'active directory', 'windows server', 'linux',
    'sql server', 'it support', 'technical support', 'cloud computing',
    'system administrator', 'database administration', 'cisco', 'tcp/ip', 'vpn',
    'firewall', 'it infrastructure', 'network engineer', 'cloud engineer',
    'aws', 'azure', 'gcp'
]
CGI_IT_FALLBACK = ['python', 'java', 'sql', 'linux', 'database', 'c#']

CGI_NET_MAIN = [
    '.net', 'dotnet', 'asp.net', 'wpf', 'blazor', 'vb.net', '.net core',
    'entity framework', 'ef core', 'xamarin', '.net maui', 'winforms'
]
CGI_NET_CSHARP = 'c#'
CGI_NET_FALLBACK = ['java', 'javascript', 'python', 'react', 'sql', 'developer']

def score_cgi_role(p, role):
    """Score for a specific CGI role. Returns (score, reason)."""
    if not is_btech(p):
        return 0, 'not B.E./B.Tech'
    if not is_fresher(p):
        exp_yrs = parse_exp_strict(p.get('e', ''))
        return 0, f'experience {exp_yrs:.1f}yr > 6 months limit'

    txt = get_text(p)
    score = 30
    reasons = ['B.E./B.Tech']
    if has_cv(p): score += 10; reasons.append('has CV')
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc: score += 5; reasons.append('Bangalore')

    if role == 'ai':
        m = count_kw(txt, CGI_AI_KWS)
        if len(m) >= 5: score += 35; reasons.append('expert AI skills: ' + ', '.join(m[:5]))
        elif len(m) >= 3: score += 28; reasons.append('strong AI skills: ' + ', '.join(m[:3]))
        elif len(m) >= 1: score += 18; reasons.append('AI skills: ' + ', '.join(m[:2]))
        else:
            # Python alone is minimal for AI fresher
            if kwb(txt, 'python'): score += 8; reasons.append('Python (basic AI signal)')
            else: score += 2; reasons.append('no AI/ML skills listed')

    elif role == 'it':
        m = count_kw(txt, CGI_IT_KWS)
        if len(m) >= 4: score += 35; reasons.append('expert IT: ' + ', '.join(m[:4]))
        elif len(m) >= 2: score += 25; reasons.append('IT skills: ' + ', '.join(m[:2]))
        elif len(m) >= 1: score += 15; reasons.append('some IT: ' + ', '.join(m))
        else:
            fb = count_kw(txt, CGI_IT_FALLBACK)
            if len(fb) >= 2: score += 8; reasons.append('general IT: ' + ', '.join(fb[:2]))
            elif len(fb) >= 1: score += 4; reasons.append('weak IT signal: ' + ', '.join(fb))
            else: score += 2; reasons.append('no specific IT skills listed')

    elif role == 'net':
        nm = count_kw(txt, CGI_NET_MAIN)
        has_cs = kwb(txt, CGI_NET_CSHARP)
        if has_cs: nm.append('c#')
        if len(nm) >= 2: score += 40; reasons.append('.NET expert: ' + ', '.join(nm[:3]))
        elif len(nm) >= 1: score += 30; reasons.append('.NET skills: ' + ', '.join(nm))
        else:
            fb = count_kw(txt, CGI_NET_FALLBACK)
            if len(fb) >= 2: score += 8; reasons.append('general programming: ' + ', '.join(fb[:2]))
            elif len(fb) >= 1: score += 4; reasons.append('weak signal: ' + ', '.join(fb))
            else: score += 2; reasons.append('no .NET skills listed')

    return score, '; '.join(reasons)

# Score each CGI candidate for all 3 roles
# PRIMARY ASSIGNMENT: each candidate goes to ONE primary JD (best score)
# SECONDARY: only if they have explicit strong skills for another role
cgi_primary = {}      # pid -> (jid, score, reason)
cgi_secondary = {}    # pid -> [(jid, score, reason)]

role_map = [(78, 'ai'), (79, 'it'), (80, 'net')]

for pid in sorted(cgi_pids_orig):
    p = d['people'][pid]
    if not is_btech(p) or not is_fresher(p):
        continue  # skip entirely if doesn't meet hard requirements

    scores = {}
    for jid_c, role in role_map:
        sc, rs = score_cgi_role(p, role)
        if sc > 0:
            scores[jid_c] = (sc, rs)

    if not scores:
        continue

    # Primary: best scoring JD
    best_jid = max(scores.keys(), key=lambda j: scores[j][0])
    best_sc, best_rs = scores[best_jid]
    cgi_primary[pid] = (best_jid, best_sc, best_rs)

    # Secondary: other JDs where candidate has STRONG explicit skills
    txt = get_text(p)
    for jid_c, role in role_map:
        if jid_c == best_jid: continue
        sc, rs = scores.get(jid_c, (0, ''))
        if sc == 0: continue
        
        # Only add as secondary if they have STRONG explicit role-specific skills
        if role == 'net':
            nm = count_kw(txt, CGI_NET_MAIN)
            if kwb(txt, CGI_NET_CSHARP): nm.append('c#')
            if nm:  # explicit .NET skills -> add to .NET JD too
                if pid not in cgi_secondary: cgi_secondary[pid] = []
                cgi_secondary[pid].append((jid_c, sc, rs))
        elif role == 'it':
            if count_kw(txt, CGI_IT_KWS):  # explicit IT support skills
                if pid not in cgi_secondary: cgi_secondary[pid] = []
                cgi_secondary[pid].append((jid_c, sc, rs))
        elif role == 'ai':
            ai_m = count_kw(txt, CGI_AI_KWS)
            if len(ai_m) >= 2:  # explicit AI skills
                if pid not in cgi_secondary: cgi_secondary[pid] = []
                cgi_secondary[pid].append((jid_c, sc, rs))

# Build CGI pl entries
new_cgi_pl = []
# Primary assignments
for pid, (jid, sc, rs) in cgi_primary.items():
    new_cgi_pl.append([jid, pid, sc, rs, False])
# Secondary assignments
for pid, secondaries in cgi_secondary.items():
    for jid, sc, rs in secondaries:
        new_cgi_pl.append([jid, pid, sc, rs + ' [also qualified]', False])

new_cgi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_cgi_pl)

print()
print('CGI results:')
for jid_c in [78, 79, 80]:
    cnt = sum(1 for r in new_cgi_pl if r[0] == jid_c)
    top = [d['people'][r[1]]['n'] for r in new_cgi_pl if r[0] == jid_c][:3]
    print(f'  JD[{jid_c}] {d["jds"][jid_c]["t"]}: {cnt} candidates | top: {top}')

# ============================================================
# HITACHI SETUP
# ============================================================
hitachi_co_idx = len(d['cos'])
d['cos'].append('Hitachi')

hitachi_jds_def = [
    {'t': 'Java Developer',             'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Full Stack Developer',       'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': '.NET Developer',             'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Agentic AI Professional',    'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Generative AI Professional', 'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Software Developer',         'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Software Tester',            'ty': 'Tech',     'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Finance',                    'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Human Resources (HR)',       'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore'},
    {'t': 'Procurement',               'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore'},
]

h_jid_start = len(d['jds'])
h_jid_map = {}
for i, jd in enumerate(hitachi_jds_def):
    nid = h_jid_start + i
    d['jds'].append({'id': nid, 'c': hitachi_co_idx, 'u': '', **jd})
    h_jid_map[jd['t']] = nid

print()
print('Hitachi JDs:', {k: v for k, v in h_jid_map.items()})

# ============================================================
# HITACHI ROLE CLASSIFIERS
# ============================================================
# Each role has REQUIRED keywords — candidate must match at least 1.
# Additionally, IT candidates are blocked from Non-IT roles and vice versa.
# A candidate is classified as IT or Non-IT based on their primary domain.

def classify_candidate_domain(p):
    """
    Classify candidate as 'it', 'nonit', or 'both'.
    Based on strongest signal in skills/designation.
    """
    txt = get_text(p)
    
    # Strong IT indicators
    it_indicators = [
        'software developer', 'software engineer', 'web developer', 'backend developer',
        'frontend developer', 'java developer', 'python developer', 'full stack', 'fullstack',
        '.net developer', 'dotnet developer', 'mobile developer', 'android developer',
        'ios developer', 'devops engineer', 'cloud engineer', 'data engineer',
        'software tester', 'qa engineer', 'test engineer', 'automation engineer',
        'machine learning', 'deep learning', 'data scientist', 'ai engineer',
        'network engineer', 'system administrator', 'database administrator',
        'java', 'spring boot', 'react', 'angular', 'nodejs', 'python', 'c#', '.net',
        'asp.net', 'selenium', 'automation testing', 'manual testing',
        'langchain', 'llm', 'agentic ai', 'generative ai'
    ]
    
    # Strong Non-IT indicators
    nonit_indicators = [
        'accountant', 'accounting', 'accounts executive', 'finance executive',
        'finance manager', 'financial analyst', 'financial controller', 'audit',
        'tally', 'gst filing', 'taxation', 'accounts payable', 'accounts receivable',
        'bookkeeping', 'budget', 'reconciliation', 'ledger',
        'hr manager', 'hr executive', 'hr generalist', 'talent acquisition', 'recruitment',
        'human resources', 'payroll', 'employee relations', 'onboarding',
        'procurement manager', 'purchase manager', 'purchase executive', 'purchase officer',
        'supply chain', 'logistics', 'warehouse', 'vendor management', 'sourcing',
        'inventory management', 'materials management', 'procurement'
    ]
    
    it_score = sum(1 for kw in it_indicators if kwb(txt, kw))
    nonit_score = sum(1 for kw in nonit_indicators if kwb(txt, kw))
    
    if it_score > 0 and nonit_score == 0:
        return 'it'
    elif nonit_score > 0 and it_score == 0:
        return 'nonit'
    elif it_score > 0 and nonit_score > 0:
        return 'both'
    else:
        return 'unknown'

def score_hitachi_java(p):
    txt = get_text(p)
    # REQUIRED: explicit Java skills
    java_kws = [
        'java developer', 'java backend', 'core java', 'java ee', 'java se',
        'spring boot', 'spring mvc', 'spring framework', 'spring cloud',
        'hibernate', 'j2ee', 'jpa', 'springboot', 'java microservices',
        'java fullstack', 'java full stack'
    ]
    m = count_kw(txt, java_kws)
    # Also check bare "java" keyword with word boundary
    has_java = kwb(txt, 'java')
    
    if not m and not has_java:
        return 0, ''
    
    # If only bare "java" with no Java-specific framework — must have at least 2 java-related signals
    if not m and has_java:
        # Need at least one more Java signal
        extra_java = count_kw(txt, ['spring', 'hibernate', 'jpa', 'j2ee', 'servlet', 'jsp', 'maven', 'gradle', 'junit', 'java developer'])
        if not extra_java:
            return 0, ''
    
    return True, m

def score_hitachi_fullstack(p):
    txt = get_text(p)
    # Must have BOTH frontend and backend signals, or explicit "full stack" term
    fullstack_explicit = count_kw(txt, ['full stack', 'fullstack', 'full-stack', 'mern stack', 'mean stack', 'mern', 'mean'])
    frontend = count_kw(txt, ['react', 'angular', 'vue', 'reactjs', 'angularjs', 'vuejs', 'next.js', 'nextjs', 'html css', 'frontend developer'])
    backend = count_kw(txt, ['nodejs', 'node.js', 'expressjs', 'express.js', 'django', 'flask', 'fastapi', 'spring boot', 'backend developer'])
    
    if fullstack_explicit:
        return True, fullstack_explicit + frontend + backend
    if frontend and backend:
        return True, frontend + backend
    return False, []

def score_hitachi_net(p):
    txt = get_text(p)
    net_kws = [
        '.net developer', '.net core', 'asp.net', 'dotnet', 'wpf', 'blazor',
        'vb.net', 'entity framework', 'ef core', '.net framework', 'net mvc',
        '.net maui', 'windows forms'
    ]
    m = count_kw(txt, net_kws)
    has_cs = kwb(txt, 'c#')
    if has_cs: m.append('c#')
    if not m:
        return False, []
    return True, m

def score_hitachi_agentic(p):
    txt = get_text(p)
    agentic_kws = [
        'agentic ai', 'ai agent', 'langchain', 'langgraph', 'langraph', 'multi-agent',
        'crewai', 'autogen', 'agent workflow', 'agent framework', 'autonomous agent',
        'rag pipeline', 'retrieval augmented generation', 'llm agent', 'ai pipeline',
        'ai-agents', 'ai agents', 'agent orchestr', 'agentic workflow'
    ]
    short_kws = ['mcp']
    m = count_kw(txt, agentic_kws)
    for kw in short_kws:
        if kwb(txt, kw): m.append(kw)
    # Also check rag + llm combo
    has_rag = kwb(txt, 'rag')
    has_llm = kwb(txt, 'llm') or kwb(txt, 'llms')
    if has_rag and has_llm and not m:
        m = ['rag', 'llm']
    if not m:
        return False, []
    return True, m

def score_hitachi_genai(p):
    txt = get_text(p)
    genai_kws = [
        'generative ai', 'gen ai', 'genai', 'prompt engineering',
        'stable diffusion', 'hugging face', 'huggingface', 'fine-tuning', 'finetuning',
        'text generation', 'image generation', 'midjourney', 'anthropic',
        'foundational model', 'text-to-image', 'diffusion model', 'rlhf',
        'vector database', 'embedding model', 'large language model',
        'chatgpt', 'openai api', 'gpt-4', 'gpt-3', 'claude api', 'gemini api'
    ]
    short_kws = ['llm', 'llms', 'gpt', 'bert']
    m = count_kw(txt, genai_kws)
    for kw in short_kws:
        if kwb(txt, kw): m.append(kw)
    
    # "AI tools" alone is not sufficient — needs more specific
    if not m:
        return False, []
    
    # "chatgpt" alone is not enough — need at least one other signal
    if m == ['chatgpt']:
        return False, []
    
    return True, m

def score_hitachi_swdev(p):
    txt = get_text(p)
    # EXPLICIT software developer/engineer title OR strong tech stack
    explicit_title = count_kw(txt, [
        'software developer', 'software engineer', 'application developer',
        'web developer', 'mobile developer', 'android developer', 'ios developer',
        'sde', 'software development engineer', 'python developer',
        'backend developer', 'frontend developer', 'react developer',
        'node developer', 'devops engineer', 'cloud developer'
    ])
    
    if explicit_title:
        # Has explicit title — also check stack
        stack = count_kw(txt, ['python', 'java', 'git', 'sql', 'api', 'agile', 'scrum', 'docker', 'aws', 'azure', 'database', 'ci/cd'])
        return True, explicit_title + stack
    
    # No explicit title — need STRONG stack (3+ languages/frameworks)
    stack_kws = ['python', 'java', 'javascript', 'typescript', 'c++', 'golang', 'ruby', 'php', 'swift',
                 'git', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'sql', 'mongodb',
                 'rest api', 'microservices', 'agile', 'scrum', 'ci/cd', 'jenkins']
    stack_m = count_kw(txt, stack_kws)
    if len(stack_m) >= 4:
        return True, stack_m
    
    return False, []

def score_hitachi_tester(p):
    txt = get_text(p)
    tester_kws = [
        'software testing', 'software tester', 'automation testing', 'manual testing',
        'quality assurance', 'test automation', 'selenium webdriver', 'test engineer',
        'qa engineer', 'qa analyst', 'qe engineer', 'testing tools',
        'jmeter', 'playwright', 'cypress', 'api testing', 'performance testing',
        'load testing', 'cucumber', 'testng', 'appium', 'functional testing',
        'regression testing', 'test plan', 'test cases', 'defect tracking',
        'bug tracking', 'test management'
    ]
    m = count_kw(txt, tester_kws)
    if not m:
        return False, []
    return True, m

def score_hitachi_finance(p):
    txt = get_text(p)
    finance_kws = [
        'finance manager', 'financial analyst', 'financial controller', 'financial reporting',
        'accounts payable', 'accounts receivable', 'accounting', 'account executive',
        'audit', 'financial audit', 'cost accounting', 'management accounting',
        'budgeting', 'financial forecasting', 'income tax', 'indirect tax',
        'direct tax', 'treasury management', 'bookkeeping',
        'tally prime', 'tally erp', 'tally', 'sap finance', 'sap fico', 'sap fi',
        'reconciliation', 'ledger', 'balance sheet', 'p&l', 'payroll processing',
        'financial modelling', 'variance analysis', 'accounts executive',
        'finance executive', 'journal entry', 'month-end closing', 'invoice processing',
        'accounts assistant', 'finance associate', 'accounting software',
        'zoho books', 'quickbooks', 'busy accounting'
    ]
    short_kws = ['gst', 'tds', 'cfa']
    m = count_kw(txt, finance_kws)
    for kw in short_kws:
        if kwb(txt, kw): m.append(kw)
    
    if not m:
        return False, []
    return True, m

def score_hitachi_hr(p):
    txt = get_text(p)
    hr_kws = [
        'human resources', 'human resource', 'talent acquisition', 'hr manager',
        'hr executive', 'hr generalist', 'hr business partner', 'hr specialist',
        'onboarding', 'employee relations', 'performance management',
        'learning and development', 'compensation and benefits', 'workforce planning',
        'talent management', 'hr analytics', 'people operations', 'hrms', 'hris',
        'hcm', 'organizational development', 'employee engagement', 'attrition management',
        'payroll management', 'recruitment specialist', 'staffing coordinator',
        'hr coordinator', 'talent sourcing', 'campus recruitment', 'bulk hiring'
    ]
    m = count_kw(txt, hr_kws)
    # 'hr' with word boundary
    if kwb(txt, 'hr') and 'human resources' not in txt and 'hr manager' not in txt:
        # Check context — "hr" alone is weak, need something else
        if m:
            m.append('hr')
        elif count_kw(txt, ['recruitment', 'talent', 'payroll', 'employee', 'workforce']):
            m.append('hr (word boundary)')
    if not m:
        return False, []
    return True, m

def score_hitachi_procurement(p):
    txt = get_text(p)
    proc_kws = [
        'procurement manager', 'purchase manager', 'purchase executive', 'purchase officer',
        'strategic sourcing', 'vendor management', 'supplier management',
        'inventory management', 'logistics management', 'warehouse management',
        'materials management', 'contract management', 'category management',
        'spend analysis', 'demand planning', 'supplier negotiation', 'purchase order',
        'bill of materials', 'sourcing specialist', 'supply chain management',
        'logistics coordinator', 'supply chain', 'procurement', 'purchasing'
    ]
    short_kws = ['sap mm', 'sap wm', 'rfq', 'rfp']
    m = count_kw(txt, proc_kws)
    for kw in short_kws:
        if kwb(txt, kw): m.append(kw)
    if not m:
        return False, []
    return True, m

ROLE_SCORERS = {
    'Java Developer': score_hitachi_java,
    'Full Stack Developer': score_hitachi_fullstack,
    '.NET Developer': score_hitachi_net,
    'Agentic AI Professional': score_hitachi_agentic,
    'Generative AI Professional': score_hitachi_genai,
    'Software Developer': score_hitachi_swdev,
    'Software Tester': score_hitachi_tester,
    'Finance': score_hitachi_finance,
    'Human Resources (HR)': score_hitachi_hr,
    'Procurement': score_hitachi_procurement,
}

IT_ROLES = {'Java Developer', 'Full Stack Developer', '.NET Developer',
            'Agentic AI Professional', 'Generative AI Professional',
            'Software Developer', 'Software Tester'}
NONIT_ROLES = {'Finance', 'Human Resources (HR)', 'Procurement'}

def build_hitachi_score(p, role_title, skill_matches, exp_yrs):
    """Build final score given role qualification check passed."""
    score = 20  # base for meeting all hard requirements
    reasons = [f'{exp_yrs:.1f}yr exp']
    if has_cv(p): score += 5; reasons.append('CV')
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc: score += 5; reasons.append('Bangalore')
    
    if exp_yrs >= 10: score += 20; reasons.append('senior')
    elif exp_yrs >= 5: score += 15
    elif exp_yrs >= 3: score += 10
    elif exp_yrs >= 2: score += 8
    else: score += 5

    n = len(skill_matches)
    skill_str = ', '.join(skill_matches[:5])
    if n >= 5: score += 35; reasons.append(f'expert: {skill_str}')
    elif n >= 3: score += 25; reasons.append(f'strong: {skill_str}')
    elif n >= 2: score += 18; reasons.append(f'good: {skill_str}')
    else: score += 10; reasons.append(f'match: {skill_str}')

    return score, '; '.join(reasons)

# Match all candidates to Hitachi JDs
all_pids = set(row[1] for row in d['pl'])
print(f'Total unique PIDs: {len(all_pids)}')

new_hitachi_pl = []
h_counts = defaultdict(int)
h_violations = defaultdict(list)

for pid in sorted(all_pids):
    p = d['people'][pid]
    exp_yrs = parse_exp_strict(p.get('e', ''))

    # HARD GATE: >1 year experience (EXPERIENCE IS A RED LINE)
    if exp_yrs <= 1:
        continue
    
    # HARD GATE: Not visually impaired (Hitachi policy)
    if is_vi(p):
        continue
    
    # Classify candidate domain (IT vs Non-IT vs both)
    domain = classify_candidate_domain(p)
    
    for role_title, jid_h in h_jid_map.items():
        # IT candidates should NOT appear in Non-IT roles (and vice versa)
        # Exception: domain=='both' can appear in either
        if role_title in IT_ROLES and domain == 'nonit':
            continue  # Non-IT people can't appear in Java/Dev/Tester roles
        if role_title in NONIT_ROLES and domain == 'it':
            continue  # IT people can't appear in Finance/HR/Procurement
        
        # Check role-specific qualification
        scorer = ROLE_SCORERS[role_title]
        qualified, matches = scorer(p)
        if not qualified:
            continue
        
        sc, rs = build_hitachi_score(p, role_title, matches, exp_yrs)
        new_hitachi_pl.append([jid_h, pid, sc, rs, False])
        h_counts[role_title] += 1

print()
print('Hitachi candidates per role:')
total_h = 0
for rt, cnt in h_counts.items():
    print(f'  {rt}: {cnt}')
    total_h += cnt
print(f'Total Hitachi pl entries: {total_h}')

new_hitachi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_hitachi_pl)
d['pl'].sort(key=lambda x: (x[0], -x[2]))

# ============================================================
# Save & verify
# ============================================================
with open('data/data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

print()
print('Saved! Companies:', d['cos'])
print(f'Total JDs: {len(d["jds"])}, Total pl: {len(d["pl"])}')
print(f'File size: {os.path.getsize("data/data.json")/1024:.1f} KB')

print()
print('=== VERIFICATION ===')
for j in d['jds']:
    co = d['cos'][j['c']]
    if co in ['CGI', 'Hitachi']:
        rows = sorted([(r[2], d['people'][r[1]]['n'], r[3], d['people'][r[1]].get('e','')) for r in d['pl'] if r[0] == j['id']], key=lambda x: -x[0])
        cnt = len(rows)
        top3 = [(r[0], r[1], r[2][:50], r[3]) for r in rows[:3]]
        print(f'[{j["id"]}] {co} / {j["t"]}: {cnt} candidates')
        for sc, nm, rs, exp in top3:
            print(f'  Score={sc} {nm} | Exp={exp} | {rs}')
        print()
