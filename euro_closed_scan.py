# -*- coding: utf-8 -*-
"""euro_closed_scan.py — 5/11/2026 (Στελιος: «υπαρχει καποια κατηγορια η οποια με το νεο τεστ βελτιωνεται και ισως την ειχαμε ξεγραψει χωρις λογο;»).
ΣΑΡΩΣΗ ΟΛΩΝ των ΚΛΕΙΣΤΩΝ κατηγοριων Ευρωπης, ΠΑΛΙΑ (8/9 προβλεψεις ή pen76, αποτελεσμα με παραταση) vs ΚΑΘΑΡΗ (euro_clean_rules: emps, 90′, Μ8 στο χαντικαπ).
Κατωφλια: φαβ ≥4 · dog ≥10 · DNB/±0.25 ≥4 · over ≥4 · under ≥10. UCL = νεα μορφη, πρωτη εμφανιση 168-2ω, τιμιος χρονος · UEL/UECL = 4 σεζον, 72ω-κλεισιμο.
ΚΡΙΤΗΡΙΑ (ιδια με euro_clean_rules): UCL ROI>0 + 2/2 σεζον · αλλοι ROI>0, 2 βιβλια, ≥3/4 σεζον · ολοι CLV οχι αρνητικο (t<−1.5), αξια xG>0 (χαντικαπ).
ΣΗΜΑΙΑ «ΝΕΑ»: κοβοταν στα παλια ΚΑΙ περνα στα καθαρα. >30 κελια: καποια περνουν απο τυχη → μονο υποψηφια για ελεγχο. Για οσα περνουν: κατωφλια/LOSO, και στις Β/Γ ελεγχος με την πηγη του live (γκολ+Elo αντι Ben).
Χρηση: python euro_closed_scan.py <φακελος με τα data_Europe_* πριν το 19/10> (για το συνολο γκολ ΜΕ παραταση)."""
import sys, json, glob, os, pickle
_src = open('euro_clean_rules.py', encoding='utf-8').read()
_pre = _src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')]
_a = "                    if kind == 'dnb' and abs(ln) > .01: continue\n"
assert _pre.count(_a) == 1
_pre = _pre.replace(_a, _a + "                    if kind == 'm25' and abs(ln + .25) > .01: continue\n                    if kind == 'p25' and abs(ln - .25) > .01: continue\n")
exec(_pre)
_ET = {}
for f in glob.glob(os.path.join(sys.argv[1], 'data_Europe_*.json')):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        if m.get('hs') is not None and m.get('as') is not None: _ET[str(k)] = m['hs'] + m['as']
TOT_ET = np.array([_ET.get(m, TOT90[i]) for i, m in enumerate(MIDS)], float)
print(f'συνολο γκολ με παραταση ≠ 90′ σε {(TOT_ET != TOT90).sum()} ματς')
KN = SH != '?'
CATS = {'Α': FMH & FMA, 'Β': (FMH != FMA) & KN, 'Γ': (~FMH) & (~FMA) & KN}
COMPS = {'UCL': 'ChampionsLeague', 'UEL': 'EuropaLeague', 'UECL': 'ConferenceLeague'}
# ---- πηγη του live στις 9 λιγκες (γκολ+Elo αντι Ben), χωρις Μ8, μονο ελεγχος Β/Γ
_e = pickle.load(open('euro_blend_dump_ben_elo.pkl', 'rb')); _ie = {str(m): k for k, m in enumerate(_e['MIDS'])}
ELO = (np.array([_e['LH'][_ie[m]] if m in _ie else np.nan for m in MIDS], float), np.array([_e['LA'][_ie[m]] if m in _ie else np.nan for m in MIDS], float))
_w = pickle.load(open('euro_v6w2_preds_pen76_elo.pkl', 'rb')); _iw = {str(m): k for k, m in enumerate(_w['mids'])}
_eh = np.array([_w['lh'][_iw[m]] if m in _iw else np.nan for m in MIDS], float); _ea = np.array([_w['la'][_iw[m]] if m in _iw else np.nan for m in MIDS], float)
OH_E, OA_E = pair_live((_eh, _ea))
NOT_NAN_E = np.isfinite(ELO[0]) & np.isfinite(_eh)
def crit(z, ucl, handicap):
    z_ = z[z.sea.isin(NEW)] if ucl else z
    if not len(z_): return False, z_
    ps = z_.groupby('sea').pnl.mean(); bb = z_.groupby('bk').pnl.mean(); tv = tval(z_.clv)
    ok = z_.pnl.mean() > 0 and ((bool((ps > 0).all()) and len(ps) == 2) if ucl else (ps > 0).sum() >= 3) and (ucl or (bool((bb > 0).all()) and len(bb) == 2))
    ok = ok and not (np.isfinite(tv) and z_.clv.mean() < 0 and tv < -1.5) and ((not handicap) or z_.xv.mean() > 0)
    return bool(ok), z_
KINDS = (('φαβορι', 'fav', .04), ('αουτσαιντερ', 'dog', .10), ('DNB', 'dnb', .04), ('−0.25', 'm25', .04), ('+0.25', 'p25', .04), ('over', 'over', .04), ('under', 'under', .10))
LIVE = {('UCL', 'Α', 'fav'), ('UCL', 'Α', 'dog'), ('UCL', 'Α', 'dnb'), ('UCL', 'Α', 'over'), ('UCL', 'Β', 'over'), ('UECL', 'Α', 'fav'), ('UECL', 'Α', 'dog'), ('UECL', 'Α', 'over')}
ROWS = []; PASS = []
def cell(lab, cn, cat, mask, kd, thr, sidefn=None, shown=True):
    ucl = cn == 'UCL'; hs = H_UCL if ucl else H_72; handicap = kd not in ('over', 'under')
    if handicap:
        old = seq_ah(OLD_A6, GD_OLD, mask, kd, hs, ucl, sidefn); new = seq_ah(P6['INS'], GD, mask, kd, hs, ucl, sidefn)
    else:
        ov = kd == 'over'
        old = seq_ou(OH_O, OA_O, TOT_ET, mask, ov, hs, ucl, not ucl); new = seq_ou(OH_N, OA_N, TOT90, mask, ov, hs, ucl, not ucl)
    zo, zn = at(old, thr), at(new, thr)
    ko, zo_ = crit(zo, ucl, handicap); kn, zn_ = crit(zn, ucl, handicap)
    ROWS.append(dict(κατηγορια=lab, n_παλιο=len(zo_) / 2, ROI_παλιο=round(100 * zo_.pnl.mean(), 1) if len(zo_) else np.nan, n=len(zn_) / 2, ROI=round(100 * zn_.pnl.mean(), 1) if len(zn_) else np.nan, μ=round(units(zn_), 1) if len(zn_) else 0,
                     σεζον=' '.join(f"{100 * zn_[zn_.sea == s].pnl.mean():+.0f}" for s in SEAS if (zn_.sea == s).any()), clv=round(zn_.clv.mean(), 3) if len(zn_) else np.nan, xG=round(100 * zn_.xv.mean(), 1) if len(zn_) and handicap else np.nan, παλιο_ok=ko, ok=kn, ΝΕΑ=(kn and not ko)))
    if kn: PASS.append((lab, cn, cat, mask, kd, thr, sidefn, old, new))
for cn, comp in COMPS.items():
    for cat, cm in CATS.items():
        mask = (COMP == comp) & cm
        for nm, kd, thr in KINDS:
            if (cn, cat, kd) in LIVE: continue
            cell(f'{cn} {cat} {nm} ≥{int(thr * 100)}%', cn, cat, mask, kd, thr)
_nofm = lambda i: (1 if FMA[i] else -1)
_fm = lambda i: (1 if FMH[i] else -1)
cell('UEL Α φαβορι εκτος ≥4%', 'UEL', 'Α', (COMP == 'EuropaLeague') & CATS['Α'], 'fav', .04, lambda i: -1)
cell('UCL Β αουτσαιντερ χωρις FotMob ≥10%', 'UCL', 'Β', (COMP == 'ChampionsLeague') & CATS['Β'], 'dog', .10, _nofm)
cell('UEL Β αουτσαιντερ χωρις FotMob ≥10%', 'UEL', 'Β', (COMP == 'EuropaLeague') & CATS['Β'], 'dog', .10, _nofm)
cell('UECL Β αουτσαιντερ ΜΕ FotMob ≥10%', 'UECL', 'Β', (COMP == 'ConferenceLeague') & CATS['Β'], 'dog', .10, _fm)
pd.set_option('display.width', 220)
T = pd.DataFrame(ROWS)
print(f'\nΟΛΑ ΤΑ ΚΕΛΙΑ ({len(T)}, ελαχιστο 10 picks)'); print(T[T.n >= 10].to_string(index=False))
print('\nΑΛΛΑΓΗ ROI παλιο → καθαρο, μεγαλυτερες ανοδοι (≥10 picks)')
U = T[T.n >= 10].assign(Δ=lambda d: d.ROI - d.ROI_παλιο).sort_values('Δ', ascending=False).head(10)
print(U[['κατηγορια', 'n_παλιο', 'ROI_παλιο', 'n', 'ROI', 'Δ', 'ok', 'ΝΕΑ']].to_string(index=False))
print('\nΛΕΠΤΟΜΕΡΕΙΕΣ για ΟΣΑ ΠΕΡΝΟΥΝ με ≥20 picks')
for lab, cn, cat, mask, kd, thr, sf, old, new in PASS:
    ucl = cn == 'UCL'; handicap = kd not in ('over', 'under'); _, z_ = crit(at(new, thr), ucl, handicap)
    if len(z_) / 2 < 20: continue
    rule(lab, old, new, thr, (.04, .06, .08, .10, .12, .14), new_only=ucl, handicap=handicap, live=False)
    if cat != 'Α':                       # πηγη του live στις 9 λιγκες
        m2 = mask & NOT_NAN_E; hs = H_UCL if ucl else H_72
        zz = at(seq_ah(ELO, GD, m2, kd, hs, ucl, sf) if handicap else seq_ou(OH_E, OA_E, TOT90, m2, kd == 'over', hs, ucl, not ucl), thr)
        zz = zz[zz.sea.isin(NEW)] if ucl else zz
        print(f'   ΜΕ γκολ+Elo (πηγη live, χωρις Μ8) {desc(zz)}')
