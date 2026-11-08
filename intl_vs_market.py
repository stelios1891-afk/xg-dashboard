"""
intl_vs_market.py — ΒΗΜΑ 4: rating εθνικων (B, E0, X3, EXT) ΕΝΑΝΤΙΟΝ closing αγορας (Nowgoal Crown 1Χ2 + AH).
ΠΡΟ-ΔΗΛΩΣΗ (19/9/2026, γραφτηκε ΠΡΙΝ κατεβουν οι αποδοσεις· ΜΙΑ εκτελεση):
  Δειγμα: αγωνιστικα ματς (nl/qual/tourn) με closing 1Χ2 Crown (τελευταια pre-match row· αν δεν κρατιεται [παλια ματς],
  proxy = πρωτη in-play row στο 0-0 εως το 3').
  Μ1 (βαθμονομηση αγορας): RPS της αγορας (χωρις γκανιοτα, ισοποσοστιαια) vs RPS του rating B (LOSO logit οπως πριν).
  Μ2 (προστιθεμενη αξια): logit-blend  z = w*logit_model + (1-w)*logit_market ανα αποτελεσμα, w fit LOSO ανα σεζον·
      «το rating προσθετει» ΜΟΝΟ αν w >= 0.15 ΚΑΙ ΔRPS(blend − αγορα) <= −0.0010 ΚΑΙ καλυτερο σε >= 4/5 σεζον.
  Μ3 (τυφλο value AH): οπου το rating διαφωνει με τη γραμμη κατα >= 8% (fair vs closing AH Crown, χωρις γκανιοτα),
      ROI στο closing· αναφορα μονο, δεν αποφασιζει.
  Ανα τυπο (nl/qual/tourn) και ανα NL league (A/B/C/D) — αναφορα.
Πηγες: nowgoal_intl_odds/{comp}.jsonl (cid=3 Crown), nowgoal_intl_map.json, intl_preds_*.csv, intl_matches.csv.
Συμβασεις Nowgoal: op rows odds {u: home, g: draw, d: away} (δεκαδικες)· ah rows {g: γραμμη, u: home odds HK, d: away HK}·
  γραμμη g>0 = ο γηπεδουχος ΔΙΝΕΙ (line_home = −g) (οπως στα ευρωπαικα)· pre-match = ht in ('', None).
"""
import sys, os, json, glob, math
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import picks

_src = open('intl_rating.py', encoding='utf-8').read(); _ns = {'np': np}
exec(_src[_src.index('def sig(x):'):_src.index("EVAL_SEASONS = ")], _ns)
sig, nelder_mead, fit_ol, probs, rps, logloss = _ns['sig'], _ns['nelder_mead'], _ns['fit_ol'], _ns['probs'], _ns['rps'], _ns['logloss']
CID = 3
SEAS = ['2122', '2223', '2324', '2425', '2526']


def hk(x):
    try:
        v = float(x); return v + 1 if v < 1.5 else v      # HK -> δεκαδικη (αν ηδη δεκαδικη, μενει)
    except Exception:
        return None


# ---- closing απο Nowgoal ----
MAP = json.load(open('nowgoal_intl_map.json', encoding='utf-8'))
close = {}
for f in glob.glob('nowgoal_intl_odds/*.jsonl'):
    for line in open(f, encoding='utf-8'):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get('cid') != CID:
            continue
        pre_op = [x for x in (r.get('op') or []) if x[1] in ('', None) and x[4] not in (None, '', '0')]
        # ΤΟ 1Χ2 pre-match ΔΕΝ κρατιεται σε παλια ματς (βλ. μνημη nowgoal) -> proxy closing = η ΠΡΩΤΗ in-play row στο 0-0, λεπτο <= 3
        if not pre_op:
            def _mn(h):
                try:
                    return int(str(h).split('+')[0])
                except Exception:
                    return 99
            early = [x for x in (r.get('op') or []) if x[1] not in ('', None) and (x[2] or 0) + (x[3] or 0) == 0 and _mn(x[1]) <= 3
                     and x[4] not in (None, '', '0') and not x[7]]
            early.sort(key=lambda x: (_mn(x[1]), x[0] or 0))
            pre_op = early[:1]
        pre_ah = [x for x in (r.get('ah') or []) if x[1] in ('', None) and x[4] not in (None, '') and x[5] not in (None, '', '0') and x[6] not in (None, '', '0')]   # 25/9: γραμμη 0 (ισοπαλο handicap) ειναι ΚΑΝΟΝΙΚΗ
        rec = {}
        if pre_op:
            x = pre_op[-1]
            try:
                oh, od, oa = float(x[5]), float(x[4]), float(x[6])       # op: g=draw? -> ελεγχεται στο sanity παρακατω
                rec.update(op=(oh, od, oa), op_raw=x)
            except Exception:
                pass
        if pre_ah:
            x = pre_ah[-1]
            try:
                rec.update(ah_line=-float(x[4]), ah_h=hk(x[5]), ah_a=hk(x[6]))
            except Exception:
                pass
        if rec:
            close[str(r['mid'])] = rec
print(f'closing Crown: {len(close)} ματς (1Χ2: {sum(1 for v in close.values() if "op" in v)}, AH: {sum(1 for v in close.values() if "ah_line" in v)})')
# sanity: ποιο πεδιο ειναι η ισοπαλια — στο 1Χ2 η ισοπαλια εχει σχεδον παντα τη μεγαλυτερη αποδοση απο τη μικροτερη πλευρα
smp = [v['op_raw'] for v in list(close.values())[:400] if 'op_raw' in v]
if smp:
    u = np.array([float(x[5]) for x in smp]); g = np.array([float(x[4]) for x in smp]); d = np.array([float(x[6]) for x in smp])
    print(f'  sanity 1Χ2: μεσοι u={u.mean():.2f} g={g.mean():.2f} d={d.mean():.2f} (η ισοπαλια ~3.3-3.8 περιμενουμε)')

# ---- ενωση με preds ----
M = pd.read_csv('intl_matches.csv', dtype={'season': str, 'mid': str})
preds = {m: pd.read_csv(f'intl_preds_{m}.csv', dtype={'season': str, 'mid': str}) for m in ['B', 'E0', 'X3', 'EXT', 'H']}
D = preds['B'][['mid', 'season', 'ctype', 'comp', 'hn', 'an', 'gd', 'diff']].rename(columns={'diff': 'diff_B'})
for m in ['E0', 'X3', 'EXT', 'H']:
    D = D.merge(preds[m][['mid', 'diff']].rename(columns={'diff': f'diff_{m}'}), on='mid', how='left')
D['y'] = np.where(D.gd > 0, 2, np.where(D.gd == 0, 1, 0))
D['op'] = D.mid.map(lambda m: close.get(m, {}).get('op'))
D['ah_line'] = D.mid.map(lambda m: close.get(m, {}).get('ah_line'))
D['ah_h'] = D.mid.map(lambda m: close.get(m, {}).get('ah_h')); D['ah_a'] = D.mid.map(lambda m: close.get(m, {}).get('ah_a'))
C = D[D.ctype.isin(['nl', 'qual', 'tourn']) & D.op.notna() & D.season.isin(SEAS)].copy()
# αγορα χωρις γκανιοτα
def novig(o):
    inv = np.array([1 / o[0], 1 / o[1], 1 / o[2]]); return inv / inv.sum()
Pm = np.vstack([novig(o) for o in C.op])
C['m_h'], C['m_d'], C['m_a'] = Pm[:, 0], Pm[:, 1], Pm[:, 2]
print(f'αγωνιστικα ματς με closing 1Χ2 (2122-2526): {len(C)} · ανα σεζον {C.season.value_counts().sort_index().to_dict()}')

out = []
def P(s=''):
    print(s); out.append(s)

# ---- Μ1: RPS αγορας vs ratings (LOSO logit για τα ratings) ----
P('\n' + '=' * 100); P('Μ1 — RPS: αγορα (closing, χωρις γκανιοτα) vs ratings (LOSO ordered logit)'); P('=' * 100)
rows = []
mk = dict(variant='ΑΓΟΡΑ closing')
for s in SEAS:
    te = C[C.season == s]
    mk[s] = round(rps(te[['m_h', 'm_d', 'm_a']].values, te['y'].values), 4) if len(te) else np.nan
mk['ALL'] = round(rps(C[['m_h', 'm_d', 'm_a']].values, C['y'].values), 4); mk['n'] = len(C)
rows.append(mk)
for v in ['B', 'H', 'E0', 'X3', 'EXT']:
    col = f'diff_{v}'; CC = C[C[col].notna()]
    row = dict(variant=f'rating {v}'); allP = []; ally = []
    for s in SEAS:
        tr = CC[CC.season != s]; te = CC[CC.season == s]
        if len(te) < 20:
            row[s] = np.nan; continue
        p = fit_ol(tr[col].values, tr['y'].values); Pr = probs(te[col].values, p)
        row[s] = round(rps(Pr, te['y'].values), 4); allP.append(Pr); ally.append(te['y'].values)
    row['ALL'] = round(rps(np.vstack(allP), np.concatenate(ally)), 4); row['n'] = len(CC)
    rows.append(row)
pd.set_option('display.width', 220)
P(pd.DataFrame(rows).set_index('variant').to_string())

# ---- Μ2: blend logit αγορας + rating B ----
P('\n' + '=' * 100); P('Μ2 — προστιθεμενη αξια: z = w*logit(rating) + (1-w)*logit(αγορα), w LOSO'); P('=' * 100)
def blend_eval(col, label):
    CC = C[C[col].notna()].copy(); allP = []; ally = []; ws = []; per = {}
    for s in SEAS:
        tr = CC[CC.season != s]; te = CC[CC.season == s]
        if len(te) < 20:
            continue
        p = fit_ol(tr[col].values, tr['y'].values)
        Ltr = np.log(np.clip(probs(tr[col].values, p), 1e-6, 1)); Lte = np.log(np.clip(probs(te[col].values, p), 1e-6, 1))
        Mtr = np.log(tr[['m_h', 'm_d', 'm_a']].values); Mte = np.log(te[['m_h', 'm_d', 'm_a']].values)
        ytr = tr['y'].values
        def nll(w):
            w = float(np.clip(w[0], 0, 1)); z = w * Ltr + (1 - w) * Mtr; z = z - z.max(1, keepdims=True)
            Pz = np.exp(z) / np.exp(z).sum(1, keepdims=True)
            return -np.sum(np.log(np.clip(Pz[np.arange(len(ytr)), 2 - ytr], 1e-9, 1)))
        w = float(np.clip(nelder_mead(nll, np.array([0.3]), np.array([0.2]))[0], 0, 1)); ws.append(w)
        z = w * Lte + (1 - w) * Mte; z = z - z.max(1, keepdims=True); Pz = np.exp(z) / np.exp(z).sum(1, keepdims=True)
        per[s] = (round(rps(Pz, te['y'].values), 4), round(rps(te[['m_h', 'm_d', 'm_a']].values, te['y'].values), 4), round(w, 2))
        allP.append(Pz); ally.append(te['y'].values)
    Pz = np.vstack(allP); yy = np.concatenate(ally); sub = CC[CC.season.isin(per.keys())]
    r_b = rps(Pz, yy); r_m = rps(sub[['m_h', 'm_d', 'm_a']].values, sub['y'].values)
    better = sum(1 for s, (a, b, w) in per.items() if a < b)
    P(f'{label:10s}: w μεσο {np.mean(ws):.2f} · RPS blend {r_b:.4f} vs αγορα {r_m:.4f} (Δ {r_b - r_m:+.4f}) · καλυτερο σε {better}/{len(per)} σεζον · '
      f'{"ΠΕΡΝΑ" if (np.mean(ws) >= 0.15 and r_b - r_m <= -0.0010 and better >= 4) else "ΔΕΝ ΠΕΡΝΑ"}')
    P('   ανα σεζον (blend, αγορα, w): ' + ' · '.join(f'{s}: {a}/{b}/w{w}' for s, (a, b, w) in per.items()))
for v in ['B', 'H', 'E0', 'X3', 'EXT']:
    blend_eval(f'diff_{v}', f'rating {v}')
P('\n-- ανα τυπο αγωνα (rating B):')
for ct in ['nl', 'qual', 'tourn']:
    sub = C[C.ctype == ct]
    if len(sub) < 60:
        continue
    r_m = rps(sub[['m_h', 'm_d', 'm_a']].values, sub['y'].values)
    allP = []; ally = []
    for s in SEAS:
        tr = C[(C.season != s)]; te = sub[sub.season == s]
        if len(te) < 15:
            continue
        p = fit_ol(tr['diff_B'].values, tr['y'].values); allP.append(probs(te['diff_B'].values, p)); ally.append(te['y'].values)
    r_r = rps(np.vstack(allP), np.concatenate(ally)) if allP else np.nan
    P(f'  {ct:6s} n={len(sub):4d}: αγορα {r_m:.4f} · rating B {r_r:.4f}')
P('\n-- Nations League ανα league (rating B vs αγορα):')
for comp in ['NationsLeagueA', 'NationsLeagueB', 'NationsLeagueC', 'NationsLeagueD']:
    sub = C[C.comp == comp]
    if len(sub) < 30:
        continue
    r_m = rps(sub[['m_h', 'm_d', 'm_a']].values, sub['y'].values)
    P(f'  {comp:16s} n={len(sub):3d}: αγορα RPS {r_m:.4f} · μεσο P(φαβορι) αγορας {np.max(sub[["m_h","m_d","m_a"]].values, 1).mean():.2f}')

# ---- Μ3: τυφλο value AH στο closing (αναφορα) ----
P('\n' + '=' * 100); P('Μ3 — τυφλο «value» AH στο closing Crown (rating B fair vs γραμμη, διαφωνια >= 8%) — ΑΝΑΦΟΡΑ'); P('=' * 100)
A = C[C.ah_line.notna() & C.ah_h.notna() & C.ah_a.notna()].copy()
# supremacy/total οπως στο intl_project: a απο ολο το δειγμα (πλαισιο), συνολο ανα τυπο
MM = M.set_index('mid')
a = float(np.sum(C['diff_B'] * C['gd']) / np.sum(C['diff_B'] ** 2))
tot = {ct: float((M[M.ctype == ct].hs + M[M.ctype == ct]['as']).mean()) for ct in ['nl', 'qual', 'tourn']}
bets = []
for r in A.itertuples():
    s = a * r.diff_B; T = tot.get(r.ctype, 2.7); lh = max((T + s) / 2, 0.15); la = max((T - s) / 2, 0.15)
    dist = picks.gd_dist(lh, la)
    for side, line, odds in ((1, r.ah_line, r.ah_h), (-1, -r.ah_line, r.ah_a)):
        pw, pp = picks.p_cover(dist, side, line)
        if pw <= 0:
            continue
        fair = (1 - pp) / pw
        edge = odds / fair - 1
        if edge >= 0.08 and 1.5 <= odds <= 2.5:
            pnl = picks.settle(r.gd, side, line, odds)
            bets.append(dict(season=r.season, ctype=r.ctype, side=side, edge=edge, odds=odds, pnl=pnl))
Bt = pd.DataFrame(bets)
if len(Bt):
    P(f'bets {len(Bt)} · ROI {Bt.pnl.mean()*100:+.1f}% · ανα σεζον: ' + ' · '.join(f'{s}: {g.pnl.mean()*100:+.1f}% (n{len(g)})' for s, g in Bt.groupby("season")))
    P('ανα τυπο: ' + ' · '.join(f'{s}: {g.pnl.mean()*100:+.1f}% (n{len(g)})' for s, g in Bt.groupby("ctype")))
    P('ανα πλευρα: ' + ' · '.join(f'{"γηπ." if s == 1 else "φιλοξ."}: {g.pnl.mean()*100:+.1f}% (n{len(g)})' for s, g in Bt.groupby("side")))
else:
    P('κανενα bet')
open('intl_vs_market_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
