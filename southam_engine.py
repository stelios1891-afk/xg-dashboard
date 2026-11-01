"""
southam_engine.py — 5/10/2026 (Στελιος: Βραζιλια & MLS με ΟΛΟΥΣ τους μηχανισμους). Η ΜΗΧΑΝΗ.
Ιδια λογικη με τη live εγχωρια (dashboard/build_data.league_ratings + picks):
  inputs: συμπιεση xG σουτ + πεναλτι 0.25 + κοκκινες + rescale ανα λιγκα-σεζον (οπως build_inputs_5s / expansion_test)
  ratings (Ax,Dx,SF,SA): ραμπα blend xG/γκολ (picks.blend_at), decay 0.96
  warm-start: ΠΕΡΣΙΝΟ flat prior · βαρος φετινου n/(n+8) · νεοφωτιστες/νεες ομαδες = μεσος λιγκας × PROMO_POOLED (καμια 2η κατηγορια)
  SoS 0.75 στα φετινα ΠΡΙΝ τη μιξη (n 6-13) · χαρακας λιγκας ραμπα περσινος→φετινος (KN 20)
  εδρα: hf = sqrt(home/away xG) απο τις ΑΛΛΕΣ σεζον (LOSO) · Dixon-Coles ρ −0.03 (picks.score_matrix_dom)
Σεζον χωρις περσινο xG (Βραζιλια 2023, MLS 2021): ολες οι ομαδες ξεκινουν απο τον μεσο ορο (flag noprior).
Παραλλαγες: base · nosos (χωρις SoS) · insea (χωρις περσινο, μονο φετινα, n≥6) · noblend (σκετο xG, χωρις γκολ).
Εξοδος: southam_preds.csv (μια γραμμη/ματς, ΟΛΕΣ οι αγωνιστικες, προ-αγωνα).
"""
import json, os, sys
from datetime import datetime
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'dashboard')
import picks
import build_data as BD

FILES = {'Brazil': {'2023': 'data_Brazil_2023.json', '2024': 'data_Brazil_2024.json',
                    '2025': 'data_Brazil_2025.json', '2026': 'data_Brazil_2026.json'},
         'MLS': {'2021': 'data_MLS_2021.json', '2022': 'data_MLS_2022.json', '2023': 'data_MLS_2023.json',
                 '2024': 'data_MLS_2024.json', '2025': 'data_MLS_2025.json', '2026': 'data_MLS_2026.json'}}
K = BD.K_WARM; KN = BD.KN_NORM

def wcomp(xg):
    if xg <= 0.2: return 1.00
    if xg <= 0.4: return 0.45
    if xg <= 0.5: return 0.25
    if xg <= 0.7: return 0.15
    return 0.05

def kodt(s):
    return datetime.strptime(s.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')

rows = []; id2name = {}
for lg, ss in FILES.items():
    for sea, path in ss.items():
        d = json.load(open(path, encoding='utf-8'))
        for mid, m in d.items():
            if m.get('hs') is None or not m.get('shots'): continue
            hid, aid = int(m['home']['id']), int(m['away']['id'])
            id2name[hid] = m['home']['name']; id2name[aid] = m['away']['name']
            agg = {hid: dict(np_raw=0., np_comp=0., pen=0, ns=0), aid: dict(np_raw=0., np_comp=0., pen=0, ns=0)}
            for s in m['shots']:
                xg = s.get('xg'); t = s.get('tid')
                if xg is None or t not in agg: continue
                if s.get('sit') == 'Penalty': agg[t]['pen'] += 1
                else:
                    agg[t]['np_raw'] += xg; agg[t]['np_comp'] += xg * wcomp(xg); agg[t]['ns'] += 1
            dh = da = 0.
            for r in m.get('reds') or []:
                dur = max(0, 95 - (r.get('min') or 0))
                if r.get('home'): dh += dur
                else: da += dur
            ko = kodt(m['date'])
            for ih, t, o, gf, ds, do in ((1, hid, aid, m['hs'], dh, da), (0, aid, hid, m['as'], da, dh)):
                a = agg[t]
                rows.append(dict(league=lg, season=sea, mid=str(mid), ko=ko, team=t, opp=o, is_home=ih, gf=int(gf),
                                 np_raw=a['np_raw'], np_comp=a['np_comp'], pen=a['pen'], ns=a['ns'],
                                 red_xg=0.0083 * do - 0.5 * 0.0083 * ds, stage=m.get('stage') or 'regular'))
df = pd.DataFrame(rows)
df['sc'] = df.np_comp
for (lg, sea), g in df.groupby(['league', 'season']):
    k = (df.league == lg) & (df.season == sea); df.loc[k, 'sc'] = df.loc[k, 'np_comp'] * g.np_raw.sum() / g.np_comp.sum()
df['xg'] = df.sc + 0.25 * df.pen + df.red_xg
df['nse'] = df.ns + df.pen + df.red_xg.abs() / 0.10
MM = []
for (lg, sea, mid), g in df.groupby(['league', 'season', 'mid'], sort=False):
    if len(g) != 2: continue
    h = g[g.is_home == 1].iloc[0]; a = g[g.is_home == 0].iloc[0]
    MM.append(dict(league=lg, season=sea, mid=mid, ko=h.ko, date=h.ko.strftime('%Y-%m-%d'), stage=h.stage,
                   home=int(h.team), away=int(a.team), hg=int(h.gf), ag=int(a.gf),
                   h_xg=h.xg, a_xg=a.xg, h_ns=h.nse, a_ns=a.nse, h_npx=h.np_raw, a_npx=a.np_raw))
M = pd.DataFrame(MM).sort_values(['league', 'season', 'ko', 'mid']).reset_index(drop=True)

# εδρα LOSO
ratio = {(lg, s): G.h_xg.sum() / G.a_xg.sum() for (lg, s), G in M.groupby(['league', 'season'])}
HF = {}
for (lg, s) in ratio:
    o = [ratio[k] for k in ratio if k[0] == lg and k[1] != s]
    HF[(lg, s)] = float(np.sqrt(np.mean(o)))

def add(hist, tid, opp, sf, xf, sa, xa, gf, ga):
    h = hist.setdefault(tid, dict(sf=[], xf=[], sa=[], xa=[], gf=[], ga=[], opp=[]))
    for k, v in (('sf', sf), ('xf', xf), ('sa', sa), ('xa', xa), ('gf', gf), ('ga', ga), ('opp', opp)):
        h[k].append(v)

def season_hist(G):
    hist = {}
    for _, r in G.iterrows():
        add(hist, r.home, r.away, r.h_ns, r.h_xg, r.a_ns, r.a_xg, r.hg, r.ag)
        add(hist, r.away, r.home, r.a_ns, r.a_xg, r.h_ns, r.h_xg, r.ag, r.hg)
    ns = pd.concat([G.h_ns, G.a_ns]); xg = pd.concat([G.h_xg, G.a_xg])
    return hist, ns.mean(), xg.sum() / ns.sum()

def rating(h, n=None, noblend=False):
    if noblend:
        sf = picks.wmean(h['sf']); sa = picks.wmean(h['sa'])
        return (picks.wmean(h['xf']) / max(sf, 1e-9), picks.wmean(h['xa']) / max(sa, 1e-9), sf, sa)
    return BD._rating(h, n)

def lam(rh, ra, lgs, lgx, hf):
    p = BD._predict_ratings(rh, ra, lgs, lgx, hf)
    return p['home_adj_xg'], p['away_adj_xg']

seasons = {lg: list(ss) for lg, ss in FILES.items()}
out = []
for lg in FILES:
    for i, sea in enumerate(seasons[lg]):
        G = M[(M.league == lg) & (M.season == sea)].reset_index(drop=True)
        hf = HF[(lg, sea)]
        prev = seasons[lg][i - 1] if i > 0 else None
        if prev:
            hp, lgs0, lgx0 = season_hist(M[(M.league == lg) & (M.season == prev)])
            hp = BD.flatten_warmstart(hp, lg)
        else:
            hp, lgs0, lgx0 = {}, None, None
        teams = set(G.home) | set(G.away)
        cur_ns_all = pd.concat([G.h_ns, G.a_ns]).mean(); cur_x_all = pd.concat([G.h_xg, G.a_xg]).sum() / pd.concat([G.h_ns, G.a_ns]).sum()
        if lgs0 is None:                       # χωρις περσινο: ο «περσινος» χαρακας = ολης της σεζον (μονο για αρχικο σημειο)
            lgs0, lgx0 = cur_ns_all, cur_x_all
        newc = [t for t in teams if t not in hp]
        lgX = lgs0 * lgx0; c = BD.PROMO_POOLED if prev else dict(xf=1, xa=1, sf=1, sa=1)
        for t in newc:
            hp[t] = {k: [v] * 8 for k, v in dict(sf=lgs0 * c['sf'], xf=lgX * c['xf'], sa=lgs0 * c['sa'], xa=lgX * c['xa'],
                                                  gf=lgX * c['xf'], ga=lgX * c['xa']).items()}
        prior = {t: BD._rating(h) for t, h in hp.items() if t in teams}
        hc = {}; cns = cx = 0.; cnt = 0
        for _, r in G.iterrows():
            H, A = r.home, r.away
            nc = cnt
            if nc:
                wn = nc / (nc + KN); lgs = lgs0 * ((cns / cnt) / lgs0) ** wn; lgx = lgx0 * ((cx / cns) / lgx0) ** wn
            else:
                lgs, lgx = lgs0, lgx0
            nh = len(hc.get(H, {}).get('sf', [])); na = len(hc.get(A, {}).get('sf', []))
            # blended (χωρις SoS) για ολη τη λιγκα — χρειαζεται για αντιπαλους SoS
            bl = {}
            for t in teams:
                h = hc.get(t); n = len(h['sf']) if h else 0
                bl[t] = prior[t] if n == 0 else BD._shrink(rating(h, n), prior[t], n, K)
            def sos_r(t):
                h = hc.get(t); n = len(h['sf']) if h else 0
                if not (picks.SOS_MIN_N <= n <= picks.SOS_MAX_N): return bl[t]
                rc = picks.sos_adjust(rating(h, n), h['opp'], bl, lgs, lgx)
                return BD._shrink(rc, prior[t], n, K)
            rec = dict(league=lg, season=sea, mid=r.mid, ko=r.ko, date=r.date, stage=r.stage, home=H, away=A,
                       home_name=id2name.get(H), away_name=id2name.get(A), hg=r.hg, ag=r.ag, n_h=nh, n_a=na,
                       h_xg_act=r.h_xg, a_xg_act=r.a_xg, hf=hf, noprior=prev is None,
                       newc_h=H in newc, newc_a=A in newc)
            rec['lh_base'], rec['la_base'] = lam(sos_r(H), sos_r(A), lgs, lgx, hf)
            rec['lh_nosos'], rec['la_nosos'] = lam(bl[H], bl[A], lgs, lgx, hf)
            if nh >= 6 and na >= 6:
                rec['lh_insea'], rec['la_insea'] = lam(rating(hc[H], nh), rating(hc[A], na), cns / cnt, cx / cns, hf)
                rn = lambda t, n: BD._shrink(rating(hc[t], n, True), prior[t], n, K)
                rec['lh_noblend'], rec['la_noblend'] = lam(rn(H, nh), rn(A, na), lgs, lgx, hf)
            out.append(rec)
            add(hc, H, A, r.h_ns, r.h_xg, r.a_ns, r.a_xg, r.hg, r.ag)
            add(hc, A, H, r.a_ns, r.a_xg, r.h_ns, r.h_xg, r.ag, r.hg)
            cns += r.h_ns + r.a_ns; cx += r.h_xg + r.a_xg; cnt += 2
P = pd.DataFrame(out)
P['md'] = np.minimum(P.n_h, P.n_a) + 1
P.to_csv('southam_preds.csv', index=False)
print(f'southam_preds.csv: {len(P)} ματς')
for (lg, s), g in P.groupby(['league', 'season']):
    print(f'  {lg:6s} {s}: n{len(g):4d} · hf {HF[(lg, s)]:.3f} (φετινη αναλογια {ratio[(lg, s)]:.3f}) · '
          f'γκολ/ματς {(g.hg + g.ag).mean():.2f} · μοντελο {(g.lh_base + g.la_base).mean():.2f} · '
          f'διαφορα γηπ πραγμ {(g.hg - g.ag).mean():+.2f} / μοντελο {(g.lh_base - g.la_base).mean():+.2f} · νεες ομαδες {int(g.newc_h.sum() and len(set(g.home[g.newc_h])))}{" · ΧΩΡΙΣ περσινο" if g.noprior.iloc[0] else ""}')
