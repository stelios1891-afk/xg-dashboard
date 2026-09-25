"""
intl_refresh.py — ΑΥΤΟΜΑΤΗ ΑΝΑΝΕΩΣΗ ΕΘΝΙΚΩΝ μετα απο καθε αγωνιστικη (25/9/2026, εντολη Στελιου: «να περναει τα αποτελεσματα οπως στα εγχωρια»).
Τρεχει στο GitHub Actions (intl-refresh.yml) — και τοπικα με τον ιδιο τροπο.

1. FotMob: ελεγχει ποια ματς της ΤΡΕΧΟΥΣΑΣ σεζον τελειωσαν (NL A-D 2026/27, AFCONQ 2026/27, φιλικα 2026) και κατεβαζει ΜΟΝΟ τα νεα
   (σκορ, σουτ/xG, κοκκινες, ενδεκαδες) — intl_fetch.py (resumable: οσα υπαρχουν δεν ξανακατεβαινουν).
2. Αν ΔΕΝ υπαρχει νεο ματς → τελος (τιποτα δεν αλλαζει).
3. Αλλιως ξαναχτιζει ολη την αλυσιδα με τον ΙΔΙΟ κωδικα που τρεχαμε τοπικα:
     intl_build.py        → intl_matches.csv (ενιαια βαση, κλειδι ασφαλειας για διπλα)
     intl_rating2_hist.py → Elo + xElo (Μοντελο 1, rating H3) → intl_ratings_h.csv, intl_preds_H.csv
     intl_mkt_anchor.py   → rating με αγκυρα αγορας (Μοντελα 2/3, λ=0.3)· closing Crown ιστορικα + closing Odds API για τα νεα ματς
     intl_project.py      → προβολες επομενων ματς (10 ημερες) → intl_projections.csv
     intl_nl_shadow.py, intl_nl_overs.py, intl_afconq_shadow_v.py (με τις τελευταιες γραμμες Nowgoal που υπαρχουν) — μη κρισιμα
     intl_dashboard_build.py → intl_projections_dashboard.json (tab 🌐 + Value Picks)
   Αν σπασει κρισιμο βημα: επαναφερει ΟΛΑ τα αρχεια οπως ηταν (ποτε μισο-ανανεωμενο μοντελο) και βγαινει με σφαλμα.
4. Αναφορα: ποια ματς περαστηκαν (σκορ, xG) και ποσο αλλαξε το rating καθε ομαδας (Μ1 και αγκυρα) → intl_refresh_log.jsonl + Telegram.

Χρηση: python intl_refresh.py            (κανονικα)
       python intl_refresh.py --force    (ξαναχτιζει και χωρις νεα ματς)
"""
import os, sys, json, shutil, subprocess, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT); sys.path.insert(0, ROOT)
CUR = {   # μονο οι σεζον που «τρεχουν» τωρα (οι παλιες δεν αλλαζουν)
    'NationsLeagueA': (9806, ['2026/2027']), 'NationsLeagueB': (9807, ['2026/2027']),
    'NationsLeagueC': (9808, ['2026/2027']), 'NationsLeagueD': (9809, ['2026/2027']),
    'AFCONQ': (10608, ['2026/2027']), 'Friendlies': (114, ['2026']),
}
CRITICAL = ['intl_build.py', 'intl_rating2_hist.py', 'intl_mkt_anchor.py', 'intl_project.py']
OPTIONAL = ['intl_nl_shadow.py', 'intl_nl_overs.py', 'intl_afconq_shadow_v.py', 'intl_dashboard_build.py']
OUTPUTS = ['intl_matches.csv', 'intl_ratings_h.csv', 'intl_preds_H.csv', 'intl_hfa_config.json', 'intl_preds_anchor.csv',
           'intl_ratings_anchor.csv', 'intl_projections.csv', 'intl_nl_shadow_2627.csv', 'intl_nl_overs_2627.csv',
           'intl_afconq_shadow_2627.csv', 'intl_afconq_overs_2627.csv', 'intl_projections_dashboard.json']
LOG_F = 'intl_refresh_log.jsonl'
BAK = os.path.join(ROOT, '.intl_refresh_bak')


def _read_csv(f, **kw):
    try:
        return pd.read_csv(f, **kw)
    except Exception:
        return None


def ratings(f, col='R'):
    d = _read_csv(f)
    if d is None:
        return {}
    d = d.set_index(d.columns[0])
    return {int(k): float(v) for k, v in d[col].items()}


def run(script):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', INTL_PIN_VARIANT='H3')      # Μοντελο 1 = H3 (κλειδωμενο)
    if not os.path.isdir('nowgoal_intl_odds'):
        env['INTL_CLOSE_COMPACT'] = '1'
    r = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    tail = '\n'.join((r.stdout or '').strip().splitlines()[-3:])
    print(f'  {script}: {"OK" if r.returncode == 0 else "ΣΦΑΛΜΑ " + str(r.returncode)}' + (f'\n    ' + tail.replace('\n', '\n    ') if tail else ''), flush=True)
    if r.returncode != 0:
        print('    ' + '\n    '.join((r.stderr or '').strip().splitlines()[-6:]), flush=True)
    return r.returncode == 0


def backup():
    shutil.rmtree(BAK, ignore_errors=True); os.makedirs(BAK)
    for f in OUTPUTS:
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(BAK, f))


def restore():
    for f in OUTPUTS:
        b = os.path.join(BAK, f)
        if os.path.exists(b):
            shutil.copy2(b, f)
    print('  ΕΠΑΝΑΦΟΡΑ: ολα τα αρχεια του μοντελου γυρισαν οπως ηταν πριν', flush=True)


def report(M0_mids, R0, RA0):
    M = pd.read_csv('intl_matches.csv', dtype={'mid': str, 'season': str})
    new = M[~M.mid.isin(M0_mids)].sort_values('date')
    R1, RA1 = ratings('intl_ratings_h.csv'), ratings('intl_ratings_anchor.csv')
    names = {}
    for r in M.itertuples():
        names[int(r.hid)] = r.hn; names[int(r.aid)] = r.an
    games = []
    for r in new.rename(columns={'as': 'as_'}).itertuples():
        games.append(dict(mid=r.mid, date=str(r.date)[:16], comp=r.comp, home=r.hn, away=r.an, score=f'{int(r.hs)}-{int(r.as_)}',
                          xg=(f'{r.xg_h:.2f}-{r.xg_a:.2f}' if bool(r.has_xg) else None), src=r.src))
    teams = sorted({int(t) for t in pd.concat([new.hid, new.aid])}) if len(new) else []
    elo = []
    for t in teams:
        elo.append(dict(tid=t, team=names.get(t, str(t)),
                        m1_before=round(R0[t]) if t in R0 else None, m1_after=round(R1[t]) if t in R1 else None,
                        anc_before=round(RA0[t]) if t in RA0 else None, anc_after=round(RA1[t]) if t in RA1 else None))
    return games, elo


def tg_text(games, elo):
    out = [f'🌐 ΕΘΝΙΚΕΣ · ανανεωση μοντελου: {len(games)} νεα αποτελεσματα']
    for g in games:
        out.append(f"{g['comp'].replace('NationsLeague', 'NL ')} · {g['home']} {g['score']} {g['away']}" + (f"  (xG {g['xg']})" if g['xg'] else ''))
    mv = [e for e in elo if e['m1_before'] is not None and e['m1_after'] is not None]
    mv.sort(key=lambda e: -abs(e['m1_after'] - e['m1_before']))
    if mv:
        out.append('\nΜεγαλυτερες αλλαγες Elo (Μ1 · αγκυρα):')
        for e in mv[:8]:
            a = f" · {e['anc_after'] - e['anc_before']:+d}" if (e['anc_before'] is not None and e['anc_after'] is not None) else ''
            out.append(f"{e['team']}: {e['m1_before']}→{e['m1_after']} ({e['m1_after'] - e['m1_before']:+d}){a}")
    out.append('\nΠροβολες/picks ξαναυπολογιστηκαν για τα επομενα ματς.')
    return '\n'.join(out)


def main(force=False):
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M')
    M0 = _read_csv('intl_matches.csv', dtype={'mid': str})
    M0_mids = set(M0.mid) if M0 is not None else set()
    R0, RA0 = ratings('intl_ratings_h.csv'), ratings('intl_ratings_anchor.csv')
    import intl_fetch as F
    F.COMPS = CUR
    print(f'[{now} UTC] 1. FotMob — τελειωμενα ματς τρεχουσας σεζον', flush=True)
    n_new = F.main() or 0
    if n_new == 0 and not force:
        print('καμια νεα αναμετρηση — τιποτα δεν αλλαζει', flush=True); return 0
    print(f'2. {n_new} νεα ματς απο FotMob → ξαναχτισιμο μοντελου', flush=True)
    backup()
    for s in CRITICAL:
        if not run(s):
            restore(); return 1
    for s in OPTIONAL:
        run(s)
    games, elo = report(M0_mids, R0, RA0)
    rec = dict(t=now, n_fetched=n_new, n_new_matches=len(games), games=games, elo=elo)
    with open(LOG_F, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    txt = tg_text(games, elo); print('\n' + txt, flush=True)
    if games and os.environ.get('TELEGRAM_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'):
        import notify
        notify.send(txt, silent=True)
    shutil.rmtree(BAK, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(force='--force' in sys.argv))
