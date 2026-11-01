"""euro_value_blend_quality.py — 15/10/2026 (Στελιος: «μου αρεσει ο μηχανισμος γιατι κοβει τα picks που ειναι το προβλημα μας — ποσο καλυτερη γινεται η
προβλεψη, η κλιση και τα υπολοιπα τεστ εκτος ROI;»).
Το Φ2 ειναι ΦΙΛΤΡΟ (παιζω/δεν παιζω) — δεν αλλαζει την προβλεψη. Για να μετρηθει ως ΠΡΟΒΛΕΨΗ, ο ιδιος μηχανισμος γινεται μιξη:
   διαφορα = (1−w)·μοντελο + w·«τι λεει η αξια»   (αξια = k·ln(αξια ενδεκαδας γηπ/φιλ) + εδρα, LOSO · w απο τις αλλες 3 σεζον · συνολο γκολ ιδιο)
ΜΕΤΡΑ (Europa, και Conference / Champions για συγκριση, ολες οι κατηγοριες με γνωστη αξια):
  ακριβεια: RPS, Δlog-lik ανα σεζον · ΚΛΙΣΗ: ποσο «αξιζει» 1 γκολ διαφορας της προβλεψης στα πραγματικα γκολ (1 = σωστη κλιμακα) ·
  ΠΛΗΡΟΦΟΡΙΑ περα απο την αγορα κλεισιματος (b: 0 = τιποτα, 1 = η προβλεψη σωστη) · σκαλα κυριαρχιας (εκτος top-5)
  + για τα picks του Φ2 (κομμενα / μενουν): edge που δηλωνε το μοντελο vs ROI, xG σε ισοπαλια vs αγορα, κινηση αγορας.
"""
import sys
exec(open("euro_value_filter_check.py", encoding="utf-8").read().split("# πλευρα ΧΩΡΙΣ FotMob")[0])
NL = chr(10)
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
def ols(x, y):
    X = np.c_[np.ones(len(x)), x]; b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    return b[1], np.sqrt(np.diag(np.linalg.inv(X.T @ X) * (e @ e) / (len(x) - 2)))[1]
WG = np.round(np.arange(0.0, 1.01, 0.05), 2)
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    x = A[(A.comp == cm) & A.hasv].reset_index(drop=True); seas = sorted(x.sea.unique())
    x['vm'] = [VF[s][0] * lv + VF[s][1] for s, lv in zip(x.sea, x.lv_)]
    mk = []
    for r in x.itertuples():
        s = snapT(str(MIDS[int(r.i)]), 'Crown', 0) or snapT(str(MIDS[int(r.i)]), 'SBOBET', 0); mk.append(implied_margin(int(r.i), *s) if s else np.nan)
    x['mk'] = mk
    def lamW(y, w):
        T = y.lh.values + y.la.values; m = (1 - w) * (y.lh.values - y.la.values) + w * y.vm.values
        return np.maximum((T + m) / 2, .05), np.maximum((T - m) / 2, .05)
    W_ = {}; lh1 = np.zeros(len(x)); la1 = np.zeros(len(x))
    for s in seas:
        tr = x[x.sea != s]; W_[s] = WG[int(np.argmax([ll(tr, *lamW(tr, w)) for w in WG]))]
        te = (x.sea == s).values; a, b = lamW(x[te], W_[s]); lh1[te] = a; la1[te] = b
    R0 = rps(x.lh.values, x.la.values, x.gd.values); R1 = rps(lh1, la1, x.gd.values)
    d = {s: ll(x[x.sea == s], lh1[(x.sea == s).values], la1[(x.sea == s).values]) - ll(x[x.sea == s], x.lh.values[(x.sea == s).values], x.la.values[(x.sea == s).values]) for s in seas}
    ok = x.mk.notna().values
    RM = rps(np.maximum((x.lh + x.la + x.mk) / 2, .05)[ok].values, np.maximum((x.lh + x.la - x.mk) / 2, .05)[ok].values, x.gd.values[ok])
    m0 = (x.lh - x.la).values; m1 = lh1 - la1; g = x.gd.values.astype(float)
    print(f'{NL}===== {lab}: {len(x)} ματς με γνωστη αξια · βαρος αξιας w (αλλες 3 σεζον): ' + ' '.join(f'{s[2:]}:{W_[s]:.2f}' for s in seas))
    print(f'   ΑΚΡΙΒΕΙΑ  RPS σημερινο {R0.mean():.4f} → με αξια {R1.mean():.4f} · (αγορα κλεισιματος {RM.mean():.4f} στα {ok.sum()}) · Δlog-lik ' +
          ' '.join(f'{s[2:]}:{t:+.1f}' for s, t in d.items()) + f' · θετικες {sum(t > 0 for t in d.values())}/4')
    for nm, m_ in (('σημερινο', m0), ('με αξια', m1)):
        b1, s1 = ols(m_, g); b2, s2 = ols((m_ - x.mk.values)[ok], (g - x.mk.values)[ok])
        sd = []
        for k_, r in x.iterrows():
            for sg, t, lg in ((1, r.th, r.lgh), (-1, r.ta, r.lga)):
                if lg not in TOP5: sd.append((t, sg * (r.gd - m_[k_])))
        S = pd.DataFrame(sd, columns=['t', 'e'])
        print(f'   {nm:9s} ΚΛΙΣΗ (1 γκολ προβλεψης = ? πραγματικα) {b1:.2f}±{s1:.2f} · ΠΛΗΡΟΦΟΡΙΑ περα απο κλεισιμο b {b2:+.2f}±{s2:.2f} · '
              f'σκαλα κυριαρχιας {S[S.t < .3].e.mean():+.2f} / {S[S.t >= .9].e.mean():+.2f} (ευρος {S[S.t < .3].e.mean() - S[S.t >= .9].e.mean():.2f})')
# picks Φ2: δηλωμενο edge vs πραγματικο, xG, CLV
print(f'{NL}===== PICKS του Φ2 (κανονες καθε διοργανωσης) — ποιοτητα ΕΚΤΟΣ ROI')
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    P = picks_comp(cm); P = P[P.dis.notna()]
    for nm, y in (('ΚΟΒΟΝΤΑΙ', P[P.dis <= -.5]), ('ΜΕΝΟΥΝ', P[P.dis > -.5])):
        yy = y.dropna(subset=['lv'])
        print(f'   {lab:10s} {nm:9s} {len(y) / 2:4.0f} picks · ROI {100 * y.pnl.mean():+6.1f}% · xG ισοπαλιας vs αγορα {np.average(yy.lv, weights=yy.lw):+.2f}/90 · '
              f'κινηση αγορας μετα την εισοδο {y.clv.mean():+.3f} γκολ')
