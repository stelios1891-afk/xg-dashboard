# -*- coding: utf-8 -*-
"""ben_alt.py — 19/10/2026 (Στελιος: «ο Ben δεν ανανεωνει τα ματς — οσο δεν το κανει πρεπει να βρουμε εναλλακτικη»).
Εναλλακτικες εισοδοι για τις 9 λιγκες του Ben στο euro engine (ιδια μορφη με load_griffis: {(λιγκα, σεζον): DataFrame date/team/gf/xg_model/ns_eff}):
  goals_dict(G)  = ΣΗΜΕΡΙΝΗ ΠΡΟΣΩΡΙΝΗ ΛΥΣΗ: ολα τα ματς απο FotMob με ΓΚΟΛ αντι xG (κλιμακα xG/γκολ του Ben στη λιγκα-σεζον, ns = μεσος Ben)
                   — μενουν «griffis» πλευρες, δηλ. ΧΩΡΙΣ Elo.
  fs_dict(G)     = FootyStats xG (ταυτιση/συντελεστης ιδια με ben_vs_fs.build_g_fs· αταιριαστα → γκολ).
  ({} στη θεση του G = γκολ + Elo: οι λιγκες γινονται goal-only και το engine βαζει Elo, οπως σε Κυπρο/Βουλγαρια κτλ.)"""
import json, os
import numpy as np, pandas as pd
from datetime import datetime


def goals_dict(G):
    from euro_engine import kodt
    out = {}
    for (lg, sea), g in G.items():
        p = f'data_{lg}_{sea}.json'
        if not os.path.exists(p) or not len(g):
            continue
        scale = g.xg_model.sum() / max(g.gf.sum(), 1e-9); ns_m = float(g.ns_eff.mean())
        recs = []
        for m in json.load(open(p, encoding='utf-8')).values():
            if m.get('hs') is None or m.get('as') is None:
                continue
            d0 = kodt(m['date'])
            if d0 is None:
                continue
            recs.append((datetime(d0.year, d0.month, d0.day), int(m['home']['id']), int(m['away']['id']), float(m['hs']), float(m['as'])))
        recs.sort(key=lambda x: x[0]); rows = []
        for d0, h, a, hs, as_ in recs:
            rows.append(dict(date=d0, team=h, gf=hs, xg_model=hs * scale, ns_eff=ns_m))
            rows.append(dict(date=d0, team=a, gf=as_, xg_model=as_ * scale, ns_eff=ns_m))
        out[(lg, sea)] = pd.DataFrame(rows)
    return out


def fs_dict(G):
    src = open('ben_vs_fs.py', encoding='utf-8').read()
    src = src[:src.index('# ================================================================ FSEngine')]
    src = src.replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass')
    ns = {'__name__': 'ben_vs_fs_part'}
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        exec(src, ns)
        FM = ns['load_fm9'](); FSM = ns['build_fsm9'](FM)
        Gb = {k: v for k, v in G.items() if k in FM}
        out = ns['build_g_fs'](Gb, FSM)
    return out
