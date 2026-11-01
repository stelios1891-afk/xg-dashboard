"""euro_tophalf_elo_test.py — 15/10/2026 (Στελιος: «οκ κανε και τα 2»: (1) picks με μιξη Elo · (2) εγχωρια δυναμη μονο απο ματς κοντρα στο ΠΑΝΩ ΜΙΣΟ).
(2) ΜΗΧΑΝΙΣΜΟΣ «ΠΑΝΩ ΜΙΣΟ» — ΧΩΡΙΣ ΚΑΜΙΑ ΡΥΘΜΙΣΗ: για καθε ομαδα εκτος top-5, απο την ΠΡΟΗΓΟΥΜΕΝΗ ολοκληρωμενη εγχωρια σεζον (κανενα μελλοντικο ματς):
      r_ολα  = ln(xG υπερ / xG κατα) σε ΟΛΑ τα ματς · r_πανω = το ιδιο ΜΟΝΟ κοντρα στο πανω μισο της βαθμολογιας (≥4 ματς)
      διορθωση c = (r_πανω − r_ολα) − μεσος ορος της λιγκας (ετσι ο μεσος της λιγκας μενει ιδιος· αλλαζει μονο το απλωμα)
      νεα προβλεψη: log λ_γηπ += (c_γηπ − c_φιλ)/2, log λ_φιλ −= (c_γηπ − c_φιλ)/2   (ιδια κλιμακα με τη δυναμη t του μοντελου, συντελεστης 1)
    λιγκες μονο-γκολ: με γκολ · ημερολογιακες λιγκες (Σουηδια/Νορβηγια) & χωρις προηγουμενη σεζον: c = 0.
(1) ΜΙΞΗ Elo: διαφορα = (1−w)·μοντελο + w·(h + k·ΔElo/100) — h, k, w απο τις αλλες 3 σεζον (οπως euro_elo_blend_test).
ΕΚΔΟΧΕΣ: Μ σημερινο · Ε μιξη Elo · Τ πανω-μισο · ΤΕ πανω-μισο + μιξη Elo. Europa (κυριο) + Conference.
ΚΡΙΤΗΡΙΑ (προ-δηλωμενα): Κ1 ακριβεια (Δlog-lik γκολ > 0 σε ≥3/4 σεζον ΚΑΙ RPS καλυτερο) · picks κατηγοριας Α (φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10%
p_cover ≥+0.5 · 1.70-2.10 · πρωτη εμφανιση ≤72ω χωρις τελευταια τιμη · Crown & SBOBET): Κ2 θετικα 2 βιβλια + ≥3/4 σεζον + οι 2 νεας μορφης ·
Κ3 xG ΣΕ ΙΣΟΠΑΛΙΑ (χωρις game state) καλυτερο απ' οσο ελεγε η αγορα στην εισοδο · Κ4 η αγορα κινειται προς τα picks. + σκαλα κυριαρχιας. Διαγνωστικο.
"""
import sys, os, json, glob, pickle
NL = chr(10)
_TO2 = sys.stdout
src = open('uecl_full_review.py', encoding='utf-8').read().split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0]
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _TO2; sys.stdout.reconfigure(encoding='utf-8')
CP = pickle.load(open('euro_components.pkl', 'rb'))
LG = {str(m): (a, b) for m, a, b in zip(V6['mids'], V6['lg_h'], V6['lg_a'])}
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
CAL_LG = {'Allsvenskan', 'Eliteserien', 'FinlandVeikkausliiga', 'LatviaVirsliga'}
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
# ---------- (2) διορθωσεις πανω-μισου ανα (λιγκα, σεζον, ομαδα)
CORR = {}
def build_corr(lg, sea):
    key = (lg, sea)
    if key in CORR: return CORR[key]
    CORR[key] = {}
    p = f'data_{lg}_{sea}.json'
    if not os.path.exists(p): return CORR[key]
    d = json.load(open(p, encoding='utf-8'))
    pts = {}; M = []
    goal_only = not any(m.get('shots') for m in d.values())
    for m in d.values():
        if m.get('hs') is None or m.get('as') is None: continue
        h, a = int(m['home']['id']), int(m['away']['id'])
        if goal_only: xh, xa = float(m['hs']), float(m['as'])
        else:
            if not m.get('shots'): continue
            xh = sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == h)
            xa = sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == a)
        M.append((h, a, xh, xa))
        ph = 3 if m['hs'] > m['as'] else (1 if m['hs'] == m['as'] else 0); pa = 3 if ph == 0 else (1 if ph == 1 else 0)
        pts[h] = pts.get(h, 0) + ph; pts[a] = pts.get(a, 0) + pa
    if len(pts) < 6: return CORR[key]
    order = sorted(pts, key=lambda t: -pts[t]); top = set(order[:len(order) // 2])
    agg = {t: [0.0, 0.0, 0.0, 0.0, 0] for t in pts}
    for h, a, xh, xa in M:
        for t, o, f_, g_ in ((h, a, xh, xa), (a, h, xa, xh)):
            agg[t][0] += f_; agg[t][1] += g_
            if o in top and o != t: agg[t][2] += f_; agg[t][3] += g_; agg[t][4] += 1
    raw = {}
    for t, (fa, ga, ft, gt, n) in agg.items():
        if n >= 4 and min(fa, ga, ft, gt) > 0: raw[t] = np.log(ft / gt) - np.log(fa / ga)
    if not raw: return CORR[key]
    mu = np.mean(list(raw.values()))
    CORR[key] = {t: v - mu for t, v in raw.items()}
    return CORR[key]
def prev_sea(s): return f'{int(s[:2]) - 1:02d}{int(s[2:]) - 1:02d}'
def corr_of(tid, lg, sea):
    if lg in TOP5 or lg in CAL_LG: return 0.0, False
    c = build_corr(lg, prev_sea(sea)).get(int(tid))
    return (c, True) if c is not None else (0.0, False)
def level_xg(m):
    hid = int(m['home']['id']); sh = sorted([s for s in (m.get('shots') or []) if s.get('xg') is not None], key=lambda s: s.get('min') or 0)
    if not sh: return None
    gh = ga = 0; xh = xa = 0.0; lm = 0.0; last = 0; level = True
    for s in sh:
        t = min(s.get('min') or 0, 95)
        if level: lm += max(t - last, 0)
        last = t
        if gh == ga:
            if int(s['tid']) == hid: xh += s['xg']
            else: xa += s['xg']
        if s.get('goal'):
            if int(s['tid']) == hid: gh += 1
            else: ga += 1
        level = gh == ga
    if level: lm += max(93 - last, 0)
    return (xh - xa) * 90 / max(lm, 1.0), lm / 90
rows = []
for i in range(len(MIDS)):
    if COMP[i] not in ('EuropaLeague', 'ConferenceLeague') or LH_N[i] <= 0: continue
    mid = str(MIDS[i]); c = CP.get(mid); m = EUM.get(mid); lg = LG.get(mid)
    if not c or not m or not lg or not np.isfinite(c['elh']) or not np.isfinite(c['ela']): continue
    ch, okh = corr_of(m['home']['id'], lg[0], SEA[i]); ca, oka = corr_of(m['away']['id'], lg[1], SEA[i])
    lx = level_xg(m)
    rows.append(dict(i=i, comp=COMP[i], sea=SEA[i], cat=cat(i), lh=LH_N[i], la=LA_N[i], de=(c['elh'] - c['ela']) / 100, dc=ch - ca, okh=okh, oka=oka,
                     gh=GH[i], ga=GA[i], gd=GD[i], th=c['th'], ta=c['ta'], lgh=lg[0], lga=lg[1],
                     lvl=lx[0] if lx else np.nan, lw=lx[1] if lx else 0.0))
A = pd.DataFrame(rows)
nt = ((~A.lgh.isin(TOP5)).sum() + (~A.lga.isin(TOP5)).sum()); nc = (A.okh & ~A.lgh.isin(TOP5)).sum() + (A.oka & ~A.lga.isin(TOP5)).sum()
print(f'Δειγμα: {len(A)} ματς UEL/UECL με Elo · πλευρες εκτος top-5 με διορθωση «πανω μισο» {nc}/{nt} ({100 * nc / nt:.0f}%)')
cv = pd.concat([A.loc[~A.lgh.isin(TOP5) & A.okh, ['th']].assign(c=A.loc[~A.lgh.isin(TOP5) & A.okh].dc * 0 + [x for x in A.loc[~A.lgh.isin(TOP5) & A.okh].dc])]) if False else None
# μεγεθος της διορθωσης ανα επιπεδο κυριαρχιας
S_ = []
for r in A.itertuples():
    for t, lg, ok, c in ((r.th, r.lgh, r.okh, None), (r.ta, r.lga, r.oka, None)):
        pass
def lam(x, h, k, w, use_t):
    lh = x.lh.values.copy(); la = x.la.values.copy()
    if use_t:
        lh = lh * np.exp(x.dc.values / 2); la = la * np.exp(-x.dc.values / 2)
    if w > 0:
        T = lh + la; m = (1 - w) * (lh - la) + w * (h + k * x.de.values)
        lh = np.maximum((T + m) / 2, .05); la = np.maximum((T - m) / 2, .05)
    return lh, la
def ll(x, lh, la): return float(np.sum(x.gh.values * np.log(lh) - lh + x.ga.values * np.log(la) - la))
HG = np.round(np.arange(0.0, 0.61, 0.05), 2); KG = np.round(np.arange(0.0, 1.21, 0.05), 2); WG = np.round(np.arange(0.1, 1.01, 0.1), 2)
VERS = (('M', 'σημερινο', False, False), ('E', 'μιξη Elo', False, True), ('T', 'πανω-μισο', True, False), ('TE', 'πανω-μισο + Elo', True, True))
def fit(x, use_t, use_e):
    if not use_e: return (0, 0, 0)
    best, bp = -1e18, (0, 0, 0)
    for h in HG:
        for k in KG:
            for w in WG:
                v = ll(x, *lam(x, h, k, w, use_t))
                if v > best: best, bp = v, (h, k, w)
    return bp
def rps(lh, la, gd):
    o = []
    for a, b, g in zip(lh, la, gd):
        D = sdist(a, b); p1 = sum(p for kk, p in D.items() if kk > 0); px = D.get(0, 0)
        o.append(((p1 - (g > 0)) ** 2 + (p1 + px - (g >= 0)) ** 2) / 2)
    return np.array(o)
HSP = [h for h in HS if h > 0]
SN = {}
def sn(i, bk, h):
    k = (i, bk, h)
    if k not in SN: SN[k] = snap_ah(MIDS[i], bk, h)
    return SN[k]
for cm, lab in (('EuropaLeague', 'EUROPA'), ('ConferenceLeague', 'CONFERENCE')):
    x = A[A.comp == cm].reset_index(drop=True); seas = sorted(x.sea.unique())
    LV = {}; PAR = {}
    for v, nm, ut, ue in VERS:
        lh = np.zeros(len(x)); la = np.zeros(len(x)); PAR[v] = {}
        for s in seas:
            te = (x.sea == s).values; p = fit(x[~te], ut, ue); PAR[v][s] = p
            a, b = lam(x[te], *p, ut); lh[te] = a; la[te] = b
        LV[v] = (lh, la)
    print(f'{NL}=================== {lab}: {len(x)} ματς ===================')
    print('   βαρος Elo w (αλλες 3 σεζον): Ε ' + ' '.join(f'{s[2:]}:{PAR["E"][s][2]:.1f}' for s in seas) + ' · ΤΕ ' + ' '.join(f'{s[2:]}:{PAR["TE"][s][2]:.1f}' for s in seas))
    R = {v: rps(*LV[v], x.gd.values) for v, *_ in VERS}
    print('   Κ1 ΑΚΡΙΒΕΙΑ (ολες οι κατηγοριες) + ΣΚΑΛΑ ΚΥΡΙΑΡΧΙΑΣ (λαθος ομαδων εκτος top-5: λιγο κυριαρχες t<0.3 / πολυ κυριαρχες t≥0.9)')
    for v, nm, ut, ue in VERS:
        d = {s: ll(x[x.sea == s], LV[v][0][(x.sea == s).values], LV[v][1][(x.sea == s).values]) -
                ll(x[x.sea == s], LV['M'][0][(x.sea == s).values], LV['M'][1][(x.sea == s).values]) for s in seas}
        npos = sum(t > 0 for t in d.values()); k1 = v != 'M' and npos >= 3 and R[v].mean() < R['M'].mean()
        sd = []
        for k_, r in x.iterrows():
            mm = LV[v][0][k_] - LV[v][1][k_]
            for sg, t, lg in ((1, r.th, r.lgh), (-1, r.ta, r.lga)):
                if lg not in TOP5: sd.append((t, sg * (r.gd - mm)))
        S = pd.DataFrame(sd, columns=['t', 'e'])
        print(f'      {nm:16s} RPS {R[v].mean():.4f} · Δlog-lik ' + ' '.join(f'{s[2:]}:{t:+.1f}' for s, t in d.items()) +
              (f' · Κ1 {"✓" if k1 else "✗"}' if v != 'M' else '      ') + f' │ σκαλα {S[S.t < .3].e.mean():+.2f} / {S[S.t >= .9].e.mean():+.2f}')
    # ---------- picks (κατηγορια Α)
    xa_ = x[x.cat == 'A']
    lv_ok = np.isfinite(x.lvl.values) & (x.lw.values > 0.2)
    mk_all = []
    for k_, r in x.iterrows():
        s = sn(r.i, 'Crown', 0) or sn(r.i, 'SBOBET', 0); mk_all.append(implied_margin(r.i, *s) if s else np.nan)
    mk_all = np.array(mk_all); okc = lv_ok & np.isfinite(mk_all)
    cal = np.polyfit(mk_all[okc], x.lvl.values[okc], 1, w=x.lw.values[okc])       # xG ισοπαλιας/90 ≈ cal0·αγορα + cal1
    print(f'   PICKS κατηγοριας Α ({len(xa_)} ματς) · Κ3: xG ισοπαλιας/90 ≈ {cal[0]:.2f}×διαφορα αγορας {cal[1]:+.2f} → μετραμε αν τα picks το ξεπερασαν')
    for v, nm, ut, ue in VERS:
        P = []
        for k_ in xa_.index:
            r = x.loc[k_]; i = int(r.i); D_ = sdist(LV[v][0][k_], LV[v][1][k_])
            for bk in ('Crown', 'SBOBET'):
                sc = sn(i, bk, 0); mcl = implied_margin(i, *sc) if sc else np.nan; got = set()
                for h in HSP:
                    s = sn(i, bk, h)
                    if not s: continue
                    L, oh, oa = s
                    for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                        if side in got or not (1.70 <= o <= 2.10): continue
                        if ln <= -0.5: f = cover_q; th = .04; kind = 'φαβ'
                        elif ln >= 0.5: f = picks.p_cover; th = .10; kind = 'dog'
                        else: continue
                        if edge(*f(D_, side, ln), o) < th: continue
                        got.add(side); me = implied_margin(i, L, oh, oa)
                        lvx = side * (r.lvl - (cal[0] * me + cal[1])) if lv_ok[k_] else np.nan
                        P.append(dict(sea=r.sea, bk=bk, kind=kind, home=side == 1, pnl=picks.settle(GD[i], side, ln, o), lv=lvx, lw=r.lw,
                                      clv=side * (mcl - me) if np.isfinite(mcl) else np.nan))
        P = pd.DataFrame(P)
        for lab2, m_ in (('ΟΛΑ', None), ('φαβ εντος', ('φαβ', True)), ('φαβ εκτος', ('φαβ', False)), ('dogs', ('dog', None))):
            y = P
            if m_ is not None and len(y):
                y = y[y.kind == m_[0]]
                if m_[1] is not None: y = y[y.home == m_[1]]
            if len(y) < 6: print(f'      {nm:16s} {lab2:9s} n{len(y) / 2:3.0f} (λιγα)'); continue
            mb = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); ps = y.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
            k2 = bool((mb > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
            yy = y.dropna(subset=['lv']); k3v = np.average(yy.lv, weights=yy.lw) if len(yy) else np.nan; k4v = y.clv.mean()
            ok_ = k2 and k3v > 0 and k4v > 0
            print(f'      {nm:16s} {lab2:9s} {n:4.0f} picks {100 * mb.mean():+6.1f}% (' + ' '.join(f'{q[2:]} {100 * w_:+.0f}' for q, w_ in ps.items()) +
                  f') · xG ισοπ. vs αγορα {k3v:+.2f}/90 · CLV {k4v:+.3f} │ Κ2 {"✓" if k2 else "✗"} Κ3 {"✓" if k3v > 0 else "✗"} Κ4 {"✓" if k4v > 0 else "✗"}'
                  + ('  ← ΠΕΡΝΑ' if ok_ and v != 'M' else ''))
