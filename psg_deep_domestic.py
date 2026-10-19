# -*- coding: utf-8 -*-
"""psg_deep_domestic.py — 19/10/2026 (Στελιος: «στο πρωταθλημα δεν φορτσαρει»). Εγχωρια xG (FotMob σουτ, μονο 90λ) ανα κατασταση σκορ & rotation.
Δ1 Παρι vs αλλοι κυριαρχοι πρωταθλητες: xG/90 υπερ-κατα οταν ισοπαλια / μπροστα 1 / μπροστα 2+ / πισω · ποσο «χανει» η συνολικη xG διαφορα λογω χρονου μπροστα.
Δ2 Rotation: εγχωρια ματς ≤4 μερες ΠΡΙΝ ή ≤3 μερες ΜΕΤΑ απο ευρωπαικο vs τα υπολοιπα (xG διαφορα, διορθωση αντιπαλου).
Δ3 ΓΕΝΙΚΟ ΤΕΣΤ (ολες οι ομαδες με ευρωπαικα): προβλεπει το «κρυμμενο απο την κατασταση» (xGD ισοπαλιας − συνολικη xGD) την ευρωπαικη αποκλιση πραγμ−μοντελο;
   Και το ιδιο με το «rotation-κενο». Αν ναι → γενικος μηχανισμος· αν οχι → οχι.
Σκορ ανα λεπτο απο τα σουτ-γκολ (αυτογκολ λειπουν → χρησιμοποιουνται μονο ματς οπου τα σουτ-γκολ = τελικο σκορ)."""
import sys, json, glob, os, math
from datetime import datetime, timedelta
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
E = pd.read_pickle('psg_deep_rows.pkl')
LGS = sorted(set(E.lg.dropna()))
SEAS = ('2122', '2223', '2324', '2425', '2526')
def pdt(s):
    try: return datetime.strptime(s.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M')
    except Exception: return None
rows = []; nm = 0; ok = 0
for lg in LGS:
    for sea in SEAS:
        fn = f'data_{lg}_{sea}.json'
        if not os.path.exists(fn): continue
        for mid, m in json.load(open(fn, encoding='utf-8')).items():
            sh = [s for s in (m.get('shots') or []) if s.get('xg') is not None and s['min'] <= 90]
            if not sh or m.get('hs') is None: continue
            nm += 1; hid = int(m['home']['id'])
            gl = sorted((s['min'], 1 if int(s['tid']) == hid else -1) for s in sh if s.get('goal'))
            good = sum(1 for g in gl if g[1] == 1) == m['hs'] and sum(1 for g in gl if g[1] == -1) == m['as']
            ok += good
            # τμηματα: [0, g1], [g1, g2], ... , [gk, 90]
            bnd = [0] + [g[0] for g in gl] + [90]; st = [0]
            for g in gl: st.append(st[-1] + g[1])
            seg = {}
            for k in range(len(st)):
                seg.setdefault(st[k], 0.0); seg[st[k]] += max(bnd[k + 1] - bnd[k], 0)
            xs = {}   # κατασταση (σκοπια γηπεδουχου) → [xg υπερ γηπ, xg υπερ φιλοξ]
            for s in sh:
                # κατασταση τη στιγμη του σουτ: γκολ ΠΡΙΝ το λεπτο του (ενα γκολ-σουτ ανηκει στην κατασταση πριν απο αυτο)
                cur = sum(g[1] for g in gl if g[0] < s['min'])
                xs.setdefault(cur, [0.0, 0.0]); xs[cur][0 if int(s['tid']) == hid else 1] += s['xg']
            dt = pdt(m.get('date') or '')
            for side, tm, op in ((1, m['home']['name'], m['away']['name']), (-1, m['away']['name'], m['home']['name'])):
                H = side == 1
                d = dict(lg=lg, sea=sea, mid=mid, team=tm, opp=op, home=H, date=dt, good=good,
                         xf=sum(s['xg'] for s in sh if (int(s['tid']) == hid) == H), xa=sum(s['xg'] for s in sh if (int(s['tid']) == hid) != H),
                         gf=m['hs'] if H else m['as'], ga=m['as'] if H else m['hs'])
                for lab, cond in (('lvl', lambda c: c == 0), ('up1', lambda c: c == 1), ('up2', lambda c: c >= 2), ('dn', lambda c: c <= -1)):
                    d['t_' + lab] = sum(v for c, v in seg.items() if cond(c * side))
                    d['xf_' + lab] = sum(v[0 if H else 1] for c, v in xs.items() if cond(c * side))
                    d['xa_' + lab] = sum(v[1 if H else 0] for c, v in xs.items() if cond(c * side))
                rows.append(d)
M = pd.DataFrame(rows); M['xgd'] = M.xf - M.xa
print(f'εγχωρια ματς με σουτ: {nm} ({len(LGS)} λιγκες, {", ".join(SEAS)}) · σκορ ανασυντεθηκε σωστα (χωρις αυτογκολ) {ok / nm:.0%} → τεστ καταστασης μονο σε αυτα')
G = M[M.good]
def state_tab(y):
    o = {}
    for lab in ('lvl', 'up1', 'up2', 'dn'):
        t = y['t_' + lab].sum()
        o[lab] = (90 * y['xf_' + lab].sum() / t if t > 30 else np.nan, 90 * y['xa_' + lab].sum() / t if t > 30 else np.nan, t / len(y) / 90)
    o['all'] = (y.xf.mean(), y.xa.mean(), 1.0)
    return o
TEAMS = ['Paris Saint-Germain', 'Bayern München', 'Inter', 'Real Madrid', 'Manchester City', 'Barcelona', 'Liverpool', 'Arsenal', 'Napoli', 'Bayer Leverkusen',
         'Benfica', 'FC Porto', 'Sporting CP', 'PSV Eindhoven', 'Celtic', 'Club Brugge', 'Borussia Dortmund']
print('\n' + '=' * 130 + '\nΔ1. ΚΑΤΑΣΤΑΣΗ ΣΚΟΡ — εγχωρια 2022-26 (xG υπερ/κατα ανα 90λ σε καθε κατασταση · % χρονου)')
print(f'   {"ομαδα":22s} {"ματς":>4s} │ {"ΙΣΟΠΑΛΙΑ xGD/90":>15s} │ {"ΜΠΡΟΣΤΑ 1 xGD/90":>16s} {"(υπερ/κατα)":>11s} │ {"ΜΠΡΟΣΤΑ 2+":>10s} │ {"ΣΥΝΟΛΟ xGD":>10s} │ {"% μπροστα":>9s} │ {"κρυμμενο":>8s} │ πτωση xG-υπερ ισοπ→μπροστα1')
TS = {}
for t in TEAMS:
    y = G[(G.team == t) & G.sea.isin(['2223', '2324', '2425', '2526'])]
    if len(y) < 30: continue
    o = state_tab(y); hid = o['lvl'][0] - o['lvl'][1] - (o['all'][0] - o['all'][1])
    TS[t] = hid
    print(f'   {t:22s} {len(y):4d} │ {o["lvl"][0] - o["lvl"][1]:+15.2f} │ {o["up1"][0] - o["up1"][1]:+16.2f} {o["up1"][0]:5.2f}/{o["up1"][1]:4.2f} │ {o["up2"][0] - o["up2"][1]:+10.2f} │ '
          f'{o["all"][0] - o["all"][1]:+10.2f} │ {100 * (o["up1"][2] + o["up2"][2]):8.0f}% │ {hid:+8.2f} │ {100 * (o["up1"][0] / o["lvl"][0] - 1):+.0f}%')
print('   («κρυμμενο» = xGD/90 στην ισοπαλια − συνολικη xGD/ματς: ποσο η συνολικη διαφορα «κρυβει» την ισχυ λογω χρονου μπροστα)')
# Παρι ανα σεζον
print('   Παρι ανα σεζον: ' + ' · '.join(f'{s}: ισοπ {state_tab(y)["lvl"][0] - state_tab(y)["lvl"][1]:+.2f} / συνολο {y.xgd.mean():+.2f} / μπροστα {100 * (state_tab(y)["up1"][2] + state_tab(y)["up2"][2]):.0f}%'
                                  for s, y in G[G.team == 'Paris Saint-Germain'].groupby('sea')))
# ---------------- Δ2 ROTATION ----------------
ED = {}
for _, r in E.iterrows():
    d = pdt(r.date or '')
    if d: ED.setdefault(r.team, []).append(d)
om = M.groupby(['lg', 'sea', 'team']).xgd.mean()
M['oadj'] = [om.get((l, s, o), np.nan) for l, s, o in zip(M.lg, M.sea, M.opp)]
M['xgd_adj'] = M.xgd + M.oadj      # + ισχυς αντιπαλου (δυνατος αντιπαλος → μεγαλυτερη διορθωση)
def near(t, d):
    if d is None or t not in ED: return 'κανονικο'
    for e in ED[t]:
        dd = (e - d).total_seconds() / 86400
        if 0 < dd <= 4: return 'ΠΡΙΝ ευρωπ (≤4μ)'
        if -3 <= dd < 0: return 'ΜΕΤΑ ευρωπ (≤3μ)'
    return 'κανονικο'
M['ctx'] = [near(t, d) for t, d in zip(M.team, M.date)]
Q = M[M.sea.isin(['2223', '2324', '2425', '2526']) & M.team.isin(set(E.team))]
print('\n' + '=' * 130 + '\nΔ2. ROTATION — εγχωρια xG διαφορα (διορθωμενη για αντιπαλο) γυρω απο ευρωπαικα, 2022-26')
print(f'   {"ομαδα":22s} │ ' + ' │ '.join(f'{c:>24s}' for c in ('κανονικο', 'ΠΡΙΝ ευρωπ (≤4μ)', 'ΜΕΤΑ ευρωπ (≤3μ)')) + ' │ κενο (γυρω − κανονικο)')
RG = {}
for t in TEAMS + ['ΟΛΕΣ ομαδες με ευρωπαικα']:
    y = Q if t.startswith('ΟΛΕΣ') else Q[Q.team == t]
    if len(y) < 30: continue
    c = {k: (z.xgd_adj.mean(), z.xgd_adj.std() / np.sqrt(len(z)), len(z)) for k, z in y.groupby('ctx')}
    nn = y[y.ctx != 'κανονικο']; gap = nn.xgd_adj.mean() - y[y.ctx == 'κανονικο'].xgd_adj.mean()
    se = np.sqrt(nn.xgd_adj.var() / max(len(nn), 1) + y[y.ctx == 'κανονικο'].xgd_adj.var() / max((y.ctx == 'κανονικο').sum(), 1))
    RG[t] = gap
    print(f'   {t:22s} │ ' + ' │ '.join(f'{c[k][0]:+6.2f}±{c[k][1]:.2f} (n={c[k][2]:3d})' if k in c else f'{"—":>24s}' for k in ('κανονικο', 'ΠΡΙΝ ευρωπ (≤4μ)', 'ΜΕΤΑ ευρωπ (≤3μ)'))
          + f' │ {gap:+.2f}±{se:.2f}')
# ---------------- Δ3 ΓΕΝΙΚΟ ΤΕΣΤ ----------------
print('\n' + '=' * 130 + '\nΔ3. ΓΕΝΙΚΟ ΤΕΣΤ (ολες οι ομαδες-σεζον με ≥6 ευρωπαικα, εγχωρια ιδιας σεζον): εξηγουν τα εγχωρια «κρυμμενα» την ευρωπαικη αποκλιση;')
TSZ = []
for (t, s), y in E.groupby(['team', 'sea']):
    if len(y) < 6: continue
    g = G[(G.team == t) & (G.sea == s)]; q = M[(M.team == t) & (M.sea == s)]
    if len(g) < 15: continue
    o = state_tab(g)
    if not np.isfinite(o['lvl'][0]): continue
    hid = o['lvl'][0] - o['lvl'][1] - (o['all'][0] - o['all'][1])
    nn = q[q.ctx != 'κανονικο']; rg = nn.xgd_adj.mean() - q[q.ctx == 'κανονικο'].xgd_adj.mean() if len(nn) >= 3 else np.nan
    TSZ.append(dict(team=t, sea=s, n=len(y), rd=y.rd.mean(), rx=y.rx.mean() if 'rx' in y else (y.xf - y.mf - y.xa + y.ma).mean(),
                    km=(y.kgd - y.mgd).mean(), hid=hid, lead=o['up1'][2] + o['up2'][2], dom=o['all'][0] - o['all'][1], rg=rg))
Z = pd.DataFrame(TSZ)
def reg(x, ycol, lab):
    z = Z[[x, ycol, 'n']].dropna(); w = z.n.values
    b = np.polyfit(z[x], z[ycol], 1, w=np.sqrt(w)); r = np.corrcoef(z[x], z[ycol])[0, 1]
    print(f'   {lab:62s} r = {r:+.2f} (n={len(z)}, ±{1 / np.sqrt(len(z)):.2f}) · κλιση {b[0]:+.2f}')
reg('hid', 'rd', '«κρυμμενο απο κατασταση» → ευρωπ. πραγμ−μοντελο')
reg('hid', 'km', '«κρυμμενο απο κατασταση» → αγορα−μοντελο')
reg('lead', 'rd', '% χρονου μπροστα (εγχωρια) → ευρωπ. πραγμ−μοντελο')
reg('dom', 'rd', 'εγχωρια κυριαρχια (xGD/ματς) → ευρωπ. πραγμ−μοντελο')
reg('dom', 'km', 'εγχωρια κυριαρχια (xGD/ματς) → αγορα−μοντελο')
reg('rg', 'rd', 'rotation-κενο (γυρω απο ευρωπ − κανονικο) → ευρωπ. πραγμ−μοντελο')
reg('rg', 'km', 'rotation-κενο → αγορα−μοντελο')
d = Z.assign(dc=pd.qcut(Z.dom, 4, labels=['Q1 αδυναμες', 'Q2', 'Q3', 'Q4 κυριαρχες']))
print('   ανα τεταρτημοριο εγχωριας κυριαρχιας: ' + ' · '.join(f'{k}: πραγμ−μοντ {v.rd.mean():+.2f} (n={len(v)})' for k, v in d.groupby('dc', observed=True)))
z = Z[Z.dom >= Z.dom.quantile(.9)].sort_values('dom', ascending=False)
print('   top 10% εγχωριας κυριαρχιας (ομαδα-σεζον): ' + ' · '.join(f'{r.team[:14]} {r.sea} {r.rd:+.2f}' for r in z.itertuples()))
print(f'   → μεσος ορος top 10%: {z.rd.mean():+.2f} (n={len(z)}) · χωρις Παρι: {z[z.team != "Paris Saint-Germain"].rd.mean():+.2f}')
print('   Παρι ανα σεζον: ' + ' · '.join(f'{r.sea}: κρυμμενο {r.hid:+.2f} · rot-κενο {r.rg:+.2f} · κυριαρχια {r.dom:+.2f} · ευρωπ {r.rd:+.2f}' for r in Z[Z.team == 'Paris Saint-Germain'].itertuples()))
