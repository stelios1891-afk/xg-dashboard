# -*- coding: utf-8 -*-
"""
nowgoal_sa_remap.py -- μετα το nowgoal_sa_fetch.py:
  1. ξανατρεχει το ταιριασμα FotMob (nowgoal_sa_map.py --remap-only) -> nowgoal_sa_map.json
  2. ξαναγραφει το mid στα nowgoal_odds/{ετος}_{Brazil|MLS}.jsonl και στο nowgoal_sa_1x2.jsonl (mid=FotMob mid αν ταιριαζει, αλλιως ng<id>)
  3. ενωνει τα nowgoal_sa_1x2_{lg}.jsonl -> nowgoal_sa_1x2.jsonl (χωρις placeholders)
  4. τυπωνει συνοψη ανα λιγκα/σεζον
ΜΗΝ τρεξει ενω τρεχει το fetch. Χρηση: python nowgoal_sa_remap.py [--no-remap]
"""
import sys, os, json, glob, re, subprocess, statistics, datetime as dt
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if '--no-remap' not in sys.argv:
    subprocess.run([sys.executable, 'nowgoal_sa_map.py', '--remap-only'], check=True, stdout=subprocess.DEVNULL)
M = json.load(open('nowgoal_sa_matches.json', encoding='utf-8'))
MAP = json.load(open('nowgoal_sa_map.json', encoding='utf-8'))
FM = {str(v['ng']): k for k, v in MAP.items()}


def newmid(ng):
    return FM.get(str(ng), f'ng{ng}')


# 2. mid στα odds αρχεια
S = defaultdict(lambda: defaultdict(lambda: dict(ah={}, ou={}, x=False)))      # (lg,sea) -> ng -> info
for fp in sorted(glob.glob('nowgoal_odds/*_Brazil.jsonl') + glob.glob('nowgoal_odds/*_MLS.jsonl')):
    if fp.endswith('_deep.jsonl'):
        continue
    sea, lg = re.match(r'(\d{4})_(Brazil|MLS)\.jsonl', os.path.basename(fp)).groups()
    out = []
    for ln in open(fp, encoding='utf-8'):
        r = json.loads(ln); r['mid'] = newmid(r['ng']); out.append(json.dumps(r, ensure_ascii=False))
        d = S[(lg, sea)][r['ng']]
        d['ah'][r['cid']] = r['ah']; d['ou'][r['cid']] = r['ou']
    open(fp + '.tmp', 'w', encoding='utf-8').write('\n'.join(out) + '\n'); os.replace(fp + '.tmp', fp)
# 3. 1x2
n1 = 0; seen = set()
with open('nowgoal_sa_1x2.jsonl.tmp', 'w', encoding='utf-8') as fo:
    for fp in sorted(glob.glob('nowgoal_sa_1x2_*.jsonl')):
        for ln in open(fp, encoding='utf-8'):
            r = json.loads(ln)
            if r.get('book') is None or (r['ng'], r['book']) in seen:
                continue
            seen.add((r['ng'], r['book'])); r['mid'] = newmid(r['ng'])
            fo.write(json.dumps(r, ensure_ascii=False) + '\n'); n1 += 1
            m = M.get(str(r['ng']))
            if m and r.get('rows'):
                S[(m['lg'], m['sea'])][r['ng']]['x'] = True
os.replace('nowgoal_sa_1x2.jsonl.tmp', 'nowgoal_sa_1x2.jsonl')
print('nowgoal_sa_1x2.jsonl:', n1, 'γραμμες')

# 4. συνοψη
cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
mapped_by = defaultdict(int)
for k, v in MAP.items():
    m = M.get(str(v['ng']))
    if m:
        mapped_by[(m['lg'], m['sea'])] += 1
print('\nlg    sea  NG_ματς NG_παιγμενα fetched CrownAH SboAH CrownOU SboOU 1X2   med_h_open(Crown) med_h_open(Sbo)  FotMob_mapped')
for lg in ('Brazil', 'MLS'):
    for sea in map(str, range(2021, 2027)):
        allm = [n for n, m in M.items() if m['lg'] == lg and m['sea'] == sea]
        played = [n for n in allm if M[n]['dt_utc'] <= cut]
        info = S.get((lg, sea), {})
        def cnt(f): return sum(1 for d in info.values() if f(d))
        def med(cid):
            hs = []
            for ng, d in info.items():
                rows = d['ah'].get(cid) or []
                if rows:
                    k = dt.datetime.strptime(M[str(ng)]['dt_utc'], '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone.utc).timestamp()
                    hs.append((k - min(r[0] for r in rows)) / 3600)
            return f'{statistics.median(hs):.1f}' if hs else '-'
        print(f"{lg:6} {sea} {len(allm):5} {len(played):8} {len(info):8} {cnt(lambda d: d['ah'].get(3)):7} {cnt(lambda d: d['ah'].get(31)):5} "
              f"{cnt(lambda d: d['ou'].get(3)):7} {cnt(lambda d: d['ou'].get(31)):5} {cnt(lambda d: d['x']):4} {med(3):>14} {med(31):>16}  "
              f"{mapped_by.get((lg, sea), 0)}/{len(played)}")
