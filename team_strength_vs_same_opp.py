"""team_strength_vs_same_opp.py — 13/10/2026 (Στελιος: «απεναντι στους ιδιους αντιπαλους; αν η ομαδα του 0.5 πεφτει στο 0.25, θα πεφτει και η 0.25 στο 0.125
— αρα δεν εξηγειται γιατι ολοι ερχονται προς τον μεσο· δηλαδη και οι χειροτερες παιζουν καλυτερα;»).
ΑΠΤΟΣ ΕΛΕΓΧΟΣ, Europa + Conference 4 σεζον, τελικη (live) προβλεψη:
  αντιπαλοι σε ΟΜΑΔΕΣ ιδιας απολυτης δυναμης (δυναμη ομαδας + επιπεδο λιγκας, τριτημορια: αδυναμοι / μεσαιοι / δυνατοι)
  και για καθε ομαδα αντιπαλων: οι ΔΙΚΕΣ μας ομαδες χωρισμενες σε αδυναμες / μεσαιες / δυνατες (ιδιο μετρο)
  → διαφορα γκολ: προβλεψη / πραγματικο / xG · «πραγμ − προβλ» > 0 = πηγε ΚΑΛΥΤΕΡΑ απ οσο περιμεναμε.
Ερωτημα: πεφτουν μονο οι δυνατες (ολοι χαμηλωνουν) ή ανεβαινουν και οι αδυναμες (ολοι πανε προς τη μεση);
+ ιδιο για Champions League (συγκριση).
"""
import sys, os, glob
_src = open('euro_live_projections.py', encoding='utf-8').read()
_cut = _src.index('# ================================================================ ΠΕΡΣΙΝΑ ΕΥΡΩΠΑΪΚΑ -> PRIOR')
_DEV = open(os.devnull, 'w', encoding='utf-8'); _REAL = sys.stdout; sys.stdout = _DEV
exec(_src[:_cut])
sys.stdout = _REAL; sys.stdout.reconfigure(encoding='utf-8')
import pickle as _pk
R = pd.read_pickle('nonfm_rating_decomp_rows.pkl'); R['mid'] = R.mid.astype(str)
_V = _pk.load(open('euro_v6_preds.pkl', 'rb')); LV = {str(m): (a, b) for m, a, b in zip(_V['mids'], _V['lh'], _V['la'])}
R = R[R.mid.isin(LV)].copy(); R['lh'] = [LV[m][0] for m in R.mid]; R['la'] = [LV[m][1] for m in R.mid]
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(k)] = m
def xgs(mid):
    m = EUM.get(mid)
    if not m or not m.get('shots'): return np.nan, np.nan
    h, a = int(m['home']['id']), int(m['away']['id'])
    f = lambda t: sum(s['xg'] for s in m['shots'] if s.get('xg') is not None and int(s['tid']) == t)
    return f(h), f(a)
X = [xgs(m) for m in R.mid]; R['xh'] = [a for a, b in X]; R['xa'] = [b for a, b in X]
# μια γραμμη ανα ΠΛΕΥΡΑ: απολυτη δυναμη = t/2 + ρ·s(λιγκα)
S = []
for r in R.itertuples():
    sh_, sa_ = RHO * s_v4(r.lgh), RHO * s_v4(r.lga)
    S.append(dict(comp=r.comp, own=r.th / 2 + sh_, opp=r.ta / 2 + sa_, pred=r.lh - r.la, act=r.gh - r.ga, xgd=r.xh - r.xa, lo=r.lh, go=r.gh, xo=r.xh, lp=r.la, gp=r.ga, xp=r.xa))
    S.append(dict(comp=r.comp, own=r.ta / 2 + sa_, opp=r.th / 2 + sh_, pred=r.la - r.lh, act=r.ga - r.gh, xgd=r.xa - r.xh, lo=r.la, go=r.ga, xo=r.xa, lp=r.lh, gp=r.gh, xp=r.xh))
S = pd.DataFrame(S)
for lab, m_ in (('EUROPA + CONFERENCE', S.comp.isin(['EuropaLeague', 'ConferenceLeague'])), ('CHAMPIONS LEAGUE (συγκριση)', S.comp == 'ChampionsLeague')):
    x = S[m_].copy()
    x['ob'] = pd.qcut(x.opp, 3, labels=['αδυναμοι', 'μεσαιοι', 'δυνατοι'])
    x['wb'] = pd.qcut(x.own, 3, labels=['ΑΔΥΝΑΜΕΣ', 'ΜΕΣΑΙΕΣ', 'ΔΥΝΑΤΕΣ'])
    print(f'\n===== {lab} — διαφορα γκολ απο τη δικη μας σκοπια: προβλεψη / πραγματικο / xG · πραγμ − προβλ (+ = καλυτερα απ οσο περιμεναμε)')
    for ob, y in x.groupby('ob', observed=True):
        print(f'   ΑΝΤΙΠΑΛΟΙ {ob}:')
        for wb, z in y.groupby('wb', observed=True):
            if len(z) < 15: print(f'      δικες μας {wb:8s} n{len(z):3d} (λιγα)'); continue
            se = (z.act - z.pred).std() / np.sqrt(len(z))
            print(f'      δικες μας {wb:8s} n{len(z):3d} · προβλ {z.pred.mean():+.2f} · πραγμ {z.act.mean():+.2f} · xG {z.xgd.mean():+.2f} · '
                  f'πραγμ − προβλ {(z.act - z.pred).mean():+.2f}±{se:.2f} (xG − προβλ {(z.xgd - z.pred).mean():+.2f})')
    print('   ΣΥΝΟΛΙΚΑ ανα δικη μας δυναμη (ολοι οι αντιπαλοι):')
    for wb, z in x.groupby('wb', observed=True):
        se = (z.act - z.pred).std() / np.sqrt(len(z))
        print(f'      {wb:8s} n{len(z):4d} · προβλ {z.pred.mean():+.2f} · πραγμ {z.act.mean():+.2f} · πραγμ − προβλ {(z.act - z.pred).mean():+.2f}±{se:.2f}')

print(chr(10) + '===== ΠΟΙΟΣ ΚΙΝΕΙΤΑΙ; ΓΚΟΛ ΚΑΘΕ ΠΛΕΥΡΑΣ (προβλεψη / πραγματικα / xG) στα ματς ΔΥΝΑΤΗ vs ΑΔΥΝΑΜΗ (ακρα τριτημορια)')
for lab, m_ in (('EUROPA + CONFERENCE', S.comp.isin(['EuropaLeague', 'ConferenceLeague'])), ('CHAMPIONS LEAGUE', S.comp == 'ChampionsLeague')):
    x = S[m_].copy(); qo = x.own.quantile([1/3, 2/3]).values
    z = x[(x.own >= qo[1]) & (x.opp <= qo[0])]          # η δικη μας ΔΥΝΑΤΗ, ο αντιπαλος ΑΔΥΝΑΜΟΣ
    print(f'   {lab}: {len(z)} ματς δυνατη vs αδυναμη')
    print(f'      η ΔΥΝΑΤΗ βαζει:   προβλ {z.lo.mean():.2f} · πραγμ {z.go.mean():.2f} · xG {z.xo.mean():.2f} → {z.go.mean() - z.lo.mean():+.2f}')
    print(f'      η ΑΔΥΝΑΜΗ βαζει:  προβλ {z.lp.mean():.2f} · πραγμ {z.gp.mean():.2f} · xG {z.xp.mean():.2f} → {z.gp.mean() - z.lp.mean():+.2f}')
