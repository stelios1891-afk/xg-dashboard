"""
southam_tune.py — 5/10/2026 (Στελιος «ξεκινα»): ΡΥΘΜΙΖΟΜΕΝΗ μηχανη Βραζιλιας/MLS + ΚΡΙΤΗΣ (LOSO ανα σεζον).
Καθε κομματι της μηχανης ειναι παραμετρος (p) — default = ΑΚΡΙΒΩΣ η live εγχωρια (CORE7) / southam_engine.py.
Γρηγορη: τα ratings ενημερωνονται μονο για τις 2 ομαδες που επαιξαν (cache) — ιδιο αποτελεσμα με το πληρες ξαναχτισιμο.

ΚΡΙΤΗΣ (evaluate): ματς κανονικης περιοδου, αγωνιστικη ≥7. Ανα σεζον:
  LL   = log-loss 1Χ2 (Dixon-Coles ρ) πανω στα αποτελεσματα
  Sg/Sx/Sm = μεσο τετραγωνικο λαθος ΥΠΕΡΟΧΗΣ vs πραγματικα γκολ / πραγματικο xG / τελικη γραμμη αγορας (Crown)
  Tg/Tx/Tm = το ιδιο για ΣΥΝΟΛΟ γκολ
LOSO: για καθε σεζον διαλεγεται η τιμη που ειναι καλυτερη στις ΑΛΛΕΣ σεζον· μετραμε τι κανει στη σεζον που κρατηθηκε εξω.
ΚΡΙΤΗΡΙΟ (δηλωμενο πριν): αλλαγη μονο αν καλυτερη σε ≥3/4 (Βραζ) / ≥5/6 (MLS) σεζον στο κυριο μετρο ΚΑΙ ΟΧΙ χειροτερη στα αλλα.
"""
import json, sys, math
from datetime import datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks

FILES = {'Brazil': {'2023': 'data_Brazil_2023.json', '2024': 'data_Brazil_2024.json', '2025': 'data_Brazil_2025.json', '2026': 'data_Brazil_2026.json'},
         'MLS': {'2021': 'data_MLS_2021.json', '2022': 'data_MLS_2022.json', '2023': 'data_MLS_2023.json', '2024': 'data_MLS_2024.json',
                 'data_MLS_2025': None, '2025': 'data_MLS_2025.json', '2026': 'data_MLS_2026.json'}}
FILES['MLS'].pop('data_MLS_2025')
PROMO_POOLED = dict(xf=0.828, xa=1.159, sf=0.861, sa=1.134)
DEFAULT = dict(comp='std', pen=0.25, red=True, blend=0.60, ramp=True, decay=0.96, K=8.0, prior_reg=0.0, promo=PROMO_POOLED,
               KN=20.0, sos=0.75, sos_lo=6, sos_hi=13, hfa='xg', hfa_K=300, hfa_team_K=0, rho=-0.03, conv=0)

# ---------------- 1. σουτ (μια φορα) ----------------
RAW = None
def load_raw():
    global RAW
    RAW = []
    for lg, ss in FILES.items():
        for sea, path in ss.items():
            for mid, m in json.load(open(path, encoding='utf-8')).items():
                if m.get('hs') is None or not m.get('shots'): continue
                tids = {x.get('tid') for x in m['shots']}
                if int(m['home']['id']) not in tids or int(m['away']['id']) not in tids: continue      # σουτ της μιας ομαδας λειπουν = σφαλμα δεδομενων
                RAW.append((lg, sea, str(mid), datetime.strptime(m['date'].replace(' UTC', ''), '%a, %b %d, %Y, %H:%M'),
                            m.get('stage') or 'regular', int(m['home']['id']), int(m['away']['id']), int(m['hs']), int(m['as']),
                            [(s.get('tid'), s.get('xg'), s.get('sit'), s.get('min') or 0, bool(s.get('goal'))) for s in m['shots'] if s.get('xg') is not None],
                            [(r.get('home'), r.get('min') or 0) for r in (m.get('reds') or [])]))
    return RAW
CW = {'std': lambda x: 1.0 if x <= .2 else (.45 if x <= .4 else (.25 if x <= .5 else (.15 if x <= .7 else .05))),
      'none': lambda x: 1.0,
      'mild': lambda x: 1.0 if x <= .2 else (.7 if x <= .4 else (.5 if x <= .5 else (.4 if x <= .7 else .3)))}
_INP = {}
def inputs(comp='std', pen=0.25, red=True):
    """red: True = live (+0.0083 xG/λεπτο στον πλεονεκτουντα, −½ στον αλλο) · False = τιποτα · 'rev' = ΑΝΑΠΟΔΑ (αφαιρει απο τον πλεονεκτουντα)
    · 'cut' = μονο τα σουτ ΠΡΙΝ την 1η κοκκινη, αναγωγη σε 95′ · 'cutg' = το ιδιο και για τα γκολ · 'half' = σουτ μετα την κοκκινη ×0.5
    · 'drop' = ματς με κοκκινη πριν το 70′ ΔΕΝ μπαινουν στο ιστορικο ratings (μονο προβλεπονται)."""
    if RAW is None: load_raw()
    key = (comp, pen, red)
    if key in _INP: return _INP[key]
    w = CW[comp]; rows = []
    NEW = red in ('emp', 'emps', 'skrip', 'caley', 'empa')
    if NEW:
        import red_modes
    for lg, sea, mid, ko, stg, H, A, hg, ag, shots, reds in RAW:
        if NEW:
            mj = dict(home=dict(id=H), away=dict(id=A), reds=[dict(home=hm, min=mn) for hm, mn in reds],
                      shots=[dict(tid=t, xg=x, sit=si, min=mn, goal=gl) for t, x, si, mn, gl in shots])
            ADJ = red_modes.team_adj(mj, red)
        rm = min([mn for hm, mn in reds], default=None)          # λεπτο 1ης κοκκινης
        a = {H: [0., 0., 0, 0, 0], A: [0., 0., 0, 0, 0]}          # raw, comp, pens, ns, goals(πριν)
        for t, x, sit, mn, gl in shots:
            if t not in a: continue
            post = rm is not None and mn > rm
            if red in ('cut', 'cutg') and post: continue
            f = 0.5 if (red == 'half' and post) else 1.0
            if sit == 'Penalty': a[t][2] += f
            else: a[t][0] += x * f; a[t][1] += x * w(x) * f; a[t][3] += f
            if gl: a[t][4] += 1
        sc = 1.0
        if red in ('cut', 'cutg') and rm is not None:
            sc = 95.0 / max(rm, 20)
        dh = sum(max(0, 95 - mn) for hm, mn in reds if hm); da = sum(max(0, 95 - mn) for hm, mn in reds if not hm)
        if red is True: hr, ar = 0.0083 * da - 0.5 * 0.0083 * dh, 0.0083 * dh - 0.5 * 0.0083 * da
        elif red == 'rev': hr, ar = -(0.0083 * da - 0.5 * 0.0083 * dh), -(0.0083 * dh - 0.5 * 0.0083 * da)
        else: hr = ar = 0.
        hgx, agx = (a[H][4] * sc, a[A][4] * sc) if (red == 'cutg' and rm is not None) else (hg, ag)
        if NEW:
            for t in (H, A):
                a[t][0] *= ADJ[t]['fr']; a[t][1] *= ADJ[t]['fc']; a[t][3] *= ADJ[t]['fn']
            hr, ar = ADJ[H]['term'], ADJ[A]['term']
        rows.append(dict(league=lg, season=sea, mid=mid, ko=ko, stage=stg, home=H, away=A, hg=hg, ag=ag, hg_in=hgx, ag_in=agx,
                         drop=(red == 'drop' and rm is not None and rm < 70),
                         h_raw=a[H][0] * sc, h_c=a[H][1] * sc, h_pen=a[H][2] * sc, h_ns=a[H][3] * sc, a_raw=a[A][0] * sc, a_c=a[A][1] * sc, a_pen=a[A][2] * sc, a_ns=a[A][3] * sc,
                         h_red=hr, a_red=ar))
    M = pd.DataFrame(rows)
    for (lg, sea), g in M.groupby(['league', 'season']):
        k = (M.league == lg) & (M.season == sea); sf = (g.h_raw.sum() + g.a_raw.sum()) / (g.h_c.sum() + g.a_c.sum())
        M.loc[k, 'h_c'] *= sf; M.loc[k, 'a_c'] *= sf
    M['h_xg'] = M.h_c + pen * M.h_pen + M.h_red; M['a_xg'] = M.a_c + pen * M.a_pen + M.a_red
    if NEW:     # νεοι τροποι: «σουτ» με προσημο (αφαιρουμε σουτ οταν αφαιρουμε xG), ποτε κατω απο το μισο
        M['h_nse'] = np.maximum(M.h_ns + M.h_pen + M.h_red / .1, 0.5 * (M.h_ns + M.h_pen)); M['a_nse'] = np.maximum(M.a_ns + M.a_pen + M.a_red / .1, 0.5 * (M.a_ns + M.a_pen))
    else:
        M['h_nse'] = M.h_ns + M.h_pen + M.h_red.abs() / .1; M['a_nse'] = M.a_ns + M.a_pen + M.a_red.abs() / .1
    tru = {mid: (sum(x for t, x, si, mn, g in sh if t == H and si != 'Penalty') + 0.76 * sum(1 for t, x, si, mn, g in sh if t == H and si == 'Penalty'),
                 sum(x for t, x, si, mn, g in sh if t == A and si != 'Penalty') + 0.76 * sum(1 for t, x, si, mn, g in sh if t == A and si == 'Penalty'))
           for lg, sea, mid, ko, stg, H, A, hg, ag, sh, reds in RAW}
    M['h_xgraw'] = M.mid.map(lambda m: tru[m][0]); M['a_xgraw'] = M.mid.map(lambda m: tru[m][1])      # «πραγματικο xG» για τον κριτη (σταθερο)
    M = M.sort_values(['league', 'season', 'ko', 'mid']).reset_index(drop=True)
    _INP[key] = M
    return M

# ---------------- 2. μηχανη ----------------
def wmean(v, dec):
    n = len(v)
    if n == 0: return None
    w = dec ** np.arange(n - 1, -1, -1); return float((w * np.asarray(v)).sum() / w.sum())
def blend_at(n, p):
    if not p['ramp'] or n is None or n > 13: return p['blend']
    D = (1.0 - p['blend']) * 25 / 13; return 1.0 - D * n / (n + 12.0)
def rating(h, n, p):
    b = blend_at(n, p); d = p['decay']
    sf = wmean(h['sf'], d); sa = wmean(h['sa'], d)
    return ((b * wmean(h['xf'], d) + (1 - b) * wmean(h['gf'], d)) / max(sf, 1e-9),
            (b * wmean(h['xa'], d) + (1 - b) * wmean(h['ga'], d)) / max(sa, 1e-9), sf, sa)
def shrink(r, pr, n, K):
    w = n / (n + K) if (n + K) > 0 else 1.0
    return tuple(max(q, 1e-9) * (max(x, 1e-9) / max(q, 1e-9)) ** w for x, q in zip(r, pr))
def sos_adj(r, opps, bl, lgs, lgx, s):
    o = [bl[t] for t in opps if t in bl]
    if not o: return r
    mA = np.mean([x[0] for x in o]); mD = np.mean([x[1] for x in o]); mSF = np.mean([x[2] for x in o]); mSA = np.mean([x[3] for x in o])
    return (r[0] * (lgx / mD) ** s, r[1] * (lgx / mA) ** s, r[2] * (lgs / mSA) ** s, r[3] * (lgs / mSF) ** s)
def lam(rh, ra, lgs, lgx, hf):
    eh = (rh[2] / lgs) * (ra[3] / lgs) * lgs; ea = (ra[2] / lgs) * (rh[3] / lgs) * lgs
    return eh * rh[0] * ra[1] / lgx * hf, ea * ra[0] * rh[1] / lgx / hf

def run(p=None):
    p = dict(DEFAULT, **(p or {}))
    M = inputs(p['comp'], p['pen'], p['red'])
    out = []
    for lg in FILES:
        seas = list(FILES[lg]); ML = M[M.league == lg]
        ratio_x = {s: g.h_xg.sum() / g.a_xg.sum() for s, g in ML.groupby('season')}
        ratio_g = {s: g.hg.sum() / g.ag.sum() for s, g in ML.groupby('season')}
        team_home = {}                                   # για εδρα ανα ομαδα: συσσωρευμενα (xg υπερ/κατα σε εδρα & εκτος)
        for i, sea in enumerate(seas):
            G = ML[ML.season == sea]
            oth = [s for s in seas if s != sea]
            hx = math.sqrt(np.mean([ratio_x[s] for s in oth])); hg_ = math.sqrt(np.mean([ratio_g[s] for s in oth]))
            hf0 = {'xg': hx, 'goals': hg_, 'mix': math.sqrt(hx * hg_)}.get(p['hfa'], hx)
            prev = seas[i - 1] if i > 0 else None
            if prev:
                Gp = ML[ML.season == prev]; hp = {}
                for r in Gp.itertuples():
                    for t, sf, xf, sa, xa, gf, ga in (((r.home, r.h_nse, r.h_xg, r.a_nse, r.a_xg, r.hg_in, r.ag_in), (r.away, r.a_nse, r.a_xg, r.h_nse, r.h_xg, r.ag_in, r.hg_in)) if not r.drop else ()):
                        h = hp.setdefault(t, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[]))
                        for k, v in (('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga)): h[k].append(v)
                ns = pd.concat([Gp.h_nse, Gp.a_nse]); lgs0 = ns.mean(); lgx0 = pd.concat([Gp.h_xg, Gp.a_xg]).sum() / ns.sum()
                hp = {t: {k: [float(np.mean(v))] * 8 for k, v in h.items()} for t, h in hp.items()}       # flat
            else:
                ns = pd.concat([G.h_nse, G.a_nse]); lgs0 = ns.mean(); lgx0 = pd.concat([G.h_xg, G.a_xg]).sum() / ns.sum(); hp = {}
            teams = set(G.home) | set(G.away)
            c = p['promo'] if prev else dict(xf=1, xa=1, sf=1, sa=1); lgX = lgs0 * lgx0
            newc = {t for t in teams if t not in hp}
            for t in newc:
                hp[t] = {k: [v] * 8 for k, v in dict(sf=lgs0 * c['sf'], xf=lgX * c['xf'], sa=lgs0 * c['sa'], xa=lgX * c['xa'], gf=lgX * c['xf'], ga=lgX * c['xa']).items()}
            prior = {t: rating(hp[t], None, p) for t in teams}
            if p['prior_reg'] > 0:                       # περσινο προς τον μεσο (γεωμετρικα)
                mu = tuple(float(np.exp(np.mean([np.log(prior[t][j]) for t in teams]))) for j in range(4))
                prior = {t: tuple(m * (x / m) ** (1 - p['prior_reg']) for x, m in zip(prior[t], mu)) if t not in newc else prior[t] for t in teams}
            hc = {}; cns = cx = 0.; cnt = 0; bl = dict(prior); sh = sa_ = 0.; ngm = 0
            for r in G.itertuples():
                H, A = r.home, r.away
                if cnt and cns > 0 and cx > 0:
                    wn = cnt / (cnt + p['KN']); lgs = lgs0 * ((cns / cnt) / lgs0) ** wn; lgx = lgx0 * ((cx / cns) / lgx0) ** wn
                else: lgs, lgx = lgs0, lgx0
                def final(t):
                    h = hc.get(t); n = len(h['sf']) if h else 0
                    if p['sos'] and h and p['sos_lo'] <= n <= p['sos_hi']:
                        return shrink(sos_adj(rating(h, n, p), h['opp'], bl, lgs, lgx, p['sos']), prior[t], n, p['K'])
                    return bl[t]
                hf = hf0
                if p['hfa'] == 'roll' and ngm:          # κυλιομενη: φετινη αναλογια xG σπρωγμενη προς το LOSO
                    w = ngm / (ngm + p['hfa_K']); hf = hx * (math.sqrt(sh / sa_) / hx) ** w
                fh, fa = final(H), final(A)
                hfh = hf
                if p['hfa_team_K']:                     # εδρα ανα ομαδα (απο ΟΛΑ τα προηγουμενα ματς της, shrink)
                    th = team_home.get(H)
                    if th and th['nh'] >= 3 and th['na'] >= 3:
                        tr = math.sqrt(max(th['hf'] / th['nh'], .05) / max(th['af'] / th['na'], .05) * max(th['aa'] / th['na'], .05) / max(th['ha'] / th['nh'], .05))
                        m_ = min(th['nh'], th['na']); w = m_ / (m_ + p['hfa_team_K'])
                        hfh = hf * (tr / hf ** 2) ** (w / 2) if tr > 0 else hf
                lh, la = lam(fh, fa, lgs, lgx, hfh)
                nh = len(hc.get(H, {}).get('sf', [])); na = len(hc.get(A, {}).get('sf', []))
                out.append((lg, sea, r.mid, r.ko, r.stage, max(nh, na) + 1, lh, la, r.hg, r.ag, r.h_xgraw, r.a_xgraw, prev is None))
                for t, o, sf, xf, sa, xa, gf, ga in (((H, A, r.h_nse, r.h_xg, r.a_nse, r.a_xg, r.hg_in, r.ag_in), (A, H, r.a_nse, r.a_xg, r.h_nse, r.h_xg, r.ag_in, r.hg_in)) if not r.drop else ()):
                    h = hc.setdefault(t, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
                    for k, v in (('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga), ('opp', o)): h[k].append(v)
                    n = len(h['sf']); bl[t] = shrink(rating(h, n, p), prior[t], n, p['K'])
                th = team_home.setdefault(H, dict(hf=0., ha=0., af=0., aa=0., nh=0, na=0)); th['hf'] += r.h_xg; th['ha'] += r.a_xg; th['nh'] += 1
                ta = team_home.setdefault(A, dict(hf=0., ha=0., af=0., aa=0., nh=0, na=0)); ta['af'] += r.a_xg; ta['aa'] += r.h_xg; ta['na'] += 1
                cns += r.h_nse + r.a_nse; cx += r.h_xg + r.a_xg; cnt += 2; sh += r.h_xg; sa_ += r.a_xg; ngm += 1
    return pd.DataFrame(out, columns=['league', 'season', 'mid', 'ko', 'stage', 'md', 'lh', 'la', 'hg', 'ag', 'hx', 'ax', 'noprior'])

# ---------------- 3. κριτης ----------------
_MK = None
MARKET_F = 'southam_phase3_rows.csv'
def market():
    global _MK
    if _MK is None:
        try:
            R = pd.read_csv(MARKET_F, dtype={'mid': str})
        except Exception:
            _MK = pd.DataFrame(columns=['msup', 'mtot']); return _MK
        R = R[(R.win == 'close') & (R.book == 'Crown')].drop_duplicates('mid')
        _MK = R.set_index('mid')[['msup', 'mtot']]
    return _MK
_DC = {}
def probs(lh, la, rho):
    out = np.empty((len(lh), 3))
    for i, (a, b) in enumerate(zip(lh, la)):
        k = (round(a, 2), round(b, 2), rho)
        if k not in _DC:
            Pm = picks.score_matrix_dom(max(k[0], .05), max(k[1], .05), rho)
            _DC[k] = (np.tril(Pm, -1).sum(), np.trace(Pm), np.triu(Pm, 1).sum())
        out[i] = _DC[k]
    return out
def evaluate(P, rho=-0.03, conv=0, mdmin=7):
    P = P.copy()
    if conv:                                              # επιπεδο γκολ λιγκας: κυλιομενο (πραγματικα / μοντελο) των προηγουμενων conv ματς
        P = P.sort_values(['league', 'ko'])
        for lg, g in P.groupby('league'):
            ratio = ((g.hg + g.ag).shift(1).rolling(conv, min_periods=50).sum() / (g.lh + g.la).shift(1).rolling(conv, min_periods=50).sum()).fillna(1.0)
            P.loc[g.index, 'lh'] = g.lh * ratio; P.loc[g.index, 'la'] = g.la * ratio
    E = P[(P.stage == 'regular') & (P.md >= mdmin)].copy()
    pr = probs(E.lh.values, E.la.values, rho); res = np.sign(E.hg - E.ag).values
    E['LL'] = -np.log(np.clip(pr[np.arange(len(E)), np.where(res > 0, 0, np.where(res == 0, 1, 2))], 1e-9, 1))
    sup = E.lh - E.la; tot = E.lh + E.la
    E['Sg'] = (E.hg - E.ag - sup) ** 2; E['Sx'] = (E.hx - E.ax - sup) ** 2
    E['Tg'] = (E.hg + E.ag - tot) ** 2; E['Tx'] = (E.hx + E.ax - tot) ** 2
    mk = market().reindex(E.mid.values)
    E['Sm'] = (mk.msup.values - sup.values) ** 2; E['Tm'] = (mk.mtot.values - tot.values) ** 2
    return E[['league', 'season', 'mid', 'LL', 'Sg', 'Sx', 'Sm', 'Tg', 'Tx', 'Tm']]

METRICS = ['LL', 'Sg', 'Sx', 'Sm', 'Tg', 'Tx', 'Tm']
def compare(variants, base_key, title, main=('LL', 'Sx'), extra_eval=None):
    """variants: {ονομα: dict παραμετρων (για run) ή ('eval', kwargs)}. Τυπωνει πινακα Δ vs βασης ανα λιγκα/σεζον + LOSO."""
    print(f'\n{"=" * 110}\n{title}\n{"=" * 110}')
    ev = {}; cache = {}
    for nm, v in variants.items():
        rp = {k: x for k, x in v.items() if k not in ('rho', 'conv')}; ekw = {k: x for k, x in v.items() if k in ('rho', 'conv')}
        key = json.dumps(rp, sort_keys=True, default=str)
        if key not in cache: cache[key] = run(rp)
        ev[nm] = evaluate(cache[key], **ekw).set_index('mid')
    B = ev[base_key]
    for lg in ('Brazil', 'MLS'):
        b = B[B.league == lg]; seas = sorted(b.season.unique())
        print(f'\n  [{lg}] Δ απο «{base_key}» (×1000· ΑΡΝΗΤΙΚΟ = καλυτερο) — ανα μετρο: ολο το δειγμα ±SE και [σεζον καλυτερες/συνολο]')
        print(f'   {"παραλλαγη":22s} ' + ' '.join(f'{m:>17s}' for m in METRICS))
        for nm, E in ev.items():
            e = E[E.league == lg]; row = []
            for m in METRICS:
                d = (e[m] - b[m].reindex(e.index)).dropna()
                if not len(d): row.append(f'{"—":>17s}'); continue
                bs = sum(1 for s in seas if d[e.loc[d.index, 'season'] == s].mean() < 0)
                row.append(f'{1000*d.mean():+7.2f}±{1000*d.std()/np.sqrt(len(d)):4.2f}[{bs}/{len(seas)}]')
            print(f'   {nm:22s} ' + ' '.join(row))
        # LOSO στο κυριο μετρο
        for m in main:
            per = {nm: E[E.league == lg].groupby('season')[m].mean() for nm, E in ev.items()}
            cnt = {nm: E[E.league == lg].groupby('season')[m].count() for nm, E in ev.items()}
            picks_, gain = [], []
            for s in seas:
                best = min(per, key=lambda nm: sum(per[nm][o] * cnt[nm][o] for o in seas if o != s) / sum(cnt[nm][o] for o in seas if o != s))
                picks_.append(f'{s}→{best}'); gain.append(per[best][s] - per[base_key][s])
            print(f'   LOSO [{m}]: ' + ' · '.join(picks_) + f' · κερδος στη σεζον-εκτος: ' + ' '.join(f'{1000*g:+.2f}' for g in gain)
                  + f' · καλυτερο σε {sum(1 for g in gain if g < -1e-12)}/{len(gain)}')
    return ev

def split_run(p_sup, p_tot):
    """υπεροχη απο μια ρυθμιση, συνολο απο αλλη: λ = (συνολο ± υπεροχη)/2."""
    A = run(p_sup).set_index('mid'); B = run(p_tot).set_index('mid')
    s = A.lh - A.la; t = (B.lh + B.la).reindex(A.index)
    A['lh'] = ((t + s) / 2).clip(lower=.05); A['la'] = ((t - s) / 2).clip(lower=.05)
    return A.reset_index()
