"""
uel_home_why.py — 9/10/2026 (Στελιος «γιατι και πως υποτιμαμε την εδρα;» στο UEL). ΠΕΡΙΓΡΑΦΙΚΟ.
Το ευρωπαικο μοντελο βαζει ΜΙΑ εδρα για ολες τις διοργανωσεις: hf = sqrt(Σ xG γηπεδουχων / Σ xG φιλοξενουμενων), ολα τα ευρωπαικα 2122-2526
→ γηπεδουχος λ × hf, φιλοξενουμενος λ ÷ hf. Ερωτηματα:
 1. Ειναι η εδρα του UEL μεγαλυτερη απο των αλλων (σε xG ΚΑΙ σε γκολ); ποσο απεχει απο το κοινο hf;
 2. Ειναι θεμα ΔΗΜΙΟΥΡΓΙΑΣ ευκαιριων (xG) ή ΕΚΤΕΛΕΣΗΣ (γκολ πανω απο xG);
 3. Σε ποια ματς: ποιος ειναι ο γηπεδουχος (top-5 / μικρη λιγκα), φαβορι ή αουτσαιντερ, αποσταση, μορφη, φαση.
 4. Η αγορα το εχει; (πραγματικο − αγορα σκοπια γηπεδουχου)
"""
import sys, io, json, contextlib
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
src = open('uel_battery.py', encoding='utf-8').read(); src = src[:src.index('# ---- Γ διορθωσεις')].replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1)
src = src.replace("print('\\nΒ. ΔΙΑΓΝΩΣΗ", "if False: print('")      # χωρις το τυπωμα της Β
g = {'__name__': 'hw'}
with contextlib.redirect_stdout(io.StringIO()): exec(src, g)
MIDS, COMP, SEA, PHASE, NEW, GD, GH, GA, LH_N, LA_N, SM, DIST_KM, LGH, LGA, TEAMS, FM = (g[k] for k in (
    'MIDS', 'COMP', 'SEA', 'PHASE', 'NEW', 'GD', 'GH', 'GA', 'LH_N', 'LA_N', 'SM', 'DIST_KM', 'LGH', 'LGA', 'TEAMS', 'FM'))
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
XG = {}
for sea in ('2122', '2223', '2324', '2425', '2526'):
    for mid, m in json.load(open(f'data_Europe_{sea}.json', encoding='utf-8')).items():
        if not m.get('shots') or m.get('hs') is None: continue
        h, a = int(m['home']['id']), int(m['away']['id']); agg = {h: 0.0, a: 0.0}
        for s in m['shots']:
            if s.get('xg') is not None and s.get('tid') in agg: agg[s['tid']] += 0.25 if s.get('sit') == 'Penalty' else s['xg']
        XG[str(mid)] = (agg[h], agg[a])
XH = np.array([XG.get(m, (np.nan, np.nan))[0] for m in MIDS]); XA = np.array([XG.get(m, (np.nan, np.nan))[1] for m in MIDS])
SMOD = LH_N - LA_N
# 1. εδρα ανα διοργανωση
print('1. ΕΔΡΑ ανα διοργανωση (2223-2526): hf = sqrt(γηπ/φιλ) · σε xG και σε γκολ · μοντελο = ποση εδρα «βλεπει» (μεσος γηπ − φιλ)')
print(f'   {"":17s} {"n":>4s} | hf xG  hf γκολ | διαφορα: xG πραγμ · γκολ πραγμ · μοντελο · αγορα')
for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague', 'ΟΛΑ'):
    m = (COMP == c) if c != 'ΟΛΑ' else np.ones(len(MIDS), bool)
    mx = m & np.isfinite(XH)
    print(f'   {c:17s} {m.sum():4d} | {np.sqrt(XH[mx].sum() / XA[mx].sum()):.3f}  {np.sqrt(GH[m].sum() / GA[m].sum()):.3f}   | '
          f'{np.mean(XH[mx] - XA[mx]):+.3f} · {np.mean(GD[m]):+.3f} · {np.mean(SMOD[m]):+.3f} · {np.nanmean(SM[m]):+.3f}')
U = COMP == 'EuropaLeague'
print('\n2. UEL: ΔΗΜΙΟΥΡΓΙΑ ή ΕΚΤΕΛΕΣΗ; (γκολ − xG ανα πλευρα· θετικο = εκτελεση πανω απο τις ευκαιριες)')
mx = U & np.isfinite(XH)
for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
    q = (COMP == c) & np.isfinite(XH)
    print(f'   {c:17s} γηπεδουχοι γκολ−xG {np.mean(GH[q] - XH[q]):+.3f} · φιλοξενουμενοι {np.mean(GA[q] - XA[q]):+.3f}'
          f' · xG γηπ {XH[q].mean():.2f} vs μοντελο {LH_N[q].mean():.2f} · xG φιλ {XA[q].mean():.2f} vs μοντελο {LA_N[q].mean():.2f}')
def row(mask, lab):
    m = U & mask; mx_ = m & np.isfinite(XH)
    if m.sum() < 20: return f'   {lab:36s} n{m.sum():4d}'
    e = GD[m] - SMOD[m]; ex = (XH[mx_] - XA[mx_]) - SMOD[mx_]; ek = GD[m] - SM[m]
    ps = pd.Series(e).groupby(SEA[m]).mean()
    return (f'   {lab:36s} n{m.sum():4d} · γκολ − μοντελο {e.mean():+.2f}±{e.std() / np.sqrt(m.sum()):.2f} ({int((ps > 0).sum())}/{ps.size} σεζον >0)'
            f' · xG − μοντελο {ex.mean():+.2f} · γκολ − αγορα {np.nanmean(ek):+.2f}')
print('\n3. UEL: ΠΟΥ υποτιμαται η εδρα (σκοπια γηπεδουχου· θετικο = ο γηπεδουχος πηγε καλυτερα απο το μοντελο)')
print(row(np.ones(len(MIDS), bool), 'ΟΛΑ'))
T5H = np.isin(LGH, list(TOP5)); T5A = np.isin(LGA, list(TOP5))
print(row(T5H & ~T5A, 'γηπ top-5, φιλ οχι')); print(row(~T5H & T5A, 'γηπ ΟΧΙ top-5, φιλ top-5'))
print(row(T5H & T5A, 'και οι δυο top-5')); print(row(~T5H & ~T5A, 'καμια top-5'))
print(row(SMOD >= 0.5, 'γηπεδουχος φαβορι (≥0.5)')); print(row(np.abs(SMOD) < 0.5, 'ισορροπο')); print(row(SMOD <= -0.5, 'γηπεδουχος αουτσαιντερ (≤−0.5)'))
q = np.nanpercentile(DIST_KM[U], [33, 67])
print(row(DIST_KM < q[0], f'ταξιδι <{q[0]:.0f} km')); print(row((DIST_KM >= q[0]) & (DIST_KM < q[1]), f'ταξιδι {q[0]:.0f}-{q[1]:.0f}')); print(row(DIST_KM >= q[1], f'ταξιδι ≥{q[1]:.0f} km'))
print(row(~NEW, 'παλια μορφη')); print(row(NEW, 'νεα μορφη'))
print(row(PHASE == 'league', 'ομιλοι/League Phase')); print(row(PHASE == 'KO', 'νοκ-αουτ'))
print(row(FM, 'FotMob και οι δυο')); print(row(~FM, 'οχι FotMob'))
for lg in pd.Series(LGH[U]).value_counts().index[:8]: print(row(LGH == lg, f'γηπεδουχος απο {lg}'))
