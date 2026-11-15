"""
intl_tmix_retro.py — ΑΝΑΔΡΟΜΗ: ολα τα ματς Nations League 2026-27 απο 24/9 ως σημερα (26/9) με το ΣΗΜΕΡΙΝΟ T και το ΝΕΟ T (T + xG ομαδων, 12 ματς).
Για καθε ματς: το dashboard ΠΡΙΝ τη σεντρα (git: τελευταιο commit του intl_projections_dashboard.json πριν το ΚΟ — για τα επομενα ματς το τρεχον),
γραμμη/τιμη over της πηγης, T ανα μοντελο, edge over, pick over (edge ≥8% ΚΑΙ κοντινο/KO) ανα μοντελο, συναινεση ≥2/3 — παλια vs νεα·
xG ομαδων ΟΠΩΣ ΗΤΑΝ πριν το ματς (walk-forward, ιδια μεθοδος με intl_xg_team_windows N=12)· σκορ απο FotMob.
Νεο T = b0 + b1·T + b2·xG (βαρη ολου του δειγματος: Μ1 −0.83/0.74/0.58 · Μ2 −0.80/0.85/0.47 · Μ3 −0.68/0.74/0.50).
Εξοδος: intl_tmix_retro.csv + εκτυπωση.
"""
import sys, json, subprocess, collections, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
import intl_pricing as ip, intl_picks_ledger as L
W = {'H': (-0.83, 0.74, 0.58), 'A': (-0.80, 0.85, 0.47), 'AV': (-0.68, 0.74, 0.50)}
MOD = {'H': 'Μ1', 'A': 'Μ2', 'AV': 'Μ3'}
NOW = dt.datetime.now(dt.timezone.utc)
log = subprocess.run(['git', 'log', 'origin/main', '--format=%H %cI', '--', 'intl_projections_dashboard.json'], capture_output=True, text=True).stdout.split('\n')
COMMITS = sorted([(pd.Timestamp(t).tz_convert('UTC'), h) for h, t in (l.split() for l in log if l)])
_cache = {}
def snap_before(ko):
    c = [h for t, h in COMMITS if t < ko]
    h = c[-1] if c else COMMITS[0][1]
    if h not in _cache:
        _cache[h] = json.loads(subprocess.run(['git', 'show', f'{h}:intl_projections_dashboard.json'], capture_output=True, text=True, encoding='utf-8').stdout)
    return _cache[h]
# ---- ολα τα ματς NL 24/9 .. τελος 26/9 (απο οποιοδηποτε snapshot) ----
matches = {}
for t, h in COMMITS[::max(1, len(COMMITS) // 40)] + [COMMITS[-1]]:
    d = snap_before(t + pd.Timedelta(seconds=1))
    for c in d['comps']:
        for m in c['matches']:
            if '2026-09-24' <= m['utc'][:10] <= '2026-09-26':
                matches[(c['comp'], m['utc'], m['home'], m['away'])] = (m['hid'], m['aid'])
# ---- xG ομαδων walk-forward ----
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}, parse_dates=['date']).sort_values('date').reset_index(drop=True)
MU = float(pd.concat([M[M.has_xg].xg_h, M[M.has_xg].xg_a]).mean()); K = 8; HF = 1.15; N = 12
def xg_at(hid, aid, ko):
    hist = collections.defaultdict(list)
    def rating(t):
        h = hist[t][-N:]; n = len(h)
        if n == 0: return MU, MU
        w = n / (n + K); return w * np.mean([x[0] for x in h]) + (1 - w) * MU, w * np.mean([x[1] for x in h]) + (1 - w) * MU
    for r in M[(M.date < ko.tz_localize(None)) & M.has_xg].itertuples():
        ah, dh = rating(r.hid); aa, da = rating(r.aid)
        hist[r.hid].append((float(r.xg_h) / (da / MU), float(r.xg_a) / (aa / MU))); hist[r.aid].append((float(r.xg_a) / (dh / MU), float(r.xg_h) / (ah / MU)))
    ah, dh = rating(hid); aa, da = rating(aid)
    return MU * (ah / MU) * (da / MU) * HF, MU * (aa / MU) * (dh / MU) / HF
res = L.fetch_results(['NL A', 'NL B', 'NL C', 'NL D'])
rows = []
for (comp, utc, h, a), (hid, aid) in sorted(matches.items(), key=lambda kv: kv[0][1]):
    ko = pd.Timestamp(utc).tz_localize('UTC'); d = snap_before(ko) if ko <= NOW else snap_before(NOW + pd.Timedelta(days=1))
    m = next((x for c in d['comps'] for x in c['matches'] if x['home'] == h and x['away'] == a and x['utc'] == utc), None)
    if m is None: continue
    src = m['market'].get('source'); mk = (m['market'].get(src) or {}) if src else {}
    if mk.get('ou_line') is None or not mk.get('over'): continue
    lh, la = xg_at(hid, aid, ko); xgs = lh + la; sc = res.get((comp, h, a))
    rec = dict(ko=utc, comp=comp, ματς=f'{h} - {a}', γραμμη=mk['ou_line'], τιμη_over=mk['over'], xG_ομαδων=round(xgs, 2), σκορ=(f'{sc[0]}-{sc[1]}' if sc else '—'),
               γκολ=(sc[0] + sc[1] if sc else np.nan))
    old_n = new_n = 0
    for v in ('H', 'A', 'AV'):
        V = m['versions'].get(v)
        if not V or V.get('T') is None: continue
        T0 = V['T']; b = W[v]; T1 = max(b[0] + b[1] * T0 + b[2] * xgs, 0.8); close = abs(V['R_h'] - V['R_a']) < 150
        e0 = ip.over_ev(T0, mk['ou_line'], mk['over']); e1 = ip.over_ev(T1, mk['ou_line'], mk['over'])
        p0 = e0 >= .08 and close; p1 = e1 >= .08 and close; old_n += p0; new_n += p1
        rec[f'T_{MOD[v]}'] = f'{T0:.2f}→{T1:.2f}'; rec[f'edge_{MOD[v]}'] = f'{e0 * 100:+.0f}→{e1 * 100:+.0f}%'
    rec['κοντινο'] = 'ναι' if abs(m['versions']['H']['R_h'] - m['versions']['H']['R_a']) < 150 else ''
    rec['over_σημερα'] = 'PICK' if old_n >= 2 else ''; rec['over_νεο'] = 'PICK' if new_n >= 2 else ''
    rec['αποτελεσμα_over'] = ('' if np.isnan(rec['γκολ']) else f"{ip.settle_over(int(rec['γκολ']), mk['ou_line'], mk['over']):+.2f}")
    rows.append(rec)
R = pd.DataFrame(rows); R.to_csv('intl_tmix_retro.csv', index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(R[['ko', 'ματς', 'γραμμη', 'τιμη_over', 'κοντινο', 'xG_ομαδων', 'T_Μ1', 'T_Μ2', 'T_Μ3', 'edge_Μ1', 'edge_Μ2', 'edge_Μ3', 'over_σημερα', 'over_νεο', 'σκορ', 'αποτελεσμα_over']].to_string(index=False))
