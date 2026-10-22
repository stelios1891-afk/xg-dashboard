# -*- coding: utf-8 -*-
"""t62_value_combos.py — ΠΟΙΟΣ ΔΕΙΚΤΗΣ / ΣΥΝΔΥΑΣΜΟΣ ΓΙΑ ΤΗΝ ΠΕΡΣΙΝΗ ΑΞΙΑ ΑΠΟΝΤΑ (22/10/2026, εγκριθηκε απο Στελιο).
Σημερα: περσινη αξια = ΑΠΛΟΣ μεσος DARKO dpm / LEBRON / BPM (value() στο nba_roster_adj.py) × λεπτα/(λεπτα+500) (MPT, περσινα RS λεπτα), αγνωστος −1.
ΔΙΟΡΘΩΣΗ BPM (μονο μεσα στο τεστ): το regex του nba_roster_adj αποτυγχανει οταν bpm ή mp ειναι σε <strong> (πρωτος λιγκας) → κρατιεται
  η γραμμη των PLAYOFFS (πινακας advanced_post). ΣΩΣΤΟ BPM = μονο html ΠΡΙΝ το 'id="advanced_post"', αφαιρεση <strong>/</strong> πριν το regex,
  πολλες γραμμες (ανταλλαγες) → αυτη με τα περισσοτερα mp. Ελεγχος: Jokić 2021 12.1 · 2022 13.7 · 2025 13.3 · Randle 2021 3.8.
ΕΚΔΟΧΕΣ βασης (ετος s−1, μεσος ΔΙΑΘΕΣΙΜΩΝ δεικτων της εκδοχης × mp/(mp+500), κανενας → −1):
  1 DARKO · 2 LEBRON · 3 BPM(σωστο) · 4 DARKO+LEBRON · 5 DARKO+BPM · 6 LEBRON+BPM · 7 ολοι (σωστο BPM) · ref = σημερινο value() (λαθος BPM).
ΜΗΧΑΝΗ: t59_inseason_value.py (exec ως 'def vmix(M):' με T59_CACHE) → ιδια ματς/απουσιες/φετινη box (FIT εκπαιδευμενο σε ref value, s′ < s, ΑΜΕΤΑΒΛΗΤΟ).
  Αλλαζει ΜΟΝΟ η βαση (vprev). ΚΥΡΙΑ: μιξη M=500: v = (λεπτα_φετος·v_box + 500·βαση)/(λεπτα_φετος + 500) (χωρις φετινο box → βαση).
  Δευτερευον: βαση μονη (M=∞). Κοστος = w·0.75·(v+2)·λεπτα/48 · μοντελο = m0 − κοστος_γηπ + κοστος_φιλ.
  Picks χαντικαπ στο ανοιγμα edge ≥8%, σ 13.5. ΕΛΕΓΧΟΣ: ref με M=500 → +164.6 μοναδες, 2996 picks (t59 LOSO). Αλλιως σταματα.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ το τρεξιμο):
  (1) LOSO: σε καθε σεζον-τεστ διαλεγεται η εκδοχη (1-7) με το μικροτερο RMSE (act − μοντελο) στις αλλες 4 → ποσο συχνα ιδια επιλογη,
      και αποτελεσμα (RMSE, picks) στη σεζον-τεστ.
  (2) Μια εκδοχη ΑΝΤΙΚΑΘΙΣΤΑ την «7 ολοι (σωστο BPM)» αν: RMSE καλυτερο απο το 7 σε ≥4/5 σεζον ΚΑΙ μοναδες picks ≥ του 7 ΚΑΙ θετικες σεζον ≥4/5
      (στη ΚΥΡΙΑ μετρηση M=500).
  (3) Αν καμια → μενει το 7.
  Περιγραφικα: RMSE ολικο και ΔRMSE ανα σεζον vs 7, κλιση κοστους (act − m0 πανω στο καθαρο κοστος, ±ΤΣ), ROI/n/μοναδες, μοναδες ανα σεζον,
  θετικες σεζον, εγγραφες αποντων στο −1 λογω ελλειψης δεικτη, ref για συγκριση, Δμοναδες vs 7 ±ΤΣ (ζευγαρωτα ανα ματς).
ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ: Jokić (2024-25 ή 2025-26), ενας με μεγαλη διαφορα αναμεσα σε δεικτες, ενας χωρις LEBRON: τιμη καθε δεικτη, καθε εκδοχης, κοστος.
Εξοδος: t62_value_combos_out.txt"""
import os, sys, io, re, contextlib, collections
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
# ---- t59 ως vmix (cache) ----
src = open(os.path.join(SC, 't59_inseason_value.py'), encoding='utf-8').read().split('def vmix(M):')[0]
g = {'__file__': os.path.join(SC, 't59_inseason_value.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
AB_, D, NM = g['AB_'], g['D'], g['NM']
# ---- nba_roster_adj (M, MPT, value, nk, NAME2PID) ----
cwd = os.getcwd(); os.chdir(ROOT)
rsrc = open(os.path.join(ROOT, 'nba_roster_adj.py'), encoding='utf-8').read().split('OUT, ABS = {}, {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
R = {}
with contextlib.redirect_stdout(_B()): exec(rsrc, R)
VM, MPT, value, nk, NAME2PID = R['M'], R['MPT'], R['value'], R['nk'], R['NAME2PID']
# ---- ΣΩΣΤΟ BPM ----
rows = []
for y in range(2020, 2026):
    fn = os.path.join(ROOT, 'bbref_cache', f'NBA_{y}_advanced.html')
    if not os.path.exists(fn): continue
    t = open(fn, encoding='utf-8', errors='ignore').read()
    k = t.find('id="advanced_post"'); t = t[:k] if k >= 0 else t
    t = t.replace('<strong>', '').replace('</strong>', '')
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
        nm = re.search(r'data-stat="name_display"[^>]*>(?:<a[^>]*>)?([^<]+)', tr)
        b = re.search(r'data-stat="bpm"[^>]*>([-\d.]+)<', tr); mp = re.search(r'data-stat="mp"[^>]*>(\d+)<', tr)
        if nm and b and mp: rows.append((nk(nm.group(1)), y, float(b.group(1)), int(mp.group(1)), nm.group(1)))
os.chdir(cwd)
br = pd.DataFrame(rows, columns=['k', 'y', 'bpm', 'mp', 'nm']).sort_values('mp', ascending=False).drop_duplicates(['k', 'y'])
BPMC = {(NAME2PID[k], y): v for k, y, v in zip(br.k, br.y, br.bpm) if k in NAME2PID}
IDX = {'DARKO': VM['DARKO'], 'LEBRON': VM['LEBRON'], 'BPM': BPMC, 'BPMold': VM['BPM']}
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
P('t62 — περσινη αξια αποντα: ποιος δεικτης/συνδυασμος (NBA, σεζον 2022-2026 = 2021-22 … 2025-26)')
# ελεγχος BPM
P(''); P('ΕΛΕΓΧΟΣ ΔΙΟΡΘΩΣΗΣ BPM (bbref, κανονικη περιοδος):')
def bpm_of(name, y, Dm):
    p = NAME2PID.get(nk(name)); return Dm.get((p, y)) if p else None
for name, y, tgt in (('Nikola Jokić', 2021, 12.1), ('Nikola Jokić', 2022, 13.7), ('Nikola Jokić', 2025, 13.3), ('Julius Randle', 2021, 3.8)):
    P(f'  {name} {y}: BPM σωστο {bpm_of(name, y, BPMC)} (στοχος {tgt}) · BPM σημερινο (λαθος) {bpm_of(name, y, VM["BPM"])}')
cm = [k for k in BPMC if k in VM['BPM']]
dif = [k for k in cm if abs(BPMC[k] - VM['BPM'][k]) > 1e-9]
P(f'  ζευγαρια (παικτης, ετος) με BPM: σωστο {len(BPMC)} · σημερινο {len(VM["BPM"])} · κοινα {len(cm)} · με διαφορετικη τιμη {len(dif)} '
  f'· μονο στο σωστο {len(set(BPMC) - set(VM["BPM"]))} · μονο στο σημερινο {len(set(VM["BPM"]) - set(BPMC))}')
# ---- εκδοχες ----
VER = collections.OrderedDict([('1 DARKO', ['DARKO']), ('2 LEBRON', ['LEBRON']), ('3 BPM', ['BPM']), ('4 DARKO+LEBRON', ['DARKO', 'LEBRON']),
                               ('5 DARKO+BPM', ['DARKO', 'BPM']), ('6 LEBRON+BPM', ['LEBRON', 'BPM']), ('7 ολοι', ['DARKO', 'LEBRON', 'BPM']),
                               ('ref (σημερινο)', ['DARKO', 'LEBRON', 'BPMold'])])
def vver(p, y, idx):
    vs = [IDX[i][(p, y)] for i in idx if (p, y) in IDX[i]]
    if not vs: return -1.0, False
    mp = MPT.get((p, y), 0.0); return float(np.mean(vs)) * mp / (mp + 500), True
vchk = np.array([vver(p, s - 1, VER['ref (σημερινο)'])[0] for p, s in zip(AB_.pid, AB_.s)])
vchk2 = np.array([value(p, s - 1) for p, s in zip(AB_.pid, AB_.s)])
P(''); P(f'ΕΛΕΓΧΟΣ ref: μεγιστη |ref ξαναυπολογ. − cache vprev| {np.max(np.abs(vchk - AB_.vprev.values)):.2e} · |value() − cache| {np.max(np.abs(vchk2 - AB_.vprev.values)):.2e} (πρεπει 0)')
BASE, KNOWN = {}, {}
for nm_, idx in VER.items():
    r = [vver(p, s - 1, idx) for p, s in zip(AB_.pid, AB_.s)]
    BASE[nm_] = np.array([x[0] for x in r]); KNOWN[nm_] = np.array([x[1] for x in r])
INF = float('inf')
def vmix(base, M):
    if M == INF: return base
    vn = np.where(AB_.ng.values > 0, AB_.vnow.values, base); mn = AB_.minnow.values
    return (mn * vn + M * base) / (mn + M)
PRED, ADJ, COST = {}, {}, {}
for nm_ in VER:
    for M in (500, INF):
        v = vmix(BASE[nm_], M); cost = AB_.w.values * 0.75 * (v + 2.0) * AB_.m.values / 48
        adj = np.zeros(len(D)); np.add.at(adj, AB_.q.values, AB_.sg.values * cost)
        PRED[(nm_, M)] = D.m0.values + adj; ADJ[(nm_, M)] = adj; COST[(nm_, M)] = cost
# ---- picks ----
from statistics import NormalDist
N_ = NormalDist(); SIG = 13.5
def cover(m, L):
    if abs(L - round(L)) < 1e-9: pw = 1 - N_.cdf((-L + .5 - m) / SIG); pl = N_.cdf((-L - .5 - m) / SIG); return pw, 1 - pw - pl, pl
    pw = 1 - N_.cdf((-L - m) / SIG); return pw, 0.0, 1 - pw
def per_game(pred):
    res = np.zeros(len(D)); hit = np.zeros(len(D), bool)
    for q, (r, mp) in enumerate(zip(D.itertuples(index=False), pred)):
        pw, pp, pl = cover(mp, r.L); e1, e2 = pw * r.oh + pp - 1, pl * r.oa + pp - 1
        sd, e, od = (1, e1, r.oh) if e1 >= e2 else (-1, e2, r.oa)
        if e < .08: continue
        x = (r.act + r.L) * sd; res[q] = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0); hit[q] = True
    return res, hit
SE = sorted(D.sea.unique()); ys = D.sea.values; ACTV = D.act.values; M0V = D.m0.values
def rm(pred, mk): return float(np.sqrt(np.mean((ACTV[mk] - pred[mk]) ** 2)))
PG = {k: per_game(v) for k, v in PRED.items()}
def stats(key):
    res, hit = PG[key]; u = res[hit]
    per = {s: float(res[hit & (ys == s)].sum()) for s in SE}
    return dict(n=int(hit.sum()), u=float(u.sum()), roi=100 * u.mean(), se=100 * u.std(ddof=1) / np.sqrt(len(u)), per=per, pos=sum(1 for s in SE if per[s] > 0))
def slope(adj):
    y = ACTV - M0V; X = np.c_[np.ones(len(y)), adj]; b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    cov = np.linalg.inv(X.T @ X) * (e @ e) / (len(y) - 2); return b[1], np.sqrt(cov[1, 1])
mref = stats(('ref (σημερινο)', 500))
P(f'ΕΛΕΓΧΟΣ ΑΝΑΠΑΡΑΓΩΓΗΣ t59: ref M=500 → μοναδες {mref["u"]:+.1f} · picks {mref["n"]} (στοχος +164.6 · 2996) {"✓" if (abs(mref["u"] - 164.6) < 0.05 and mref["n"] == 2996) else "✗ ΣΤΟΠ"}')
if not (abs(mref['u'] - 164.6) < 0.05 and mref['n'] == 2996):
    open(os.path.join(SC, 't62_value_combos_out.txt'), 'w', encoding='utf-8').write('\n'.join(out)); sys.exit(1)
P(f'ματς {len(D)} · εγγραφες αποντων {len(AB_)}')
# ---- πινακας 0: καλυψη ----
P(''); P('ΠΙΝΑΚΑΣ 0 — εγγραφες αποντων στο −1 (λειπει ΚΑΘΕ δεικτης της εκδοχης για τη σεζον s−1):')
any3 = KNOWN['7 ολοι']
for nm_ in VER:
    k = KNOWN[nm_]
    P(f'  {nm_:16s}: στο −1 {int((~k).sum()):5d} απο {len(k)} ({100 * (~k).mean():4.1f}%) · εκ των οποιων εχουν αλλο δεικτη (DARKO/LEBRON/σωστο BPM) {int((~k & any3).sum()):4d}')
# ---- πινακας 1/2: RMSE + κλιση + picks ----
for M, tag in ((500, 'ΚΥΡΙΑ: μιξη M=500'), (INF, 'ΔΕΥΤΕΡΕΥΟΝ: βαση μονη M=∞')):
    P(''); P(f'ΠΙΝΑΚΑΣ — {tag} · RMSE (act − μοντελο, ποντοι, ολα τα ματς) · ΔRMSE ανα σεζον vs «7 ολοι» (αρνητικο = καλυτερο) · κλιση κοστους')
    r7 = {s: rm(PRED[('7 ολοι', M)], ys == s) for s in SE}
    for nm_ in VER:
        pr = PRED[(nm_, M)]; b, se = slope(ADJ[(nm_, M)])
        dd = [rm(pr, ys == s) - r7[s] for s in SE]
        P(f'  {nm_:16s}: RMSE {rm(pr, np.ones(len(D), bool)):.4f} · ΔRMSE ανα σεζον ' + ' '.join(f'{s % 100}:{x:+.4f}' for s, x in zip(SE, dd))
          + f' · καλυτερο απο 7 σε {sum(x < 0 for x in dd)}/5 · κλιση {b:.3f} ± {se:.3f}')
    P(f'  PICKS ({tag}, χαντικαπ ανοιγμα edge ≥8%, μοναδες = 1 μοναδα/pick)')
    g7, _ = PG[('7 ολοι', M)]
    for nm_ in VER:
        st = stats((nm_, M)); gg, _ = PG[(nm_, M)]; dg = gg - g7
        P(f'  {nm_:16s}: ROI {st["roi"]:+5.1f}% ± {st["se"]:.1f} · n {st["n"]} · μοναδες {st["u"]:+6.1f} · θετικες σεζον {st["pos"]}/5 · ανα σεζον '
          + ' '.join(f'{s % 100}:{st["per"][s]:+.1f}' for s in SE) + f' · Δμοναδες vs 7 {dg.sum():+.1f} ± {dg.std(ddof=1) * np.sqrt(len(dg)):.1f}')
# ---- κριτηριο (2) ----
P(''); P('ΚΡΙΤΗΡΙΟ (2) στη ΚΥΡΙΑ (M=500): RMSE καλυτερο απο 7 σε ≥4/5 ΚΑΙ μοναδες ≥ 7 ΚΑΙ θετικες ≥4/5')
s7 = stats(('7 ολοι', 500)); r7 = {s: rm(PRED[('7 ολοι', 500)], ys == s) for s in SE}; repl = []
for nm_ in list(VER)[:6] + ['ref (σημερινο)']:
    pr = PRED[(nm_, 500)]; st = stats((nm_, 500)); nb = sum(rm(pr, ys == s) < r7[s] for s in SE)
    c1, c2, c3 = nb >= 4, st['u'] >= s7['u'], st['pos'] >= 4
    P(f'  {nm_:16s}: RMSE {nb}/5 {"✓" if c1 else "✗"} · μοναδες {st["u"]:+.1f} vs {s7["u"]:+.1f} {"✓" if c2 else "✗"} · θετικες {st["pos"]}/5 {"✓" if c3 else "✗"} → {"ΑΝΤΙΚΑΘΙΣΤΑ" if (c1 and c2 and c3) else "οχι"}')
    if c1 and c2 and c3 and nm_ != 'ref (σημερινο)': repl.append(nm_)
P(f'  → εκδοχες που περνουν (1-6): {", ".join(repl) if repl else "καμια (μενει το 7)"}')
# ---- LOSO (1) ----
V7 = list(VER)[:7]
for M, tag in ((500, 'M=500 (κυρια)'), (INF, 'M=∞')):
    P(''); P(f'LOSO {tag}: εκδοχη (1-7) με μικροτερο RMSE στις αλλες 4 σεζον → εφαρμογη στη σεζον-τεστ')
    held = np.zeros(len(D)); ch = []
    for s in SE:
        tr = ys != s
        best = min(V7, key=lambda v: np.mean((ACTV[tr] - PRED[(v, M)][tr]) ** 2)); ch.append(best); held[ys == s] = PRED[(best, M)][ys == s]
    cnt = collections.Counter(ch)
    P('  επιλογη ανα σεζον-τεστ: ' + ' · '.join(f'{s % 100}:{c}' for s, c in zip(SE, ch)) + f' · ιδια επιλογη {cnt.most_common(1)[0][1]}/5')
    r7m = {s: rm(PRED[('7 ολοι', M)], ys == s) for s in SE}
    P('  RMSE σεζον-τεστ LOSO − 7 ολοι: ' + ' '.join(f'{s % 100}:{rm(held, ys == s) - r7m[s]:+.4f}' for s in SE))
    gh, hh = per_game(held); g7, h7 = PG[('7 ολοι', M)]
    per = {s: gh[hh & (ys == s)].sum() for s in SE}; u = gh[hh]
    P(f'  LOSO picks: ROI {100 * u.mean():+.1f}% ± {100 * u.std(ddof=1) / np.sqrt(len(u)):.1f} · n {int(hh.sum())} · μοναδες {u.sum():+.1f} · θετικες {sum(per[s] > 0 for s in SE)}/5 · ανα σεζον '
      + ' '.join(f'{s % 100}:{per[s]:+.1f}' for s in SE) + f' · Δμοναδες vs 7 {(gh - g7).sum():+.1f} ± {(gh - g7).std(ddof=1) * np.sqrt(len(D)):.1f}')
# ---- παραδειγματα ----
P(''); P('ΕΛΕΓΧΟΣ ΠΑΡΑΔΕΙΓΜΑΤΩΝ (απων Out/Doubtful · δεικτες ακατεργαστοι ετους s−1 · εκδοχες μετα το × mp/(mp+500) · κοστος M=500 και M=∞ σε ποντους):')
def raw(p, y, i): return IDX[i].get((p, y))
def show(tag, i):
    r = AB_.iloc[i]; p, y = r.pid, int(r.s) - 1; mp = MPT.get((p, y), 0.0); rr = D.iloc[int(r.q)]
    P(f'  [{tag}] {r.d} {rr.away}@{rr.home} · {r.team} {NM.get(p)} [pid {p}] · {r.stt} (w {r.w:.2f}) · λεπτα live {r.m:.1f}′ · περσινα λεπτα {mp:.0f} (συρρικνωση ×{mp / (mp + 500):.3f})'
      f' · φετινη box {r.vnow:+.2f} με {r.minnow:.0f}′ φετος')
    P('      δεικτες ' + ' · '.join(f'{i_} {raw(p, y, i_) if raw(p, y, i_) is not None else "—"}' for i_ in ('DARKO', 'LEBRON', 'BPM', 'BPMold')))
    for nm_ in VER:
        P(f'      {nm_:16s}: βαση {BASE[nm_][i]:+.2f}{"" if KNOWN[nm_][i] else " (−1)"} · μιξη M=500 {vmix(BASE[nm_], 500)[i]:+.2f} · κοστος M=500 {COST[(nm_, 500)][i]:.2f} π. · κοστος M=∞ {COST[(nm_, INF)][i]:.2f} π.')
OD_ = AB_.stt.isin(['Out', 'Doubtful']).values
jk = [i for i in range(len(AB_)) if OD_[i] and 'Joki' in str(NM.get(AB_.pid.values[i])) and AB_.s.values[i] in (2025, 2026)]
if jk: show('Jokić', jk[0])
sp = []
for i in range(len(AB_)):
    if not OD_[i]: continue
    p, y = AB_.pid.values[i], int(AB_.s.values[i]) - 1; vs = [raw(p, y, k) for k in ('DARKO', 'LEBRON', 'BPM')]
    if all(v is not None for v in vs) and MPT.get((p, y), 0) > 1000: sp.append((max(vs) - min(vs), i))
sp.sort(reverse=True); show('μεγαλη διαφορα δεικτων (οχι Jokić)', [i for d_, i in sp if 'Joki' not in str(NM.get(AB_.pid.values[i]))][0])
nl = [(MPT.get((AB_.pid.values[i], int(AB_.s.values[i]) - 1), 0), i) for i in range(len(AB_)) if OD_[i]
      and raw(AB_.pid.values[i], int(AB_.s.values[i]) - 1, 'LEBRON') is None and raw(AB_.pid.values[i], int(AB_.s.values[i]) - 1, 'DARKO') is not None]
nl.sort(reverse=True)
if nl: show('χωρις LEBRON', nl[0][1])
P(f'  σημειωση: εγγραφες χωρις LEBRON αλλα με DARKO: {len(nl)} Out/Doubtful · με περσινα λεπτα 0: {sum(1 for m_, _ in nl if m_ == 0)} (DARKO δινει τιμη και σε παικτη χωρις λεπτα → ×0 = 0 αντι −1)')
nb = [(NM.get(AB_.pid.values[i]), int(AB_.s.values[i]) - 1, MPT.get((AB_.pid.values[i], int(AB_.s.values[i]) - 1), 0)) for i in range(len(AB_))
      if raw(AB_.pid.values[i], int(AB_.s.values[i]) - 1, 'BPM') is None and raw(AB_.pid.values[i], int(AB_.s.values[i]) - 1, 'DARKO') is not None
      and MPT.get((AB_.pid.values[i], int(AB_.s.values[i]) - 1), 0) > 0]
P(f'  σημειωση: εγγραφες χωρις σωστο BPM ενω επαιξαν περσι (πιθανο ονομα που δεν ταιριαζει): {len(nb)} · ' + ', '.join(f'{a} {b} ({c:.0f}′) ×{n_}' for (a, b, c), n_ in collections.Counter(nb).most_common()))
open(os.path.join(SC, 't62_value_combos_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
