"""uel_home_away_fav_diag.py — 14/10/2026 (Στελιος: «πως γινεται τα φαβορι εντος να ειναι κερδοφορα και τα φαβορι εκτος οχι; ποια ειναι η πηγη;»).
Κατηγορια Α (FotMob και οι 2), 4 σεζον, κλεισιμο Crown (αλλιως SBOBET). Ολα απο τη σκοπια του ΓΗΠΕΔΟΥΧΟΥ:
  1) ΑΝΑΛΥΣΗ ΛΑΘΟΥΣ: (xG διαφορα − διαφορα μοντελου) = a + b·(διαφορα μοντελου) → a = λαθος ΕΔΡΑΣ (ιδιο σε καθε ματς), b = ΣΥΜΠΙΕΣΗ
     (μεγαλες διαφορες φουσκωμενες). Ιδιο για γκολ και για την αγορα (κλεισιμο). UEL / UECL / UCL.
  2) ΦΑΒΟΡΙ ΑΓΟΡΑΣ εντος vs εκτος: διαφορα (σκοπια φαβορι) αγορα / μοντελο / γκολ / xG και ποσο απο το λαθος του μοντελου εξηγειται απο
     εδρα (a) και απο συμπιεση (b·διαφορα).
  3) PICKS φαβορι @4% (σημερινος κανονας) εντος/εκτος: δηλωμενο edge vs πραγματικο ROI vs αξια xG.
"""
import sys, os, glob
NL = chr(10)
src = open('uecl_full_review.py', encoding='utf-8').read().split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0]
_R = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _R; sys.stdout.reconfigure(encoding='utf-8')
XG = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []
        if not sh: continue
        hid = int(m['home']['id'])
        XG[str(k)] = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid),
                      sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid))
rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('EuropaLeague', 'ConferenceLeague', 'ChampionsLeague') or VI.get(str(MIDS[i])) is None or LH_N[i] <= 0 or cat(i) != 'A': continue
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    x = XG.get(str(MIDS[i]))
    if not s or not x: continue
    rows.append(dict(i=i, comp=COMP[i], sea=SEA[i], gd=GD[i], xgd=x[0] - x[1], mgd=LH_N[i] - LA_N[i], kgd=implied_margin(i, *s), L=s[0]))
C = pd.DataFrame(rows)
def fit(x, col, base='mgd'):
    y = x[col] - x[base]; X = np.c_[np.ones(len(x)), x[base]]
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b
    cov = np.linalg.inv(X.T @ X) * (e @ e) / (len(x) - 2); se = np.sqrt(np.diag(cov))
    return b, se
print('1) ΑΝΑΛΥΣΗ ΛΑΘΟΥΣ (σκοπια γηπεδουχου): πραγματικο − προβλεψη = a (λαθος ΕΔΡΑΣ) + b × προβλεψη (b<0 = ΣΥΜΠΙΕΣΗ, οι διαφορες φουσκωμενες)')
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    x = C[C.comp == cm]
    print(f'   {lab} ({len(x)} ματς): μεση διαφορα γηπεδουχου πραγμ {x.gd.mean():+.2f} · xG {x.xgd.mean():+.2f} · μοντελο {x.mgd.mean():+.2f} · αγορα {x.kgd.mean():+.2f}')
    for nm, base, col in (('ΜΟΝΤΕΛΟ vs xG ', 'mgd', 'xgd'), ('ΜΟΝΤΕΛΟ vs γκολ', 'mgd', 'gd'), ('ΑΓΟΡΑ vs xG   ', 'kgd', 'xgd'), ('ΑΓΟΡΑ vs γκολ ', 'kgd', 'gd')):
        (a, b), (sa, sb) = fit(x, col, base)
        print(f'      {nm}: εδρα a {a:+.2f} ±{sa:.2f} · συμπιεση b {b:+.2f} ±{sb:.2f}')
print(NL + '2) ΦΑΒΟΡΙ ΑΓΟΡΑΣ (κλεισιμο, γραμμη ≤ −0.25 για το φαβορι) — διαφορα απο τη σκοπια του ΦΑΒΟΡΙ')
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    x = C[C.comp == cm]; (a, b), _ = fit(x, 'xgd')
    print(f'   {lab}')
    for nm, m_, sg in (('φαβορι ΕΝΤΟΣ', x.L <= -0.25, 1), ('φαβορι ΕΚΤΟΣ', x.L >= 0.25, -1)):
        y = x[m_]; err = sg * (y.mgd - y.xgd)
        ea = -sg * a; eb = -sg * b * y.mgd
        print(f'      {nm:14s} n{len(y):4d} · αγορα {sg * y.kgd.mean():+.2f} · ΜΟΝΤΕΛΟ {sg * y.mgd.mean():+.2f} · γκολ {sg * y.gd.mean():+.2f} · xG {sg * y.xgd.mean():+.2f}'
              f' │ μοντελο − xG {err.mean():+.2f} ±{err.std() / np.sqrt(len(y)):.2f} = απο εδρα {ea:+.2f} + απο συμπιεση {eb.mean():+.2f} + υπολοιπο {err.mean() - ea - eb.mean():+.2f}'
              f' │ μοντελο − αγορα {sg * (y.mgd - y.kgd).mean():+.2f}')
# ---- 3) picks
print(NL + '3) PICKS ΦΑΒΟΡΙ @4% (σημερινος κανονας, σωστα τεταρτα, ≤−0.5, 1.70-2.10, πρωτη εμφανιση ≤72ω) — Europa')
HSx = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1)
P = []
for r in C[C.comp == 'EuropaLeague'].itertuples():
    i = r.i; D = sdist(LH_N[i], LA_N[i])
    for bk in ('Crown', 'SBOBET'):
        got = set()
        for h in HSx:
            s = snap_ah(MIDS[i], bk, h)
            if not s: continue
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if side in got or ln > -0.5 or not (1.70 <= o <= 2.10): continue
                e = edge(*cover_q(D, side, ln), o)
                if e < .04: continue
                got.add(side)
                xh, xa = XG[str(MIDS[i])]; pw, pp = cover_q(sdist(max(xh, .05), max(xa, .05)), side, ln)
                P.append(dict(sea=r.sea, bk=bk, home=side == 1, e=e, pnl=picks.settle(GD[i], side, ln, o), xv=edge(pw, pp, o),
                              err=side * (r.mgd - r.xgd), mm=side * r.mgd, km=side * r.kgd))
P = pd.DataFrame(P)
for nm, m_ in (('ΕΝΤΟΣ', P.home), ('ΕΚΤΟΣ', ~P.home)):
    y = P[m_]
    print(f'   {nm}: {cc(y)} · δηλωμενο edge {100 * y.e.mean():+.1f}% · αξια με βαση xG {100 * y.xv.mean():+.1f}% · μοντελο {y.mm.mean():+.2f} / αγορα {y.km.mean():+.2f} / '
          f'μοντελο − xG {y.err.mean():+.2f}')
