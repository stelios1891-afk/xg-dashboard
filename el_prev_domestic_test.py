# -*- coding: utf-8 -*-
"""el_prev_domestic_test.py — ΠΕΡΣΙΝΑ ΕΓΧΩΡΙΑ ΣΤΗΝ ΑΦΕΤΗΡΙΑ ΤΗΣ ΕΥΡΩΛΙΓΚΑΣ (30/9/2026, αιτημα Στελιου: αγων 1-10).
Δεδομενα εγχωριων: Flashscore (fs_bk_games.json + fs_bk_stats.jsonl, 10 λιγκες 2020-21…) + Basketball-Reference για τα κενα
  (bbref_intl_box.jsonl: Τουρκια 22-23/24-25, Ισραηλ 20-21/21-22) · ΜΕ πλει-οφ · box → κατοχες + διορθωση τυχης (οπως EL).
ΕΚΔΟΧΗ Α (καλυπτει και τις νεες ομαδες): το ΤΕΛΟΣ της περσινης σεζον υπολογιζεται ΜΑΖΙ απο ματς Ευρωλιγκας + εγχωρια
  (ιδιο ridge O/D ανα 100 κατοχες, ιδια φθορα HL60, εδρα 5· εγχωριοι αντιπαλοι = δικες τους ομαδες· οι ομαδες Ευρωλιγκας
  συνδεουν τις λιγκες) με βαρος εγχωριων wd. Ταβανι διαφορας εγχωριων 28/100 (≈20 π.).
ΑΦΕΤΗΡΙΑ φετος = wt·(κοινο περσινο τελος) + 0.42·ειδικοι (οπως live) · ΣΕ ΟΛΕΣ τις εκδοχες ενεργα και τα ΦΕΤΙΝΑ εγχωρια (κ .5, ταβανι 20).
ΠΛΕΓΜΑ: wd {0, .25, .5, 1} × wt {.5, .6, .7} × τυχη εγχωριων {box, μονο σκορ}.
ΠΡΟ-ΔΗΛΩΜΕΝΟ ΚΡΙΤΗΡΙΟ: LOSO (ρυθμιση απο τις ΑΛΛΕΣ 4 σεζον, ελαχιστο RMSE αγων 1-10)· ΠΕΡΝΑ αν το εκτος-δειγματος RMSE αγων 1-10
  καλυτερο απο τη βαση (wd 0, wt .5 = live + φετινα εγχωρια) σε ≥4/5 σεζον. Επισης: ολη η σεζον, b, ROI, νεες ομαδες χωριστα.
Εξοδος: el_prev_domestic_test_out.txt"""
import sys, json, re, math, unicodedata
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
NS = {}
src = open('el_domestic_rating_test.py', encoding='utf-8').read().split("PRED = {}")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
exec(src, NS)
out = []
def P(s=''):
    print(s, flush=True); out.append(str(s))
D, SE5, EM, GN, dnum, IDX, PRC, ACT, SE, RS = (NS[k] for k in ('D', 'SE5', 'EM', 'GN', 'dnum', 'IDX', 'PRC', 'ACT', 'SE', 'RS'))
fit_eff, fit_pace, LUCK, ENDS, cfg, S20, dom_shift = (NS[k] for k in ('fit_eff', 'fit_pace', 'LUCK', 'ENDS', 'cfg', 'S20', 'dom_shift'))
D0 = pd.Timestamp(D.date.iloc[0])
def tok(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = s.replace('milano', 'milan').replace('olympiakos', 'olympiacos').replace('olimpia', 'olympia').replace('munchen', 'munich')
    return set(w for w in re.findall(r'[a-z]{3,}', s) if w not in ('basketball', 'basket', 'club', 'the', 'sport', 'bc', 'kk', 'fc', 'bk', 'sad',
                                                                   'baloncesto', 'istanbul', 'athens', 'belgrade', 'aviv', 'tel', 'kaunas', 'piraeus'))
# ---- 1. ενιαια εγχωρια ματς ----
FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
FST = {}
for ln in open('fs_bk_stats.jsonl', encoding='utf-8'):
    r = json.loads(ln); FST[r['id']] = r['stats']
BR = [json.loads(l) for l in open('bbref_intl_box.jsonl', encoding='utf-8')]
def fnum(x):
    try: return float(str(x).replace('%', ''))
    except Exception: return None
def fs_box(st, side):
    if not st: return None
    i = 0 if side == 'h' else 1
    g = lambda k: fnum(st.get(k, (None, None))[i])
    b = dict(fg3=g('3-point field goals made'), fg3a=g('3-point field goals attempts'), ft=g('Free throws made'), fta=g('Free throws attempts'),
             fga=g('Field goals attempts'), orb=g('Offensive rebounds'), tov=g('Turnovers'))
    return b if all(v is not None for v in b.values()) else None
BRI = {}
for r in BR:
    if not (r.get('v') and r.get('h')): continue
    try: hp, vp = int(r['h']['pts']), int(r['v']['pts'])
    except Exception: continue
    BRI.setdefault((r['league'], hp, vp), []).append(r)
rows = []
for key, L in FG.items():
    lg, y = key.split('_'); y = int(y)
    if y > 2025: continue
    es = f'E{y}'
    for e in L:
        try: hs, as_ = int(e['hs']), int(e['as_'])
        except Exception: continue
        st = FST.get(e['id']); hb_, ab_ = fs_box(st, 'h'), fs_box(st, 'a')
        dd = pd.Timestamp(e['ts'], unit='s').normalize()
        if hb_ is None and lg in ('TBL', 'ISR'):
            cv = lambda d_: dict(fg3=float(d_['fg3']), fg3a=float(d_['fg3a']), ft=float(d_['ft']), fta=float(d_['fta']), fga=float(d_['fga']),
                                 orb=float(d_['orb']), tov=float(d_['tov']))
            for swap in (False, True):
                cand = BRI.get((lg, as_, hs) if swap else (lg, hs, as_), [])
                r = next((r for r in cand if abs((pd.Timestamp(r['date']) - dd).days) <= 2), None)
                if r:
                    try: hb_, ab_ = (cv(r['v']), cv(r['h'])) if swap else (cv(r['h']), cv(r['v']))
                    except Exception: pass
                    break
        rows.append(dict(lg=lg, es=es, d=(dd - D0).days, home=e['home'], away=e['away'], hs=hs, as_=as_, hb=hb_, ab=ab_))
DM = pd.DataFrame(rows)
def poss(b): return b['fga'] + 0.44 * b['fta'] - b['orb'] + b['tov']
DM['okbox'] = [h is not None and a is not None and (poss(h) + poss(a)) / 2 >= 50 for h, a in zip(DM.hb, DM.ab)]
P(f'εγχωρια ματς 2020-21…2025-26: {len(DM)} · με box {DM.okbox.mean():.1%}')
for lg in sorted(DM.lg.unique()):
    P(f'  {lg}: ' + ' '.join(f'{es[-4:]}:{DM[(DM.lg == lg) & (DM.es == es)].okbox.mean():.0%}' for es in sorted(DM.es.unique())))
# κατοχες + διορθωση τυχης (ιδιος τυπος με την EL, μεσοι ορ. λιγκας-σεζον)
lw = cfg['lw']
EFF = {}
for (lg, es), g in DM.groupby(['lg', 'es']):
    bx = g[[h is not None and a is not None and (poss(h) + poss(a)) / 2 >= 50 for h, a in zip(g.hb, g.ab)]]
    p3 = (sum(b['fg3'] for b in bx.hb) + sum(b['fg3'] for b in bx.ab)) / max(1, sum(b['fg3a'] for b in bx.hb) + sum(b['fg3a'] for b in bx.ab))
    ftp = (sum(b['ft'] for b in bx.hb) + sum(b['ft'] for b in bx.ab)) / max(1, sum(b['fta'] for b in bx.hb) + sum(b['fta'] for b in bx.ab))
    pace = np.mean([(poss(h) + poss(a)) / 2 for h, a in zip(bx.hb, bx.ab)]) if len(bx) else 72.0
    for i, r in g.iterrows():
        ps = (poss(r.hb) + poss(r.ab)) / 2 if (r.hb is not None and r.ab is not None) else 0
        if ps >= 50:                                   # αλλιως «αδειο» box → μονο σκορ
            def adj(pts, b):
                p3g = b['fg3'] / b['fg3a'] if b['fg3a'] else p3; ftg = b['ft'] / b['fta'] if b['fta'] else ftp
                return pts - 3 * b['fg3'] + 3 * b['fg3a'] * (lw * p3g + (1 - lw) * p3) - b['ft'] + b['fta'] * (lw * ftg + (1 - lw) * ftp)
            EFF[i] = dict(box=(100 * adj(r.hs, r.hb) / ps, 100 * adj(r.as_, r.ab) / ps), raw=(100 * r.hs / ps, 100 * r.as_ / ps))
        else:
            EFF[i] = dict(box=(100 * r.hs / pace, 100 * r.as_ / pace), raw=(100 * r.hs / pace, 100 * r.as_ / pace))
# ---- 2. αντιστοιχιση ομαδων Ευρωλιγκας ----
NAMEMAP = {}
for es in sorted(D.season.unique()):
    sub = D[D.season == es]; el = {}
    for r in sub.itertuples(): el.setdefault(r.home, r.hname); el.setdefault(r.away, r.aname)
    dsub = DM[DM.es == es]
    names = set(dsub.home) | set(dsub.away)
    for code, nm in el.items():
        te = tok(nm); best = (0, None)
        for n in names:
            tn = tok(n)
            if not tn or not te: continue
            sc = len(te & tn) / min(len(te), len(tn)) + 0.01 * len(te & tn)
            if sc > best[0]: best = (sc, n)
        if best[0] >= 0.5: NAMEMAP[(es, best[1])] = code
P('αντιστοιχιση (ομαδα EL ← εγχωριο ονομα), δειγμα 2024: ' + ' · '.join(f'{c}←{n}' for (es, n), c in sorted(NAMEMAP.items(), key=lambda x: x[1]) if es == 'E2024'))
# ---- 3. κοινο τελος περσινης σεζον (EL + εγχωρια) ----
CAP = 28.0
def joint_end(p, wd, mode):
    """τελος σεζον p με ματς EL + εγχωρια (βαρος wd)· αφετηρια fit = οπως ENDS (0.7 × τελος p-1, μονο EL)."""
    EH, EA = LUCK[cfg['lw']]; st = ENDS[p]; prior = st['prior']
    sidx = np.where(D.season.values == p)[0]
    elteams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx]))
    dg = DM[DM.es == p] if wd > 0 else DM.iloc[0:0]
    code = lambda n: NAMEMAP.get((p, n), f'D:{n}')
    dteams = sorted({code(n) for n in set(dg.home) | set(dg.away)} - set(elteams))
    teams = elteams + dteams; ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
    o0 = np.array([0.7 * prior.get(t, (0, 0, 0))[0] for t in teams]); d0 = np.array([0.7 * prior.get(t, (0, 0, 0))[1] for t in teams])
    hi = list(D.home.values[sidx]); ai = list(D.away.values[sidx]); eh = list(EH[sidx]); ea = list(EA[sidx])
    hb = list(np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, cfg['h'] / 2)); dd = list(dnum[sidx]); ww = [1.0] * len(sidx)
    for i, r in dg.iterrows():
        a, b = EFF[i][mode]; df = a - b
        if abs(df) > CAP: a, b = a - np.sign(df) * (abs(df) - CAP) / 2, b + np.sign(df) * (abs(df) - CAP) / 2
        hi.append(code(r.home)); ai.append(code(r.away)); eh.append(a); ea.append(b); hb.append(cfg['h'] / 2); dd.append(r.d); ww.append(wd)
    dd = np.array(dd, float); w = np.array(ww) * 0.5 ** ((dd.max() - dd) / cfg['HL'])
    mu, O, Dd = fit_eff(np.array([ix[t] for t in hi]), np.array([ix[t] for t in ai]), np.array(eh), np.array(ea), np.array(hb), w, n, o0, d0, cfg['lam'], st['mu0'])
    return {t: (O[ix[t]], Dd[ix[t]]) for t in teams}
# ---- 4. EL με νεα αφετηρια (+ φετινα εγχωρια κ .5 ταβανι 20) ----
def run(wd, wt, mode, kappa=0.5):
    EH, EA = LUCK[cfg['lw']]; v = np.full(len(D), np.nan)
    for Y in SE5:
        st = ENDS[Y]; seasons = sorted(D.season.unique()); p = seasons[seasons.index(Y) - 1]
        J = joint_end(p, wd, mode)
        sidx = np.where(D.season.values == Y)[0]
        teams = sorted(set(D.home.values[sidx]) | set(D.away.values[sidx])); ix = {t: i for i, t in enumerate(teams)}; n = len(teams)
        e = np.array([EM[Y].get(t, 0.0) for t in teams]) * cfg['we']
        # νεες ομαδες (χωρις EL περσι): το ονομα τους στο περσινο εγχωριο
        for t in teams:
            if t not in J:
                nm = D[(D.season == Y) & (D.home == t)].hname.iloc[0] if (D[(D.season == Y) & (D.home == t)]).size else t
                te = tok(nm); best = (0, None)
                for k_ in J:
                    if not str(k_).startswith('D:'): continue
                    tn = tok(k_[2:])
                    if tn and te:
                        sc = len(te & tn) / min(len(te), len(tn))
                        if sc > best[0]: best = (sc, k_)
                if best[0] >= 0.5 and wd > 0: J[t] = J[best[1]]
        o0b = np.array([wt * J.get(t, (0, 0))[0] for t in teams]) + e / 2
        d0b = np.array([wt * J.get(t, (0, 0))[1] for t in teams]) - e / 2
        p0 = np.array([0.7 * st['prior'].get(t, (0, 0, 0))[2] for t in teams])
        hi = np.array([ix[t] for t in D.home.values[sidx]]); ai = np.array([ix[t] for t in D.away.values[sidx]])
        hb = np.where(D.ff.values[sidx] | D.relocated.values[sidx], 0.0, cfg['h'] / 2); dn = dnum[sidx]
        pred = np.full(len(sidx), np.nan)
        for d in np.unique(dn):
            sh = np.array([kappa * dom_shift(S20, Y, t, d) * 100 / 72 for t in teams]) if kappa else np.zeros(n)
            o0 = o0b + sh / 2; d0 = d0b - sh / 2
            past = dn < d; cur = np.where(dn == d)[0]
            if past.any():
                w = 0.5 ** ((d - dn[past]) / cfg['HL'])
                mu, O, Dd = fit_eff(hi[past], ai[past], EH[sidx][past], EA[sidx][past], hb[past], w, n, o0, d0, cfg['lam'], st['mu0'])
                pm, Pc = fit_pace(hi[past], ai[past], D.pace.values[sidx][past], w, n, p0, cfg['lam'], st['pm0'])
            else:
                mu, O, Dd, pm, Pc = st['mu0'], o0, d0, st['pm0'], p0
            hh, aa, hbb = hi[cur], ai[cur], hb[cur]
            pred[cur] = (pm + Pc[hh] + Pc[aa]) * ((mu + O[hh] + Dd[aa] + hbb) - (mu + O[aa] + Dd[hh] - hbb)) / 100
        v[sidx] = pred
    return np.where(GN >= 7, v * cfg['sf'], v)
PRED = {}
for mode in ('box', 'raw'):
    for wd in (0.0, 0.25, 0.5, 1.0):
        for wt in (0.5, 0.6, 0.7):
            if wd == 0 and mode == 'raw': PRED[(mode, wd, wt)] = PRED[('box', wd, wt)]; continue
            PRED[(mode, wd, wt)] = run(wd, wt, mode); print(f'  {mode} wd {wd} wt {wt} ετοιμο', flush=True)
ACTD = (D.hs - D.as_).values.astype(float); RSM = D.phase.values == 'RS'; SEASD = D.season.values
E10 = RSM & (GN <= 10)
def rm(v, ss, msk): m = msk & np.isin(SEASD, ss); return float(np.sqrt(np.mean((ACTD - v)[m] ** 2)))
base = PRED[('box', 0.0, 0.5)]
P('')
P('=== IN-SAMPLE (5 σεζον) RMSE αγων 1-10 / ολη ===')
for k, v in PRED.items():
    if k[0] == 'raw' and k[1] == 0: continue
    P(f'  {k[0]:3s} wd {k[1]:<4} wt {k[2]}: 1-10 {rm(v, SE5, E10):.3f} · ολη {rm(v, SE5, RSM):.3f}')
jj = np.array([j for j in range(len(IDX)) if RS[j] and not np.isnan(PRC[j, 0]) and SE[j] in SE5])
L_, OH, OA = PRC[jj, 0], PRC[jj, 1], PRC[jj, 2]; AC = ACT[jj]; SJ = SE[jj]; GJ = GN[IDX[jj]]; MK = -L_
Phi = np.vectorize(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))))
isint = np.abs(L_ - np.round(L_)) < 1e-9
def roi(v, msk, thr=0.08):
    m = v[IDX][jj]
    pw = np.where(isint, Phi((m + L_ - 0.5) / 11.5), Phi((m + L_) / 11.5)); pl = np.where(isint, Phi((-m - L_ - 0.5) / 11.5), 1 - pw); pp = 1 - pw - pl
    eh, ea = pw * OH + pp - 1, pl * OA + pp - 1
    side = np.where(eh >= ea, 1, -1); e = np.maximum(eh, ea); od = np.where(side == 1, OH, OA)
    vv = (AC + L_) * side; pr = np.where(vv > 0, od - 1, np.where(vv == 0, 0.0, -1.0)); sel = (e >= thr) & msk
    pos_ = sum(1 for s in SE5 if (sel & (SJ == s)).any() and pr[sel & (SJ == s)].mean() > 0)
    return f'{pr[sel].mean()*100:+.1f}% ({sel.sum()}) {pos_}/5'
newc = np.zeros(len(D), bool)
for Y in SE5:
    prev_teams = set(ENDS[Y]['prior'])
    m = (SEASD == Y) & ~(np.isin(D.home.values, list(prev_teams)) & np.isin(D.away.values, list(prev_teams)))
    newc |= m
for mode in ('box', 'raw'):
    keys = [k for k in PRED if k[0] == mode or k[1] == 0]
    held = np.full(len(D), np.nan); ch = []
    for Y in SE5:
        tr = [s for s in SE5 if s != Y]
        best = min(keys, key=lambda k: rm(PRED[k], tr, E10)); ch.append(best)
        held[SEASD == Y] = PRED[best][SEASD == Y]
    P('')
    P(f'=== LOSO — εγχωρια {"ΜΕ box (τυχη+κατοχες)" if mode == "box" else "ΜΟΝΟ σκορ"} ===')
    P('  επιλογες: ' + ' | '.join(f'{Y[-4:]}: wd {k[1]} wt {k[2]}' for Y, k in zip(SE5, ch)))
    for nm, msk in (('αγων 1-10', E10), ('αγων 1-10 ΝΕΕΣ ομαδες', E10 & newc), ('αγων 11+', RSM & (GN > 10)), ('ολη η σεζον', RSM)):
        if not (msk & np.isin(SEASD, SE5)).any(): continue
        diffs = [rm(held, [Y], msk) - rm(base, [Y], msk) if (msk & (SEASD == Y)).any() else 0 for Y in SE5]; w_ = sum(d < 0 for d in diffs)
        P(f'  {nm:24s}: βαση {rm(base, SE5, msk):.3f} → {rm(held, SE5, msk):.3f} · ανα σεζον ' + ' '.join(f'{d:+.3f}' for d in diffs)
          + f' → καλυτερο {w_}/5' + (f' → {"ΠΕΡΝΑ" if w_ >= 4 else "✗"}' if nm == 'αγων 1-10' else ''))
    for nm, v in (('βαση (live + φετινα εγχ.)', base), ('με περσινα εγχ. (LOSO)', held)):
        for lab, msk in (('αγων 1-10', GJ <= 10), ('ολη', np.ones(len(jj), bool))):
            b = np.polyfit((v[IDX][jj] - MK)[msk], (AC - MK)[msk], 1)[0]
            P(f'    {nm:26s} {lab:10s}: b {b:+.3f} · ROI ≥8% {roi(v, msk)} · ≥5% {roi(v, msk, 0.05)}')
open('el_prev_domestic_test_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
