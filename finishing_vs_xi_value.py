"""finishing_vs_xi_value.py — 14/10/2026 (Στελιος: «οσο καλυτερη η ενδεκαδα (καλυτεροι παικτες), τοσο πιο πιθανο overperformance στο τελειωμα;»).
Ευρωπαικα ματς 2122-2526 (UCL/UEL/UECL) με ενδεκαδα (euro_squads: αξια βασικων FotMob) και σουτ (data_Europe): για καθε ομαδα
ΦΙΝΙΡΙΣΜΑ = γκολ − xG (χωρις πεναλτι), ανα ΑΠΟΛΥΤΗ αξια ενδεκαδας (πεμπτημορια) και ανα ποσοστο ενδεκαδας (rotation). + κλιση.
"""
import json, glob, math, numpy as np, pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
SQ = json.load(open('euro_squads.json', encoding='utf-8'))
rows = []
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        if not m.get('shots') or m.get('hs') is None or str(mid) not in SQ: continue
        sq = SQ[str(mid)]
        for side, key in (('home', 'h'), ('away', 'a')):
            x = sq.get(key) or {}
            if not x.get('mv'): continue
            tid = int(m[side]['id'])
            sh = [s for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == tid and s.get('sit') != 'Penalty']
            g_np = sum(1 for s in sh if s.get('goal')); xg = sum(s['xg'] for s in sh)
            rows.append(dict(comp=m.get('comp'), mv=float(x['mv']), g=g_np, xg=xg, n=len(sh)))
X = pd.DataFrame(rows); X['fin'] = X.g - X.xg
X['q'] = pd.qcut(X.mv, 5, labels=['1 φθηνοτερες', '2', '3', '4', '5 ακριβοτερες'])
se = lambda a: a.std() / np.sqrt(len(a))
print(f'ομαδες-ματς: {len(X)} · φινιρισμα (γκολ − xG, χωρις πεναλτι) ανα ΑΠΟΛΥΤΗ αξια ενδεκαδας:')
for k, x in X.groupby('q', observed=True):
    print(f'   {k:14s} n{len(x):5d} · αξια διαμεσος {x.mv.median() / 1e6:6.0f} εκ. · γκολ {x.g.mean():.2f} · xG {x.xg.mean():.2f} · φινιρισμα {x.fin.mean():+.3f} ±{se(x.fin):.3f} · ανα σουτ {100 * x.g.sum() / x.n.sum():.1f}% vs xG {100 * x.xg.sum() / x.n.sum():.1f}%')
b = np.polyfit(np.log(X.mv), X.fin, 1)[0]
print(f'   κλιση: {b:+.3f} γκολ ανα ×2.7 αξια ενδεκαδας ({b * math.log(2):+.3f} ανα διπλασιασμο)')
for cm, x in X.groupby('comp'):
    print(f'   {cm:18s} n{len(x):5d} · κλιση φινιρισματος {np.polyfit(np.log(x.mv), x.fin, 1)[0] * math.log(2):+.3f} ανα διπλασιασμο αξιας · μεσο {x.fin.mean():+.3f}')
