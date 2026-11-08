"""euro_elo_nontop5_test.py — 15/10/2026 (Στελιος: «μηπως το Elo να χρησιμοποιειται μονο για τις εκτος top-5 ομαδες;»).
ΜΗΧΑΝΙΣΜΟΣ (κανενα νουμερο απο ευρωπαικα αποτελεσματα):
  • ομαδες top-5: ΑΜΕΤΑΒΛΗΤΕΣ (η εγχωρια δυναμη τους μεταφερεται σωστα)
  • ομαδες εκτος top-5: η ΘΕΣΗ τους μεσα στη λιγκα (t) ερχεται απο το Elo, ο ΜΕΣΟΣ της λιγκας μενει του μοντελου (ηταν σωστος):
        t_νεο = μεσος t των ομαδων της λιγκας-σεζον + b · (Elo − μεσος Elo των ιδιων ομαδων)
    (μεσοι ορους πανω στις ομαδες της ιδιας λιγκας-σεζον που παιζουν Ευρωπη· ΜΟΝΟ η απλωση αλλαζει, οχι το επιπεδο)
  • b = «ισοτιμια» Elo → t μετρημενη ΜΕΣΑ στις top-5 λιγκες (εκει το t ειναι επικυρωμενο) — οχι απο αποτελεσματα Ευρωπης
  ΔΙΑΓΝΩΣΤΙΚΟ ΙΣΟΤΙΜΙΑΣ: ιδια κλιση μετρημενη στις εκτος top-5 → αν ειναι μεγαλυτερη, το t τους ειναι «τεντωμενο» σε σχεση με το Elo.
Αξιολογηση (ιδια με euro_tophalf_elo_test / uel_elo_by_market): Europa & Conference, ακριβεια (RPS, Δlog-lik ανα σεζον), σκαλα κυριαρχιας,
picks κατηγοριας Α ανα αγορα (φαβ εντος/εκτος, dog εντος/εκτος, 0, ±0.25) με Κ2 (2 βιβλια, ≥3/4, νεα μορφη) · Κ3 xG ισοπαλιας · Κ4 CLV.
"""
import sys
src = open('uel_elo_by_market.py', encoding='utf-8').read().split("x = A[A.comp == 'EuropaLeague'].reset_index(drop=True)")[0]
exec(src)
# ---------- ολες οι πλευρες ολων των ευρωπαικων (για μεσους ορους & ισοτιμια)
SD = []
for mid, c in CP.items():
    lg = LG.get(mid)
    if not lg or not np.isfinite(c['elh']) or not np.isfinite(c['ela']): continue
    sea = None
    m = EUM.get(mid)
    for side, t, el, l in (('h', c['th'], c['elh'], lg[0]), ('a', c['ta'], c['ela'], lg[1])):
        SD.append(dict(mid=mid, side=side, lg=l, t=t, elo=el))
SD = pd.DataFrame(SD)
SEAof = {str(MIDS[i]): SEA[i] for i in range(len(MIDS))}
SD['sea'] = SD.mid.map(SEAof); SD = SD.dropna(subset=['sea'])
SD['key'] = SD.lg + '|' + SD.sea
g = SD.groupby('key'); SD['t_m'] = g.t.transform('mean'); SD['e_m'] = g.elo.transform('mean'); SD['n'] = g.t.transform('size')
SD['dt'] = SD.t - SD.t_m; SD['de_'] = (SD.elo - SD.e_m) / 100
def slope(z):
    z = z[z.n >= 3]; b = np.polyfit(z.de_, z.dt, 1); e = z.dt - np.polyval(b, z.de_)
    return b[0], np.sqrt((e ** 2).sum() / (len(z) - 2) / ((z.de_ - z.de_.mean()) ** 2).sum()), len(z)
bT, sT, nT = slope(SD[SD.lg.isin(TOP5)]); bN, sN, nN = slope(SD[~SD.lg.isin(TOP5)])
print(f'ΙΣΟΤΙΜΙΑ Elo → δυναμη t (ανα 100 Elo, μεσα στην ιδια λιγκα-σεζον):  top-5 b = {bT:.3f} ±{sT:.3f} (n{nT}) · εκτος top-5 {bN:.3f} ±{sN:.3f} (n{nN})')
print(f'   → στις εκτος top-5 καθε 100 Elo διαφορα «γινεται» {bN / bT:.2f}× περισσοτερη δυναμη t απ οτι στις top-5 (>1 = τεντωμενο t)')
SD['t_new'] = np.where(SD.lg.isin(TOP5) | (SD.n < 3), SD.t, SD.t_m + bT * SD.de_)
TN = {(r.mid, r.side): r.t_new - r.t for r in SD.itertuples()}
A['dcE'] = [TN.get((str(MIDS[int(r.i)]), 'h'), 0.0) - TN.get((str(MIDS[int(r.i)]), 'a'), 0.0) for r in A.itertuples()]
A['thN'] = [r.th + TN.get((str(MIDS[int(r.i)]), 'h'), 0.0) for r in A.itertuples()]
A['taN'] = [r.ta + TN.get((str(MIDS[int(r.i)]), 'a'), 0.0) for r in A.itertuples()]
MK2 = (('φαβορι ΕΝΤΟΣ', lambda ln, side: ln <= -0.5 and side == 1, .04, 'q'), ('φαβορι ΕΚΤΟΣ', lambda ln, side: ln <= -0.5 and side == -1, .04, 'q'),
       ('αουτσαιντερ ΕΝΤΟΣ', lambda ln, side: ln >= 0.5 and side == 1, .10, 'p'), ('αουτσαιντερ ΕΚΤΟΣ', lambda ln, side: ln >= 0.5 and side == -1, .10, 'p'),
       ('γραμμη 0 (DNB)', lambda ln, side: ln == 0, .04, 'q'), ('γραμμη −0.25', lambda ln, side: ln == -0.25, .04, 'q'), ('γραμμη +0.25', lambda ln, side: ln == 0.25, .04, 'q'))
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE')):
    x = A[A.comp == cm].reset_index(drop=True); seas = sorted(x.sea.unique())
    LV = {'M': (x.lh.values, x.la.values), 'N': (x.lh.values * np.exp(x.dcE.values / 2), x.la.values * np.exp(-x.dcE.values / 2))}
    R = {v: rps(*LV[v], x.gd.values) for v in LV}
    print(f'\n=================== {lab}: {len(x)} ματς ===================')
    for v, nm in (('M', 'σημερινο'), ('N', 'Elo μονο εκτος top-5')):
        d = {s: ll(x[x.sea == s], LV[v][0][(x.sea == s).values], LV[v][1][(x.sea == s).values]) -
                ll(x[x.sea == s], LV['M'][0][(x.sea == s).values], LV['M'][1][(x.sea == s).values]) for s in seas}
        npos = sum(t > 0 for t in d.values()); k1 = v != 'M' and npos >= 3 and R[v].mean() < R['M'].mean()
        sd = []
        for k_, r in x.iterrows():
            mm = LV[v][0][k_] - LV[v][1][k_]
            for sg, t, lg in ((1, r.th, r.lgh), (-1, r.ta, r.lga)):
                if lg not in TOP5: sd.append((t, sg * (r.gd - mm)))
        S = pd.DataFrame(sd, columns=['t', 'e'])
        print(f'   {nm:22s} RPS {R[v].mean():.4f} · Δlog-lik ' + ' '.join(f'{s[2:]}:{t:+.1f}' for s, t in d.items()) +
              (f' · Κ1 {"✓" if k1 else "✗"}' if v != 'M' else '      ') + f' │ σκαλα κυριαρχιας {S[S.t < .3].e.mean():+.2f} / {S[S.t >= .9].e.mean():+.2f}')
    # picks ανα αγορα
    lv_ok = np.isfinite(x.lvl.values) & (x.lw.values > 0.2)
    mk_all = []
    for r in x.itertuples():
        s = sn(int(r.i), 'Crown', 0) or sn(int(r.i), 'SBOBET', 0); mk_all.append(implied_margin(int(r.i), *s) if s else np.nan)
    mk_all = np.array(mk_all); okc = lv_ok & np.isfinite(mk_all); cal = np.polyfit(mk_all[okc], x.lvl.values[okc], 1, w=x.lw.values[okc])
    xa_ = x[x.cat == 'A']
    def pk(v):
        P = []
        for k_ in xa_.index:
            r = x.loc[k_]; i = int(r.i); D_ = sdist(LV[v][0][k_], LV[v][1][k_])
            for bk in ('Crown', 'SBOBET'):
                sc = sn(i, bk, 0); mcl = implied_margin(i, *sc) if sc else np.nan
                for mname, cond, th, how in MK2:
                    got = set()
                    for h in HSP:
                        s = sn(i, bk, h)
                        if not s: continue
                        L, oh, oa = s
                        for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                            if side in got or not (1.70 <= o <= 2.10) or not cond(ln, side): continue
                            f = cover_q if how == 'q' else picks.p_cover
                            if edge(*f(D_, side, ln), o) < th: continue
                            got.add(side); me = implied_margin(i, L, oh, oa)
                            P.append(dict(m=mname, sea=r.sea, bk=bk, pnl=picks.settle(GD[i], side, ln, o),
                                          lv=side * (r.lvl - (cal[0] * me + cal[1])) if lv_ok[k_] else np.nan, lw=r.lw,
                                          clv=side * (mcl - me) if np.isfinite(mcl) else np.nan))
        return pd.DataFrame(P)
    PK = {v: pk(v) for v in ('M', 'N')}
    print(f'   PICKS κατηγοριας Α ({len(xa_)} ματς) ανα αγορα — σημερινο / Elo μονο εκτος top-5')
    for mname, *_ in MK2:
        for v, nm in (('M', 'σημερινο'), ('N', 'Elo εκτος top-5')):
            y = PK[v][PK[v].m == mname] if len(PK[v]) else PK[v]
            if len(y) < 6: print(f'      {mname:18s} {nm:15s} {len(y) / 2:4.0f} picks (λιγα)'); continue
            mb = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
            k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
            yy = y.dropna(subset=['lv']); lv = np.average(yy.lv, weights=yy.lw) if len(yy) else np.nan; cl = y.clv.mean()
            print(f'      {mname:18s} {nm:15s} {n:4.0f} picks {100 * mb.mean():+6.1f}% (' + ' '.join(f'{q[2:]} {100 * w_:+.0f}' for q, w_ in ps.items()) +
                  f') · xG ισοπ. {lv:+.2f} · CLV {cl:+.3f} │ Κ2 {"✓" if k2 else "✗"} Κ3 {"✓" if lv > 0 else "✗"} Κ4 {"✓" if cl > 0 else "✗"}'
                  + ('  ← ΠΕΡΝΑ' if (k2 and lv > 0 and cl > 0 and v == 'N') else ''))
