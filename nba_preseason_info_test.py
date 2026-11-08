# -*- coding: utf-8 -*-
"""nba_preseason_info_test.py — NBA: ΓΝΩΜΗ ΕΙΔΙΚΩΝ, ΑΠΟΔΟΣΕΙΣ, ΦΙΛΙΚΑ στην αφετηρια (6/10/2026, Στελιος «ας μην βγαζουμε γρηγορα συμπερασματα,
ειδικα στο NBA η πληροφορια ειναι πιο ευκολη»). Ιδια λογικη με το EuroCup (ec_expert_test / ec_carry_test).
ΒΑΣΗ = καλυτερη μηχανη ομαδων χωρις ματια στο μελλον (nba_base_grid3: V0|W1 — ρόστερ πρεμιερας, περσι .8, K 12, beta 1, εδρα 2, HL 60, τυχη .75).
ΠΗΓΕΣ (ολες ΠΡΙΝ την πρεμιερα, 2021-22…2025-26):
  W  ορια νικων (win totals, Basketball-Reference)               → z μεσα στη σεζον
  T  αποδοση πρωταθλητη (−ln δεκαδικης)                         → z
  R  κατατάξεις ειδικων (NBA.com, ESPN, CBS, B/R, Ringer, NBC — μονο τελικες πριν την πρεμιερα) → Φ⁻¹(1 − (θεση − .5)/30), μεσος πηγων
  C  ΣΥΝΑΙΝΕΣΗ = μεσος των W/T/R
  P  φιλικα προετοιμασιας: r = Σ[+/− − (περσινη διαφορα ανα ματς ομαδας − αντιπαλου)]/(n + 4), μονο αντιπαλοι NBA
ΜΗΧΑΝΙΣΜΟΣ: αφετηρια += κ·z ποντοι/100 κατοχες (μισο επιθεση, μισο αμυνα) — σβηνει μονη της με τα ματς (K 12). κ {0,1,2,3,4,6} (P: {0,.25,.5,1}).
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): για καθε πηγη, LOSO (κ απο τις ΑΛΛΕΣ 4 σεζον, ελαχιστο RMSE Οκτ-Δεκ) → ΠΕΡΝΑ αν RMSE Οκτ-Δεκ καλυτερο απο τη
  βαση σε ≥4/5 σεζον. Μετα: «ΓΝΩΣΗ ΠΟΥ ΔΕΝ ΕΧΕΙ Η ΑΓΟΡΑ» = Κ2 vs κλεισιμο Οκτ-Δεκ b ≥ .15 & t ≥ 2 & θετικο ≥4/5.
  ROI (αναφορα, καθαρο): μοντελο ≥5%/≥8% και μιξη 50/50 ≥6%, ανοιγμα & κλεισιμο Crown, Οκτ-Δεκ και ολη η σεζον.
Εξοδος: nba_preseason_info_out.txt"""
import sys, os, json, math, collections
import numpy as np
from multiprocessing import Pool
VAR_F = 'nba_preseason_info_variants.json'
BASEV = 'V0|W1'
def _init():
    import nba_base_core as C
    R2 = C._radj2(); V = json.load(open(VAR_F, encoding='utf-8'))
    for k, d in V.items():
        R2[k] = {kk: R2[BASEV].get(kk, 0.0) + vv for kk, vv in d.items()}
        for kk, vv in R2[BASEV].items(): R2[k].setdefault(kk, vv)
def _job(cfg):
    import nba_base_core as C
    return cfg['radj'], C.run2(**cfg)
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import nba_base_core as C
    from statistics import NormalDist
    nd = NormalDist()
    out = []
    def P(s=''): print(s, flush=True); out.append(str(s))
    G, IDX, ACT, SE = C.G, C.IDX, C.ACT, C.SE
    EV = [int(s) for s in C.EVAL]
    P(f'σεζον-τεστ {EV}')
    # ---------- πηγες → z ανα (σεζον, ομαδα) ----------
    lab = lambda y: f'{y - 1}-{str(y)[2:]}'
    O = json.load(open('nba_preseason_odds.json', encoding='utf-8'))['seasons']
    RK = json.load(open('nba_power_rankings.json', encoding='utf-8'))['sources']
    PG = json.load(open('nba_preseason_games.json', encoding='utf-8'))['seasons']
    Z = {k: {} for k in 'WTRCP'}
    def zs(d):
        v = np.array(list(d.values()), float); m, s = v.mean(), v.std()
        return {t: (x - m) / s for t, x in d.items()} if s > 0 else {}
    used = collections.defaultdict(list)
    for y in EV:
        L = lab(y); teams = O.get(L, {}).get('teams', {})
        Z['W'].update({(y, t): z for t, z in zs({t: v['win_total'] for t, v in teams.items() if v.get('win_total') is not None}).items()})
        Z['T'].update({(y, t): z for t, z in zs({t: -math.log(v['title_odds_decimal']) for t, v in teams.items() if v.get('title_odds_decimal')}).items()})
        acc = collections.defaultdict(list)
        for src, ss in RK.items():
            r = ss.get(L)
            if not r or r.get('kind', '') != 'preseason_final' or len(r.get('ranking', [])) < 30: continue
            used[y].append(src)
            for i, t in enumerate(r['ranking'], 1): acc[t].append(nd.inv_cdf(1 - (i - .5) / 30))
        Z['R'].update({(y, t): float(np.mean(v)) for t, v in acc.items()})
        for t in set(teams) | set(acc):
            zz = [Z[k][(y, t)] for k in 'WTR' if (y, t) in Z[k]]
            if zz: Z['C'][(y, t)] = float(np.mean(zz))
        # φιλικα: περσινη διαφορα ανα ματς (κανονικη)
        prev = G[G.season == y - 1]
        pd_ = collections.defaultdict(list)
        for r in prev.itertuples():
            pd_[r.home].append(r.hs - r.as_); pd_[r.away].append(r.as_ - r.hs)
        Rp = {t: float(np.mean(v)) for t, v in pd_.items()}
        res = collections.defaultdict(list)
        for r in PG.get(L, {}).get('rows', []):
            if not (r.get('team_is_nba') and r.get('opp_is_nba')): continue
            me, op = r['team'], r.get('opp')
            if me not in Rp or op not in Rp: continue
            res[me].append(float(np.clip(r['plus_minus'], -30, 30)) - (Rp[me] - Rp[op]))
        Z['P'].update({(y, t): sum(v) / (len(v) + 4) for t, v in res.items()})
    for y in EV:
        P(f'  {lab(y)}: W {sum(1 for k in Z["W"] if k[0] == y)} · T {sum(1 for k in Z["T"] if k[0] == y)} · R {sum(1 for k in Z["R"] if k[0] == y)} ({", ".join(used[y])}) · '
          f'P {sum(1 for k in Z["P"] if k[0] == y)} (sd {np.std([v for k, v in Z["P"].items() if k[0] == y]):.1f})')
    for a in 'WTR':
        for b in 'WTR':
            if a < b:
                ks = [k for k in Z[a] if k in Z[b]]
                P(f'  συσχετιση {a}-{b}: {np.corrcoef([Z[a][k] for k in ks], [Z[b][k] for k in ks])[0, 1]:+.2f}')
    # ---------- εκδοχες ----------
    # 6/10 ΕΠΕΚΤΑΣΗ μετα το 1ο τρεξιμο (η επιλογη ηταν στο ακρο κ=1 → δοκιμη και μικροτερων· nba_preseason_info_out_v1.txt = 1ο τρεξιμο)
    KS = {'W': (.25, .5, .75, 1, 2), 'T': (.25, .5, .75, 1, 2), 'R': (.25, .5, .75, 1, 2), 'C': (.25, .5, .75, 1, 2), 'P': (.1, .25, .5)}
    V = {}
    for src, ks in KS.items():
        for k in ks:
            V[f'{src}|{k}'] = {f'{y}|{t}': k * z for (y, t), z in Z[src].items()}
    for kc in (.5, 1):
        for kp in (.1, .25):
            d = {f'{y}|{t}': kc * z for (y, t), z in Z['C'].items()}
            for (y, t), z in Z['P'].items(): d[f'{y}|{t}'] = d.get(f'{y}|{t}', 0.0) + kp * z
            V[f'CP|{kc}|{kp}'] = d
    json.dump(V, open(VAR_F, 'w', encoding='utf-8'))
    base_cfg = dict(h=2.0, lam=12, HL=60, carry=0.8, lw=0.75, beta=1.0)
    cfgs = [dict(base_cfg, radj=BASEV)] + [dict(base_cfg, radj=k) for k in V]
    PRED = {}
    with Pool(12, initializer=_init) as pool:
        for j, (k, pr) in enumerate(pool.imap_unordered(_job, cfgs)):
            PRED[k] = pr
            if (j + 1) % 10 == 0: print(f'  {j + 1}/{len(cfgs)}', flush=True)
    # ---------- αγορα: ανοιγμα & κλεισιμο Crown ----------
    import pandas as pd
    ODD = {}
    for ln in open('nowgoal_nba/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['t'] == 21: ODD[r['ngid']] = sorted([x for x in r['rows'] if x[4] == 2 and x[1] is not None and x[2] and x[3]], key=lambda x: x[0])
    keyd = {}
    for i, r in G.iterrows(): keyd.setdefault((r.season, int(r.hs), int(r.as_)), []).append(i)
    MKO = {}
    NGS = {'21-22': 2022, '22-23': 2023, '23-24': 2024, '24-25': 2025, '25-26': 2026}
    for sea, se in NGS.items():
        try: S = json.load(open(f'nowgoal_nba/sched_{sea}.json', encoding='utf-8'))
        except FileNotFoundError: continue
        for g in S:
            if g['hs'] is None or not ODD.get(g['ngid']): continue
            us = (pd.Timestamp(g['bj']) - pd.Timedelta(hours=8)).tz_localize('UTC').tz_convert('America/New_York').tz_localize(None).normalize()
            cand = [i for i in keyd.get((se, g['hs'], g['as_']), []) if abs((G.date[i] - us).days) <= 1]; swap = False
            if not cand: cand = [i for i in keyd.get((se, g['as_'], g['hs']), []) if abs((G.date[i] - us).days) <= 1]; swap = True
            if len(cand) != 1: continue
            def cv(x):
                L = -x[1] * (-1 if swap else 1); oh, oa = (1 + x[2], 1 + x[3]) if not swap else (1 + x[3], 1 + x[2])
                ph = (1 / oh) / (1 / oh + 1 / oa); mu = -L + C.SIG * nd.inv_cdf(min(max(ph, 1e-4), 1 - 1e-4)); return (L, mu, oh, oa)
            rows = ODD[g['ngid']]; MKO[cand[0]] = dict(o=cv(rows[0]), c=cv(rows[-1]))
    P(f'αγορα ανοιγμα/κλεισιμο: {len(MKO)} ματς')
    MON = G.date.dt.month.values; OD = np.isin(MON, [10, 11, 12]); SEAS_G = G.season.values; ACTG = (G.hs - G.as_).values.astype(float)
    def rm(p, ys, msk):
        m = np.isin(SEAS_G, ys) & msk & np.isfinite(p) & np.isin(np.arange(len(G)), IDX); return float(np.sqrt(np.mean((ACTG - p)[m] ** 2)))
    base = PRED[BASEV]
    P(''); P(f'ΒΑΣΗ: RMSE Οκτ-Δεκ {rm(base, EV, OD):.3f} · ολη {rm(base, EV, np.ones(len(G), bool)):.3f} · αγορα κλεισιμο Οκτ-Δεκ '
             f'{np.sqrt(np.mean([(ACTG[i] - MKO[i]["c"][1]) ** 2 for i in MKO if SEAS_G[i] in EV and OD[i]])):.3f}')
    P(''); P('################ LOSO ανα πηγη (κ απο τις αλλες σεζον, RMSE Οκτ-Δεκ) ################')
    fams = {'W': [k for k in V if k.startswith('W|')], 'T': [k for k in V if k.startswith('T|')], 'R': [k for k in V if k.startswith('R|')],
            'C': [k for k in V if k.startswith('C|')], 'P': [k for k in V if k.startswith('P|')], 'C+P': [k for k in V if k.startswith('CP|')]}
    NAMES = {'W': 'ορια νικων', 'T': 'αποδοση πρωταθλητη', 'R': 'κατατάξεις ειδικων', 'C': 'συναινεση W/T/R', 'P': 'φιλικα', 'C+P': 'συναινεση + φιλικα'}
    HELD = {}
    for fam, ks in fams.items():
        keys = [BASEV] + ks; held = np.full(len(G), np.nan); ch = []
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(keys, key=lambda k: rm(PRED[k], tr, OD)); ch.append(k)
            m = SEAS_G == Y; held[m] = PRED[k][m]
        HELD[fam] = held
        d = [rm(held, [Y], OD) - rm(base, [Y], OD) for Y in EV]; ok = sum(x < 0 for x in d) >= 4
        P(f'  {NAMES[fam]:22s} Οκτ-Δεκ {rm(base, EV, OD):.3f} → {rm(held, EV, OD):.3f} · ' + ' '.join(f'{x:+.3f}' for x in d) + f' → {sum(x < 0 for x in d)}/5'
          + ('  <- ΠΕΡΝΑ' if ok else '  <- ✗') + f' · ολη {rm(held, EV, np.ones(len(G), bool)):.3f} · επιλογες {[c.split("|", 1)[1] if c != BASEV else 0 for c in ch]}')
    P('  in-sample Οκτ-Δεκ ανα κ: ' + ' · '.join(f'{k}: {rm(PRED[k], EV, OD):.3f}' for k in sorted(V) if not k.startswith('CP')))
    # ---------- Κ2 & ROI ----------
    Phi = nd.cdf
    def cover(m_, L, s):
        if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
        pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
    def eval_(p, lab):
        P(f'  [{lab}]')
        for per, msk in (('Οκτ-Δεκ', OD), ('ολη', np.ones(len(G), bool))):
            ii = [i for i in MKO if SEAS_G[i] in EV and msk[i] and np.isfinite(p[i])]
            mc = np.array([MKO[i]['c'][1] for i in ii]); a = ACTG[ii]; m = p[ii]; ss = SEAS_G[ii]
            x, z = m - mc, a - mc; b = np.polyfit(x, z, 1)[0]; r_ = z - np.polyval(np.polyfit(x, z, 1), x)
            se = math.sqrt(np.sum(r_ ** 2) / (len(x) - 2) / np.sum((x - x.mean()) ** 2)); per_ = [np.polyfit(x[ss == Y], z[ss == Y], 1)[0] for Y in EV]
            cells = []
            for rl, w, thr in (('μοντελο ≥5%', 1.0, .05), ('μοντελο ≥8%', 1.0, .08), ('μιξη ≥6%', .5, .06)):
                for wh in ('o', 'c'):
                    R = []
                    for i in ii:
                        L, mk, o1, o2 = MKO[i][wh]; pw, pp, pl = cover(mk + w * (p[i] - mk), L, C.SIG)
                        e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1; s_, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
                        if e < thr: continue
                        v = (ACTG[i] + L) * s_; R.append(((od - 1) if v > 0 else (0 if v == 0 else -1), SEAS_G[i]))
                    u = np.array([q[0] for q in R]) if R else np.array([0.0]); pos = sum(1 for Y in EV if [q for q in R if q[1] == Y] and np.mean([q[0] for q in R if q[1] == Y]) > 0)
                    cells.append(f'{rl} {"ανοιγ" if wh == "o" else "κλεισ"} {u.mean()*100:+.1f}% ({len(R)}, {pos}/5)')
            P(f'    {per:8s} Κ2 b {b:+.2f} (t {b/se:+.1f}, θετ. {sum(q > 0 for q in per_)}/5)' + (' ✓' if b >= .15 and b / se >= 2 and sum(q > 0 for q in per_) >= 4 else ' ✗') + ' · ' + ' · '.join(cells))
    P(''); P('################ ΓΝΩΣΗ vs ΑΓΟΡΑ & ROI (καθαρα — κ απο τις αλλες σεζον) ################')
    eval_(base, 'ΒΑΣΗ')
    for fam in fams: eval_(HELD[fam], f'+ {NAMES[fam]}')
    open('nba_preseason_info_out.txt', 'w', encoding='utf-8').write(chr(10).join(out))
if __name__ == '__main__':
    main()
