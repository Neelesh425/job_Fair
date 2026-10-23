import json
import re
import copy

# Load the data
with open('data/data.json', encoding='utf-8') as f:
    d = json.load(f)

print('=== CURRENT STATE ===')
print('Companies:', d['cos'])
print('Total JDs:', len(d['jds']))
print('Total people:', len(d['people']))
print('Total pl:', len(d['pl']))
print('Thresholds (GREEN, YELLOW):', d['thr'])
print()

# Understand the CGI requirement:
# - Location: Bangalore
# - Qualification: B.E./B.Tech ONLY
# - Minimum CGPA: 7.0 (no cgpa field in data, so we use q field to check)
# - Eligible Batches: 2025, 2026, 2027 (freshers)
# - Experience: 0-6 months internship (FRESHERS)
# - Mandatory: relevant role-specific certifications (sk field)
# - Open to candidates with mild disabilities ONLY

# Current CGI JDs in "Other roles" (indexes 78, 79, 80):
# 78: CGI: AI Fresher
# 79: CGI: IT Support
# 80: CGI: NET Fresher (actually .NET Fresher)

# CGI candidates from analysis:
# All have Exp="" (blank = fresher) and Qual=B.E./B.Tech
# None have DT/DP fields filled (disability info missing)

# =============================================
# STEP 1: Add CGI as a proper company
# =============================================
cgi_co_idx = len(d['cos'])
d['cos'].append('CGI')
print('Added CGI at company index:', cgi_co_idx)

# =============================================
# STEP 2: Remove old CGI JDs from "Other roles" (jids 78, 79, 80)
# We'll replace them with proper CGI JDs
# =============================================
# The old JD indices for CGI in "Other roles"
old_cgi_jids = {78, 79, 80}

# Map old jid -> new jid (we'll reuse same slots but update company)
# Actually, let's just update those JDs to point to CGI company

# JD 78 = AI Fresher
# JD 79 = IT Support  
# JD 80 = .NET Fresher

# Update the company index for these JDs and fix their metadata
cgi_jd_updates = {
    78: {'t': 'AI Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore'},
    79: {'t': 'IT Support', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore'},
    80: {'t': '.NET Fresher', 'ty': 'Tech', 'e': 'Fresher (0-6 months internship)', 'l': 'Bangalore'},
}

for jid, updates in cgi_jd_updates.items():
    d['jds'][jid]['c'] = cgi_co_idx
    d['jds'][jid]['t'] = updates['t']
    d['jds'][jid]['ty'] = updates['ty']
    d['jds'][jid]['e'] = updates['e']
    d['jds'][jid]['l'] = updates['l']
    d['jds'][jid]['u'] = ''
    print('Updated JD', jid, '->', d['jds'][jid])

# =============================================
# STEP 3: Analyze CGI candidates and filter based on requirements
# - B.E./B.Tech only
# - Freshers (exp = "" or "Fresher")
# - Mild disability (can't verify from data, but we keep all)
# - Must have relevant skills/certifications
# =============================================

# Get all candidates mapped to CGI JDs
cgi_pl = [row for row in d['pl'] if row[0] in old_cgi_jids]
print()
print('Total CGI pl entries:', len(cgi_pl))

# Check each candidate
def is_btech(p):
    q = str(p.get('q', '')).lower()
    return any(x in q for x in ['b.e', 'be/', 'b.tech', 'btech', 'b tech', 'engineering', 'b.e.'])

def is_fresher(p):
    e = str(p.get('e', '')).strip().lower()
    return e in ['', 'fresher', '0', '0-1 years', 'fresher ', 'no experience']

# Group by JD and analyze
print()
print('=== ANALYZING CGI CANDIDATES ===')

for jid_check in [78, 79, 80]:
    jd = d['jds'][jid_check]
    jd_pl = [(row[1], row[2], row[3]) for row in d['pl'] if row[0] == jid_check]
    
    print()
    print(f"JD[{jid_check}] {jd['t']}:")
    eligible = []
    not_eligible = []
    
    for pid, score, reason in jd_pl:
        p = d['people'][pid]
        btech = is_btech(p)
        fresher = is_fresher(p)
        has_cv = bool(p.get('cv', ''))
        has_skills = bool(str(p.get('sk', '')).strip())
        
        status = 'ELIGIBLE' if (btech and fresher) else 'NOT ELIGIBLE'
        if btech and fresher:
            eligible.append((pid, score, p.get('n',''), p.get('sk','')[:50], p.get('loc',''), reason))
        else:
            not_eligible.append((pid, p.get('n',''), btech, fresher))
    
    print(f"  Eligible ({len(eligible)}):")
    for e in eligible:
        print(f"    PID={e[0]} Score={e[1]} {e[2]} | Skills: {e[3]} | Loc: {e[4]}")
    
    if not_eligible:
        print(f"  NOT eligible ({len(not_eligible)}):")
        for ne in not_eligible:
            print(f"    PID={ne[0]} {ne[1]} | btech={ne[2]} fresher={ne[3]}")
