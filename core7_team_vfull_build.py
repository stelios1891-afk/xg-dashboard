# -*- coding: utf-8 -*-
"""
core7_team_vfull_build.py — χτιζει το ΜΙΚΡΟ αρχειο core7_team_vfull.json για το season_sim_2627.py (αποφαση Στελιου 24/9/2026).
Τρεχει ΤΟΠΙΚΑ, χειροκινητα (~1x/μηνα): χρειαζεται core7_squads.json + core7_player_values.json (10MB το καθενα, gitignored,
ΔΕΝ υπαρχουν στο GitHub Actions) και teamgame_inputs_5s_wf.csv (μεσω season_sim.load_5s).

V_full(ομαδα) = 80ο εκατοστημοριο της XI value των ματς της στις τελευταιες 365 ημερες (εως σημερα), >=3 ματς αλλιως null.
XI value ματς = αθροισμα αξιων (FotMob/SciSports ιστορικο) των 11 βασικων στην πλησιεστερη ημερομηνια ΠΡΙΝ το ματς,
>=8/11 με τιμη, αναγωγη στα 11 — ιδια μεθοδος με core7_value_test.py / season_sim_tests.py (Γ3).
Ομαδες = οσες εμφανιζονται στα data_{lg}_2627.json (φετινες)· οσες δεν εχουν ενδεκαδες στο αρχειο (νεοφωτιστες απο 2η
κατηγορια) -> vfull null (το season_sim_2627 τις αφηνει lv=0).
Εξοδος: core7_team_vfull.json = {"asof":..., "window_days":365, "leagues": {league: {team_id: {name, vfull, n_xi}}}}
"""
import os, sys, json, bisect
from datetime import date
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import season_sim as SS

WINDOW = 365
ASOF = pd.Timestamp(sys.argv[1]) if len(sys.argv) > 1 else pd.Timestamp(date.today())

SQ = json.load(open('core7_squads.json', encoding='utf-8'))
PV = json.load(open('core7_player_values.json', encoding='utf-8'))
H = {}
for pid, v in PV.items():
    h = sorted((d, float(x)) for d, x in (v.get('hist') or []) if d and x)
    if h:
        H[int(pid)] = ([d for d, _ in h], [x for _, x in h])
    elif v.get('mv_now') and str(v['mv_now']) != 'None':
        H[int(pid)] = (['2026-09-20'], [float(v['mv_now'])])


def value_at(pid, dstr):
    h = H.get(pid)
    if not h:
        return None
    ds, vs = h; i = bisect.bisect_right(ds, dstr) - 1
    return vs[i] if i >= 0 else vs[0]


def xi_value(mid, side, dstr):
    s = (SQ.get(str(mid)) or {}).get(side) or {}; st = s.get('st') or []
    if len(st) < 8:
        return np.nan
    got = [v for v in (value_at(int(p), dstr) for p in st) if v]
    return sum(got) * len(st) / len(got) if len(got) >= len(st) - 3 else np.nan


def main():
    M, id2name = SS.load_5s()
    lo = ASOF - pd.Timedelta(days=WINDOW)
    Mw = M[(pd.to_datetime(M.date) > lo) & (pd.to_datetime(M.date) <= ASOF)]
    print(f"asof {ASOF.date()} · παραθυρο ({lo.date()}, {ASOF.date()}] · ματς 5σ στο παραθυρο: {len(Mw)}")
    xi = {}
    for r in Mw.itertuples(index=False):
        for tid, side in ((r.home, 'h'), (r.away, 'a')):
            v = xi_value(r.mid, side, r.date)
            if v and v > 0:
                xi.setdefault(int(tid), []).append(float(v))
    out = dict(asof=str(ASOF.date()), window_days=WINDOW, method='p80 XI value 365d (core7_value_test / season_sim_tests Γ3)', leagues={})
    for lg in SS.CORE7:
        d = json.load(open(f'data_{lg}_2627.json', encoding='utf-8'))
        names = {}
        for m in d.values():
            names[int(m['home']['id'])] = m['home']['name']; names[int(m['away']['id'])] = m['away']['name']
        L = {}
        for t in sorted(names):
            vals = xi.get(t, [])
            L[str(t)] = dict(name=names[t], vfull=round(float(np.percentile(vals, 80))) if len(vals) >= 3 else None, n_xi=len(vals))
        out['leagues'][lg] = L
        have = [v['vfull'] for v in L.values() if v['vfull']]
        print(f"  {lg:13s}: {len(L)} ομαδες, με V {len(have)}, διαμεσος {np.median(have)/1e6:.0f} εκ.€, χωρις V: {[v['name'] for v in L.values() if not v['vfull']]}")
    json.dump(out, open('core7_team_vfull.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print("core7_team_vfull.json γραφτηκε.")


if __name__ == '__main__':
    main()
