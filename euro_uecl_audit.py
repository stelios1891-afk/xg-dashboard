# -*- coding: utf-8 -*-
"""euro_uecl_audit.py — 5/11/2026 (Στελιος: «στο conference αναλυση ολου του μηχανισμου και των αποτελεσματων του, πιθανες αδυναμιες και βελτιωσεις»). Καθαρη μηχανη (euro_clean_rules: 90′, emps, Μ8 στο χαντικαπ).
1. ΠΡΟΒΛΕΨΗ vs αγορα (Α/Β): γκολ, RPS, πληροφορια περα απο αγορα, εδρα, ισοπαλιες, συνολα. 2. ΚΑΘΕ ΚΑΝΟΝΑΣ ανα εδρα/φαση/αγωνιστικη/εισοδο/γραμμη/τιμη/edge/λιγκα + αν περιμενα το κλεισιμο + γκολ vs xG vs αγορα.
3. ΙΔΙΟ ΜΑΤΣ: διπλα picks. 4. ΠΗΓΗ LIVE στις 9 λιγκες (γκολ+Elo). 5. ΦΕΤΙΝΑ picks (ημερολογιο). 6. ΒΕΛΤΙΩΣΕΙΣ, ΜΙΑ ΠΑΡΑΜΕΤΡΟΣ η καθε μια, LOSO: συμπιεση υπεροχης c · αγκυρα στην αγορα λ (χαντικαπ και συνολα) · σταθερος χρονος εισοδου.
ΚΡΙΤΗΡΙΑ ΒΕΛΤΙΩΣΗΣ (γραφτηκαν πριν): LOSO εκτος δειγματος μοναδες > σημερα, θετικα 2 βιβλια, ≥3/4 σεζον, και οι 2 σεζον νεας μορφης θετικες. Οι κοψιες του 2 ειναι ΠΕΡΙΓΡΑΦΙΚΕΣ: υποψηφιες, οχι ευρηματα."""
import sys, json, glob, os, pickle, math
_src = open('euro_clean_rules.py', encoding='utf-8').read()
exec(_src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')])
LGH = np.array([_V['lg_h'][_VI[m]] if m in _VI else '?' for m in MIDS]); LGA = np.array([_V['lg_a'][_VI[m]] if m in _VI else '?' for m in MIDS])
PHASE = np.array([_V['phase'][_VI[m]] if m in _VI else '?' for m in MIDS])
RND = np.array([str(_V['round'][_VI[m]]) if m in _VI and 'round' in _V else '?' for m in MIDS])
TOP5 = ('EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1')
UI = COMP == 'ConferenceLeague'; KN = SH != '?'
CA = UI & FMH & FMA; CB = UI & (FMH != FMA) & KN
INS = P6['INS']; XD = np.array([(XG[m][0] - XG[m][1]) if m in XG else np.nan for m in MIDS]); XT = np.array([(XG[m][0] + XG[m][1]) if m in XG else np.nan for m in MIDS])
NM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): NM[str(k)] = (m['home']['name'], m['away']['name'], m.get('hs'), m.get('as'))
def mk_sup(i):
    v = [fair(*snap(MIDS[i], bk, 0)) for bk in ('Crown', 'SBOBET') if snap(MIDS[i], bk, 0)]
    return float(np.mean(v)) if v else np.nan
def mk_tot(i):
    v = [mtot(*snap_ou(MIDS[i], bk, 0)) for bk in ('Crown', 'SBOBET') if snap_ou(MIDS[i], bk, 0)]
    return float(np.mean(v)) if v else np.nan
IDX = np.where(UI)[0]
KS = {i: mk_sup(i) for i in IDX}; KT = {i: mk_tot(i) for i in IDX}
print('=' * 100 + '\n1. ΠΡΟΒΛΕΨΗ vs ΑΓΟΡΑ (κλεισιμο), Conference 2223-2526')
def probs(lh, la):
    D = sdist(lh, la); return sum(p for k, p in D.items() if k > 0), D.get(0, 0.)
def rps3(p1, px, gd):
    y1, yx = float(gd > 0), float(gd == 0); return ((p1 - y1) ** 2 + (p1 + px - y1 - yx) ** 2) / 2
def fc(mask, lab):
    I = [i for i in np.where(mask)[0] if np.isfinite(KS.get(i, np.nan))]
    if len(I) < 15: return
    m = np.array([INS[0][i] - INS[1][i] for i in I]); k = np.array([KS[i] for i in I]); g = GD[I]; x = XD[I]
    T = np.array([INS[0][i] + INS[1][i] for i in I])
    rm = np.mean([rps3(*probs(INS[0][i], INS[1][i]), GD[i]) for i in I])
    rk = np.mean([rps3(*probs(max((INS[0][i] + INS[1][i] + KS[i]) / 2, .05), max((INS[0][i] + INS[1][i] - KS[i]) / 2, .05)), GD[i]) for i in I])
    def ols2(y):
        ok = np.isfinite(y); X = np.c_[np.ones(ok.sum()), k[ok], (m - k)[ok]]; b = np.linalg.lstsq(X, y[ok], rcond=None)[0]; e = y[ok] - X @ b
        s = np.sqrt(np.diag(np.linalg.inv(X.T @ X)) * (e @ e) / (len(e) - 3)); return b[2], s[2], b[1]
    bg, sg, kg = ols2(g.astype(float)); bx, sx, kx = ols2(x)
    print(f"   {lab:26s} n{len(I):3d} · υπεροχη γηπ: πραγμ {g.mean():+.2f} xG {np.nanmean(x):+.2f} μοντ {m.mean():+.2f} αγορα {k.mean():+.2f} · |γκολ−μοντ| {np.abs(g - m).mean():.2f} vs αγορα {np.abs(g - k).mean():.2f} · RPS μοντ {rm:.4f} αγορα {rk:.4f} · (μοντ−αγορα) αξιζει: γκολ {bg:+.2f}±{sg:.2f} xG {bx:+.2f}±{sx:.2f} · κλιση αγορας {kg:.2f}")
for lab, m in (('Α ολα', CA), ('Β ολα', CB), ('Α νεα μορφη', CA & NEWb), ('Β νεα μορφη', CB & NEWb), ('Α league', CA & (PHASE == 'league')), ('Α KO', CA & (PHASE == 'KO')), ('Β league', CB & (PHASE == 'league')), ('Β KO', CB & (PHASE == 'KO'))): fc(m, lab)
print('   ΣΥΝΟΛΑ ΓΚΟΛ')
for lab, m, OH, OA in (('Α', CA, OH_N, OA_N), ('Β', CB, OH_N, OA_N)):
    I = [i for i in np.where(m)[0] if np.isfinite(KT.get(i, np.nan))]
    print(f"   {lab} n{len(I)} · πραγματικα {TOT90[I].mean():.2f}±{TOT90[I].std() / np.sqrt(len(I)):.2f} · xG {np.nanmean(XT[I]):.2f} · μοντελο {(OH[I] + OA[I]).mean():.2f} · αγορα {np.mean([KT[i] for i in I]):.2f} · ανα σεζον πραγμ−αγορα " + ' '.join(f"{s[2:]}:{np.mean([TOT90[i] - KT[i] for i in I if SEA[i] == s]):+.2f}" for s in SEAS))
print('   ΕΔΡΑ & ΙΣΟΠΑΛΙΕΣ (μοντελο με ×0.85 ισοπαλιες)')
for lab, m in (('Α', CA), ('Β', CB), ('ΟΛΟ UECL', UI & KN)):
    I = np.where(m)[0]; pr = [probs(INS[0][i], INS[1][i]) for i in I]
    print(f"   {lab:9s} n{len(I)} · γκολ γηπ−φιλ {GD[I].mean():+.2f}±{GD[I].std() / np.sqrt(len(I)):.2f} vs μοντελο {(INS[0][I] - INS[1][I]).mean():+.2f} · xG {np.nanmean(XD[I]):+.2f} · ισοπαλιες {100 * (GD[I] == 0).mean():.1f}% vs μοντελο {100 * np.mean([p[1] for p in pr]):.1f}% · νικες γηπ {100 * (GD[I] > 0).mean():.1f}% vs {100 * np.mean([p[0] for p in pr]):.1f}%")
# ------------------------------------------------- ροες κανονων
side_nf = lambda i: (1 if FMA[i] else -1)
PK = {'Α φαβορι ≥4%': (seq_ah(INS, GD, CA, 'fav', H_72), .04, 'ah'), 'Α αουτσαιντερ ≥10%': (seq_ah(INS, GD, CA, 'dog', H_72), .10, 'ah'), 'Β αουτσαιντερ χωρις FotMob ≥10%': (seq_ah(INS, GD, CB, 'dog', H_72, sidefn=side_nf), .10, 'ah'),
      'Α over ≥−2%': (seq_ou(OH_N, OA_N, TOT90, CA, True, H_72), -.02, 'ou'), 'Β under ≥14%': (seq_ou(OH_N, OA_N, TOT90, CB, False, H_72), .14, 'ou')}
def enrich(z, typ):
    z = z.copy(); ln = []; od = []; pc = []; own = []; home = []
    for r in z.itertuples():
        if typ == 'ah':
            L, oh, oa = snap(MIDS[r.i], r.bk, r.h); l_ = L if r.side == 1 else -L; o = oh if r.side == 1 else oa; c = snap(MIDS[r.i], r.bk, 0)
            p = picks.settle(float(GD[r.i]), r.side, c[0] if r.side == 1 else -c[0], c[1] if r.side == 1 else c[2]) if c else np.nan
            own.append(LGH[r.i] if r.side == 1 else LGA[r.i]); home.append(r.side == 1)
        else:
            over = r.side == 1; L, oo, un = snap_ou(MIDS[r.i], r.bk, r.h); l_ = L; o = oo if over else un; c = snap_ou(MIDS[r.i], r.bk, 0)
            p = settle_t(TOT90[r.i], c[0], c[1] if over else c[2], over) if c else np.nan
            own.append('-'); home.append(True)
        ln.append(l_); od.append(o); pc.append(p)
    return z.assign(ln=ln, od=od, pc=pc, own=own, home=home, ph=PHASE[z.i.values], rd=RND[z.i.values])
def sh(z):
    if not len(z): return '—'
    return f"{len(z) / 2:5.1f}p {100 * z.pnl.mean():+6.1f}% {units(z):+6.1f}μ │ " + ' '.join(f"{s[2:]}:{100 * z[z.sea == s].pnl.mean():+.0f}" for s in SEAS if (z.sea == s).any()) + f" │ C{100 * z[z.bk == 'Crown'].pnl.mean():+.0f} S{100 * z[z.bk == 'SBOBET'].pnl.mean():+.0f} │ CLV {z.clv.mean():+.3f}"
print('\n' + '=' * 100 + '\n2. ΚΑΘΕ ΚΑΝΟΝΑΣ (κοψιες = περιγραφικες)')
Z = {}
for name, (pack, thr, typ) in PK.items():
    z = enrich(at(pack, thr), typ); Z[name] = z
    print(f'\n--- {name}: {sh(z)}')
    print(f"    αν περιμενα το κλεισιμο: {100 * z.pc.mean():+.1f}% · νεα μορφη {sh(z[z.sea.isin(NEW)])}")
    if typ == 'ah':
        I = z.i.values; sg = z.side.values
        print(f"    μεσα: γραμμη {z.ln.mean():+.2f} τιμη {z.od.mean():.2f} · διαφορα υπερ μας: πραγμ {np.mean(sg * GD[I]):+.2f} xG {np.nanmean(sg * XD[I]):+.2f} μοντελο {np.mean(sg * (INS[0][I] - INS[1][I])):+.2f} αγορα κλεισ. {np.mean([s * KS[i] for s, i in zip(sg, I) if np.isfinite(KS[i])]):+.2f} · αξια xG {100 * z.xv.mean():+.1f}%")
        for lab, m in (('εντος', z.home), ('εκτος', ~z.home)): print(f'    {lab:18s} {sh(z[m])}')
    else:
        I = z.i.values; xv = []
        for r in z.itertuples():
            over = r.side == 1; x = XG.get(MIDS[r.i])
            if not x: xv.append(np.nan); continue
            po, pu = ES.p_over(ES.tot_dist(max(x[0], .05), max(x[1], .05), 1.0), r.ln); pw, pl = (po, pu) if over else (pu, po); xv.append(pw * (r.od - 1) - pl)
        z = z.assign(xv=xv); Z[name] = z
        print(f"    μεσα: γραμμη {z.ln.mean():.2f} τιμη {z.od.mean():.2f} · γκολ πραγμ {TOT90[I].mean():.2f} xG {np.nanmean(XT[I]):.2f} μοντελο {(OH_N[I] + OA_N[I]).mean():.2f} αγορα κλεισ. {np.nanmean([KT[i] for i in I]):.2f} · αξια xG {100 * np.nanmean(xv):+.1f}%")
    for lab, m in (('φαση league', z.ph == 'league'), ('φαση KO', z.ph == 'KO')): print(f'    {lab:18s} {sh(z[m])}')
    rr = pd.to_numeric(z.rd, errors='coerce')
    for lab, m in (('αγων. 1-2', (z.ph == 'league') & (rr <= 2)), ('αγων. 3-4', (z.ph == 'league') & (rr >= 3) & (rr <= 4)), ('αγων. 5+', (z.ph == 'league') & (rr >= 5))): print(f'    {lab:18s} {sh(z[m])}')
    for lab, a, b in (('εισοδος 72-48ω', 48, 72), ('εισοδος 36-18ω', 18, 36), ('εισοδος 12-4ω', 4, 12), ('εισοδος 2ω-κλεισ', 0, 2)): print(f'    {lab:18s} {sh(z[(z.h >= a) & (z.h <= b)])}')
    for lab, a, b in (('τιμη 1.70-1.84', 1.7, 1.84), ('τιμη 1.85-1.97', 1.85, 1.97), ('τιμη 1.98-2.10', 1.98, 2.11)): print(f'    {lab:18s} {sh(z[(z.od >= a) & (z.od <= b + .001)])}')
    for v, q in z.groupby(z.ln.abs().round(2) if typ == 'ah' else z.ln.round(2)):
        if len(q) >= 8: print(f'    γραμμη {v:<11} {sh(q)}')
    cuts = {.04: (.04, .10, .20, 9), .10: (.10, .20, .30, 9), -.02: (-.02, .04, .10, 9), .14: (.14, .20, .30, 9)}[thr]
    for a, b in zip(cuts[:-1], cuts[1:]): print(f'    edge {100 * a:.0f}-{100 * b:.0f}%{"":10s} {sh(z[(z.e >= a) & (z.e < b)])}')
    if typ == 'ah':
        for lab, m in (('ομαδα top-5', z.own.isin(TOP5)), ('ομαδα εκτος top-5', ~z.own.isin(TOP5))): print(f'    {lab:18s} {sh(z[m])}')
print('\n' + '=' * 100 + '\n3. ΙΔΙΟ ΜΑΤΣ: οταν βγαινουν 2 picks (χαντικαπ + συνολο) στο ιδιο βιβλιο')
ALL = pd.concat([z.assign(rule=k) for k, z in Z.items()])
pairs = []
for (i, bk), q in ALL.groupby(['i', 'bk']):
    if len(q) >= 2:
        a = q[q.rule.str.contains('φαβορι|αουτσαιντερ')]; b = q[q.rule.str.contains('over|under')]
        if len(a) and len(b): pairs.append(dict(i=i, bk=bk, sea=SEA[i], combo=a.rule.iloc[0][:14] + ' + ' + b.rule.iloc[0][:7], p1=a.pnl.iloc[0], p2=b.pnl.iloc[0]))
PP = pd.DataFrame(pairs)
if len(PP):
    print(f'   ζευγη {len(PP) / 2:.1f} · απο ολα τα ματς με pick {ALL.groupby(["i", "bk"]).ngroups / 2:.0f} · συσχετιση p1/p2 {np.corrcoef(PP.p1, PP.p2)[0, 1]:+.2f}')
    for c, q in PP.groupby('combo'): print(f"   {c:30s} {len(q) / 2:5.1f} ζευγη · χαντικαπ {100 * q.p1.mean():+.1f}% · συνολο {100 * q.p2.mean():+.1f}% · συσχ {np.corrcoef(q.p1, q.p2)[0, 1] if len(q) > 3 else np.nan:+.2f} · και τα 2 χαμενα {100 * ((q.p1 < 0) & (q.p2 < 0)).mean():.0f}% · και τα 2 κερδισμενα {100 * ((q.p1 > 0) & (q.p2 > 0)).mean():.0f}%")
print('\n' + '=' * 100 + '\n4. ΠΗΓΗ LIVE: κατηγορια Β με γκολ+Elo στις 9 λιγκες αντι Ben (χωρις Μ8)')
_e = pickle.load(open('euro_blend_dump_ben_elo.pkl', 'rb')); _ie = {str(m): k for k, m in enumerate(_e['MIDS'])}
ELO = (np.array([_e['LH'][_ie[m]] if m in _ie else np.nan for m in MIDS], float), np.array([_e['LA'][_ie[m]] if m in _ie else np.nan for m in MIDS], float))
_w = pickle.load(open('euro_v6w2_preds_pen76_elo.pkl', 'rb')); _iw = {str(m): k for k, m in enumerate(_w['mids'])}
OHE, OAE = pair_live((np.array([_w['lh'][_iw[m]] if m in _iw else np.nan for m in MIDS], float), np.array([_w['la'][_iw[m]] if m in _iw else np.nan for m in MIDS], float)))
okE = np.isfinite(ELO[0]) & np.isfinite(OHE)
print('   Β αουτσαιντερ ≥10%: ' + desc(at(seq_ah(ELO, GD, CB & okE, 'dog', H_72, sidefn=side_nf), .10)))
print('   Β under ≥14%:      ' + desc(at(seq_ou(OHE, OAE, TOT90, CB & okE, False, H_72), .14)))
print('\n' + '=' * 100 + '\n5. ΦΕΤΙΝΑ PICKS (ημερολογιο, στην τιμη και γραμμη καταγραφης)')
L = [json.loads(x) for x in open('euro_picks_ledger.jsonl', encoding='utf-8')]
EU = json.load(open('data_Europe_2627.json', encoding='utf-8')); rows = []
for r in L:
    if r.get('comp') != 'ConferenceLeague' or r.get('no_play'): continue
    m = EU.get(str(r['mid']))
    if not m or m.get('hs') is None: rows.append(dict(rule=r.get('rule') or r['role'], rnd=r.get('rnd'), done=False)); continue
    gd = m['hs'] - m['as']; tot = m['hs'] + m['as']
    if r['role'] in ('over', 'under'): p = settle_t(tot, r['line'], r['odds'], r['role'] == 'over')
    else: p = picks.settle(float(gd), r['side'], r['line'], r['odds'])
    rows.append(dict(rule=r.get('rule') or r['role'], rnd=r.get('rnd'), done=True, p=p, n=f"{m['home']['name'][:14]}-{m['away']['name'][:14]} {m['hs']}-{m['as']} {r.get('team') or r['role']} {r['line']} @{r['odds']} e{100 * r['edge']:.0f}%"))
Y = pd.DataFrame(rows); D_ = Y[Y.done == True]
print(f"   τελειωμενα {len(D_)} · ανοιχτα {(Y.done == False).sum()} · ΣΥΝΟΛΟ {D_.p.sum():+.2f}μ ({100 * D_.p.mean():+.1f}%)")
for k, q in D_.groupby('rule'): print(f'   {k:14s} {len(q):2d} picks {q.p.sum():+.2f}μ ({100 * q.p.mean():+.1f}%)')
for r in D_.itertuples(): print(f'      αγ.{r.rnd} {r.p:+.2f} {r.n}')
print('\n' + '=' * 100 + '\n6. ΒΕΛΤΙΩΣΕΙΣ (μια παραμετρος η καθε μια· ιδια κατωφλια)')
def seq_ah2(LL, mask, kind, hs, sidefn=None, c=1.0, lam=0.0):
    S = []
    for i in np.where(mask)[0]:
        mid = MIDS[i]
        for bk in ('Crown', 'SBOBET'):
            cl = snap(mid, bk, 0)
            for side in ((1, -1) if sidefn is None else (sidefn(i),)):
                q = []
                for h in hs:
                    s = snap(mid, bk, h)
                    if not s: continue
                    L, oh, oa = s; ln = L if side == 1 else -L; o = oh if side == 1 else oa
                    if not (1.70 <= o <= 2.10): continue
                    if kind == 'fav' and ln > -0.5: continue
                    if kind == 'dog' and ln < 0.5: continue
                    T = LL[0][i] + LL[1][i]; m = c * (LL[0][i] - LL[1][i])
                    if lam: m = (1 - lam) * m + lam * fair(L, oh, oa)
                    D = sdist(max((T + m) / 2, .05), max((T - m) / 2, .05)); pw, pp = picks.p_cover(D, side, ln) if kind == 'dog' else cover_q(D, side, ln)
                    q.append((h, edge(pw, pp, o), L, oh, oa, ln, o))
                if q: S.append(dict(i=i, bk=bk, side=side, q=q, cl=cl))
    def eval_(rec):
        i, side = rec['i'], rec['side']; cl = rec['cl']; h, e, L, oh, oa, ln, o = rec['hit']
        return dict(i=i, bk=rec['bk'], side=side, sea=SEA[i], h=h, e=e, pnl=picks.settle(float(GD[i]), side, ln, o), clv=side * (fair(cl[0], cl[1], cl[2]) - fair(L, oh, oa)) if cl else np.nan, xv=xg_value(i, side, ln, o))
    return S, eval_
def seq_ou2(mask, over, hs, lam=0.0):
    S = []; sg = 1 if over else -1
    for i in np.where(mask)[0]:
        mid = MIDS[i]
        for bk in ('Crown', 'SBOBET'):
            cl = snap_ou(mid, bk, 0); q = []
            for h in hs:
                s = snap_ou(mid, bk, h)
                if not s: continue
                L, oo, un = s; o = oo if over else un
                if not (1.70 <= o <= 2.10): continue
                T0 = OH_N[i] + OA_N[i]; m = OH_N[i] - OA_N[i]; T = (1 - lam) * T0 + lam * mtot(L, oo, un) if lam else T0
                po, pu = ES.p_over(ES.tot_dist(max((T + m) / 2, .05), max((T - m) / 2, .05), .85), L); pw, pp = (po, pu) if over else (pu, po)
                q.append((h, pw * (o - 1) * (1 - picks.MARGIN) - pp, L, oo, un, o))
            if q: S.append(dict(i=i, bk=bk, side=sg, q=q, cl=cl))
    def eval_(rec):
        i = rec['i']; cl = rec['cl']; h, e, L, oo, un, o = rec['hit']
        return dict(i=i, bk=rec['bk'], side=sg, sea=SEA[i], h=h, e=e, pnl=settle_t(TOT90[i], L, o, over), clv=sg * (mtot(cl[0], cl[1], cl[2]) - mtot(L, oo, un)) if cl else np.nan, xv=np.nan)
    return S, eval_
def verdict(z, base):
    ps = z.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]; bb = z.groupby('bk').pnl.mean()
    return units(z) > units(base) and bool((bb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
def ladder(lab, grid, builder):
    """builder(v) → λιστα (ονομα, ροη, κατωφλι)· LOSO: η τιμη με τις περισσοτερες μοναδες στις αλλες σεζον, ενωμενα ολα τα σκελη."""
    print(f'\n   {lab}')
    TT = {}
    for v in grid:
        parts = builder(v); zz = pd.concat([at(p, t).assign(rule=n) for n, p, t in parts]); TT[v] = zz
        print(f"      {v:<5} ΣΥΝΟΛΟ {sh(zz)}  ·  " + ' · '.join(f"{n[:10]} {len(q) / 2:.0f}p {100 * q.pnl.mean():+.1f}%" for n, q in zz.groupby('rule')))
    ch = {}; oo = []
    for s in SEAS:
        b = max(grid, key=lambda v: units(TT[v][TT[v].sea != s])); ch[s] = b; oo.append(TT[b][TT[b].sea == s])
    oo = pd.concat(oo); base = TT[grid[0]]
    print(f"      LOSO: " + ' '.join(f'{s[2:]}→{v}' for s, v in ch.items()) + f" · εκτος δειγματος {sh(oo)} vs σημερα {units(base):+.1f}μ → {'ΠΕΡΝΑ' if verdict(oo, base) else 'ΔΕΝ ΠΕΡΝΑ'}")
HAND = lambda c=1.0, lam=0.0: [('Α φαβ', seq_ah2(INS, CA, 'fav', H_72, c=c, lam=lam), .04), ('Α dog', seq_ah2(INS, CA, 'dog', H_72, c=c, lam=lam), .10), ('Β dog', seq_ah2(INS, CB, 'dog', H_72, side_nf, c=c, lam=lam), .10)]
ladder('Α. ΣΥΜΠΙΕΣΗ ΥΠΕΡΟΧΗΣ c (1 = σημερα): υπεροχη ×c, ιδιο συνολο γκολ — χαντικαπ', (1.0, .9, .8, .7, .6), lambda c: HAND(c=c))
for c in (.9, .8, .7, .6):
    I = np.where(UI & KN)[0]; d = []
    for i in I:
        T = INS[0][i] + INS[1][i]; m0 = INS[0][i] - INS[1][i]; m = c * m0
        d.append(rps3(*probs((T + m) / 2, (T - m) / 2), GD[i]) - rps3(*probs(INS[0][i], INS[1][i]), GD[i]))
    d = np.array(d); print(f"      RPS c={c}: {1000 * d.mean():+.2f}±{1000 * d.std() / np.sqrt(len(d)):.2f} ×10⁻³ · " + ' '.join(f"{s[2:]}:{1000 * d[SEA[I] == s].mean():+.2f}" for s in SEAS))
ladder('Β. ΑΓΚΥΡΑ ΣΤΗΝ ΑΓΟΡΑ λ (0 = σημερα): υπεροχη = (1−λ)·μοντελο + λ·γραμμη της στιγμης — χαντικαπ', (0.0, .2, .35, .5, .7), lambda l: HAND(lam=l))
ladder('Γ. ΑΓΚΥΡΑ ΣΥΝΟΛΩΝ λ (0 = σημερα): συνολο = (1−λ)·μοντελο + λ·γραμμη — over Α, under Β', (0.0, .2, .35, .5, .7), lambda l: [('Α over', seq_ou2(CA, True, H_72, l), -.02), ('Β under', seq_ou2(CB, False, H_72, l), .14)])
print('\n   Δ. ΣΤΑΘΕΡΟΣ ΧΡΟΝΟΣ ΕΙΣΟΔΟΥ (αντι πρωτης εμφανισης ≤72ω): ροη μονο στην ωρα αυτη')
for nm, (pack, thr, typ) in PK.items():
    base = at(pack, thr); c = [f"≤72ω {len(base) / 2:.0f}p {100 * base.pnl.mean():+.1f}% {units(base):+.1f}μ"]
    for hs in ((48,), (24,), (12,), (6,), (2,), (0,)):
        if typ == 'ah':
            kd = 'fav' if 'φαβορι' in nm else 'dog'; p = seq_ah(INS, GD, CA if nm.startswith('Α') else CB, kd, hs, sidefn=None if nm.startswith('Α') else side_nf)
        else:
            p = seq_ou(OH_N, OA_N, TOT90, CA if nm.startswith('Α') else CB, 'over' in nm, hs)
        y = at(p, thr); c.append(f"{hs[0]}ω {len(y) / 2:.0f}p {100 * y.pnl.mean():+.1f}% {units(y):+.1f}μ")
    print(f"      {nm[:22]:22s} " + ' · '.join(c))
print('\n' + '=' * 100 + '\n7. ΕΛΕΓΧΟΙ: τυφλα, επαναληψη σε αλλες διοργανωσεις, φινιρισμα')
print('   Α. ΤΥΦΛΑ (ιδια γραμμη/τιμη, πρωτη εμφανιση ≤72ω, ΧΩΡΙΣ κατωφλι edge) vs κανονας')
for nm, (pack, thr, typ) in PK.items():
    print(f'      {nm[:30]:30s} τυφλα {sh(at(pack, -9.0))}'); print(f'      {"":30s} κανονας {sh(at(pack, thr))}')
print('   Β. ΚΑΝΟΝΕΣ ΦΙΛΤΡΩΝ (LOSO: κραταω το φιλτρο στην κρυμμενη σεζον αν στις αλλες εδινε περισσοτερες μοναδες)')
def filt(name, z, keep):
    a = z[keep]; ok = []
    for s in SEAS:
        tr = z.sea != s; use = units(a[a.sea != s]) > units(z[tr]); ok.append((a if use else z)[(a if use else z).sea == s])
    oo = pd.concat(ok)
    print(f"      {name}: ολα {sh(z)}\n         με φιλτρο {sh(a)}\n         φευγουν {sh(z[~keep])}\n         LOSO {sh(oo)} → {'ΠΕΡΝΑ' if verdict(oo, z) else 'ΔΕΝ ΠΕΡΝΑ'}")
zf = Z['Α φαβορι ≥4%']; filt('Α φαβορι χωρις ομαδα top-5', zf, ~zf.own.isin(TOP5)); filt('Α φαβορι μονο φαση λιγκας', zf, zf.ph == 'league')
zd = Z['Α αουτσαιντερ ≥10%']; filt('Α αουτσαιντερ μονο φαση λιγκας', zd, zd.ph == 'league'); filt('Α αουτσαιντερ μονο εκτος εδρας', zd, ~zd.home)
print('   Γ. ΕΠΑΝΑΛΗΨΗ σε UEL/UCL (φαβορι Α ≥4%, 72ω, μιξη 60%, 4 σεζον)')
for cn, cm in (('UEL', (COMP == 'EuropaLeague') & FMH & FMA), ('UCL', (COMP == 'ChampionsLeague') & FMH & FMA), ('UECL', CA)):
    y = enrich(at(seq_ah(INS, GD, cm, 'fav', H_72), .04), 'ah')
    print(f'      {cn} ολα {sh(y)}\n         ομαδα top-5 {sh(y[y.own.isin(TOP5)])}\n         εκτος top-5 {sh(y[~y.own.isin(TOP5)])}\n         league {sh(y[y.ph == "league"])}\n         KO {sh(y[y.ph == "KO"])}')
print('   Δ. ΦΙΝΙΡΙΣΜΑ: γκολ vs xG ανα σεζον')
for nm in ('Β αουτσαιντερ χωρις FotMob ≥10%', 'Β under ≥14%', 'Α over ≥−2%'):
    z = Z[nm]; typ = PK[nm][2]; c = []
    for s in SEAS:
        q = z[z.sea == s]; I = q.i.values
        if typ == 'ah': c.append(f"{s[2:]}: γκολ {np.mean(q.side.values * GD[I]):+.2f} xG {np.nanmean(q.side.values * XD[I]):+.2f} αγορα {np.nanmean([sd * KS[i] for sd, i in zip(q.side.values, I)]):+.2f}")
        else: c.append(f"{s[2:]}: γκολ {TOT90[I].mean():.2f} xG {np.nanmean(XT[I]):.2f} αγορα {np.nanmean([KT[i] for i in I]):.2f}")
    print(f'      {nm[:30]:30s} ' + ' │ '.join(c))
I = np.where(CB)[0]; fg = []; fx = []; ng = []; nx = []
for i in I:
    x = XG.get(MIDS[i]); hs, as_ = R90[MIDS[i]]
    if not x: continue
    if FMH[i]: fg.append(hs); fx.append(x[0]); ng.append(as_); nx.append(x[1])
    else: fg.append(as_); fx.append(x[1]); ng.append(hs); nx.append(x[0])
print(f'      κατηγορια Β, ομαδα ΜΕ FotMob: γκολ {np.mean(fg):.2f} vs xG {np.mean(fx):.2f} ({np.mean(fg) - np.mean(fx):+.2f}) · ομαδα ΧΩΡΙΣ: γκολ {np.mean(ng):.2f} vs xG {np.mean(nx):.2f} ({np.mean(ng) - np.mean(nx):+.2f}) · n{len(fg)}')
