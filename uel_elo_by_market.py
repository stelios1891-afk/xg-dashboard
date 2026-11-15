"""uel_elo_by_market.py — 15/10/2026 (Στελιος: «στο europa δειξε μου το σημερινο και το μοντελο με μιξη Elo σε ολες τις αγορες ξεχωριστα»).
Europa League, κατηγορια Α, 4 σεζον, εκτος δειγματος (βαρος Elo απο τις αλλες 3 σεζον — ιδιο με euro_tophalf_elo_test).
Αγορες χαντικαπ (πρωτη εμφανιση ≤72ω χωρις τελευταια τιμη, 1.70-2.10, Crown & SBOBET):
  φαβορι εντος / εκτος (≤−0.5, ≥4%, σωστα τεταρτα) · αουτσαιντερ εντος / εκτος (≥+0.5, ≥10%, p_cover) · γραμμη 0 (DNB), −0.25, +0.25 (≥4%, σωστα τεταρτα)
Για καθε αγορα: picks · ROI εισοδου · ROI αν επαιζες το ιδιο στο κλεισιμο · ανα σεζον · xG σε ισοπαλια vs αγορα (/90) · κινηση αγορας μετα (CLV).
ΣΥΝΟΛΑ: η μιξη Elo αλλαζει ΜΟΝΟ τη διαφορα, οχι το συνολο γκολ → over/under ιδια με το σημερινο (δεν ξαναμετριουνται).
"""
import sys
src = open('euro_tophalf_elo_test.py', encoding='utf-8').read().split("for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE')):")[0]
exec(src)
x = A[A.comp == 'EuropaLeague'].reset_index(drop=True); seas = sorted(x.sea.unique())
LV = {}
for v, ue in (('M', False), ('E', True)):
    lh = np.zeros(len(x)); la = np.zeros(len(x))
    for s in seas:
        te = (x.sea == s).values; p = fit(x[~te], False, ue); a, b = lam(x[te], *p, False); lh[te] = a; la[te] = b
    LV[v] = (lh, la)
lv_ok = np.isfinite(x.lvl.values) & (x.lw.values > 0.2)
mk_all = np.array([implied_margin(int(r.i), *(sn(int(r.i), 'Crown', 0) or sn(int(r.i), 'SBOBET', 0))) if (sn(int(r.i), 'Crown', 0) or sn(int(r.i), 'SBOBET', 0)) else np.nan for r in x.itertuples()])
okc = lv_ok & np.isfinite(mk_all); cal = np.polyfit(mk_all[okc], x.lvl.values[okc], 1, w=x.lw.values[okc])
MK = (('φαβορι ΕΝΤΟΣ', lambda ln, side: ln <= -0.5 and side == 1, .04, 'q'), ('φαβορι ΕΚΤΟΣ', lambda ln, side: ln <= -0.5 and side == -1, .04, 'q'),
      ('αουτσαιντερ ΕΝΤΟΣ', lambda ln, side: ln >= 0.5 and side == 1, .10, 'p'), ('αουτσαιντερ ΕΚΤΟΣ', lambda ln, side: ln >= 0.5 and side == -1, .10, 'p'),
      ('γραμμη 0 (DNB)', lambda ln, side: ln == 0, .04, 'q'), ('γραμμη −0.25', lambda ln, side: ln == -0.25, .04, 'q'), ('γραμμη +0.25', lambda ln, side: ln == 0.25, .04, 'q'))
xa_ = x[x.cat == 'A']
def picks_for(v):
    P = []
    for k_ in xa_.index:
        r = x.loc[k_]; i = int(r.i); D_ = sdist(LV[v][0][k_], LV[v][1][k_])
        for bk in ('Crown', 'SBOBET'):
            sc = sn(i, bk, 0); mcl = implied_margin(i, *sc) if sc else np.nan
            for mname, cond, th, how in MK:
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
                        pc = np.nan
                        if sc:
                            Lc, ohc, oac = sc; pc = picks.settle(GD[i], side, Lc if side == 1 else -Lc, ohc if side == 1 else oac)
                        P.append(dict(m=mname, sea=r.sea, bk=bk, pnl=picks.settle(GD[i], side, ln, o), pc=pc,
                                      lv=side * (r.lvl - (cal[0] * me + cal[1])) if lv_ok[k_] else np.nan, lw=r.lw,
                                      clv=side * (mcl - me) if np.isfinite(mcl) else np.nan))
    return pd.DataFrame(P)
PK = {v: picks_for(v) for v in ('M', 'E')}
def line(y):
    if len(y) < 6: return f'{len(y) / 2:4.0f} picks (λιγα)'
    mb = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
    yy = y.dropna(subset=['lv']); lv = np.average(yy.lv, weights=yy.lw) if len(yy) else np.nan
    return (f'{n:4.0f} picks {100 * mb.mean():+6.1f}% · κλεισ {100 * y.pc.mean():+6.1f}% (' + ' '.join(f'{q[2:]} {100 * w_:+.0f}' for q, w_ in ps.items()) +
            f') · xG ισοπ. {lv:+.2f}/90 · CLV {y.clv.mean():+.3f} │ Κ2 {"✓" if k2 else "✗"} Κ3 {"✓" if lv > 0 else "✗"} Κ4 {"✓" if y.clv.mean() > 0 else "✗"}')
print(f'EUROPA LEAGUE κατηγορια Α ({len(xa_)} ματς, 4 σεζον, εκτος δειγματος) — ΣΗΜΕΡΙΝΟ vs ΜΙΞΗ Elo, ανα αγορα')
for mname, *_ in MK:
    print(f'\n  {mname}')
    for v, nm in (('M', 'σημερινο'), ('E', 'μιξη Elo')):
        print(f'     {nm:9s} {line(PK[v][PK[v].m == mname])}')
