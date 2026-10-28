# -*- coding: utf-8 -*-
"""el_travel_validation.py — ΕΛΕΓΧΟΣ ΤΟΥ LIVE ΚΑΝΟΝΑ ΤΑΞΙΔΙΟΥ (el_travel.py: 2ο ματς διαβολοβδομαδας, γηπ. σπιτι, φιλοξ. ≥1000 χλμ →
+4.5 απο εντος / +6.6 απο εκτος, μονο χαντικαπ) με 3 τεστ που δεν ειχαν γινει (28/10/2026, Στελιος «τρεξε ολα τα τεστ»).
1 ΕΠΑΝΑΛΗΨΗ σε ΣΕΖΟΝ ΠΟΥ Ο ΚΑΝΟΝΑΣ ΔΕΝ ΕΙΔΕ (E2017-E2020): παγωμενο παλιο μοντελο el_preds_all.csv (m_model, ιδιο για ολες τις σεζον),
  κανονικη περιοδος, οχι ουδετερα. Αποκλιση = (πραγματικη διαφορα − μοντελο) στα ματς του κανονα ΜΕΙΟΝ την ιδια αποκλιση στα υπολοιπα ματς
  της σεζον (αφαιρει τη μεροληψια εδρας του παλιου μοντελου). Ιδιος υπολογισμος και στο E2021-25 (εκει που βρεθηκε) για συγκριση.
  ΚΡΙΤΗΡΙΟ (προ-δηλωμενο): 2017-20 μαζι (εντος+εκτος) αποκλιση > 0 με t ≥ 1.5 ΚΑΙ θετικη σε ≥3/4 σεζον.
2 ΑΓΟΡΑ (E2021-25, Crown χαντικαπ): στα ματς του κανονα · ανοιγμα − live μοντελο (χωρις κανονα) · κινηση ανοιγμα→κλεισιμο προς τον γηπ.
  (vs υπολοιπα ματς) · πραγματικο − κλεισιμο. Πληροφορια.
3 WALK-FORWARD (E2022-25, live μοντελο el_newmodel_preds + Crown ανοιγμα, picks χαντικαπ ≥8%, σ 11.5): διορθωση καθε σεζον = μεση αποκλιση
  (πραγματικο − μοντελο) στα ματς του κανονα των ΠΡΟΗΓΟΥΜΕΝΩΝ σεζον (Α: μονο live σεζον απο E2021 · Β: + E2017-20 με το παλιο μοντελο),
  χωριστα εντος/εκτος (χωρις προηγουμενα → η τιμη του «εντος»). ΚΡΙΤΗΡΙΟ: μοναδες με κανονα ≥ χωρις ΚΑΙ θετικες ≥3/4 σεζον.
Εξοδος: el_travel_validation_out.txt"""
import os, sys, io, contextlib, json, pickle, math
import numpy as np, pandas as pd
from statistics import NormalDist
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT); sys.path.insert(0, ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
import el_travel
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
Phi = NormalDist().cdf
SCH = json.load(open('el_sched.json', encoding='utf-8'))
FLAG = {}
for sea, L in SCH.items():
    adj, miss = el_travel.adjustments(L, neutral=lambda x: bool(x.get('neutral')))
    for c, a in adj.items(): FLAG[f'{sea}_{c}'] = a
    if miss: P(f'  {sea}: γηπεδα χωρις συντεταγμενες {miss}')
OLD = pd.read_csv('el_preds_all.csv'); OLD = OLD[(OLD.phase == 'RS') & (OLD.neutral == 0)].copy()
OLD['frm'] = OLD.key.map(lambda k: FLAG[k]['frm'] if k in FLAG else None)
P('el_travel_validation · κανονας: 2ο ματς διαβολοβδομαδας, γηπ. επαιξε το προηγ. σπιτι, φιλοξ. ≥1000 χλμ (live +4.5 εντος / +6.6 εκτος)')
P('\n## 1 ΕΠΑΝΑΛΗΨΗ με το ΠΑΓΩΜΕΝΟ ΠΑΛΙΟ ΜΟΝΤΕΛΟ (αποκλιση ματς κανονα − αποκλιση υπολοιπων ματς ιδιας σεζον, ποντοι υπερ γηπεδουχου)')
P(f'  {"σεζον":6s} | απο εντος: ματς, αποκλιση | απο εκτος: ματς, αποκλιση | ολα του κανονα: ματς, αποκλιση')
def blk(df):
    base = df[df.frm.isna()].res.mean(); r = {}
    for lab, m in (('εντος', df.frm == 'εντος'), ('εκτος', df.frm == 'εκτος'), ('ολα', df.frm.notna())):
        x = df[m].res - base; r[lab] = (len(x), x.mean() if len(x) else np.nan, x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan)
    return r
PER = {}
for sea in sorted(OLD.season.unique()):
    r = blk(OLD[OLD.season == sea]); PER[sea] = r
    P(f'  {sea:6s} | {r["εντος"][0]:3d}, {r["εντος"][1]:+5.1f}             | {r["εκτος"][0]:3d}, {r["εκτος"][1]:+5.1f}             | {r["ολα"][0]:3d}, {r["ολα"][1]:+5.1f}')
for lab, ss in (('2017-20 (ΝΕΕΣ για τον κανονα)', ['E2017', 'E2018', 'E2019', 'E2020']), ('2021-25 (εκει που βρεθηκε)', ['E2021', 'E2022', 'E2023', 'E2024', 'E2025'])):
    parts = [OLD[OLD.season == s].assign(res=lambda d: d.res - d[d.frm.isna()].res.mean()) for s in ss]; X = pd.concat(parts)
    line = []
    for g, m in (('εντος', X.frm == 'εντος'), ('εκτος', X.frm == 'εκτος'), ('ολα', X.frm.notna())):
        x = X[m].res; se = x.std(ddof=1) / np.sqrt(len(x)); line.append(f'{g} {len(x)} ματς {x.mean():+.2f} ±{se:.2f} (t {x.mean() / se:+.1f})')
    pos = sum(1 for s in ss if PER[s]['ολα'][1] > 0)
    P(f'  ΜΑΖΙ {lab}: ' + ' · '.join(line) + f' · θετικες σεζον {pos}/{len(ss)}')
    if ss[0] == 'E2017':
        x = X[X.frm.notna()].res; t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
        P(f'  → ΚΡΙΤΗΡΙΟ επαναληψης (t ≥ 1.5 ΚΑΙ ≥3/4 σεζον): {"✓ ΕΠΑΝΑΛΑΜΒΑΝΕΤΑΙ" if t >= 1.5 and pos >= 3 else "✗ δεν επαναλαμβανεται"}')
OLDRES = {k: (r.season, r.frm, r.res - OLD[(OLD.season == r.season) & OLD.frm.isna()].res.mean()) for k, r in OLD[OLD.frm.notna()].set_index('key').iterrows()}
# ---- live μοντελο + Crown (E2021-25) ----
ns = {}
with contextlib.redirect_stdout(_B()): exec(open('el_line_timing.py', encoding='utf-8').read().split("lp = np.array(lastpre)")[0], ns)
sys.stdout.reconfigure(encoding='utf-8')
D, REC = ns['D'], ns['REC']; NP = pickle.load(open('el_newmodel_preds.pkl', 'rb'))
SE = ['E2021', 'E2022', 'E2023', 'E2024', 'E2025']; R = []
for pos, d_ in REC[21].items():
    x = D.iloc[pos]
    if x.season not in SE or x.phase != 'RS' or x.neutral: continue
    t = pd.Timestamp(D.t.values[pos]); k = (x.season, x.home, x.away, t.strftime('%Y-%m-%d %H:%M'))
    if k not in NP or NP[k].get('h_new') is None: continue
    f = FLAG.get(x.key)
    R.append(dict(key=x.key, sea=x.season, frm=f['frm'] if f else None, M=float(NP[k]['h_new']), act=float(x.hs - x.as_), op=d_['open'], cl=d_[0]))
R = pd.DataFrame(R); R['res'] = R.act - R.M; R['mo'] = R.op.map(lambda o: o[1]); R['mc'] = R.cl.map(lambda o: o[1])
P(f'\n## 2 ΑΓΟΡΑ (Crown χαντικαπ, E2021-25, live μοντελο χωρις τον κανονα) · ματς {len(R)} · του κανονα {int(R.frm.notna().sum())}')
for lab, m in (('απο εντος', R.frm == 'εντος'), ('απο εκτος', R.frm == 'εκτος'), ('ολα του κανονα', R.frm.notna()), ('υπολοιπα ματς', R.frm.isna())):
    d = R[m]
    P(f'  {lab:16s} ({len(d):4d}) · πραγματικο − μοντελο {d.res.mean():+5.2f} · ανοιγμα − μοντελο {(d.mo - d.M).mean():+5.2f} · κινηση ανοιγμα→κλεισιμο {(d.mc - d.mo).mean():+5.2f} · '
      f'πραγματικο − κλεισιμο {(d.act - d.mc).mean():+5.2f} · πραγματικο − ανοιγμα {(d.act - d.mo).mean():+5.2f}')
# ---- walk-forward ----
P('\n## 3 WALK-FORWARD (picks χαντικαπ ≥8% στο ανοιγμα Crown, ΜΟΝΟ τα ματς του κανονα· τα αλλα δεν αλλαζουν)')
def pick(M, op, act):
    L, o1, o2 = op[2], op[3], op[4]
    if abs(L - round(L)) < 1e-9: pw = Phi((M + L - .5) / 11.5); pl = Phi((-M - L - .5) / 11.5)
    else: pw = Phi((M + L) / 11.5); pl = 1 - pw
    pp = 1 - pw - pl; e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; sd, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    if e < .08: return 0, 0.0
    x = (act + L) * sd; return sd, (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
F = R[R.frm.notna()].copy()
base_rest = {s: R[(R.sea == s) & R.frm.isna()].res.mean() for s in SE}
def wf_adj(sea, frm, with_old):
    prior = [s for s in SE if s < sea]
    xs = [r.res - base_rest[r.sea] for r in F.itertuples() if r.sea in prior and r.frm == frm]
    if with_old: xs += [v[2] for v in OLDRES.values() if v[1] == frm]
    if len(xs) < 3:
        xs = [r.res - base_rest[r.sea] for r in F.itertuples() if r.sea in prior and r.frm == 'εντος'] + ([v[2] for v in OLDRES.values() if v[1] == 'εντος'] if with_old else [])
    return float(np.mean(xs)) if xs else 0.0
P('  διορθωσεις που θα εβγαιναν (εντος / εκτος): ' + ' · '.join(f"{s[-2:]}: Α {wf_adj(s, 'εντος', False):+.1f}/{wf_adj(s, 'εκτος', False):+.1f} · Β {wf_adj(s, 'εντος', True):+.1f}/{wf_adj(s, 'εκτος', True):+.1f}" for s in SE[1:]))
VAR = {'χωρις κανονα': lambda r: 0.0, 'live 4.5/6.6 (ειδε ολες τις σεζον)': lambda r: 4.5 if r.frm == 'εντος' else 6.6,
       'WF Α (μονο live σεζον)': lambda r: wf_adj(r.sea, r.frm, False), 'WF Β (+ 2017-20)': lambda r: wf_adj(r.sea, r.frm, True)}
RESW = {}
for nm, fa in VAR.items():
    per = {s: [] for s in SE}
    for r in F.itertuples():
        sd, u = pick(r.M + fa(r), r.op, r.act)
        if sd: per[r.sea].append(u)
    wf4 = SE[1:]; U = sum(sum(per[s]) for s in wf4); n = sum(len(per[s]) for s in wf4); RESW[nm] = (U, sum(1 for s in wf4 if sum(per[s]) > 0))
    P(f'  {nm:36s} 2022-25: picks {n:3d} · μοναδες {U:+6.1f} · θετικες {RESW[nm][1]}/4 · ανα σεζον ' + ' '.join(f'{s[-2:]}:{sum(per[s]):+.1f}({len(per[s])})' for s in SE)
      + f' │ ολες 2021-25 {sum(sum(v) for v in per.values()):+.1f}')
for nm in ('WF Α (μονο live σεζον)', 'WF Β (+ 2017-20)'):
    P(f'  ΚΡΙΤΗΡΙΟ {nm}: μοναδες ≥ χωρις ({RESW[nm][0]:+.1f} vs {RESW["χωρις κανονα"][0]:+.1f}) ΚΑΙ θετικες ≥3/4 ({RESW[nm][1]}/4) → '
      + ('✓' if RESW[nm][0] >= RESW['χωρις κανονα'][0] and RESW[nm][1] >= 3 else '✗'))
open('el_travel_validation_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
