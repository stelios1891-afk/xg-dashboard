# -*- coding: utf-8 -*-
"""t117_january_totals_diag.py — ΣΥΝΟΛΑ NBA: ΤΙ ΑΛΛΑΖΕΙ ΤΟΝ ΙΑΝΟΥΑΡΙΟ; (27/10/2026, Στελιος «συμφωνω» στη λιστα 7 παραγοντων). ΔΙΑΓΝΩΣΤΙΚΟ.
ΚΥΡΙΟ ΔΕΙΓΜΑ: «κανονικες» σεζον χωρις ξαφνικη πτωση (2021-22, 2022-23, 2024-25)· ελεγχος στις 2023-24 & 2025-26.
Βαση: _t104_totals_live.csv (LIVE μηχανη συνολων, ολα τα ματς, προβλεψη μ στο ανοιγμα) + box scores (nba_player_games.csv).
r = πραγματικο συνολο − μ (μοντελο). Picks = ανοιγμα Crown ≥8%.
 1 «ΧΑΝΓΚΟΒΕΡ ΔΕΚΕΜΒΡΙΟΥ»: r ομαδας τον Δεκ (και γιορτες 23/12-2/1) → προβλεπει r του Ιαν; κλιση vs ιδια μετρηση για Νοε→Δεκ, Ιαν→Φεβ, Φεβ→Μαρ.
   + «τυχη» Δεκ: 3P% στα ματς της ομαδας τον Δεκ − 3P% στα ματς της ολη τη σεζον.
 2 ΕΒΔΟΜΑΔΕΣ: 23-31/12 · Ιαν 1-7 · 8-14 · 15-21 · 22-31 (μεροληψια ολων, ROI/CLV picks).
 3 ΡΥΘΜΟΣ vs ΑΠΟΔΟΤΙΚΟΤΗΤΑ: «εκπληξη ρυθμου» = κατοχες − μεσος ορος των 2 ομαδων ως τοτε · «εκπληξη αποδοτικοτητας» = ποντοι/κατοχη − μεσος ως τοτε.
 4 ΠΥΚΝΟΤΗΤΑ: ματς τις 7 μερες (αθροισμα 2 ομαδων) · ματς ανα ομαδα ανα μηνα.
 5 ΡΟΤΕΙΣΟΝ: μεριδιο λεπτων των 5 με τα περισσοτερα λεπτα · αλλαγη Δεκ→Ιαν ανα ομαδα vs r Ιαν.
 6 ΟΓΚΟΣ ΑΠΟΥΣΙΩΝ: |διορθωση απουσιων| (μ − μηχανη) & πληθος αποντων → μεροληψια/ROI.
 7 ΣΥΓΚΕΝΤΡΩΣΗ: ποσες ομαδες κανουν τη ζημια των picks Ιαν.
Εξοδος: nba_tests/t117_january_totals_diag_out.txt"""
import os, sys, collections
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC); sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
NORM, DROP = [2022, 2023, 2025], [2024, 2026]
X = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv')); X['day'] = pd.to_datetime(X.date).dt.normalize(); X['r'] = X.tot - X.mu
AB = {'BRK': 'BKN', 'CHO': 'CHA', 'PHO': 'PHX'}; X['h'] = X.home.map(lambda t: AB.get(t, t)); X['a'] = X.away.map(lambda t: AB.get(t, t))
# ---- box ανα ομαδα-ματς
B = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['GAME_ID', 'GAME_DATE', 'TEAM_ABBREVIATION', 'MIN', 'FGA', 'FG3M', 'FG3A', 'FTA', 'OREB', 'TOV', 'PTS', 'stype'])
B = B[B.stype == 'RS'].copy(); B['MIN'] = pd.to_numeric(B.MIN, errors='coerce').fillna(0)
def top5(m): v = np.sort(m.values)[::-1]; return v[:5].sum() / max(v.sum(), 1)
TB = B.groupby(['GAME_ID', 'GAME_DATE', 'TEAM_ABBREVIATION']).agg(FGA=('FGA', 'sum'), FG3M=('FG3M', 'sum'), FG3A=('FG3A', 'sum'), FTA=('FTA', 'sum'),
                                                                OREB=('OREB', 'sum'), TOV=('TOV', 'sum'), PTS=('PTS', 'sum'), t5=('MIN', top5)).reset_index()
TB['poss'] = TB.FGA + 0.44 * TB.FTA - TB.OREB + TB.TOV; TB['day'] = pd.to_datetime(TB.GAME_DATE).dt.normalize()
GM = TB.groupby('GAME_ID').agg(day=('day', 'first'), poss=('poss', 'mean'), pts=('PTS', 'sum'), fg3m=('FG3M', 'sum'), fg3a=('FG3A', 'sum')).reset_index()
TB = TB.merge(GM[['GAME_ID', 'poss', 'pts', 'fg3m', 'fg3a']].rename(columns={'poss': 'gposs', 'pts': 'gpts', 'fg3m': 'g3m', 'fg3a': 'g3a'}), on='GAME_ID')
TB = TB.sort_values('day')
def season_of(d): return d.year + (1 if d.month >= 7 else 0)
TB['sea'] = TB.day.map(season_of)
# αναμενομενα ως τοτε (μονο προηγουμενα ματς ιδιας σεζον): κατοχες & ποντοι/κατοχη στα ματς της ομαδας
TB['exp_poss'] = TB.groupby(['sea', 'TEAM_ABBREVIATION']).gposs.transform(lambda s: s.shift().expanding().mean())
TB['ppp'] = TB.gpts / (2 * TB.gposs)
TB['exp_ppp'] = TB.groupby(['sea', 'TEAM_ABBREVIATION']).ppp.transform(lambda s: s.shift().expanding().mean())
# πυκνοτητα 7 μερων
dens = []
for (s, t), d in TB.groupby(['sea', 'TEAM_ABBREVIATION']):
    days = d.day.values
    for k, dd in zip(d.index, days): dens.append((k, int(((days < dd) & (days >= dd - np.timedelta64(7, 'D'))).sum())))
TB.loc[[k for k, _ in dens], 'g7'] = [v for _, v in dens]
KEY = {(r.day, r.TEAM_ABBREVIATION): r for r in TB.itertuples(index=False)}
def g(r, t, f):
    v = KEY.get((r.day, t)); return getattr(v, f) if v is not None else np.nan
for f in ('exp_poss', 'exp_ppp', 'g7', 't5'):
    X[f + '_h'] = [g(r, r.h, f) for r in X.itertuples(index=False)]; X[f + '_a'] = [g(r, r.a, f) for r in X.itertuples(index=False)]
X['poss'] = [g(r, r.h, 'gposs') for r in X.itertuples(index=False)]
X['pace_sur'] = X.poss - (X.exp_poss_h + X.exp_poss_a) / 2
X['eff_sur'] = 100 * (X.tot / (2 * X.poss) - (X.exp_ppp_h + X.exp_ppp_a) / 2)
X['g7s'] = X.g7_h + X.g7_a
X['abs_size'] = (X.mu - X.eng).abs()
NM = ((10, 'Οκτ'), (11, 'Νοε'), (12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ'), (3, 'Μαρ'), (4, 'Απρ'))
def cell(d):
    k = d[d.pick]
    return f"μεροληψια {d.r.mean():+5.2f} ({len(d)}) · picks {100 * k.res.mean():+5.1f}% ({len(k)}) CLV {k.clv.mean():+.2f}" if len(k) else f"μεροληψια {d.r.mean():+5.2f} ({len(d)})"
P('t117 · ΣΥΝΟΛΑ NBA · ΤΙ ΑΛΛΑΖΕΙ ΤΟΝ ΙΑΝΟΥΑΡΙΟ · κυριο δειγμα κανονικες σεζον 21-22/22-23/24-25 (ελεγχος 23-24/25-26) · r = πραγμ − μοντελο')
N = X[X.sea.isin(NORM)]; D = X[X.sea.isin(DROP)]
# ===== 1
P('\n=== 1. «ΧΑΝΓΚΟΒΕΡ»: η μεροληψια μιας ομαδας τον προηγουμενο μηνα προβλεπει τη μεροληψια της τον επομενο; ===')
P('  κλιση: r ματς μηνα Β πανω στο μεσο r (προηγουμενου μηνα Α) των 2 ομαδων· αρνητικη = οι «ζεστες» ομαδες γυριζουν κατω (το μοντελο τους παρα-εμαθε)')
TR = []
for r in X.itertuples(index=False):
    for t in (r.h, r.a): TR.append((r.sea, r.mon, r.day, t, r.r))
TR = pd.DataFrame(TR, columns=['sea', 'mon', 'day', 't', 'r'])
def team_month(df, mon): return df[df.mon == mon].groupby(['sea', 't']).r.mean()
def slope(Y, A, B_, mask=None):
    ta = team_month(TR[TR.sea.isin(Y)], A)
    d = X[X.sea.isin(Y) & (X.mon == B_)]
    if mask is not None: d = d[mask(d)]
    x = np.array([(ta.get((s, h), np.nan) + ta.get((s, a), np.nan)) / 2 for s, h, a in zip(d.sea, d.h, d.a)]); y = d.r.values; m = np.isfinite(x)
    b = np.polyfit(x[m], y[m], 1)[0]; se = np.std(y[m] - np.polyval(np.polyfit(x[m], y[m], 1), x[m])) / np.sqrt(((x[m] - x[m].mean()) ** 2).sum())
    return b, se, m.sum()
for lab, A, B_ in (('Νοε→Δεκ', 11, 12), ('Δεκ→Ιαν', 12, 1), ('Ιαν→Φεβ', 1, 2), ('Φεβ→Μαρ', 2, 3)):
    b, se, n = slope(NORM, A, B_); b2, se2, n2 = slope(DROP, A, B_)
    P(f'  {lab}: κανονικες {b:+.3f} ± {se:.3f} ({n} ματς) · με πτωση {b2:+.3f} ± {se2:.3f}')
# γιορτες
hol = TR[((TR.day.dt.month == 12) & (TR.day.dt.day >= 23)) | ((TR.day.dt.month == 1) & (TR.day.dt.day <= 2))].groupby(['sea', 't']).r.mean()
d = N[(N.mon == 1) & (N.day.dt.day >= 3)]
x = np.array([(hol.get((s, h), np.nan) + hol.get((s, a), np.nan)) / 2 for s, h, a in zip(d.sea, d.h, d.a)]); m = np.isfinite(x)
P(f'  γιορτες (23/12-2/1) → Ιαν 3-31: κλιση {np.polyfit(x[m], d.r.values[m], 1)[0]:+.3f} ({m.sum()} ματς) · μεση μεροληψια γιορτων {TR[TR.sea.isin(NORM) & (((TR.day.dt.month == 12) & (TR.day.dt.day >= 23)) | ((TR.day.dt.month == 1) & (TR.day.dt.day <= 2)))].r.mean():+.2f}')
# τυχη 3P Δεκ
TB['g3p'] = TB.g3m / TB.g3a
sea3 = TB.groupby(['sea', 'TEAM_ABBREVIATION']).apply(lambda d: d.g3m.sum() / d.g3a.sum()); dec3 = TB[TB.day.dt.month == 12].groupby(['sea', 'TEAM_ABBREVIATION']).apply(lambda d: d.g3m.sum() / d.g3a.sum())
luck = (dec3 - sea3) * 100
d = N[N.mon == 1]; x = np.array([(luck.get((s, h), np.nan) + luck.get((s, a), np.nan)) / 2 for s, h, a in zip(d.sea, d.h, d.a)]); m = np.isfinite(x)
P(f'  «τυχη» 3P% Δεκ (ποσοστιαιες μοναδες πανω απο τη σεζον) → r Ιαν: κλιση {np.polyfit(x[m], d.r.values[m], 1)[0]:+.3f} ποντοι ανα 1% · ματς με τυχη Δεκ ≥+1%: {cell(d[x >= 1])} │ ≤−1%: {cell(d[x <= -1])}')
# picks Ιαν σε «ζεστες» ομαδες Δεκ
tdec = team_month(TR[TR.sea.isin(NORM)], 12)
d = N[N.mon == 1].copy(); d['hot'] = [(tdec.get((s, h), np.nan) + tdec.get((s, a), np.nan)) / 2 for s, h, a in zip(d.sea, d.h, d.a)]
P(f'  picks Ιαν ανα «ζεστο Δεκ» (μεσο r Δεκ των 2 ομαδων): ≥+3 {cell(d[d.hot >= 3])} │ 0…3 {cell(d[(d.hot >= 0) & (d.hot < 3)])} │ <0 {cell(d[d.hot < 0])}')
P(f'     Over μονο: ≥+3 {cell(d[(d.hot >= 3) & (d.side == 1)])} │ <0 {cell(d[(d.hot < 0) & (d.side == 1)])} · Under μονο: ≥+3 {cell(d[(d.hot >= 3) & (d.side == -1)])} │ <0 {cell(d[(d.hot < 0) & (d.side == -1)])}')
# ===== 2
P('\n=== 2. ΕΒΔΟΜΑΔΕΣ (κανονικες σεζον) ===')
wk = [('Δεκ 1-22', (N.mon == 12) & (N.day.dt.day <= 22)), ('γιορτες 23/12-2/1', ((N.mon == 12) & (N.day.dt.day >= 23)) | ((N.mon == 1) & (N.day.dt.day <= 2))),
      ('Ιαν 3-9', (N.mon == 1) & N.day.dt.day.between(3, 9)), ('Ιαν 10-16', (N.mon == 1) & N.day.dt.day.between(10, 16)),
      ('Ιαν 17-23', (N.mon == 1) & N.day.dt.day.between(17, 23)), ('Ιαν 24-31', (N.mon == 1) & (N.day.dt.day >= 24)), ('Φεβ', N.mon == 2)]
for lab, m in wk: P(f'  {lab:18s} {cell(N[m])}')
# ===== 3
P('\n=== 3. ΡΥΘΜΟΣ vs ΑΠΟΔΟΤΙΚΟΤΗΤΑ (εκπληξη = πραγματικο − μεσος ορος των 2 ομαδων ως τοτε) ===')
P('  μηνας: εκπληξη κατοχων (ανα ομαδα) · εκπληξη ποντων/100 κατ. · r  │ στα picks Ιαν που ΧΑΘΗΚΑΝ: κατοχες / αποδοτικοτητα')
for mo, nm in NM:
    d = N[N.mon == mo]
    P(f'  {nm}: {d.pace_sur.mean():+5.2f} · {d.eff_sur.mean():+5.2f} · r {d.r.mean():+5.2f}')
for lab, side in (('Over', 1), ('Under', -1)):
    for when, mm in (('Ιαν', N.mon == 1), ('αλλοι', N.mon != 1)):
        k = N[mm & N.pick & (N.side == side)]; lo = k[k.res < 0]; wi = k[k.res > 0]
        P(f'  {lab} picks {when}: χαμενα κατοχες {lo.pace_sur.mean():+.2f} αποδοτ. {lo.eff_sur.mean():+.2f} · κερδισμενα κατοχες {wi.pace_sur.mean():+.2f} αποδοτ. {wi.eff_sur.mean():+.2f} · ολα: κατ {k.pace_sur.mean():+.2f} αποδ {k.eff_sur.mean():+.2f}')
# ===== 4
P('\n=== 4. ΠΥΚΝΟΤΗΤΑ (ματς τις 7 προηγουμενες μερες, αθροισμα 2 ομαδων) ===')
P('  ματς ανα ομαδα ανα μηνα (κανονικες, ανα 30 μερες): ' + ' · '.join(f"{nm} {30 * len(TB[TB.sea.isin(NORM) & (TB.day.dt.month == mo)]) / (30 * len(set(TB.day[TB.sea.isin(NORM) & (TB.day.dt.month == mo)])) / 1) :.1f}" for mo, nm in NM))
for lab, f in (('≤4', lambda d: d.g7s <= 4), ('5-6', lambda d: d.g7s.between(5, 6)), ('≥7', lambda d: d.g7s >= 7)):
    P(f'  {lab:4s} Ιαν {cell(N[(N.mon == 1) & f(N)])} │ αλλοι {cell(N[(N.mon != 1) & f(N)])} │ μεριδιο Ιαν {100 * ((N.mon == 1) & f(N)).sum() / (N.mon == 1).sum():.0f}% vs {100 * ((N.mon != 1) & f(N)).sum() / (N.mon != 1).sum():.0f}%')
# ===== 5
P('\n=== 5. ΡΟΤΕΙΣΟΝ: μεριδιο λεπτων των 5 πρωτων (ανα ομαδα-ματς) ===')
P('  μεσο ανα μηνα (κανονικες): ' + ' · '.join(f"{nm} {100 * TB[TB.sea.isin(NORM) & (TB.day.dt.month == mo)].t5.mean():.1f}%" for mo, nm in NM))
t5d = TB[TB.day.dt.month == 12].groupby(['sea', 'TEAM_ABBREVIATION']).t5.mean(); t5j = TB[TB.day.dt.month == 1].groupby(['sea', 'TEAM_ABBREVIATION']).t5.mean()
ch = (t5j - t5d) * 100
d = N[N.mon == 1].copy(); d['rot'] = [(ch.get((s, h), np.nan) + ch.get((s, a), np.nan)) / 2 for s, h, a in zip(d.sea, d.h, d.a)]
P(f'  ματς Ιαν ανα αλλαγη ροτεισον Δεκ→Ιαν (μ.ο. 2 ομαδων): πιο «σφιχτο» ≥+1.5 {cell(d[d.rot >= 1.5])} │ ιδιο {cell(d[d.rot.abs() < 1.5])} │ πιο «ανοιχτο» ≤−1.5 {cell(d[d.rot <= -1.5])}')
# ===== 6
P('\n=== 6. ΟΓΚΟΣ ΑΠΟΥΣΙΩΝ (διορθωση απουσιων στο συνολο, ποντοι) ===')
for lab, f in (('0', lambda d: d.abs_size < 0.05), ('0-1', lambda d: (d.abs_size >= 0.05) & (d.abs_size < 1)), ('1-2', lambda d: d.abs_size.between(1, 2)), ('>2', lambda d: d.abs_size > 2)):
    P(f'  {lab:4s} Ιαν {cell(N[(N.mon == 1) & f(N)])} │ αλλοι {cell(N[(N.mon != 1) & f(N)])} │ μεριδιο Ιαν {100 * ((N.mon == 1) & f(N)).sum() / (N.mon == 1).sum():.0f}% vs {100 * ((N.mon != 1) & f(N)).sum() / (N.mon != 1).sum():.0f}%')
P(f'  μεσος αριθμος αποντων ρολου/ματς: ' + ' · '.join(f"{nm} {N[N.mon == mo].NABS.mean():.2f}" for mo, nm in NM))
# ===== 7
P('\n=== 7. ΣΥΓΚΕΝΤΡΩΣΗ ζημιας picks Ιαν (κανονικες): μοναδες ανα ομαδα (καθε pick μετρα και στις 2 ομαδες) ===')
k = N[(N.mon == 1) & N.pick]; tl = collections.Counter()
for r in k.itertuples(index=False): tl[r.h] += r.res; tl[r.a] += r.res
srt = sorted(tl.items(), key=lambda x: x[1])
P('  χειροτερες 8: ' + ' · '.join(f'{t} {v:+.1f}' for t, v in srt[:8]) + ' │ καλυτερες 5: ' + ' · '.join(f'{t} {v:+.1f}' for t, v in srt[-5:]))
neg = sum(v for _, v in srt if v < 0); P(f'  μεριδιο των 8 χειροτερων στη συνολικη αρνητικη: {100 * sum(v for _, v in srt[:8]) / neg:.0f}% · ομαδες με αρνητικο: {sum(1 for _, v in srt if v < 0)}/30')
open(os.path.join(SC, 't117_january_totals_diag_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
