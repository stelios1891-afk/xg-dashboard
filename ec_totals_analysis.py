# -*- coding: utf-8 -*-
"""ec_totals_analysis.py — ΓΙΑΤΙ ΣΤΑ ΣΥΝΟΛΑ ΤΟΥ EUROCUP ΔΕΝ ΒΡΙΣΚΟΥΜΕ EDGE ενω στην Ευρωλιγκα ναι; (5/10/2026, Στελιος).
ΣΥΓΚΡΙΣΗ EL vs EC (Crown, κανονικη+ολα, 2020/21-2025/26), ιδιο μετρο:
  1. δομη: ομαδες/σεζον, ματς ανα ομαδα, ομαδες που επιστρεφουν απο περσι
  2. αγορα: ποσο διαφερουν τα συνολα μεταξυ ματς (sd γραμμης), θορυβος (sd πραγματικο − κλεισιμο), ποσο «εξηγει» η αγορα
  3. μοντελο (live καθε διοργανωσης): λαθος vs αγορα, Κ2 vs κλεισιμο — ολη η σεζον / αγων 1-6 / 7+
  4. μεροληψια αγορας (πραγματικο − κλεισιμο) ανα φαση
5. EC ΜΟΝΟ — ΔΕΔΟΜΕΝΑ ΠΟΥ ΛΕΙΠΟΥΝ: τα φετινα ΕΓΧΩΡΙΑ σκορ των ομαδων (ποντοι γηπ+φιλ στα εγχωρια ματς πριν το ματς EC, vs μεσο ορο
   του πρωταθληματος τους) — εξηγουν το (πραγματικο − κλεισιμο) / (πραγματικο − μοντελο); (≥3 εγχωρια ματς και οι 2 ομαδες)
   ΠΡΟ-ΔΗΛΩΜΕΝΟ: σημα αν κλιση vs ΚΛΕΙΣΙΜΟ t ≥ 2 ΚΑΙ ιδιο προσημο ≥4/6 σεζον.
Εξοδος: ec_totals_analysis_out.txt"""
import sys, io, contextlib, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# ---------- EuroCup (live ec1 συνολα + Crown) ----------
EC = {'__name__': 'y'}
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    pass
exec(open('ec_season_backtest.py', encoding='utf-8').read().replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
     .replace("open('ec_season_backtest_out.txt', 'w', encoding='utf-8')", "open('_unused_ecsb.txt', 'w', encoding='utf-8')"), EC)
Dc, TOTPc, MKTc, TOTc, GNc, seac = EC['D'], EC['TOTP'], EC['MKT'], EC['TOT'], EC['GN'], EC['seasn']
INNER = EC['NS']; MAPD, DOMNS = INNER['MAPD'], INNER['DOMNS']
out.clear()
# ---------- Ευρωλιγκα (live συνολο t_new + Crown) ----------
EL = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), EL)
Dl, RECl, PRl, keyl, TOTl, SE5 = EL['D'], EL['REC'], EL['PR'], EL['key'], EL['TOT'], EL['SE5']
GNl = np.zeros(len(Dl), int); cnt = {}
for i in np.argsort(pd.to_datetime(Dl.t.values).values):
    s, h, a = Dl.season.values[i], Dl.home.values[i], Dl.away.values[i]
    GNl[i] = max(cnt.get((s, h), 0), cnt.get((s, a), 0)); cnt[(s, h)] = cnt.get((s, h), 0) + 1; cnt[(s, a)] = cnt.get((s, a), 0) + 1
# κοινη μορφη: λιστα (season, GN, actual, model, close_line, close_mu, open_mu)
rows_ec = [(seac[i], GNc[i], TOTc[i], TOTPc[i], MKTc[i]['c'][0], MKTc[i]['c'][1], MKTc[i]['o'][1]) for i in MKTc if seac[i] in EC['EVM'] and np.isfinite(TOTPc[i])]
rows_el = []
for p, r in RECl[23].items():
    m = PRl.get(keyl(p), {}).get('t_new')
    if m is None or not np.isfinite(m): continue
    rows_el.append((Dl.season.values[p], GNl[p], TOTl[p], m, r[0][2], r[0][1], r['open'][1]))
def team_struct(D_, seasons):
    res = []
    prev = None
    for Y in seasons:
        s = D_[D_.season == Y]; tm = set(s.home) | set(s.away)
        gp = np.median([((s.home == c) | (s.away == c)).sum() for c in tm])
        ret = len(tm & prev) / len(tm) if prev else np.nan; prev = tm; res.append((len(tm), gp, ret))
    return res
P('################ 1. ΔΟΜΗ ################')
for nm, D_, ss in (('Ευρωλιγκα', Dl, sorted(set(Dl.season))), ('EuroCup', Dc, sorted(set(Dc.season)))):
    st = team_struct(D_, ss)
    P(f'  {nm:10s} ομαδες/σεζον {np.mean([x[0] for x in st]):.0f} · ματς ανα ομαδα (διαμεσος) {np.mean([x[1] for x in st]):.0f} · επιστρεφουν απο περσι {np.nanmean([x[2] for x in st])*100:.0f}%')
def k2(x, z):
    b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x); se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); return b, b / se
P(''); P('################ 2-4. ΑΓΟΡΑ & ΜΟΝΤΕΛΟ (Crown) ################')
for nm, R in (('Ευρωλιγκα', rows_el), ('EuroCup', rows_ec)):
    A = np.array([r[2:] for r in R], float); g = np.array([r[1] for r in R]); ss = np.array([r[0] for r in R])
    a, m, Lc, mc, mo = A.T
    P(f'  [{nm}] n {len(a)} · μεσο συνολο {a.mean():.1f} · sd γραμμης κλεισ. (ποσο διαφερουν τα ματς) {Lc.std():.1f} · θορυβος sd(πραγμ − κλεισ.) {np.std(a - mc):.1f}'
      f' · «εξηγει» η αγορα {1 - np.var(a - mc) / np.var(a):.1%}')
    for lab, sel in (('ολη η σεζον', g >= 0), ('αγων 1-6', g <= 5), ('αγων 7+', g >= 6)):
        rm = lambda v: float(np.sqrt(np.mean((a[sel] - v[sel]) ** 2)))
        b, t = k2(m[sel] - mc[sel], a[sel] - mc[sel])
        per = [np.polyfit((m - mc)[sel & (ss == Y)], (a - mc)[sel & (ss == Y)], 1)[0] for Y in sorted(set(ss)) if (sel & (ss == Y)).sum() > 20]
        P(f'     {lab:12s} n {sel.sum():4d} · λαθος μοντ. {rm(m):.2f} / ανοιγμα {rm(mo):.2f} / κλεισιμο {rm(mc):.2f} (χασμα {rm(m) - rm(mc):+.2f}) · '
          f'Κ2 b {b:+.2f} (t {t:+.1f}, θετ. {sum(x > 0 for x in per)}/{len(per)}) · μεροληψια αγορας (πραγμ − κλεισ.) {np.mean(a[sel] - mc[sel]):+.2f} · μοντ. {np.mean(a[sel] - m[sel]):+.2f}')
# ---------- 5. EC: φετινα εγχωρια σκορ ----------
P(''); P('################ 5. EuroCup — ΦΕΤΙΝΑ ΕΓΧΩΡΙΑ ΣΚΟΡ (δεδομενα που δεν χρησιμοποιουμε στα συνολα) ################')
DOM = DOMNS['DOM']
LGT = {}   # (L, sea) -> λιστα (ts, total) για μεσο λιγκας
TMT = {}   # (L, sea, tid) -> λιστα (ts, total, pace?)
for k, v in DOM.items():
    L, sea = k.split('_')
    for g in v['games']:
        try: tt = int(g[4]) + int(g[5])
        except Exception: continue
        ts = pd.Timestamp(g[1]).tz_localize(None).timestamp()
        LGT.setdefault((L, sea), []).append((ts, tt))
        for tid in (g[2], g[3]): TMT.setdefault((L, sea, int(tid)), []).append((ts, tt))
TS = np.array([pd.Timestamp(t).tz_localize(None).timestamp() if pd.Timestamp(t).tzinfo else pd.Timestamp(t).timestamp() for t in Dc.t])
def dom_dev(i, c):
    m = MAPD.get((seac[i], c))
    if not m: return None
    y = int(m[0][1:]); sea = f'{y % 100:02d}-{(y + 1) % 100:02d}'; L = m[2]
    tg = [x[1] for x in TMT.get((L, sea, int(m[1])), []) if x[0] < TS[i] - 3600]
    lg = [x[1] for x in LGT.get((L, sea), []) if x[0] < TS[i] - 3600]
    if len(tg) < 3 or len(lg) < 20: return None
    return float(np.mean(tg) - np.mean(lg)), len(tg)
X, R1, R2, SS, G6 = [], [], [], [], []
for i in MKTc:
    if seac[i] not in EC['EVM'] or not np.isfinite(TOTPc[i]): continue
    dh, da = dom_dev(i, Dc.home.values[i]), dom_dev(i, Dc.away.values[i])
    if dh is None or da is None: continue
    X.append(dh[0] + da[0]); R1.append(TOTc[i] - MKTc[i]['c'][1]); R2.append(TOTc[i] - TOTPc[i]); SS.append(seac[i]); G6.append(GNc[i] <= 5)
X, R1, R2, SS, G6 = map(np.array, (X, R1, R2, SS, G6))
P(f'  ματς με εγχωρια ≥3 και για τις 2 ομαδες: {len(X)} · sd σηματος {X.std():.1f} ποντοι')
for lab, sel in (('ολη η σεζον', np.ones(len(X), bool)), ('αγων 1-6', G6), ('αγων 7+', ~G6)):
    for nm_, R in (('vs ΚΛΕΙΣΙΜΟ', R1), ('vs ΜΟΝΤΕΛΟ', R2)):
        b, t = k2(X[sel], R[sel]); per = [np.polyfit(X[sel & (SS == Y)], R[sel & (SS == Y)], 1)[0] for Y in EC['EVM'] if (sel & (SS == Y)).sum() > 15]
        same = sum(np.sign(p) == np.sign(b) for p in per)
        flag = '  ← ΣΗΜΑ (η αγορα δεν το εχει πληρως)' if nm_ == 'vs ΚΛΕΙΣΙΜΟ' and abs(t) >= 2 and same >= 4 else ''
        P(f'     {lab:12s} {nm_:12s} n {sel.sum():4d} · κλιση {b:+.3f} π. ανα ποντο εγχωριας διαφορας (t {t:+.1f}, ιδιο προσημο {same}/{len(per)}){flag}')
open('ec_totals_analysis_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
