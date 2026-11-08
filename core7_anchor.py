"""
core7_anchor.py — ΑΓΚΥΡΑ ΑΓΟΡΑΣ για τα εγχωρια (CORE7), ΜΟΝΟ κοντες γραμμες (+0.5/+0.75) απο την 15η αγωνιστικη.
Αποφαση Στελιου 29/9/2026 μετα τα τεστ core7_anchor_short_accuracy (αγκυρα ακριβεστερη στις κοντες 4/4, διαφωνια πιο κοντα
στην πραγματικοτητα) και core7_anchor_mix_short (w LOSO = 1 σε 4/4 · picks 15+ 939 +6.7% +63u → 833 +8.8% +73u).

ΜΗΧΑΝΙΣΜΟΣ (ιδιος με core7_anchor_test.run(λ=0.5, c=0)):
  καθε ομαδα εχει διορθωση o (γκολ υπεροχης), 0 στην αρχη της σεζον.
  Για καθε ματς που παιχτηκε (με σειρα ημερομηνιας): s = s_μοντελου(προ-αγωνα) + o_h − o_a.
  Αν και οι δυο ομαδες εχουν ≥6 φετινα ματς (= αγων. 7+, οπως το τεστ) ΚΑΙ υπαρχει κλεισιμο:
     e = s_αγορας(κλεισιμο) − s ·  o_h += λ·e/2 ·  o_a −= λ·e/2        (λ = 0.5)
  Εφαρμογη live (toa_live): αν md ≥ 15 (και οι δυο ≥14 ματς) ΚΑΙ |γραμμη| ∈ {0.5, 0.75}:
     s' = s_μοντελου + o_h − o_a  (το συνολο γκολ T μενει του μοντελου) → evaluate_bet με (T+s')/2, (T−s')/2.
  Βαθιες γραμμες, αγων. 1-14, συνολα, projections: ΑΜΕΤΑΒΛΗΤΑ.

Προ-αγωνα προβλεψη = αναπαραγωγη της live μηχανης (build_data.league_ratings) με τα φετινα ματς ΜΕΧΡΙ την προηγουμενη μερα.
Κλεισιμο = τελευταια εγγραφη odds_history.jsonl πριν τη σεντρα (Pinnacle 'pin' αν υπαρχει, αλλιως line/oh/oa).
Υπεροχη αγορας απο γραμμη+τιμες με picks.gd_dist (ιδια sup() με το τεστ), T = συνολο μοντελου.

Χρηση:  python core7_anchor.py            → χτιζει core7_anchor_offsets.json (τρεχει στο data-refresh)
        python core7_anchor.py validate   → αναπαραγωγη 2526 vs core7_mech_preds_base.csv (ελεγχος ταυτισης με το τεστ)
"""
import os, sys, json, datetime
import numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'dashboard'))
import picks

LAM = 0.5
LEARN_MIN_PLAYED = 6      # μαθαινει απο αγων. 7+ (και οι δυο ≥6 ματς) — οπως το τεστ (md ≥ 6)
APPLY_MD = 15             # live md = min(ματς)+1 → 15 = και οι δυο ≥14 ματς
SHORT_LINES = (0.5, 0.75)
CORE7 = ['EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1', 'PrimeiraLiga', 'Eredivisie']
OUT_F = os.path.join(ROOT, 'core7_anchor_offsets.json')
HIST_F = os.path.join(ROOT, 'odds_history.jsonl')

_sc = {}
def sup(line, oh, oa, T):
    """υπεροχη γηπεδουχου (γκολ) που αναπαραγει τη γραμμη AH κλεισιματος — ιδια με core7_anchor_test.sup."""
    key = (line, oh, oa, round(T, 1))
    if key in _sc: return _sc[key]
    kk = 1 / oh + 1 / oa; tgt = (1 / oh) / kk; lo, hi = -5.0, 5.0
    parts = [line] if (line * 4) % 2 == 0 else [line - .25, line + .25]
    for _ in range(34):
        md = (lo + hi) / 2; d = picks.gd_dist(max((T + md) / 2, .05), max((T - md) / 2, .05))
        c = [picks.p_cover(d, 1, L) for L in parts]; pe = sum(a for a, _ in c) / max(sum(1 - b for _, b in c), 1e-9)
        lo, hi = (md, hi) if pe < tgt else (lo, md)
    _sc[key] = (lo + hi) / 2; return _sc[key]


def replay_preds(lg, Mp, Mc, prior_sea, cur_sea, id2name, name2id):
    """Προ-αγωνα (xg_h, xg_a) της live μηχανης για καθε ματς της σεζον, με ratings απο τα ματς ΠΡΙΝ τη μερα του."""
    import build_data
    G = Mc[(Mc.league == lg) & (Mc.season == str(cur_sea))].sort_values(['date', 'mid']).reset_index(drop=True)
    if not len(G):
        return pd.DataFrame()
    teams = sorted(set(G.home) | set(G.away))
    fx = [dict(home_id=int(t), away_id=None, home_name=id2name.get(t)) for t in teams]
    rows = []
    for d, grp in G.groupby('date', sort=True):
        Mt = G[G.date < d]
        LR = build_data.league_ratings(lg, Mp, Mt, prior_sea, cur_sea, dict(id2name), dict(name2id), fixtures=fx)
        for r in grp.itertuples():
            rh, ra = LR['blended'].get(r.home), LR['blended'].get(r.away)
            nh = int(((Mt.home == r.home) | (Mt.away == r.home)).sum()); na = int(((Mt.home == r.away) | (Mt.away == r.away)).sum())
            if rh is None or ra is None:
                continue
            pf = build_data._predict_ratings(rh, ra, LR['lg_shots'], LR['lg_xgps'], LR['hf'])
            rows.append(dict(league=lg, season=str(cur_sea), mid=str(r.mid), date=str(d)[:10], home=int(r.home), away=int(r.away),
                             home_name=id2name.get(r.home), away_name=id2name.get(r.away), played=min(nh, na),
                             xg_h=pf['home_adj_xg'], xg_a=pf['away_adj_xg'], gd=int(r.hg - r.ag)))
    return pd.DataFrame(rows)


def closing_index():
    """{(hid, aid): (ko_date, line, oh, oa)} — τελευταια εγγραφη ΠΡΙΝ τη σεντρα (+10′), Pinnacle αν υπαρχει."""
    idx = {}
    if not os.path.exists(HIST_F):
        return idx
    for ln in open(HIST_F, encoding='utf-8'):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get('inplay'):
            continue
        try:
            t = datetime.datetime.fromisoformat(str(r['t'])[:16]); ko = datetime.datetime.fromisoformat(str(r['ko'])[:16])
        except Exception:
            continue
        if t > ko + datetime.timedelta(minutes=10):
            continue
        pin = r.get('pin')
        if pin and all(x is not None for x in pin):
            line, oh, oa = pin
        else:
            line, oh, oa = r.get('line'), r.get('oh'), r.get('oa')
        if line is None or not oh or not oa:
            continue
        k = (int(r['hid']), int(r['aid']))
        if k not in idx or t >= idx[k][0]:
            idx[k] = (t, ko, float(line), float(oh), float(oa))
    return idx


def run_anchor(P, close_of):
    """P: προ-αγωνα προβλεψεις (μια λιγκα-σεζον, με σειρα). close_of(row) → (line, oh, oa) ή None.
    → (offsets {tid: o}, updates {tid: n}, log rows)"""
    off, nup, log = {}, {}, []
    for r in P.sort_values(['date', 'mid']).itertuples():
        s_mod = r.xg_h - r.xg_a; T = r.xg_h + r.xg_a
        s = s_mod + off.get(r.home, 0.0) - off.get(r.away, 0.0)
        c = close_of(r)
        rec = dict(date=r.date, h=r.home_name, a=r.away_name, played=int(r.played), s_mod=round(s_mod, 3), s=round(s, 3))
        if c is not None and r.played >= LEARN_MIN_PLAYED:
            s_m = sup(c[0], c[1], c[2], T); e = s_m - s
            off[r.home] = off.get(r.home, 0.0) + LAM * e / 2; off[r.away] = off.get(r.away, 0.0) - LAM * e / 2
            nup[r.home] = nup.get(r.home, 0) + 1; nup[r.away] = nup.get(r.away, 0) + 1
            rec.update(line=c[0], s_mkt=round(s_m, 3), e=round(e, 3))
        log.append(rec)
    return off, nup, log


def build(cur_sea='2627', prior_sea='2526'):
    picks.MIN_PRIOR = 6                        # ιδιο με το live (GitHub Actions)
    Mp, id2name = picks.load_matches(CORE7, [prior_sea])
    Mc, id2c = picks.load_matches(CORE7, [cur_sea]); id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}
    CI = closing_index()
    def close_of(r):
        c = CI.get((int(r.home), int(r.away)))
        if c is None or abs((c[1].date() - datetime.date.fromisoformat(r.date)).days) > 2:
            return None
        return c[2:]
    out = dict(updated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), season=cur_sea, lam=LAM,
               learn_min_played=LEARN_MIN_PLAYED, apply_md=APPLY_MD, short_lines=list(SHORT_LINES), leagues={})
    for lg in CORE7:
        P = replay_preds(lg, Mp, Mc, prior_sea, cur_sea, id2name, name2id)
        if not len(P):
            out['leagues'][lg] = dict(teams={}, matches=0, learned=0, log=[]); continue
        off, nup, log = run_anchor(P, close_of)
        learnable = int((P.played >= LEARN_MIN_PLAYED).sum())
        out['leagues'][lg] = dict(
            teams={str(t): dict(name=id2name.get(t), o=round(o, 4), n=nup.get(t, 0)) for t, o in sorted(off.items(), key=lambda kv: -kv[1])},
            matches=len(P), learnable=learnable, learned=sum(1 for x in log if 'e' in x), log=log[-60:])
        print(f"{lg:13s} ματς {len(P):3d} · για μαθηση (αγων. 7+) {learnable:3d} · με κλεισιμο {out['leagues'][lg]['learned']:3d}", flush=True)
    with open(OUT_F, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'→ {OUT_F}')
    return out


# ---------- LIVE εφαρμογη ----------
_OFF = None
def load_offsets():
    global _OFF
    if _OFF is None:
        try:
            _OFF = json.load(open(OUT_F, encoding='utf-8'))
        except Exception:
            _OFF = {}
    return _OFF

def apply(lg, H, A, xg_h, xg_a, line, md):
    """→ (xg_h', xg_a', info) — info=None αν δεν εφαρμοζεται (τοτε xg αμεταβλητα)."""
    try:
        if md is None or md < APPLY_MD or line is None or abs(float(line)) not in SHORT_LINES:
            return xg_h, xg_a, None
        L = (load_offsets().get('leagues') or {}).get(lg) or {}
        tm = L.get('teams') or {}
        oh = (tm.get(str(int(H))) or {}).get('o', 0.0); oa = (tm.get(str(int(A))) or {}).get('o', 0.0)
    except Exception:
        return xg_h, xg_a, None
    T = xg_h + xg_a; s = (xg_h - xg_a) + oh - oa
    nh, na = max((T + s) / 2, .05), max((T - s) / 2, .05)
    return nh, na, dict(o_h=round(oh, 3), o_a=round(oa, 3), shift=round(oh - oa, 3), xg_raw=[round(xg_h, 3), round(xg_a, 3)])


def apply_fav(lg, H, A, xg_h, xg_a, md, w=None):
    """1/10/2026 ΦΑΒΟΡΙ 15η+: αγκυρα σε ΟΛΕΣ τις γραμμες με βαρος w (picks.FAV_ANCHOR_W=0.7) → (xg_h', xg_a', info|None)."""
    w = picks.FAV_ANCHOR_W if w is None else w
    try:
        if md is None or md < picks.FAV_MIN_MD:
            return xg_h, xg_a, None
        L = (load_offsets().get('leagues') or {}).get(lg) or {}
        tm = L.get('teams') or {}
        oh = (tm.get(str(int(H))) or {}).get('o', 0.0); oa = (tm.get(str(int(A))) or {}).get('o', 0.0)
    except Exception:
        return xg_h, xg_a, None
    T = xg_h + xg_a; s = (xg_h - xg_a) + w * (oh - oa)
    nh, na = max((T + s) / 2, .05), max((T - s) / 2, .05)
    return nh, na, dict(o_h=round(oh, 3), o_a=round(oa, 3), w=w, shift=round(w * (oh - oa), 3), xg_raw=[round(xg_h, 3), round(xg_a, 3)])


# ---------- ελεγχος: αναπαραγωγη 2526 vs αρχειο τεστ ----------
def validate(variant='cur_0.75_6_13'):      # 1/10: live = σωστο SoS 0.75 → συγκριση με την ιδια εκδοχη του τεστ
    picks.MIN_PRIOR = 6
    Mp, id2name = picks.load_matches(CORE7, ['2425'])
    Mc, id2c = picks.load_matches(CORE7, ['2526']); id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}
    B = pd.read_csv(f'core7_mech_preds_{variant}.csv', dtype={'season': str, 'mid': str}); B = B[B.season == '2526']
    allp = []
    for lg in CORE7:
        P = replay_preds(lg, Mp, Mc, '2425', '2526', id2name, name2id)
        m = P.merge(B[['mid', 'xg_h', 'xg_a', 'md']], on='mid', suffixes=('', '_t'))
        m = m[m.md >= 6]
        ds = (m.xg_h - m.xg_a) - (m.xg_h_t - m.xg_a_t)
        print(f'{lg:13s} ματς {len(m):3d} · διαφ. υπεροχης αναπαραγωγη−τεστ: μεση {ds.mean():+.3f} · |μεση| {ds.abs().mean():.3f} · '
              f'corr {np.corrcoef(m.xg_h - m.xg_a, m.xg_h_t - m.xg_a_t)[0, 1]:.4f}', flush=True)
        allp.append(m)
    A = pd.concat(allp); ds = (A.xg_h - A.xg_a) - (A.xg_h_t - A.xg_a_t)
    print(f'ΣΥΝΟΛΟ {len(A)} · |διαφ| μεση {ds.abs().mean():.3f} · p90 {ds.abs().quantile(.9):.3f} · corr {np.corrcoef(A.xg_h - A.xg_a, A.xg_h_t - A.xg_a_t)[0, 1]:.4f}')
    A.to_csv(os.path.join(ROOT, 'core7_anchor_validate_2526.csv'), index=False)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if len(sys.argv) > 1 and sys.argv[1] == 'validate':
        validate(*sys.argv[2:3])
    else:
        build()
