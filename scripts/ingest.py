"""Reads the master JD sheet + candidate response sheets, maps candidates to JDs,
scores them (0-100) and writes data/data.json.  Run: python3 scripts/ingest.py"""
import re, json, os, openpyxl, pandas as pd
IN='/mnt/user-data/uploads/'                      # <- change to your folder
MASTER=IN+'1792310686686_Job_Fair_Master_Sheet__1_.xlsx'
JA=IN+'1792322682987_Job_Application_Form__Responses_.xlsx'
TECH=IN+'1792322682988_Technology_Roles___Inclusive_Hiring_Registration__Responses_.xlsx'
HL=IN+'1792322682987_HighLevel_Inclusive_Hiring_PwD_Candidate_Registration_Form__Responses_.xlsx'
GREEN,YELLOW=66,52                                # zone thresholds
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','data.json')
# (file, sheet, [companies in JD sheet] or "label" for companies NOT in the JD sheet, role column, default role)
SRC=[(JA,'Wipro (COntent) First source Cu',['Wipro','Firstsource'],'Job Role',''),
 (JA,'15 Profiles (dell,allstate,info',['Dell','Allstate','Infosys','Titan'],'Select the position you are applying for',''),
 (JA,'CRM(Titan)',['Titan'],'Job Role Applied For',''),(JA,'Indigo Aocs',['Indigo'],None,''),
 (TECH,0,['Asian Paints'],'Job Role Applied For',''),(HL,0,['GoHighLevel'],'Position Applying For',''),
 (JA,'Picker Paacker','Picker & Packer','Job Role ','Picker Packer'),(JA,'CGI(freshesrs)','CGI','Which role are you applying for?',''),
 (JA,'Partk time(^K)','Part-time PAN card job',None,'Part-time 5-9 PM'),(JA,'Vmart Retail Store','V-Mart',None,'Retail Store'),
 (JA,'Telesales (Global Visa)','Global Visa',None,'Telesales'),(JA,'Delloite','Deloitte',None,''),(JA,'RT Delloite','Deloitte',None,''),
 (JA,'Customer Support mail','Customer Support (sheet name unclear)',None,'Customer Support'),
 (JA,'Form Responses 6','Unlabelled sheet (Form Responses 6)',None,''),(JA,'Form Responses 2','Unlabelled sheet (Form Responses 2)','Job Role','Apprenticeship, IT & finance roles (mixed)'),
 (JA,'Form Responses 1','Cargo sheet (Form Responses 1)','Job Role','Cargo & airport operations (mixed)')]
ALIAS={'network support':'enterprise networking','security operations':'information security','devsecops':'devsecops','it infrastructure':'it infra','ot security':'ot security','sde-2':'sde2','revenue operations':'revenue operations'}
# ---------- JDs
cos=[];jds=[]
def e70(v):return '' if str(v or '').lower().startswith('not specified') else str(v or '').strip()[:70]
for r in openpyxl.load_workbook(MASTER)['JDs Overview '].iter_rows(min_row=2):
    co=str(r[1].value or '').strip()
    if co in('','Company Name'):continue
    m=re.match(r'=HYPERLINK\("([^"]*)","(.*)"\)$',str(r[4].value or ''));u,t=(m[1],m[2]) if m else ('',str(r[4].value or ''))
    t=re.sub(r'\.(docx|pdf)$','',re.sub(r'^(Infosys - |JD[ _]*-?\s*)','',t)).strip()
    if 'duplicate file' in t or not t:continue
    if co not in cos:cos.append(co)
    jds.append(dict(id=len(jds),c=cos.index(co),t=t,ty=str(r[2].value or '').strip(),e=e70(r[6].value),l=e70(r[8].value)[:40],u=u))
CI={c:i for i,c in enumerate(cos)};OTH=len(cos)
CW={w for c in cos for w in re.findall(r'[a-z]+',c.lower())}-{'insurance','life','max'}
cos.append('Other roles (not in your JD sheet)')
STOP=set('the and for with from work office location confirmed be to of in at grade'.split());LV=set('executive associate manager deputy senior sr asst assistant officer specialist trainee chief lead'.split())
CITYW=r'bang?alore|bengalore|bengaluru|bangalor\w*|pune|mumbai|gurugram|gurgaon|delhi|hyderabad|chennai|karnataka|remote|head office'
def toks(s,extra=()):
    d={}
    for w in re.findall(r'[a-z0-9#+]{2,}',re.sub(CITYW,' ',s.lower())):
        if w not in STOP and w not in CW and w not in extra:d.setdefault(w[:6],w)
    return d
def match(role,allowed):
    rt=set(toks(role));best=(0,None)
    for j in jds:
        if j['c'] not in allowed:continue
        jt=set(toks(j['t']))
        if not jt or not rt:continue
        if jt==rt:return j['id']
        s=len(jt&rt)/len(jt|rt)
        if len(jt&rt)>=2 and s>best[0]:best=(s,j['id'])
    return best[1] if best[0]>=.6 else None
oth={}
def other(t):
    k=t.lower()
    if k not in oth:
        oth[k]=len(jds);jds.append(dict(id=len(jds),c=OTH,t=t,ty='Not in JD sheet',e='',l='',u=''))
    return oth[k]
GRP={'Form Responses 1','Form Responses 2'}   # sheets whose free-text role is grouped under one JD
def resolve(co,role,default,grp=False):
    r=re.sub(r'\s+',' ',(role or default or '')).strip(' .')
    if isinstance(co,str):return [other(f'{co}: {(default if grp else r) or "Application (role not captured by form)"}')]
    al={CI[n] for n in co};rl=r.lower()
    if 'both positions' in rl:return [j['id'] for j in jds if j['c'] in al]
    for k,v in ALIAS.items():
        if k in rl:
            for j in jds:
                if j['c'] in al and v in j['t'].lower():return [j['id']]
    m=match(r,al)
    if m is not None:return [m]
    js=[j['id'] for j in jds if j['c'] in al]
    if not r and len(js)==1:return js
    return [other(f'{r or "Application"} (no matching JD)')]
# ---------- field extraction
F={'name':[r'^full name$',r'^name$',r"^candidate.s name"],'em':[r'^email id$',r'^email$',r'^email address 2$',r'^email address$'],
'ph':[r'^mobile number$',r'^contact (number|no|details)',r'^mobile'],'loc':[r'^current (city|location)'],'pref':[r'^preferred'],
'exp':[r'^relevant (work )?experience',r'^total (work )?experience',r'^total years',r'^work experience in years',r'^total and relevant',r'previous work experience'],
'np':[r'notice',r'when can you join|earliest joining|availability to join|joining availability'],
'sk':[r'key skills',r'skillset',r'^which ai/ml',r'^specific required skill',r'additional skill'],'q':[r'^highest (educational )?qualification',r'^education level'],
'org':[r'^current (or last )?(organi[sz]ation|company)'],'des':[r'^current (or last )?(designation|job role|role)',r'^designation',r'if experienced, mention'],
'cv':[r'resume|\bcv\b'],'ct':[r'current.*ctc'],'ex':[r'^expected.*(ctc|salary)'],'rl':[r'relocate',r'^are you willing to work in',r'^are you available to work in'],'ts':[r'^timestamp']}
def cl(v):
    v=str(v if v is not None else '').strip();return '' if v.lower() in('nan','nat','none','') else v
def yrs(t):
    t=t.lower()
    if not t:return None
    if 'fresh' in t or t.startswith('no exp'):return 0
    v=[float(x) for x in re.findall(r'\d+(?:\.\d+)?',t)[:2]]
    if not v or v[0]>40:return None
    if 'month' in t and 'year' not in t and len(v)==1:return round(v[0]/12,1)
    return sum(v)/2 if len(v)==2 and re.search(r'\d\s*(-|–|to)\s*\d',t) else v[0]
def ndays(t):
    t=t.lower()
    if not t or re.search(r'20\d\d',t):return None
    if re.search(r'immed|served|^nil|joined|^0\b',t):return 0
    m=re.search(r'(\d+)\s*(day|week|month)?',t)
    return None if not m else int(m[1])*({'week':7,'month':30}.get(m[2],1))
CITY=[('Bengaluru',r'(?<!west )b[ae]ng|bnglr|whitefield|sarjapur'),('Mumbai',r'mumbai|thane|navi|kalyan|vashi'),('Pune',r'pune|pimpri'),('NCR',r'delhi|noida|gurgaon|gurugram|ghaziabad|faridabad|ncr'),('Hyderabad',r'hyderabad|secunderabad'),('Chennai',r'chennai')]
cities=lambda t:{c for c,p in CITY if re.search(p,str(t).lower())}
def rng(e,t):
    e=e.lower()
    if 'fresher' in e and 'experienced' in e:return None
    if 'fresher' in e or ('fresher' in t.lower() and not e):return (0,1)
    m=re.search(r'(\d+)\s*[–-]\s*(\d+)',e)
    if m:return (float(m[1]),float(m[2]))
    m=re.search(r'(\d+)\s*(\+|yr|year)',e);return (float(m[1]),None) if m else None
def score(c,j,role):
    y=yrs(c['exp']);rg=rng(j['e'],j['t']);why=[]
    ex=8 if y is None else 15 if rg is None else 25 if (y>=rg[0] and (rg[1] is None or y<=rg[1]+3)) else 18 if y>rg[0] else max(0,25-12*(rg[0]-y))
    why.append(('experience not stated' if y is None else f'{y:g} yrs experience')+(f" (JD: {j['e'][:30]})" if rg and j['e'] else ''))
    jt=set(toks(j['t'].split(': ',1)[-1],LV));wd=toks(' '.join([c['sk'],c['des'],c['q']]),LV);bag=set(wd)
    sh=jt&bag;fit=35*(.3+.7*min(1,len(sh)/min(len(jt),4)))*(1 if bag else .6) if jt else 21
    why.append(('matches: '+', '.join(sorted(wd[k] for k in sh)[:4])) if sh else 'little keyword overlap with role')
    jc=cities(j['l'])|cities(j['t'])|cities(role);cc=cities(c['loc']);yes=re.match(r'\s*y',c['rl'].lower())
    if 'remote' in (j['l']+j['t']).lower():lo=15;why.append('remote role')
    elif not jc:lo=8
    elif cc&jc:lo=15;why.append('based in role city')
    elif cities(c['pref'])&jc or yes:lo=10;why.append('outside role city, open to relocate')
    else:lo=3;why.append('not in role city')
    n=ndays(c['np']);nt=5 if n is None else 10 if n<=15 else 8 if n<=30 else 5 if n<=60 else 3 if n<=90 else 1
    why.append('notice n/a' if n is None else 'immediate joiner' if n==0 else f'{n} days notice')
    cp=5*bool(c['cv'])+4*bool(c['ph'] or c['em'])+3*bool(c['q'])+3*bool(c['sk'] or c['des'])
    if not c['cv']:why.append('no CV link')
    return round(fit+ex+lo+nt+cp),'; '.join(why)
# ---------- read & build
rows=[];stats={}
for f,sh,co,rc,dr in SRC:
    df=pd.read_excel(f,sheet_name=sh,dtype=str).fillna('');cols=list(df.columns);cm={}
    for k,pats in F.items():cm[k]=[c for p in pats for c in cols if re.search(p,c,re.I) and not (k=='cv' and re.search('certif',c,re.I))]
    n0=len(rows)
    for _,r in df.iterrows():
        g=lambda k:next((cl(r[c]) for c in cm[k] if cl(r[c])),'')
        c={k:g(k) for k in F};c['sk']='; '.join(dict.fromkeys(cl(r[x]) for x in cm['sk'] if cl(r[x])))
        c['cv']=(re.search(r'https?://\S+',c['cv']) or [''])[0].rstrip(',');ph=re.sub(r'\D','',c['ph'].split('.')[0]);c['ph']=ph[-10:] if len(ph)>=10 else ''
        if not (c['name'] or c['em'] or c['cv']) or c['em'].lower().startswith('xyz@') or c['name'].lower() in('name','full name'):continue
        c['name']=c['name'] or c['em'].split('@')[0] or 'Unnamed'
        role=cl(r[rc]) if rc and rc in df.columns else '';sheetname=sh if isinstance(sh,str) else 'form'
        if re.fullmatch(r'\d{10}|Contact No',role):continue   # stray header/phone rows in the Titan sheet
        for jid in resolve(co,role,dr,sh in GRP):rows.append((c,jid,role,sheetname))
    stats[str(sh)]=len(rows)-n0
best={}
for c,jid,role,s in rows:
    k=((c['em'] or c['ph'] or c['name']).lower(),jid)
    if k not in best or c['ts']>best[k][0]['ts']:best[k]=(c,jid,role,s)
cands=[]
for c,jid,role,s in best.values():
    j=jds[jid];sc,why=score(c,j,role);nm=c['name'][:60].strip()
    cands.append(dict(jd=jid,co=j['c'],role=role or j['t'],n=nm.title() if nm.isupper() else nm,org=c['org'][:40],e=c['exp'][:40],loc=c['loc'][:40],np=c['np'][:25],em=c['em'],ph=c['ph'],cv=c['cv'],sk=c['sk'][:160],q=c['q'][:50],ct=c['ct'][:20],ex=c['ex'][:20],ts=c['ts'][:16],src=s,sc=sc,rs=why))
cands.sort(key=lambda c:(c['jd'],-c['sc']))
for i,c in enumerate(cands):c['id']='c%d'%i
json.dump(dict(cos=cos,jds=jds,cands=cands,thr=[GREEN,YELLOW]),open(OUT,'w'),ensure_ascii=False,separators=(',',':'))
if __name__=='__main__':
    import collections
    print('rows per sheet',stats);print('submissions',len(rows),'after dedupe',len(cands),'JDs',len(jds))
    print('zones',collections.Counter('g' if c['sc']>=GREEN else 'y' if c['sc']>=YELLOW else 'r' for c in cands))
    cj=collections.Counter(c['jd'] for c in cands)
    for j in jds:
        if j['c']==OTH or cj[j['id']]:print(cos[j['c']][:12],'|',j['t'][:62],'|',cj[j['id']])
