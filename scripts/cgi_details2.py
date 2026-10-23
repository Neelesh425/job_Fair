import json

d = json.load(open('data/data.json', encoding='utf-8'))

# Get full details of ALL people in CGI JDs - including the truncated ones
cgi_jids = {78, 79, 80}

cgi_pids = set()
for row in d['pl']:
    jid, pid, score, reason, is_pool = row
    if jid in cgi_jids:
        cgi_pids.add(pid)

# Also print PIDs 468-480 (the ones we might have missed) 
print('=== FIRST BATCH of CGI Candidates (468-480) ===')
for pid in range(468, 481):
    if pid in cgi_pids:
        p = d['people'][pid]
        print('PID='+str(pid)+' | Name='+str(p.get('n','')))
        print('  Exp='+str(p.get('e',''))+' | Qual='+str(p.get('q',''))+' | Skills='+str(p.get('sk','')))
        print('  Loc='+str(p.get('loc',''))+' | DT='+str(p.get('dt',''))+' | DP='+str(p.get('dp','')))
        print('  Org='+str(p.get('org',''))+' | Des='+str(p.get('des','')))
        my_jds = [(row[0], row[2]) for row in d['pl'] if row[1] == pid]
        print('  JDs: '+str(my_jds))
        print()

# Also find the very first ones (the truncated part mentioned PID 470, 480, 482, etc.)
print()
print('=== Earlier PIDs in CGI ===')
for pid in [468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501]:
    if pid in cgi_pids:
        p = d['people'][pid]
        print('PID='+str(pid)+' | Name='+str(p.get('n',''))+' | Qual='+str(p.get('q',''))+' | Skills='+str(p.get('sk',''))[:60])
        my_jds = [(row[0], row[2]) for row in d['pl'] if row[1] == pid]
        print('  JDs: '+str(my_jds)+' | DT='+str(p.get('dt',''))+' | DP='+str(p.get('dp','')))
        print()
