# -*- coding: utf-8 -*-
"""t24_motivation_groups.py — ΚΙΝΗΤΡΟ: ΓΚΡΟΥΠ ΟΜΑΔΩΝ ΑΠΟ ΤΗ ΒΑΘΜΟΛΟΓΙΑ (21/10/2026, Στελιος: «αναλυση Απριλιου, χωρισε τις ομαδες σε γκρουπς·
αλλο η αδιαφορη ομαδα και αλλο η tanking — μην βιαστεις»). ΦΑΣΗ 2 (μονο βαθμολογια· η συμπεριφορα 4ης περιοδου ερχεται στη φαση 3).
Βαθμολογια ΩΣ τη μερα του αγωνα (χωρις ματια στο μελλον), ανα περιφερεια, με ποσοστο νικων. R = αγωνες που απομενουν (82 − ματς).
ΓΚΡΟΥΠ (γραφτηκαν πριν το τρεξιμο, για ομαδες με ≥50 ματς):
  ΚΛΕΙΔΩΜΕΝΗ: δεν μπορει να φτασει την απο πανω της (Ν + R < Ν_πανω) ΚΑΙ δεν τη φτανει η απο κατω (Ν_κατω + R_κατω < Ν).
  ΜΑΧΗ ΘΕΣΗΣ (1-6): θεση 1-6, οχι κλειδωμενη.
  ΜΑΧΗ PLAY-IN: θεση 7-12, ΔΕΝ εχει αποκλειστει απο τη 10η (Ν + R ≥ Ν_10ης), οχι κλειδωμενη.
  ΑΔΙΑΦΟΡΗ: μαθηματικα εκτος play-in (Ν + R < Ν_10ης) αλλα ΟΧΙ στις 5 χειροτερες της λιγκας.
  TANKING: μια απο τις 5 χειροτερες της λιγκας (πιθανοτητες λοταριας 14/14/14/12.5/10.5%), ≥50 ματς.
  (υπολοιπες με ≥50 ματς που δεν πιανονται: «αλλη») · πριν το 50ο ματς: «νωρις».
Μοντελο = αντιγραφο live (t15 core). Picks = edge ≥8% στο ανοιγμα (Crown). Εξοδος: t24_motivation_groups_out.txt + nba_tests/_t24_groups.csv"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__))
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't15_trades.py'), encoding='utf-8').read().split('# ---------- (Α) περιγραφικο ----------')[0]
ns = {'__file__': os.path.join(SC, 't15_trades.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, ns)
sys.stdout.reconfigure(encoding='utf-8')
np = ns['np']; G = ns['G']; SEAS_G = ns['SEAS_G']; dD = ns['dD']; EV = ns['EV']; ACT = ns['ACT']; BASE = ns['BASE']; MKH = ns['MKH']
inner = ns['ns']; cover_, SIG_ = inner['cover'], inner['SIG']
V = BASE + ns['adj'](1.0, -2.0, None)
EAST = set('ATL BOS BRK CHO CHI CLE DET IND MIA MIL NYK ORL PHI TOR WAS'.split())
MON = G.date.dt.month.values
W = collections.Counter(); L_ = collections.Counter(); GRP = {}; DBG = {}
day = collections.defaultdict(list)
for i in np.argsort(dD, kind='stable'): day[(SEAS_G[i], dD[i])].append(i)
for (s, d) in sorted(day):
    teams = {t for (ss, t) in set(W) | set(L_) if ss == s}
    for i in day[(s, d)]: teams |= {G.home.values[i], G.away.values[i]}
    rec = {t: (W[(s, t)], L_[(s, t)]) for t in teams}
    pct = {t: (w + .5) / (w + l + 1) for t, (w, l) in rec.items()}
    worst5 = set(sorted(teams, key=lambda t: pct[t])[:5]) if len(teams) >= 30 else set()
    for conf in (EAST, set(teams) - EAST):
        ct = sorted([t for t in teams if t in conf], key=lambda t: -pct[t])
        if len(ct) < 15: continue
        Wn = [rec[t][0] for t in ct]; Rn = [82 - sum(rec[t]) for t in ct]
        for r, t in enumerate(ct):
            gp = sum(rec[t]); w, R = rec[t][0], 82 - gp
            if gp < 50: GRP[(s, d, t)] = 'νωρις'; continue
            up_ok = r > 0 and w + R >= Wn[r - 1]                      # μπορει ακομα να ανεβει
            down_ok = r < len(ct) - 1 and Wn[r + 1] + Rn[r + 1] >= w  # μπορει ακομα να πεσει
            locked = (not up_ok) and (not down_ok)
            elim10 = w + R < Wn[9]
            if t in worst5: g = 'TANKING'
            elif elim10: g = 'ΑΔΙΑΦΟΡΗ'                                # 21/10 ελεγχος (Νετς 5/4/2024): εκτος play-in μετρα πριν το «κλειδωμενη»
            elif locked: g = 'ΚΛΕΙΔΩΜΕΝΗ'
            elif r < 6: g = 'ΜΑΧΗ ΘΕΣΗΣ 1-6'
            elif r < 12 and not elim10: g = 'ΜΑΧΗ PLAY-IN'
            elif elim10: g = 'ΑΔΙΑΦΟΡΗ'
            else: g = 'αλλη'
            GRP[(s, d, t)] = g; DBG[(s, d, t)] = (r + 1, w, gp - w, R)
    for i in day[(s, d)]:
        h, a = G.home.values[i], G.away.values[i]
        if ACT[i] > 0: W[(s, h)] += 1; L_[(s, a)] += 1
        elif ACT[i] < 0: W[(s, a)] += 1; L_[(s, h)] += 1
# 21/10 (Στελιος «τα picks ηταν γνωριζοντας τις απουσιες;»): ανα (ομαδα, μερα) ΓΝΩΣΤΕΣ στο μοντελο (εχασε ≥2 προηγουμενα, οπως live-backtest)
# vs ΠΡΑΓΜΑΤΙΚΕΣ (παικτης ρολου ≥20′ που ΔΕΝ επαιξε στο ματς, box score) · κοστος 0.75·(αξια+2)·λεπτα/48
Ab = inner['A']; value_, traded_ = inner['value'], inner['traded']
ABS = {}
for (t, s), g in Ab.groupby(['team', 's']):
    days = sorted(g.d.unique()); pm = {d: dict(zip(x.pid, x.MIN)) for d, x in g.groupby('d')}; played = {d: {p for p, m in v.items() if m > 0} for d, v in pm.items()}
    nmn = dict(zip(g.pid, g.PLAYER_NAME))
    hist = collections.defaultdict(list)
    for j, d in enumerate(days):
        prev = days[:j]; usable = prev if prev and (np.datetime64(d) - np.datetime64(prev[-1])).astype(int) > 1 else prev[:-1]
        kc = ac = 0.0; kn = []; an = []
        for p, Hh in hist.items():
            avg = float(np.mean([m for _, m in Hh[-10:]]))
            if avg < 20: continue
            lastp = Hh[-1][0]
            if traded_(p, t, lastp, d): continue
            c = 0.75 * (value_(p, s - 1) + 2.0) * avg / 48
            nmiss = sum(1 for x in usable if x > lastp)
            if nmiss >= 2: kc += c; kn.append(str(nmn.get(p, p)))
            if p not in played[d]: ac += c; an.append((str(nmn.get(p, p)), round(c, 1)))
        ABS[(t, np.datetime64(d, 'D'))] = (kc, ac, kn, an)
        for p in played[d]: hist[p].append((d, pm[d][p]))
rows = []
for i, d_ in MKH.items():
    s = SEAS_G[i]
    if s not in EV or not np.isfinite(V[i]): continue
    L, mk, o1, o2 = d_['o']; cl = d_['c'][1]
    pw, pp, pl = cover_(V[i], L, SIG_); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
    sd, e, od_ = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
    gh, ga = GRP.get((s, dD[i], G.home.values[i]), 'νωρις'), GRP.get((s, dD[i], G.away.values[i]), 'νωρις')
    res = None
    if e >= .08:
        x = (ACT[i] + L) * sd; res = (od_ - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    for t, g, og, sg in ((G.home.values[i], gh, ga, 1), (G.away.values[i], ga, gh, -1)):
        rows.append(dict(i=i, sea=s, mon=int(MON[i]), t=t, g=g, og=og, rm=sg * (ACT[i] - V[i]), ro=sg * (ACT[i] - mk), rc=sg * (ACT[i] - cl),
                         pick=(res is not None and sd == sg), against=(res is not None and sd == -sg), res=res, home=(sg == 1),
                         **dict(zip(('k_cost', 'a_cost', 'k_names', 'a_names'), (lambda z: (z[0], z[1], '|'.join(z[2]), '|'.join(f'{n}:{c}' for n, c in z[3])))(ABS.get((t, np.datetime64(dD[i], 'D')), (0, 0, [], []))))),
                         edge=e))
import pandas as pd
X = pd.DataFrame(rows)
X.to_csv(os.path.join(SC, '_t24_groups.csv'), index=False)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def roi(d):
    if not len(d): return '      —'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):3d}, {d.res.sum():+6.1f}μ, {int((ps > 0).sum())}/{d.sea.nunique()})'
GROUPS = ('ΚΛΕΙΔΩΜΕΝΗ', 'ΜΑΧΗ ΘΕΣΗΣ 1-6', 'ΜΑΧΗ PLAY-IN', 'ΑΔΙΑΦΟΡΗ', 'TANKING')
P('NBA · ΚΙΝΗΤΡΟ — ΓΚΡΟΥΠ ΑΠΟ ΤΗ ΒΑΘΜΟΛΟΓΙΑ (≥50 ματς) · αντιγραφο live · 5 σεζον · + = η ομαδα επαιξε ΚΑΛΥΤΕΡΑ απο την προβλεψη')
# ελεγχος παραδειγματος: 2023-24, 5 Απριλιου
P(''); P('=== ΕΛΕΓΧΟΣ: γκρουπ στις 5/4/2024 (ανατολη/δυση, θεση, ρεκορ, ματς που απομενουν) ===')
dd = np.datetime64('2024-04-05')
for (s, d, t), g in sorted(GRP.items(), key=lambda kv: (kv[1], kv[0][2])):
    if s == 2024 and d == dd: P(f'  {t} {g:15s} θεση {DBG[(s, d, t)][0]:2d} · {DBG[(s, d, t)][1]}-{DBG[(s, d, t)][2]} · απομενουν {DBG[(s, d, t)][3]}')
for per, months in (('ΜΑΡΤΙΟΣ', [3]), ('ΑΠΡΙΛΙΟΣ', [4])):
    P(''); P(f'=== {per}: ανα γκρουπ ===')
    D_ = X[X.mon.isin(months)]
    for g in GROUPS:
        d = D_[D_.g == g]
        if not len(d): continue
        P(f'  {g:16s} ματς {len(d):4d} · μοντελο {d.rm.mean():+5.2f} · αγορα ανοιγ. {d.ro.mean():+5.2f} · κλεισ. {d.rc.mean():+5.2f} · '
          f'picks ΥΠΕΡ {roi(d[d.pick])} · ΚΟΝΤΡΑ {roi(d[d.against])}')
    P(f'  -- {per}: συνδυασμοι (γκρουπ ομαδας vs γκρουπ αντιπαλου), υπολοιπο μοντελου απο την πλευρα της πρωτης --')
    for g in GROUPS:
        for og in GROUPS:
            d = D_[(D_.g == g) & (D_.og == og)]
            if len(d) >= 25: P(f'     {g:16s} vs {og:16s} n {len(d):4d} · μοντελο {d.rm.mean():+5.2f} · αγορα κλεισ. {d.rc.mean():+5.2f}')
open(os.path.join(SC, 't24_motivation_groups_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
