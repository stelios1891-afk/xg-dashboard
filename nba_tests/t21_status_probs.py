# -*- coding: utf-8 -*-
"""t21_status_probs.py — ΕΠΙΣΗΜΕΣ ΑΝΑΦΟΡΕΣ ΤΡΑΥΜΑΤΙΩΝ ↔ ΠΟΙΟΣ ΕΠΑΙΞΕ (21/10/2026, Στελιος «ξεκινα για μια πρωτη γευση»).
Πηγη: nba_injrep/rows_{σεζον}.csv (nba_injrep_fetch.py, ωριαιες αναφορες NBA) · box score: nba_player_games.csv (κανονικη περιοδος).
Για καθε (παικτης, ματς) που εμφανιζεται σε αναφορα: η ΚΑΤΑΣΤΑΣΗ του στην πιο προσφατη αναφορα πριν απο Τ−24ω / Τ−12ω / Τ−6ω / Τ−2ω / Τ−0
(Τ = τζαμπολ, ωρα ΝΥ) και αν τελικα ΕΠΑΙΞΕ (λεπτα > 0 στο box score). Εκτος: G League / two-way.
ΡΟΛΟΣ = μ.ο. λεπτων στα 10 τελευταια φετινα ματς του για την ομαδα πριν το ματς: σταρ ≥30′ · βασικος 20-30′ · ρολιστας 10-20′ · <10′.
Εξοδος: t21_status_probs_out.txt + nba_injrep/status_games.csv (για τα επομενα τεστ)."""
import os, sys, re, collections, unicodedata, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda n: os.path.join(ROOT, n)
AB = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'SA': 'SAS', 'UTAH': 'UTA', 'WSH': 'WAS'}
SUF = re.compile(r'\b(jr|sr|ii|iii|iv)\b\.?', re.I)
def nkey(s):
    s = unicodedata.normalize('NFD', str(s)); s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()
    s = SUF.sub('', s); return re.sub(r'[^a-z]', '', s)
# ---------- box score ----------
B = pd.read_csv(F('nba_player_games.csv'), usecols=['PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MIN', 'season', 'stype'], low_memory=False)
B = B[B.stype == 'RS'].copy(); B['MIN'] = pd.to_numeric(B.MIN, errors='coerce').fillna(0)
B['team'] = B.TEAM_ABBREVIATION.replace(AB); B['d'] = pd.to_datetime(B.GAME_DATE).dt.strftime('%Y-%m-%d'); B['k'] = B.PLAYER_NAME.map(nkey)
PLAYED = {(r.k, r.team, r.d): r.MIN for r in B.itertuples(index=False)}
TEAMDAYS = set(zip(B.team, B.d))
hist = collections.defaultdict(list)                                   # (k, team) → [(d, min)] με σειρα
for r in B.sort_values('d').itertuples(index=False):
    if r.MIN > 0: hist[(r.k, r.team)].append((r.d, r.MIN))
def role_min(k, t, d):
    h = [m for dd, m in hist.get((k, t), []) if dd < d][-10:]
    return float(np.mean(h)) if h else np.nan
# ---------- αναφορες ----------
R = []
for s in (2022, 2023, 2024, 2025, 2026):
    fn = F(f'nba_injrep/rows_{s}.csv')
    if not os.path.exists(fn): continue
    x = pd.read_csv(fn, dtype=str).dropna(subset=['rep_ts', 'game_date', 'team', 'key', 'status']); x['sea'] = s; R.append(x)
R = pd.concat(R, ignore_index=True)
R = R[~R.reason.fillna('').str.replace(' ', '').str.contains('GLeague', case=False)]
R['rep'] = pd.to_datetime(R.rep_ts, format='%m/%d/%y %I:%M %p', errors='coerce')
R['gd'] = pd.to_datetime(R.game_date, format='%m/%d/%Y', errors='coerce')
R['gtime'] = R.game_time_et.str.extract(r'(\d\d:\d\d)')[0]
_t = pd.to_datetime(R.gd.dt.strftime('%Y-%m-%d') + ' ' + R['gtime'], errors='coerce')
R['tip'] = _t + pd.to_timedelta(np.where(_t.dt.hour < 12, 12, 0), unit='h')   # ωρες ματς στην αναφορα: 12ωρο χωρις PM (01:00 = 1μμ, 07:00 = 7μμ· 12:00 = μεσημερι)
R = R.dropna(subset=['rep', 'tip'])
R['hb'] = (R.tip - R.rep).dt.total_seconds() / 3600
R = R[R.hb >= -0.5]
R['d'] = R.gd.dt.strftime('%Y-%m-%d')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
# τελικη εικονα ανα (παικτης, ομαδα, ματς)
WIN = (('Τ−24ω', 24), ('Τ−12ω', 12), ('Τ−6ω', 6), ('Τ−2ω', 2), ('τελευταια', -1))
G = []
for (k, t, d), g in R.sort_values('rep').groupby(['key', 'team', 'd']):
    if (t, d) not in TEAMDAYS: continue                     # ματς που δεν βρισκεται στα box scores (πλει-οφ, αναβολη)
    st = {}
    for lab, h in WIN:
        gg = g[g.hb >= h] if h >= 0 else g
        st[lab] = gg.status.iloc[-1] if len(gg) else None
    mn = PLAYED.get((k, t, d), 0)
    G.append(dict(k=k, name=g.player.iloc[-1], t=t, d=d, sea=g.sea.iloc[0], played=mn > 0, minutes=mn, role=role_min(k, t, d),
                  first_hb=g.hb.max(), **{f's_{lab}': v for lab, v in st.items()}))
G = pd.DataFrame(G)
G.to_csv(F('nba_injrep/status_games.csv'), index=False, encoding='utf-8')
P(f'NBA · ΕΠΙΣΗΜΕΣ ΑΝΑΦΟΡΕΣ ↔ BOX SCORE · σεζον {sorted(G.sea.unique().tolist())} · {len(G)} περιπτωσεις παικτη-ματς σε αναφορα')
# ---- ελεγχος με γνωστα παραδειγματα ----
P(''); P('=== ΕΛΕΓΧΟΣ (γνωστα παραδειγματα) ===')
for nm, d in (('joelembiid', '2023-01-10'), ('cadecunningham', '2023-01-10'), ('pjtucker', '2023-01-10'), ('lukadoncic', '2025-02-04'), ('lukadoncic', '2025-02-10')):
    x = G[(G.k == nm) & (G.d == d)]
    for _, r in x.iterrows():
        P(f"  {r['name']:22s} {r['d']} {r['t']}: Τ−24ω {r['s_Τ−24ω']} · Τ−6ω {r['s_Τ−6ω']} · τελευταια {r['s_τελευταια']} → επαιξε {r['played']} ({r['minutes']:.0f}′) · ρολος {r['role']:.0f}′")
    if not len(x): P(f'  {nm} {d}: δεν βρεθηκε')
# ---- πιθανοτητα να ΜΗΝ παιξει ----
ROLES = (('σταρ ≥30′', 30, 99), ('βασικος 20-30′', 20, 30), ('ρολιστας 10-20′', 10, 20))
for lab, h in WIN:
    col = f's_{lab}'
    P(''); P(f'=== ΚΑΤΑΣΤΑΣΗ στο {lab} → ποσοι ΔΕΝ επαιξαν (παικτες με ≥10′ μ.ο.) ===')
    for stt in ('Out', 'Doubtful', 'Questionable', 'Probable', 'Available'):
        d = G[(G[col] == stt) & (G.role >= 10)]
        if not len(d): continue
        parts = []
        for rl, lo, hi in ROLES:
            dd = d[(d.role >= lo) & (d.role < hi)]
            if len(dd): parts.append(f'{rl} {100 * (~dd.played).mean():5.1f}% ({len(dd)})')
        P(f'  {stt:12s} δεν επαιξαν {100 * (~d.played).mean():5.1f}% (n {len(d):5d}) · ' + ' · '.join(parts))
P(''); P('=== ΜΕΤΑΒΑΣΕΙΣ: κατασταση Τ−24ω → τελικη (παικτες ≥10′) ===')
d = G[G.role >= 10]
tab = pd.crosstab(d['s_Τ−24ω'].fillna('δεν ηταν στη λιστα'), d['s_τελευταια'].fillna('—'), normalize='index') * 100
P(tab.round(1).to_string())
P(''); P('=== ΑΝΑ ΣΕΖΟΝ: Questionable στο Τ−6ω → δεν επαιξαν ===')
for s in sorted(G.sea.unique()):
    dd = G[(G.sea == s) & (G['s_Τ−6ω'] == 'Questionable') & (G.role >= 10)]
    P(f'  {s - 1}-{str(s)[2:]}: {100 * (~dd.played).mean() if len(dd) else 0:5.1f}% (n {len(dd)})')
open(F('nba_tests/t21_status_probs_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
