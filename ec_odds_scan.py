# -*- coding: utf-8 -*-
"""ec_odds_scan.py — Αποδοσεις EuroCup απο την Pinnacle (δημοσια υπηρεσια, 0 credits, pin_api league 377) — 1/10/2026.
Ιδια μορφη/ταιριασμα με el_odds_scan.py (χρησιμοποιει τις συναρτησεις του)· το Odds API ΔΕΝ εχει EuroCup → μονο Pinnacle.
Τρεχει στον scanner (scanner_tick.sh) · request μονο αν καποιο ματς ξεκινα ≤48ω · το πολυ 1 / 10'.
Εξοδος: ec_odds_latest.json (ιδια δομη με el_odds_latest.json) · ec_odds_hist.jsonl (διαδρομη γραμμων· τελευταια πριν το τζαμπολ = κλεισιμο)."""
import os, sys, json, datetime
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
import el_odds_scan as E
ROOT = os.path.dirname(os.path.abspath(__file__))
E.PROJ_F = os.path.join(ROOT, 'ec_projections.json')
E.SCHED_F = os.path.join(ROOT, 'ec_sched.json')
OUT_F = os.path.join(ROOT, 'ec_odds_latest.json')
HIST_F = os.path.join(ROOT, 'ec_odds_hist.jsonl')
WINDOW_H, GAP_MIN = 48, 10
FORCE = os.environ.get('EC_FORCE') == '1'

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    games, season = E.our_games(now)
    fut = [(f['utc'] - now).total_seconds() / 3600 for f in games if f['utc'] > now]
    nearest_h = min(fut) if fut else None
    if nearest_h is None or nearest_h > WINDOW_H:
        print(f"EuroCup: {'κανενα επερχομενο ματς' if nearest_h is None else f'κοντινοτερο τζαμπολ σε {nearest_h:.1f}h'} (> {WINDOW_H}h) — skip")
        return
    try:
        old = json.load(open(OUT_F, encoding='utf-8'))
    except Exception:
        old = {}
    try:
        age_min = (now - E._pdt(old['scanned_at'])).total_seconds() / 60
    except Exception:
        age_min = 1e9
    if age_min < GAP_MIN and not FORCE:
        print(f'EuroCup: τελευταιο scan πριν {age_min:.0f}λ < {GAP_MIN}λ — skip'); return
    import pin_api
    try:
        data = pin_api.toa_like('eurocup', include_alt=True)
    except pin_api.PinError as e:
        print(f'EuroCup: Pinnacle σφαλμα ({e}) — τιποτα δεν γραφτηκε (δεν υπαρχει εφεδρεια: το Odds API δεν εχει EuroCup)')
        return
    odds, hist_rows, unmatched, nmatch = E.build_records(list(data), games, now, old.get('odds', {}))
    json.dump(dict(scanned_at=now.isoformat()[:16], season=season, src='pinnacle', n_games=nmatch, unmatched=unmatched[:20], odds=odds),
              open(OUT_F, 'w', encoding='utf-8'), ensure_ascii=False)
    if hist_rows:
        with open(HIST_F, 'a', encoding='utf-8') as hf:
            for row in hist_rows: hf.write(json.dumps(row, ensure_ascii=False) + chr(10))
    print(f'EuroCup: Pinnacle {len(data)} ματς · ταιριαξαν {nmatch} · hist +{len(hist_rows)}' + (f" · unmatched: {'; '.join(unmatched[:6])}" if unmatched else ''))

if __name__ == '__main__':
    main()
