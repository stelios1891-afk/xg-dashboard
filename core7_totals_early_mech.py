"""core7_totals_early_mech.py — 10/11/2026 (Στελιος: «διαβασε ολη τη μηχανη των συνολων ... ενα τεστ πανω σε καθε μηχανισμο ... η μηχανη
δημιουργηθηκε για το κλεισιμο, ισως στις 5 μερες πριν να θελει διαφορετικη μηχανη»).
ΣΥΝΟΛΑ ΕΓΧΩΡΙΩΝ CORE7 ΝΩΡΙΣ (5+ μερες), 2223-2526, Crown & Bet365 (Nowgoal). Ιδιος κανονας με την καταγραφη core7_totals_shadow:
  μοντελο = live μηχανη (core7_mech_preds_cur_0.75_6_13~emps) + αγκυρα ομαδας (μαθαινει απο το ΚΛΕΙΣΙΜΟ Crown απο την 7η αγωνιστικη, λ 0.5, ισο μοιρασμα)
  τιμες = απο τον «τιμιο χρονο» (06:00 UTC μετα το προηγουμενο ματς ΚΑΙ των δυο) ως ≥120ω πριν τη σεντρα· pick = η ΠΡΩΤΗ τιμη που πληρει
  (οπως η live καταγραφη που σαρωνει συνεχως), καλυτερη πλευρα · edge ≥10% (κουρεμα 3%), 1.70-2.10, κυρια γραμμη · αγωνιστικη ≥8.
md στα αρχεια = 0-based (md 6 = 7η αγωνιστικη).
ΤΕΣΤ: ενας μηχανισμος τη φορα (python core7_totals_early_mech.py <τ1|τ2|...>). ΚΡΙΤΗΡΙΑ (δηλωθηκαν πριν, Στελιος «ξεκινα»): υποψηφια αλλαγη μονο αν
  (1) περισσοτερες μοναδες ΚΑΙ στα 2 βιβλια · (2) καλυτερη ≥3/4 σεζον · (3) CLV οχι χειροτερο · (4) ακριβεια οχι χειροτερη (οπου αλλαζει το μοντελο) ·
  (5) κατωφλια/βαρη: LOSO διαλεγει την ιδια τιμη ≥3/4. Ο,τι περασει = καταγραφη διπλα στην τωρινη, οχι χρηματα. Τιποτα live."""
import sys, os, json, glob, datetime, pickle
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
UTC = datetime.timezone.utc
SEAS = ['2223', '2324', '2425', '2526']
TOP5 = {'EPL', 'LaLiga', 'SerieA', 'Bundesliga', 'Ligue1'}
CACHE = 'core7_totals_early_cache.pkl'


def load(pred_csv='core7_mech_preds_cur_0.75_6_13~emps.csv'):
    W = pd.read_csv('core7_goals_gap_rows.csv', dtype={'season': str, 'mid': str})
    P = pd.read_csv(pred_csv, dtype={'mid': str, 'season': str})
    P = P[P.season.isin(SEAS)].copy()
    if os.path.exists(CACHE):
        KO, SER = pickle.load(open(CACHE, 'rb'))
    else:
        KO = {}
        for f in glob.glob('data_*_*.json'):
            try: d = json.load(open(f, encoding='utf-8'))
            except Exception: continue
            if not isinstance(d, dict): continue
            for k, v in d.items():
                try: KO[str(k)] = datetime.datetime.strptime(v['date'], '%a, %b %d, %Y, %H:%M UTC').replace(tzinfo=UTC).timestamp()
                except Exception: pass
        def pl(gs):
            try:
                p = [float(x) for x in str(gs).split('/')]; return sum(p) / len(p)
            except Exception: return None
        SER = {}; mids = set(P.mid)
        for f in glob.glob('nowgoal_odds/*.jsonl'):
            for ln in open(f, encoding='utf-8'):
                try: r = json.loads(ln)
                except Exception: continue
                if r.get('cid') not in (3, 8) or not r.get('ou') or str(r['mid']) not in mids: continue
                rows = []
                for mt, ov, gl, un in r['ou']:
                    L = pl(gl)
                    try: oo, uu = float(ov) + 1, float(un) + 1
                    except (TypeError, ValueError): continue
                    if L is None or mt is None or oo <= 1 or uu <= 1: continue
                    rows.append((mt, L, oo, uu))
                if rows: rows.sort(); SER[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'Bet365')] = rows
        pickle.dump((KO, SER), open(CACHE, 'wb'))
    TG = dict(zip(W.mid, W.tg)); TMK = dict(zip(W.mid, W.T_mkt))
    P['ko'] = P.mid.map(KO)
    P = P[P.ko.notna()].sort_values(['league', 'season', 'ko']).reset_index(drop=True)
    prev_ko = {}; PREV = []
    for r in P.itertuples():
        k = (r.league, r.season)
        PREV.append(max(prev_ko.get((k, r.home), -1), prev_ko.get((k, r.away), -1)))
        prev_ko[(k, r.home)] = r.ko; prev_ko[(k, r.away)] = r.ko
    P['prev'] = PREV
    P['tg'] = P.mid.map(TG)
    tm = []
    for r in P.itertuples():
        if r.mid in TMK: tm.append(TMK[r.mid]); continue
        seq = SER.get((r.mid, 'Crown'))
        tm.append(t_mkt(seq[-1][1], seq[-1][2], seq[-1][3], r.xg_h - r.xg_a) if seq else np.nan)
    P['T_mkt'] = tm
    return P, SER


IDX = np.add.outer(np.arange(13), np.arange(13)); KS = np.arange(25)


def tdist(h, a, rho=None, disp=0.0):
    """Κατανομη συνολου γκολ. disp>0 = πιο «απλωμενη» (μιξη λ με γαμμα, διασπορα του λ = disp·λ²)."""
    h, a = max(h, .05), max(a, .05)
    if disp <= 0:
        M = picks.score_matrix_dom(h, a, rho)
        return np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25)
    out = np.zeros(25); qs = (np.arange(9) + .5) / 9
    from scipy.stats import gamma
    k = 1 / disp; mult = gamma.ppf(qs, k, scale=1 / k)            # κοινος πολλαπλασιαστης ρυθμου του ματς
    for m in mult:
        M = picks.score_matrix_dom(h * m, a * m, rho)
        out += np.bincount(IDX.ravel(), weights=np.asarray(M).ravel(), minlength=25) / len(mult)
    return out


def parts(L):
    return [L] if (L * 4) % 2 == 0 else [L - .25, L + .25]


def side_probs(d, L, over):
    """ανα μισο-γραμμη: (p_win, p_push)"""
    return [(d[(KS > x + .01) if over else (KS < x - .01)].sum(), d[np.abs(KS - x) < .01].sum()) for x in parts(L)]


def edge_of(sp, o, margin):
    return sum(pw * (o - 1) * (1 - margin) - (1 - pw - pp) for pw, pp in sp) / len(sp)


def settle(tg, L, o, over):
    r = 0.0
    for x in parts(L):
        m = (tg - x) if over else (x - tg)
        r += ((o - 1) if m > .01 else (0 if abs(m) < .01 else -1)) / len(parts(L))
    return r


_tm = {}


def t_mkt(L, o, u, s):
    k = (L, round(o, 3), round(u, 3), round(s, 2))
    if k in _tm: return _tm[k]
    q = (1 / o) / (1 / o + 1 / u); lo, hi = 0.8, 7.0
    for _ in range(26):
        T = (lo + hi) / 2; d = tdist((T + s) / 2, (T - s) / 2)
        po = sum(d[KS > x + .01].sum() for x in parts(L)); pu = sum(d[KS < x - .01].sum() for x in parts(L))
        lo, hi = (T, hi) if po / max(po + pu, 1e-9) < q else (lo, T)
    _tm[k] = (lo + hi) / 2; return _tm[k]


def anchored(P, start_md=6, lam=0.5, split='equal', src='close', SER=None, Tsrc=None):
    """Συνολο μοντελου + αγκυρα ομαδας (πριν απο το καθε ματς). src='close' (κλεισιμο Crown) ή πινακας Tsrc (π.χ. τιμη 5 ημερων)."""
    out = np.zeros(len(P)); off = {}; cur = None
    TM = P.T_mkt.values if Tsrc is None else Tsrc
    for i, r in enumerate(P.itertuples()):
        k = (r.league, r.season)
        if k != cur: off = {}; cur = k
        oh, oa = off.get(r.home, 0), off.get(r.away, 0)
        out[i] = r.xg_h + r.xg_a + oh + oa
        if r.md >= start_md and TM[i] == TM[i]:
            e = TM[i] - out[i]
            if split == 'equal':
                wh = wa = .5
            else:                                                  # αναλογικα με το xG καθε ομαδας στο ματς
                wh = r.xg_h / max(r.xg_h + r.xg_a, 1e-9); wa = 1 - wh
            off[r.home] = oh + lam * e * wh; off[r.away] = oa + lam * e * wa
    return out


def honest_t(prev, ko):
    t_av = prev + 2 * 3600
    d0 = datetime.datetime.fromtimestamp(t_av, UTC)
    nxt = d0.replace(hour=6, minute=0, second=0)
    if nxt.timestamp() <= t_av: nxt += datetime.timedelta(days=1)
    return nxt.timestamp() if nxt.timestamp() < ko else None


def table(P, SER, T, rho=None, disp=0.0, min_md=7, hmin=0, split_sup=None):
    """Ολες οι τιμες ανα ματς/βιβλιο απο τον τιμιο χρονο ως τη σεντρα (με ωρες πριν), με πιθανοτητες μοντελου ανα πλευρα."""
    rows = []
    for i, r in enumerate(P.itertuples()):
        if r.md < min_md or r.tg != r.tg: continue
        t0 = honest_t(r.prev, r.ko)
        if t0 is None: continue
        s = (r.xg_h - r.xg_a) if split_sup is None else split_sup[i]
        d = tdist((T[i] + s) / 2, (T[i] - s) / 2, rho, disp)
        for bk in ('Crown', 'Bet365'):
            seq = SER.get((r.mid, bk))
            if not seq: continue
            before = [x for x in seq if x[0] <= t0]
            snaps = ([(t0,) + tuple(before[-1][1:])] if before else []) + [x for x in seq if t0 < x[0] < r.ko]
            if not snaps: continue
            Lc, oc, uc = seq[-1][1], seq[-1][2], seq[-1][3]
            Tc = t_mkt(Lc, oc, uc, r.xg_h - r.xg_a)
            cache = {}
            for t, L, oo, uu in snaps:
                hrs = (r.ko - t) / 3600
                if hrs < hmin: continue
                if L not in cache: cache[L] = (side_probs(d, L, True), side_probs(d, L, False))
                spo, spu = cache[L]
                a, b = spo[0], spo[-1]; c, e = spu[0], spu[-1]
                rows.append((i, r.mid, bk, r.season, r.league, r.md, t, hrs, L, oo, uu, a[0], a[1], b[0], b[1], c[0], c[1], e[0], e[1],
                             settle(r.tg, L, oo, True), settle(r.tg, L, uu, False), Tc))
    return pd.DataFrame(rows, columns=['i', 'mid', 'bk', 'season', 'league', 'md', 't', 'hrs', 'L', 'oo', 'uu', 'ow1', 'op1', 'ow2', 'op2',
                                       'uw1', 'up1', 'uw2', 'up2', 'pnl_o', 'pnl_u', 'Tc'])


def picks_from(Tb, P, thr=.10, hi=None, omin=1.70, omax=2.10, margin=picks.MARGIN, hmin=120, hmax=1e9, thr_o=None, thr_u=None, mode='first'):
    """Η ΠΡΩΤΗ τιμη ανα ματς/βιβλιο που πληρει (ή mode='honest': μονο η τιμη του τιμιου χρονου). Καλυτερη πλευρα σε εκεινη την τιμη."""
    to = thr if thr_o is None else thr_o; tu = thr if thr_u is None else thr_u
    g = Tb[(Tb.hrs >= hmin) & (Tb.hrs <= hmax)]
    if mode == 'honest':
        g = g.groupby(['i', 'bk'], sort=False).head(1)
    def ed(o, w1, p1, w2, p2):
        return ((w1 * (o - 1) * (1 - margin) - (1 - w1 - p1)) + (w2 * (o - 1) * (1 - margin) - (1 - w2 - p2))) / 2
    eo = ed(g.oo.values, g.ow1.values, g.op1.values, g.ow2.values, g.op2.values)
    eu = ed(g.uu.values, g.uw1.values, g.up1.values, g.uw2.values, g.up2.values)
    oko = (g.oo.values >= omin) & (g.oo.values <= omax) & (eo >= to) & ((eo < hi) if hi is not None else True)
    oku = (g.uu.values >= omin) & (g.uu.values <= omax) & (eu >= tu) & ((eu < hi) if hi is not None else True)
    pick_o = oko & (~oku | (eo >= eu))
    q = g.assign(eo=eo, eu=eu, ok=oko | oku, po=pick_o)
    q = q[q.ok].groupby(['i', 'bk'], sort=False).head(1)
    if not len(q):
        return pd.DataFrame(columns=['i', 'mid', 'bk', 'season', 'league', 'md', 'hrs', 'side', 'L', 'odds', 'edge', 'pnl', 'clv'])
    ov = q.po.values
    s_ = P.xg_h.values[q.i.values] - P.xg_a.values[q.i.values]
    Ts = np.array([t_mkt(L, o, u, sv) for L, o, u, sv in zip(q.L.values, q.oo.values, q.uu.values, s_)])
    sd = np.where(ov, 1, -1)
    return pd.DataFrame(dict(i=q.i.values, mid=q.mid.values, bk=q.bk.values, season=q.season.values, league=q.league.values, md=q.md.values,
                             hrs=q.hrs.values, side=np.where(ov, 'OVER', 'UNDER'), L=q.L.values, odds=np.where(ov, q.oo.values, q.uu.values),
                             edge=np.where(ov, q.eo.values, q.eu.values), pnl=np.where(ov, q.pnl_o.values, q.pnl_u.values),
                             clv=sd * (q.Tc.values - Ts)))


def accuracy(Tb):
    """Ακριβεια στην τιμη του τιμιου χρονου (μια ανα ματς/βιβλιο), γραμμες x.0/x.5 χωρις επιστροφη:
    log-πιθανοφανεια over/under μοντελου vs αγορας (χωρις περιθωριο). Επιστρεφει πινακα με ll_mod, ll_mkt ανα ματς."""
    h = Tb.groupby(['i', 'bk'], sort=False).head(1)
    h = h[(h.L * 2 == np.round(h.L * 2)) & ((h.pnl_o != 0) | (h.pnl_u != 0))]
    y = (h.pnl_o > 0).values.astype(float)
    pm = h.ow1.values / np.maximum(h.ow1.values + h.uw1.values, 1e-9)
    pk = (1 / h.oo.values) / (1 / h.oo.values + 1 / h.uu.values)
    ll = lambda p: y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1))
    return pd.DataFrame(dict(i=h.i.values, mid=h.mid.values, bk=h.bk.values, season=h.season.values, ll_mod=ll(pm), ll_mkt=ll(pk), pm=pm, pk=pk, y=y))


def acc_txt(A, A0=None):
    t = f"ακριβεια (n {len(A)}): μοντελο−αγορα {1000 * (A.ll_mod - A.ll_mkt).mean():+.1f}×10⁻³"
    if A0 is not None:
        m = A.merge(A0[['mid', 'bk', 'season', 'll_mod']], on=['mid', 'bk', 'season'], suffixes=('', '_0'))
        d = m.ll_mod - m.ll_mod_0
        t += f" · vs βαση {1000 * d.mean():+.2f}×10⁻³ (σεζον " + ' '.join(f"{1000 * d[m.season == s].mean():+.1f}" for s in SEAS) + f", καλυτερη {sum(d[m.season == s].mean() > 0 for s in SEAS)}/4)"
    return t


def snap_T(P, SER, bk='Crown', hmin=120):
    """Συνολο αγορας στην πρωτη τιμη του τιμιου χρονου ≥hmin (για αγκυρα που μαθαινει απο την τιμη 5 ημερων)."""
    out = np.full(len(P), np.nan)
    for i, r in enumerate(P.itertuples()):
        seq = SER.get((r.mid, bk)); t0 = honest_t(r.prev, r.ko) if seq else None
        if not seq or t0 is None: continue
        before = [x for x in seq if x[0] <= t0]
        cand = ([(t0,) + tuple(before[-1][1:])] if before else []) + [x for x in seq if t0 < x[0] < r.ko]
        cand = [x for x in cand if (r.ko - x[0]) / 3600 >= hmin]
        if cand: out[i] = t_mkt(cand[0][1], cand[0][2], cand[0][3], r.xg_h - r.xg_a)
    return out


def summ(z):
    """μεσος Crown/Bet365: picks ανα σεζον, ROI, μοναδες, ανα σεζον, CLV"""
    if not len(z): return dict(n=0, ns=0, roi=np.nan, u=0, uC=0, uB=0, rC=np.nan, rB=np.nan, sea={}, pos=0, clv=np.nan)
    b = {bk: z[z.bk == bk] for bk in ('Crown', 'Bet365')}
    sea = {s: np.nanmean([b[bk][b[bk].season == s].pnl.mean() if (b[bk].season == s).any() else np.nan for bk in b]) for s in SEAS}
    sea = {k: 100 * v for k, v in sea.items()}
    return dict(n=len(z) / 2, ns=len(z) / 2 / 4, roi=100 * np.nanmean([b[k].pnl.mean() for k in b]), u=z.pnl.sum() / 2,
                uC=b['Crown'].pnl.sum(), uB=b['Bet365'].pnl.sum(), rC=100 * b['Crown'].pnl.mean(), rB=100 * b['Bet365'].pnl.mean(),
                sea=sea, pos=sum(1 for v in sea.values() if v == v and v > 0), clv=z.clv.mean())


def fmt(lab, z, base=None):
    s = summ(z)
    if not s['n']: return f'{lab:30s}   0'
    t = (f"{lab:30s} {s['ns']:5.1f}/σεζ · ROI {s['roi']:+6.1f}% (C {s['rC']:+5.1f} / B {s['rB']:+5.1f}) · {s['u']:+6.1f}μ (C {s['uC']:+5.1f} / B {s['uB']:+5.1f}) · "
         + ' '.join(f"{v:+4.0f}" if v == v else '   —' for v in s['sea'].values()) + f" ({s['pos']}/4) · CLV {s['clv']:+.3f}")
    if base is not None:
        b = summ(base)
        better = sum(1 for k in SEAS if _su(z, k) > _su(base, k) + 1e-9)
        t += f" │ vs βαση: μον. C {s['uC'] - b['uC']:+.1f} B {s['uB'] - b['uB']:+.1f} · σεζον καλυτερες {better}/4 · CLV {s['clv'] - b['clv']:+.3f}"
    return t


def _su(z, s):
    return z[z.season == s].pnl.sum() / 2


def loso(cands, label='τιμη'):
    """cands: {τιμη: picks DataFrame}. Κρυβει μια σεζον, διαλεγει την τιμη με τις περισσοτερες μοναδες στις αλλες 3."""
    ch = {}; oos = 0.0
    for s in SEAS:
        best = max(cands, key=lambda k: cands[k][cands[k].season != s].pnl.sum())
        ch[s] = best; oos += cands[best][cands[best].season == s].pnl.sum() / 2
    return ch, oos


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'τ1'
    P, SER = load()
    T = anchored(P)
    TBF = 'core7_totals_early_tb_base.pkl'
    if os.path.exists(TBF): Tb = pd.read_pickle(TBF)
    else: Tb = table(P, SER, T, hmin=0); Tb.to_pickle(TBF)
    base = picks_from(Tb, P)
    print('ΒΑΣΗ (σημερινος κανονας): edge ≥10%, 1.70-2.10, κουρεμα 3%, ≥120ω, πρωτη τιμη που πληρει, αγωνιστικη ≥8')
    print('στηλες: picks ανα σεζον (μεσος 2 βιβλιων) · ROI (Crown / Bet365) · μοναδες · ROI ανα σεζον 22-23 23-24 24-25 25-26 (θετικες) · CLV γκολ (+ = υπερ μας)')
    print(fmt('ΒΑΣΗ', base))
    hon = picks_from(Tb, P, mode='honest')
    print(fmt('ελεγχος: μονο τιμη τιμιου χρονου', hon) + '   (οπως το τεστ 15/10)')
    if which in ('τ1', 'ολα'):
        print('\n== Τ1 ΚΑΤΩΦΛΙ EDGE')
        C = {}
        for th in (.04, .06, .08, .10, .12, .14, .16):
            C[th] = picks_from(Tb, P, thr=th); print(fmt(f'edge ≥{th:.0%}', C[th], base))
        for lo, hi in ((.04, .10), (.06, .10), (.10, .14), (.14, .20), (.20, 9)):
            print(fmt(f'ζωνη {lo:.0%}-{hi:.0%}' if hi < 9 else f'ζωνη {lo:.0%}+', picks_from(Tb, P, thr=lo, hi=hi)))
        ch, oos = loso(C)
        print('LOSO: ' + ' '.join(f'{s[2:]}→{v:.0%}' for s, v in ch.items()) + f' · εκτος δειγματος {oos:+.1f}μ vs σημερινο {base.pnl.sum() / 2:+.1f}μ')
    if which in ('τ2', 'ολα'):
        print('\n== Τ2 ΕΥΡΟΣ ΑΠΟΔΟΣΗΣ')
        for a, b in ((1.70, 2.10), (1.60, 2.30), (1.50, 2.50), (1.01, 99), (1.80, 2.10), (1.70, 2.00)):
            print(fmt(f'{a:.2f}-{b:.2f}' if b < 50 else 'χωρις οριο', picks_from(Tb, P, omin=a, omax=b), base))
    if which in ('τ3', 'ολα'):
        print('\n== Τ3 ΚΟΥΡΕΜΑ ΣΤΟ EDGE')
        for m in (0.0, 0.015, 0.03, 0.05):
            print(fmt(f'κουρεμα {m:.1%}', picks_from(Tb, P, margin=m), base))
    if which in ('τ10', 'ολα'):
        print('\n== Τ10 ΠΟΣΟ ΝΩΡΙΣ (ελαχιστες ωρες πριν τη σεντρα)')
        C = {}
        for h in (72, 96, 120, 144, 168):
            C[h] = picks_from(Tb, P, hmin=h); print(fmt(f'≥{h}ω ({h / 24:.0f} μερες)', C[h], base))
        for a, b in ((72, 120), (120, 168), (168, 1e9)):
            print(fmt(f'μονο {a}-{b if b < 1e8 else "∞"}ω', picks_from(Tb, P, hmin=a, hmax=b)))
        ch, oos = loso(C)
        print('LOSO: ' + ' '.join(f'{s[2:]}→{v}ω' for s, v in ch.items()) + f' · εκτος δειγματος {oos:+.1f}μ vs σημερινο {base.pnl.sum() / 2:+.1f}μ')
    if which in ('τ11', 'ολα'):
        print('\n== Τ11 OVER ΚΑΙ UNDER ΧΩΡΙΣΤΑ')
        for sd in ('OVER', 'UNDER'):
            print(fmt(f'βαση: μονο {sd}', base[base.side == sd]))
        for to, tu in ((.06, .10), (.08, .10), (.10, .06), (.10, .08), (.10, .12), (.12, .10), (.14, .10), (.10, .14)):
            print(fmt(f'over ≥{to:.0%} · under ≥{tu:.0%}', picks_from(Tb, P, thr_o=to, thr_u=tu), base))
        for sd, key in (('OVER', 'thr_o'), ('UNDER', 'thr_u')):
            C = {th: picks_from(Tb, P, **{key: th, ('thr_u' if key == 'thr_o' else 'thr_o'): 9.0}) for th in (.04, .06, .08, .10, .12, .14, .16)}
            for th in C: print(fmt(f'  μονο {sd} ≥{th:.0%}', C[th]))
            ch, oos = loso(C)
            print(f'  LOSO {sd}: ' + ' '.join(f'{s[2:]}→{v:.0%}' for s, v in ch.items()) + f' · εκτος δειγματος {oos:+.1f}μ vs σημερινο {base[base.side == sd].pnl.sum() / 2:+.1f}μ')
    def variant(lab, T_, **kw):
        t_ = table(P, SER, T_, hmin=0, **kw); z = picks_from(t_, P)
        print(fmt(lab, z, base)); print(' ' * 31 + acc_txt(accuracy(t_), A0)); return t_, z
    if which in ('τ4', 'τ7', 'ολα'):
        A0 = accuracy(Tb); print('\nΑΚΡΙΒΕΙΑ ΒΑΣΗΣ: ' + acc_txt(A0))
    if which in ('τ4', 'ολα'):
        print('\n== Τ4 ΑΓΚΥΡΑ')
        variant('χωρις αγκυρα', anchored(P, lam=0))
        C = {}
        for lam in (.25, .5, .75, 1.0):
            C[lam] = variant(f'βαρος {lam}', anchored(P, lam=lam))[1]
        ch, oos = loso(C); print('LOSO βαρους: ' + ' '.join(f'{s[2:]}→{v}' for s, v in ch.items()) + f' · εκτος δειγματος {oos:+.1f}μ vs σημερινο {base.pnl.sum() / 2:+.1f}μ')
        variant('μοιρασμα αναλογικο', anchored(P, split='prop'))
        for sm, nm in ((4, '5η'), (9, '10η')):
            variant(f'μαθαινει απο την {nm}', anchored(P, start_md=sm))
        variant('μαθαινει απο την τιμη 5 ημερων', anchored(P, Tsrc=snap_T(P, SER)))
    if which in ('τ7', 'ολα'):
        print('\n== Τ7 ΚΑΤΑΝΟΜΗ ΣΚΟΡ')
        for rho in (0.0, -0.08):
            variant(f'Dixon-Coles {rho}', T, rho=rho)
        for dp in (.03, .06, .10):
            variant(f'πιο απλωμενη ({dp})', T, disp=dp)
    if which in ('τ5689', 'ολα'):
        print('\n== Τ5/Τ6/Τ8/Τ9 ΜΗΧΑΝΗ (καθε εκδοχη συγκρινεται με τη ΔΙΚΗ της βαση, ιδια εποχη αρχειων)')
        def run_file(f):
            P_, S_ = load(f); t_ = table(P_, S_, anchored(P_), hmin=0); return t_, picks_from(t_, P_), accuracy(t_)
        E = 'core7_mech_preds_cur_0.75_6_13~emps'
        for title, bf, vs in (('Τ5 xG ΕΝΑΝΤΙ ΓΚΟΛ (τελικο μειγμα, ραμπα 100→X· σημερα 60%)', 'core7_mech_preds_bl_0.6~emps.csv',
                               [(f'xG {int(float(x) * 100)}%', f'core7_mech_preds_bl_{x}~emps.csv') for x in ('0.4', '0.8', '0.9', '1.0')]),
                              ('Τ6 ΜΕΓΑΛΕΣ ΦΑΣΕΙΣ (συμπιεση) & ΠΕΝΑΛΤΙ (σημερα: συμπιεση ναι, πεναλτι 0.25)', E + '.csv',
                               [('χωρις συμπιεση', E + '@nocomp.csv'), ('πεναλτι 0.5', E + '@pen0.5.csv'), ('πεναλτι 0.76', E + '@pen0.76.csv'),
                                ('χωρις συμπιεση + πεναλτι 0.76', E + '@pen0.76@nocomp.csv')]),
                              ('Τ8 ΠΡΟΓΡΑΜΜΑ ΑΝΤΙΠΑΛΩΝ (SoS 0.75 στις 7-14)', E + '.csv', [('SoS κλειστο', 'core7_mech_preds_cur_0_6_13~emps.csv')]),
                              ('Τ9 ΜΙΞΗ ΜΕ ΠΕΡΣΙΝΗ (σημερα K=8)', E + '.csv', [('K=4 (λιγοτερη περσινη)', E + '@K4.csv'), ('K=16 (περισσοτερη περσινη)', E + '@K16.csv')]),
                              ('Τ12 ΚΟΚΚΙΝΕΣ ΚΑΡΤΕΣ (σημερα εμπειρικη διορθωση)', E + '.csv', [('χωρις διορθωση κοκκινων', 'core7_mech_preds_cur_0.75_6_13~nored.csv')])):
            print('\n' + title)
            t0_, z0, a0 = run_file(bf)
            print(fmt('βαση αυτης της εποχης', z0)); print(' ' * 31 + acc_txt(a0))
            C = {'βαση': z0}
            for lab, f in vs:
                t_, z, a = run_file(f); C[lab] = z
                print(fmt(lab, z, z0)); print(' ' * 31 + acc_txt(a, a0))
            if len(C) > 2:
                ch, oos = loso(C); print('LOSO: ' + ' '.join(f'{s_[2:]}→{v}' for s_, v in ch.items()) + f' · εκτος δειγματος {oos:+.1f}μ vs βαση {z0.pnl.sum() / 2:+.1f}μ')
    if which == 'τ13':
        print('\n== Τ13 ΣΥΝΔΥΑΣΜΟΙ (αρχεια @6s = με τα σημερινα δεδομενα· οι 4 ιστορικες σεζον)')
        def run_file(f):
            P_, S_ = load(f); t_ = table(P_, S_, anchored(P_), hmin=0); return t_, picks_from(t_, P_), accuracy(t_)
        t0_, z0, a0 = run_file('core7_mech_preds_bl_0.6~emps@6s.csv')
        print(fmt('βαση xG 60% K=8', z0)); print(' ' * 31 + acc_txt(a0))
        C = {'βαση': z0}
        for lab, f in (('xG 80%', 'bl_0.8~emps@6s'), ('xG 90%', 'bl_0.9~emps@6s'), ('K=16', 'cur_0.75_6_13~emps@6s@K16'),
                       ('xG 80% + K=16', 'bl_0.8~emps@6s@K16'), ('xG 90% + K=16', 'bl_0.9~emps@6s@K16')):
            t_, z, a = run_file(f'core7_mech_preds_{f}.csv'); C[lab] = z
            print(fmt(lab, z, z0)); print(' ' * 31 + acc_txt(a, a0))
        ch, oos = loso(C); print('LOSO: ' + ' '.join(f'{s_[2:]}→{v}' for s_, v in ch.items()) + f' · εκτος δειγματος {oos:+.1f}μ vs βαση {z0.pnl.sum() / 2:+.1f}μ')
    base.to_csv('core7_totals_early_base_rows.csv', index=False)
