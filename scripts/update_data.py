"""
update_data.py - Adds CGI and Hitachi companies to data.json with properly matched candidates.

CGI Requirements:
- Location: Bangalore
- Qualification: B.E./B.Tech only
- Min CGPA: 7.0 (no cgpa field, use q check)
- Eligible Batches: 2025, 2026, 2027 (freshers)
- Experience: Freshers with 0-6 months internship
- Mandatory: role-specific certifications
- Open to mild disabilities only

Hitachi Requirements:
- Date: Friday, 30 Oct 2026, Bangalore
- Experience: More than 1 year
- IT: Java Dev, Full Stack Dev, .NET Dev, Agentic AI, Gen AI, Software Dev, Software Tester
- Non-IT: Finance, HR, Procurement
- Disability: Open to all EXCEPT visually impaired
"""
import json
import re
import shutil
import os

# Backup original
if not os.path.exists('data/data.json.backup_pre_cgi_hitachi'):
    shutil.copy('data/data.json', 'data/data.json.backup_pre_cgi_hitachi')
    print('Backup created: data/data.json.backup_pre_cgi_hitachi')

with open('data/data.json', encoding='utf-8') as f:
    d = json.load(f)

print('Original companies:', d['cos'])
print('Original JD count:', len(d['jds']))
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
    # "N Year(s) M Month(s)"
    m = re.search(r'(\d+)\s*year', e)
    if m:
        years = int(m.group(1))
        mm = re.search(r'(\d+)\s*month', e)
        months = int(mm.group(1)) if mm else 0
        return years + months / 12
    # "N-M years"
    m = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)', e)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    # "N+ years"
    m = re.search(r'(\d+)\+\s*(?:years?|yrs?)', e)
    if m:
        return float(m.group(1))
    # "N years" or "Nyrs"
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)', e)
    if m:
        return float(m.group(1))
    # Bare number
    m = re.search(r'^(\d+(?:\.\d+)?)$', e)
    if m:
        return float(m.group(1))
    # Any number
    m = re.search(r'(\d+(?:\.\d+)?)', e)
    if m:
        v = float(m.group(1))
        return v if v <= 50 else 0  # ignore huge numbers that are clearly not exp
    return 0

def is_btech(p):
    q = str(p.get('q', '')).lower()
    return any(x in q for x in ['b.e', 'be/', 'b.tech', 'btech', 'b tech', 'b.e.', 'engineering'])

def is_fresher(p):
    e = str(p.get('e', '')).strip().lower()
    exp_yrs = parse_exp_years(p.get('e', ''))
    return exp_yrs <= 0.6  # 0-6 months

def is_visually_impaired(p):
    dt = str(p.get('dt', '')).lower()
    return any(x in dt for x in ['visual', 'blind', 'vision', 'visually', 'low vision', 'low visi'])

def has_cv(p):
    return bool(str(p.get('cv', '')).strip())

def has_skills(p):
    sk = str(p.get('sk', '')).strip().lower()
    return sk and sk not in ['yes', 'no', 'na', 'n/a', '-']

def get_combined(p):
    return (str(p.get('sk', '')) + ' ' + str(p.get('des', '')) + ' ' + str(p.get('role', '')) + ' ' + str(p.get('org', ''))).lower()

# ============================================================
# STEP 1: CGI Company Setup
# ============================================================
# Check if CGI already exists as proper company
if 'CGI' not in d['cos']:
    cgi_co_idx = len(d['cos'])
    d['cos'].append('CGI')
    print(f'Added CGI as company index {cgi_co_idx}')
else:
    cgi_co_idx = d['cos'].index('CGI')
    print(f'CGI already exists at index {cgi_co_idx}')

# Old CGI JDs that were under "Other roles" (jids 78, 79, 80)
old_cgi_jids = [78, 79, 80]

# Verify these are the CGI ones
for jid in old_cgi_jids:
    print(f"  JD[{jid}]: {d['jds'][jid]['t']}")

# Update JDs 78, 79, 80 to be proper CGI JDs
cgi_jd_map = {
    78: {'t': 'AI Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    79: {'t': 'IT Support', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
    80: {'t': '.NET Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore', 'u': ''},
}
for jid, updates in cgi_jd_map.items():
    d['jds'][jid].update(updates)
    d['jds'][jid]['c'] = cgi_co_idx
    print(f"Updated JD[{jid}]: {d['jds'][jid]}")

print()

# ============================================================
# STEP 2: Score CGI candidates properly
# CGI scoring logic:
# - B.E./B.Tech: required (+30 if yes, otherwise exclude)
# - Fresher / 0-6 months exp: required
# - Has skills mentioned: +20
# - Has CV link: +10
# - Role-specific skill alignment: up to 30
# ============================================================

def score_cgi_candidate(p, role):
    """Score a CGI candidate for a specific role. Returns (score, reason)."""
    score = 0
    reasons = []
    
    # Hard requirements - B.E./B.Tech
    if not is_btech(p):
        return 0, 'not B.E./B.Tech'
    
    # Hard requirement - fresher
    if not is_fresher(p):
        return 0, 'experience exceeds 6 months'
    
    # Base score for meeting hard requirements
    score += 30
    reasons.append('B.E./B.Tech qualification')
    
    # Skills check
    sk = get_combined(p)
    has_sk = has_skills(p)
    
    # CV link
    if has_cv(p):
        score += 10
        reasons.append('has CV')
    
    # Role-specific skill alignment
    if role == 'ai_fresher':
        ai_keywords = ['python', 'machine learning', 'ml', 'ai', 'artificial intelligence', 
                       'deep learning', 'dl', 'nlp', 'natural language', 'tensorflow', 'pytorch',
                       'scikit', 'pandas', 'numpy', 'llm', 'generative', 'genai', 'langchain',
                       'rag', 'neural', 'cnn', 'transformers', 'hugging face', 'data science',
                       'computer vision', 'openai', 'gemini', 'agentic', 'langgraph']
        matches = [kw for kw in ai_keywords if kw in sk]
        if len(matches) >= 5:
            score += 35
            reasons.append(f'strong AI skills: {", ".join(matches[:4])}')
        elif len(matches) >= 3:
            score += 25
            reasons.append(f'good AI skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 15
            reasons.append(f'some AI skills: {", ".join(matches[:2])}')
        elif has_sk:
            score += 5
            reasons.append('has skills but limited AI alignment')
    
    elif role == 'it_support':
        it_keywords = ['networking', 'hardware', 'software support', 'troubleshoot', 'helpdesk', 
                       'help desk', 'active directory', 'windows', 'linux', 'sql', 'python', 
                       'it support', 'technical support', 'network', 'server', 'cloud', 'aws',
                       'azure', 'system admin', 'java', 'c#', 'c++', 'database']
        matches = [kw for kw in it_keywords if kw in sk]
        if len(matches) >= 4:
            score += 35
            reasons.append(f'strong IT skills: {", ".join(matches[:4])}')
        elif len(matches) >= 2:
            score += 25
            reasons.append(f'good IT skills: {", ".join(matches[:2])}')
        elif len(matches) >= 1:
            score += 15
            reasons.append(f'some IT skills: {", ".join(matches[:2])}')
        elif has_sk:
            score += 5
            reasons.append('has skills but limited IT alignment')
    
    elif role == 'net_fresher':
        net_keywords = ['.net', 'dotnet', 'c#', 'asp.net', 'wpf', 'blazor', 'vb.net', 'mvc', 
                        'entity framework', 'ef core', 'xamarin', '.net core', 'maui']
        matches = [kw for kw in net_keywords if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong .NET skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 25
            reasons.append(f'.NET skills: {", ".join(matches[:2])}')
        # General programming also valid for .NET fresher
        else:
            gen_keywords = ['python', 'java', 'javascript', 'react', 'sql', 'programming', 'developer']
            gen_matches = [kw for kw in gen_keywords if kw in sk]
            if gen_matches:
                score += 10
                reasons.append(f'programming skills (no .NET specific): {", ".join(gen_matches[:2])}')
            elif has_sk:
                score += 5
                reasons.append('has skills but limited .NET alignment')
    
    # Location bonus (Bangalore preferred)
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc or 'blr' in loc:
        score += 5
        reasons.append('Bangalore location')
    
    reason_str = '; '.join(reasons) if reasons else 'meets basic requirements'
    return score, reason_str

# ============================================================
# Re-score CGI candidates
# Remove all existing CGI pl entries and re-add properly scored ones
# ============================================================
print('=== RE-SCORING CGI CANDIDATES ===')

# Remove old CGI pl entries
original_pl_count = len(d['pl'])
d['pl'] = [row for row in d['pl'] if row[0] not in set(old_cgi_jids)]
print(f'Removed {original_pl_count - len(d["pl"])} old CGI pl entries')

# Role mapping
cgi_role_map = {
    78: ('ai_fresher', ['python', 'machine learning', 'ml', 'ai', 'deep learning', 'llm', 'generative', 'nlp', 'data science', 'tensorflow', 'pytorch']),
    79: ('it_support', ['networking', 'hardware', 'support', 'helpdesk', 'windows', 'linux', 'sql', 'python', 'java', 'it', 'technical']),
    80: ('net_fresher', ['.net', 'dotnet', 'c#', 'asp.net', 'wpf']),
}

# Find all unique PIDs that were in CGI JDs
# Get from original backup
with open('data/data.json.backup_pre_cgi_hitachi', encoding='utf-8') as f:
    d_orig = json.load(f)

cgi_pids_orig = set()
for row in d_orig['pl']:
    if row[0] in set(old_cgi_jids):
        cgi_pids_orig.add(row[1])

print(f'Total unique CGI candidate PIDs: {len(cgi_pids_orig)}')

# For each CGI JD, find best matching candidates
new_cgi_entries = []
assigned = {78: [], 79: [], 80: []}  # jid -> list of (pid, score)

for pid in cgi_pids_orig:
    p = d['people'][pid]
    
    # Hard requirement checks
    if not is_btech(p):
        continue
    if not is_fresher(p):
        continue
    
    sk = get_combined(p)
    
    # Score for each role and pick best
    scores = {}
    for jid_cgi, (role_key, _) in cgi_role_map.items():
        sc, rs = score_cgi_candidate(p, role_key)
        scores[jid_cgi] = (sc, rs)
    
    # Assign to best scoring role
    best_jid = max(scores.keys(), key=lambda j: scores[j][0])
    best_score, best_reason = scores[best_jid]
    
    if best_score > 0:
        assigned[best_jid].append((pid, best_score, best_reason))

# Now also check if any candidate could fit multiple roles (add to secondary)
# Primary assignment done above; add secondary assignments for candidates with good scores in other roles
for pid in cgi_pids_orig:
    p = d['people'][pid]
    if not is_btech(p) or not is_fresher(p):
        continue
    
    sk = get_combined(p)
    primary_jid = None
    primary_score = 0
    
    for jid_cgi, (role_key, _) in cgi_role_map.items():
        sc, _ = score_cgi_candidate(p, role_key)
        if sc > primary_score:
            primary_score = sc
            primary_jid = jid_cgi
    
    # Add to other JDs if they also score well (secondary placements)
    for jid_cgi, (role_key, _) in cgi_role_map.items():
        if jid_cgi == primary_jid:
            continue
        sc, rs = score_cgi_candidate(p, role_key)
        # Only add as secondary if score >= YELLOW threshold
        if sc >= YELLOW:
            assigned[jid_cgi].append((pid, sc, rs + ' [secondary match]'))

# Build new pl entries
for jid_cgi in [78, 79, 80]:
    entries = assigned[jid_cgi]
    # Sort by score desc
    entries.sort(key=lambda x: -x[1])
    # Remove duplicates by pid (keep highest score)
    seen_pids = {}
    for pid, sc, rs in entries:
        if pid not in seen_pids or sc > seen_pids[pid][0]:
            seen_pids[pid] = (sc, rs)
    
    for pid, (sc, rs) in sorted(seen_pids.items(), key=lambda x: -x[1][0]):
        new_cgi_entries.append([jid_cgi, pid, sc, rs, False])

print(f'New CGI pl entries: {len(new_cgi_entries)}')
for jid_cgi in [78, 79, 80]:
    count = sum(1 for e in new_cgi_entries if e[0] == jid_cgi)
    print(f'  JD[{jid_cgi}] {d["jds"][jid_cgi]["t"]}: {count} candidates')

# Add new entries to pl
d['pl'].extend(new_cgi_entries)

# ============================================================
# STEP 3: Hitachi Company Setup
# ============================================================
if 'Hitachi' not in d['cos']:
    hitachi_co_idx = len(d['cos'])
    d['cos'].append('Hitachi')
    print(f'\nAdded Hitachi as company index {hitachi_co_idx}')
else:
    hitachi_co_idx = d['cos'].index('Hitachi')
    print(f'\nHitachi already exists at index {hitachi_co_idx}')
    # Remove existing Hitachi JDs and their pl entries
    hitachi_existing_jids = [j['id'] for j in d['jds'] if j['c'] == hitachi_co_idx]
    print(f'Removing existing Hitachi JDs: {hitachi_existing_jids}')
    # We'll just overwrite - but we need to handle JD indices carefully
    # Actually, the safest approach is to keep the JD indices and just remove + re-add

# Hitachi JDs to add
hitachi_jds_info = [
    # IT roles
    {'t': 'Java Developer', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Full Stack Developer', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': '.NET Developer', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Agentic AI Professional', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Generative AI Professional', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Software Developer', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Software Tester', 'ty': 'Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    # Non-IT roles
    {'t': 'Finance', 'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Human Resources (HR)', 'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
    {'t': 'Procurement', 'ty': 'Non-Tech', 'e': 'More than 1 year', 'l': 'Bangalore', 'u': ''},
]

# Check if Hitachi already has JDs, if so remove their pl entries first
existing_hitachi_jids = [j['id'] for j in d['jds'] if j['c'] == hitachi_co_idx]
if existing_hitachi_jids:
    print(f'Removing existing Hitachi pl entries for JDs: {existing_hitachi_jids}')
    d['pl'] = [row for row in d['pl'] if row[0] not in set(existing_hitachi_jids)]
    # Remove existing Hitachi JDs (we'll re-add)
    hitachi_jid_set = set(existing_hitachi_jids)
    d['jds'] = [j for j in d['jds'] if j['id'] not in hitachi_jid_set]
    # Fix IDs
    for i, j in enumerate(d['jds']):
        j['id'] = i
    # Fix pl references (jid values)
    jid_remap = {}
    for i, j in enumerate(d['jds']):
        jid_remap[j['id']] = i
    d['pl'] = [[jid_remap.get(row[0], row[0])] + row[1:] for row in d['pl']]
    print(f'JDs after removing Hitachi: {len(d["jds"])}')

# Add Hitachi JDs
hitachi_jid_start = len(d['jds'])
hitachi_jid_map = {}  # jd_title -> jid
for i, jd_info in enumerate(hitachi_jds_info):
    new_jid = hitachi_jid_start + i
    new_jd = {
        'id': new_jid,
        'c': hitachi_co_idx,
        't': jd_info['t'],
        'ty': jd_info['ty'],
        'e': jd_info['e'],
        'l': jd_info['l'],
        'u': jd_info['u'],
    }
    d['jds'].append(new_jd)
    hitachi_jid_map[jd_info['t']] = new_jid
    print(f'Added JD[{new_jid}]: {jd_info["t"]}')

print(f'\nHitachi JD indices: {hitachi_jid_map}')

# ============================================================
# STEP 4: Match candidates to Hitachi JDs
# ============================================================
print('\n=== MATCHING HITACHI CANDIDATES ===')

def score_hitachi_candidate(p, role_title):
    """Score a candidate for a Hitachi role. Returns (score, reason)."""
    score = 0
    reasons = []
    
    exp_yrs = parse_exp_years(p.get('e', ''))
    
    # Hard requirement: > 1 year experience
    if exp_yrs <= 1:
        return 0, f'experience {exp_yrs:.1f}yr <= 1yr required'
    
    # Hard requirement: NOT visually impaired
    if is_visually_impaired(p):
        return 0, 'visually impaired - excluded per Hitachi policy'
    
    # Base score for meeting hard requirements
    score += 20
    reasons.append(f'{exp_yrs:.1f}yr experience (>1yr required)')
    
    sk = get_combined(p)
    
    # CV bonus
    if has_cv(p):
        score += 5
        reasons.append('has CV')
    
    # Location bonus
    loc = str(p.get('loc', '')).lower()
    if 'bangalore' in loc or 'bengaluru' in loc or 'blr' in loc:
        score += 5
        reasons.append('Bangalore location')
    
    # Experience scoring (more experience = higher score, capped)
    if exp_yrs >= 10:
        score += 20
    elif exp_yrs >= 5:
        score += 15
    elif exp_yrs >= 3:
        score += 10
    elif exp_yrs >= 2:
        score += 8
    else:
        score += 5  # 1-2 years
    
    # Role-specific scoring
    if role_title == 'Java Developer':
        java_kw = ['java', 'spring boot', 'spring', 'hibernate', 'j2ee', 'springboot', 'jpa', 
                   'spring mvc', 'microservices', 'java developer', 'core java']
        matches = [kw for kw in java_kw if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong Java skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'Java skills: {", ".join(matches)}')
    
    elif role_title == 'Full Stack Developer':
        fs_kw = ['full stack', 'fullstack', 'react', 'angular', 'vue', 'nodejs', 'node.js', 
                 'frontend', 'backend', 'javascript', 'typescript', 'next.js', 'nextjs',
                 'express', 'mongodb', 'html', 'css', 'django', 'flask', 'fastapi', 'restapi', 'rest api']
        matches = [kw for kw in fs_kw if kw in sk]
        if len(matches) >= 4:
            score += 35
            reasons.append(f'strong Full Stack skills: {", ".join(matches[:4])}')
        elif len(matches) >= 2:
            score += 20
            reasons.append(f'Full Stack skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 10
            reasons.append(f'some Full Stack skills: {", ".join(matches)}')
    
    elif role_title == '.NET Developer':
        net_kw = ['.net', 'dotnet', 'c#', 'asp.net', 'wpf', 'blazor', 'vb.net', 
                  '.net core', 'entity framework', 'ef core', 'mvc', 'net developer']
        matches = [kw for kw in net_kw if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong .NET skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'.NET skills: {", ".join(matches)}')
    
    elif role_title == 'Agentic AI Professional':
        agentic_kw = ['agentic ai', 'ai agent', 'langchain', 'langgraph', 'langraph', 
                      'llm', 'llms', 'rag', 'retrieval', 'agent', 'mcp', 'multi-agent', 
                      'crewai', 'autogen', 'agentic', 'orchestrat']
        matches = [kw for kw in agentic_kw if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong Agentic AI skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'Agentic AI skills: {", ".join(matches)}')
    
    elif role_title == 'Generative AI Professional':
        genai_kw = ['generative ai', 'genai', 'gen ai', 'gpt', 'openai', 'gemini', 
                    'prompt engineering', 'stable diffusion', 'huggingface', 'hugging face', 
                    'transformers', 'fine-tuning', 'langchain', 'vector', 'llm', 'llms',
                    'diffusion', 'midjourney', 'dall-e', 'text-to-image']
        matches = [kw for kw in genai_kw if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong GenAI skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'GenAI skills: {", ".join(matches)}')
    
    elif role_title == 'Software Developer':
        dev_kw = ['software developer', 'software development', 'python', 'java', 'c++', 
                  'golang', 'ruby', 'php', 'developer', 'programming', 'coding', 'git',
                  'agile', 'scrum', 'ci/cd', 'devops', 'sql', 'database']
        matches = [kw for kw in dev_kw if kw in sk]
        if len(matches) >= 5:
            score += 35
            reasons.append(f'strong Software Dev skills: {", ".join(matches[:4])}')
        elif len(matches) >= 2:
            score += 20
            reasons.append(f'Software Dev skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 10
            reasons.append(f'some Software Dev skills: {", ".join(matches)}')
    
    elif role_title == 'Software Tester':
        test_kw = ['testing', 'qa', 'quality assurance', 'selenium', 'automation testing', 
                   'manual testing', 'test', 'jira', 'bug', 'playwright', 'cypress',
                   'postman', 'api testing', 'performance testing', 'load testing', 'jmeter']
        matches = [kw for kw in test_kw if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong Testing skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'Testing skills: {", ".join(matches)}')
    
    elif role_title == 'Finance':
        fin_kw = ['finance', 'accounting', 'financial', 'accounts', 'audit', 'gst', 
                  'taxation', 'tds', 'ledger', 'balance sheet', 'ca', 'cpa', 'cfa', 
                  'controller', 'reconciliation', 'tally', 'sap fi', 'sap co', 'excel',
                  'accounts payable', 'accounts receivable', 'budgeting', 'forecasting']
        matches = [kw for kw in fin_kw if kw in sk]
        if len(matches) >= 3:
            score += 35
            reasons.append(f'strong Finance skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'Finance skills: {", ".join(matches)}')
    
    elif role_title == 'Human Resources (HR)':
        hr_kw = ['hr', 'human resource', 'recruitment', 'talent acquisition', 'onboarding', 
                 'payroll', 'hris', 'people ops', 'employee relations', 'training',
                 'learning and development', 'l&d', 'performance management', 'hrms', 'hcm']
        matches = [kw for kw in hr_kw if kw in sk]
        if len(matches) >= 2:
            score += 35
            reasons.append(f'strong HR skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'HR skills: {", ".join(matches)}')
    
    elif role_title == 'Procurement':
        proc_kw = ['procurement', 'purchase', 'supply chain', 'sourcing', 'vendor', 
                   'supplier', 'inventory', 'logistics', 'warehouse', 'sap mm', 'sap wm',
                   'materials management', 'buying', 'contract management', 'rfq', 'rfp']
        matches = [kw for kw in proc_kw if kw in sk]
        if len(matches) >= 2:
            score += 35
            reasons.append(f'strong Procurement skills: {", ".join(matches[:3])}')
        elif len(matches) >= 1:
            score += 20
            reasons.append(f'Procurement skills: {", ".join(matches)}')
    
    reason_str = '; '.join(reasons) if reasons else 'meets experience requirement'
    return score, reason_str

# Find all candidates with >1 year experience, not visually impaired
hitachi_candidates = []  # (pid, exp_yrs, p)
seen_pids = set()

for row in d_orig['pl']:
    pid = row[1]
    if pid in seen_pids:
        continue
    seen_pids.add(pid)
    p = d['people'][pid]
    exp_yrs = parse_exp_years(p.get('e', ''))
    if exp_yrs > 1 and not is_visually_impaired(p):
        hitachi_candidates.append((pid, exp_yrs, p))

print(f'Total candidates with >1yr experience, not visually impaired: {len(hitachi_candidates)}')

# For each Hitachi JD, find best matching candidates
hitachi_role_titles = [jd_info['t'] for jd_info in hitachi_jds_info]

# Primary assignment: each candidate goes to their BEST matching Hitachi role
# Then we also add secondary matches for candidates with very strong skills in multiple roles

new_hitachi_pl = []

# Score each candidate for each role
candidate_scores = {}  # pid -> {role_title: (score, reason)}
for pid, exp_yrs, p in hitachi_candidates:
    candidate_scores[pid] = {}
    for role_title in hitachi_role_titles:
        sc, rs = score_hitachi_candidate(p, role_title)
        candidate_scores[pid][role_title] = (sc, rs)

# For each Hitachi JD, collect candidates
role_to_candidates = {rt: [] for rt in hitachi_role_titles}
for pid, exp_yrs, p in hitachi_candidates:
    for role_title in hitachi_role_titles:
        sc, rs = candidate_scores[pid][role_title]
        if sc > 0:
            role_to_candidates[role_title].append((pid, sc, rs))

# Sort each role's candidates by score desc
for role_title in hitachi_role_titles:
    role_to_candidates[role_title].sort(key=lambda x: -x[1])

# Build pl entries for Hitachi
for role_title, jid_hitachi in hitachi_jid_map.items():
    entries = role_to_candidates.get(role_title, [])
    # Remove duplicate pids (keep highest score)
    seen = {}
    for pid, sc, rs in entries:
        if pid not in seen or sc > seen[pid][0]:
            seen[pid] = (sc, rs)
    
    count = 0
    for pid, (sc, rs) in sorted(seen.items(), key=lambda x: -x[1][0]):
        new_hitachi_pl.append([jid_hitachi, pid, sc, rs, False])
        count += 1
    
    print(f'  JD[{jid_hitachi}] {role_title}: {count} candidates')

print(f'\nTotal new Hitachi pl entries: {len(new_hitachi_pl)}')

# Sort pl by (jid, -score) as required
new_hitachi_pl.sort(key=lambda x: (x[0], -x[2]))
d['pl'].extend(new_hitachi_pl)

# ============================================================
# STEP 5: Re-sort all pl entries
# ============================================================
d['pl'].sort(key=lambda x: (x[0], -x[2]))

# ============================================================
# STEP 6: Save
# ============================================================
print()
print('=== FINAL STATE ===')
print('Companies:', d['cos'])
print('Total JDs:', len(d['jds']))
print('Total pl:', len(d['pl']))

# Verify CGI and Hitachi
print()
print('CGI JDs:')
for j in d['jds']:
    if d['cos'][j['c']] == 'CGI':
        count = sum(1 for row in d['pl'] if row[0] == j['id'])
        print(f"  [{j['id']}] {j['t']} - {count} candidates")

print()
print('Hitachi JDs:')
for j in d['jds']:
    if d['cos'][j['c']] == 'Hitachi':
        count = sum(1 for row in d['pl'] if row[0] == j['id'])
        print(f"  [{j['id']}] {j['t']} - {count} candidates")

with open('data/data.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, separators=(',', ':'))

print('\ndata.json saved successfully!')
print(f'File size: {os.path.getsize("data/data.json") / 1024:.1f} KB')
