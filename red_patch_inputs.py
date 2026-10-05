"""
red_patch_inputs.py — 5/10/2026 (μια φορα): ξαναυπολογιζει στο LIVE teamgame_inputs.csv τις στηλες που εξαρτωνται απο τις κοκκινες
(np_raw, np_comp, ns, red_xg, comp_np_scaled, xg_model, ns_eff, xgps) για ΟΛΕΣ τις σεζον, με red_modes.LIVE_MODE.
Ξεκινα παντα απο τα ωμα σουτ (data_*.json) → idempotent. Κραταει τον υπαρχοντα συντελεστη sf της καθε λιγκας-σεζον.
Ελεγχος: γραμμες ματς ΧΩΡΙΣ κοκκινη πρεπει να βγαινουν ιδιες (εγγυαται οτι ξαναχτιζουμε σωστα).
"""
import json, sys
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import red_modes
W = lambda x: 1.0 if x <= .2 else (.45 if x <= .4 else (.25 if x <= .5 else (.15 if x <= .7 else .05)))
T = pd.read_csv('teamgame_inputs.csv', dtype={'mid': str}); T['season'] = T['season'].astype(str)
T['ns'] = T['ns'].astype(float)
old = T.copy(); upd = {}
for (lg, sea), g in T.groupby(['league', 'season']):
    d = json.load(open(f'data_{lg}_{sea}.json', encoding='utf-8'))
    for mid in g.mid.unique():
        m = d.get(str(mid))
        if m is None: continue
        hid, aid = int(m['home']['id']), int(m['away']['id'])
        agg = {hid: [0., 0., 0], aid: [0., 0., 0]}
        for s in m['shots']:
            x = s.get('xg'); t = s.get('tid')
            if x is None or t not in agg or s.get('sit') == 'Penalty': continue
            agg[t][0] += x; agg[t][1] += x * W(x); agg[t][2] += 1
        R = red_modes.live_adj(m)
        for t in (hid, aid):
            upd[(str(mid), t)] = (agg[t][0] * R[t]['fr'], agg[t][1] * R[t]['fc'], agg[t][2] * R[t]['fn'], R[t]['term'], bool(m.get('reds')))
k = [upd.get((mi, int(t))) for mi, t in zip(T.mid, T.team)]
miss = sum(1 for x in k if x is None); print('γραμμες χωρις json:', miss)
has = [x is not None for x in k]
T.loc[has, 'np_raw'] = [x[0] for x in k if x]; T.loc[has, 'np_comp'] = [x[1] for x in k if x]
T.loc[has, 'ns'] = [x[2] for x in k if x]; T.loc[has, 'red_xg'] = [x[3] for x in k if x]
T['comp_np_scaled'] = T.np_comp * T.sf
T['xg_model'] = T.comp_np_scaled + 0.25 * T.pen + T.red_xg
T['ns_eff'] = np.maximum(T.ns + T.pen + T.red_xg / 0.10, 0.5 * (T.ns + T.pen))
T['xgps'] = T.xg_model / T.ns_eff.clip(lower=1)
red = np.array([bool(x and x[4]) for x in k])
for c in ('xg_model', 'ns_eff', 'np_raw'):
    print(f'{c}: max |διαφορα| σε ματς ΧΩΡΙΣ κοκκινη = {(T[c] - old[c])[~red].abs().max():.2e} · σε ματς ΜΕ κοκκινη = {(T[c] - old[c])[red].abs().mean():.3f} (μεσος)')
print('γραμμες με κοκκινη:', red.sum(), '· μεσο red_xg παλιο', round(old.red_xg[red].mean(), 3), 'νεο', round(T.red_xg[red].mean(), 3))
T.to_csv('teamgame_inputs.csv', index=False); print('OK', len(T))
