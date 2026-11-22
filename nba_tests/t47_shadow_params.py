# -*- coding: utf-8 -*-
"""t47_shadow_params.py — ΠΑΡΑΜΕΤΡΟΙ για τις 2 ΣΚΙΕΣ συνολων (21/10/2026, Στελιος «υψομετρο ντενβερ γιουτα περνα το σε σκια και τους διαιτητες σε σκια»).
 ΥΨΟΜΕΤΡΟ: Μ2δ + β·[εντος DEN/UTA] (ridge λ50, ολα τα ματς 5σ, ανοιγμα) → β.
 ΔΙΑΙΤΗΤΕΣ: δεικτης διαιτητη = μεσο (πραγμ − αγορα ανοιγματος) στα 60 τελευταια ματς του (≥20) × n/(n+40) (t42)· τριαδα = μεσος (≥2 γνωστοι)·
   Μ2δ + γ·τριαδα → γ. Πινακας δεικτων ΟΠΩΣ ΕΙΝΑΙ στο τελος της 2025-26 (στατικος· ανανεωση με νεα ματς αργοτερα).
Εξοδος: nba_totals_extra_shadow.json (ριζα)."""
import os, sys, io, json, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't36_totals_diag.py'), encoding='utf-8').read().split("P(''); P('=== ΜΗΧΑΝΕΣ (LOSO) ===')")[0]
src = src.replace("out = []\ndef P(s=''): print(s, flush=True); out.append(str(s))", "out = []\ndef P(s=''): pass")
with contextlib.redirect_stdout(_B()): exec(src)
sys.stdout.reconfigure(encoding='utf-8')
D = X[X.tau == 'ανοιγμα'].reset_index(drop=True).copy(); D['dd'] = pd.to_datetime(D.date); D = D.sort_values('dd').reset_index(drop=True)
REF = {}
for s in (2022, 2023, 2024, 2025, 2026):
    for ln in open(os.path.join(ROOT, f'nba_refs/refs_{s}.jsonl'), encoding='utf-8'):
        r = json.loads(ln); REF[(r['date'], r['home'])] = r['refs']
def refs_of(d, h):
    for k in (0, -1, 1):
        x = REF.get(((pd.Timestamp(d) + pd.Timedelta(days=k)).strftime('%Y-%m-%d'), h))
        if x: return x
    return None
D['refs'] = [refs_of(d, h) for d, h in zip(D.date, D.home)]; D['res'] = D.tot - D.fair
hist = collections.defaultdict(list); crew = []
for r in D.itertuples(index=False):
    v = [np.mean(hist[n][-60:]) * len(hist[n][-60:]) / (len(hist[n][-60:]) + 40) for n in (r.refs or [])[:3] if len(hist[n]) >= 20]
    crew.append(np.mean(v) if len(v) >= 2 else 0.0)
    for n in (r.refs or [])[:3]: hist[n].append(r.res)
D['crew'] = crew; D['alt'] = D.home.isin(['DEN', 'UTA']).astype(float)
y = D.res.values; base = np.c_[feats(D), (D.mon == 4).astype(float)]
def fit(Xv):
    A = np.c_[np.ones(len(D)), Xv]; return np.linalg.solve(A.T @ A + 50 * np.eye(A.shape[1]), A.T @ y)
b_alt = fit(np.c_[base, D.alt])[-1]; b_ref = fit(np.c_[base, D.crew])[-1]
IDX = {n: dict(v=round(float(np.mean(h[-60:]) * len(h[-60:]) / (len(h[-60:]) + 40)), 3), n=len(h)) for n, h in hist.items() if len(h) >= 20}
J = dict(created='2026-10-21', src='nba_tests/t47 (t41 Π2 υψομετρο, t42 διαιτητες), ridge λ50 πανω στη Μ2δ, ανοιγμα Crown 2021-26',
         alt_teams=['DEN', 'UTA'], alt_coef=round(float(b_alt), 3), ref_coef=round(float(b_ref), 3), ref_index=IDX,
         note='ΣΚΙΕΣ: Μ2δ + alt_coef·[εντος DEN/UTA] · Μ2δ + ref_coef·(μεσος δεικτης τριαδας, ≥2 γνωστοι, αλλιως 0)')
json.dump(J, open(os.path.join(ROOT, 'nba_totals_extra_shadow.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'υψομετρο β {b_alt:+.2f} · διαιτητες γ {b_ref:+.2f} · διαιτητες με δεικτη {len(IDX)} · sd δεικτη {np.std([v["v"] for v in IDX.values()]):.2f}')
