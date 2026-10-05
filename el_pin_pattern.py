"""
el_pin_pattern.py — ΜΟΤΙΒΟ ΟΡΙΩΝ PINNACLE Ευρωλιγκας (5/10/2026, Στελιος: «να δουμε αν το μοτιβο επαναλαμβανεται»).
Απο το el_pin_hist.jsonl (el_pin_watch, καθε αλλαγη οριου): για καθε ματς ποτε περασε απο καθε σταδιο οριου χαντικαπ/συνολου
(300 → 1500 → 3000 → 6000…), σε ωρα Ελλαδας και ωρες πριν το τζαμπολ· και συνοψη ανα σταδιο (διαμεσος/ευρος ωρων πριν).
ΠΡΟΣΟΧΗ: το «πρωτο» σταδιο ενος ματς ειναι οτι βρηκε η καταγραφη (που ξεκινα 48ω πριν) — αν ηταν ηδη ανοιχτο, δεν ειναι το ανοιγμα.
Χρηση: python el_pin_pattern.py
"""
import json, collections, statistics, datetime as dt, sys
from zoneinfo import ZoneInfo
sys.stdout.reconfigure(encoding='utf-8')
HF = 'ec_pin_hist.jsonl' if 'EC' in sys.argv[1:] else 'el_pin_hist.jsonl'   # python el_pin_pattern.py EC → EuroCup
rows = [json.loads(l) for l in open(HF, encoding='utf-8') if l.strip()]
gr = lambda iso: dt.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(ZoneInfo('Europe/Athens'))
by = collections.defaultdict(list)
for r in rows: by[(r['start'], r['home'], r['away'])].append(r)
stage = collections.defaultdict(list)
for k in sorted(by):
    v = sorted(by[k], key=lambda r: r['t']); ko = gr(k[0]); seen = []
    for i, r in enumerate(v):
        lim = (r.get('sp') or {}).get('lim')
        if not seen or lim != seen[-1][0]:
            seen.append((lim, gr(r['t']), r['hrs'], i == 0))
    print(f"{ko:%a %d/%m %H:%M}  {k[1]} – {k[2]}")
    for lim, t, h, first in seen:
        print(f"     {lim:>5} : {t:%a %d/%m %H:%M} ({h:4.1f}ω πριν){'  [ηδη ετσι οταν ξεκινησε η καταγραφη]' if first and h < 47 and lim and lim >= 3000 else ''}")
        if not (first and lim and lim >= 3000):
            stage[lim].append((h, t))
print('\nΣΥΝΟΨΗ ανα σταδιο (χαντικαπ/συνολο) — ωρες πριν το τζαμπολ & ωρα Ελλαδας')
for lim in sorted(x for x in stage if x):
    hs = [h for h, _ in stage[lim]]; ts = sorted({t.strftime('%H:%M') for _, t in stage[lim]})
    print(f"  {lim:>5}: n{len(hs):2d} · διαμεσος {statistics.median(hs):4.1f}ω πριν (ευρος {min(hs):.1f}–{max(hs):.1f}) · ωρες: {', '.join(ts[:8])}{' …' if len(ts) > 8 else ''}")
