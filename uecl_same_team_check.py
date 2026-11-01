"""uecl_same_team_check.py — 12/10/2026 (Στελιος: «πως η ιδια ομαδα, πχ ΠΑΟΚ, με ομαδα Α την υποτιμαμε και με ομαδα Β την υπερτιμαμε, με 15 μερες
διαφορα; δεν μου καθεται καλα»). Conference League 4 σεζον.
  1) ΙΔΙΕΣ ΟΜΑΔΕΣ (FotMob, με ματς και στην Α και στη Β): γκολ / xG / μοντελο σε καθε κατηγορια — το μοντελο τις «βλεπει» διαφορετικα;
  2) ΠΟΙΟΤΗΤΑ ΣΟΥΤ της ομαδας FotMob: σουτ, xG ανα σουτ, ποσοστο γκολ ανα κατηγορια φασης (μικρη <0.1 / μεσαια / μεγαλη ≥0.3) — Α vs Β
  3) ΤΟ ΙΔΙΟ στο Europa και στο Champions League (για να φανει αν ειναι κανονικοτητα ή τυχη του Conference)
"""
import sys
exec(open('ucl_nonfm_teams.py', encoding='utf-8').read().split('# ===== 1 =====')[0])
NL = chr(10)
S['tid'] = [int(EUM[str(MIDS[i])]['home' if v == 'εντος' else 'away']['id']) for i, v in zip(S.i, S.venue)]
S['fav'] = [r.lam >= S.loc[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')], 'lam'] for r in S.itertuples()]
def shots(i, tid):
    return [s for s in (EUM[str(MIDS[i])].get('shots') or []) if s.get('xg') is not None and int(s['tid']) == tid and s.get('sit') != 'Penalty']
def line(x, lab, w=32):
    if len(x) < 8: return f'   {lab:{w}s} n{len(x):3d} (λιγα)'
    return (f'   {lab:{w}s} n{len(x):3d} · γκολ {x.g.mean():.2f} · xG {x.xg.mean():.2f} · μοντελο {x.lou.mean():.2f} · '
            f'ΔΗΜΙΟΥΡΓΙΑ {(x.xg - x.lou).mean():+.2f} · ΦΙΝΙΡΙΣΜΑ {(x.g - x.xg).mean():+.2f}±{se(x.g - x.xg):.2f}')
for cm in ('UECL', 'UEL', 'UCL'):
    X = S[(S.comp == cm) & (S.src == 'FotMob') & S['cat'].isin(['Α', 'Β'])]
    both = set(X[X['cat'] == 'Α'].team) & set(X[X['cat'] == 'Β'].team)
    Y = X[X.team.isin(both)]
    print(f'{NL}===== {cm} =====')
    print(f'1. ΙΔΙΕΣ ομαδες FotMob με ματς ΚΑΙ στην Α ΚΑΙ στη Β: {len(both)} ομαδες')
    for c in ('Α', 'Β'):
        print(line(Y[Y['cat'] == c], f'οι ιδιες ομαδες στην {c}'))
        for fv, fl in ((True, 'ως φαβορι'), (False, 'ως αουτσαιντερ')):
            print(line(Y[(Y['cat'] == c) & (Y.fav == fv)], f'   {fl}'))
    print('2. ΣΟΥΤ της ομαδας FotMob (χωρις πεναλτι): ανα ματς σουτ · xG/σουτ · μετατροπη ανα φαση (γκολ/σουτ)')
    for c in ('Α', 'Β'):
        sh = [s for r in X[X['cat'] == c].itertuples() for s in shots(r.i, r.tid)]; n = len(X[X['cat'] == c])
        if not sh: continue
        xg = np.array([s['xg'] for s in sh]); gl = np.array([1.0 if s.get('goal') else 0.0 for s in sh])
        cells = []
        for lo, hi, lb in ((0, .1, 'μικρες <0.1'), (.1, .3, 'μεσαιες'), (.3, 1.1, 'μεγαλες ≥0.3')):
            m = (xg >= lo) & (xg < hi)
            cells.append(f'{lb}: {m.sum() / n:.1f}/ματς, γκολ {100 * gl[m].mean():.0f}% vs xG {100 * xg[m].mean():.0f}%')
        print(f'   {c}: {len(sh) / n:.1f} σουτ/ματς · xG/σουτ {xg.mean():.3f} · γκολ/σουτ {gl.mean():.3f} (διαφορα {100 * (gl.mean() - xg.mean()):+.1f} μον.) · ' + ' · '.join(cells))
