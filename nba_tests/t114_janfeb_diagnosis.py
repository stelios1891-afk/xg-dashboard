# -*- coding: utf-8 -*-
"""t114_janfeb_diagnosis.py — ΤΙ ΧΑΛΑΕΙ ΤΑ PICKS ΤΟΝ ΙΑΝ-ΦΕΒ; (27/10/2026, Στελιος «εδω ειμαστε για τα δυσκολα — ποιο ειναι το προβλημα, ποια picks
κοντραρει η αγορα και γιατι· ειδησεις; κουραση; τι ειναι;»). ΠΕΡΙΓΡΑΦΙΚΟ / ΔΙΑΓΝΩΣΤΙΚΟ — δεν αλλαζει τιποτα.
PICKS: ανοιγμα Crown, edge ≥8% ΠΑΝΤΟΥ (για διαγνωση· και τα 8-12% του Ιαν-Φεβ μεσα), 5 σεζον.
  ΧΑΝΤΙΚΑΠ: αντιγραφο live t22 (VNO + απουσιες αναφορας ανοιγματος, πιθανοτητες) · ΣΥΝΟΛΑ: live μηχανη (_t104_totals_live.csv).
ΣΥΓΚΡΙΣΗ: Ιαν-Φεβ vs ΥΠΟΛΟΙΠΟΙ μηνες (Οκτ-Δεκ, Μαρ-Απρ). Για καθε ομαδα χαρακτηριστικων: ποσο συχνο · ROI · CLV · % «αγορα κοντρα» (CLV < −0.25π).
ΧΑΡΑΚΤΗΡΙΣΤΙΚΑ:
 1 ΑΙΦΝΙΔΙΑ ΠΛΗΡΟΦΟΡΙΑ μετα το ανοιγμα (αληθεια = box score): παικτης ρολου (≥20′ τα τελευταια 10) ΔΕΝ επαιξε ενω η αναφορα του ανοιγματος δεν
   τον ειχε Out (αιφνιδια απουσια, βαρος 1 − πιθ. αναφορας) · ή ΕΠΑΙΞΕ ενω ηταν Out/Doubtful/Questionable (επιστροφη). Ποντοι (αξια οπως live) προς
   την πλευρα μας: «κοντρα» ≤ −1π · «υπερ» ≥ +1π · «τιποτα» αλλιως. Συνολα: −0.5·επιθεση + 1.0·αμυνα, προς την πλευρα μας (Over/Under).
 2 ΚΟΥΡΑΣΗ/ΠΡΟΓΡΑΜΜΑ: ματς τις τελευταιες 7 μερες (δικη μας πλευρα − αντιπαλου στο χαντικαπ· αθροισμα στα συνολα) · B2B · συνεχομενα εκτος.
 3 ΗΜΕΡΟΛΟΓΙΟ: ±10 μερες απο την προθεσμια μεταγραφων · 7 μερες μετα το All-Star.
 4 ΟΜΑΔΑ: pick σε ομαδα κατω-8 σε ποσοστο νικων τη στιγμη (ή ΚΟΝΤΡΑ σε τετοια) · φαβορι/αουτσαιντερ · εντος/εκτος · Over/Under.
 5 ΔΙΑΦΩΝΙΑ μοντελου−αγορας (ποντοι).
Εξοδος: nba_tests/t114_janfeb_diagnosis_out.txt · cache _t114_picks.csv"""
import os, sys, io, contextlib, collections, datetime as dt
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
class _B(io.StringIO):
    def reconfigure(self, **k): pass
src = open(os.path.join(SC, 't22_report_timing.py'), encoding='utf-8').read().split("TAUS = (('ανοιγμα'")[0].replace("if os.environ.get('T22_AUDIT'):", "if False:")
g = {'__file__': os.path.join(SC, 't22_report_timing.py'), '__name__': 'x'}
with contextlib.redirect_stdout(_B()): exec(src, g)
sys.stdout.reconfigure(encoding='utf-8')
np, pd = g['np'], g['pd']
G, VNO, SER, SHIFT, line_at, cover_, SIG_, abs_cost, W_B, EV, ACT, SEAS_G, dD, REPS = (g[x] for x in (
    'G', 'VNO', 'SER', 'SHIFT', 'line_at', 'cover_', 'SIG_', 'abs_cost', 'W_B', 'EV', 'ACT', 'SEAS_G', 'dD', 'REP_SEASONS'))
status_at, K2P, mins, value, A2, HM = g['status_at'], g['K2P'], g['mins'], g['value'], g['A2'], g['HM']
odval = g['nt']['odval']
# ---- ποιος επαιξε: (ομαδα, μερα) → {pid}
PLAYED = collections.defaultdict(set)
for r in A2.itertuples(index=False): PLAYED[(r.team, r.dd)].add(r.pid)
PID2K = {(r.pid, r.team, int(r.s)): r.k for r in A2.drop_duplicates(['pid', 'team', 's']).itertuples(index=False)}
ROSTER = collections.defaultdict(set)
for (pid, t, s) in HM: ROSTER[(t, s)].add(pid)
def surprise(t, d, s, t0):
    """(χαντ: ποντοι ΥΠΕΡ της ομαδας t απο ο,τι μαθαμε μετα το ανοιγμα, συνολα: ποντοι στο συνολο) · αιφνιδιες απουσιες − / επιστροφες +"""
    st = status_at(t, d, t0); pl = PLAYED.get((t, d), set()); hc = 0.0; tt = 0.0; n_abs = 0
    for pid in ROSTER.get((t, s), ()):
        m = mins(pid, t, s, d)
        if m is None or m < 20: continue
        k = PID2K.get((pid, t, s)); w = W_B.get(st.get(k), 0.0)
        c = 0.75 * (value(pid, s - 1) + 2.0) * m / 48; o_, d_ = odval(pid, s - 1); tot_eff = -0.5 * (o_ + 0.5) * m / 48 + 1.0 * (d_ + 0.5) * m / 48
        if pid not in pl and w < 1.0:
            hc -= (1 - w) * c; tt += (1 - (1.0 if st.get(k) == 'Out' else 0.0)) * tot_eff; n_abs += 1
        elif pid in pl and w > 0:
            hc += w * c; tt -= (1.0 if st.get(k) == 'Out' else 0.0) * tot_eff
    return hc, tt, n_abs
# ---- προγραμμα / ποσοστο νικων
SCH = collections.defaultdict(list)
for i in range(len(G)):
    for t, home in ((G.home.values[i], True), (G.away.values[i], False)): SCH[(t, int(SEAS_G[i]))].append((dD[i], i, home))
for k in SCH: SCH[k].sort(key=lambda x: x[0])
POS = {}
for k, L in SCH.items():
    w = l = 0; away_run = 0
    for j, (d, i, home) in enumerate(L):
        prev = [x[0] for x in L[:j]]
        g7 = sum(1 for p in prev if (d - p).astype(int) <= 7); b2b = bool(prev) and (d - prev[-1]).astype(int) == 1
        POS[(k[0], i)] = dict(g7=g7, b2b=b2b, away_run=away_run + (0 if home else 1), wp=(w / (w + l)) if w + l >= 10 else np.nan)
        away_run = 0 if home else away_run + 1
        a = ACT[i]
        if np.isfinite(a):
            win = (a > 0) == home
            w += win; l += (not win)
WPR = {}
for s in set(int(x) for x in SEAS_G):
    for i in np.where(SEAS_G == s)[0]:
        pass
DEAD = {2022: '2022-02-10', 2023: '2023-02-09', 2024: '2024-02-08', 2025: '2025-02-06', 2026: '2026-02-05'}
ASB = {2022: '2022-02-24', 2023: '2023-02-23', 2024: '2024-02-22', 2025: '2025-02-19', 2026: '2026-02-18'}      # πρωτη μερα ΜΕΤΑ το All-Star
def cal(d, s):
    dd = (d - np.datetime64(DEAD[s])).astype(int); da = (d - np.datetime64(ASB[s])).astype(int)
    return ('προθεσμια ±10' if abs(dd) <= 10 else ('μετα All-Star 0-7' if 0 <= da <= 7 else 'αλλο'))
# rank κατω-8 ανα μερα (ποσοστο νικων ως τοτε)
def bottom8(t, i, s):
    wp = POS[(t, i)]['wp']
    if not np.isfinite(wp): return False
    d = dD[i]; others = [POS[(tt, ii)]['wp'] for (tt, ss), L in SCH.items() if ss == s for (dx, ii, _) in L if dx < d][-0:]
    return None
# απλουστερο: κατω-8 = ποσοστο νικων < 0.35
# ---- ΧΑΝΤΙΚΑΠ picks
HR = []
for i, (sw, tip, r21, _) in SER.items():
    s = int(SEAS_G[i])
    if s not in EV or s not in REPS or not np.isfinite(VNO[i]): continue
    rows = [[x[0] + SHIFT] + list(x[1:]) for x in r21]; rows = [x for x in rows if x[0] <= tip + 900]
    if not rows: continue
    t0 = rows[0][0]; ln = line_at(rows, t0, sw); cl = line_at(rows, tip, sw)
    if not ln or not cl: continue
    h, a, d = G.home.values[i], G.away.values[i], dD[i]
    m0 = VNO[i] - abs_cost(h, d, s, t0, W_B)[0] + abs_cost(a, d, s, t0, W_B)[0]
    pw, pp, pl = cover_(m0, ln[0], SIG_); e1, e2 = pw * ln[1] + pp - 1, pl * ln[2] + pp - 1
    sd, e, od = (1, e1, ln[1]) if e1 >= e2 else (-1, e2, ln[2])
    if e < .08: continue
    x = (ACT[i] + ln[0]) * sd; res = (od - 1) if x > 0 else (0.0 if x == 0 else -1.0)
    sh, th, nh = surprise(h, d, s, t0); sa, ta, na = surprise(a, d, s, t0)
    me, op = (h, a) if sd == 1 else (a, h)
    pm, po = POS[(me, i)], POS[(op, i)]
    HR.append(dict(i=i, sea=s, mon=int(str(d)[5:7]), sd=sd, edge=e, res=res, clv=sd * (cl[3] - ln[3]), sur=sd * (sh - sa), nsur=nh + na,
                   g7=pm['g7'] - po['g7'], b2b_me=pm['b2b'], b2b_op=po['b2b'], away_run=pm['away_run'], cal=cal(d, s),
                   wp_me=pm['wp'], wp_op=po['wp'], fav=(sd * (-ln[0])) > 0, home=sd == 1, gap=sd * (m0 - ln[3])))
H = pd.DataFrame(HR)
# ---- ΣΥΝΟΛΑ picks
T4 = pd.read_csv(os.path.join(SC, '_t104_totals_live.csv')); T4 = T4[T4.pick].copy()
GI = {(str(dD[k])[:10], G.home.values[k], G.away.values[k]): k for k in range(len(G))}
TR = []
for r in T4.itertuples(index=False):
    i = GI.get((str(r.date)[:10], r.home, r.away))
    if i is None or i not in SER: continue
    sw, tip, r21, r23 = SER[i]; rr = [[x[0] + SHIFT] + list(x[1:]) for x in (r23 or [])]
    if not rr: continue
    t0 = rr[0][0]; s = int(r.sea); d = dD[i]
    sh, th, nh = surprise(r.home, d, s, t0); sa, ta, na = surprise(r.away, d, s, t0)
    ph, pa = POS[(r.home, i)], POS[(r.away, i)]
    TR.append(dict(i=i, sea=s, mon=int(r.mon), sd=int(r.side), edge=r.edge, res=r.res, clv=r.clv, sur=r.side * (th + ta), nsur=nh + na,
                   g7=ph['g7'] + pa['g7'], b2b_n=int(ph['b2b']) + int(pa['b2b']), cal=cal(d, s), gap=r.side * (r.mu - r.fair),
                   wp_lo=min(ph['wp'], pa['wp']) if np.isfinite(ph['wp']) and np.isfinite(pa['wp']) else np.nan))
T = pd.DataFrame(TR)
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
def cell(d):
    if not len(d): return '—'
    ps = d.groupby('sea').res.sum()
    return f'{100 * d.res.mean():+6.1f}% ({len(d):4d}, θ{int((ps > 0).sum())}/{d.sea.nunique()}) CLV {d.clv.mean():+.2f} κοντρα {100 * (d.clv < -0.25).mean():3.0f}%'
def block(lab, D, feats):
    JF = D.mon.isin([1, 2]); P(f'\n=== {lab} ===  (κελι: ROI (picks, θετ. σεζον) · CLV ποντοι · % picks οπου η αγορα πηγε κοντρα)')
    P(f'  ΟΛΑ            Ιαν-Φεβ {cell(D[JF])}   │ υπολοιποι {cell(D[~JF])}')
    for fname, fn in feats:
        P(f'  — {fname}')
        cats = fn(D)
        for c in [c for c in pd.unique(cats) if isinstance(c, str)]:
            m = cats == c
            P(f'    {c:24s} Ιαν-Φεβ {100 * (m & JF).sum() / max(JF.sum(), 1):4.0f}% των picks · {cell(D[m & JF])}   │ υπολοιποι {100 * (m & ~JF).sum() / max((~JF).sum(), 1):4.0f}% · {cell(D[m & ~JF])}')
def sur3(D): return np.where(D.sur <= -1, 'κοντρα μας (≤−1π)', np.where(D.sur >= 1, 'υπερ μας (≥+1π)', 'τιποτα σημαντικο'))
FH = [('1 ΑΙΦΝΙΔΙΑ ΠΛΗΡΟΦΟΡΙΑ μετα το ανοιγμα (box score)', sur3),
      ('2 ΚΟΥΡΑΣΗ: ματς σε 7 μερες (εμεις − αντιπαλος)', lambda D: np.where(D.g7 >= 1, 'εμεις περισσοτερα', np.where(D.g7 <= -1, 'αντιπαλος περισσοτερα', 'ιδια'))),
      ('2 B2B', lambda D: np.where(D.b2b_me & ~D.b2b_op, 'εμεις B2B', np.where(D.b2b_op & ~D.b2b_me, 'αντιπαλος B2B', np.where(D.b2b_me & D.b2b_op, 'και οι δυο', 'κανεις')))),
      ('2 συνεχομενα εκτος (δικη μας πλευρα)', lambda D: np.where(D.away_run >= 3, '3ο+ εκτος στη σειρα', np.where(D.away_run >= 1, '1ο-2ο εκτος', 'εντος'))),
      ('3 ΗΜΕΡΟΛΟΓΙΟ', lambda D: D.cal.values),
      ('4 ΟΜΑΔΑ: ποσοστο νικων', lambda D: np.where(D.wp_me < .35, 'pick ΣΕ αδυναμη (<35%)', np.where(D.wp_op < .35, 'pick ΚΟΝΤΡΑ σε αδυναμη', np.where(D.wp_me.isna(), '<10 ματς', 'αλλο')))),
      ('4 φαβορι/αουτσαιντερ', lambda D: np.where(D.fav, 'φαβορι', 'αουτσαιντερ')),
      ('4 εντος/εκτος', lambda D: np.where(D.home, 'γηπεδουχος', 'φιλοξενουμενος')),
      ('5 ΔΙΑΦΩΝΙΑ μοντελο−αγορα', lambda D: np.where(D.gap.abs() >= 4, '≥4π', np.where(D.gap.abs() >= 2.5, '2.5-4π', '<2.5π')))]
FT = [('1 ΑΙΦΝΙΔΙΑ ΠΛΗΡΟΦΟΡΙΑ μετα το ανοιγμα (box score)', sur3),
      ('2 ΚΟΥΡΑΣΗ: ματς σε 7 μερες (αθροισμα 2 ομαδων)', lambda D: np.where(D.g7 >= 7, '≥7', np.where(D.g7 >= 5, '5-6', '≤4'))),
      ('2 B2B (ποσες ομαδες)', lambda D: np.array([f'{int(x)} σε B2B' for x in D.b2b_n])),
      ('3 ΗΜΕΡΟΛΟΓΙΟ', lambda D: D.cal.values),
      ('4 Over/Under', lambda D: np.where(D.sd == 1, 'Over', 'Under')),
      ('4 ματς με αδυναμη ομαδα (<35%)', lambda D: np.where(D.wp_lo < .35, 'ναι', np.where(D.wp_lo.isna(), '<10 ματς', 'οχι'))),
      ('5 ΔΙΑΦΩΝΙΑ μοντελο−αγορα', lambda D: np.where(D.gap.abs() >= 6, '≥6π', np.where(D.gap.abs() >= 3.5, '3.5-6π', '<3.5π')))]
P(f't114 · ΔΙΑΓΝΩΣΗ ΙΑΝ-ΦΕΒ · Crown ανοιγμα · edge ≥8% παντου · 5 σεζον · χαντικαπ picks {len(H)} · συνολα picks {len(T)}')
block('ΧΑΝΤΙΚΑΠ', H, FH)
block('ΣΥΝΟΛΑ', T, FT)
# ποσο εξηγει η αιφνιδια πληροφορια το χασμα Ιαν-Φεβ
for lab, D in (('ΧΑΝΤΙΚΑΠ', H), ('ΣΥΝΟΛΑ', T)):
    JF = D.mon.isin([1, 2]); m = D.sur > -1
    P(f'\n{lab}: χωρις τα picks με αιφνιδια πληροφορια ΚΟΝΤΡΑ (≤−1π): Ιαν-Φεβ {cell(D[JF & m])} │ υπολοιποι {cell(D[~JF & m])}')
    P(f'  μεση αιφνιδια πληροφορια προς εμας (ποντοι): Ιαν-Φεβ {D.sur[JF].mean():+.2f} · υπολοιποι {D.sur[~JF].mean():+.2f} · αιφνιδιες απουσιες/ματς Ιαν-Φεβ {D.nsur[JF].mean():.2f} vs {D.nsur[~JF].mean():.2f}')
    P('  ανα μηνα: ' + ' · '.join(f"{mo}: πληρ. {D.sur[D.mon == mo].mean():+.2f}π, απουσ. {D.nsur[D.mon == mo].mean():.2f}, ROI {100 * D.res[D.mon == mo].mean():+.1f}%" for mo in (10, 11, 12, 1, 2, 3, 4) if (D.mon == mo).any()))
H.to_csv(os.path.join(SC, '_t114_hcap.csv'), index=False); T.to_csv(os.path.join(SC, '_t114_tot.csv'), index=False)
P('\nελεγχος (2 picks Ιαν με αιφνιδια πληροφορια κοντρα):')
for _, q in H[H.mon.isin([1]) & (H.sur <= -1)].head(2).iterrows():
    j = int(q.i); P(f'   {G.home.values[j]}-{G.away.values[j]} {str(dD[j])[:10]} · pick {"γηπ" if q.sd == 1 else "φιλ"} · αιφνιδια πληροφορια {q.sur:+.1f}π (αιφνιδιες απουσιες {q.nsur}) · CLV {q.clv:+.2f} · αποτ {q.res:+.2f}')
open(os.path.join(SC, 't114_janfeb_diagnosis_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
