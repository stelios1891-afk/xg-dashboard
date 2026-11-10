"""core7_totals_early_2627.py — 10/11/2026 (Στελιος «τρεξτο»): ελεγχος ΕΚΤΟΣ ιστορικου των εκδοχων της μηχανης συνολων (core7_totals_early_mech)
στη φετινη σεζον 2627 με τιμες Pinnacle (odds_history.jsonl), με τον ΙΔΙΟ κανονα με την καταγραφη core7_totals_shadow:
αγκυρα απο το κλεισιμο Pinnacle (αγων. ≥7, λ 0.5), picks αγων. ≥8, ≥120ω, τιμιος χρονος (προηγουμενο ματς ΚΑΙ των 2 παιγμενο), edge ≥10%, 1.70-2.10,
η ΠΡΩΤΗ τιμη που πληρει. Μονη διαφορα: το μοντελο = προβλεψεις core7_mech_preds_<εκδοχη>@6s αντι για το αρχειο της live μηχανης.
Χρηση: python core7_totals_early_2627.py <αρχειο προβλεψεων> [...]"""
import sys, os, json, glob, collections, datetime as dt
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
import core7_totals_shadow as C
UTC = dt.timezone.utc

KO = {}; SC = {}
for f in glob.glob('data_*_2627.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for k, v in d.items():
        try:
            KO[str(k)] = dt.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=UTC)
            if v.get('hs') is not None and v.get('as') is not None: SC[str(k)] = v['hs'] + v['as']
        except Exception: pass
OH = collections.defaultdict(list)
for l in open('odds_history.jsonl', encoding='utf-8'):
    try: r = json.loads(l)
    except Exception: continue
    if not r.get('ou') or not r.get('ko') or r.get('inplay'): continue
    OH[(str(r.get('hid')), str(r.get('aid')))].append((C.utc(r['t']), [float(x) for x in r['ou'][:3]], C.utc(r['ko'])))
for k in OH: OH[k].sort(key=lambda x: x[0])
NOW = dt.datetime.now(UTC)


def run(pred_csv, lam=0.5):
    P = pd.read_csv(pred_csv, dtype={'mid': str, 'season': str})
    P = P[P.season == '2627'].copy()
    M = []
    for r in P.itertuples():
        ko = KO.get(r.mid)
        if ko is None: continue
        M.append(dict(mid=r.mid, lg=r.league, gw=int(r.md) + 1, hid=str(r.home), aid=str(r.away), ko=ko, T=r.xg_h + r.xg_a, s=r.xg_h - r.xg_a,
                      tg=SC.get(r.mid), seq=[x[:2] for x in OH.get((str(r.home), str(r.away)), []) if abs((x[2] - ko).total_seconds()) <= 3 * 86400]))
    M.sort(key=lambda r: r['ko'])
    UPD = collections.defaultdict(list); OFF = collections.defaultdict(float); TEAM_KO = collections.defaultdict(list)
    for r in M:
        TEAM_KO[(r['lg'], r['hid'])].append(r['ko']); TEAM_KO[(r['lg'], r['aid'])].append(r['ko'])
        if r['tg'] is None or r['gw'] < C.LEARN_GW: continue
        pre = [x for x in r['seq'] if x[0] < r['ko']]
        if not pre: continue
        L, o, u = pre[-1][1]
        kh, ka = (r['lg'], r['hid']), (r['lg'], r['aid'])
        e = C.t_mkt(L, o, u, r['s']) - (r['T'] + OFF[kh] + OFF[ka])
        for k in (kh, ka):
            OFF[k] += lam * e / 2; UPD[k].append((r['ko'] + dt.timedelta(hours=2), lam * e / 2))
    off_at = lambda k, t: sum(d for tt, d in UPD.get(k, []) if tt <= t)
    def prev_done(k, ko, t):
        L_ = [x for x in TEAM_KO.get(k, []) if x < ko - dt.timedelta(hours=6)]
        return (not L_) or (max(L_) + dt.timedelta(hours=2) <= t)
    out = []
    for r in M:
        if r['gw'] < C.MIN_GW or r['tg'] is None: continue
        kh, ka = (r['lg'], r['hid']), (r['lg'], r['aid'])
        for t, (L, o, u) in [x for x in r['seq'] if x[0] < r['ko']]:
            if (r['ko'] - t).total_seconds() / 3600 < C.MIN_H or not (prev_done(kh, r['ko'], t) and prev_done(ka, r['ko'], t)): continue
            Tp = r['T'] + off_at(kh, t) + off_at(ka, t)
            d = C.tdist((Tp + r['s']) / 2, (Tp - r['s']) / 2)
            best = max((C.edge(d, L, True, o), 'over', o), (C.edge(d, L, False, u), 'under', u))
            if best[0] >= C.EDGE and C.OMIN <= best[2] <= C.OMAX:
                pre = [x for x in r['seq'] if x[0] < r['ko']]; Lc, oc, uc = pre[-1][1]
                mv = (Lc - L) if best[1] == 'over' else (L - Lc)
                out.append(dict(mid=r['mid'], lg=r['lg'], gw=r['gw'], side=best[1], line=L, odds=best[2], edge=best[0], tg=r['tg'],
                                pnl=C.settle(r['tg'], L, best[2], best[1] == 'over'), clv_line=mv, t=t))
                break
    return pd.DataFrame(out)


if __name__ == '__main__':
    base = None
    for f in sys.argv[1:]:
        z = run(f)
        lab = f.replace('core7_mech_preds_', '').replace('.csv', '')
        if not len(z): print(f'{lab:32s} 0 picks'); continue
        w = (z.pnl > 0).sum(); p0 = (z.pnl == 0).sum()
        print(f"{lab:32s} {len(z):3d} picks · {z.pnl.sum():+6.2f}μ ({100 * z.pnl.mean():+6.1f}%) · κερδ/επιστρ/χασ {w}/{p0}/{len(z) - w - p0} · "
              f"under {(z.side == 'under').sum()} · CLV γραμμης {z.clv_line.mean():+.3f} γκολ (υπερ {(z.clv_line > 0).sum()}/κοντρα {(z.clv_line < 0).sum()})")
        z.to_csv(f'core7_totals_early_2627_{lab}.csv', index=False)
