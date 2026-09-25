"""
intl_callups_validate.py — ΕΠΑΛΗΘΕΥΣΗ ΟΤΙ Η ΚΛΗΣΗ TRANSFERMARKT ΕΙΝΑΙ Η ΤΡΕΧΟΥΣΑ (25/9/2026, εντολη Στελιου «βεβαιωσου οτι ειναι οντως αυτη»).
Για καθε ομαδα που εχει ΗΔΗ παιξει στο τρεχον παραθυρο (FotMob αποστολη = 11 βασικοι + ολος ο παγκος, intl_squads.json):
  καλυψη = ποσοι απο οσους ΝΤΥΘΗΚΑΝ υπαρχουν στη λιστα κλησης TM (intl_vcall_tm.json 'called').
    ≥90% → η λιστα ειναι η τρεχουσα ✓ · 75-90% → ελεγχος · <75% → ΛΑΘΟΣ/παλια λιστα ✗
  αποχωρησαν = ντυθηκαν σε ματς του παραθυρου ΠΡΙΝ το τραβηγμα αλλα ΔΕΝ ειναι πια στη λιστα TM (τραυματισμος/αποχωρηση, π.χ. Brobbey 24/9 —
  διορθωση Στελιου: η λιστα TM ειναι η αποστολη που θα παιξει, αυτοι ΛΕΙΠΟΥΝ στο επομενο ματς). Ελεγχος τους με ειδησεις αν ειναι σημαντικοι.
Ομαδες που δεν εχουν παιξει ακομα: δεν επαληθευονται εδω (ξανατρεχει μετα το 1ο τους ματς).
Εξοδος: intl_callups_validate_out.txt
"""
import sys, json, glob, datetime as dt
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, '.')
src = open('intl_callups_tm.py', encoding='utf-8').read(); ns = {}
exec(src[src.index('import sys'):src.index('# ονομα intl -> ονομα TM rank-map')], ns)
norm = ns['norm']
VC = json.load(open('intl_vcall_tm.json', encoding='utf-8'))
import os
NAMES_P = json.load(open('intl_player_names.json', encoding='utf-8'))   # pid -> ονομα (συμπαγες, απο intl_player_values· τρεχει και στο Actions)
SQ = json.load(open('intl_squads.json', encoding='utf-8'))
M = pd.read_csv('intl_matches.csv', dtype={'mid': str}, parse_dates=['date'])
out = []
def P_(s=''):
    print(s, flush=True); out.append(str(s))


name_in_call = ns['name_in_call']


asof = min((v.get('asof') or '9999') for v in VC.values())
win0 = pd.Timestamp('2026-09-20')                     # αρχη τρεχοντος διεθνους παραθυρου (21/9-6/10/2026)
R = M[(M.date >= win0) & M.mid.isin(SQ.keys())]
P_(f'ΕΠΑΛΗΘΕΥΣΗ ΚΛΗΣΕΩΝ TRANSFERMARKT (τραβηγμα {asof} UTC) με τις αποστολες FotMob των ματς απο {win0.date()}')
rows = []
for r in R.itertuples():
    for k, tid, nm in (('h', r.hid, r.hn), ('a', r.aid, r.an)):
        v = VC.get(str(tid))
        if not v or not v.get('called'):
            continue
        dressed = [(p, NAMES_P.get(str(p)) or '') for p in ((SQ[r.mid].get(k) or {}).get('p') or {})]
        dressed = [(p, n) for p, n in dressed if n]
        miss = [n for p, n in dressed if not name_in_call(n, v['called'])]
        false_abs = [m['nm'] for m in v.get('missing', []) if any(int(m['pid']) == int(p) for p, _ in dressed)]
        cov = 1 - len(miss) / len(dressed) if dressed else float('nan')
        rows.append(dict(team=nm, match=f'{r.hn} - {r.an}', date=str(r.date)[:10], dressed=len(dressed), cov=cov, not_in_call=miss, false_abs=false_abs, n_call=v['n_sq']))
rows.sort(key=lambda x: x['cov'])
for x in rows:
    verdict = '✓ τρεχουσα' if x['cov'] >= 0.90 else ('? ελεγχος' if x['cov'] >= 0.75 else '✗ ΛΑΘΟΣ/ΠΑΛΙΑ')
    P_(f"  {x['team']:22s} {x['date']} ({x['match']}): ντυθηκαν {x['dressed']:2d} · στη λιστα TM {x['cov'] * 100:5.1f}% · κληση TM {x['n_call']} · {verdict}"
       + (f" · ντυθηκαν αλλα ΔΕΝ ειναι πια στη λιστα (αποχωρησαν;): {', '.join(x['not_in_call'][:5])}" if x['not_in_call'] else '')
       + (f" · σημαια «λειπει» για το επομενο ματς: {', '.join(x['false_abs'])}" if x['false_abs'] else ''))
if rows:
    ok = sum(1 for x in rows if x['cov'] >= 0.90)
    P_(f'\nΣΥΝΟΛΟ: {ok}/{len(rows)} ομαδες-ματς με ≥90% καλυψη · μεση καλυψη {sum(x["cov"] for x in rows) / len(rows) * 100:.1f}% · '
       f'αποχωρησαν μετα απο ματς του παραθυρου (βασικοι με σημαια) {sum(len(x["false_abs"]) for x in rows)}')
played = {x['team'] for x in rows}
P_(f'ομαδες με κληση που ΔΕΝ εχουν παιξει ακομα (ανεπαληθευτες): {sorted(v["nm"] for v in VC.values() if v["nm"] not in played)}')
open('intl_callups_validate_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
