# -*- coding: utf-8 -*-
"""toa_vs_nowgoal.py — Ειναι παρομοιες οι πηγες αποδοσεων; (παιγμενα ματς 26/27)

Συγκρινει στις ~KO−24h:
  - The Odds API Pinnacle  vs nowgoal Crown  (οι δυο «sharp» πηγες μας)
  - The Odds API Bet365    vs nowgoal Bet365 (ιδιο βιβλιο, δυο καταγραφες — καθαρο τεστ)
σε: γραμμη AH (προοπτικη γηπεδουχου), αποδοσεις, και no-vig πιθανοτητα γηπεδουχου.

TOA: toa_hist_2627.jsonl (snapshot στις KO−24h). Nowgoal: τελευταιο snapshot <= cm−24h.
"""
import sys, json, datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
from nowgoal_merged import load_traj

LGS = ['EPL', 'LaLiga', 'SerieA']

# ---- δικα μας ματς (για ονοματα/mids/KO) ----
Mc, id2name = picks.load_matches(LGS, ['2627'])
ko_map = {}
for lg in LGS:
    d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
    for m in d.values():
        ko = datetime.datetime.strptime(m['date'], '%a, %b %d, %Y, %H:%M UTC').replace(
            tzinfo=datetime.timezone.utc)
        ko_map[str(m['mid'])] = ko

# ---- TOA snapshots ----
toa = {}   # (lg, req_ts) -> events
for line in open('toa_hist_2627.jsonl', encoding='utf-8'):
    r = json.loads(line)
    toa[(r['lg'], r['req_ts'])] = r['events']


def toa_match(lg, ko, home_nm, away_nm):
    """Βρες το event του ματς στο snapshot του KO−24h (ταιριασμα με norm tokens)."""
    req_ts = (ko - datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
    evs = toa.get((lg, req_ts))
    if not evs:
        return None
    hn, an = picks.norm(home_nm), picks.norm(away_nm)
    best = None
    for ev in evs:
        eh, ea = picks.norm(ev['home_team']), picks.norm(ev['away_team'])
        sc = len(hn & eh) + len(an & ea)
        if sc >= 1 and (best is None or sc > best[0]):
            best = (sc, ev)
    return best[1] if best else None


def toa_spread(ev, bk):
    for b in ev.get('bookmakers', []):
        if b.get('key') != bk:
            continue
        for m in b.get('markets', []):
            if m.get('key') == 'spreads':
                hp = ho = ao = None
                for o in m.get('outcomes', []):
                    if o.get('name') == ev['home_team']:
                        hp = o.get('point'); ho = o.get('price')
                    elif o.get('name') == ev['away_team']:
                        ao = o.get('price')
                if hp is not None and ho and ao:
                    return float(hp), float(ho), float(ao)
    return None


def ng_at24(tr):
    if not tr:
        return None
    cm = tr[-1][0]
    past = [x for x in tr if x[0] <= cm - 24 * 3600]
    if not past:
        return None
    e = past[-1]
    return e[1], e[2], e[3]     # line (γηπεδουχου), oh, oa


def novig_h(oh, oa):
    return (1 / oh) / (1 / oh + 1 / oa)


NG3 = load_traj('2627', 3)
NG8 = load_traj('2627', 8)

rows = []
for _, m in Mc.iterrows():
    mid = str(m['mid'])
    ko = ko_map.get(mid)
    if ko is None:
        continue
    ev = toa_match(m['league'], ko, id2name.get(m['home'], ''), id2name.get(m['away'], ''))
    if not ev:
        continue
    for tag, bk, src in (('Pinnacle↔Crown', 'pinnacle', NG3), ('Bet365↔Bet365', 'bet365', NG8)):
        tsp = toa_spread(ev, bk)
        ngs = ng_at24(src.get(mid))
        if not tsp or not ngs:
            continue
        tl, th, ta = tsp
        nl, nh, na = ngs
        rows.append(dict(lg=m['league'], mid=mid, pair=tag,
                         toa_line=tl, ng_line=nl, dline=tl - nl,
                         dph=novig_h(th, ta) - novig_h(nh, na),
                         toa=f'{tl:+.2f} {th:.2f}/{ta:.2f}', ng=f'{nl:+.2f} {nh:.2f}/{na:.2f}'))

D = pd.DataFrame(rows)
print(f'ζευγαρωμενα σημεια συγκρισης: {len(D)} ({D.mid.nunique()} ματς)')
print()
for pair in ('Pinnacle↔Crown', 'Bet365↔Bet365'):
    g = D[D.pair == pair]
    if not len(g):
        continue
    same = (g.dline.abs() < 0.01).mean() * 100
    q = (g.dline.abs() <= 0.25).mean() * 100
    print(f'=== {pair} (n={len(g)}) ===')
    print(f'  γραμμη: ιδια {same:.0f}% · εντος 0.25 {q:.0f}% · μεση |Δ| {g.dline.abs().mean():.3f} γκολ · μεγιστη {g.dline.abs().max():.2f}')
    print(f'  no-vig πιθ. γηπεδουχου: μεση Δ {g.dph.mean()*100:+.2f}pp · μεση |Δ| {g.dph.abs().mean()*100:.2f}pp · max |Δ| {g.dph.abs().max()*100:.2f}pp')
    bad = g[g.dline.abs() > 0.25].sort_values('dline', key=abs, ascending=False)
    if len(bad):
        print('  αποκλισεις γραμμης >0.25:')
        for _, r in bad.head(8).iterrows():
            hn = id2name.get(int(Mc[Mc.mid == r.mid].iloc[0]['home']), '?')
            an = id2name.get(int(Mc[Mc.mid == r.mid].iloc[0]['away']), '?')
            print(f'    {r.lg:7s} {hn[:16]:16s}-{an[:16]:16s}  TOA {r.toa}  ·  nowgoal {r.ng}')
    print()
