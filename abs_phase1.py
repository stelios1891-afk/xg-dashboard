# -*- coding: utf-8 -*-
"""abs_phase1.py — ΦΑΣΗ 1 του εργου απουσιων (20/10/2026): ποιο ΜΕΤΡΟ της απωλειας πριν το ματς εξηγει (α) το λαθος του μοντελου μας και
(β) το λαθος της ΑΓΟΡΑΣ σε διαφορες στιγμες (ανοιγμα → 48ω → 24ω → 3ω → κλεισιμο) — δηλ. ποτε η αγορα «χωνευει» τις απουσιες
(ερωτημα Στελιου: Σιτι-ΑΕΚ, η τιμη κουνηθηκε οταν βγηκε ο Σεμενιο εκτος).
ΔΕΔΟΜΕΝΑ: core7_goals_gap_rows.csv (ματς CORE7 2223-2526 αγων. 7+, live μηχανη xh/xa, κλεισιμο Pinnacle s_mkt / T_mkt) + abs_sides.csv (Φαση 0) +
  nowgoal_odds (Crown, χαντικαπ & συνολα με χρονοσφραγιδα). Μονο ματς οπου ΚΑΙ οι 2 ομαδες εχουν λιστα Sofascore.
ΜΕΤΡΑ απωλειας (γηπεδουχος − φιλοξενουμενος, μονο πληροφορια πριν το ματς):
  dV = ln(αξια διαθεσιμης 11αδας / πληρους) · dA = Δ μεσης ικανοτητας 11αδας · θεσεις: επιθεση+μεσοι (γκολ που βαζει) / αμυνα+τερματοφυλακας (που τρωει)
ΚΡΙΤΗΡΙΑ (γραφτηκαν ΠΡΙΝ): Κ1 κλιση υπολοιπου μοντελου πανω στο μετρο θετικη σε ≥3/4 σεζον και συνολικα t≥2 · Κ2 LOSO (συντελεστης απο 3 σεζον →
  4η): μικροτερο τετραγωνικο λαθος σε ≥3/4 σεζον · για την αγορα: ιδια κλιση στο ανοιγμα και στο κλεισιμο (περιγραφικο) + κινηση s_κλεισ − s_ανοιγ."""
import sys, json, glob, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'mid': str, 'season': str})
A = pd.read_csv('abs_sides.csv', dtype={'mid': str, 'sea': str})
A['dV'] = np.log(A.V_avail / A.V_full); A['dA'] = A.A_avail - A.A_full
A['dVa'] = np.log(A.V_act / A.V_full); A['dAa'] = A.A_act - A.A_full
A['att'] = A.dA_att + A.dA_mid; A['dfn'] = A.dA_def + A.dA_gk
A['dVf'] = np.log(A.V_avail / A.V_fullr); A['dAf'] = A.A_avail - A.A_fullr     # ΜΟΝΟ οι νεες απουσιες (επαιζαν στα 2 τελευταια)
H = A[A.side == 'h'].set_index('mid'); Aw = A[A.side == 'a'].set_index('mid')
cols = ['dV', 'dA', 'dVa', 'dAa', 'dVf', 'dAf', 'att', 'dfn', 'sofa_list', 'n_miss_reg', 'n_fresh']
D = W.join(H[cols].add_suffix('_h'), on='mid').join(Aw[cols].add_suffix('_a'), on='mid')
D = D[D.sofa_list_h.fillna(False).astype(bool) & D.sofa_list_a.fillna(False).astype(bool)].copy()
D = D[D.dV_h.notna() & D.dV_a.notna()].copy()
D['dV'] = D.dV_h - D.dV_a; D['dA'] = D.dA_h - D.dA_a; D['dVf'] = D.dVf_h - D.dVf_a; D['dAf'] = D.dAf_h - D.dAf_a; D['dVa'] = D.dVa_h - D.dVa_a; D['dAa'] = D.dAa_h - D.dAa_a
D['tg'] = D.hg + D.ag
# ---------- χρονικη σειρα Crown (χαντικαπ + συνολα) ----------
KO = {}
for f in glob.glob('data_*_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for k, v in d.items():
        try: KO[str(k)] = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=dt.timezone.utc).timestamp()
        except Exception: pass
def pl(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]; return sum(p) / len(p)
    except Exception: return None
AH, OU = {}, {}
mids = set(D.mid)
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') != 3 or str(r.get('mid')) not in mids: continue
        for key, store in (('ah', AH), ('ou', OU)):
            rows = []
            for row in r.get(key) or []:
                try: t, a, g, b = row; L = pl(g); a, b = float(a) + 1, float(b) + 1
                except Exception: continue
                if L is None or t is None: continue
                rows.append((t, L, a, b))
            if rows: rows.sort(); store[str(r['mid'])] = rows
IDX = np.add.outer(np.arange(13), np.arange(13))
def sup_from_ah(L_home, oh, oa, T):
    """υπεροχη s που δικαιολογει χαντικαπ γηπεδουχου L_home (αρνητικο = δινει) στο συνολο T."""
    q = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -4.0, 4.0
    for _ in range(28):
        s = (lo + hi) / 2; d = picks.gd_dist(max((T + s) / 2, .05), max((T - s) / 2, .05))
        pw, pp = picks.p_cover(d, 1, L_home); pl_ = 1 - pw - pp
        if pw / max(pw + pl_, 1e-9) < q: lo = s
        else: hi = s
    return (lo + hi) / 2
def at(seq, t):
    prev = [x for x in seq if x[0] <= t]
    return prev[-1] if prev else None
# προσημο γραμμης Nowgoal: ελεγχος με το κλεισιμο Pinnacle (W.L = γραμμη γηπεδουχου)
chk = []
for r in D.itertuples():
    s = AH.get(r.mid); ko = KO.get(r.mid)
    if s and ko:
        c = at(s, ko)
        if c: chk.append((c[1], r.L))
chk = np.array(chk); SIGN = -1 if np.corrcoef(chk[:, 0], chk[:, 1])[0, 1] < 0 else 1
print(f'προσημο Nowgoal: {SIGN:+d} (συσχ. με Pinnacle {abs(np.corrcoef(chk[:, 0], chk[:, 1])[0, 1]):.2f}, n {len(chk)})')
TP = [('ανοιγμα', None), ('48ω', 48), ('24ω', 24), ('3ω', 3), ('κλεισιμο', 0)]
for lab, h in TP:
    ss = []
    for r in D.itertuples():
        s = AH.get(r.mid); ko = KO.get(r.mid)
        if not s or not ko: ss.append(np.nan); continue
        p = s[0] if h is None else at(s, ko - h * 3600)
        if p is None or (h is not None and h > 0 and p[0] > ko - h * 3600): ss.append(np.nan); continue
        o = OU.get(r.mid); po = (o[0] if h is None else at(o, ko - h * 3600)) if o else None
        T = (po[1] if po else r.T_mkt)
        ss.append(sup_from_ah(SIGN * p[1], p[2], p[3], T))
    D[f's_{lab}'] = ss
D['res_mod'] = D.gd - (D.xh - D.xa)
SE = sorted(D.season.unique())
def fit(x, y):
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    if len(x) < 30: return np.nan, np.nan, len(x)
    xc = x - x.mean(); b = (xc * (y - y.mean())).sum() / (xc ** 2).sum()
    res = y - y.mean() - b * xc; se = np.sqrt((res ** 2).sum() / (len(x) - 2) / (xc ** 2).sum())
    return b, b / se, len(x)
print(f'{NL}ματς με λιστα και στις 2 ομαδες: {len(D)} · ανα σεζον ' + ' · '.join(f'{s}: {(D.season == s).sum()}' for s in SE))
print(f'κατανομη dV (γηπ−φιλ): sd {D.dV.std():.3f} · 5% {D.dV.quantile(.05):+.3f} · 95% {D.dV.quantile(.95):+.3f} · |dV|>0.15: {(D.dV.abs() > .15).mean():.1%}')
print(f'{NL}{"=" * 118}{NL}Α. ΛΑΘΟΣ ΤΟΥ ΜΟΝΤΕΛΟΥ (πραγματικη διαφορα − μοντελο) πανω στο μετρο απωλειας — κλιση = γκολ ανα μοναδα')
print(f'   {"μετρο":32s} │ {"ολα: κλιση":>11s} {"t":>5s} │ ' + ' │ '.join(f'{s:>12s}' for s in SE) + ' │ LOSO λαθος (−= καλυτερα)')
for nm, col in (('αξια πριν (dV)', 'dV'), ('ικανοτητα πριν (dA)', 'dA'), ('αξια ΝΕΩΝ απουσιων (dVf)', 'dVf'), ('ικανοτητα ΝΕΩΝ (dAf)', 'dAf'), ('αξια πραγματικης 11αδας', 'dVa'), ('ικανοτητα πραγματικης', 'dAa')):
    b, t, n = fit(D[col].values, D.res_mod.values)
    per = [fit(D[D.season == s][col].values, D[D.season == s].res_mod.values) for s in SE]
    loso = []
    for s in SE:
        tr, te = D[D.season != s], D[D.season == s]
        bb, _, _ = fit(tr[col].values, tr.res_mod.values)
        x = te[col].fillna(0).values; y = te.res_mod.values
        loso.append(np.mean((y - bb * x) ** 2) - np.mean(y ** 2))
    print(f'   {nm:32s} │ {b:+11.2f} {t:5.1f} │ ' + ' │ '.join(f'{p[0]:+6.2f} t{p[1]:4.1f}' for p in per)
          + ' │ ' + ' '.join(f'{1000 * v:+.1f}' for v in loso) + f' ({sum(v < 0 for v in loso)}/4)')
print(f'{NL}{"=" * 118}{NL}Β. ΛΑΘΟΣ ΤΗΣ ΑΓΟΡΑΣ (Crown) ΣΕ ΚΑΘΕ ΣΤΙΓΜΗ πανω στην απωλεια ΠΡΙΝ (dV) — αν η κλιση πεφτει στο 0 ως το κλεισιμο, η αγορα «χωνευει» τις απουσιες')
for lab, h in TP:
    col = f's_{lab}'; y = (D.gd - D[col]).values
    b, t, n = fit(D.dV.values, y); per = [fit(D[D.season == s].dV.values, (D[D.season == s].gd - D[D.season == s][col]).values) for s in SE]
    bA, tA, _ = fit(D.dA.values, y)
    print(f'   {lab:10s} n {n:5d} │ dV κλιση {b:+.2f} t {t:4.1f} │ ' + ' │ '.join(f'{p[0]:+5.2f}' for p in per) + f' │ dA κλιση {bA:+.2f} t {tA:4.1f}')
for lab, h in TP:
    col = f's_{lab}'; y = (D.gd - D[col]).values; b, t, n = fit(D.dVf.values, y)
    print(f'   ΝΕΕΣ απουσιες {lab:10s} │ dVf κλιση {b:+.2f} t {t:4.1f} │ ' + ' │ '.join(f'{fit(D[D.season == s].dVf.values, (D[D.season == s].gd - D[D.season == s][col]).values)[0]:+5.2f}' for s in SE))
mv = (D.s_κλεισιμο - D.s_ανοιγμα).values
print(f'   ΚΙΝΗΣΗ αγορας πανω στις ΝΕΕΣ (dVf): κλιση {fit(D.dVf.values, mv)[0]:+.2f} t {fit(D.dVf.values, mv)[1]:.1f}')
b, t, n = fit(D.dV.values, mv)
print(f'   ΚΙΝΗΣΗ αγορας ανοιγμα→κλεισιμο πανω στο dV: κλιση {b:+.2f} t {t:.1f} (n {n}) · και η αυξηση της απωλειας ως την επισημη (dVa−dV): {fit((D.dVa - D.dV).values, mv)[0]:+.2f} t {fit((D.dVa - D.dV).values, mv)[1]:.1f}')
for lab, lo, hi in (('μεγαλη απωλεια γηπ. (dV ≤ −0.15)', -9, -.15), ('ουδετερο', -.05, .05), ('μεγαλη απωλεια φιλοξ. (dV ≥ +0.15)', .15, 9)):
    q = D[(D.dV > lo) & (D.dV <= hi)] if lo > -9 else D[D.dV <= hi]
    print(f'   {lab:36s} n {len(q):4d} · μοντελο−πραγμ {(-(q.res_mod)).mean():+.2f} · ανοιγμα−πραγμ {(q.s_ανοιγμα - q.gd).mean():+.2f} · 24ω {(q["s_24ω"] - q.gd).mean():+.2f} · κλεισιμο {(q.s_κλεισιμο - q.gd).mean():+.2f} · κινηση {(q.s_κλεισιμο - q.s_ανοιγμα).mean():+.2f}')
D.to_csv('abs_phase1_rows.csv', index=False)
