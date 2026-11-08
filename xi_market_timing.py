# -*- coding: utf-8 -*-
"""xi_market_timing.py — 21/10/2026 (Στελιος: «το νοημα δεν ειναι το κλεισιμο, αλλα 60′ ή για σιγουρια 55′ πριν — να ξερουμε αν οι επισημες ενδεκαδες
μπορουν να μας δωσουν κατι· ξεχωρισε τα ματς με τη μεγαλυτερη αλλαγη (π.χ. 10%) και δες ποσο κινειται η αγορα και σε ποση ωρα»).
ΦΟΡΜΟΥΛΑ (εκτος δειγματος, LOSO 4 σεζον): χαντικαπ f_gd = αξια + εμπιστοσυνη (διαφορα) · συνολα f_t = εμπιστ./αξια ανα θεση + xGI ενδεκαδας.
  Υπολογιζεται με την ΠΡΑΓΜΑΤΙΚΗ ενδεκαδα = ο,τι ξερει κανεις μολις ανακοινωθει (~60′ πριν).
ΑΓΟΡΑ: Crown & Bet365 (Nowgoal, χρονοσφραγιδες) → υπεροχη s(t) απο χαντικαπ+τιμη, συνολο T(t) απο over/under+τιμη, σε: 24ω · 6ω · 2ω · 90′ · 60′ · 55′ ·
  45′ · 30′ · 15′ · κλεισιμο. (μετατροπη με πινακα Poisson, συνολο 2.7 για το χαντικαπ, υπεροχη 0 για τα συνολα)
ΕΡΩΤΗΣΕΙΣ: (1) κινειται η αγορα ΜΕΤΑ το 55′ προς τη μερια της φορμουλας; (κλιση κινησης πανω στη φορμουλα) · (2) το αποτελεσμα vs τιμη 55′:
  εξηγει η φορμουλα το λαθος της τιμης του 55′; · (3) top 10% αλλαγες: χρονοδιαγραμμα κινησης · (4) πονταρισμα στο 55′ οταν |φορμουλα| στο top 10%.
ΚΡΙΤΗΡΙΟ για (4) (γραφτηκε ΠΡΙΝ): ROI > 0 σε ≥3/4 σεζον και στα 2 βιβλια, CLV (τιμη 55′ vs κλεισιμο) υπερ μας."""
import sys, json, glob, bisect, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
NL = chr(10)
# ---------- φορμουλα LOSO ----------
src = open('xi_xgi_eval.py', encoding='utf-8').read()
exec(src[:src.index("print(f'ματς {len(D)} · με xGI")])
SE = sorted(D.season.unique())
def loso_pred(cols, y):
    p = pd.Series(np.nan, index=D.index)
    for s in SE:
        tr = D[(D.season != s) & D[y].notna()]; te = D[D.season == s]
        X = np.column_stack([np.ones(len(tr))] + [tr[c].fillna(0).values for c in cols]); b = np.linalg.lstsq(X, tr[y].values, rcond=None)[0]
        p[te.index] = np.column_stack([np.zeros(len(te))] + [te[c].fillna(0).values for c in cols]) @ b
    return p
D['f_gd'] = loso_pred(['x_Vlog', 'x_Tm10'], 'r_xgd')
D['f_t'] = loso_pred(['s_VlogO', 's_VlogD', 's_Tm10O', 's_Tm10D', 's_XGI'], 'r_tx')
# ---------- αγορα: χρονοσειρες ----------
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
mids = set(D.mid); AH, OU = {}, {}
for f in glob.glob('nowgoal_odds/*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get('cid') not in (3, 8) or str(r.get('mid')) not in mids: continue
        bk = 'Crown' if r['cid'] == 3 else 'Bet365'
        for key, store in (('ah', AH), ('ou', OU)):
            rows = []
            for row in r.get(key) or []:
                try: t, a, g, b = row; L = pl(g); a, b = float(a) + 1, float(b) + 1
                except Exception: continue
                if L is None or t is None or a <= 1 or b <= 1: continue
                rows.append((t, L, a, b))
            if rows: rows.sort(); store[(str(r['mid']), bk)] = rows
# πινακες μετατροπης (γρηγορα): υπεροχη ↔ πιθανοτητα καλυψης γραμμης, συνολο ↔ πιθανοτητα over
S_GRID = np.round(np.arange(-4.0, 4.001, 0.02), 3); LINES = np.round(np.arange(-4.0, 4.001, 0.25), 2)
QH = {}
for L in LINES:
    q = []
    for s in S_GRID:
        d = picks.gd_dist(max((2.7 + s) / 2, .05), max((2.7 - s) / 2, .05)); pw, pp = picks.p_cover(d, 1, -L); pl_ = 1 - pw - pp
        q.append(pw / max(pw + pl_, 1e-9))
    QH[L] = np.array(q)
T_GRID = np.round(np.arange(0.8, 6.0, 0.02), 3); OLINES = np.round(np.arange(0.5, 6.01, 0.25), 2)
IDXT = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25)
QO = {}
for L in OLINES:
    q = []
    for T in T_GRID:
        M = picks.score_matrix_dom(T / 2, T / 2); tot = np.bincount(IDXT.ravel(), weights=np.asarray(M).ravel(), minlength=25)
        parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; po = pu = 0
        for x in parts: po += tot[KS > x + .01].sum() / len(parts); pu += tot[KS < x - .01].sum() / len(parts)
        q.append(po / max(po + pu, 1e-9))
    QO[L] = np.array(q)
def sup(L_home_gives, oh, oa):
    L = round(round(L_home_gives * 4) / 4, 2)
    if L not in QH: return np.nan
    q = (1 / oh) / (1 / oh + 1 / oa); arr = QH[L]
    return float(np.interp(q, arr, S_GRID)) if arr[0] < arr[-1] else float(np.interp(q, arr[::-1], S_GRID[::-1]))
def tot(L, oo, uu):
    L = round(round(L * 4) / 4, 2)
    if L not in QO: return np.nan
    q = (1 / oo) / (1 / oo + 1 / uu); return float(np.interp(q, QO[L], T_GRID))
TP = [('24ω', 1440), ('6ω', 360), ('2ω', 120), ('90′', 90), ('60′', 60), ('55′', 55), ('45′', 45), ('30′', 30), ('15′', 15), ('κλεισ.', 0)]
TA = {k: [x[0] for x in v] for k, v in AH.items()}; TO = {k: [x[0] for x in v] for k, v in OU.items()}
SIGN = -1                      # Nowgoal: θετικη γραμμη = δινει ο γηπεδουχος (ελεγχθηκε στο abs_phase1, συσχ. 0.99)
recs = []
for r in D.itertuples():
    ko = KO.get(r.mid)
    if not ko: continue
    for bk in ('Crown', 'Bet365'):
        a = AH.get((r.mid, bk)); o = OU.get((r.mid, bk))
        if not a: continue
        row = dict(mid=r.mid, bk=bk, season=r.season, league=r.league, f_gd=r.f_gd, f_t=r.f_t, gd=r.gd, tg=(r.hg + r.ag) if r.hg == r.hg else np.nan)
        for lab, mins in TP:
            t = ko - mins * 60 if mins else ko
            ia = bisect.bisect_right(TA[(r.mid, bk)], t); pa = a[:ia]
            po = (o or [])[:bisect.bisect_right(TO[(r.mid, bk)], t)] if o else []
            if pa:
                L, oh, oa = pa[-1][1], pa[-1][2], pa[-1][3]
                row[f's_{lab}'] = sup(SIGN * -L, oh, oa) if True else np.nan        # sup() θελει «ποσα δινει ο γηπεδουχος» → −(γραμμη γηπ.)
                row[f'L_{lab}'] = L; row[f'oh_{lab}'] = oh; row[f'oa_{lab}'] = oa
            if po:
                row[f'T_{lab}'] = tot(po[-1][1], po[-1][2], po[-1][3]); row[f'OL_{lab}'] = po[-1][1]; row[f'oo_{lab}'] = po[-1][2]; row[f'ou_{lab}'] = po[-1][3]
        recs.append(row)
M = pd.DataFrame(recs)
# προσημο: η υπεροχη στο κλεισιμο πρεπει να συσχετιζεται θετικα με τη διαφορα γκολ
c = np.corrcoef(M['s_κλεισ.'].fillna(0), M.gd.fillna(0))[0, 1]
if c < 0:
    for lab, _ in TP: M[f's_{lab}'] = -M[f's_{lab}']
print(f'γραμμες αγορας: {len(M)} (ματς×βιβλιο) · συσχετιση υπεροχης κλεισιματος με διαφορα γκολ {abs(c):.2f}')
def fit(x, y):
    m = np.isfinite(x) & np.isfinite(y); x, y = x[m], y[m]
    if len(x) < 50: return np.nan, np.nan, len(x)
    xc = x - x.mean(); b = (xc * (y - y.mean())).sum() / (xc ** 2).sum(); res = y - y.mean() - b * xc
    return b, b / np.sqrt((res ** 2).sum() / (len(x) - 2) / (xc ** 2).sum()), len(x)
for kind, f, pre, lab_y in (('ΧΑΝΤΙΚΑΠ', 'f_gd', 's', 'gd'), ('ΣΥΝΟΛΑ', 'f_t', 'T', 'tg')):
    print(f'{NL}{"=" * 130}{NL}{kind} — φορμουλα ({f}) με την επισημη ενδεκαδα')
    for bk in ('Crown', 'Bet365'):
        q = M[M.bk == bk]
        mv = []
        for (a, _), (b, _) in zip(TP[:-1], TP[1:]):
            bb, tt, n = fit(q[f].values, (q[f'{pre}_{b}'] - q[f'{pre}_{a}']).values); mv.append(f'{a}→{b} {bb:+.2f}(t{tt:.1f})')
        print(f'   {bk:7s} ΚΙΝΗΣΗ αγορας ανα διαστημα πανω στη φορμουλα (1 = η αγορα κουνηθηκε οσο λεει η φορμουλα): ' + ' · '.join(mv))
        b55, t55, n55 = fit(q[f].values, (q[lab_y] - q[f'{pre}_55′']).values); bcl, tcl, _ = fit(q[f].values, (q[lab_y] - q[f'{pre}_κλεισ.']).values)
        b90, t90, _ = fit(q[f].values, (q[lab_y] - q[f'{pre}_90′']).values)
        print(f'   {bk:7s} ΑΠΟΤΕΛΕΣΜΑ − τιμη πανω στη φορμουλα: 90′ πριν {b90:+.2f} (t {t90:.1f}) · 55′ πριν {b55:+.2f} (t {t55:.1f}, n {n55}) · κλεισιμο {bcl:+.2f} (t {tcl:.1f})')
    # top 10% |φορμουλα| — χρονοδιαγραμμα κινησης ΠΡΟΣ τη μερια της φορμουλας
    q = M[M.bk == 'Crown'].copy(); thr = q[f].abs().quantile(.90); top = q[q[f].abs() >= thr].copy(); sg = np.sign(top[f])
    base = top[f'{pre}_24ω']
    print(f'   TOP 10% (|φορμουλα| ≥ {thr:.2f}, n {len(top)}, μεσο |φορμουλα| {top[f].abs().mean():.2f}): μεση κινηση ΠΡΟΣ τη φορμουλα απο 24ω πριν (Crown): '
          + ' · '.join(f'{lab} {((top[f"{pre}_{lab}"] - base) * sg).mean():+.3f}' for lab, _ in TP[1:]))
    rest = q[q[f].abs() < q[f].abs().quantile(.5)]; sgr = np.sign(rest[f])
    print(f'   (ελεγχος — ουδετερα 50%: ' + ' · '.join(f'{lab} {((rest[f"{pre}_{lab}"] - rest[f"{pre}_24ω"]) * sgr).mean():+.3f}' for lab, _ in TP[1:]) + ')')
# ---------- (4) πονταρισμα στο 55′ ----------
def settle_ah(gd, side, ln, o): return picks.settle(gd, side, ln, o)
def settle_ou(tg, L, o, over):
    parts = [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]; r = 0.0
    for p in parts:
        dd = (tg - p) if over else (p - tg); r += ((o - 1) if dd > 0 else (0 if dd == 0 else -1)) / len(parts)
    return r
M.to_csv('xi_market_timing_rows.csv', index=False)
M = pd.read_csv('xi_market_timing_rows.csv', dtype={'mid': str, 'season': str}) if 'M' not in globals() else M
print(f'{NL}{"=" * 130}{NL}(4) ΠΟΝΤΑΡΙΣΜΑ ΣΤΟ 55′ προς τη μερια της φορμουλας, οταν |φορμουλα| στο top 10% (ορια απο τις ΑΛΛΕΣ σεζον) — ROI, CLV')
for kind, f in (('χαντικαπ', 'f_gd'), ('συνολα', 'f_t')):
    for bk in ('Crown', 'Bet365'):
        q = M[M.bk == bk]; out = []; allp = []
        for s in SE:
            thr = q[q.season != s][f].abs().quantile(.90); z = q[(q.season == s) & (q[f].abs() >= thr)]
            pn = []
            for r in z.to_dict('records'):
                if kind == 'χαντικαπ':
                    L, oh, oa, Lc, ohc, oac = r.get('L_55′'), r.get('oh_55′'), r.get('oa_55′'), r.get('L_κλεισ.'), r.get('oh_κλεισ.'), r.get('oa_κλεισ.')
                    if L is None or L != L or Lc != Lc or r['gd'] != r['gd']: continue
                    side = 1 if r['f_gd'] > 0 else -1; ln = -L if side == 1 else L          # Nowgoal: θετικη = δινει ο γηπεδουχος
                    o, oc = (oh, ohc) if side == 1 else (oa, oac)
                    pn.append((picks.settle(r['gd'], side, ln, o), o / oc - 1 if L == Lc else np.nan))
                else:
                    L, oo, uu, Lc, ooc, uuc = r.get('OL_55′'), r.get('oo_55′'), r.get('ou_55′'), r.get('OL_κλεισ.'), r.get('oo_κλεισ.'), r.get('ou_κλεισ.')
                    if L is None or L != L or Lc != Lc or r['tg'] != r['tg']: continue
                    over = r['f_t'] > 0; o, oc = (oo, ooc) if over else (uu, uuc)
                    pn.append((settle_ou(r['tg'], L, o, over), o / oc - 1 if L == Lc else np.nan))
            if pn:
                a = np.array(pn, float); out.append((s, len(a), a[:, 0].mean())); allp += pn
        A = np.array(allp, float)
        print(f'   {kind:9s} {bk:7s} n {len(A):4d} · ROI {100 * A[:, 0].mean():+.1f}% · τιμη 55′ vs κλεισιμο (ιδια γραμμη) {100 * np.nanmean(A[:, 1]):+.1f}% · '
              + ' · '.join(f'{s}: {100 * r:+.0f}% (n {n})' for s, n, r in out) + f' · θετικες {sum(r > 0 for _, _, r in out)}/4')
