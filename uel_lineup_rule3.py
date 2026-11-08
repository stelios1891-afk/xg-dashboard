"""uel_lineup_rule3.py — 14/10/2026 (Στελιος: «γιατι λειπουν ενδεκαδες; αν δεν τις εχουμε κατεβασει, κατεβασε τις · πινακας με τι ελεγε το
μοντελο διπλα στην αγορα, το αποτελεσμα και το ποσοστο ενδεκαδας · στα τυφλα με καλη ενδεκαδα, τι γινεται με το over;»).
ΑΙΤΙΑ ΕΛΛΕΙΨΗΣ: οι ενδεκαδες υπαρχουν σχεδον ολες (euro_squads/core7_squads: βασικοι 26.905/26.908) — ελειπε η ΕΤΟΙΜΗ συνολικη αξια του FotMob
(totalStarterMarketValue) στο 60%. ΕΔΩ: αξια ενδεκαδας = αθροισμα αξιων των 11 βασικων ΣΤΗΝ ΗΜΕΡΟΜΗΝΙΑ του ματς απο το ιστορικο αξιων καθε
παικτη (euro_player_values + core7_player_values, καλυψη ~95%· αν λειπουν 1-2 παικτες, αναγωγη σε 11· <9 γνωστοι → αγνωστη). ΙΔΙΟΣ τροπος για
ευρωπαικα και εγχωρια → συνεπης συγκριση. Ποσοστο = ευρωπαικη ενδεκαδα / διαμεσος 5 τελευταιων εγχωριων (≤45 μερες, ≥3).
  1) ΚΑΝΟΝΑΣ (εκδοχη Α, τυφλα): φαβορι αγορας ≤−0.25, 1.70-2.10, ενδεκαδα ≥ τ, τιμη 1ω πριν · ΧΩΡΙΣ τα ματς του live «φαβορι εντος 12-36ω»
     · Europa (κυριο) + Conference (επαναληψη) · LOSO τ · Κ1-Κ3 (ιδια με uel_lineup_rule2) · + αξια με βαση τα xG
  2) ΠΙΝΑΚΑΣ ανα pick (Europa): ενδεκαδα · αγορα (γραμμη/τιμη 1ω, διαφορα που δικαιολογει) · ΜΟΝΤΕΛΟ (διαφορα, edge στη γραμμη) · σκορ · xG · pnl
     → uel_lineup_rule3_picks.csv
  3) OVER στα ιδια ματς (κυρια γραμμη συνολων 1ω πριν) · και ανα ενδεκαδα
"""
import sys, glob, bisect, datetime as _dt
src = open('uel_lineup_rule2.py', encoding='utf-8').read().split('# ---------- φαβορι αγορας με την τιμη 1ω')[0]
exec(src)
# ---------- αξια ενδεκαδας απο ιστορικο αξιων ----------
PV = {}
for f in ('euro_player_values.json', 'core7_player_values.json'):
    for pid, v in json.load(open(f, encoding='utf-8')).items():
        h = v.get('hist') or []
        if h: PV[int(pid)] = ([pd.Timestamp(d) for d, _ in h], [float(x) for _, x in h])
def val_at(pid, t):
    h = PV.get(int(pid))
    if not h: return None
    k = bisect.bisect_right(h[0], t) - 1
    return h[1][max(k, 0)]
def xi_value(x, t):
    st = (x or {}).get('st') or []
    vs = [val_at(p, t) for p in st]; vs = [v for v in vs if v is not None]
    if len(st) < 10 or len(vs) < 9: return None
    return sum(vs) * 11.0 / len(vs)
DOMV = {}
for mid, v in SQ.items():
    t = DATE.get(mid)
    if t is None: continue
    for k in ('h', 'a'):
        x = v.get(k) or {}
        if x.get('t'):
            xv = xi_value(x, t)
            if xv: DOMV.setdefault(int(x['t']), []).append((t, xv))
for k in DOMV: DOMV[k].sort(key=lambda z: z[0])
def ratio2(mid, side, ko):
    x = (SQ.get(str(mid)) or {}).get(side) or {}
    if not x.get('t'): return np.nan, 'λειπει ευρωπαικη ενδεκαδα'
    ev = xi_value(x, ko)
    if not ev: return np.nan, 'αγνωστες αξιες παικτων'
    prev = [z for z in DOMV.get(int(x['t']), []) if ko - pd.Timedelta(days=45) <= z[0] < ko - pd.Timedelta(hours=12)][-5:]
    if len(prev) < 3: return np.nan, f'<3 εγχωρια ({len(prev)})'
    return ev / np.median([z[1] for z in prev]), 'OK'
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
def xgs(mid):
    m = EUM.get(str(mid))
    if not m or not m.get('shots'): return np.nan, np.nan
    h, a = int(m['home']['id']), int(m['away']['id'])
    f = lambda tt: sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == tt)
    return f(h), f(a)
import collections
cov = collections.Counter(); rows = []; ou_rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('EuropaLeague', 'ConferenceLeague'): continue
    j = VI.get(str(MIDS[i]))
    if j is None: continue
    ko = pd.Timestamp(V6['date'][j])
    (rh, wh), (ra, wa) = ratio2(MIDS[i], 'h', ko), ratio2(MIDS[i], 'a', ko)
    if COMP[i] == 'EuropaLeague': cov[wh] += 1; cov[wa] += 1
    xh, xa = xgs(MIDS[i])
    for bk in ('Crown', 'SBOBET'):
        s1 = snap_ah(MIDS[i], bk, 1)
        if not s1: continue
        L, oh, oa = s1
        if abs(L) < 0.2: continue
        side = 1 if L < 0 else -1; ln = L if side == 1 else -L; o = oh if side == 1 else oa
        if not (1.70 <= o <= 2.10): continue
        r = rh if side == 1 else ra
        if not np.isfinite(r): continue
        if side == 1 and (i, bk) in HF: continue
        km = side * implied_margin(i, L, oh, oa) if LH_N[i] > 0 else np.nan
        mm = side * (LH_N[i] - LA_N[i]) if LH_N[i] > 0 else np.nan
        me = edge(*cover_q(sdist(LH_N[i], LA_N[i]), side, ln), o) if (LH_N[i] > 0 and SRCC[i] == 'FF') else np.nan
        # «αξια xG»: τιμη που δικαιολογουν τα ΤΕΛΙΚΑ xG
        xv = np.nan
        if np.isfinite(xh):
            d_ = picks.gd_dist(max(xh, .05), max(xa, .05)); pw, pp = picks.p_cover(d_, side, ln); xv = o / ((1 - pp) / max(pw, 1e-9)) - 1
        mid_ = str(MIDS[i]); m_ = EUM.get(mid_, {})
        rows.append(dict(comp=COMP[i], sea=SEA[i], bk=bk, mid=mid_, home=m_.get('home', {}).get('name'), away=m_.get('away', {}).get('name'),
                         fav=(m_.get('home', {}).get('name') if side == 1 else m_.get('away', {}).get('name')), side=side, ratio=r,
                         line=ln, odds=o, mkt=km, mdl=mm, medge=me, src=SRCC[i], gh=GH[i], ga=GA[i], xh=xh, xa=xa, xv=xv,
                         pnl=picks.settle(GD[i], side, ln, o)))
        so = snap_ou(MIDS[i], bk, 1)
        if so:
            Lt, ov, un = so
            po_, pu_ = ES.p_over(ES.tot_dist(OH[i], OA[i], DRAW_SCALE), Lt) if OH[i] > 0 else (np.nan, np.nan)
            ou_rows.append(dict(comp=COMP[i], sea=SEA[i], bk=bk, ratio=r, Lt=Lt, ov=ov, un=un, mt=mtot(Lt, ov, un), mod_t=OH[i] + OA[i], tg=GH[i] + GA[i],
                                xg_t=(xh + xa) if np.isfinite(xh) else np.nan,
                                over=settle(GH[i] + GA[i], Lt, ov, True) if 1.70 <= ov <= 2.10 else np.nan,
                                under=settle(GH[i] + GA[i], Lt, un, False) if 1.70 <= un <= 2.10 else np.nan,
                                eo=(po_ * (ov - 1) * (1 - picks.MARGIN) - pu_) if np.isfinite(po_) else np.nan))
B = pd.DataFrame(rows); OU = pd.DataFrame(ou_rows)
tot = sum(cov.values())
print('ΚΑΛΥΨΗ ΕΝΔΕΚΑΔΑΣ (Europa, ομαδες-ματς) με αξιες απο ιστορικο παικτων: ' + ' · '.join(f'{k} {v} ({100 * v / tot:.0f}%)' for k, v in cov.most_common()) +
      '   [πριν: OK 39%]')
def cc(x, col='pnl'):
    x = x.dropna(subset=[col])
    if len(x) < 6: return f'n{len(x) / 2:3.0f} (λιγα)'
    m = x.groupby('bk')[col].mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea')[col].mean()
    return f'{n:4.0f} picks {100 * m.mean():+6.1f}% [C {100 * m.get("Crown", np.nan):+.0f}/S {100 * m.get("SBOBET", np.nan):+.0f}] (' + ' '.join(f'{s[2:]} {100 * v:+.0f}' for s, v in ps.items()) + ')'
TAUS = (0.90, 0.93, 0.95, 0.97, 1.00)
for cm, lab in (('EuropaLeague', 'EUROPA LEAGUE (κυριο)'), ('ConferenceLeague', 'CONFERENCE (επαναληψη)')):
    U = B[B.comp == cm]
    print(NL + f'===== 1. {lab} — φαβορι αγορας, τιμη 1ω, ΧΩΡΙΣ τα «φαβορι εντος 12-36ω» · ROI | αξια με βαση τα τελικα xG')
    for tau in TAUS:
        x = U[U.ratio >= tau]; print(f'   ενδεκαδα ≥{tau:.2f}   {cc(x)} | xG {100 * x.xv.mean():+.1f}%')
    for lo, hi, l in ((0, .85, '<0.85'), (.85, .90, '0.85-0.90'), (.90, 1.0, '0.90-1.00')):
        x = U[(U.ratio >= lo) & (U.ratio < hi)]; print(f'   ενδεκαδα {l:9s} {cc(x)} | xG {100 * x.xv.mean():+.1f}%')
    print(f'   ολα τα φαβορι    {cc(U)} | xG {100 * U.xv.mean():+.1f}%')
    if cm == 'EuropaLeague':
        outs = []
        for hold in SEAS:
            tr = U[U.sea != hold]; sc = {t: tr[tr.ratio >= t].groupby('bk').pnl.mean().mean() for t in TAUS}
            t = max(sc, key=lambda k: sc[k]); outs.append((hold, t, U[(U.sea == hold) & (U.ratio >= t)]))
        X = pd.concat([o[2] for o in outs]); m = X.groupby('bk').pnl.mean(); ps = X.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
        k1 = m.mean() > 0 and bool((m > 0).all()); k2 = (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
        k3 = U[U.ratio < .9].groupby('bk').pnl.mean().mean() < X.groupby('bk').pnl.mean().mean()
        print(f'   LOSO: ' + ' '.join(f'{h[2:]}:τ={t:.2f}' for h, t, _ in outs) + f' → εκτος δειγματος {cc(X)} · Κ1 {"✓" if k1 else "✗"} Κ2 {"✓" if k2 else "✗"} Κ3 {"✓" if k3 else "✗"}')
        TAU = max(set(t for _, t, _ in outs), key=lambda t: sum(1 for _, tt, _ in outs if tt == t))
# ---------- 2. πινακας ----------
U = B[(B.comp == 'EuropaLeague') & (B.ratio >= TAU) & (B.bk == 'Crown')].copy()
U = U.sort_values(['sea', 'mid'])
U.to_csv('uel_lineup_rule3_picks.csv', index=False, encoding='utf-8-sig')
print(NL + f'===== 2. EUROPA, ενδεκαδα ≥{TAU:.2f} (Crown) — ΤΙ ΕΛΕΓΕ ΤΟ ΜΟΝΤΕΛΟ (διαφορα απο τη σκοπια του φαβορι)')
v = U.dropna(subset=['mdl'])
print(f'   {len(U)} picks · με προβλεψη μοντελου {len(v)} · αγορα {v.mkt.mean():+.2f} · ΜΟΝΤΕΛΟ {v.mdl.mean():+.2f} · πραγματικο {(v.side * (v.gh - v.ga)).mean():+.2f} · '
      f'xG {(v.side * (v.xh - v.xa)).mean():+.2f}')
w = v.dropna(subset=['medge'])
for lab, m_ in (('το μοντελο ΣΥΜΦΩΝΟΥΣΕ (edge ≥ 0)', w.medge >= 0), ('το μοντελο ΔΙΑΦΩΝΟΥΣΕ (edge < 0)', w.medge < 0), ('το μοντελο εδινε pick (edge ≥ 4%)', w.medge >= .04)):
    y = w[m_]; print(f'   {lab:38s} n{len(y):3d} · ROI {100 * y.pnl.mean():+6.1f}% · αγορα {y.mkt.mean():+.2f} · μοντελο {y.mdl.mean():+.2f} · πραγμ {(y.side * (y.gh - y.ga)).mean():+.2f}')
print(f'   {"ματς":44s} {"ενδεκ.":>6s} {"γραμμη":>7s} {"τιμη":>5s} {"αγορα":>6s} {"μοντ.":>6s} {"edge μ.":>7s} {"σκορ":>6s} {"xG":>9s} {"pnl":>6s}')
for r in U.itertuples():
    me = f'{100 * r.medge:+5.0f}%' if np.isfinite(r.medge) else '   —  '
    md = f'{r.mdl:+6.2f}' if np.isfinite(r.mdl) else '    — '
    xg = f'{r.xh:.1f}-{r.xa:.1f}' if np.isfinite(r.xh) else '—'
    print(f'   {r.sea} {(r.home or "")[:19]:19s}-{(r.away or "")[:19]:19s} {100 * r.ratio:5.0f}% {-r.line:+7.2f} {r.odds:5.2f} {r.mkt:+6.2f} {md} {me:>7s} {int(r.gh)}-{int(r.ga):<4d} {xg:>9s} {r.pnl:+6.2f}  [{r.fav}]')
# ---------- 3. over ----------
print(NL + '===== 3. OVER / UNDER στα ιδια ματς (κυρια γραμμη συνολων 1ω πριν, 1.70-2.10)')
for cm in ('EuropaLeague', 'ConferenceLeague'):
    O = OU[OU.comp == cm]
    print(f'   {cm}:')
    for lab, m_ in ((f'φαβορι με ενδεκαδα ≥{TAU:.2f}', O.ratio >= TAU), ('φαβορι με rotation <0.90', O.ratio < .90), ('ολα (με γνωστη ενδεκαδα)', O.ratio.notna())):
        x = O[m_]
        print(f'      {lab:28s} OVER {cc(x, "over")} · UNDER {cc(x, "under")}')
        print(f'      {"":28s} γκολ: πραγμ {x.tg.mean():.2f} · xG {x.xg_t.mean():.2f} · αγορα {x.mt.mean():.2f} · μοντελο {x.mod_t.mean():.2f}')
    x = O[(O.ratio >= TAU) & (O.eo >= 0)]
    print(f'      ενδεκαδα ≥{TAU:.2f} ΚΑΙ μοντελο βλεπει over (edge ≥0): OVER {cc(x, "over")}')
