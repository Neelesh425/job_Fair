import json

d = json.load(open('data/data.json', encoding='utf-8'))

# Get full details of ALL people in CGI JDs and also all pool candidates
cgi_jids = {78, 79, 80}

# Get unique PIDs from CGI JDs
cgi_pids = set()
for row in d['pl']:
    jid, pid, score, reason, is_pool = row
    if jid in cgi_jids:
        cgi_pids.add(pid)

print('=== ALL CGI Candidate Details ===')
for pid in sorted(cgi_pids):
    p = d['people'][pid]
    print('PID='+str(pid)+' | Name='+str(p.get('n','')))
    print('  Exp='+str(p.get('e',''))+' | Qual='+str(p.get('q',''))+' | Skills='+str(p.get('sk','')))
    print('  Loc='+str(p.get('loc',''))+' | DT='+str(p.get('dt',''))+' | DP='+str(p.get('dp','')))
    print('  Org='+str(p.get('org',''))+' | Des='+str(p.get('des',''))+' | CV='+str(p.get('cv',''))[:50])
    # Find all JDs this person is in
    my_jds = [(row[0], row[2]) for row in d['pl'] if row[1] == pid]
    print('  JDs: '+str(my_jds))
    print()
