# -*- coding: utf-8 -*-
"""euro_elo_level.py — 5/11/2026 (Στελιος: «τρεξε και το τεστ με το ελο»). Το επιπεδο λιγκας s (χασμα στις ευρωπαικες προβλεψεις) απο ΜΙΞΗ αξιων παικτων και Elo: s = (1−w)·s_αξιες + w·s_elo, ΕΝΑΣ συντελεστης w για ολες τις λιγκες.
s_elo Α (ΤΙΜΙΟ): σημερινο μεσο Elo ΟΛΩΝ των ομαδων πρωτης κατηγοριας της χωρας + η μεση αλλαγη απο τις 15/8 της σεζον στις ομαδες με διαθεσιμο ιστορικο (euro_elo_hist_fetch· Νορβηγια 5/16 ομαδες) → ιδια κλιμακα με τις αξιες (γραμμικη προσαρμογη ανα σεζον). Μονο οι λιγκες με αξιες· οι αλλες μενουν ως εχουν.
s_elo Β (ΜΕ ΔΙΑΡΡΟΗ, μονο για εικονα): σημερινο μεσο Elo χωρας (clubelo_current). Το API ClubElo ανα ημερομηνια δινει 502.
Χρηση: python euro_elo_level.py table · python euro_elo_level.py dump <μιξη xG> <w> <A|B> · python euro_elo_level.py eval
ΚΡΙΤΗΡΙΑ (γραφτηκαν πριν): Κ1 RPS ολων των ευρωπαικων καλυτερο συνολικα ΚΑΙ ≥3/4 σεζον, με w απο LOSO · Κ2 μοναδες live κανονων χαντικαπ με το w του LOSO ≥ σημερα · Κ3 μικροτερη μεση απολυτη αποκλιση λιγκων (γκολ & xG − μοντελο, n≥25)."""
import sys, os, io, json, math, pickle, builtins, contextlib
import numpy as np, pandas as pd
MODE = sys.argv[1]
TBL = 'euro_lvl_elo.json'
if MODE == 'table':
    sys.stdout.reconfigure(encoding='utf-8')
    from euro_engine import GAMMA_PLAYER, player_offsets
    POFF = player_offsets()
    src = open('euro_inseason_eu_test.py', encoding='utf-8').read(); ns = {}
    exec(src[src.index('LG_COUNTRY = {'):src.index('# ================================================================ V0/V4/V5')], ns)
    H = json.load(open('clubelo_cache/level1_hist.json', encoding='utf-8')); OUT = {'A': {}, 'B': {}}
    _c = pd.read_csv('clubelo_current.csv'); EC0 = _c[_c.level == 1].groupby('country')['elo'].mean()
    def at_date(ser, d):
        prev = [v for t, v in ser if t <= d]
        return prev[-1] if prev else ser[0][1]
    for fold, d in (('2223', '2022-08-15'), ('2324', '2023-08-15'), ('2425', '2024-08-15'), ('2526', '2025-08-15'), ('2627', '2026-08-15')):
        lv = {}; nn = {}
        for lg, cc in ns['LG_COUNTRY'].items():
            if lg in POFF and cc in EC0.index:
                dr = [at_date(se, d) - se[-1][1] for se in H.get(cc, {}).values()]       # ποσο αλλαξαν απο τοτε οι ομαδες με ιστορικο (ιδια συνθεση, χωρις μεροληψια «μονο οι καλες»)
                lv[lg] = float(EC0[cc] + (np.mean(dr) if dr else 0.0)); nn[lg] = len(dr)
        ax = np.array([lv[lg] / 100 for lg in lv]); ay = np.array([POFF[lg] for lg in lv]); c1 = np.cov(ax, ay)[0, 1] / np.var(ax); c0 = ay.mean() - c1 * ax.mean()
        OUT['A'][fold] = {lg: float(-GAMMA_PLAYER * (c0 + c1 * v / 100)) for lg, v in lv.items()}
        print(f'{fold}: λιγκες {len(lv)} · κλιση {c1:+.3f} · r {np.corrcoef(ax, ay)[0, 1]:.2f}')
        for lg in ('Belgium', 'Eliteserien', 'DanishSuperLiga', 'Allsvenskan', 'SwissSuperleague', 'AustrianBundesliga', 'ScottishPrem', 'EPL'):
            if lg in lv: print(f"   {lg:22s} Elo {lv[lg]:.0f} (n{nn[lg]}) · s αξιες {-GAMMA_PLAYER * POFF[lg]:+.3f} · s Elo {OUT['A'][fold][lg]:+.3f}")
    cel = pd.read_csv('clubelo_current.csv'); EC = cel[cel.level == 1].groupby('country')['elo'].mean()
    an = [(EC[ns['LG_COUNTRY'][lg]], POFF[lg]) for lg in POFF if lg in ns['LG_COUNTRY'] and ns['LG_COUNTRY'][lg] in EC.index]
    ax = np.array([a[0] / 100 for a in an]); ay = np.array([a[1] for a in an]); c1 = np.cov(ax, ay)[0, 1] / np.var(ax); c0 = ay.mean() - c1 * ax.mean()
    b = {lg: float(-GAMMA_PLAYER * (c0 + c1 * EC[cc] / 100)) for lg, cc in ns['LG_COUNTRY'].items() if cc in EC.index}
    OUT['B'] = {f: b for f in ('2223', '2324', '2425', '2526')}
    json.dump(OUT, open(TBL, 'w', encoding='utf-8'), ensure_ascii=False, indent=0); print('ok')
elif MODE == 'dump':
    BL, W, VAR = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    import picks
    picks.BLEND = BL; picks._BLEND_D = (picks.BLEND_EARLY - BL) * (picks.BLEND_SPLIT + picks.BLEND_KG) / picks.BLEND_SPLIT
    _o = builtins.open; _SIO = io.StringIO
    s = _o('euro_inseason_eu_test.py', encoding='utf-8').read()
    a = '# ================================================================ arrays δειγματος'
    assert s.count(a) == 1
    PATCH = f"""_s_old = s_v4
_LV = json.load(builtins_open('{TBL}', encoding='utf-8'))['{VAR}']
def s_v4(lg, fold):
    o = _s_old(lg, fold); e = _LV.get(str(fold), {{}}).get(lg)
    return o if e is None else (1 - {W}) * o + {W} * e

"""
    PATCHED = s.replace(a, PATCH + a).replace("import json, glob, sys, pickle, math, time", "import json, glob, sys, pickle, math, time, builtins as _bi; builtins_open = _bi.open", 1)
    def op(f, *x, **k):
        if isinstance(f, str) and os.path.basename(f) == 'euro_inseason_eu_test.py': return _SIO(PATCHED)
        return _o(f, *x, **k)
    builtins.open = op
    class _Q(io.StringIO):
        def reconfigure(self, **k): pass
    io.StringIO = _Q
    g = {'__name__': 'lv'}
    with contextlib.redirect_stdout(_Q()):
        exec(_o('euro_adj_methods.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass', 1), g)
    INS = g['RES']['M8'][0][0.5][0]; BASE = g['BASE']; G = g['g']
    pickle.dump(dict(MIDS=[str(m) for m in G['MIDS']], BASE=(np.asarray(BASE[0]), np.asarray(BASE[1])), INS=(np.asarray(INS[0]), np.asarray(INS[1]))), _o(f'euro_lvl_{BL}_{W}_{VAR}.pkl', 'wb'))
    sys.__stdout__.write(f'ok {BL} {W} {VAR}\n')
else:
    _src = open('euro_clean_rules.py', encoding='utf-8').read()
    exec(_src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')])
    WS = (0.0, .25, .5, .75, 1.0)
    def load(bl, w, v='A'):
        if w == 0: return (P6 if bl == .6 else P8)['INS']
        P = pickle.load(open(f'euro_lvl_{bl}_{w}_{v}.pkl', 'rb')); assert P['MIDS'] == MIDS; return P['INS']
    E6 = {w: load(.6, w) for w in WS}; E8 = {w: load(.8, w) for w in WS}
    y1 = (GD > 0).astype(float); yx = (GD == 0).astype(float)
    def rps(L):
        out = np.zeros(len(MIDS))
        for i in range(len(MIDS)):
            D = sdist(L[0][i], L[1][i]); p1 = sum(p for k, p in D.items() if k > 0); px = D.get(0, 0.)
            out[i] = ((p1 - y1[i]) ** 2 + (p1 + px - y1[i] - yx[i]) ** 2) / 2
        return out
    R = {w: rps(E6[w]) for w in WS}
    print('\nΚ1. ΑΚΡΙΒΕΙΑ: αλλαγη RPS ×10⁻³ vs σημερα (μιξη 60%, ολα τα ευρωπαικα 2223-2526, αρνητικο = καλυτερο)')
    MS = {'ΟΛΑ': np.ones(len(MIDS), bool), 'UCL': COMP == 'ChampionsLeague', 'UEL': COMP == 'EuropaLeague', 'UECL': COMP == 'ConferenceLeague', 'FotMob+FotMob': FM}
    for w in WS[1:]:
        d = R[w] - R[0.0]
        print(f"   w={w:.2f}: " + ' · '.join(f"{k} {1000 * d[m].mean():+.2f}±{1000 * d[m].std() / np.sqrt(m.sum()):.2f}" for k, m in MS.items()) + ' │ σεζον ' + ' '.join(f"{s[2:]}:{1000 * d[SEA == s].mean():+.2f}" for s in SEAS))
    ch = {}
    oos = np.zeros(len(MIDS))
    for s in SEAS:
        tr = SEA != s; best = min(WS, key=lambda w: R[w][tr].mean()); ch[s] = best; oos[SEA == s] = R[best][SEA == s]
    d = oos - R[0.0]
    k1 = d.mean() < 0 and sum(d[SEA == s].mean() < 0 for s in SEAS) >= 3
    print(f"   LOSO: w " + ' '.join(f'{s[2:]}→{v:.2f}' for s, v in ch.items()) + f" · εκτος δειγματος {1000 * d.mean():+.2f}±{1000 * d.std() / np.sqrt(len(d)):.2f} · σεζον " + ' '.join(f"{s[2:]}:{1000 * d[SEA == s].mean():+.2f}" for s in SEAS) + f" → Κ1 {'✓' if k1 else '✗'}")
    for v, ww in (('B', (.5, 1.0)),):
        for w in ww:
            if os.path.exists(f'euro_lvl_.6_{w}_{v}.pkl') or os.path.exists(f'euro_lvl_0.6_{w}_{v}.pkl'):
                dd = rps(load(.6, w, v)) - R[0.0]; print(f"   Β (σημερινο Elo, ΔΙΑΡΡΟΗ) w={w:.2f}: {1000 * dd.mean():+.2f}±{1000 * dd.std() / np.sqrt(len(dd)):.2f} · σεζον " + ' '.join(f"{s[2:]}:{1000 * dd[SEA == s].mean():+.2f}" for s in SEAS))
    print('\nΚ2. ΚΑΝΟΝΕΣ LIVE ΧΑΝΤΙΚΑΠ (ROI, μοναδες· UCL = νεα μορφη) ανα w')
    side_nf = lambda i: (1 if FMA[i] else -1); home = lambda i: 1
    RULES = (('UCL φαβορι ≥4', 6, UCLA, 'fav', .04, H_UCL, True, None, True), ('UCL dog ≥10', 6, UCLA, 'dog', .10, H_UCL, True, None, True), ('UCL DNB ≥4', 6, UCLA, 'dnb', .04, H_UCL, True, None, True),
             ('UEL φαβ εντος ≥4', 8, UELA, 'fav', .04, H_UEL, False, home, False), ('UECL Α φαβ ≥4', 6, ECA, 'fav', .04, H_72, False, None, False), ('UECL Α dog ≥10', 6, ECA, 'dog', .10, H_72, False, None, False),
             ('UECL Β dog ≥10', 6, ECB, 'dog', .10, H_72, False, side_nf, False))
    TAB = {}
    for w in WS:
        for lab, bl, mk, kd, thr, hs, hon, sf, nw in RULES:
            z = at(seq_ah((E6 if bl == 6 else E8)[w], GD, mk, kd, hs, hon, sf), thr); z = z.assign(rule=lab, w=w)
            TAB[(w, lab)] = z[z.sea.isin(NEW)] if nw else z
    for lab, *_ in RULES:
        print(f'   {lab:18s} ' + ' · '.join(f"w{w:.2f} {len(TAB[(w, lab)]) / 2:.0f}p {100 * TAB[(w, lab)].pnl.mean():+.1f}% {units(TAB[(w, lab)]):+.1f}μ" for w in WS))
    tot = {w: sum(units(TAB[(w, lab)]) for lab, *_ in RULES) for w in WS}; npk = {w: sum(len(TAB[(w, lab)]) / 2 for lab, *_ in RULES) for w in WS}
    print('   ΣΥΝΟΛΟ             ' + ' · '.join(f"w{w:.2f} {npk[w]:.0f}p {tot[w]:+.1f}μ" for w in WS))
    lo = 0.0
    for s in SEAS:
        lo += sum(units(TAB[(ch[s], lab)][TAB[(ch[s], lab)].sea == s]) for lab, *_ in RULES)
    k2 = lo >= tot[0.0]
    print(f"   Με το w του LOSO (απο Κ1): {lo:+.1f}μ vs σημερα {tot[0.0]:+.1f}μ → Κ2 {'✓' if k2 else '✗'}")
    print('\nΚ3. ΑΠΟΚΛΙΣΕΙΣ ΛΙΓΚΩΝ (απο τη σκοπια της λιγκας, γκολ/ματς, ομαδα vs αλλη λιγκα)')
    LGH = np.array([_V['lg_h'][_VI[m]] if m in _VI else '?' for m in MIDS]); LGA = np.array([_V['lg_a'][_VI[m]] if m in _VI else '?' for m in MIDS])
    NMH = {}
    for f in glob.glob('data_Europe_*.json'):
        for k, m in json.load(open(f, encoding='utf-8')).items(): NMH[str(k)] = (m['home']['name'], m['away']['name'])
    KF = {}
    for i, mid in enumerate(MIDS):
        fr = [fair(*snap(mid, bk, 0)) for bk in ('Crown', 'SBOBET') if snap(mid, bk, 0)]
        KF[i] = np.mean(fr) if fr else np.nan
    XD = np.array([(XG[m][0] - XG[m][1]) if m in XG else np.nan for m in MIDS]); KK = np.array([KF[i] for i in range(len(MIDS))])
    ok = (LGH != '?') & (LGA != '?') & (LGH != LGA)
    def dev(L, lg, drop=()):
        m = L[0] - L[1]; ih = ok & (LGH == lg); ia = ok & (LGA == lg)
        if drop:
            ih = ih & np.array([NMH.get(x, ('', ''))[0] not in drop for x in MIDS]); ia = ia & np.array([NMH.get(x, ('', ''))[1] not in drop for x in MIDS])
        g_ = np.r_[(GD - m)[ih], -(GD - m)[ia]]; x_ = np.r_[(XD - m)[ih], -(XD - m)[ia]]; k_ = np.r_[(KK - m)[ih], -(KK - m)[ia]]
        return len(g_), g_, x_, k_
    for lab, lg, dr in (('Βελγιο', 'Belgium', ()), ('Νορβηγια χωρις Bodø', 'Eliteserien', ('Bodø/Glimt',)), ('Νορβηγια ολες', 'Eliteserien', ()), ('Δανια', 'DanishSuperLiga', ()), ('Σουηδια', 'Allsvenskan', ()), ('Ελβετια', 'SwissSuperleague', ()), ('Αυστρια', 'AustrianBundesliga', ()), ('Σκωτια', 'ScottishPrem', ()), ('EPL', 'EPL', ())):
        c = []
        for w in (0.0, .5, 1.0):
            n, g_, x_, k_ = dev(E6[w], lg, dr); c.append(f"w{w:.1f} γκολ {np.nanmean(g_):+.2f}±{np.nanstd(g_) / np.sqrt(n):.2f} xG {np.nanmean(x_):+.2f} αγορα {np.nanmean(k_):+.2f}")
        print(f'   {lab:20s} n{n:3d} ' + ' │ '.join(c))
    LS = [g for g in set(LGH[ok]) | set(LGA[ok]) if dev(E6[0.0], g)[0] >= 25]
    k3v = {}
    for w in WS:
        a_g, a_x, a_k, nn = 0, 0, 0, 0
        for g in LS:
            n, g_, x_, k_ = dev(E6[w], g); a_g += n * abs(np.nanmean(g_)); a_x += n * abs(np.nanmean(x_)); a_k += n * abs(np.nanmean(k_)); nn += n
        k3v[w] = (a_g / nn, a_x / nn, a_k / nn)
    print(f'   μεση |αποκλιση| {len(LS)} λιγκων: ' + ' · '.join(f"w{w:.2f} γκολ {v[0]:.3f} xG {v[1]:.3f} αγορα {v[2]:.3f}" for w, v in k3v.items()))
    wb = max(set(ch.values()), key=list(ch.values()).count)
    k3 = k3v[wb][0] < k3v[0.0][0] and k3v[wb][1] < k3v[0.0][1]
    print(f"   Κ3 (w {wb:.2f} vs σημερα): {'✓' if k3 else '✗'}")
    print('\nΣΗΜΕΡΑ: St.Truiden–Brann ανα w (s Elo 15/8/2026· οι υπολοιποι ορισμοι απο την προβλεψη 4/11)')
    L_ = json.load(open(TBL, encoding='utf-8'))['A']['2627']; Dv = .303; De = L_['Belgium'] - L_['Eliteserien']; print(f'   D αξιες {Dv:+.3f} · D Elo {De:+.3f}')
    for w in WS:
        D = (1 - w) * Dv + w * De; c = -.47 * D
        h = 1.784 * math.exp(D) * 1.1419 - c / 2; a = 1.643 * math.exp(-D) / 1.1419 + c / 2
        pw, pp = cover_q(sdist(h, a), 1, -.75); print(f'   w={w:.2f}: υπεροχη {h - a:+.2f} · edge St.Truiden −0.75 @1.91 {100 * edge(pw, pp, 1.91):+.1f}%')
    print(f"\nΚΡΙΣΗ: Κ1 {'✓' if k1 else '✗'} · Κ2 {'✓' if k2 else '✗'} · Κ3 {'✓' if k3 else '✗'}")
