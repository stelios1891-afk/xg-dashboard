# -*- coding: utf-8 -*-
"""core7_totals_shadow.py — 29/10/2026 (Στελιος: «ξεκιναμε απο την 15η αγωνιστικη — η καταγραφη απο την αγωνιστικη που μπαινει η αγκυρα»).
ΚΑΤΑΓΡΑΦΗ (paper, κανενα pick/Telegram) των ΣΥΝΟΛΩΝ ΕΓΧΩΡΙΩΝ ΜΕ ΑΓΚΥΡΑ, ΝΩΡΙΣ — ο κανονας των τεστ core7_totals_anchor_md1_test / core7_totals_honest_split
(τιμιος χρονος, ≥5 μερες: 15η+ Crown +9.6% / Bet365 +13.1% 4/4, CLV +0.16 γκολ).
  ΑΓΚΥΡΑ: καθε ομαδα μαθαινει διορθωση συνολου απο το ΚΛΕΙΣΙΜΟ Pinnacle των ματς της απο την 7η αγωνιστικη (λ 0.5: o_γηπ, o_φιλ += 0.25·e,
    e = συνολο αγορας − (μοντελο + o_γηπ + o_φιλ))· ισχυει για το pick μονο οτι εχει ηδη παιχτει τη στιγμη του pick.
  ΠΟΤΕ ΓΡΑΦΕΤΑΙ: αγωνιστικη ≥8 (η πρωτη με αγκυρα) · σεντρα ≥120ω μπροστα · και οι ΔΥΟ ομαδες εχουν ηδη παιξει το προηγουμενο ματς πρωταθληματος
    («τιμιος χρονος») · edge ≥10% στην κυρια γραμμη Pinnacle (over ή under), αποδοση 1.70-2.10 · ΜΙΑ εγγραφη ανα ματς, η ΠΡΩΤΗ φορα που πληρει.
  ΜΕΤΑ: κλεισιμο Pinnacle (τελευταια τιμη πριν τη σεντρα), CLV (γραμμη σε γκολ, + = υπερ μας· τιμη % οταν η γραμμη ιδια), αποτελεσμα, μοναδες.
  Αγωνιστικες 8-14 = καταγραφη· απο την 15η ο Στελιος αποφασιζει για χρηματα (κριτηρια: CLV υπερ μας, οχι αρνητικο φετος, ορια ≥500 στο top-5).
Εγγραφες που βρεθηκαν αναδρομικα (τιμη παλιοτερη απο 1ω τη στιγμη της καταγραφης) σημειωνονται backfill.
Πηγες: match_projections_archive.json (live μηχανη, παγωμενη προ-αγωνα) · odds_history.jsonl (Pinnacle: ou, lim). Εξοδος: core7_totals_shadow.json."""
import os, sys, json, bisect, datetime as dt, collections
import numpy as np
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import picks

LOG_F = os.path.join(ROOT, 'core7_totals_shadow.json')
LEARN_GW, MIN_GW, LAM, MIN_H, EDGE, OMIN, OMAX = 7, 8, 0.5, 120, 0.10, 1.70, 2.10
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
UTC = dt.timezone.utc
IDX = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25)


def utc(s):
    d = dt.datetime.fromisoformat(str(s).replace('Z', '').replace(' ', 'T')[:19])
    return d.replace(tzinfo=UTC)


def tdist(h, a):
    M = picks.score_matrix_dom(max(h, .05), max(a, .05))
    return np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25)


def _parts(L):
    return [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]


def edge(d, L, over, o):
    e = 0.0
    for x in _parts(L):
        pw = d[(KS > x + .01) if over else (KS < x - .01)].sum(); pp = d[np.abs(KS - x) < .01].sum()
        e += (pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)) / len(_parts(L))
    return float(e)


def t_mkt(L, o, u, s):
    q = (1 / o) / (1 / o + 1 / u); lo, hi = 0.8, 7.0
    for _ in range(30):
        T = (lo + hi) / 2; d = tdist((T + s) / 2, (T - s) / 2)
        po = sum(d[KS > x + .01].sum() for x in _parts(L)); pu = sum(d[KS < x - .01].sum() for x in _parts(L))
        lo, hi = (T, hi) if po / max(po + pu, 1e-9) < q else (lo, T)
    return (lo + hi) / 2


def settle(tg, L, o, over):
    r = 0.0
    for x in _parts(L):
        win = tg > x + .01 if over else tg < x - .01; lose = tg < x - .01 if over else tg > x + .01
        r += ((o - 1) if win else (-1.0 if lose else 0.0)) / len(_parts(L))
    return round(r, 3)


def run(now=None, verbose=False):
    now = now or dt.datetime.now(UTC)
    A = json.load(open(os.path.join(ROOT, 'match_projections_archive.json'), encoding='utf-8'))
    OH = collections.defaultdict(list)
    for l in open(os.path.join(ROOT, 'odds_history.jsonl'), encoding='utf-8'):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if not r.get('ou') or not r.get('ko') or r.get('inplay'):
            continue
        OH[(str(r.get('hid')), str(r.get('aid')))].append((utc(r['t']), [float(x) for x in r['ou'][:3]], (r.get('lim') or {}).get('totals'), utc(r['ko'])))
    for k in OH:
        OH[k].sort(key=lambda x: x[0])
    M = []
    for fid, m in A.items():
        try:
            ko = utc(m.get('utc'))
        except Exception:
            continue
        if m.get('home_adj_xg') is None or m.get('away_adj_xg') is None:
            continue
        hx, ax = float(m['home_adj_xg']), float(m['away_adj_xg'])
        M.append(dict(fid=str(fid), lg=m.get('league'), gw=int(m.get('gw') or 0), home=m.get('home'), away=m.get('away'),
                      hid=str(m.get('home_id')), aid=str(m.get('away_id')), ko=ko, T=hx + ax, s=hx - ax, score=m.get('score'),
                      seq=[x[:3] for x in OH.get((str(m.get('home_id')), str(m.get('away_id'))), [])
                           if abs((x[3] - ko).total_seconds()) <= 3 * 86400]))     # ±3 μερες: ματς που μετατεθηκαν (π.χ. Παρι–Λιον 25→26/10)
    M.sort(key=lambda r: r['ko'])
    # ---- ΑΓΚΥΡΑ: διαδοχικα, απο τα κλεισιματα των παιγμενων (αγωνιστικη ≥7). Χρονος ισχυος = σεντρα + 2ω ----
    OFF = collections.defaultdict(float); UPD = collections.defaultdict(list)
    TEAM_KO = collections.defaultdict(list)
    for r in M:
        TEAM_KO[(r['lg'], r['hid'])].append(r['ko']); TEAM_KO[(r['lg'], r['aid'])].append(r['ko'])
        if not r['score'] or r['gw'] < LEARN_GW:
            continue
        pre = [x for x in r['seq'] if x[0] < r['ko']]
        if not pre:
            continue
        L, o, u = pre[-1][1]
        kh, ka = (r['lg'], r['hid']), (r['lg'], r['aid'])
        e = t_mkt(L, o, u, r['s']) - (r['T'] + OFF[kh] + OFF[ka])
        for k in (kh, ka):
            OFF[k] += LAM * e / 2; UPD[k].append((r['ko'] + dt.timedelta(hours=2), LAM * e / 2))
    def off_at(k, t):
        return sum(d for tt, d in UPD.get(k, []) if tt <= t)
    def prev_done(k, ko, t):
        L_ = [x for x in TEAM_KO.get(k, []) if x < ko - dt.timedelta(hours=6)]
        return (not L_) or (max(L_) + dt.timedelta(hours=2) <= t)
    try:
        log = json.load(open(LOG_F, encoding='utf-8'))
    except Exception:
        log = {}
    n_new = 0
    for r in M:
        if r['gw'] < MIN_GW or r['fid'] in log:
            continue
        kh, ka = (r['lg'], r['hid']), (r['lg'], r['aid'])
        cands = [x for x in r['seq'] if x[0] <= now] + ([(now, r['seq'][-1][1], r['seq'][-1][2])] if r['seq'] and r['ko'] > now else [])
        for t, (L, o, u), lim in cands:
            if (r['ko'] - t).total_seconds() / 3600 < MIN_H or not (prev_done(kh, r['ko'], t) and prev_done(ka, r['ko'], t)):
                continue
            oh, oa = off_at(kh, t), off_at(ka, t); Tp = r['T'] + oh + oa
            d = tdist((Tp + r['s']) / 2, (Tp - r['s']) / 2)
            best = max((edge(d, L, True, o), 'over', o), (edge(d, L, False, u), 'under', u))
            if best[0] >= EDGE and OMIN <= best[2] <= OMAX:
                log[r['fid']] = dict(seen=t.isoformat()[:16], backfill=bool(t < now - dt.timedelta(hours=1)), lg=r['lg'], gw=r['gw'],
                                     grp='top-5' if r['lg'] in TOP5 else 'PT/NL', home=r['home'], away=r['away'], ko=r['ko'].isoformat()[:16],
                                     hours_before=round((r['ko'] - t).total_seconds() / 3600, 1), side=best[1], line=L, odds=round(best[2], 3),
                                     edge=round(best[0], 4), lim=lim, T_model=round(r['T'], 3), T_anchor=round(Tp, 3),
                                     anchor=[round(oh, 3), round(oa, 3)], T_market=round(t_mkt(L, o, u, r['s']), 3),
                                     paper=True, window='8-14' if r['gw'] <= 14 else '15+')
                n_new += 1
                break
    # ---- κλεισιμο / αποτελεσμα ----
    byfid = {r['fid']: r for r in M}
    for fid, e in log.items():
        r = byfid.get(fid)
        if not r:
            continue
        pre = [x for x in r['seq'] if x[0] < r['ko']]
        if pre and r['ko'] <= now:
            Lc, oc, uc = pre[-1][1]; pc = oc if e['side'] == 'over' else uc
            mv = (Lc - e['line']) if e['side'] == 'over' else (e['line'] - Lc)
            e.update(close_line=Lc, close_odds=pc, close_t=pre[-1][0].isoformat()[:16], clv_line=round(mv, 2),
                     clv_price=round(e['odds'] / pc - 1, 4) if abs(Lc - e['line']) < .01 else None, close_lim=pre[-1][2])
        if not r['score'] and r['ko'] < now - dt.timedelta(days=3) and 'tg' not in e:
            e['void'] = True                                          # αναβολη / χωρις σκορ → ακυρο (δεν μετραει)
        if r['score'] and 'tg' not in e:
            e.pop('void', None)
            try:
                a, b = [int(x) for x in str(r['score']).replace(' ', '').split('-')]
                e.update(score=f'{a}-{b}', tg=a + b, pnl=settle(a + b, e['line'], e['odds'], e['side'] == 'over'))
                if e.get('close_line') is not None:
                    e['pnl_close'] = settle(a + b, e['close_line'], e['close_odds'], e['side'] == 'over')
            except Exception:
                pass
    json.dump(log, open(LOG_F, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'core7_totals_shadow: νεες {n_new} · συνολο {len(log)} · αγκυρα απο {sum(len(v) for v in UPD.values()) // 2} ματς')
    if verbose:
        for e in sorted(log.values(), key=lambda e: e['ko']):
            print(f"  {e['ko']} αγ.{e['gw']:2d} {e['lg']:12s} {e['home'][:18]:18s}-{e['away'][:18]:18s} {e['side']:5s} {e['line']} @{e['odds']} edge {100 * e['edge']:4.1f}% "
                  f"· {e['hours_before'] / 24:.1f}μ πριν · οριο {e['lim']} │ κλεισ {e.get('close_line')} @{e.get('close_odds')} CLV {e.get('clv_line')} "
                  f"│ {e.get('score', '—')} → {e.get('pnl', '—')}{'  (αναδρομικο)' if e['backfill'] else ''}")
    return log


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run(verbose='-v' in sys.argv)
