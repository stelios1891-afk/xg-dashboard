# -*- coding: utf-8 -*-
"""t25_lineups.py — ΦΑΣΗ 3: ΠΟΙΟΙ ΠΑΙΖΟΥΝ (πενταδες ESPN play-by-play, Ιαν-Απρ 5 σεζον) (21/10/2026, Στελιος: «βλεποντας τις 5αδες τους
ειδικα στην 4η περιοδο… αλλο η αδιαφορη και αλλο η tanking — μια αδιαφορη μπορει να δινει χρονο σε μικρους χωρις να θελει να χασει»).
ΑΝΑΣΥΝΘΕΣΗ ΠΕΝΤΑΔΑΣ ανα περιοδο: στην αρχη καθε περιοδου στο γηπεδο = οσοι εμφανιζονται (φαση ή «βγαινει» σε αλλαγη) πριν μπουν με αλλαγη·
  αν βρεθουν <5, συμπληρωνονται απο την πενταδα του τελους της προηγουμενης (1η περιοδος: βασικοι του box). Αλλαγη: συμμετεχοντες [μπαινει, βγαινει].
  Χρονος στο γηπεδο = δευτερολεπτα αναμεσα στις φασεις.
ΟΡΙΣΜΟΙ (γραφτηκαν ΠΡΙΝ το τρεξιμο, ολα απο ΠΡΟΗΓΟΥΜΕΝΑ ματς της ιδιας σεζον μεσα στο αρχειο, ≥10 ματς ιστορικο):
  ΒΑΣΙΚΟΙ = οι 5 με τα περισσοτερα λεπτα στα προηγουμενα ματς · ΡΟΤΑΣΙΟΝ = οι 8 πρωτοι · ΠΕΡΙΘΩΡΙΑΚΟΙ = εκτος των 8.
  Ανα ομαδα-ματς:
   core_min   = λεπτα των 5 βασικων (box) · core_dnp = ποσοι απο τους 5 δεν επαιξαν
   fringe_sh  = μεριδιο λεπτων σε περιθωριακους (εκτος 8)
   q4_core    = μεριδιο του χρονου της 4ης περιοδου με βασικους στο γηπεδο (0-1, 1 = και οι 5 ολη την 4η)
   q4c_close  = το ιδιο ΜΟΝΟ οταν η διαφορα ειναι ≤8 ποντους (κοντινο ματς)
   close_core = μεριδιο βασικων στα τελευταια 5′ της 4ης με διαφορα ≤6 («ποιος κλεινει το ματς»)
  Συγκριση με τον ΜΕΣΟ ΟΡΟ της ιδιας ομαδας στα προηγουμενα ματς (Δ) → «αλλαξε συμπεριφορα;».
Εξοδος: nba_tests/_t25_feats.csv (ενα ανα ομαδα-ματς) + t25_lineups_out.txt (ελεγχος παραδειγματος + γκρουπ Μαρ/Απρ)."""
import os, sys, json, collections, datetime as dt
import numpy as np, pandas as pd
SC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SC)
sys.stdout.reconfigure(encoding='utf-8')
out = []
def P(s=''): print(s, flush=True); out.append(str(s))

def mmss(x):
    try:
        x = str(x)
        if ':' in x: m, s = x.split(':'); return int(m) + int(s) / 60
        return float(x)
    except Exception: return 0.0

def game_feats(g):
    """→ {ομαδα: dict(sec={pid: δευτ. στο γηπεδο ανα περιοδο}, q4=[(pid_set, dur, margin_for_team, secs_left)], mins={pid: λεπτα box})}"""
    box = g['box']; tid = g['team_ids']; home = g['teams']['home']
    team_of = {pid: v[0] for pid, v in box.items()}
    played = {pid for pid, v in box.items() if mmss(v[3]) > 0 and not v[4]}
    plays = [p for p in g['plays'] if p[0] is not None and p[1] is not None]
    per = collections.defaultdict(list)
    for p in plays: per[p[0]].append(p)
    on = {t: set(pid for pid, v in box.items() if v[0] == t and v[2]) for t in set(team_of.values())}
    res = {t: dict(sec=collections.Counter(), q4=[]) for t in on}
    for q in sorted(per):
        ev = per[q]
        if q > 1:                                                     # πενταδα αρχης περιοδου
            first = {t: set() for t in on}; entered = set()
            for p in ev:
                ids = [x for x in p[4] if x in team_of]
                if p[5] and len(ids) >= 2:
                    inn, outp = ids[0], ids[1]
                    if outp not in entered: first[team_of[outp]].add(outp)
                    entered.add(inn)
                else:
                    for x in ids:
                        if x not in entered and x in played: first[team_of[x]].add(x)
            for t in on:
                f = first[t]
                if len(f) < 5:
                    for x in on[t]:
                        if len(f) >= 5: break
                        if x not in f and x not in entered: f.add(x)
                if len(f) == 5: on[t] = set(f)
        plen = 720 if q <= 4 else 300
        last_clock = plen
        for p in ev:
            c = min(max(p[1], 0), plen); dur = max(last_clock - c, 0)
            if dur > 0:
                for t in on:
                    for x in on[t]: res[t]['sec'][x] += dur
                    if q == 4:
                        mg = (p[2] or 0) - (p[3] or 0); mg = mg if t == home else -mg
                        res[t]['q4'].append((frozenset(on[t]), dur, mg, c))
            last_clock = c
            ids = [x for x in p[4] if x in team_of]
            if p[5] and len(ids) >= 2:
                inn, outp = ids[0], ids[1]; t = team_of[outp]
                if team_of.get(inn) == t:
                    on[t].discard(outp); on[t].add(inn)
        if last_clock > 0:
            for t in on:
                for x in on[t]: res[t]['sec'][x] += last_clock
                if q == 4: res[t]['q4'].append((frozenset(on[t]), last_clock, 0, 0))
    for t in res: res[t]['mins'] = {pid: mmss(v[3]) for pid, v in box.items() if v[0] == t}
    return res

rows = []; AUD = []
for s in (2022, 2023, 2024, 2025, 2026):
    fn = os.path.join(ROOT, f'nba_pbp/pbp_{s}.jsonl')
    games = [json.loads(l) for l in open(fn, encoding='utf-8')]
    games.sort(key=lambda g: g['date'])
    hist = collections.defaultdict(list)                              # ομαδα → [mins dict ανα προηγουμενο ματς]
    prevf = collections.defaultdict(list)
    for g in games:
        try: F = game_feats(g)
        except Exception as e: continue
        d_et = (dt.datetime.fromisoformat(g['date'].replace('Z', '+00:00')) - dt.timedelta(hours=5)).date()
        for t, r in F.items():
            H = hist[t]
            if len(H) >= 10:
                tot = collections.Counter()
                for m in H:
                    for pid, x in m.items(): tot[pid] += x
                order = [pid for pid, _ in tot.most_common()]
                core, rot = set(order[:5]), set(order[:8])
                mins = r['mins']; T = sum(mins.values()) or 240
                q4 = r['q4']; q4t = sum(x[1] for x in q4) or 1
                f = dict(sea=s, date=str(d_et), team=t, opp=[x for x in F if x != t][0], home=(t == g['teams']['home']), gid=g['id'],
                         core_min=sum(mins.get(p, 0) for p in core), core_dnp=sum(1 for p in core if mins.get(p, 0) <= 0),
                         fringe_sh=sum(x for p, x in mins.items() if p not in rot) / T,
                         q4_core=sum(len(x[0] & core) * x[1] for x in q4) / (5 * q4t))
                cl = [x for x in q4 if abs(x[2]) <= 8]; ct = sum(x[1] for x in cl)
                f['q4c_close'] = sum(len(x[0] & core) * x[1] for x in cl) / (5 * ct) if ct >= 120 else np.nan
                ce = [x for x in q4 if x[3] <= 300 and abs(x[2]) <= 6]; cet = sum(x[1] for x in ce)
                f['close_core'] = sum(len(x[0] & core) * x[1] for x in ce) / (5 * cet) if cet >= 60 else np.nan
                for nm_, cond in (('q4c_trail10', lambda mg: mg <= -10), ('q4c_lead10', lambda mg: mg >= 10)):   # 21/10 (Στελιος: «παρατανε οι αουτσαιντερ;»)
                    zz = [x for x in q4 if cond(x[2])]; zt = sum(x[1] for x in zz)
                    f[nm_] = sum(len(x[0] & core) * x[1] for x in zz) / (5 * zt) if zt >= 120 else np.nan
                pv = prevf[t]
                for k in ('core_min', 'fringe_sh', 'q4_core', 'q4c_close', 'close_core', 'q4c_trail10', 'q4c_lead10'):
                    xs = [z[k] for z in pv if np.isfinite(z[k])]
                    f[k + '_avg'] = float(np.mean(xs)) if xs else np.nan
                if len(AUD) < 2 and s == 2024 and t in ('BOS',) and d_et.month == 4:
                    AUD.append((g, t, core, r))
                rows.append(f); prevf[t].append(f)
            H.append(r['mins'])
    P(f'{s}: {len(games)} ματς · {sum(1 for r in rows if r["sea"] == s)} ομαδα-ματς με ≥10 ιστορικο')
X = pd.DataFrame(rows)
# ελεγχος: συνολο δευτ. στο γηπεδο ανα ομαδα ≈ 5 × διαρκεια
P(''); P('=== ΕΛΕΓΧΟΣ ΑΝΑΣΥΝΘΕΣΗΣ ===')
for g, t, core, r in AUD:
    box = g['box']; nm = {pid: v[1] for pid, v in box.items()}
    P(f"  {g['date'][:10]} {g['teams']} · ομαδα {t} · βασικοι (απο ιστορικο): {[nm.get(p, p) for p in core]}")
    for pid, sec in r['sec'].most_common():
        P(f"     {nm.get(pid, pid):24s} ανασυνθεση {sec / 60:5.1f}′ · box {r['mins'].get(pid, 0):4.0f}′")
X.to_csv(os.path.join(SC, '_t25_feats.csv'), index=False)
open(os.path.join(SC, 't25_lineups_out.txt'), 'w', encoding='utf-8').write('\n'.join(out))
