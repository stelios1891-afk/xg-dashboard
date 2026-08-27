# -*- coding: utf-8 -*-
"""
add_current_season.py -- Προσθετει/ανανεωνει τις γραμμες της ΦΕΤΙΝΗΣ σεζον (2627, CORE7)
στο teamgame_inputs.csv, με ΑΚΡΙΒΩΣ την ιδια λογικη με το build_inputs.py (compression +
penalty 0.25 + red adj + per-league-season rescale). Idempotent: πεταει τις παλιες 2627
γραμμες και τις ξαναχτιζει. ΔΕΝ αγγιζει τις υπολοιπες σεζον (2425/2526).

Τρεξε μετα απο καθε εβδομαδιαιο refresh (discover+dl) των CORE7:  python add_current_season.py
"""
import json, os, sys
import pandas as pd
from datetime import datetime
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass

CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
SEASON = '2627'
CSV = 'teamgame_inputs.csv'

def isodate(s):
    try:
        return datetime.strptime(s.replace(' UTC', ''), '%a, %b %d, %Y, %H:%M').strftime('%Y-%m-%d')
    except Exception:
        return s[:10]

def w(xg):   # ΙΔΙΟ με build_inputs.py (Caley step-wise compression)
    if xg <= 0.2: return 1.00
    if xg <= 0.4: return 0.45
    if xg <= 0.5: return 0.25
    if xg <= 0.7: return 0.15
    return 0.05

rows = []
for lg in CORE7:
    path = f'data_{lg}_{SEASON}.json'
    if not os.path.exists(path):
        print(f"  (λειπει {path})"); continue
    d = json.load(open(path, encoding='utf-8'))
    for mid, m in d.items():
        hid = int(m['home']['id']); aid = int(m['away']['id'])
        if m['hs'] is None or m['as'] is None:
            continue
        agg = {hid: dict(np_raw=0.0, np_comp=0.0, pen=0, ns=0),
               aid: dict(np_raw=0.0, np_comp=0.0, pen=0, ns=0)}
        for s in m['shots']:
            xg = s.get('xg')
            if xg is None: continue
            tid = s.get('tid')
            if tid not in agg: continue
            if s.get('sit') == 'Penalty':
                agg[tid]['pen'] += 1
            else:
                agg[tid]['np_raw'] += xg
                agg[tid]['np_comp'] += xg * w(xg)
                agg[tid]['ns'] += 1
        ft = 95
        dis_home = 0.0; dis_away = 0.0
        for r in m['reds']:
            mn = r.get('min') or 0; dur = max(0, ft - mn)
            if r['home']: dis_home += dur
            else: dis_away += dur
        for is_home, tid, opp, gf, dis_self, dis_opp in [
                (1, hid, aid, m['hs'], dis_home, dis_away),
                (0, aid, hid, m['as'], dis_away, dis_home)]:
            a = agg[tid]
            red_xg = 0.0083 * dis_opp - 0.5 * 0.0083 * dis_self
            rows.append(dict(league=lg, season=SEASON, mid=mid, date=isodate(m['date']),
                             team=tid, opp=opp, is_home=is_home, gf=gf,
                             np_raw=a['np_raw'], np_comp=a['np_comp'], pen=a['pen'], ns=a['ns'],
                             red_xg=red_xg))

if not rows:
    print("Καμια 2627 γραμμη — τιποτα να προσθεσω."); sys.exit(0)

new = pd.DataFrame(rows)
# ---------- per-league rescale, ΜΕ WARM-START (2026-08-27) ----------
# Το build_inputs.py υπολογιζει τον συντελεστη απο ΟΛΗ την τελειωμενη σεζον (380 ματς).
# Εδω, μεσα στη σεζον, ειχαμε μονο τα ματς που εχουν παιχτει -> 8.1% σφαλμα στην 1η αγων.
# Ο περσινος συντελεστης ειναι ΣΤΑΘΕΡΟΤΕΡΟΣ (3.7% σφαλμα, σταθερα) απο 20 ματς φετινα.
# Μιξη (ιδια μορφη με το warm-start των ratings): σφαλμα 8.1%->3.3% (md1), 2.2%->1.4% (md8).
# Kf=4 = στην 4η αγωνιστικη μετρανε 50/50. Πλατο Kf=2-8 (βλ. συνομιλια 2026-08-27).
KF = 4.0
_prev = pd.read_csv(CSV)
_prev['season'] = _prev['season'].astype(str)
_seasons = sorted(_prev.season.unique())
PREV_SEASON = _seasons[-1] if _seasons and _seasons[-1] != SEASON else (
    _seasons[-2] if len(_seasons) > 1 else None)

new['comp_np_scaled'] = new['np_comp']
for (lg, sea), g in new.groupby(['league', 'season']):
    live = g.np_raw.sum() / g.np_comp.sum()
    pg = _prev[(_prev.league == lg) & (_prev.season == PREV_SEASON)] if PREV_SEASON else None
    if pg is not None and len(pg) and pg.np_comp.sum() > 0:
        prior = pg.np_raw.sum() / pg.np_comp.sum()
        md = len(g) / max(g.team.nunique(), 1)          # αγωνιστικες που εχουν παιχτει
        w = md / (md + KF)
        sf = prior * (live / prior) ** w
    else:
        sf = live                                        # καμια περσινη -> ο,τι εχουμε
        md = float('nan'); w = 1.0; prior = float('nan')
    mk = (new.league == lg) & (new.season == sea)
    new.loc[mk, 'comp_np_scaled'] = new.loc[mk, 'np_comp'] * sf
    new.loc[mk, 'sf'] = sf
    print("  %-13s md%-4.1f  περσινος %.4f · φετινος %.4f · βαρος φετ. %.0f%%  ->  %.4f"
          % (lg, md, prior, live, w * 100, sf))
new['xg_model'] = new['comp_np_scaled'] + 0.25 * new['pen'] + new['red_xg']
new['ns_eff'] = new['ns'] + new['pen'] + (new['red_xg'].abs() / 0.10)
new['xgps'] = new['xg_model'] / new['ns_eff'].clip(lower=1)

# merge: κρατα ολες τις ΑΛΛΕΣ σεζον ως εχουν, αντικατεστησε τις 2627
old = pd.read_csv(CSV); old['season'] = old['season'].astype(str)
before = old[old.season != SEASON].copy()
new = new[old.columns]   # ιδια σειρα στηλων
out = pd.concat([before, new], ignore_index=True).sort_values(['league', 'season', 'date', 'mid', 'is_home'])
out.to_csv(CSV, index=False)

print(f"ΟΚ. {len(new)} γραμμες-ομαδα 2627 ({len(new)//2} ματς) για {sorted(new.league.unique())}")
print(f"Σεζον τωρα στο csv: {sorted(out.season.astype(str).unique())}")
print(f"Αμεταβλητες γραμμες (μη-2627): {len(before)} (ηταν {len(old[old.season!=SEASON])})")
print("\nΜεσο xg_model/ομαδα (2627):")
print(new.groupby('league').xg_model.mean().round(3))
