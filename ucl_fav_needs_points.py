"""ucl_fav_needs_points.py — 16/10/2026 (Στελιος: «μ αρεσει να παιξω μια μεγαλη ομαδα κοντρα σε μικρη, με τη μεγαλη να πρεπει να κυνηγησει γκολ —
η Inter εχει 2 ηττες, η Roma 1 βαθμο, αυτο ειναι το ματς που πρεπει να κυνηγησουν 4-0, 5-0»).
Champions League ΝΕΟ φορματ (2425, 2526), league phase αγωνιστικες 2-8. Φαβορι = της αγορας (κλεισιμο Crown, γραμμη ≤ −1.0 = «μεγαλο φαβορι»).
Ομαδες χωρισμενες με τους ΒΑΘΜΟΥΣ ΤΟΥ ΦΑΒΟΡΙ πριν το ματς ανα αγωνιστικη: «πιεσμενο» (≤1 βαθμος ανα ματς) vs «ανετο» (≥2) vs ενδιαμεσο.
Μετρο: διαφορα φαβορι − γραμμη, καλυψη, ROI χαντικαπ κλεισιματος, νικη ≥4 · γκολ − γραμμη συνολου, ROI over κλεισιματος (Crown)."""
import json, glob, sys, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
FX = json.load(open('europe_fixtures.json', encoding='utf-8'))
def pl(g):
    try:
        p = [float(x) for x in str(g).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception: return None
KO = {}; M = []
for sea in ('2425', '2526'):
    pts = {}; gp = {}
    for m in sorted(FX.get(f'ChampionsLeague_{sea}', []), key=lambda m: m['utc']):
        if not str(m.get('round', '')).isdigit(): continue
        try: hs, as_ = [int(x) for x in m['score'].split('-')]
        except Exception: continue
        ko = int(dt.datetime.strptime(m['utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc).timestamp())
        h, a = m['hid'], m['aid']
        M.append(dict(mid=str(m['mid']), sea=sea, rd=int(m['round']), ko=ko, home=m['hname'], away=m['aname'], gh=hs, ga=as_,
                      ph=pts.get(h, 0), pa=pts.get(a, 0), nh=gp.get(h, 0), na=gp.get(a, 0)))
        ph_ = 3 if hs > as_ else (1 if hs == as_ else 0); pa_ = 3 if as_ > hs else (1 if hs == as_ else 0)
        pts[h] = pts.get(h, 0) + ph_; pts[a] = pts.get(a, 0) + pa_; gp[h] = gp.get(h, 0) + 1; gp[a] = gp.get(a, 0) + 1
X = pd.DataFrame(M); ids = set(X.mid); KOd = dict(zip(X.mid, X.ko))
AH = {}; OU = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r['cid'] != 3 or str(r['mid']) not in ids: continue
        mid = str(r['mid']); ko = KOd[mid]
        a = sorted((int(mt), pl(g), float(u) + 1, float(dn) + 1) for mt, u, g, dn in (r.get('ah') or []) if mt and pl(g) is not None and int(mt) <= ko + 900)
        o = sorted((int(mt), pl(g), float(ov) + 1, float(un) + 1) for mt, ov, g, un in (r.get('ou') or []) if mt and pl(g) is not None and int(mt) <= ko + 900)
        if a: AH[mid] = a[-1][1:]
        if o: OU[mid] = o[-1][1:]
rows = []
for r in X.itertuples():
    if r.rd < 2 or r.mid not in AH: continue
    sup, oh, oa = AH[r.mid]                      # sup = αναμενομενη υπεροχη γηπεδουχου (θετικο = φαβορι ο γηπ)
    if abs(sup) < 1.0: continue
    fh = sup > 0; side = 1 if fh else -1; ln = -abs(sup); o = oh if fh else oa
    pf, nf = (r.ph, r.nh) if fh else (r.pa, r.na)
    ppg = pf / max(nf, 1)
    grp = 'ΠΙΕΣΜΕΝΟ (≤1 β/ματς)' if ppg <= 1.0 else ('ΑΝΕΤΟ (≥2 β/ματς)' if ppg >= 2.0 else 'ενδιαμεσο')
    gd = (r.gh - r.ga) * side
    ou = OU.get(r.mid)
    rows.append(dict(sea=r.sea, rd=r.rd, grp=grp, fav=r.home if fh else r.away, opp=r.away if fh else r.home, pf=pf, line=abs(sup), gd=gd,
                     ah=picks.settle(r.gh - r.ga, side, ln, o), big4=int(gd >= 4),
                     tot=r.gh + r.ga, ol=ou[0] if ou else np.nan,
                     ov=(lambda L, oo, tg: sum(((oo - 1) if tg - x > 0 else (0 if tg == x else -1)) for x in ([L] if (L * 4) % 2 == 0 else [L - .25, L + .25])) / (1 if (L * 4) % 2 == 0 else 2))(ou[0], ou[1], r.gh + r.ga) if ou else np.nan))
R = pd.DataFrame(rows)
print(f'Champions νεο φορματ, αγων. 2-8, μεγαλο φαβορι αγορας (γραμμη ≥1.0): {len(R)} ματς')
print(f'   {"φαβορι":22s} {"ματς":>5s} │ {"διαφορα−γραμμη":>14s} {"καλυψη":>7s} {"ROI χαντικαπ":>12s} {"νικη≥4":>7s} │ {"γκολ−γραμμη":>11s} {"ROI over":>9s} │ ανα σεζον (χαντ./over)')
for g in ('ΠΙΕΣΜΕΝΟ (≤1 β/ματς)', 'ενδιαμεσο', 'ΑΝΕΤΟ (≥2 β/ματς)'):
    y = R[R.grp == g]
    if not len(y): continue
    print(f'   {g:22s} {len(y):5d} │ {(y.gd - y.line).mean():+14.2f} {100 * (y.gd > y.line).mean():6.0f}% {100 * y.ah.mean():+11.1f}% {100 * y.big4.mean():6.0f}% │ '
          f'{(y.tot - y.ol).mean():+11.2f} {100 * y.ov.mean():+8.1f}% │ ' + ' '.join(f'{s[2:]}: {100 * y[y.sea == s].ah.mean():+.0f}/{100 * y[y.sea == s].ov.mean():+.0f}' for s in ('2425', '2526')))
print('\n   ΠΙΕΣΜΕΝΑ μεγαλα φαβορι — ολα τα ματς:')
for r in R[R.grp.str.startswith('ΠΙΕΣ')].sort_values(['sea', 'rd']).itertuples():
    print(f'     {r.sea} αγ.{r.rd} {r.fav} ({r.pf} β) – {r.opp}: γραμμη −{r.line:g} · διαφορα {r.gd:+d} → χαντ. {r.ah:+.2f} · γκολ {r.tot} / γραμμη {r.ol:g} → over {r.ov:+.2f}')
