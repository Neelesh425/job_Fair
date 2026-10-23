import json

d = json.load(open('data/data.json', encoding='utf-8'))

# Print a few sample people to understand the data structure
print('=== Sample People Fields ===')
for i in range(3):
    p = d['people'][i]
    print('Keys available:', list(p.keys()))
    print(json.dumps(p, indent=2, default=str)[:500])
    print()

# Check how many people we have and what unique experience values there are
print('=== Experience Values (sample) ===')
exp_vals = {}
for p in d['people']:
    e = str(p.get('e', '')).strip()
    if e not in exp_vals:
        exp_vals[e] = 0
    exp_vals[e] += 1

# Sort by count
sorted_exp = sorted(exp_vals.items(), key=lambda x: -x[1])
for e, c in sorted_exp[:30]:
    print(repr(e) + ' -> ' + str(c))

print()
print('=== Checking for CGPA / batch year fields ===')
for p in d['people'][:10]:
    print('n='+str(p.get('n',''))+' q='+str(p.get('q',''))+' batch='+str(p.get('batch','N/A'))+' cgpa='+str(p.get('cgpa','N/A')))
