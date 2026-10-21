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
F={'name':[r'^full name$',r'^name$',r"^candidate.s name",r'^candidate name$'],
'em':[r'^email id$',r'^mail id$',r'^email$',r'^email address 2$',r'^email address$'],
'ph':[r'^mobile number$',r'^phone number$',r'^contact (number|no|details)',r'^mobile'],'loc':[r'^current (city|location)'],'pref':[r'^preff?erred'],
'exp':[r'^relevant (work )?experience',r'^total (work )?experience',r'^total years',r'^work experience in years',r'^total and relevant',r'^experience$',r'previous work experience'],
'np':[r'notice',r'when can you join|earliest joining|availability to join|joining availability'],
'sk':[r'key skills',r'skillset',r'^skills$',r'^which ai/ml',r'^specific required skill',r'additional skill'],
'q':[r'^highest (educational )?qualification',r'^qualification$',r'^under graduation degree',r'^education level'],
'org':[r'^current (or last )?(organi[sz]ation|company)',r'^curr\. company name',r'^company$'],
'des':[r'^current (or last )?(designation|job role|role)',r'^designation',r'^curr\. company designation',r'if experienced, mention'],
'cv':[r'resume|\bcv\b'],'ct':[r'current.*ctc',r'^annual salary'],'ex':[r'^expected.*(ctc|salary)',r'expected ctc'],
'rl':[r'relocate',r'^are you willing to work in',r'^are you available to work in'],'ts':[r'^timestamp',r'^date of application'],
'dt':[r'disability types?|type of disability'],'dp':[r'disability (percentage|%)|percentage of disability'],'ad':[r'full address',r'^address$',r'permanent address'],
'note':[r'^remarks?$'],'rt':[r'^job role$',r'^role$',r'^department$',r'^resume headline$',r'^job title$']}
def cl(v):
    v=str(v if v is not None else '').strip();return '' if v.lower() in('nan','nat','none','') else v
def yrs(t):
    t=t.lower()
    if not t:return None
    if 'fresh' in t or t.startswith('no exp'):return 0
    ym=re.search(r'(\d+)\s*year',t);mm=re.search(r'(\d+)\s*month',t)
    if ym and mm:return round(int(ym[1])+int(mm[1])/12,1)
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
    y=yrs(c['exp']);rg=rng(j['e'],j['t']);why=[];exp_mismatch=False
    ex=8 if y is None else 15 if rg is None else 25 if (y>=rg[0] and (rg[1] is None or y<=rg[1]+2)) else max(0,25-12*abs(rg[0]-y) if y<rg[0] else 25-5*(y-(rg[1]+2)) if rg[1] is not None else 0)
    # Flag experience mismatch for hard cap
    if y is not None and rg is not None:
        in_range = y>=rg[0] and (rg[1] is None or y<=rg[1]+2)
        if not in_range: exp_mismatch=True
    why.append(('experience not stated' if y is None else f'{y:g} yrs experience'+(' MISMATCH' if exp_mismatch else ''))+(f" (JD: {j['e'][:30]})" if rg and j['e'] else ''))
    jt=set(toks(j['t'].split(': ',1)[-1],LV));wd=toks(' '.join([c['sk'],c['des'],c['q']]),LV);bag=set(wd)
    sh=jt&bag;fit=35*(.3+.7*min(1,len(sh)/min(len(jt),4)))*(1 if bag else .6) if jt else 21
    why.append(('matches: '+', '.join(sorted(wd[k] for k in sh)[:4])) if sh else 'little keyword overlap with role')
    jc=cities(j['l'])|cities(j['t'])|cities(role);cc=cities(c['loc']);yes=re.match(r'\\s*y',c['rl'].lower())
    if 'remote' in (j['l']+j['t']).lower():lo=15;why.append('remote role')
    elif not jc:lo=8
    elif cc&jc:lo=15;why.append('based in role city')
    elif cities(c['pref'])&jc or yes:lo=10;why.append('outside role city, open to relocate')
    else:lo=3;why.append('not in role city')
    n=ndays(c['np']);nt=5 if n is None else 10 if n<=15 else 8 if n<=30 else 5 if n<=60 else 3 if n<=90 else 1
    why.append('notice n/a' if n is None else 'immediate joiner' if n==0 else f'{n} days notice')
    cp=5*bool(c['cv'])+4*bool(c['ph'] or c['em'])+3*bool(c['q'])+3*bool(c['sk'] or c['des'])
    if not c['cv']:why.append('no CV link')
    total=round(fit+ex+lo+nt+cp)
    # Hard cap: experience mismatch prevents green zone
    if exp_mismatch and total>=GREEN:
        total=GREEN-1
        why.append('capped: exp out of range')
    return total,'; '.join(why)
# ---------- read & build
GEN={'manage','operat','servic','suppor','busine','commun'}
NK=IN+'Naukri_PWD_hiring_sheets.xlsx';SL=IN+'Candidates_Complete_Details_Shortlist.xlsx';PE=IN+'Purchase-Executive_20260728113748_160.xlsx'
POOL=[(PE,'MySheet'),(SL,'Complete Candidates')]+[(NK,s) for s in ['Sheet2','Sheet10','Sheet3','Sheet4','PWD CCDS','Sheet5','Sheet6','Sheet7']]
GRP={'Form Responses 1','Form Responses 2'}   # sheets whose free-text role is grouped under one JD
def dpct(v):
    m=re.search(r'\d+(?:\.\d+)?',v)
    if not m:return v[:20]
    x=float(m[0]);x=x*100 if x<=1 else x
    return f'{x:g}%'
def load(f,sh):
    df=pd.read_excel(f,sheet_name=sh,dtype=str).fillna('');cols=list(df.columns)
    cm={k:[c for p in pats for c in cols if re.search(p,c,re.I) and not (k=='cv' and re.search('certif',c,re.I))] for k,pats in F.items()}
    cm['cv']+=[c for c in cols if re.search(r'^candidate profile',c,re.I)]
    for _,r in df.iterrows():
        g=lambda k:next((cl(r[c]) for c in cm[k] if cl(r[c])),'')
        c={k:g(k) for k in F}
        for k in('sk','rt'):c[k]='; '.join(dict.fromkeys(v for v in (cl(r[x]) for x in cm[k]) if v and not v.lower().startswith('diversity hiring')))
        c['cv']=next((m[0].rstrip(',') for x in cm['cv'] for m in [re.search(r'https?://\S+',cl(r[x]))] if m),'')
        ph=re.sub(r'\D','',c['ph'].split('.')[0]);c['ph']=ph[-10:] if len(ph)>=10 else ''
        if not (c['name'] or c['em'] or c['cv']) or c['em'].lower().startswith('xyz@') or c['name'].lower() in('name','full name'):continue
        c['name']=c['name'] or c['em'].split('@')[0] or 'Unnamed';c['dp']=dpct(c['dp']) if c['dp'] else ''
        yield r,c
items=[]   # (person, jd id, score, reason, is_pool, role, source sheet)
for f,sh,co,rc,dr in SRC:
    for r,c in load(f,sh):
        role=cl(r[rc]) if rc and rc in r.index else ''
        if re.fullmatch(r'\d{10}|Contact No',role):continue
        for jid in resolve(co,role,dr,sh in GRP):
            s,why=score(c,jds[jid],role);items.append((c,jid,s,why,0,role,sh if isinstance(sh,str) else 'form'))
JM=[j for j in jds if j['c']!=OTH];npool=nomatch=0
for f,sh in POOL:                       # candidates with no JD: match to every JD they fit (score >= YELLOW, best 5)
    for r,c in load(f,sh):
        c['des']=(c['des']+' '+c['rt']).strip();bag=set(toks(c['sk']+' '+c['des'],LV));hits=[];npool+=1
        for j in JM:
            sh_=set(toks(j['t'],LV))&bag
            if not sh_ or (len(sh_)<2 and sh_<=GEN):continue
            s,why=score(c,j,'')
            if s>=YELLOW:hits.append((s,j['id'],why))
        if not hits:
            nomatch+=1;jid=other('Talent pool: no matching JD yet');s,why=score(c,jds[jid],'');hits=[(s,jid,why)]
        for s,jid,why in sorted(hits,reverse=True)[:5]:items.append((c,jid,s,why,1,c['rt'][:60],sh))
best={}
for it in items:                         # same person + same JD: explicit application beats pool match, then latest, then score
    c,jid,s=it[0],it[1],it[2];k=((c['em'] or c['ph'] or c['name']).lower(),jid);key=(1-it[4],c['ts'],s)
    if k not in best or key>best[k][0]:best[k]=(key,it)
people=[];pidx={};pl=[]
for _k,(c,jid,s,why,ispool,role,src) in best.values():
    i=pidx.get(id(c))
    if i is None:
        i=pidx[id(c)]=len(people);nm=c['name'][:60].strip()
        people.append(dict(n=nm.title() if nm.isupper() else nm,org=c['org'][:40],e=c['exp'][:40],loc=c['loc'][:40],np=c['np'][:25],em=c['em'],ph=c['ph'],cv=c['cv'],sk=c['sk'][:160],q=c['q'][:50],ct=c['ct'][:20],ex=c['ex'][:20],ts=c['ts'][:16],src=src,role=role,note=c['note'][:80],dt=c['dt'][:40],dp=c['dp'],ad=c['ad'][:110],pr=(c['pref'] or c['rl'])[:60]))
    pl.append([jid,i,s,why,ispool])
pl.sort(key=lambda r:(r[0],-r[2]))
json.dump(dict(cos=cos,jds=jds,people=people,pl=pl,thr=[GREEN,YELLOW]),open(OUT,'w'),ensure_ascii=False,separators=(',',':'))
if __name__=='__main__':
    import collections
    z=lambda s:'g' if s>=GREEN else 'y' if s>=YELLOW else 'r'
    print('placements',len(pl),'| people records',len(people),'| pool people',npool,'no JD fit',nomatch,'| size KB',os.path.getsize(OUT)//1024)
    t=collections.defaultdict(collections.Counter)
    for jid,i,s,w,pp in pl:t[cos[jds[jid]['c']]][z(s)]+=1;t[cos[jds[jid]['c']]]['pool' if pp else 'form']+=1
    for k,v in t.items():print(f"{k[:30]:30} form {v['form']:4} pool {v['pool']:4}  G{v['g']} Y{v['y']} R{v['r']}")
    cj=collections.Counter(r[0] for r in pl)
    print('top JDs:',[(jds[j]['t'][:34],n) for j,n in cj.most_common(8)])
