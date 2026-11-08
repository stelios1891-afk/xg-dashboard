# -*- coding: utf-8 -*-
"""t115_janfeb_deep.py — ΙΑΝ-ΦΕΒ ΣΕ ΒΑΘΟΣ (27/10/2026, Στελιος: «πρωτα αυτο που εξαρταται απο εμας — τα picks χωρις απουσιες · στα συνολα
δες βολες/ρυθμο ΚΑΙ αν πεφτει η ευστοχια · και το 2 (ποιοι ειναι οι αιφνιδιοι αποντες)»). ΠΕΡΙΓΡΑΦΙΚΟ.
Α. ΧΑΝΤΙΚΑΠ «χωρις πληροφορια»: εχει η ΓΡΑΜΜΗ ΚΛΕΙΣΙΜΑΤΟΣ μεροληψια τον Ιαν-Φεβ; (ΟΛΑ τα ματς: γηπεδουχος/φαβορι vs κλεισιμο ανα μηνα)
   + τα picks μας «χωρις πληροφορια» παιγμενα ΣΤΟ ΚΛΕΙΣΙΜΟ ανα μηνα (αν χανουν κι εκει → το προβλημα ειναι μετα το κλεισιμο).
Β. ΣΥΝΟΛΑ: ανα μηνα & σεζον (κανονικη περιοδος, ολα τα ματς): ποντοι, κατοχες, βολες (FTA), φαουλ, ευστοχια (FG%, 3P%, FT%, eFG%), 3ποντα (3PA)
   — διαφορα απο τον μεσο της σεζον · + μεροληψια μοντελου / ανοιγματος / κλεισιματος (πραγμ − προβλεψη) ανα μηνα.
Γ. ΑΙΦΝΙΔΙΟΙ ΑΠΟΝΤΕΣ (χαντικαπ, πληροφορια κοντρα ≥1π): τι ηταν στην αναφορα του ανοιγματος (καθολου/Probable/Questionable/Doubtful)
   και ο λογος στην τελευταια αναφορα (ξεκουραση/«Injury Management» vs τραυματισμος) — Ιαν-Φεβ vs υπολοιποι.
Εξοδος: nba_tests/t115_janfeb_deep_out.txt"""
import os, sys, io, contextlib, collections
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't114_janfeb_diagnosis.py'), encoding='utf-8').read().split('# ---- ΧΑΝΤΙΚΑΠ picks')[0]
gg = {'__file__': os.path.join(SC, 't114_janfeb_diagnosis.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, gg)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = gg['np'], gg['pd']; g = gg['g']
G, SER, SHIFT, line_at, EV, ACT, SEAS_G, dD, REPS = (g[x] for x in ('G', 'SER', 'SHIFT', 'line_at', 'EV', 'ACT', 'SEAS_G', 'dD', 'REP_SEASONS'))
status_at, mins, value, W_B, R = g['status_at'], g['mins'], g['value'], g['W_B'], g['R']
PLAYED, PID2K, ROSTER = gg['PLAYED'], gg['PID2K'], gg['ROSTER']
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
MN = ((10, 'Οκτ'), (11, 'Νοε'), (12, 'Δεκ'), (1, 'Ιαν'), (2, 'Φεβ'), (3, 'Μαρ'), (4, 'Απρ'))
# ============ Α ============
H = pd.read_csv(os.path.join(SC, '_t114_hcap.csv'))
ALL = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or not np.isfinite(ACT[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    cl = line_at(rows, tip, sw)
    if not cl: continue
    ALL.append(dict(i=i, sea=s, mon=int(str(dD[i])[5:7]), L=cl[0], oh=cl[1], oa=cl[2], cf=cl[3], act=float(ACT[i])))
A = pd.DataFrame(ALL); CL = {r.i: r for r in A.itertuples(index=False)}
P('t115 · ΙΑΝ-ΦΕΒ ΣΕ ΒΑΘΟΣ · Crown · 5 σεζον')
P('\n=== Α1. ΓΡΑΜΜΗ ΚΛΕΙΣΙΜΑΤΟΣ ανα μηνα (ΟΛΑ τα ματς): πραγμ. − δικαιη κλεισιματος (ποντοι προς γηπ. · προς φαβορι) · % καλυψης γηπ / φαβορι ===')
A['fav_home'] = A.cf > 0; A['res_h'] = A.act - A.cf; A['res_f'] = np.where(A.fav_home, A.act - A.cf, A.cf - A.act)
A['cov_h'] = np.sign(A.act + A.L); A['cov_f'] = np.where(A.fav_home, A.cov_h, -A.cov_h)
for m, nm in MN:
    d = A[A.mon == m]
    P(f'  {nm}: {len(d):4d} ματς · γηπ {d.res_h.mean():+.2f}π (καλυψη {100 * (d.cov_h > 0).sum() / max((d.cov_h != 0).sum(), 1):.1f}%) · φαβορι {d.res_f.mean():+.2f}π (καλυψη {100 * (d.cov_f > 0).sum() / max((d.cov_f != 0).sum(), 1):.1f}%)'
      + ' · ανα σεζον φαβορι ' + ' '.join(f"{s % 100}:{d[d.sea == s].res_f.mean():+.1f}" for s in sorted(A.sea.unique())))
P('\n=== Α2. ΤΑ PICKS ΜΑΣ «ΧΩΡΙΣ ΠΛΗΡΟΦΟΡΙΑ» ΣΤΟ ΑΝΟΙΓΜΑ vs ΑΝ ΤΑ ΠΑΙΖΑΜΕ ΣΤΟ ΚΛΕΙΣΙΜΟ (ιδια πλευρα, γραμμη & τιμη κλεισιματος) ===')
N = H[H.sur.abs() < 1].copy()
def at_close(r):
    c = CL.get(r.i)
    if c is None: return np.nan
    od = c.oh if r.sd == 1 else c.oa; x = (c.act + c.L) * r.sd
    return (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
N['res_c'] = [at_close(r) for r in N.itertuples(index=False)]
for lab, ms in (('Οκτ-Δεκ', (10, 11, 12)), ('Ιαν', (1,)), ('Φεβ', (2,)), ('Μαρ-Απρ', (3, 4))):
    d = N[N.mon.isin(ms)]
    P(f'  {lab:8s} {len(d):4d} picks · ανοιγμα {100 * d.res.mean():+5.1f}% · ΣΤΟ ΚΛΕΙΣΙΜΟ {100 * d.res_c.mean():+5.1f}% · CLV {d.clv.mean():+.2f}π')
P('  Ιαν-Φεβ στο κλεισιμο ανα πλευρα: ' + ' · '.join(f"{lab} {100 * d.res_c.mean():+.1f}% ({len(d)})" for lab, d in (
    ('φαβορι', N[N.mon.isin([1, 2]) & N.fav]), ('αουτσ.', N[N.mon.isin([1, 2]) & ~N.fav]), ('γηπ', N[N.mon.isin([1, 2]) & N.home]), ('φιλ', N[N.mon.isin([1, 2]) & ~N.home]))))
# ============ Β ============
B = pd.read_csv(os.path.join(ROOT, 'nba_player_games.csv'), usecols=['GAME_ID', 'GAME_DATE', 'TEAM_ABBREVIATION', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'TOV', 'PF', 'PTS', 'season', 'stype'])
B = B[B.stype == 'RS']
TG = B.groupby(['GAME_ID', 'GAME_DATE', 'season'])[['FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'TOV', 'PF', 'PTS']].sum().reset_index()
TG['mon'] = pd.to_datetime(TG.GAME_DATE).dt.month; TG['poss'] = (TG.FGA + 0.44 * TG.FTA - TG.OREB + TG.TOV) / 2
TG['efg'] = (TG.FGM + 0.5 * TG.FG3M) / TG.FGA; TG['fg'] = TG.FGM / TG.FGA; TG['p3'] = TG.FG3M / TG.FG3A; TG['ft'] = TG.FTM / TG.FTA
TG['pts100'] = 100 * TG.PTS / TG.poss
COLS = (('PTS', 'ποντοι/ματς', 1), ('poss', 'κατοχες', 1), ('pts100', 'ποντοι/100 κατ.', 1), ('FTA', 'βολες (FTA)', 1), ('PF', 'φαουλ', 1),
        ('fg', 'FG%', 100), ('p3', '3P%', 100), ('ft', 'FT%', 100), ('efg', 'eFG%', 100), ('FG3A', '3ποντα (3PA)', 1))
P('\n=== Β1. ΣΚΟΡ & ΣΥΣΤΑΤΙΚΑ ανα μηνα: διαφορα απο τον μεσο ΤΗΣ σεζον (μεσος 5 σεζον · και ανα σεζον Δεκ→Ιαν) ===')
for c, lab, k in COLS:
    rows = {}
    for s, d in TG.groupby('season'):
        mu = d[c].mean(); rows[s] = {m: k * (d[d.mon == m][c].mean() - mu) for m, _ in MN if (d.mon == m).any()}
    avg = {m: np.mean([rows[s][m] for s in rows if m in rows[s]]) for m, _ in MN}
    dj = ' '.join(f"{s[2:4]}-{s[5:7]}:{rows[s].get(1, np.nan) - rows[s].get(12, np.nan):+.1f}" for s in sorted(rows))
    P(f'  {lab:16s} ' + ' · '.join(f'{nm} {avg[m]:+5.2f}' for m, nm in MN) + f'   │ Ιαν − Δεκ ανα σεζον: {dj}')
P('  (επιπεδα 5 σεζον: ' + ' · '.join(f'{lab} {k * TG[c].mean():.1f}' for c, lab, k in COLS) + ')')
T4 = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv'))
P('\n=== Β2. ΜΕΡΟΛΗΨΙΑ (πραγματικο συνολο − προβλεψη, ποντοι) ανα μηνα · ολα τα ματς ===')
for m, nm in MN:
    d = T4[T4.mon == m]
    P(f'  {nm}: μοντελο {np.mean(d.tot - d.mu):+.2f} · ανοιγμα {np.mean(d.tot - d.fair):+.2f} · κλεισιμο {np.mean(d.tot - d.cfair):+.2f} · μοντελο−ανοιγμα {np.mean(d.mu - d.fair):+.2f}'
      + ' · μοντελο ανα σεζον ' + ' '.join(f"{s % 100}:{np.mean(d[d.sea == s].tot - d[d.sea == s].mu):+.1f}" for s in sorted(T4.sea.unique())))
P('  Over picks Ιαν: πραγμ − μοντελο ' + f"{np.mean((T4[(T4.mon == 1) & T4.pick & (T4.side == 1)].tot - T4[(T4.mon == 1) & T4.pick & (T4.side == 1)].mu)):+.2f}"
  + ' · πραγμ − ανοιγμα ' + f"{np.mean((T4[(T4.mon == 1) & T4.pick & (T4.side == 1)].tot - T4[(T4.mon == 1) & T4.pick & (T4.side == 1)].fair)):+.2f}"
  + ' · πραγμ − κλεισιμο ' + f"{np.mean((T4[(T4.mon == 1) & T4.pick & (T4.side == 1)].tot - T4[(T4.mon == 1) & T4.pick & (T4.side == 1)].cfair)):+.2f}")
# ============ Γ ============
RS = R.copy(); RS['reason'] = RS.reason.fillna('')
LAST = {}
for r in RS.itertuples(index=False): LAST[(r.team, r.gd, r.key)] = (r.ep, r.status, r.reason) if (r.team, r.gd, r.key) not in LAST or r.ep >= LAST[(r.team, r.gd, r.key)][0] else LAST[(r.team, r.gd, r.key)]
def kind_reason(rs):
    rl = rs.lower()
    if 'rest' in rl or 'management' in rl: return 'ξεκουραση/διαχειριση'
    if 'illness' in rl or 'protocol' in rl or 'covid' in rl: return 'ασθενεια/πρωτοκολλο'
    if 'personal' in rl: return 'προσωπικοι λογοι'
    if rl.strip(): return 'τραυματισμος'
    return 'χωρις αναφορα'
rec = []
SURP = H[H.sur <= -1]
for r in SURP.itertuples(index=False):
    i = int(r.i); s = int(r.sea); d = dD[i]; sw, tip, r21, _ = SER[i]
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; t0 = rows[0][0]
    me, op = (G.home.values[i], G.away.values[i]) if r.sd == 1 else (G.away.values[i], G.home.values[i])
    for t, mine in ((me, True), (op, False)):
        st = status_at(t, d, t0); pl = PLAYED.get((t, d), set())
        for pid in ROSTER.get((t, s), ()):
            m = mins(pid, t, s, d)
            if m is None or m < 20: continue
            k = PID2K.get((pid, t, s)); s0 = st.get(k); w = W_B.get(s0, 0.0)
            if mine and pid not in pl and w < 1.0:                                   # αιφνιδια απουσια ΔΙΚΗ ΜΑΣ (κοντρα μας)
                lr = LAST.get((t, d, k), (0, None, ''))
                rec.append(dict(jf=r.mon in (1, 2), what='δικη μας απουσια', st0=s0 or 'καθολου στην αναφορα', why=kind_reason(lr[2]) if lr[1] else 'χωρις αναφορα', c=(1 - w) * 0.75 * (value(pid, s - 1) + 2) * m / 48, star=m >= 30))
            if not mine and pid in pl and w > 0:                                     # επιστροφη ΑΝΤΙΠΑΛΟΥ (κοντρα μας)
                rec.append(dict(jf=r.mon in (1, 2), what='επιστροφη αντιπαλου', st0=s0, why='—', c=w * 0.75 * (value(pid, s - 1) + 2) * m / 48, star=m >= 30))
E = pd.DataFrame(rec)
P(f'\n=== Γ. ΤΙ ΕΙΝΑΙ Η «ΠΛΗΡΟΦΟΡΙΑ ΚΟΝΤΡΑ» (χαντικαπ picks με ≤−1π: Ιαν-Φεβ {int((SURP.mon.isin([1, 2])).sum())} · υπολοιποι {int((~SURP.mon.isin([1, 2])).sum())}) — μεριδιο του κοστους (ποντοι) ===')
for col, lab in (('what', 'ειδος'), ('st0', 'κατασταση στο ανοιγμα'), ('why', 'λογος (τελευταια αναφορα, μονο δικες απουσιες)'), ('star', 'παικτης ≥30′')):
    P(f'  — {lab}')
    for v in pd.unique(E[col]):
        a = E[(E[col] == v) & E.jf].c.sum() / E[E.jf].c.sum(); b = E[(E[col] == v) & ~E.jf].c.sum() / E[~E.jf].c.sum()
        P(f'    {str(v):34s} Ιαν-Φεβ {100 * a:5.1f}% · υπολοιποι {100 * b:5.1f}%')
P(f'  κοστος ανα pick (ποντοι): Ιαν-Φεβ {E[E.jf].c.sum() / max((SURP.mon.isin([1, 2])).sum(), 1):.2f} · υπολοιποι {E[~E.jf].c.sum() / max((~SURP.mon.isin([1, 2])).sum(), 1):.2f}')
open(os.path.join(SC, 't115_janfeb_deep_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
