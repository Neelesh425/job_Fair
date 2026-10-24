import sys
sys.stdout.reconfigure(encoding="utf-8")

HTML_PATH = r"c:\Users\neels\OneDrive\Desktop\k\job-fair-tracker\public\index.html"

with open(HTML_PATH, "r", encoding="utf-8") as f:
    content = f.read()

START = "/* ====== Experience Parsing & Strict Check ====== */"
END   = "\nconst jdOf=c=>"
s = content.find(START)
e = content.find(END)
assert s != -1 and e != -1, f"Markers not found: s={s} e={e}"
print(f"Patching chars {s} to {e}")

NEW = """/* ====== Experience Parsing & Strict Check ====== */
function parseYrs(t){
  if(!t)return null;
  t=t.toLowerCase();
  if(/fresh|no exp|nil|^0$/i.test(t))return 0;
  const ym=t.match(/(\\d+)\\s*year/);const mm=t.match(/(\\d+)\\s*month/);
  if(ym&&mm)return Math.round((parseInt(ym[1])+parseInt(mm[1])/12)*10)/10;
  const v=t.match(/\\d+(?:\\.\\d+)?/g);
  if(!v||parseFloat(v[0])>40)return null;
  if(/month/.test(t)&&!/year/.test(t)&&v.length===1)return Math.round(parseFloat(v[0])/12*10)/10;
  if(v.length>=2&&/\\d\\s*[-\\u2013to]\\s*\\d/.test(t))return(parseFloat(v[0])+parseFloat(v[1]))/2;
  return parseFloat(v[0]);
}
function parseExpRange(e,title){
  if(!e)e="";
  e=e.toLowerCase();title=(title||"").toLowerCase();
  if(/fresher/.test(e)&&/experience/.test(e))return null;
  if(/fresher/.test(e)||((/fresher/.test(title))&&!e))return[0,1];
  let m=e.match(/(\\d+)\\s*[\\u2013\\-]\\s*(\\d+)/);
  if(m)return[parseFloat(m[1]),parseFloat(m[2])];
  m=e.match(/(\\d+)\\s*(\\+|yr|year)/);
  return m?[parseFloat(m[1]),null]:null;
}
function expMatch(candExp,jdExp,jdTitle){
  const y=parseYrs(candExp);
  const rng=parseExpRange(jdExp,jdTitle);
  if(y===null||rng===null)return{match:"unknown",y,rng,strict:false};
  const[lo,hi]=rng;
  const inRange=y>=lo&&(hi===null||y<=hi+2);
  return{match:inRange?"yes":"no",y,rng,strict:!inRange};
}

/* ====== Qualification Red-Line Check ====== */
function qualMatch(candQ,jdQ){
  if(!jdQ||!jdQ.trim())return{ok:true,label:"No qualification requirement"};
  const q=(candQ||"").toLowerCase();
  const jq=jdQ.toLowerCase();
  const bcoms=["b.com","bcom","b com","bachelor of commerce","commerce graduate","commerce"];
  const mcom=["m.com","mcom","m com","master of commerce","postgraduate","pg"];
  const btech=["b.tech","btech","b tech","bachelor of technology","b.e","be"];
  const mba=["mba","master of business"];
  const mca=["mca","master of computer"];
  const anyGrad=["graduate","graduation","degree","bachelor"];
  const needsCommerce=bcoms.some(k=>jq.includes(k))||jq.includes("account")||jq.includes("finance");
  const hasBcom=bcoms.some(k=>q.includes(k));
  const hasMcom=mcom.some(k=>q.includes(k));
  const hasRelated=hasBcom||hasMcom||q.includes("commerce")||q.includes("account")||q.includes("finance")||q.includes("financial")||mba.some(k=>q.includes(k));
  const hasGrad=anyGrad.some(k=>q.includes(k))||hasBcom||hasMcom||btech.some(k=>q.includes(k))||mba.some(k=>q.includes(k))||mca.some(k=>q.includes(k))||q.includes("bsc")||q.includes("b.sc");
  if(needsCommerce){
    return{ok:hasRelated,label:hasRelated?"Qualification \u2713":"\u274c Qual red-line: Commerce/Accounting/Finance degree required"};
  }
  if(jq.includes("graduate")||jq.includes("bachelor")){
    return{ok:hasGrad,label:hasGrad?"Qualification \u2713":"\u274c Qual red-line: Graduate degree required"};
  }
  return{ok:true,label:"Qualification \u2713"};
}

/* ====== JD Skill Keyword Scoring ====== */
function jdSkillScore(c,j){
  if(!j||!j.sk)return{hits:0,total:0,pct:0,hitList:[],missList:[]};
  const candText=((c.sk||"")+" "+(c.q||"")+" "+(c.role||"")+" "+(c.org||"")).toLowerCase();
  const jdKeywords=j.sk.toLowerCase().split(/[\\s,\\/\\.\\-]+/).filter(w=>w.length>2);
  const unique=[...new Set(jdKeywords)];
  let hits=0;const hitList=[];const missList=[];
  unique.forEach(kw=>{
    const matched=candText.includes(kw)||(kw.length>5&&(candText.includes(kw.slice(0,5))||candText.includes(kw.slice(0,-2))));
    if(matched){hits++;hitList.push(kw);}else{missList.push(kw);}
  });
  const pct=unique.length>0?Math.round(hits/unique.length*100):0;
  return{hits,total:unique.length,pct,hitList,missList};
}

/* ====== AI zone (experience, qualification & skill red-lines) ====== */
function ai(c,j){
  if(c._ai&&c._ai_jid===j?.id)return c._ai;
  const base=c._a||(c._a={s:c.sc,z:c.sc>=D.thr[0]?"g":(c.sc>=D.thr[1]?"y":"r"),r:c.rs});
  if(!j){c._ai=base;c._ai_jid=null;return base}
  const dc=disCheck(c);
  const em=expMatch(c.e,j.e,j.t);
  const qm=qualMatch(c.q,j.q||"");
  const isPool=c.pool||(c.sc===50&&!(c.rs&&c.rs.length>10));
  let s=base.s;
  let reasons=[base.r||""];
  if(isPool&&j.sk){
    const sk=jdSkillScore(c,j);
    s=30+Math.round(sk.pct*0.6);
    reasons=["Skill match: "+sk.pct+"% ("+sk.hits+"/"+sk.total+" keywords)"];
    if(sk.hitList.length)reasons.push("\u2713 "+sk.hitList.slice(0,5).join(", "));
    if(sk.missList.length>0&&sk.missList.length<=5)reasons.push("\u2717 Missing: "+sk.missList.join(", "));
    else if(sk.missList.length>5)reasons.push("\u2717 Missing "+sk.missList.length+" skills");
  }
  // RED LINE 1: disability
  if(!dc.ok){
    reasons.push("\u26a0 Disability: "+dc.label);
    if(s>=D.thr[0])s=D.thr[0]-1;
  }
  // RED LINE 2: experience
  if(em.strict){
    reasons.push("[EXP RED-LINE] "+em.y+"yrs vs JD "+(j.e||"not specified"));
    if(s>=D.thr[0])s=D.thr[0]-1;
    s=Math.min(s,D.thr[1]-1);
  }
  // RED LINE 3: qualification
  if(!qm.ok){
    reasons.push(qm.label);
    if(s>=D.thr[0])s=D.thr[0]-1;
  }
  const z=s>=D.thr[0]?"g":(s>=D.thr[1]?"y":"r");
  const result={s,z,r:reasons.join("; ")};
  c._ai=result;c._ai_jid=j?.id;
  return result;
}
"""

out = content[:s] + NEW + content[e:]
print(f"New length: {len(out)}")

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(out)

# Verify
with open(HTML_PATH, "r", encoding="utf-8") as f:
    v = f.read()
assert len(v) > 100000, "File too small!"
assert "AI zone (experience, qualification" in v, "New marker missing!"
assert "qualMatch" in v, "qualMatch missing!"
assert "jdSkillScore" in v, "jdSkillScore missing!"
assert "RED LINE 3" in v, "RED LINE 3 missing!"
print("All checks passed!")
