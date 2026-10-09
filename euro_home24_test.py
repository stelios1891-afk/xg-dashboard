"""
euro_home24_test.py — 9/10/2026 (Στελιος «τρεξε οτι πιστευεις οτι αξιζει»): ΤΥΦΛΟ «ΓΗΠΕΔΟΥΧΟΣ στο UEL, τιμη 24 ωρες πριν».
Βρεθηκε post-hoc στο euro_role_venue (FotMob ματς 2223-2526: φαβορι εντος −24ω +11.2% n149, αουτσαιντερ εντος +12.2% n42, κλεισιμο +3.5%).
ΕΔΩ: ΟΛΑ τα ματς (οχι μονο FotMob), 2122-2526 (η 2122 = ΑΘΙΚΤΗ σεζον), Crown & SBOBET ΧΩΡΙΣΤΑ, χωρις μοντελο.
Συνολο στοιχηματων: πλευρα γηπεδουχου στο ασιατικο χαντικαπ, αποδοση 1.70-2.10, στην τελευταια τιμη ≤ ΚΟ−Τ (οχι παλιοτερη απο Τ+24ω).
ΠΡΟ-ΔΗΛΩΜΕΝΑ ΚΡΙΤΗΡΙΑ (UEL, −24ω, ολες οι γραμμες):
  (1) ROI > 0 ΚΑΙ στα 2 βιβλια ΧΩΡΙΣΤΑ · (2) θετικο σε ≥4/5 σεζον (μεσος βιβλιων) ΚΑΙ η 2122 θετικη ·
  (3) η γραμμη κινειται ΥΠΕΡ του γηπεδουχου απο −24ω ως το κλεισιμο (μεσος t > 2) · (4) ιδια φορα στις −48ω.
  Ελεγχος: UCL & UECL (αν δουλευει παντου = γενικο φαινομενο αγορας, αλλιως UEL-ειδικο).
"""
import sys, json, glob, os, datetime, math
import numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')
import picks
def parse_line(gs):
    try:
        p = [float(x) for x in str(gs).split('/')]
        if len(p) == 2 and p[0] < 0: p[1] = -abs(p[1])
        return sum(p) / len(p)
    except Exception: return None
FX = {}
for k, lst in json.load(open('europe_fixtures.json', encoding='utf-8')).items():
    comp, sea = k.rsplit('_', 1)
    for m in lst:
        sc = str(m.get('score') or '')
        if '-' not in sc: continue
        try: hs, as_ = [int(x) for x in sc.split('-')]
        except ValueError: continue
        FX[str(m['mid'])] = dict(comp=comp, sea=sea, ko=datetime.datetime.fromisoformat(m['utc'].replace('Z', '+00:00')).timestamp(), gd=hs - as_, rnd=m.get('round'))
TR = {}
for f in glob.glob('nowgoal_odds/*_U*.jsonl'):
    for ln in open(f, encoding='utf-8'):
        r = json.loads(ln)
        if r['cid'] not in (3, 31): continue
        rows = []
        for mt, u, gg, dn in r.get('ah') or []:
            L = parse_line(gg)
            try: rows.append((int(mt), -L, float(u) + 1, float(dn) + 1))
            except (TypeError, ValueError): pass
        TR[(str(r['mid']), 'Crown' if r['cid'] == 3 else 'SBOBET')] = sorted(x for x in rows if x[1] is not None)
def snap(mid, bk, h):
    f = FX[mid]; seq = TR.get((mid, bk))
    if not seq: return None
    cut = f['ko'] - h * 3600 if h else f['ko'] + 900
    prev = [x for x in seq if x[0] <= cut]
    if not prev or (h and (f['ko'] - prev[-1][0]) / 3600 > h + 24): return None
    return prev[-1][1:]
def home_strength(L, oh, oa):
    p = (1 / oh) / (1 / oh + 1 / oa); return -L + (p - 0.5) * 1.6       # υπεροχη γηπεδουχου ~ σε γκολ
rows = []
for mid, f in FX.items():
    for bk in ('Crown', 'SBOBET'):
        sc = snap(mid, bk, 0)
        for h in (48, 24, 6, 0):
            s = snap(mid, bk, h)
            if not s: continue
            L, oh, oa = s
            mv = (home_strength(*sc) - home_strength(L, oh, oa)) if (sc and h) else np.nan
            rows.append(dict(mid=mid, comp=f['comp'], sea=f['sea'], book=bk, h=h, L=L, oh=oh, mv=mv,
                             ok=1.70 <= oh <= 2.10, role='φαβορι' if L <= -0.5 else ('αουτσαιντερ' if L >= 0.5 else 'κοντη (0/±0.25)'),
                             pnl=picks.settle(f['gd'], 1, L, oh)))
D = pd.DataFrame(rows)
def cell(d):
    if len(d) < 8: return f'n{len(d):4d}' + ' ' * 18
    ps = d.groupby('sea').pnl.mean()
    return f'n{len(d):4d} {100 * d.pnl.mean():+6.1f}% {int((ps > 0).sum())}/{ps.size}'
SEAS = ['2122', '2223', '2324', '2425', '2526']
for comp in ('EuropaLeague', 'ChampionsLeague', 'ConferenceLeague'):
    print(f'\n===== {comp} — ΤΥΦΛΑ ο ΓΗΠΕΔΟΥΧΟΣ (αποδοση 1.70-2.10) =====')
    for h in (48, 24, 6, 0):
        x = D[(D.comp == comp) & (D.h == h) & D.ok]
        lab = 'κλεισιμο' if h == 0 else f'−{h}ω'
        print(f'  {lab:9s} Crown {cell(x[x.book == "Crown"])} · SBOBET {cell(x[x.book == "SBOBET"])} · μεσος {100 * x.pnl.mean():+6.1f}%'
              f' · ανα σεζον ' + ' '.join(f'{s}:{100 * x[x.sea == s].pnl.mean():+.0f}' for s in SEAS if (x.sea == s).sum() >= 8))
        if h == 24:
            for role in ('φαβορι', 'αουτσαιντερ', 'κοντη (0/±0.25)'):
                y = x[x.role == role]; print(f'       {role:16s} Crown {cell(y[y.book == "Crown"])} · SBOBET {cell(y[y.book == "SBOBET"])}')
    m = D[(D.comp == comp) & (D.h == 24) & D.mv.notna()]
    m2 = D[(D.comp == comp) & (D.h == 48) & D.mv.notna()]
    print(f'  ΚΙΝΗΣΗ γραμμης ΥΠΕΡ γηπεδουχου ως το κλεισιμο: απο −24ω {m.mv.mean():+.3f} γκολ (t {m.mv.mean() / (m.mv.std() / np.sqrt(len(m))):+.1f}, n{len(m)})'
          f' · απο −48ω {m2.mv.mean():+.3f} (t {m2.mv.mean() / (m2.mv.std() / np.sqrt(len(m2))):+.1f})')
# ---- κρισεις UEL ----
x = D[(D.comp == 'EuropaLeague') & (D.h == 24) & D.ok]; x48 = D[(D.comp == 'EuropaLeague') & (D.h == 48) & D.ok]
pb = x.groupby('book').pnl.mean(); ps = x.groupby('sea').pnl.mean()
m = D[(D.comp == 'EuropaLeague') & (D.h == 24) & D.mv.notna()]; tmv = m.mv.mean() / (m.mv.std() / np.sqrt(len(m)))
c1 = (pb > 0).all(); c2 = int((ps > 0).sum()) >= 4 and ps.get('2122', -1) > 0; c3 = tmv > 2; c4 = x48.pnl.mean() > 0
print(f'\nΚΡΙΤΗΡΙΑ UEL γηπεδουχος −24ω: (1) Crown {100 * pb.get("Crown", np.nan):+.1f}% / SBOBET {100 * pb.get("SBOBET", np.nan):+.1f}% {"✓" if c1 else "✗"}'
      f' · (2) σεζον {int((ps > 0).sum())}/5, 2122 {100 * ps.get("2122", np.nan):+.1f}% {"✓" if c2 else "✗"} · (3) κινηση t {tmv:+.1f} {"✓" if c3 else "✗"}'
      f' · (4) −48ω {100 * x48.pnl.mean():+.1f}% {"✓" if c4 else "✗"} → {"ΠΕΡΝΑ" if all((c1, c2, c3, c4)) else "ΔΕΝ ΠΕΡΝΑ"}')
