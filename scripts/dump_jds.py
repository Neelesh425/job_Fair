import json

d = json.load(open('data/data.json', encoding='utf-8'))
print('Companies:', d['cos'])
print()
print('Total JDs:', len(d['jds']))
print('Total people:', len(d['people']))
print('Thresholds:', d['thr'])
print()
print('All JDs:')
for j in d['jds']:
    co = d['cos'][j['c']] if j['c'] < len(d['cos']) else '?'
    print('  ['+str(j['id'])+'] '+co+' | '+j['t']+' | ty='+j['ty']+' | e='+str(j['e'])+' | l='+str(j['l']))
