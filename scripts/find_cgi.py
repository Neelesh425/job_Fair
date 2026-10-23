import json

d = json.load(open('data/data.json', encoding='utf-8'))

# Find candidates in CGI JDs (78, 79, 80)
cgi_jids = {78, 79, 80}

print('=== CGI JD Candidates ===')
for row in d['pl']:
    jid, pid, score, reason, is_pool = row
    if jid in cgi_jids:
        p = d['people'][pid]
        jd = d['jds'][jid]
        print('JD['+str(jid)+'] '+jd['t']+' | PID='+str(pid)+' | Score='+str(score))
        print('  Name='+str(p.get('n',''))+' | Exp='+str(p.get('e',''))+' | CGPA='+str(p.get('q',''))+' | Skills='+str(p.get('sk',''))[:80])
        print('  Qual='+str(p.get('q',''))+' | DT='+str(p.get('dt',''))+' | DP='+str(p.get('dp',''))+' | Loc='+str(p.get('loc','')))
        print('  Reason='+str(reason)[:100])
        print()
