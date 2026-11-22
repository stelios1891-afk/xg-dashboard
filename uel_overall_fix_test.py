"""uel_overall_fix_test.py — 14/10/2026 (Στελιος: «οκ τρεξτα ολα» — συνολικη βελτιωση Europa, οχι ανα ομαδα).
Europa League, κατηγορια Α (FotMob και οι 2), 4 σεζον 2223-2526, live harness λ (w=2, γ, ισοπαλιες ×0.85). ΤΕΣΣΕΡΙΣ ΕΚΔΟΧΕΣ:
  Α σημερινο
  Β + ΔΙΟΡΘΩΣΗ ΤΕΝΤΩΜΑΤΟΣ: λ_γηπ × exp(bt·Δt/2 + bD·D), λ_φιλ × exp(−bt·Δt/2 − bD·D) · Δt = δυναμη ομαδας γηπ − φιλ, D = διαφορα λιγκας
      (euro_components.pkl) · εδρα ΑΘΙΚΤΗ · bt, bD απο πλεγμα, μεγιστη πιθανοφανεια ΓΚΟΛ στις αλλες 3 σεζον
  Γ + ΑΓΚΥΡΑ ΣΤΟ ΑΝΟΙΓΜΑ: διαφορα = w·μοντελο + (1−w)·αγορα ανοιγματος (πρωτη τιμη ≤72ω, Crown αλλιως SBOBET), συνολο ιδιο · w απο τις αλλες 3 σεζον
  Δ Β + Γ (πρωτα διορθωση, μετα αγκυρα· bt,bD,w μαζι απο τις αλλες 3 σεζον)
Ολα ΕΚΤΟΣ ΔΕΙΓΜΑΤΟΣ (LOSO). Κοινο δειγμα: ματς με τιμη ανοιγματος και κομματια.
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (vs Α):
  Κ1 ακριβεια: Δlog-lik γκολ > 0 σε ≥3/4 σεζον ΚΑΙ RPS 1Χ2 συνολικα καλυτερο
  Κ2 picks (κανονες UEL: φαβ ≥4% σωστα τεταρτα ≤−0.5 · dog ≥10% p_cover ≥+0.5 · 1.70-2.10 · πρωτη εμφανιση ≤72ω χωρις τελευταια τιμη · Crown & SBOBET):
     θετικα και στα 2 βιβλια, ≥3/4 σεζον, και οι 2 σεζον νεας μορφης
  Κ3 ΑΞΙΑ ΜΕ ΒΑΣΗ ΤΑ ΤΕΛΙΚΑ xG των picks > 0
  Κ4 η αγορα κινειται ΠΡΟΣ τα picks μετα την εισοδο (μεση κινηση γραμμης ως το κλεισιμο > 0)
Διαγνωστικο — τιποτα live.
"""
import sys, os, json, glob, pickle, math
NL = chr(10)
_UO = sys.stdout
src = open('uecl_full_review.py', encoding='utf-8').read().replace("CMP = 'ConferenceLeague'", "CMP = 'EuropaLeague'").split('# ================= Α. ΒΑΘΜΟΝΟΜΗΣΗ')[0]
sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(src); sys.stdout = _UO; sys.stdout.reconfigure(encoding='utf-8')
COMPS = pickle.load(open('euro_components.pkl', 'rb'))
XG = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []
        if not sh: continue
        hid = int(m['home']['id'])
        XG[str(k)] = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid),
                      sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid))
HSP = [h for h in HS if h > 0]
SNAP = {}
def sn(i, bk, h):
    k = (i, bk, h)
    if k not in SNAP: SNAP[k] = snap_ah(MIDS[i], bk, h)
    return SNAP[k]
def opening(i, bk):
    for h in HSP:
        s = sn(i, bk, h)
        if s: return s
    return None
# ---------- δειγμα
rows = []
for i in UI:
    if cat(i) != 'A' or LH_N[i] <= 0: continue
    c = COMPS.get(str(MIDS[i]))
    if not c: continue
    so = opening(i, 'Crown') or opening(i, 'SBOBET')
    if not so: continue
    rows.append(dict(i=i, sea=SEA[i], dt=c['th'] - c['ta'], D=c['D'], mo=implied_margin(i, *so)))
S = pd.DataFrame(rows)
I = S.i.values; LH0 = LH_N[I]; LA0 = LA_N[I]; DT = S.dt.values; DD = S.D.values; MO = S.mo.values
YH = np.asarray(GH, float)[I]; YA = np.asarray(GA, float)[I]
print(f'Δειγμα: {len(S)} ματς Europa κατηγορια Α με τιμη ανοιγματος (ανα σεζον: ' + ' '.join(f'{s}:{n}' for s, n in S.sea.value_counts().sort_index().items()) + ')')
def lam(bt, bD, w, idx=slice(None)):
    lh = LH0[idx] * np.exp(bt * DT[idx] / 2 + bD * DD[idx]); la = LA0[idx] * np.exp(-bt * DT[idx] / 2 - bD * DD[idx])
    if w < 1:
        T = lh + la; m = w * (lh - la) + (1 - w) * MO[idx]
        lh = np.maximum((T + m) / 2, .05); la = np.maximum((T - m) / 2, .05)
    return lh, la
def ll(lh, la, idx):
    return float(np.sum(YH[idx] * np.log(lh) - lh + YA[idx] * np.log(la) - la))
BT = np.round(np.arange(-0.9, 0.31, 0.05), 2); BDg = np.round(np.arange(-0.9, 0.51, 0.05), 2); WG = np.round(np.arange(0.0, 1.01, 0.05), 2)
def fit(ver, idx):
    best, bp = -1e18, (0.0, 0.0, 1.0)
    bts = BT if ver in ('B', 'D') else [0.0]; bds = BDg if ver in ('B', 'D') else [0.0]; ws = WG if ver in ('C', 'D') else [1.0]
    for bt in bts:
        for bd in bds:
            for w in ws:
                v = ll(*lam(bt, bd, w, idx), idx)
                if v > best: best, bp = v, (bt, bd, w)
    return bp
SEAS_ = sorted(S.sea.unique())
PAR = {v: {} for v in 'ABCD'}
for v in 'ABCD':
    for s in SEAS_:
        tr = np.where(S.sea.values != s)[0]; PAR[v][s] = fit(v, tr)
    PAR[v]['ALL'] = fit(v, np.arange(len(S)))
LV = {}
for v in 'ABCD':
    lh = np.zeros(len(S)); la = np.zeros(len(S))
    for s in SEAS_:
        te = np.where(S.sea.values == s)[0]; bt, bd, w = PAR[v][s]; a, b = lam(bt, bd, w, te); lh[te] = a; la[te] = b
    LV[v] = (lh, la)
def rps_one(lh, la, gd):
    Dd = sdist(lh, la); p1 = sum(p for k, p in Dd.items() if k > 0); px = Dd.get(0, 0)
    o1 = 1.0 if gd > 0 else 0.0; o2 = 1.0 if gd >= 0 else 0.0
    return ((p1 - o1) ** 2 + (p1 + px - o2) ** 2) / 2
RPS = {v: np.array([rps_one(LV[v][0][k], LV[v][1][k], GD[I[k]]) for k in range(len(S))]) for v in 'ABCD'}
print(NL + '1) ΠΑΡΑΜΕΤΡΟΙ (απο τις αλλες 3 σεζον) — bt δυναμη ομαδας · bD διαφορα λιγκας · w βαρος μοντελου στην αγκυρα (1 = καθολου αγκυρα)')
for v, nm in (('B', 'Β τεντωμα'), ('C', 'Γ αγκυρα'), ('D', 'Δ και τα 2')):
    print(f'   {nm:11s} ' + ' · '.join(f'{s}: bt {PAR[v][s][0]:+.2f} bD {PAR[v][s][1]:+.2f} w {PAR[v][s][2]:.2f}' for s in SEAS_) +
          f'  │ με ολες: bt {PAR[v]["ALL"][0]:+.2f} bD {PAR[v]["ALL"][1]:+.2f} w {PAR[v]["ALL"][2]:.2f}')
print(NL + '2) Κ1 ΑΚΡΙΒΕΙΑ εκτος δειγματος (Δlog-lik γκολ vs Α ανα σεζον · RPS 1Χ2)')
K1 = {}
for v, nm in (('A', 'Α σημερινο'), ('B', 'Β τεντωμα'), ('C', 'Γ αγκυρα'), ('D', 'Δ και τα 2')):
    d = {}
    for s in SEAS_:
        te = np.where(S.sea.values == s)[0]
        d[s] = ll(LV[v][0][te], LV[v][1][te], te) - ll(LV['A'][0][te], LV['A'][1][te], te)
    npos = sum(x > 0 for x in d.values()); k1 = v != 'A' and npos >= 3 and RPS[v].mean() < RPS['A'].mean(); K1[v] = k1
    print(f'   {nm:11s} RPS {RPS[v].mean():.4f} · Δlog-lik ' + ' '.join(f'{s[2:]}:{x:+.1f}' for s, x in d.items()) +
          (f' · θετικες {npos}/4 → Κ1 {"✓" if k1 else "✗"}' if v != 'A' else ''))
mo_r = np.array([rps_one(max((LV['A'][0][k] + LV['A'][1][k] + MO[k]) / 2, .05), max((LV['A'][0][k] + LV['A'][1][k] - MO[k]) / 2, .05), GD[I[k]]) for k in range(len(S))])
mc = []
for k, i in enumerate(I):
    s = sn(i, 'Crown', 0) or sn(i, 'SBOBET', 0)
    if s:
        T = LV['A'][0][k] + LV['A'][1][k]; m = implied_margin(i, *s); mc.append(rps_one(max((T + m) / 2, .05), max((T - m) / 2, .05), GD[i]))
    else: mc.append(np.nan)
mc = np.array(mc); ok = np.isfinite(mc)
print(f'   (αναφορα: ΑΓΟΡΑ ανοιγμα RPS {mo_r.mean():.4f} · ΑΓΟΡΑ κλεισιμο RPS {mc[ok].mean():.4f} (n{ok.sum()}, Α στο ιδιο {RPS["A"][ok].mean():.4f}))')
# ---------- picks
def make_picks(v):
    out = []
    for k, i in enumerate(I):
        D_ = sdist(LV[v][0][k], LV[v][1][k]); x = XG.get(str(MIDS[i]))
        Dx = sdist(max(x[0], .05), max(x[1], .05)) if x else None
        for bk in ('Crown', 'SBOBET'):
            sc = sn(i, bk, 0); mcl = implied_margin(i, *sc) if sc else np.nan
            got = set()
            for h in HSP:
                s = sn(i, bk, h)
                if not s: continue
                L, oh, oa = s
                for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                    if side in got or not (1.70 <= o <= 2.10): continue
                    if ln <= -0.5: f = cover_q; th = .04; kind = 'φαβορι'
                    elif ln >= 0.5: f = picks.p_cover; th = .10; kind = 'αουτσαιντερ'
                    else: continue
                    if edge(*f(D_, side, ln), o) < th: continue
                    got.add(side)
                    me = implied_margin(i, L, oh, oa)
                    out.append(dict(sea=SEA[i], bk=bk, kind=kind, home=side == 1, pnl=picks.settle(GD[i], side, ln, o),
                                    xv=edge(*f(Dx, side, ln), o) if Dx else np.nan, clv=side * (mcl - me) if np.isfinite(mcl) else np.nan))
    return pd.DataFrame(out)
def judge(x):
    if len(x) == 0: return '—', False
    m = x.groupby('bk').pnl.mean(); n = x.groupby('bk').size().mean(); ps = x.groupby('sea').pnl.mean(); pn = ps[ps.index.isin(NEW)]
    k2 = bool((m > 0).all()) and (ps > 0).sum() >= 3 and len(pn) == 2 and bool((pn > 0).all())
    k3 = x.xv.mean() > 0; k4 = x.clv.mean() > 0
    s = (f'{n:4.0f} picks {100 * m.mean():+6.1f}% μον {m.mean() * n:+5.1f} (' + ' '.join(f'{q[2:]} {100 * w:+.0f}' for q, w in ps.items()) +
         f') · xG {100 * x.xv.mean():+5.1f}% · CLV {x.clv.mean():+.3f} │ Κ2 {"✓" if k2 else "✗"} Κ3 {"✓" if k3 else "✗"} Κ4 {"✓" if k4 else "✗"}')
    return s, (k2 and k3 and k4)
print(NL + '3) PICKS εκτος δειγματος (κανονες UEL, πρωτη εμφανιση ≤72ω) — Κ2 βιβλια/σεζον/νεα μορφη · Κ3 αξια xG · Κ4 CLV')
PK = {v: make_picks(v) for v in 'ABCD'}
for v, nm in (('A', 'Α σημερινο'), ('B', 'Β τεντωμα'), ('C', 'Γ αγκυρα'), ('D', 'Δ και τα 2')):
    print(f'   {nm}  (Κ1 ακριβεια {"✓" if K1.get(v) else ("—" if v == "A" else "✗")})')
    for lab, m_ in (('ΟΛΑ', None), ('φαβορι εντος', ('φαβορι', True)), ('φαβορι εκτος', ('φαβορι', False)), ('αουτσαιντερ', ('αουτσαιντερ', None))):
        x = PK[v]
        if m_ and len(x):
            x = x[x.kind == m_[0]]
            if m_[1] is not None: x = x[x.home == m_[1]]
        s, ok_ = judge(x)
        print(f'      {lab:14s} {s}' + ('  ← ΠΕΡΝΑ Κ2-Κ4' if ok_ and v != 'A' else ''))
