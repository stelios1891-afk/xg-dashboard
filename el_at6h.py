# -*- coding: utf-8 -*-
"""el_at6h.py — EUROLEAGUE: «ΑΝ ΕΠΑΙΖΑ 6 ΩΡΕΣ ΠΡΙΝ» (16/10/2026, Στελιος «κρατα μονο τα picks που υπηρχαν μεχρι και 6 ωρες πριν το ματς»).
Για καθε ματς: το στιγμιοτυπο του el_value_latest.json (git, scanner ~καθε 30′) ακριβως πριν τη στιγμη «τζαμπολ − 6ω» (οχι παλιοτερο απο 2ω).
Picks ενεργα εκεινη τη στιγμη (οχι καταγραφες paper), στην ΤΙΜΗ εκεινης της στιγμης. Αποτελεσμα (el_projections) + CLV απλη μεθοδος
(τιμη μας / τιμη κλεισιματος ιδιας πλευρας − 1, μεταφρασμενη στη γραμμη μας) — ιδια με Pick History / el_clv_now.
Συγκριση: τα επισημα picks (πρωτη εμφανιση ≤72ω) των ιδιων ματς. Εξοδος: el_at6h_out.txt"""
import sys, io, json, subprocess, contextlib, datetime as dt, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
class _B(io.StringIO):
    def reconfigure(self, **k): pass
g = {'__name__': 'x'}
with contextlib.redirect_stdout(_B()):
    exec(open('el_clv_now.py', encoding='utf-8').read().replace("open('el_clv_now_out.txt', 'w', encoding='utf-8').write('\\n'.join(out))", ''), g)
ts, probs, fair, snap, SER, GAMES, SM, STT, NOW, OFFICIAL = (g[k] for k in ('ts', 'probs', 'fair', 'snap', 'SER', 'GAMES', 'SM', 'STT', 'NOW', 'recs'))
H = 6.0
log = subprocess.run(['git', 'log', '--since=2026-09-25', '--format=%H %cI', '--', 'el_value_latest.json'], capture_output=True, text=True).stdout.split('\n')
COM = sorted((ts(t), h) for h, t in (ln.split() for ln in log if ln.strip()))
cache = {}
def snapshot(t):
    c = [x for x in COM if x[0] <= t]
    if not c or (t - c[-1][0]).total_seconds() > 2 * 3600: return None, None
    h = c[-1][1]
    if h not in cache:
        raw = subprocess.run(['git', 'show', f'{h}:el_value_latest.json'], capture_output=True).stdout
        try: cache[h] = json.loads(raw.decode('utf-8'))
        except Exception: cache[h] = {}
    return c[-1][0], cache[h]
rows = []
for code, gm in GAMES.items():
    tip = ts(gm['utc'])
    t6 = tip - dt.timedelta(hours=H)
    if t6 > NOW: continue
    at, d = snapshot(t6)
    if d is None: continue
    for p in d.get('picks', []):
        if str(p.get('code')) != code or p.get('paper'): continue
        kind = 1 if p['mkt'] == 'hcap' else 2
        sig = SM if kind == 1 else STT; lo, hi = ((-80, 80) if kind == 1 else (90, 280))
        role = (('ΦΑΒΟΡΙ' if float(p['hcap']) < 0 else 'ΑΟΥΤΣΑΪΝΤΕΡ' if float(p['hcap']) > 0 else 'PK') if kind == 1
                else ('OVER' if str(p.get('bet', '')).startswith('Over') else 'UNDER'))
        dd = (1 if int(p['side']) == 1 else -1) if kind == 1 else (1 if role == 'OVER' else -1)
        L, o = float(p['hcap']), float(p['odds'])
        res = None
        if gm.get('hs') is not None and gm.get('as_') is not None:
            mar = gm['hs'] - gm['as_']; tot = gm['hs'] + gm['as_']
            x = ((mar if dd == 1 else -mar) + L) if kind == 1 else ((tot - L) * dd)
            res = 0.0 if abs(x) < 1e-9 else ((o - 1) if x > 0 else -1.0)
        ph = None
        cl = snap(SER.get(code, []), min(tip, NOW + dt.timedelta(minutes=1)), kind)
        if cl:
            m_cl = fair(-cl[0] if kind == 1 else cl[0], cl[1], cl[2], sig, lo, hi)
            if kind == 1:
                w, pp = probs(m_cl * dd, -L, sig); cL, co = (cl[0], cl[1]) if dd == 1 else (-cl[0], cl[2]); wc, pc = probs(m_cl * dd, -cL, sig)
            else:
                w, pp = probs(m_cl, L, sig) if dd == 1 else probs(-m_cl, -L, sig)
                cL, co = cl[0], (cl[1] if dd == 1 else cl[2]); wc, pc = probs(m_cl, cL, sig) if dd == 1 else probs(-m_cl, -cL, sig)
            if w > 0 and wc > 0:
                ph = o / (co * ((1 - pp) / w) / ((1 - pc) / wc)) - 1
        rows.append(dict(dir=(str(p['side']) if p['mkt'] == 'hcap' else str(p.get('bet') or '').split(' ')[0]), code=code, mkt=('ΧΑΝΤΙΚΑΠ' if kind == 1 else 'ΣΥΝΟΛΑ'), role=role, res=res, ph=ph, hrs=p.get('hrs_birth'),
                         lab=f"{tip:%d/%m} {p['home'][:16]}–{p['away'][:16]} · {('%+g' % L) if kind == 1 else p.get('bet')} @{o}"))
out = []
def P(s=''): print(s); out.append(str(s))
def line(lab, R):
    R2 = [x for x in R if x['res'] is not None]
    if not R2: P(f'  {lab:14s} —'); return
    u = sum(x['res'] for x in R2); w = sum(1 for x in R2 if x['res'] > 0); l = sum(1 for x in R2 if x['res'] < 0)
    c = [x['ph'] for x in R2 if x['ph'] is not None]
    P(f"  {lab:14s} {len(R2):3d} · {w}-{l}-{len(R2)-w-l} · {u:+6.2f}μ · ROI {100*u/len(R2):+6.1f}% · CLV {100*st.mean(c) if c else float('nan'):+5.1f}%")
CATS = (('ΦΑΒΟΡΙ', lambda x: x['role'] == 'ΦΑΒΟΡΙ'), ('ΑΟΥΤΣΑΪΝΤΕΡ', lambda x: x['role'] == 'ΑΟΥΤΣΑΪΝΤΕΡ'), ('ΧΑΝΤΙΚΑΠ', lambda x: x['mkt'] == 'ΧΑΝΤΙΚΑΠ'),
        ('OVER', lambda x: x['role'] == 'OVER'), ('UNDER', lambda x: x['role'] == 'UNDER'), ('ΣΥΝΟΛΑ', lambda x: x['mkt'] == 'ΣΥΝΟΛΑ'), ('ΟΛΑ', lambda x: True))
codes6 = {x['code'] for x in rows}
P(f'EUROLEAGUE · «αν επαιζα 6 ωρες πριν»: picks ενεργα στις −6ω, τιμη εκεινης της στιγμης · ματς με στιγμιοτυπο {len(codes6)}')
P(''); P('=== ΣΤΙΣ −6ω (Ν-Η-Ι · μοναδες · ROI · CLV απλη μεθοδος) ===')
for lab, f in CATS: line(lab, [x for x in rows if f(x)])
OFF = [x for x in OFFICIAL if x['kind'] == 'pick' and x['code'] in codes6]
P(''); P(f'=== ΣΥΓΚΡΙΣΗ: τα επισημα picks (πρωτη εμφανιση ≤72ω) στα ΙΔΙΑ {len(codes6)} ματς ===')
for lab, f in CATS: line(lab, [x for x in OFF if f(x)])
k6 = {(x['code'], x['mkt'], x['dir']) for x in rows}; ko = {(x['code'], x['mkt'], x['dir']) for x in OFF}
P(''); P('=== ΤΙ ΑΛΛΑΖΕΙ (ιδια ματς) ===')
line('επισημα που ΕΠΕΣΑΝ πριν τις −6ω', [x for x in OFF if (x['code'], x['mkt'], x['dir']) not in k6])
line('επισημα ΕΝΕΡΓΑ στις −6ω (τιμη επισημου)', [x for x in OFF if (x['code'], x['mkt'], x['dir']) in k6])
line('ΝΕΑ στις −6ω (δεν ηταν επισημα)', [x for x in rows if (x['code'], x['mkt'], x['dir']) not in ko])
P(''); P('  ανα pick στις −6ω:')
for x in sorted(rows, key=lambda x: x['lab']):
    P(f"    {x['lab']:58s} · {x['role']:11s} · {('%+.2f' % x['res']) if x['res'] is not None else 'εκκρεμει'} · CLV {('%+.1f%%' % (100*x['ph'])) if x['ph'] is not None else '—'}"
      + ('' if (x['code'], x['mkt'], x['dir']) in ko else ' · ΝΕΟ'))
open('el_at6h_out.txt', 'w', encoding='utf-8').write('\n'.join(out))
