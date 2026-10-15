"""euro_value_filter_check.py — 15/10/2026 (Στελιος: «τρεξε και τα 2 — στις αλλες 2 διοργανωσεις δεν εχουμε δει οτι αυτα τα picks βλαπτουν, π.χ. τα
αουτσαιντερ του Conference ιστορικα αποδιδουν, ισως κοβονταν»).
ΦΙΛΤΡΟ Φ2 (ιδιο με uel_value_filter, κανενα νεο νουμερο): «τι λεει η αξια» = k·ln(συνηθισμενη αξια ενδεκαδας γηπ/φιλ) + εδρα (ευθεια LOSO απο ολα τα
ευρωπαικα) · κοβεται το pick αν η αξια βλεπει την ομαδα του pick ≥0.5 γκολ χειροτερη απο το μοντελο.
 1) ΕΠΑΝΑΛΗΨΗ: Conference & Champions League με τους LIVE κανονες τους (UECL: φαβ ≥4% / dog ≥10% / Β dog ΧΩΡΙΣ FotMob ≥10% · UCL: φαβ ≥10% / dog ≥4%)
    + Europa για συγκριση — ανα κατηγορια & αγορα: ολα / κοβονται / μενουν.
 2) ΠΛΗΡΗ ΚΡΙΤΗΡΙΑ για Europa Β + Φ2 (τα picks που μενουν): Κ2 θετικο και στα 2 βιβλια + ≥3/4 σεζον + οι 2 νεας μορφης · Κ3 xG σε ισοπαλια
    καλυτερα απ οσο ελεγε η αγορα · Κ4 η αγορα κινειται προς τα picks ως το κλεισιμο.
Πρωτη εμφανιση ≤72ω (χωρις τελευταια τιμη), 1.70-2.10, Crown & SBOBET (καθε βιβλιο χωριστα).
"""
import sys
_fs = open('euro_fix_threshold_timing.py', encoding='utf-8').read().split("for cm in COMP_ONLY:")[0]
# ΧΩΡΙΣ απαιτηση Elo (το Elo δεν χρειαζεται εδω — αλλιως χανονται πολλες μικρες ομαδες του Conference)
_ELO_OLD = "if not c or not m or not lg or not np.isfinite(c['elh']) or not np.isfinite(c['ela']): continue"
_ELO_NEW = "if not c or not m or not lg: continue"
_fs = _fs.replace("exec(src)" + chr(10) + "NL = chr(10)",
                  "src = src.replace(_ELO_OLD, _ELO_NEW)" + chr(10) + "exec(src)" + chr(10) + "NL = chr(10)", 1)
exec(_fs)
NL = chr(10)
A['hasv'] = [str(MIDS[int(i)]) in TV for i in A.i]
VF = {}
for s in sorted(A.sea.unique()):
    tr = A[(A.sea != s) & A.hasv]; VF[s] = np.polyfit(tr.lv_.values, tr.gd.values.astype(float), 1)
RULES = {'EuropaLeague': (.04, .10), 'ConferenceLeague': (.04, .10), 'ChampionsLeague': (.10, .04)}
def picks_comp(cm):
    x = A[(A.comp == cm) & A.cat.isin(['A', 'B'])].reset_index(drop=True)
    th_f, th_d = RULES[cm]
    mk = []
    for r in x.itertuples():
        s = snapT(str(MIDS[int(r.i)]), 'Crown', 0) or snapT(str(MIDS[int(r.i)]), 'SBOBET', 0); mk.append(implied_margin(int(r.i), *s) if s else np.nan)
    mk = np.array(mk); ok = np.isfinite(x.lvl.values) & (x.lw.values > .2) & np.isfinite(mk)
    cal = np.polyfit(mk[ok], x.lvl.values[ok], 1, w=x.lw.values[ok])
    out = []
    for k_, r in x.iterrows():
        i = int(r.i); mid = str(MIDS[i]); D_ = sdist(r.lh, r.la)
        dis_h = np.nan
        if mid in TV: dis_h = VF[r['sea']][0] * r['lv_'] + VF[r['sea']][1] - (r['lh'] - r['la'])
        fmh = CP[mid].get('cat') if mid in CP else None
        for bk in ('Crown', 'SBOBET'):
            sc = snapT(mid, bk, 0); mcl = implied_margin(i, *sc) if sc else np.nan; got = set()
            for h_ in [hh for hh in HS if hh > 0]:
                s = snapT(mid, bk, h_)
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if side in got or not (1.70 <= o <= 2.10): continue
                    if ln <= -0.5: f = cover_q; th = th_f; kind = 'φαβ'
                    elif ln >= 0.5: f = picks.p_cover; th = th_d; kind = 'dog'
                    else: continue
                    if edge(*f(D_, side, ln), o) < th: continue
                    got.add(side); me = implied_margin(i, L, oh, oa)
                    src_side = (r.src_h if side == 1 else r.src_a) if hasattr(r, 'src_h') else None
                    out.append(dict(cat=r['cat'], sea=r['sea'], bk=bk, kind=kind, ven='εντος' if side == 1 else 'εκτος', pnl=picks.settle(GD[i], side, ln, o),
                                    dis=side * dis_h if np.isfinite(dis_h) else np.nan,
                                    lv=side * (r.lvl - (cal[0] * me + cal[1])) if ok[k_] else np.nan, lw=r.lw,
                                    clv=side * (mcl - me) if np.isfinite(mcl) else np.nan, i=i, side=side))
    return pd.DataFrame(out)
def cell(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean()
    return f'{n:3.0f} {100 * m.mean():+6.1f}% ({m.mean() * n:+5.1f}μ)'
# πλευρα ΧΩΡΙΣ FotMob (για τον κανονα Β του Conference)
SRC = {}
for m in __import__('json').load(open('euro_projections.json', encoding='utf-8'))['matches']: pass
import pickle as _p
_V6 = _p.load(open('euro_v6_preds.pkl', 'rb'))
for mm, sh, sa in zip(_V6['mids'], _V6['src_h'], _V6['src_a']): SRC[str(mm)] = (sh, sa)
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE'), ('ChampionsLeague', 'CHAMPIONS')):
    P = picks_comp(cm)
    P['nofm'] = [((SRC.get(str(MIDS[i]), ('', ''))[0] if s == 1 else SRC.get(str(MIDS[i]), ('', ''))[1]) != 'shots') for i, s in zip(P.i, P.side)]
    print(f'{NL}{"=" * 112}{NL}{lab} — Φ2 (μονο picks με γνωστη αξια) · κελι = picks ανα βιβλιο · ROI · μοναδες')
    print(f'   {"κατηγορια / αγορα":34s} │ {"ολα":>22s} │ {"ΚΟΒΟΝΤΑΙ":>22s} │ {"μενουν":>22s}')
    P = P[P.dis.notna()]
    groups = [('Α φαβορι εντος', (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εντος')), ('Α φαβορι εκτος', (P.cat == 'A') & (P.kind == 'φαβ') & (P.ven == 'εκτος')),
              ('Α αουτσαιντερ', (P.cat == 'A') & (P.kind == 'dog')), ('Β φαβορι', (P.cat == 'B') & (P.kind == 'φαβ')), ('Β αουτσαιντερ', (P.cat == 'B') & (P.kind == 'dog'))]
    if cm == 'ConferenceLeague': groups.append(('Β αουτσαιντερ ΧΩΡΙΣ FotMob (live κανονας)', (P.cat == 'B') & (P.kind == 'dog') & P.nofm))
    for nm, m_ in groups:
        y = P[m_]
        print(f'   {nm:34s} │ {cell(y):>22s} │ {cell(y[y.dis <= -.5]):>22s} │ {cell(y[y.dis > -.5]):>22s}')
    y = P[P.dis <= -.5]
    if len(y): print('   ΚΟΜΜΕΝΑ ανα σεζον (ολα): ' + ' '.join(f'{s[2:]}:{100 * v:+.0f}%' for s, v in y.groupby('sea').pnl.mean().items()))
    if cm == 'EuropaLeague':
        K = P[(P.cat == 'B') & (P.dis > -.5)]
        print(f'{NL}   ΠΛΗΡΗ ΚΡΙΤΗΡΙΑ — Europa Β + Φ2 (τα picks που μενουν)')
        for nm, m_ in (('ΟΛΑ', K.kind.notna()), ('φαβορι', K.kind == 'φαβ'), ('φαβορι εντος', (K.kind == 'φαβ') & (K.ven == 'εντος')), ('αουτσαιντερ', K.kind == 'dog')):
            y = K[m_]
            if len(y) < 6: continue
            mb = y.groupby('bk').pnl.mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
            k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
            yy = y.dropna(subset=['lv']); k3 = np.average(yy.lv, weights=yy.lw) if len(yy) else np.nan; k4 = y.clv.mean()
            print(f'      {nm:14s} {cell(y)} · Crown {100 * mb.get("Crown", np.nan):+.0f}% / SBOBET {100 * mb.get("SBOBET", np.nan):+.0f}% · σεζον ' +
                  ' '.join(f'{s[2:]}:{100 * v:+.0f}%({(y.sea == s).sum() // 2})' for s, v in ps.items()) +
                  f' · xG ισοπ. {k3:+.2f}/90 · CLV {k4:+.3f} │ Κ2 {"✓" if k2 else "✗"} Κ3 {"✓" if k3 > 0 else "✗"} Κ4 {"✓" if k4 > 0 else "✗"}')
