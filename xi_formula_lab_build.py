# -*- coding: utf-8 -*-
"""xi_formula_lab_build.py — 21/10/2026 (Στελιος: «lineup lab με τη νεα φορμουλα — προβλεπομενη (predicted11) και επισημη 11αδα, οι αλλαγες
κατευθειαν πανω στις τιμες»). Χτιζει το xi_formula_lab.json για το dashboard (Lineup Lab):
  για καθε ομαδα CORE7: η ΣΥΝΗΘΙΣΜΕΝΗ 11αδα (11 με τα περισσοτερα λεπτα στα 10 τελευταια ματς πρωταθληματος: 1 τερματοφυλακας + 10)
  και για καθε παικτη (ροστερ Lineup Lab + οσοι επαιξαν στα 10 ματς): [θεση, εμπιστοσυνη, ln(αξια), xGI/90].
  Συντελεστες = xi_formula (G_V, G_T, B). Τρεχει καθε πρωι στο data-refresh μετα το lineup_lab_data."""
import os, sys, json, math, collections, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import xi_formula as XF
ROOT = os.path.dirname(os.path.abspath(__file__))
S = XF.state()
lab = json.load(open(os.path.join(ROOT, 'lineup_lab.json'), encoding='utf-8'))
teams = {}
for tid_s, t in lab['teams'].items():
    tid = int(tid_s); hist = S['team_hist'].get(tid, [])[-10:]
    if len(hist) < 4: continue
    mins = collections.Counter()
    for h in hist:
        for p, mn in h.items(): mins[p] += mn
    pool = [p for p, mn in mins.most_common() if mn > 0]
    usual = [p for p in pool if S['pos'].get(p, 2) == 0][:1] + [p for p in pool if S['pos'].get(p, 2) != 0][:10]
    ids = {str(p['id']) for p in t['players']} | set(pool)
    pl = {}
    for p in ids:
        ins = [h[p] for h in hist if p in h]
        trust = sum(ins) / (90.0 * len(ins)) if ins else 0.3
        v = S['val'].get(p); s = S['xgi'].get(p); pos = S['pos'].get(p)
        if pos is None:
            pos = next((q['pos'] for q in t['players'] if str(q['id']) == p), 2)
        m = S['mu'].get(pos, 0.25)
        pl[p] = [pos, round(trust, 3), round(math.log(v), 3) if v else None, round((s[0] + 5 * m) / (s[1] + 5) if s else m, 3)]
    teams[tid_s] = dict(name=t.get('name'), usual=usual, players=pl, n_hist=len(hist))
out = dict(built=dt.datetime.now(dt.timezone.utc).isoformat()[:16], G_V=XF.G_V, G_T=XF.G_T, B=XF.B, teams=teams,
           note='Δ = 11αδα − συνηθισμενη · χαντικαπ: G_V·ΔV + G_T·ΔT (γηπ − φιλ) · συνολα: Σ B_k·(Δk γηπ + Δk φιλ)')
json.dump(out, open(os.path.join(ROOT, 'xi_formula_lab.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(f'xi_formula_lab.json: {len(teams)} ομαδες')
