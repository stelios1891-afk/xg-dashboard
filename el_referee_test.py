# -*- coding: utf-8 -*-
"""el_referee_test.py — ΔΙΑΙΤΗΤΕΣ στην Ευρωλιγκα (1/10/2026, Στελιος «ξεκινα»: 3 διαιτητες ανα ματς, δυσκολο αλλα ας το δουμε).
Δεδομενα: el_referees.json (επισημο API v2, 3 διαιτητες ανα ματς 2017-2026· ανακοινωνονται ~1-2 μερες πριν = γνωστοι στο alert) ·
  el_box.json (βολες/φαουλ ανα ομαδα) · Crown ανοιγμα/κλεισιμο & live μοντελο E2021-25 (el_alert_types).
ΒΗΜΑΤΑ (σταματαμε οπου αποτυχει):
 1. ΜΗΧΑΝΙΣΜΟΣ: βολες (FTA) & φαουλ ανα ματς (ανα 40′) = επιπεδο σεζον + ομαδα γηπ + ομαδα φιλ + διαιτ1 + διαιτ2 + διαιτ3 (ridge).
 2. ΣΤΑΘΕΡΟΤΗΤΑ (το σημαντικοτερο): επιδραση διαιτητων απο τις ΑΛΛΕΣ σεζον → προβλεπει τις βολες της τριαδας στη νεα σεζον; (κλιση, t, ανα σεζον)
 3. ΠΟΝΤΟΙ: η προβλεψη της τριαδας (LOSO) → συνολο − αγορα (ανοιγμα/κλεισιμο) και συνολο − μοντελο.
 4. ΕΔΡΑ: ευνοια γηπεδουχου (διαφορα βολων γηπ − φιλ) → διαφορα σκορ − αγορα/μοντελο.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: (α) σταθεροτητα: κλιση βολων LOSO > 0 με t ≥ 2 και θετικη σε ≥4/5 σεζον · (β) συνολο/διαφορα: διορθωση
  μοντελου LOSO με RMSE καλυτερο σε ≥4/5 σεζον · (γ) δεν χαλαει τις μοναδες των picks στο alert.
Εξοδος: el_referee_test_out.txt"""
import sys, json, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
exec(open('el_alert_types.py', encoding='utf-8').read().split('ZZ = {}')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", ''), NS)
D, REC, PR, key, pick, settle, SE5 = (NS[k] for k in ('D', 'REC', 'PR', 'key', 'pick', 'settle', 'SE5'))
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
REF = json.load(open('el_referees.json', encoding='utf-8'))
BOX = json.load(open('el_box.json', encoding='utf-8'))
rows = []
for k, b in BOX.items():
    r = REF.get(k)
    if not r or len(r['refs']) < 3 or not b.get('h') or not b.get('a'): continue
    mn = float(b.get('min') or 200) or 200
    sc = 200.0 / mn if mn > 150 else 1.0
    try:
        rows.append(dict(key=k, season=b['season'], home=b['hcode'], away=b['acode'], r1=r['refs'][0][0], r2=r['refs'][1][0], r3=r['refs'][2][0],
                         fta=(b['h']['fta'] + b['a']['fta']) * sc, pf=(b['h']['pf'] + b['a']['pf']) * sc, ftad=(b['h']['fta'] - b['a']['fta']) * sc,
                         tot=b['h']['pts'] + b['a']['pts'], mar=b['h']['pts'] - b['a']['pts']))
    except Exception:
        pass
X = pd.DataFrame(rows)
X = X[X.season.isin([f'E{y}' for y in range(2017, 2026)])].reset_index(drop=True)
NAMES = {c: n for r in REF.values() for c, n in r['refs']}
P(f'ματς με 3 διαιτητες και box: {len(X)} (2017-2025) · διαιτητες: {len(set(X.r1) | set(X.r2) | set(X.r3))} · μεσες βολες/ματς {X.fta.mean():.1f} (sd {X.fta.std():.1f}) · φαουλ {X.pf.mean():.1f}')
# ---- ridge: y = σεζον + ομαδα-σεζον(γηπ) + ομαδα-σεζον(φιλ) + διαιτητες ----
def fit(df, y, lam_ref=10.0, lam_team=5.0, home_dir=False):
    """home_dir=False: συνολο (ιδια φορα για γηπ/φιλ) · True: διαφορα (γηπ − φιλ, ομαδα = δυναμη ελκυσης βολων)"""
    ts = sorted(set(df.season + '|' + df.home) | set(df.season + '|' + df.away)); ti = {t: i for i, t in enumerate(ts)}
    rf = sorted(set(df.r1) | set(df.r2) | set(df.r3)); ri = {r: i for i, r in enumerate(rf)}
    ss = sorted(set(df.season)); si = {s: i for i, s in enumerate(ss)}
    n, nt, nr, ns = len(df), len(ts), len(rf), len(ss)
    A = np.zeros((n + nt + nr, ns + nt + nr)); b = np.zeros(n + nt + nr); r_ = np.arange(n)
    A[r_, [si[s] for s in df.season]] = 1
    A[r_, ns + np.array([ti[s + '|' + h] for s, h in zip(df.season, df.home)])] += 1
    A[r_, ns + np.array([ti[s + '|' + a] for s, a in zip(df.season, df.away)])] += (-1 if home_dir else 1)
    for c in ('r1', 'r2', 'r3'): A[r_, ns + nt + np.array([ri[x] for x in df[c]])] += 1
    b[:n] = df[y].values
    A[n + np.arange(nt), ns + np.arange(nt)] = math.sqrt(lam_team); A[n + nt + np.arange(nr), ns + nt + np.arange(nr)] = math.sqrt(lam_ref)
    x = np.linalg.lstsq(A, b, rcond=None)[0]
    return {r: x[ns + nt + i] for r, i in ri.items()}
CNT = pd.concat([X.r1, X.r2, X.r3]).value_counts()
def crew(df, eff): return np.array([eff.get(a, 0) + eff.get(b, 0) + eff.get(c, 0) for a, b, c in zip(df.r1, df.r2, df.r3)])
# ---- 1+2. βολες/φαουλ: ολο το δειγμα + LOSO σταθεροτητα ----
SEAS9 = [f'E{y}' for y in range(2017, 2026)]
for y, lab, hd in (('fta', 'ΒΟΛΕΣ (FTA, 2 ομαδες, ανα 40′)', False), ('pf', 'ΦΑΟΥΛ (2 ομαδες)', False), ('ftad', 'ΕΥΝΟΙΑ ΕΔΡΑΣ: βολες γηπ − φιλ', True)):
    P(''); P(f'=== {lab} ===')
    eff = fit(X, y, home_dir=hd)
    big = {r: v for r, v in eff.items() if CNT.get(r, 0) >= 60}
    vals = np.array(list(big.values()))
    P(f'  ολο το δειγμα: διαιτητες με ≥60 ματς: {len(big)} · διασπορα επιδρασης ενος διαιτητη {vals.std():.2f} · τριαδας (≈√3×) {vals.std() * math.sqrt(3):.2f}')
    srt = sorted(big.items(), key=lambda kv: kv[1])
    P('  λιγοτερα: ' + ' · '.join(f'{NAMES.get(r, r)[:16]} {v:+.2f} ({CNT[r]})' for r, v in srt[:4]))
    P('  περισσοτερα: ' + ' · '.join(f'{NAMES.get(r, r)[:16]} {v:+.2f} ({CNT[r]})' for r, v in srt[-4:]))
    # LOSO: επιδραση απο τις αλλες σεζον → προβλεψη τριαδας στη νεα σεζον· κατι «αληθινο» => κλιση ~ 1
    sl, allp, ally = [], [], []
    for Y in SEAS9:
        tr, te = X[X.season != Y], X[X.season == Y]
        if len(te) < 50: continue
        e = fit(tr, y, home_dir=hd); pr = crew(te, e)
        base = fit(te.assign(r1='x', r2='y', r3='z'), y, home_dir=hd)     # μονο ομαδες/σεζον (ψευτο-διαιτητες)
        # υπολοιπο της νεας σεζον χωρις διαιτητες: ξαναφτιαχνουμε με ομαδες μονο
        ts_eff = te[y].values - (te[y].mean() if not hd else te[y].mean())
        res = te[y].values - pd.Series(te[y].values).groupby((te.home + '|' + te.away).values).transform('mean').values * 0
        # καθαρο: παλινδρομηση του y στη προβλεψη τριαδας + σταθερα ανα ομαδα (δυο fixed effects) → απλουστευση: αφαιρουμε μεσους ομαδων
        mh = te.groupby('home')[y].transform('mean'); ma = te.groupby('away')[y].transform('mean')
        yr = te[y].values - mh.values - ma.values + te[y].mean()
        b_ = np.polyfit(pr, yr, 1)[0]; r_ = yr - np.polyval(np.polyfit(pr, yr, 1), pr)
        se = math.sqrt(np.sum(r_ ** 2) / (len(pr) - 2) / np.sum((pr - pr.mean()) ** 2))
        sl.append((Y, b_, b_ / se, pr.std())); allp += list(pr); ally += list(yr)
    allp, ally = np.array(allp), np.array(ally)
    cf = np.polyfit(allp, ally, 1); rr = ally - np.polyval(cf, allp); se = math.sqrt(np.sum(rr ** 2) / (len(allp) - 2) / np.sum((allp - allp.mean()) ** 2))
    pos = sum(1 for s in sl if s[1] > 0)
    P(f'  (α) ΣΤΑΘΕΡΟΤΗΤΑ (LOSO): κλιση {cf[0]:+.2f} (t {cf[0]/se:+.1f}) · θετικη {pos}/{len(sl)} σεζον · [' + ' '.join(f'{s[0][-2:]}:{s[1]:+.2f}' for s in sl) + ']'
      + f' · διασπορα προβλεψης τριαδας {allp.std():.2f}' + ('   ← ΠΕΡΝΑ (α)' if cf[0] / se >= 2 and pos >= 0.8 * len(sl) else '   ✗'))
# ---- 3+4. ΠΟΝΤΟΙ απεναντι σε αγορα/μοντελο (E2021-25) ----
P(''); P('=== 3. ΠΟΝΤΟΙ (E2021-25, LOSO προβλεψη τριαδας απο τις ΑΛΛΕΣ σεζον 2017-25) ===')
MK = {}
for p in REC[21]:
    if p in REC[23]:
        MK[D.key.values[p]] = dict(mo=REC[21][p]['ser'][0][1], mc=REC[21][p]['ser'][-1][1], to=REC[23][p]['ser'][0][1], tc=REC[23][p]['ser'][-1][1],
                                   hm=PR.get(key(p), {}).get('h_new', np.nan), tm=PR.get(key(p), {}).get('t_new', np.nan), p=p)
Z = X[X.key.isin(MK)].copy()
for c in ('mo', 'mc', 'to', 'tc', 'hm', 'tm', 'p'): Z[c] = [MK[k][c] for k in Z.key]
Z['cf'] = np.nan; Z['cd'] = np.nan
for Y in SE5:
    tr = X[X.season != Y]; m = Z.season == Y
    Z.loc[m, 'cf'] = crew(Z[m], fit(tr, 'fta')); Z.loc[m, 'cd'] = crew(Z[m], fit(tr, 'ftad', home_dir=True))
def rg(yc, xc, lab):
    m = Z[[yc, xc, 'season']].dropna()
    cf = np.polyfit(m[xc], m[yc], 1); r_ = m[yc] - np.polyval(cf, m[xc]); se = math.sqrt(np.sum(r_ ** 2) / (len(m) - 2) / np.sum((m[xc] - m[xc].mean()) ** 2))
    per = [np.polyfit(m[m.season == Y][xc], m[m.season == Y][yc], 1)[0] for Y in SE5]
    P(f'  {lab:56s} κλιση {cf[0]:+.3f} π. ανα βολη τριαδας (t {cf[0]/se:+.1f}) · ιδια φορα {sum(np.sign(p) == np.sign(cf[0]) for p in per)}/5 · [' + ' '.join(f'{p:+.2f}' for p in per) + ']')
Z['rt_c'] = Z.tot - Z.tc; Z['rt_o'] = Z.tot - Z.to; Z['rt_m'] = Z.tot - Z.tm
Z['rm_c'] = Z.mar - Z.mc; Z['rm_o'] = Z.mar - Z.mo; Z['rm_m'] = Z.mar - Z.hm
P(f'  διασπορα προβλεψης τριαδας (βολες): {Z.cf.std():.2f} · (ευνοια εδρας): {Z.cd.std():.2f}')
rg('fta', 'cf', 'ΕΛΕΓΧΟΣ: βολες (πραγματικες) ~ προβλεψη τριαδας')
rg('rt_m', 'cf', 'ΣΥΝΟΛΟ − ΜΟΝΤΕΛΟ ~ βολες τριαδας')
rg('rt_o', 'cf', 'ΣΥΝΟΛΟ − ΑΓΟΡΑ (ανοιγμα) ~ βολες τριαδας')
rg('rt_c', 'cf', 'ΣΥΝΟΛΟ − ΑΓΟΡΑ (κλεισιμο) ~ βολες τριαδας')
Z['mv_t'] = Z.tc - Z.to
rg('mv_t', 'cf', 'ΚΙΝΗΣΗ αγορας ανοιγμα→κλεισιμο ~ βολες τριαδας')
rg('rm_m', 'cd', 'ΔΙΑΦΟΡΑ − ΜΟΝΤΕΛΟ ~ ευνοια εδρας τριαδας')
rg('rm_c', 'cd', 'ΔΙΑΦΟΡΑ − ΑΓΟΡΑ (κλεισιμο) ~ ευνοια εδρας τριαδας')
P('  ανα πεμπτημοριο προβλεψης βολων τριαδας: συνολο − μοντελο / − αγορα κλεισ.')
Z['q'] = pd.qcut(Z.cf, 5, labels=False)
for q in range(5):
    x = Z[Z.q == q]; P(f'    Q{q + 1} (τριαδα {x.cf.mean():+.1f} βολες): n {len(x)} · βολες {x.fta.mean():.1f} · συνολο−μοντ. {x.rt_m.mean():+.2f} · −αγορα {x.rt_c.mean():+.2f}')
open('el_referee_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
Z.to_csv('el_referee_games.csv', index=False)
