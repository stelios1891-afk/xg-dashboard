# -*- coding: utf-8 -*-
"""ec_audit_1310.py — ΕΛΕΓΧΟΣ EuroCup (13/10/2026, Στελιος: «επαναλαβε για το EuroCup τις αναλυσεις που καναμε σημερα για το BCL»).
ΠΕΡΙΓΡΑΦΙΚΟ — καμια αλλαγη live. Δεν γραφει σε κανενα αρχειο του repo εκτος απο ec_audit_1310_out.txt και ec_audit_1310_preds.pkl
(φρουρος open(): καθε αλλη εγγραφη των παλιων scripts που εκτελουνται πηγαινει στο scratchpad).
ΕΝΟΤΗΤΕΣ:
  1. ΦΡΕΣΚΑΔΑ: ec_projections generated · τελευταιο ματς EC (ec_sched/ec_box) · ανα ομαδα: ματς EC / εγχωρια (bk_domestic + fs_bk_extra) /
     φιλικα (fs_bk_preseason) + τελευταιο εγχωριο · σημαια αν το εγχωριο σταματα πριν τις 10/10 ενω η λιγκα παιζει · ομαδες χωρις εγχωριο.
  2. ΕΠΙΠΕΔΟ ΣΥΝΟΛΩΝ: αγων 1-2 πραγματικο vs μοντελο (projections 'total') vs αγορα (αγων 1: ec_closing_backfill Crown ·
     αγων 2: ec_odds_hist τελευταια 'tl' πριν την εναρξη, Pinnacle) · ιστορια U2017-U2025: πρωτα 16 / 32 ματς / αγων 1-2 / κανονικη περιοδος
     (+ Crown ανοιγμα/κλεισιμο οπου υπαρχει) · επιπεδο της μηχανης συνολων σημερα.
  3. ΜΕΓΑΛΕΣ ΔΙΑΦΩΝΙΕΣ (οπως bcl_bigedge_early): live-ισοδυναμη μηχανη (ec_fresh_engine_test run2 LIVE: περσι .2, ειδικοι 4·z συνδυασμος,
     φιλικα .5, εγχωρια κ1) walk-forward U2020-U2025 · pick χαντικαπ edge ≥8% στο ΑΝΟΙΓΜΑ Crown (σ 11.5) · ζωνες |μοντελο − αγορα|
     (αγορα = −γραμμη ανοιγματος) <4 / 4-7 / 7-10 / ≥10 × αγων 1-3 / 4-10 / 11+ · ROI ανοιγμα & κλεισιμο (ιδιο pick), n, θετικες σεζον.
     Ιδιο χωρις ειδικους (κ_x 0).
  4. ΚΙΝΗΣΗ ΚΟΝΤΡΑ (οπως bcl_move_against): ιδια picks · κινηση = (γραμμη κλεισ. − ανοιγμ.)·πλευρα (+ = κοντρα) · ενας πινακας ολης της σεζον.
  5α. ΒΑΡΟΣ ΕΙΔΙΚΩΝ ΣΗΜΕΡΑ: live μηχανη (αντιγραφο ec_refresh, χωρις δικτυο/εγγραφες) με & χωρις ειδικους, % του αρχικου 4·z που μενει.
  5β. LOSO: ΣΗΜΕΡΑ (ορος ειδικων μεσα στη μηχανη, κ_x 4) vs ΕΚ ΤΩΝ ΥΣΤΕΡΩΝ ορος κ·Δz·k/(k+r) πανω στη βαση χωρις ειδικους,
      k ∈ {2,3,4}, κ ∈ 0..6 ανα .5, r = μεσος αριθμος ματς EC (ολες οι φασεις) που εχουν ηδη παιξει οι 2 ομαδες.
      ΠΡΟ-ΔΗΛΩΜΕΝΟ (γραφτηκε ΠΡΙΝ την εκτελεση): μετρο = held-out RMSE διαφορας ΟΛΩΝ των ματς της σεζον · επιλογη (κ,k) με ελαχιστο
      τετρ. λαθος στις ΑΛΛΕΣ σεζον · ο ορος εκ των υστερων «ΠΕΡΝΑ» αν καλυτερος απο ΣΗΜΕΡΑ (κ_x 4 μεσα) σε ≥6/8 σεζον (συνδυασμος z,
      U2018-U2025) ή 3/3 (μονο αποδοσεις νικητη, U2023-U2025). Αναφορα: ΔRMSE ανα σεζον, ματς 1-3 / 4-6 / 7-10 / 11+.
      Ευαισθησια (οχι κριτηριο): ΣΗΜΕΡΑ με κ_x επιλεγμενο LOSO {0,2,3,4,5,6}.
  6. ΣΗΜΕΡΙΝΑ PICKS: αντιστοιχιση ονοματων, εγχωρια, αποτελεσματα, αναλυση διαφορας μοντελου (περσι / ειδικοι / φιλικα / εγχωρια / ματς EC).
Χρηση: python ec_audit_1310.py [ενοτητες, π.χ. 123456] · Εξοδος: ec_audit_1310_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, json, math, pickle, collections, builtins, io, contextlib, time, datetime as dt
import numpy as np, pandas as pd
from statistics import NormalDist
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
SCR = r'C:\Users\steli\AppData\Local\Temp\claude\C--Users-steli-My-Drive-Betting-Model\67d4ba59-0c37-4db7-a951-badbf5076962\scratchpad'
os.makedirs(SCR, exist_ok=True)
OUTF, CACHE = 'ec_audit_1310_out.txt', 'ec_audit_1310_preds.pkl'
SECT = sys.argv[1] if len(sys.argv) > 1 else '123456'
out = []
def P(s=''): print(s, flush=True); out.append(str(s))
_real_open = builtins.open
def _guard(file, mode='r', *a, **k):
    if isinstance(file, (str, os.PathLike)) and any(c in mode for c in 'wax+'):
        bn = os.path.basename(str(file))
        if bn not in (OUTF, CACHE): file = os.path.join(SCR, bn)
    return _real_open(file, mode, *a, **k)
builtins.open = _guard
def _snap(): return {f: os.path.getmtime(f) for f in os.listdir('.') if os.path.isfile(f)}
SNAP0 = _snap()
Phi = NormalDist().cdf; NN = NormalDist()
TODAY = dt.date.today()
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass

# =============================== LIVE ΑΝΤΙΓΡΑΦΟ (ec_refresh χωρις δικτυο) ===============================
def live_ns(kx=None):
    src = _real_open('ec_refresh.py', encoding='utf-8').read()
    head = src.split('# ---- 1. προγραμμα ----')[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '')
    if kx is not None: head = head.replace('KD = 1.0', f'KD = 1.0\nKX = {kx}')
    body = src.split('# ---- 3. μηχανη (ιδια με τα τεστ EuroCup) ----')[1]
    os.environ['EC_PROJ_F'] = os.path.join(SCR, f'ec_proj_audit_kx{kx}.json')
    ns = {'__name__': 'ecaudit'}; buf = _Buf()
    with contextlib.redirect_stdout(buf):
        exec(head + "\nS = json.load(open('ec_sched.json', encoding='utf-8'))\n" + body, ns)
    return ns, buf.getvalue()
NEED_LIVE = any(c in SECT for c in '1256')
if NEED_LIVE:
    t0 = time.time()
    L1, LOG1 = live_ns(None)
    L0, LOG0 = live_ns(0.0)
    print(f'(live αντιγραφα ετοιμα {time.time() - t0:.0f}s)', flush=True)
    SEASON = L1['SEASON']; SCH = L1['S'][SEASON]
    NAMES = {}
    for x in SCH: NAMES[x['hcode']] = x['home']; NAMES[x['acode']] = x['away']
    PROJ = json.load(_real_open('ec_projections.json', encoding='utf-8'))
    PRIOR = L1['PRIOR']

# =============================== 1. ΦΡΕΣΚΑΔΑ ===============================
if '1' in SECT:
    P('################ 1. ΦΡΕΣΚΑΔΑ ΔΕΔΟΜΕΝΩΝ ################')
    BX = json.load(_real_open('ec_box.json', encoding='utf-8'))
    bk = [v for k, v in BX.items() if k.startswith(SEASON)]
    pl = [x for x in SCH if x['played']]
    P(f'ec_projections.json generated {PROJ["generated"]} (UTC) · ec_sched: παιγμενα {len(pl)}/{len(SCH)}, τελευταιο {max(x["utc"] for x in pl)} · '
      f'ec_box {SEASON}: {len(bk)} box scores, τελευταιο {max(v["utc"] for v in bk)} · επομενο ματς {min(x["utc"] for x in SCH if not x["played"])}')
    # εγχωρια (ιδια δεδομενα με το live)
    from el_season import NG
    DOM = json.load(_real_open('bk_domestic.json', encoding='utf-8')); DOM.update(L1['extra'])
    MAPT = L1['MAPT']; dinfo = L1['_dinfo']; ddelta = L1['_ddelta']; today_cut = L1['today_cut']
    def ok(g): return str(g[4]).strip() not in ('', '-1', 'None') and str(g[5]).strip() not in ('', '-1', 'None') and (g[-1] if len(g) > 6 else 1) == 1
    LGLAST = {}
    for k, v in DOM.items():
        if not k.endswith(NG): continue
        ds = [g[1][:10] for g in v['games'] if ok(g)]
        LGLAST[k.split('_')[0]] = (max(ds) if ds else None, len(ds))
    # φιλικα (fs_bk_preseason, ids του ec_prior)
    PS = json.load(_real_open('fs_bk_preseason.json', encoding='utf-8'))
    start = min(pd.Timestamp(x['utc']).date() for x in SCH)
    npre = collections.Counter()
    for key, Lx in PS.items():
        if not key.endswith(str(L1['_Y'])): continue
        for e in Lx:
            if not e.get('ts') or e.get('hs') in (None, ''): continue
            d = dt.datetime.fromtimestamp(e['ts'], dt.timezone.utc).date()
            if not (dt.date(L1['_Y'], 8, 1) <= d < start): continue
            for c, fid in PRIOR.get('fs', {}).items():
                if fid in (e.get('hid'), e.get('aid')): npre[c] += 1
    ecn = collections.Counter()
    for x in pl: ecn[x['hcode']] += 1; ecn[x['acode']] += 1
    P(f'πρωταθληματα {NG} (τελευταιο ματς, παιγμενα): ' + ' · '.join(f'{L} {v[0]} ({v[1]})' for L, v in sorted(LGLAST.items())))
    P(f'{"κωδ":4s} {"ομαδα EC":30s} {"εγχωριο (αντιστοιχιση)":34s} {"EC":>3s} {"εγχ":>4s} {"φιλ":>4s} {"τελ. εγχωριο":>12s} {"Δ σημ.":>6s}  σημαια')
    flags, nodom = [], []
    for c in sorted(NAMES):
        m = MAPT.get(c)
        if m:
            Lg, tid = m; v = DOM.get(f'{Lg}_{NG}', {}); tn = v.get('teams', {}).get(str(tid), '?')
            gs = [g for g in v.get('games', []) if ok(g) and int(tid) in (int(g[2]), int(g[3])) and g[1][:10] <= str(TODAY)]
            last = max((g[1][:10] for g in gs), default='—'); nd = len(gs)
            fl = ''
            if nd == 0: fl = 'ΚΑΝΕΝΑ εγχωριο ματς'
            elif last < '2026-10-10' and (LGLAST.get(Lg, (None,))[0] or '') >= '2026-10-10': fl = f'ΣΤΑΜΑΤΑ {last} (λιγκα ως {LGLAST[Lg][0]})'
            if fl: flags.append(f'{c} {fl}')
            P(f'{c:4s} {NAMES[c][:30]:30s} {(Lg + " " + tn)[:34]:34s} {ecn[c]:3d} {nd:4d} {npre[c]:4d} {last:>12s} {ddelta(c, today_cut):+6.1f}  {fl}')
        else:
            nodom.append(c)
            P(f'{c:4s} {NAMES[c][:30]:30s} {"— ΧΩΡΙΣ εγχωριο —":34s} {ecn[c]:3d} {"—":>4s} {npre[c]:4d} {"—":>12s} {"0.0":>6s}  ΧΩΡΙΣ ΕΓΧΩΡΙΟ')
    P(f'σημαιες: {flags or "καμια"}')
    P(f'χωρις εγχωρια δεδομενα: ' + ', '.join(f'{c} {NAMES[c]}' for c in nodom))
    P('live log (εγχωρια):'); [P('  ' + ln) for ln in LOG1.splitlines() if 'εγχωρια' in ln or 'αντιστοιχ' in ln]

# =============================== 2. ΕΠΙΠΕΔΟ ΣΥΝΟΛΩΝ ===============================
if '2' in SECT:
    P(''); P('################ 2. ΕΠΙΠΕΔΟ ΣΥΝΟΛΩΝ ################')
    G = {g['code']: g for g in PROJ['games']}
    BF = {}
    for ln in _real_open('ec_closing_backfill.jsonl', encoding='utf-8'):
        r = json.loads(ln); BF[r['code']] = r
    OH = collections.defaultdict(list)
    for ln in _real_open('ec_odds_hist.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r.get('tl') is not None: OH[r['code']].append(r)
    rows = []
    for x in SCH:
        if not x['played']: continue
        g = G.get(x['code']); act = x['hs'] + x['as_']
        ko = pd.Timestamp(x['utc'])
        cand = [r for r in OH.get(x['code'], []) if pd.Timestamp(r['t'] + ('' if '+' in r['t'] else '+00:00')) < ko]
        mk = (sorted(cand, key=lambda r: r['t'])[-1]['tl'], 'pin') if cand else ((BF[x['code']]['tl'], 'crown') if x['code'] in BF else (np.nan, '—'))
        op = (sorted(cand, key=lambda r: r['t'])[0]['tl']) if cand else np.nan
        rows.append(dict(rnd=x['rnd'], act=act, model=g['total'] if g else np.nan, mk=mk[0], src=mk[1], op=op))
    R = pd.DataFrame(rows)
    for rd in (1, 2, 'ολα'):
        d = R if rd == 'ολα' else R[R.rnd == rd]
        mm = d.mk.notna()
        P(f'  αγων {rd}: n {len(d)} · πραγματικο {d.act.mean():.1f} · μοντελο (προ-αγωνα, projections) {d.model.mean():.1f} · '
          f'αγορα κλεισ. {d.mk[mm].mean():.1f} (n {mm.sum()}, {"/".join(sorted(set(d.src[mm])))})'
          + (f' · αγορα πρωτη τιμη (Pinnacle) {d.op.mean():.1f}' if d.op.notna().any() else '')
          + f' · πραγμ. − αγορα {(d.act - d.mk)[mm].mean():+.1f} · πραγμ. − μοντελο {(d.act - d.model).mean():+.1f} · τ.α. πραγμ. {d.act.std():.1f}')
    P(f'  over της αγορας: {(R.act > R.mk).sum()}/{R.mk.notna().sum()} · over του μοντελου: {(R.act > R.model).sum()}/{len(R)}')
    # ιστορια (ec_box) + Crown (nowgoal) οπου υπαρχει
    BX = json.load(_real_open('ec_box.json', encoding='utf-8'))
    H = pd.DataFrame([dict(season=v['season'], utc=v['utc'], rnd=v.get('rnd'), phase=v.get('phase'), tot=v['hs'] + v['as_'], hs=v['hs'], as_=v['as_'])
                      for v in BX.values() if v.get('hs') is not None and v.get('as_') is not None])
    H['t'] = pd.to_datetime(H.utc, utc=True); H = H.sort_values('t')
    # Crown συνολα (nowgoal t=23) — ανοιγμα/κλεισιμο, αντιστοιχιση σκορ + ωρα
    SCHN = {}
    for sea in ('20-21', '21-22', '22-23', '23-24', '24-25', '25-26'):
        for g in json.load(_real_open(f'nowgoal_ec/sched_{sea}.json', encoding='utf-8')):
            if g.get('hs') is not None: SCHN[g['ngid']] = g
    RW = {}
    for ln in _real_open('nowgoal_ec/odds.jsonl', encoding='utf-8'):
        r = json.loads(ln)
        if r['cid'] == 3 and r['t'] == 23: RW[r['ngid']] = r['rows']
    ix2 = {}
    for i, r in H.iterrows(): ix2.setdefault((int(r.hs), int(r.as_)), []).append(i)
    TO, TC = {}, {}
    for ng, g in SCHN.items():
        tip = pd.Timestamp(g['bj']) - pd.Timedelta(hours=8); hit = None
        for key_ in ((g['hs'], g['as_']), (g['as_'], g['hs'])):
            for i in ix2.get(key_, []):
                if abs(H.t[i].tz_localize(None) - tip) <= pd.Timedelta(hours=26): hit = i; break
            if hit is not None: break
        if hit is None: continue
        rws = sorted([x for x in RW.get(ng, []) if x[4] == 2 and x[1] is not None and x[0] + 8 * 3600 <= tip.timestamp() + 600], key=lambda x: x[0])
        if rws: TO[hit] = float(rws[0][1]); TC[hit] = float(rws[-1][1])
    H['op'] = [TO.get(i, np.nan) for i in H.index]; H['cl'] = [TC.get(i, np.nan) for i in H.index]
    P(''); P('  ΙΣΤΟΡΙΑ μεσου συνολου (ec_box) · [Crown ανοιγμα/κλεισιμο μεσος, οπου υπαρχει] · κανονικη περιοδος = RS')
    P(f'  {"σεζον":6s} {"πρωτα 16":>22s} {"πρωτα 32":>22s} {"αγων 1-2 RS":>22s} {"RS ολη":>22s} {"ολα":>7s}')
    def cl(d):
        s = f'{d.tot.mean():6.1f}'
        if d.cl.notna().sum() >= 0.5 * len(d): s += f' [{d.op.mean():.1f}/{d.cl.mean():.1f}]'
        return f'{s:>22s}'
    for s_ in sorted(H.season.unique()):
        d = H[H.season == s_]; rs = d[d.phase == 'RS']
        P(f'  {s_:6s} {cl(d.iloc[:16])} {cl(d.iloc[:32])} {cl(rs[rs.rnd <= 2])} {cl(rs)} {d.tot.mean():7.1f}')
    # επιπεδο μηχανης συνολων σημερα
    CT = L1['CTXT']; stT = L1['stateT'](CT, L1['today_cut'])
    lvl0 = CT['pm0'] * 2 * CT['mu0'] / 100; lvl1 = stT['pm'] * 2 * stT['mu'] / 100
    P(''); P(f'  ΜΗΧΑΝΗ ΣΥΝΟΛΩΝ (live): επιπεδο διοργανωσης (ρυθμος × 2μ, μεση ομαδα, χωρις καμπυλη/εγχωρια/φιλικα): αρχη σεζον {lvl0:.1f} '
      f'(ρυθμος {CT["pm0"]:.2f}, μ {CT["mu0"]:.2f}) → σημερα {lvl1:.1f} (ρυθμος {stT["pm"]:.2f}, μ {stT["mu"]:.2f}) · '
      f'καμπυλη αγων 3: {L1["CURVE_A"] + L1["CURVE_B"] * 2:+.2f} · μ_pre_T (ec_prior) {PRIOR.get("mu_pre_T")}')
    up = [g for g in PROJ['games'] if not g['played'] and g['round'] == 3]
    P(f'  αγων 3 (projections): μεσο συνολο μοντελου {np.mean([g["total"] for g in up]):.1f} (n {len(up)}) · αγων 3 ec_odds_latest '
      + (lambda o: f'μεση γραμμη Pinnacle {np.mean([v["pin"]["tl"] for v in o.values() if (v.get("pin") or {}).get("tl")]):.1f} (n {sum(1 for v in o.values() if (v.get("pin") or {}).get("tl"))})')(
          json.load(_real_open('ec_odds_latest.json', encoding='utf-8')).get('odds', {})))

# =============================== ΙΣΤΟΡΙΚΗ ΜΗΧΑΝΗ (ενοτητες 3, 4, 5β) ===============================
if any(c in SECT for c in '345'):
    if os.path.exists(CACHE):
        HC = pickle.load(_real_open(CACHE, 'rb')); print('(ιστορικες προβλεψεις απο cache)', flush=True)
    else:
        t0 = time.time()
        src = _real_open('ec_fresh_engine_test.py', encoding='utf-8').read()
        src = src.split("LIVE = (9999, 4, 5.0, .5, 5, .2, 4.0, .5)")[0].replace("sys.stdout.reconfigure(encoding='utf-8')", '', 1)
        NS = {'__name__': 'x'}
        with contextlib.redirect_stdout(_Buf()):
            exec(src, NS)
        print(f'  ιστορικη βαση ετοιμη {time.time() - t0:.0f}s', flush=True)
        D = NS['D']; run2 = NS['run2']
        ZC = dict(NS['ZC'])
        # z μονο αποδοσεις νικητη (οπως outright_persist_test: χωρις τιμη → −ln(1.5×max), τυποποιηση σε ολες τις ομαδες της σεζον)
        EX = json.load(_real_open('ec_expert.json', encoding='utf-8')); ZO = {}
        for S_ in ('U2023', 'U2024', 'U2025'):
            allt = sorted(set(D.home[D.season == S_]) | set(D.away[D.season == S_]))
            od = {c: d['odds'] for c, d in EX[S_].items() if d.get('odds') and c in allt}
            mx = max(od.values()); x = {t: -math.log(od[t]) if t in od else -math.log(1.5 * mx) for t in allt}
            v = np.array(list(x.values())); m_, s_ = v.mean(), v.std()
            for t in allt: ZO[(S_, t)] = (x[t] - m_) / s_
        PR = {}
        for kx in (0.0, 2.0, 3.0, 4.0, 5.0, 6.0):
            PR[('C', kx)] = run2(9999, 4, 5.0, .5, 5, .2, kx, .5); print(f'  συνδυασμος κ_x {kx} ({time.time() - t0:.0f}s)', flush=True)
        NS['ZC'] = ZO
        for kx in (2.0, 3.0, 4.0, 5.0, 6.0):
            PR[('O', kx)] = run2(9999, 4, 5.0, .5, 5, .2, kx, .5); print(f'  αποδοσεις κ_x {kx} ({time.time() - t0:.0f}s)', flush=True)
        NS['ZC'] = ZC
        HC = dict(PR=PR, ZC=ZC, ZO=ZO, season=D.season.values, home=D.home.values, away=D.away.values, phase=D.phase.values,
                  act=(D.hs - D.as_).values.astype(float), GN=NS['GN'], t=D.t.astype(str).values)
        pickle.dump(HC, _real_open(CACHE, 'wb'))
    Z = pickle.load(_real_open('ec_fresh_market.pkl', 'rb'))
    chk = np.nanmax(np.abs(Z['live'] - HC['PR'][('C', 4.0)]))
    P(''); P(f'ελεγχος: ιστορικες προβλεψεις live (κ_x 4) ιδιες με ec_fresh_market.pkl → μεγιστη διαφορα {chk:.4f}')
    MK = Z['MK']; ACT = HC['act']; GN = HC['GN']; SEA = HC['season']
    EVM = ['U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
def cover(m_, L, s=11.5):
    if abs(L - round(L)) < 1e-9: pw = Phi((m_ + L - .5) / s); pl = Phi((-m_ - L - .5) / s); return pw, 1 - pw - pl, pl
    pw = Phi((m_ + L) / s); return pw, 0.0, 1 - pw
res_ = lambda x, o: (o - 1) if x > 0 else (0 if x == 0 else -1)
def picks(v):
    rows = []
    for i, mk in MK.items():
        if SEA[i] not in EVM or not np.isfinite(v[i]): continue
        L, _, o1, o2 = mk['o']; Lc, _, c1, c2 = mk['c']; m = float(v[i])
        pw, pp, pl = cover(m, L); e1, e2 = pw * o1 + pp - 1, pl * o2 + pp - 1
        side, e, od = (1, e1, o1) if e1 >= e2 else (-1, e2, o2)
        if e < .08: continue
        oc = c1 if side == 1 else c2; ln = L * side
        rows.append(dict(y=SEA[i], gn=int(GN[i]), gap=abs(m + L), mv=(Lc - L) * side, role='dog' if ln > 0 else 'fav', edge=e,
                         pa=res_((ACT[i] + L) * side, od), pc=res_((ACT[i] + Lc) * side, oc)))
    return pd.DataFrame(rows)
def cell(d, col='pa'):
    if not len(d): return f'{"—":>21s}'
    ps = d.groupby('y')[col].mean()
    return f'{100 * d[col].mean():+6.1f}% ({len(d):3d}, {int((ps > 0).sum())}/{ps.size})'

# =============================== 3. ΜΕΓΑΛΕΣ ΔΙΑΦΩΝΙΕΣ ===============================
if '3' in SECT:
    P(''); P('################ 3. ΜΕΓΑΛΕΣ ΔΙΑΦΩΝΙΕΣ · χαντικαπ edge ≥8% στο ΑΝΟΙΓΜΑ Crown (σ 11.5) · U2020-U2025 · ROI (picks, θετικες σεζον) ################')
    P('διαφωνια = |μοντελο − (−γραμμη ανοιγματος)| · «κλεισιμο» = το ιδιο pick στη γραμμη/τιμη κλεισιματος · αγων = max(ματς ηδη παιγμενα των 2)+1')
    BANDS = [(0, 4, '<4 π.'), (4, 7, '4-7 π.'), (7, 10, '7-10 π.'), (10, 99, '≥10 π.')]
    ZN = [('αγων 1-3', lambda g: g <= 2), ('αγων 4-10', lambda g: (g >= 3) & (g <= 9)), ('αγων 11+', lambda g: g >= 10), ('ΟΛΑ', lambda g: g >= 0)]
    for lab, key in (('ΜΕ ειδικους (live: κ_x 4, συνδυασμος)', ('C', 4.0)), ('ΧΩΡΙΣ ειδικους (κ_x 0)', ('C', 0.0))):
        X = picks(HC['PR'][key])
        P(''); P(f'=== {lab} · picks {len(X)} ===')
        P(f'  {"":12s} {"ζωνη":8s} {"ανοιγμα":>21s}   {"κλεισιμο":>21s}')
        for zl, f in ZN:
            d0 = X[f(X.gn)]
            for lo, hi, bl in BANDS + [(0, 999, 'ολες')]:
                d = d0[(d0.gap >= lo) & (d0.gap < hi)]
                P(f'  {zl:12s} {bl:8s} {cell(d)}   {cell(d, "pc")}')

# =============================== 4. ΚΙΝΗΣΗ ΚΟΝΤΡΑ ===============================
if '4' in SECT:
    P(''); P('################ 4. ΚΙΝΗΣΗ ΑΓΟΡΑΣ ΑΝΟΙΓΜΑ→ΚΛΕΙΣΙΜΟ στην πλευρα του pick (live, edge ≥8% στο ανοιγμα, Crown, U2020-U2025, ολη η σεζον) ################')
    P('«κοντρα Χ» = η γραμμη της πλευρας μας μεγαλωσε κατα Χ (η αγορα πηγε αλλου) · ROI (picks, θετικες σεζον)')
    X = picks(HC['PR'][('C', 4.0)])
    B = [('προς εμας', -99, -0.25), ('καμια κινηση', -0.25, 0.25), ('κοντρα 0.5-1.5', 0.25, 1.75), ('κοντρα 2-2.5', 1.75, 2.75), ('κοντρα ≥3', 2.75, 99), ('ΟΛΑ', -99, 99)]
    P(f'  {"κινηση":16s} {"ΟΛΑ ανοιγμα":>21s} {"ΟΛΑ κλεισιμο":>21s} {"ΦΑΒ ανοιγμα":>21s} {"ΦΑΒ κλεισιμο":>21s} {"ΑΟΥΤ ανοιγμα":>21s} {"ΑΟΥΤ κλεισιμο":>21s}')
    for bl, lo, hi in B:
        d = X[(X.mv > lo) & (X.mv <= hi)]
        P(f'  {bl:16s} ' + ' '.join(cell(dd, c) for dd in (d, d[d.role == 'fav'], d[d.role == 'dog']) for c in ('pa', 'pc')))
    P(f'  (μεση κινηση ολων των picks {X.mv.mean():+.2f} π. · μεριδιο «κοντρα ≥0.5» {100 * (X.mv > .25).mean():.0f}% · «προς εμας» {100 * (X.mv < -.25).mean():.0f}%)')
    P('  ιδιο, αγων 1-3 μονο (πληροφοριακο):')
    for bl, lo, hi in B:
        d = X[(X.mv > lo) & (X.mv <= hi) & (X.gn <= 2)]
        P(f'  {bl:16s} ' + ' '.join(cell(dd, c) for dd in (d, d[d.role == 'fav'], d[d.role == 'dog']) for c in ('pa', 'pc')))

# =============================== 5α. ΒΑΡΟΣ ΕΙΔΙΚΩΝ ΣΗΜΕΡΑ ===============================
if '5' in SECT:
    P(''); P('################ 5α. ΠΟΣΟ ΑΠΟ ΤΟ ΑΡΧΙΚΟ 4·z ΜΕΝΕΙ ΣΗΜΕΡΑ (live αντιγραφο με vs χωρις ειδικους, net = O − D σε π./100) ################')
    tc = L1['today_cut']; s1 = L1['state_at'](L1['CTX'], tc); s0 = L0['state_at'](L0['CTX'], tc)
    KX = L1['KX']; rows = []
    for t in L1['CTX']['tl']:
        z = PRIOR['z'].get(t, 0.0); start = KX * z * 100 / 72
        now = (s1['O'][t] - s1['D'][t]) - (s0['O'][t] - s0['D'][t])
        n = sum(1 for x in SCH if x['played'] and t in (x['hcode'], x['acode']))
        rows.append((t, z, start, now, now / start if abs(start) > 1e-9 else np.nan, n))
    big = [r for r in rows if abs(r[1]) >= 0.3]
    P(f'  ομαδες με |z| ≥ 0.3: {len(big)} · ΔΙΑΜΕΣΟ % που μενει {100 * np.median([r[4] for r in big]):.0f}% (ευρος {100 * min(r[4] for r in big):.0f}-{100 * max(r[4] for r in big):.0f}%) · '
      f'ολες: διαμεσο {100 * np.nanmedian([r[4] for r in rows]):.0f}%')
    P(f'  ματς EC ανα ομαδα: {sorted(collections.Counter(r[5] for r in rows).items())} · τα ΕΓΧΩΡΙΑ ματς ΔΕΝ μειωνουν το βαρος των ειδικων (μπαινουν ως μετατοπιση της αφετηριας, οχι ως δεδομενα)')
    for r in sorted(rows, key=lambda r: -abs(r[1]))[:10]:
        P(f'    {r[0]} {NAMES.get(r[0], "")[:26]:26s} z {r[1]:+.2f} · αρχικο {r[2]:+5.1f}/100 → σημερα {r[3]:+5.1f}/100 ({100 * r[4]:.0f}%) · ματς EC {r[5]}')
    # σε ποντους διαφορας: Δ(μοντελο με − χωρις) για τα αυριανα/σημερινα ματς
    P('  σημερινα/επομενα ματς: διαφορα γηπ. με ειδικους vs χωρις (ποντοι):')
    for g in [g for g in PROJ['games'] if not g['played']][:8]:
        cut = (pd.Timestamp(g['utc']).date() - L1['d0date']).days if pd.Timestamp(g['utc']).date() <= TODAY else tc
        m1 = L1['predict'](L1['state_at'](L1['CTX'], cut), g['hcode'], g['acode'], g['neutral'])[0]
        m0 = L0['predict'](L0['state_at'](L0['CTX'], cut), g['hcode'], g['acode'], g['neutral'])[0]
        P(f'    {g["home"][:24]:24s} - {g["away"][:24]:24s} με {m1:+5.1f} · χωρις {m0:+5.1f} · ειδικοι {m1 - m0:+5.1f}')

# =============================== 5β. LOSO: ΣΗΜΕΡΑ vs ΕΚ ΤΩΝ ΥΣΤΕΡΩΝ ===============================
if '5' in SECT:
    P(''); P('################ 5β. LOSO: ορος ειδικων ΜΕΣΑ στη μηχανη (σημερα, κ_x 4) vs ΕΚ ΤΩΝ ΥΣΤΕΡΩΝ κ·Δz·k/(k+r) πανω στη βαση χωρις ειδικους ################')
    PH = HC['phase']; HOME, AWAY = HC['home'], HC['away']
    R_ = np.zeros(len(ACT)); cnt = collections.Counter()
    order = np.argsort(pd.to_datetime(HC['t']).values, kind='stable')
    for i in order:
        s_, h_, a_ = SEA[i], HOME[i], AWAY[i]
        R_[i] = (cnt[(s_, h_)] + cnt[(s_, a_)]) / 2.0; cnt[(s_, h_)] += 1; cnt[(s_, a_)] += 1
    SPL = [('1-3', GN <= 2), ('4-6', (GN >= 3) & (GN <= 5)), ('7-10', (GN >= 6) & (GN <= 9)), ('11+', GN >= 10), ('ολα', GN >= 0)]
    KAP = [x / 2 for x in range(13)]; KS = [2, 3, 4]
    BASE = HC['PR'][('C', 0.0)]
    def block(lab, ZZ, EVS, fam, crit):
        ZD = np.array([ZZ.get((SEA[i], HOME[i]), 0.0) - ZZ.get((SEA[i], AWAY[i]), 0.0) for i in range(len(ACT))])
        ev = np.isin(SEA, EVS) & np.isfinite(BASE)
        TODAYP = HC['PR'][(fam, 4.0)]
        SQ = {(kp, k): (ACT - (BASE + kp * ZD * k / (k + R_))) ** 2 for kp in KAP for k in KS}
        held = np.full(len(ACT), np.nan); ch = {}
        for Y in EVS:
            tr = ev & (SEA != Y); g = min(SQ, key=lambda g: (SQ[g][tr].sum(), g[0], g[1])); ch[Y] = g
            m = SEA == Y; held[m] = (BASE + g[0] * ZD * g[1] / (g[1] + R_))[m]
        # ευαισθησια: σημερα με κ_x LOSO
        kxs = [k for k in (0.0, 2.0, 3.0, 4.0, 5.0, 6.0) if (fam, k) in HC['PR'] or k == 0.0]
        PRk = {k: (HC['PR'][(fam, k)] if k > 0 else BASE) for k in kxs}
        heldT = np.full(len(ACT), np.nan); chT = {}
        for Y in EVS:
            tr = ev & (SEA != Y); k_ = min(kxs, key=lambda k: ((ACT - PRk[k]) ** 2)[tr].sum()); chT[Y] = k_
            heldT[SEA == Y] = PRk[k_][SEA == Y]
        rm = lambda v, m: math.sqrt(np.mean(((ACT - v) ** 2)[m]))
        P(''); P(f'=== {lab} · σεζον {EVS[0]}-{EVS[-1]} · ματς {int(ev.sum())} ===')
        P(f'  {"σεζον":6s} {"n":>4s} {"βαση(χωρις)":>11s} {"ΣΗΜΕΡΑ κx4":>10s} {"εκ υστ.LOSO":>11s} {"Δ(υστ−σημ)":>10s} {"(κ,k) επιλ.":>11s} {"σημ.κx LOSO":>11s} {"κx":>4s}')
        wins = 0
        for Y in EVS:
            m = ev & (SEA == Y); d = rm(held, m) - rm(TODAYP, m); wins += d < 0
            P(f'  {Y:6s} {int(m.sum()):4d} {rm(BASE, m):11.3f} {rm(TODAYP, m):10.3f} {rm(held, m):11.3f} {d:+10.3f} {str(ch[Y]):>11s} {rm(heldT, m):11.3f} {chT[Y]:4.0f}')
        P(f'  ΕΝΩΜΕΝΑ ανα αγων (RMSE βαση / σημερα κx4 / εκ υστ. LOSO / Δ υστ−σημ / n):')
        for sl, mm in SPL:
            m = ev & mm
            d_ = (ACT - held) ** 2 - (ACT - TODAYP) ** 2
            P(f'    αγων {sl:5s} {rm(BASE, m):.3f} / {rm(TODAYP, m):.3f} / {rm(held, m):.3f} / {rm(held, m) - rm(TODAYP, m):+.3f} '
              f'(ΔMSE {d_[m].mean():+.2f} ± {d_[m].std(ddof=1) / math.sqrt(m.sum()):.2f}) · n {int(m.sum())}')
        P(f'  → εκ των υστερων καλυτερο απο ΣΗΜΕΡΑ σε {wins}/{len(EVS)} σεζον (κριτηριο ≥{crit}) → {"ΠΕΡΝΑ" if wins >= crit else "ΔΕΝ ΠΕΡΝΑ"}')
        # προφιλ in-sample
        P('  προφιλ in-sample (ολες οι σεζον): ' + ' · '.join(
            (lambda kp: f'k {k}: κ* {kp} (RMSE {math.sqrt(SQ[(kp, k)][ev].mean()):.3f})')(min(KAP, key=lambda kp: SQ[(kp, k)][ev].sum())) for k in KS)
            + f' · βαση {rm(BASE, ev):.3f} · σημερα κx4 {rm(TODAYP, ev):.3f}')
    EV8 = ['U2018', 'U2019', 'U2020', 'U2021', 'U2022', 'U2023', 'U2024', 'U2025']
    block('ΣΥΝΔΥΑΣΜΟΣ z (καταταξεις + αποδοσεις νικητη οπου υπαρχουν, ιδιο με live)', HC['ZC'], EV8, 'C', 6)
    block('ΜΟΝΟ ΑΠΟΔΟΣΕΙΣ ΝΙΚΗΤΗ (z οπως outright_persist_test)', HC['ZO'], ['U2023', 'U2024', 'U2025'], 'O', 3)

# =============================== 6. ΣΗΜΕΡΙΝΑ PICKS ===============================
if '6' in SECT:
    P(''); P('################ 6. ΣΗΜΕΡΙΝΑ PICKS (ec_value_latest.json) ################')
    V = json.load(_real_open('ec_value_latest.json', encoding='utf-8'))
    P(f'scanned_at {V["scanned_at"]}')
    for p in V['picks']:
        if p['mkt'] == 'hcap':
            P(f'  {p["home"]} - {p["away"]} · χαντικαπ {"γηπ" if p["side"] == 1 else "φιλ"} {p["hcap"]:+g} @{p["odds"]} · edge {100 * p["edge"]:.1f}% · μοντελο {p["model_line"]:+.1f} · αγορα {p["mkt_line"]:+.1f}')
        else:
            P(f'  {p["home"]} - {p["away"]} · {p["bet"]} @{p["odds"]} · edge {100 * p["edge"]:.1f}% · μοντελο {p["model_total"]} · αγορα {p["mkt_total"]} · μιξη {p.get("mix_total")}')
    from el_season import NG
    DOM = json.load(_real_open('bk_domestic.json', encoding='utf-8')); DOM.update(L1['extra'])
    MAPT = L1['MAPT']
    P(''); P(f'  DOM_NAME (ec_refresh): {L1["DOM_NAME"]} · Lega A {NG}: ' + ', '.join(n for n in DOM[f"LBA_{NG}"]["teams"].values() if 'roma' in n.lower()))
    P('  αντιστοιχιση EC → εγχωριο: ' + ' · '.join(f'{c}→{MAPT[c][0]} {DOM[f"{MAPT[c][0]}_{NG}"]["teams"].get(str(MAPT[c][1]))}' if c in MAPT else f'{c}→—'
                                         for c in ('BCR', 'MRO', 'BLK', 'BAH', 'MAN', 'LKB', 'PAO', 'KLA', 'BOU')))
    # ελεγχος: χωρις DOM_NAME πως θα αντιστοιχιζοταν η BCR
    import el_domestic_live as EDL
    te = EDL._tok('Roma Basketball'); cands = [(round(len(te & EDL._tok(n)) / min(len(te), len(EDL._tok(n))) + .01 * len(te & EDL._tok(n)), 2), n)
                                              for n in DOM[f'LBA_{NG}']['teams'].values() if te & EDL._tok(n)]
    P(f'  (χωρις DOM_NAME το «Roma Basketball» → tokens {te} → υποψηφιες {cands} — ισοπαλια, θα επαιρνε την πρωτη)')
    P(f'  ελεγχος ταυτοτητας: ec_prior fs (Flashscore, απο σκορ αγωνων EC): BCR→{PRIOR["fs_name"].get("BCR")} · MRO→{PRIOR["fs_name"].get("MRO")}')
    def team_games(c):
        L_ = []
        for x in SCH:
            if x['played'] and c in (x['hcode'], x['acode']):
                me, op, sg = (x['hs'], x['as_'], 'εντος') if x['hcode'] == c else (x['as_'], x['hs'], 'εκτος')
                L_.append(f'EC {x["utc"][5:10]} {sg} vs {(x["away"] if x["hcode"] == c else x["home"])[:16]} {me}-{op} ({me - op:+d})')
        m = MAPT.get(c)
        if m:
            v = DOM[f'{m[0]}_{NG}']; tm = v['teams']
            for g in v['games']:
                if str(g[4]).strip() in ('', '-1', 'None') or int(m[1]) not in (int(g[2]), int(g[3])): continue
                h_ = int(g[2]) == int(m[1]); me, op = (int(g[4]), int(g[5])) if h_ else (int(g[5]), int(g[4]))
                L_.append(f'{m[0]} {g[1][5:10]} {"εντος" if h_ else "εκτος"} vs {tm.get(str(g[3] if h_ else g[2]), "?")[:16]} {me}-{op} ({me - op:+d})')
        return L_
    # αναλυση διαφορας μοντελου
    ns = L1; fit_eff = ns['fit_eff']; C = ns['CTX']; ix = C['ix']; n = C['n']; tl = C['tl']
    KX, KP, CARRY, H_ = ns['KX'], ns['KP'], ns['CARRY'], ns['H']
    def decomp(h, a, utc, neu):
        gd = pd.Timestamp(utc).date(); cut = (gd - ns['d0date']).days if gd <= TODAY else ns['today_cut']
        st = ns['state_at'](C, cut); mg, tt, poss = ns['predict'](st, h, a, neu)
        sh = np.array([ns['DOMSHIFT'](t, cut) for t in tl]) if ns['DOMSHIFT'] else np.zeros(n)
        prev = C['prev']
        comps = {'περσι (0.2×)': (np.array([CARRY * (prev.get(t) or (0, 0, 0))[0] for t in tl]), np.array([CARRY * (prev.get(t) or (0, 0, 0))[1] for t in tl])),
                 'ειδικοι 4·z': (np.array([KX * PRIOR['z'].get(t, 0) * 100 / 72 / 2 for t in tl]), -np.array([KX * PRIOR['z'].get(t, 0) * 100 / 72 / 2 for t in tl])),
                 'φιλικα .5·r': (np.array([KP * PRIOR['pre'].get(t, 0) * 100 / 72 / 2 for t in tl]), -np.array([KP * PRIOR['pre'].get(t, 0) * 100 / 72 / 2 for t in tl])),
                 'εγχωρια κ1': (sh / 2, -sh / 2)}
        so = sum(c_[0] for c_ in comps.values()); sd = sum(c_[1] for c_ in comps.values())
        chk = max(np.max(np.abs(so - (C['o0'] + sh / 2))), np.max(np.abs(sd - (C['d0'] - sh / 2))))
        past = C['dn'] < cut; hb0 = np.zeros(int(past.sum())); w = np.ones(int(past.sum())); z0 = np.zeros(int(past.sum()))
        res = {}
        for k_, (o_, d_) in comps.items():
            _, O_, D_ = fit_eff(C['hi'][past], C['ai'][past], z0, z0, hb0, w, n, o_, d_, ns['LAM'], 0.0)
            pri = poss * (o_[ix[h]] + d_[ix[a]] - o_[ix[a]] - d_[ix[h]]) / 100
            now = poss * (O_[ix[h]] + D_[ix[a]] - O_[ix[a]] - D_[ix[h]]) / 100
            res[k_] = (pri, now)
        rest = mg - sum(v[1] for v in res.values())
        return mg, poss, res, rest, chk, cut
    for p in [p for p in V['picks'] if p['mkt'] == 'hcap']:
        g = next(g for g in PROJ['games'] if g['code'] == p['code'])
        mg, poss, res, rest, chk, cut = decomp(g['hcode'], g['acode'], g['utc'], g['neutral'])
        P(''); P(f'  --- {g["home"]} ({g["hcode"]}) - {g["away"]} ({g["acode"]}) · αγορα γηπ {p["mkt_line"] if p["side"] == 1 else -p["hcap"]:+g} · '
              f'μοντελο σε projections {g["margin"]:+.1f} (γηπ.) · αντιγραφο σημερα {mg:+.1f} · κατοχες {poss:.1f} (ελεγχος αθροισματος {chk:.1e})')
        P(f'      συνιστωσα          αφετηρια(πριν ματς EC)  →  σημερα (μετα τα ματς EC)   [ποντοι διαφορας γηπεδουχου]')
        for k_, (pri, now) in res.items(): P(f'      {k_:18s} {pri:+6.1f} → {now:+6.1f}')
        P(f'      ματς EC + εδρα     {rest:+6.1f}   (υπολοιπο = συνολο − αφετηριακες συνιστωσες· εδρα μονη της ≈ {poss * H_ / 100:+.1f})')
        hist = sorted([json.loads(l) for l in _real_open('ec_odds_hist.jsonl', encoding='utf-8') if f'"code": {g["code"]},' in l], key=lambda r: r['t'])
        if hist:
            P(f'      γραμμη γηπ (ec_odds_hist, Pinnacle): πρωτη {hist[0]["line"]:+g} ({hist[0]["t"]}) → τελευταια {hist[-1]["line"]:+g} ({hist[-1]["t"]}) · '
              f'ολες: {" ".join(f"{r_[chr(108) + chr(105) + chr(110) + chr(101)]:+g}" for r_ in hist)} · γηπεδο {g.get("venue")} · ουδετερο {g["neutral"]}')
        for c in (g['hcode'], g['acode']):
            P(f'      {c} {NAMES[c]}: z {PRIOR["z"].get(c)} · φιλικα r {PRIOR["pre"].get(c)} · περσινο EC {"ναι" if C["prev"].get(c) else "ΟΧΙ (νεα, 0)"} · '
              f'εγχωρια Δ {ns["_ddelta"](c, cut):+.1f} π./ματς ({MAPT.get(c, ("—",))[0]})')
            for s in team_games(c): P(f'          {s}')

ch = sorted(f for f, m in _snap().items() if f not in (OUTF, CACHE) and (f not in SNAP0 or SNAP0[f] != m))
P(''); P(f'ελεγχος: αρχεια του repo που αλλαξαν κατα την εκτελεση: {ch or "κανενα"}')
builtins.open = _real_open
_real_open(OUTF if SECT == '123456' else os.path.join(SCR, f'ec_audit_{SECT}.txt'), 'w', encoding='utf-8').write('\n'.join(out))
