# -*- coding: utf-8 -*-
"""el_absence_position_cost.py — EUROLEAGUE: ΠΟΣΟ ΚΟΣΤΙΖΕΙ ΜΙΑ ΑΠΟΥΣΙΑ ΑΝΑ ΘΕΣΗ × ΠΟΝΤΟΥΣ (28/10/2026, Στελιος «ποσο στοιχιζει περιπου μια απωλεια
γκαρντ με μ.ο. 12 ποντους, σεντερ με 13 ποντους κτλ»). ΠΕΡΙΓΡΑΦΙΚΟ — οχι κανονας για live.
Δειγμα: 1.563 ματς E2021-25 (live μοντελο, χωρις διορθωση απουσιων). Αποντας = ΝΕΑ απουσια (1ο-3ο ματς εκτος) ταχτικου που ΔΕΝ επαιξε (box).
Θεση: 3StepsBasket (Guard / Forward / Center, ιδια σεζον· αλλιως γειτονικη). Ποντοι/ματς: 10 τελευταια ματς του στη σεζον (≥3).
Κελια: 3 θεσεις × 4 κλιμακες (8-11, 11-14, 14-17, 17+ π/μ) = 12.
Μοντελο (ομαδα-ματς, γηπ. + φιλοξ. = 3.126 γραμμες): ποντοι ομαδας − μοντελο = Σ a_κελι × (αποντες ΔΙΚΟΙ της) + Σ d_κελι × (αποντες ΤΟΥ ΑΝΤΙΠΑΛΟΥ)
  + ελεγχος: λεπτα/40 των υπολοιπων αποντων (δικοι / αντιπαλου) · ridge 1.
  → για παικτη του κελιου που λειπει απο την ομαδα Χ: ποντοι Χ = a · ποντοι αντιπαλου = d · ΣΥΝΟΛΟ = a + d · ΧΑΝΤΙΚΑΠ (για τη Χ) = a − d.
± = τυπικο σφαλμα · «ιδια φορα» = σεζον (με ≥5 απουσιες στο κελι) οπου ο συντελεστης εχει την ιδια φορα με τον συνολικο.
Συγκριση: τι θα εδινε η μηχανη Α (συντελεστης −0.275 × [ποντοι − λεπτα × ρυθμος παγκου]) για τους ιδιους παικτες.
Εξοδος: el_absence_position_cost_out.txt"""
import os, sys, io, contextlib, collections, re, unicodedata, time
import numpy as np, pandas as pd
ROOT = r'C:\Users\steli\My Drive\Betting Model'; os.chdir(ROOT)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
T00 = time.time()
src = open('el_scorer_engine_test.py', encoding='utf-8').read().split("VERD = {}")[0]
src = src.replace("def P(s=''): print(s, flush=True); out.append(str(s))", "def P(s=''): pass").replace("def save(): open('el_scorer_engine_test_out.txt'", "def save_(): open('x'")
S = {}
with contextlib.redirect_stdout(_B()): exec(src, S)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
rows, ys, YH, YA, SE, NAME, recent = S['rows'], S['ys'], S['YH'], S['YA'], S['SE'], S['NAME'], S['recent']
N = len(rows)
# ---- θεσεις απο 3StepsBasket ----
def tok(s): return [w for w in re.split(r'[^a-z]+', unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()) if w]
D3 = pd.read_csv('el_onoff_3s.csv')
POS = collections.defaultdict(dict); BYS = collections.defaultdict(set)
for _, x in D3.iterrows():
    if not isinstance(x.position, str): continue
    k = (tuple(tok(x.surname)), (tok(x.firstname) or [''])[0][:1]); POS[k][int(str(x.season)[:4])] = x.position.capitalize(); BYS[k[0]].add(k)
def pos_of(pid, sea):
    nm = NAME.get(pid, ''); sur, fst = (nm.split(',', 1) + [''])[:2]; k = (tuple(tok(sur)), (tok(fst) or [''])[0][:1])
    if k not in POS:
        c = list(BYS.get(k[0], []))
        if len(c) != 1: return None
        k = c[0]
    y = int(sea[1:]); d = POS[k]
    for yy in (y, y - 1, y + 1, y - 2, y + 2):
        if yy in d: return d[yy]
    return next(iter(d.values()))
BR = [(8, 11), (11, 14), (14, 17), (17, 99)]; PS = ['Guard', 'Forward', 'Center']
PGR = {'Guard': 'γκαρντ', 'Forward': 'φοργουορντ', 'Center': 'σεντερ'}
CELLS = [(p, b) for p in PS for b in BR]; CI = {c: i for i, c in enumerate(CELLS)}
def blab(b): return f'{b[0]}-{b[1]}' if b[1] < 99 else f'{b[0]}+'
nC = len(CELLS)
OWN, OTH, EX = np.zeros((N, 2, nC)), np.zeros((N, 2)), []          # ανα ματς, ανα πλευρα (0 γηπ, 1 φιλοξ)
NOPOS = collections.Counter()
for j, r in enumerate(rows):
    for si, (own, team) in enumerate(((r['CH'], r['hc']), (r['CA'], r['ac']))):
        for p in own:
            if p['played']: continue
            rc = recent(r['y'], team, p['pid'], r['ts']) if p['k'] <= 3 else None
            ps = pos_of(p['pid'], r['y']) if rc and rc['ppg'] >= 8 else None
            if rc and rc['ppg'] >= 8: NOPOS[ps is None] += 1
            if ps is None:
                OTH[j, si] += p['w']; continue
            b = next(x for x in BR if x[0] <= rc['ppg'] < x[1]); c = CI[(ps, b)]; OWN[j, si, c] += 1
            EX.append((c, NAME.get(p['pid'], p['pid']), rc['ppg'], rc['mpg'], max(rc['ppg'] - rc['mpg'] * rc['br'], 0.0), r['y'], j, si))
P(f'el_absence_position_cost · Ευρωλιγκα 2021-25 · ματς {N} · νεες απουσιες ≥8 π/μ: με θεση {NOPOS[False]} · χωρις θεση {NOPOS[True]} (πανε στον ελεγχο) · {time.time() - T00:.0f} δευτ.')
# ---- σχεδιασμος: γραμμη ανα ομαδα-ματς ----
X = np.zeros((2 * N, 2 * nC + 2)); Y = np.zeros(2 * N); YS = np.r_[ys, ys]
for si, Yv in ((0, YH), (1, YA)):
    o = 1 - si; sl = slice(si * N, (si + 1) * N)
    X[sl, :nC] = OWN[:, si]; X[sl, nC:2 * nC] = OWN[:, o]; X[sl, 2 * nC] = OTH[:, si]; X[sl, 2 * nC + 1] = OTH[:, o]; Y[sl] = Yv
def fitr(m):
    A = X[m]; b = np.linalg.solve(A.T @ A + np.eye(A.shape[1]), A.T @ Y[m]); return b
b = fitr(np.ones(2 * N, bool)); res = Y - X @ b; s2 = res @ res / (len(Y) - X.shape[1])
V = s2 * np.linalg.inv(X.T @ X + np.eye(X.shape[1])); se = np.sqrt(np.diag(V))
PER = {s: fitr(YS == s) for s in SE}
cnt = OWN.sum(axis=(0, 1)); cnt_s = {s: OWN[ys == s].sum(axis=(0, 1)) for s in SE}
P(f'ελεγχος: αλλοι αποντες (λεπτα/40): δικοι {b[2 * nC]:+.2f} · αντιπαλου {b[2 * nC + 1]:+.2f} ποντοι ομαδας')
P('\n## ΚΟΣΤΟΣ ΑΝΑ ΚΕΛΙ (ποντοι, για την ομαδα που ΧΑΝΕΙ τον παικτη· ± τυπ. σφαλμα)')
P(f'  {"θεση / π/μ":20s} | απουσ. | ποντοι ομαδας | ποντοι αντιπαλου | ΣΥΝΟΛΟ ματς   | ΧΑΝΤΙΚΑΠ ομαδας | ιδια φορα (συνολο) | μηχανη Α (ομαδα=συνολο) | παραδειγματα')
for c, (ps, br) in enumerate(CELLS):
    a, d = b[c], b[nC + c]; ea, ed = se[c], se[nC + c]
    et = np.sqrt(V[c, c] + V[nC + c, nC + c] + 2 * V[c, nC + c]); em = np.sqrt(V[c, c] + V[nC + c, nC + c] - 2 * V[c, nC + c])
    ok = [s for s in SE if cnt_s[s][c] >= 5]; same = sum(np.sign(PER[s][c] + PER[s][nC + c]) == np.sign(a + d) for s in ok)
    ex = [e for e in EX if e[0] == c]; eng = -0.275 * np.mean([e[4] for e in ex]) if ex else 0.0
    top = collections.Counter(e[1] for e in ex).most_common(3)
    P(f'  {PGR[ps] + " " + blab(br):20s} | {int(cnt[c]):5d} | {a:+5.2f} ±{ea:4.2f}  | {d:+5.2f} ±{ed:4.2f}    | {a + d:+5.2f} ±{et:4.2f} | {a - d:+5.2f} ±{em:4.2f}   | {same}/{len(ok)}'
      f'                | {eng:+5.2f}                  | ' + ', '.join(f'{n.split(",")[0].title()} ({k})' for n, k in top))
# ---- ανα θεση (ολες οι κλιμακες) & ανα κλιμακα (ολες οι θεσεις): ιδιο μοντελο με λιγοτερα κελια ----
def grouped(key, labels, lab):
    G = {lb: [c for c, cc in enumerate(CELLS) if key(cc) == lb] for lb in labels}
    Xg = np.zeros((2 * N, 2 * len(G) + 2))
    for i, (lb, cs) in enumerate(G.items()):
        Xg[:, i] = X[:, cs].sum(1); Xg[:, len(G) + i] = X[:, [nC + c for c in cs]].sum(1)
    Xg[:, -2:] = X[:, -2:]
    bg = np.linalg.solve(Xg.T @ Xg + np.eye(Xg.shape[1]), Xg.T @ Y); rg = Y - Xg @ bg; Vg = rg @ rg / (len(Y) - Xg.shape[1]) * np.linalg.inv(Xg.T @ Xg + np.eye(Xg.shape[1]))
    P(f'\n## ΑΝΑ {lab}')
    for i, lb in enumerate(G):
        k = len(G); et = np.sqrt(Vg[i, i] + Vg[k + i, k + i] + 2 * Vg[i, k + i]); em = np.sqrt(Vg[i, i] + Vg[k + i, k + i] - 2 * Vg[i, k + i])
        n_ = int(sum(cnt[c] for c in G[lb])); pp = np.mean([e[2] for e in EX if e[0] in G[lb]])
        P(f'  {str(lb):12s} | απουσ. {n_:4d} (μ.ο. {pp:4.1f} π/μ) | ποντοι ομαδας {bg[i]:+5.2f} ±{np.sqrt(Vg[i, i]):.2f} | ποντοι αντιπαλου {bg[k + i]:+5.2f} ±{np.sqrt(Vg[k + i, k + i]):.2f} | '
          f'ΣΥΝΟΛΟ {bg[i] + bg[k + i]:+5.2f} ±{et:.2f} | ΧΑΝΤΙΚΑΠ {bg[i] - bg[k + i]:+5.2f} ±{em:.2f}')
grouped(lambda cc: PGR[cc[0]], [PGR[p] for p in PS], 'ΘΕΣΗ (ολες οι κλιμακες ποντων)')
grouped(lambda cc: blab(cc[1]), [blab(x) for x in BR], 'ΚΛΙΜΑΚΑ ΠΟΝΤΩΝ (ολες οι θεσεις)')
P(f'\nχρονος {time.time() - T00:.0f} δευτ.')
open('el_absence_position_cost_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
