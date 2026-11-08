# -*- coding: utf-8 -*-
"""el_total_early_info_test.py — ΣΥΝΟΛΑ ΑΡΧΗΣ ΣΕΖΟΝ: αλλαγες ροστερ/προπονητη (Ι2) & ρυθμος νεου προπονητη (Ι3) (25/9/2026).
ΒΑΣΗ: live συνολα = v2 + καμπυλη Κ2 (ιδια LOSO κατασκευη με el_total_curve_test).
ΔΙΟΡΘΩΣΗ μονο νωρις: total += Σ β_k·x_k · w(αγων), w = 8/(8 + αγων − 1) (οσο «σβηνει» η περσινη εικονα στο μοντελο, βαρος 8)
  Ι2: x1 = (1−συνεχεια γηπ) + (1−συνεχεια φιλ) [νεα ομαδα = 1] · x2 = πληθος ομαδων με ΝΕΟ προπονητη (0/1/2)
  Ι3: x3 = Σ ομαδων με νεο προπονητη ΜΕ ιστορικο Ευρωλιγκας: (ρυθμος ομαδων του προπονητη τις 1-2 προηγ. σεζον − μεσος λιγκας)
        − (ρυθμος της ομαδας περσι − μεσος λιγκας)   [κατοχες/40]
  Ι2+Ι3: ολα μαζι. β: LOSO (ελαχιστα τετραγωνα στο (πραγμ − βαση), κανονικη περιοδος, αλλες σεζον).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (ΜΙΑ εκτελεση) — περνα αν σε σχεση με τη βαση:
  (α) RMSE συνολου αγων 1-10 χαμηλοτερο συνολικα ΚΑΙ σε ≥4/6 σεζον · (β) b οχι < βαση − 0.02 ·
  (γ) ROI συνολων ≥8% ΚΑΙ ≥10% μεγαλυτερο, κερδοφορες σεζον οχι λιγοτερες. Πολλες περνουν → μεγαλυτερος μεσος ROI.
ΔΙΟΡΘΩΣΗ ΛΑΘΟΥΣ 25/9 (πριν την κριση): νεοφερμενες ομαδες ειχαν κενο προπονητη → μετρουσαν ως νεος προπονητης
  και επαιρναν «ρυθμο» απο αλλες νεοφερμενες. Τωρα: μονο αλλαγη ροστερ· ρυθμος μονο με γνωστο προπονητη. Ιδια κριτηρια.
Εξοδος: el_total_early_info_test_out.txt"""
import sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
_o2 = []
src = open('el_total_curve_test.py', encoding='utf-8').read().split("VARS = {")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src)
out = _o2
def P(s=''):
    print(s, flush=True); out.append(str(s))
BASE = C2                                                  # live: v2 + Κ2 (LOSO)
H = D.home.values[IDX]; A = D.away.values[IDX]
CO = pd.read_csv('el_continuity.csv').set_index(['season', 'team'])
def cont(s, t):
    if (s, t) not in CO.index: return 0.0
    r = CO.loc[(s, t)]; return 0.0 if bool(r.new) else float(r.cont)
def cch(s, t):
    # ΔΙΟΡΘΩΣΗ 25/9: νεοφερμενες ομαδες (coach_change = NaN) ΔΕΝ μετρανε ως «νεος προπονητης» — τις καλυπτει η αλλαγη ροστερ
    if (s, t) not in CO.index: return 0.0
    v = CO.loc[(s, t)].coach_change
    return float(v is True or (isinstance(v, str) and v == 'True') or (not pd.isna(v) and bool(v)))
# ρυθμος ανα ομαδα-σεζον (κανονικη περιοδος) σε αποκλιση απο τον μεσο της σεζον
Dr = D[D.phase == 'RS']
pace_ts = {}
for s, g in Dr.groupby('season'):
    lm = g.pace.mean()
    for t in set(g.home) | set(g.away):
        pace_ts[(s, t)] = g[(g.home == t) | (g.away == t)].pace.mean() - lm
coach_team = {}                                          # (προπονητης) -> [(σεζον, ομαδα)] οπου ηταν head coach στην αρχη
for (s, t), r in CO.iterrows():
    if not pd.isna(r.coach): coach_team.setdefault(str(r.coach), []).append((s, t))
SEAS_ALL = sorted(set(CO.index.get_level_values(0)))
def coach_pace_shift(s, t):
    if not cch(s, t) or pd.isna(CO.loc[(s, t)].coach): return 0.0, False   # ΔΙΟΡΘΩΣΗ 25/9: αγνωστος προπονητης → καμια διορθωση
    c = str(CO.loc[(s, t)].coach); prev = [f'E{int(s[1:]) - k}' for k in (1, 2)]
    hist = [pace_ts[(ps, pt)] for ps, pt in coach_team.get(c, []) if ps in prev and pt != t and (ps, pt) in pace_ts]
    if not hist: return 0.0, False
    own = pace_ts.get((f'E{int(s[1:]) - 1}', t), 0.0)
    return float(np.mean(hist)) - own, True
W = 8.0 / (8.0 + RND - 1)
X1 = np.array([(1 - cont(s, h)) + (1 - cont(s, a)) for s, h, a in zip(SE, H, A)])
X2 = np.array([cch(s, h) + cch(s, a) for s, h, a in zip(SE, H, A)])
x3, known = [], []
for s, h, a in zip(SE, H, A):
    ph, kh = coach_pace_shift(s, h); pa, ka = coach_pace_shift(s, a); x3.append(ph + pa); known.append(kh or ka)
X3 = np.array(x3); KN = np.array(known)
P(f'ματς κανονικης περιοδου με νεο προπονητη που εχει ιστορικο EL (Ι3 ≠ 0): {int((KN & RS).sum())} · με τουλαχιστον 1 νεο προπονητη: {int(((X2 > 0) & RS).sum())}')
FEATS = {'Ι2 αλλαγες + προπονητης': [X1, X2], 'Ι3 ρυθμος προπονητη': [X3], 'Ι2+Ι3': [X1, X2, X3]}
VARS = {'live (v2 + Κ2)': BASE}; COEF = {}
for k, xs in FEATS.items():
    v = np.array(BASE, float); cs = []
    Z = np.column_stack([x * W for x in xs])
    for s in SS:
        tr = RS & (SE != s) & np.isin(SE, SS); te = SE == s
        c = np.linalg.lstsq(Z[tr], (TOT - BASE)[tr], rcond=None)[0]; cs.append(c)
        v[te] += Z[te] @ c
    VARS[k] = v; COEF[k] = np.mean(cs, axis=0)
P('συντελεστες (μεσος LOSO, ποντοι συνολου ανα μοναδα, στην 1η αγωνιστικη): ' + ' | '.join(f'{k}: {np.round(c, 2).tolist()}' for k, c in COEF.items()))
P('  (x1 = ποσο αλλαξαν τα δυο ροστερ 0-2 · x2 = νεοι προπονητες 0-2 · x3 = διαφορα ρυθμου κατοχες/40)')
P('')
E10 = RS & (RND <= 10)
P('=== ΜΕΣΗ ΜΕΡΟΛΗΨΙΑ & RMSE, αγων 1-10 ===')
res = {}
for k, v in VARS.items():
    per = {s: np.sqrt(np.mean((TOT - v)[E10 & (SE == s)] ** 2)) for s in SS}
    res[k] = dict(rmse=np.sqrt(np.mean((TOT - v)[E10 & np.isin(SE, SS)] ** 2)), per=per)
    m16 = RS & (RND <= 6)
    P(f'  {k:26s} μεροληψια 1-6 {np.mean((TOT - v)[m16]):+.2f} · RMSE 1-10 {res[k]["rmse"]:.3f} | ' + ' '.join(f'{s[-2:]}:{per[s]:.2f}' for s in SS))
P('')
jj = [j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0])]
P('=== ΚΛΙΣΗ b & ROI ΣΥΝΟΛΩΝ (Pinnacle closing) ===')
for k, v in VARS.items():
    m = RS & np.isin(SE, SS); res[k]['b'] = np.polyfit((v - MT)[m], (TOT - MT)[m], 1)[0]
    bt = tot_bets(v); bt['rnd'] = RND[jj]; res[k]['bets'] = bt
    cells = []
    for thr in (0.08, 0.10):
        g = bt[bt.edge >= thr]; pos = sum(1 for s in SS if len(g[g.season == s]) and g[g.season == s].p.mean() > 0)
        res[k][thr] = (g.p.mean() * 100, pos); cells.append(f'≥{thr*100:.0f}%: {g.p.mean()*100:+.1f}% ({len(g)}) {pos}/6')
    g = bt[(bt.edge >= 0.08) & (bt.rnd <= 6)]
    e16 = ' · '.join(f'{r_} {g[g.role == r_].p.mean()*100:+.1f}% ({(g.role == r_).sum()})' for r_ in ('over', 'under'))
    P(f'  {k:26s} b {res[k]["b"]:+.3f} | ' + ' | '.join(cells) + f' | αγων 1-6 (≥8%): {e16}')
P('')
P('=== ΚΡΙΤΗΡΙΑ ===')
base = res['live (v2 + Κ2)']; passed = []
for k in FEATS:
    r = res[k]; w_ = sum(r['per'][s] < base['per'][s] for s in SS)
    a_ = r['rmse'] < base['rmse'] and w_ >= 4; b_ = r['b'] >= base['b'] - 0.02
    c_ = all(r[t][0] > base[t][0] and r[t][1] >= base[t][1] for t in (0.08, 0.10))
    P(f'  {k:26s} (α) {"✓" if a_ else "✗"} ({w_}/6)  (β) {"✓" if b_ else "✗"}  (γ) {"✓" if c_ else "✗"}')
    if a_ and b_ and c_: passed.append(k)
P(f'→ ΠΕΡΝΑ: {max(passed, key=lambda k: res[k][0.08][0] + res[k][0.10][0])}' if passed else '→ ΚΑΜΙΑ δεν περνα· μενει το live')
open('el_total_early_info_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))

# ---- ΤΙ ΣΗΜΑΙΝΕΙ ΦΕΤΟΣ (E2026): διορθωση Ι2+Ι3 με τους συντελεστες ολων των σεζον ----
m = RS & np.isin(SE, SS)
Zall = np.column_stack([x * W for x in FEATS['Ι2+Ι3']])
cf = np.linalg.lstsq(Zall[m], (TOT - BASE)[m], rcond=None)[0]
P('')
P(f'συντελεστες ολων των σεζον (για live): αλλαγες ροστερ {cf[0]:+.2f} · νεος προπονητης {cf[1]:+.2f} · ρυθμος προπονητη {cf[2]:+.2f}')
import json
S26 = json.load(open('el_sched.json', encoding='utf-8'))['E2026']
cnt = {}; rows = []
for x in sorted(S26, key=lambda y: y['utc']):
    if x['phase'] != 'RS': continue
    h, a = x['hcode'], x['acode']
    for t in (h, a): cnt[t] = cnt.get(t, 0) + 1
    r = max(cnt[h], cnt[a]); w = 8 / (8 + r - 1)
    x1 = (1 - cont('E2026', h)) + (1 - cont('E2026', a)); x2 = cch('E2026', h) + cch('E2026', a)
    ph, _ = coach_pace_shift('E2026', h); pa, _ = coach_pace_shift('E2026', a)
    adj = w * (cf[0] * x1 + cf[1] * x2 + cf[2] * (ph + pa))
    rows.append((r, x['home'], x['away'], x1, x2, ph + pa, adj))
P('φετινα ματς, διορθωση συνολου (ποντοι):')
for r, h, a, x1, x2, x3, adj in rows[:20]:
    P(f'  αγων {r:2d} {h[:18]:18s}-{a[:18]:18s} αλλαγες {x1:.2f} · νεοι προπ. {x2:.0f} · ρυθμος προπ. {x3:+.1f} → {adj:+.1f}')
P('  ανα προπονητη (νεοι φετος, με ιστορικο EL): ' + ' · '.join(f'{t} {str(CO.loc[("E2026", t)].coach).title()} {coach_pace_shift("E2026", t)[0]:+.1f}' for t in sorted({t for s_, t in CO.index if s_ == 'E2026'}) if coach_pace_shift('E2026', t)[1]))
open('el_total_early_info_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
