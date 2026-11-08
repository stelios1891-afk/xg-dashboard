"""
ledger_h72_backfill.py — 26/9/2026 (Στελιος): αναδρομικη εισοδος ≤72ω για ΟΛΑ τα εγχωρια picks απο 13/9.
Απο το git ιστορικο του value_picks_latest.json (καθε σαρωση του scanner): για καθε ματς & πλευρα, η ΠΡΩΤΗ σαρωση
μεσα σε 72ω πριν τη σεντρα οπου το pick ηταν ενεργο → εγγραφη h72 (τιμη/γραμμη εκεινης της στιγμης) στο clv_bets.jsonl.
Ετσι ενα pick που ηρθε 10 μερες νωριτερα μπαινει με την τιμη που ειχε οταν «μπηκε» στις 72ω (αν ηταν ακομα ενεργο).
Χρονος = ωρα του commit του scanner (UTC). Τρεχει μια φορα.
"""
import os, sys, json, subprocess, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT); sys.path.insert(0, ROOT)
import clv_ledger as cl
UTC = dt.timezone.utc
FROM_KO = '2026-09-13'      # οπως το ledger (καταγραφη απο md1 ξεκινησε 13/9)
log = subprocess.run(['git', 'log', '--reverse', '--format=%H %cI', '--since=2026-08-20', '--', 'value_picks_latest.json'],
                     capture_output=True, text=True).stdout.split('\n')
have = {(b.get('hid'), b.get('aid'), str(b.get('ko'))[:16], b.get('side')) for b in cl._jsonl(cl.BETS_F) if b.get('h72')}
out, nver = [], 0
for ln in log:
    if not ln.strip():
        continue
    h, t = ln.split()
    t = dt.datetime.fromisoformat(t).astimezone(UTC)
    try:
        d = json.loads(subprocess.run(['git', 'show', f'{h}:value_picks_latest.json'], capture_output=True).stdout.decode('utf-8'))
    except Exception:
        continue
    nver += 1
    for p in d.get('picks', []):
        ko = cl._dt(p.get('when'))
        if ko is None or str(p.get('when')) < FROM_KO:
            continue
        hb = (ko - t).total_seconds() / 3600
        k = (p.get('home_id'), p.get('away_id'), str(p.get('when'))[:16], p['side'])
        if 0 < hb <= cl.ENTRY_H and k not in have:
            have.add(k)
            md = p.get('md')
            out.append(dict(seen=t.isoformat(timespec='minutes'), lg=p['lg'], home=p['home'], away=p['away'], tot=None, pin=None,
                            hid=p.get('home_id'), aid=p.get('away_id'), ko=p.get('when'), side=p['side'], hcap=p['hcap'], odds=p['odds'],
                            edge=round(p['edge'], 4), stake=round(p.get('stake_final', 0) or 0, 4), md=md, mxh=p.get('mxh'), mxa=p.get('mxa'),
                            zone=('deep' if abs(p['hcap']) >= 1 else 'mid'),
                            window=(None if md is None else ('1-6' if md < 7 else ('7-14' if md < 15 else '15+'))),
                            paper=(None if md is None else bool(md < 15)), placed_at=None, stake_asked=None, stake_accepted=None, book=None,
                            h72=True, hours_before=round(hb, 1), backfill=True))
print(f'{nver} σαρωσεις · {len(out)} εισοδοι ≤72ω')
if '--write' in sys.argv and out:
    with open(cl.BETS_F, 'a', encoding='utf-8') as fh:
        for r in sorted(out, key=lambda r: r['seen']):
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('γραφτηκαν στο clv_bets.jsonl')
