# -*- coding: utf-8 -*-
"""dom_bk_miss_analysis.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΠΟΥ ΠΕΦΤΕΙ ΕΞΩ ΤΟ ΜΟΝΤΕΛΟ (και η αγορα) — 7/10/2026 (Στελιος: «ευρωπαικα βοηθανε για οσες
παιζουν Ευρωπη; το προγραμμα βοηθαει; αν ερχονται απο ματς στην Ευρωπη κτλ — μπορεις να κανεις την αναλυση του που πεφτουμε εξω;»).
Προβλεψεις: ΤΕΛΙΚΗ βαση dom_bk_mech_v2 ανα πρωταθλημα. Αγορα: κλεισιμο Crown/Bet365 (μεσος, nowgoal_dom). Ματς κανονικης+πλει οφ 2021-26 με αγορα.
Για καθε κατηγορια (απο τη μερια του ΓΗΠΕΔΟΥΧΟΥ): n · λαθος μοντελου (πραγμ − μοντ) · λαθος αγορας (πραγμ − κλεισ) · RMSE μοντ/αγορα ·
  t της αγορας · σε ποσες σεζον ιδιο προσημο (x/5). «Πεφτουμε εξω» = μεγαλη μεροληψια μοντελου· «ευκαιρια» = μεροληψια ΑΓΟΡΑΣ (t ≥ 2, ≥4/5).
ΔΙΕΡΕΥΝΗΤΙΚΟ (πολλες κατηγοριες → καποιες θα βγουν τυχαια)· οτι βρεθει θελει δικο του προ-δηλωμενο τεστ. Εξοδος: dom_bk_miss_analysis_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, math, json, collections, bisect
import numpy as np, pandas as pd
LGS = ['ACB', 'LBA', 'GBL', 'TBL', 'LNB', 'BBL']
class _Buf(io.StringIO):
    def reconfigure(self, **k): pass
_src = open('dom_bk_outrights_test_4lg.py', encoding='utf-8').read()
_src = _src.replace("ARGS = ['GBL', 'TBL', 'LNB', 'BBL']", f"ARGS = {LGS!r}", 1).replace("sys.stdout.reconfigure(encoding='utf-8')", 'pass').split("KX = (0, 1, 2, 3, 4, 6)")[0]
with contextlib.redirect_stdout(_Buf()):
    exec(_src, globals())
FINAL = {'ACB': (.7, 12, 9999, .5, False, -8, 2), 'LBA': (1.0, 12, 120, None, False, 0, 0), 'GBL': (1.0, 4, 9999, None, True, 0, 0),
         'TBL': (1.0, 4, 60, .5, True, -8, 1), 'LNB': (1.0, 8, 9999, .5, True, 0, 0), 'BBL': (.85, 8, 9999, .5, False, -4, 0)}
EUC = ('EL', 'EC', 'BCL', 'FEC')

def _job(lg):
    b = FINAL[lg]; pr, gn, new, fin = run(lg, *b)
    return lg, pr, gn, new

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    O = []
    def W(s=''): print(s, flush=True); O.append(str(s))
    with Pool(6) as pool: res = pool.map(_job, LGS)
    pred = np.full(len(G), np.nan); gno = np.zeros(len(G), int); isnew = np.zeros(len(G), bool)
    for lg, pr, gn, nw in res:
        m = G.lg.values == lg; pred[m] = pr[m]; gno[m] = gn[m]; isnew[m] = nw[m]
    # ---- προγραμμα ομαδων απο ΟΛΕΣ τις διοργανωσεις (fs_bk_games: εγχωρια + EL/EC/BCL/FEC) ----
    FG = json.load(open('fs_bk_games.json', encoding='utf-8'))
    SCH = collections.defaultdict(list); EUTEAM = set()
    for key, L in FG.items():
        comp = key.split('_')[0]; y = int(key.split('_')[1])
        for e in L:
            if not (e.get('ts') and e.get('hid') and e.get('aid')): continue
            for t in (e['hid'], e['aid']):
                SCH[t].append((e['ts'], comp in EUC))
                if comp in EUC: EUTEAM.add((t, y))
    for v in SCH.values(): v.sort()
    def sched(t, ts):
        v = SCH.get(t, []); k = bisect.bisect_left(v, (ts - 3600, False))
        prev = v[k - 1] if k > 0 else None
        nxt = next((x for x in v[k:] if x[0] > ts + 3600), None)
        rest = (ts - prev[0]) / 86400 if prev else 9.0
        n7 = sum(1 for x in v[max(0, k - 6):k] if ts - x[0] <= 7 * 86400)
        return dict(rest=rest, prev_eu=bool(prev and prev[1] and rest <= 3.5), next_eu=bool(nxt and nxt[1] and (nxt[0] - ts) / 86400 <= 3.5), n7=n7)
    rows = []
    for i in MK:
        if G.y.values[i] not in EV or not np.isfinite(pred[i]): continue
        ts = G.t.values[i].astype('datetime64[s]').astype(int)
        h, a = sched(G.hid.values[i], ts), sched(G.aid.values[i], ts)
        y = int(G.y.values[i])
        rows.append(dict(lg=G.lg.values[i], y=y, act=act[i], pr=pred[i], mc=MK[i]['mc'], mo=MK[i]['mo'], gn=gno[i], new=isnew[i],
                         po='lay' in str(G.stage.values[i]).lower() or 'final' in str(G.stage.values[i]).lower(),
                         month=pd.Timestamp(G.t.values[i]).month, h_eu=(G.hid.values[i], y) in EUTEAM, a_eu=(G.aid.values[i], y) in EUTEAM,
                         h_prev=h['prev_eu'], a_prev=a['prev_eu'], h_next=h['next_eu'], a_next=a['next_eu'],
                         rest_d=min(h['rest'], 9) - min(a['rest'], 9), n7_d=h['n7'] - a['n7']))
    R = pd.DataFrame(rows); R['em'] = R.act - R.pr; R['ek'] = R.act - R.mc; R['gap'] = R.pr - R.mc
    W(f'Ματς με αγορα & προβλεψη 2021-26: {len(R)} · RMSE μοντελο {np.sqrt((R.em**2).mean()):.2f} · αγορα κλεισιμο {np.sqrt((R.ek**2).mean()):.2f} · ανοιγμα {np.sqrt(((R.act-R.mo)**2).mean()):.2f}')
    for lg in LGS:
        s = R[R.lg == lg]; W(f'  {NAME[lg]:9s} n {len(s):4d} · μοντελο {np.sqrt((s.em**2).mean()):.2f} · κλεισιμο {np.sqrt((s.ek**2).mean()):.2f} · μεση διαφορα μοντ−αγορας {s.gap.mean():+.2f} · |διαφ| {s.gap.abs().mean():.2f}')
    def line(lab, m, sub=R):
        s = sub[m]
        if len(s) < 25: return
        em, ek = s.em.mean(), s.ek.mean(); sd = s.ek.std(); t = ek / (sd / math.sqrt(len(s))) if sd > 0 else 0
        tm = em / (s.em.std() / math.sqrt(len(s)))
        sg = sum(1 for y in EV if (s.y == y).sum() >= 5 and np.sign(s[s.y == y].ek.mean()) == np.sign(ek))
        sgm = sum(1 for y in EV if (s.y == y).sum() >= 5 and np.sign(s[s.y == y].em.mean()) == np.sign(em))
        flag = ('  ◀ ΑΓΟΡΑ' if abs(t) >= 2 and sg >= 4 else '') + ('  ◀ ΜΟΝΤΕΛΟ' if abs(tm) >= 2.5 and sgm >= 4 else '')
        W(f'  {lab:46s} n {len(s):5d} · μοντ {em:+.2f} (t {tm:+.1f}, {sgm}/5) · αγορα {ek:+.2f} (t {t:+.1f}, {sg}/5) · RMSE {np.sqrt((s.em**2).mean()):.2f}/{np.sqrt((s.ek**2).mean()):.2f}{flag}')
    def block(title, items, sub=R):
        W(''); W(f'## {title}  (θετικο = ο γηπεδουχος πηγε ΚΑΛΥΤΕΡΑ απο την προβλεψη)')
        for lab, m in items: line(lab, m, sub)
    block('ΕΥΡΩΠΑΙΚΟ ΜΑΤΣ ≤3.5 μερες ΠΡΙΝ', [('μονο ο γηπεδουχος', R.h_prev & ~R.a_prev), ('μονο ο φιλοξενουμενος', ~R.h_prev & R.a_prev), ('και οι δυο', R.h_prev & R.a_prev), ('κανεις', ~R.h_prev & ~R.a_prev)])
    block('ΕΥΡΩΠΑΙΚΟ ΜΑΤΣ ≤3.5 μερες ΜΕΤΑ (ξεκουραση/rotation;)', [('μονο ο γηπεδουχος', R.h_next & ~R.a_next), ('μονο ο φιλοξενουμενος', ~R.h_next & R.a_next), ('και οι δυο', R.h_next & R.a_next)])
    block('ΔΙΑΦΟΡΑ ΞΕΚΟΥΡΑΣΗΣ (μερες γηπ − φιλοξ)', [('≤ −3', R.rest_d <= -3), ('−2 … −1', (R.rest_d > -3) & (R.rest_d <= -1)), ('−1 … +1', (R.rest_d > -1) & (R.rest_d < 1)),
                                                      ('+1 … +2', (R.rest_d >= 1) & (R.rest_d < 3)), ('≥ +3', R.rest_d >= 3)])
    block('ΜΑΤΣ ΣΤΙΣ 7 ΤΕΛΕΥΤΑΙΕΣ ΜΕΡΕΣ (γηπ − φιλοξ)', [('φιλοξ. 2+ περισσοτερα', R.n7_d <= -2), ('φιλοξ. 1 περισσοτερο', R.n7_d == -1), ('ιδια', R.n7_d == 0), ('γηπ. 1 περισσοτερο', R.n7_d == 1), ('γηπ. 2+ περισσοτερα', R.n7_d >= 2)])
    block('ΟΜΑΔΕΣ ΕΥΡΩΠΗΣ (φετος σε EL/EC/BCL/FEC)', [('γηπ Ευρωπη, φιλοξ οχι', R.h_eu & ~R.a_eu), ('φιλοξ Ευρωπη, γηπ οχι', ~R.h_eu & R.a_eu), ('και οι δυο', R.h_eu & R.a_eu), ('κανεις', ~R.h_eu & ~R.a_eu)])
    block('ΜΕΓΕΘΟΣ ΓΡΑΜΜΗΣ (κλεισιμο, αναμενομενη διαφορα γηπ.)', [('γηπ φαβορι ≥15', R.mc >= 15), ('γηπ φαβορι 8-15', (R.mc >= 8) & (R.mc < 15)), ('γηπ φαβορι 3-8', (R.mc >= 3) & (R.mc < 8)),
                                                                 ('κοντα (−3…+3)', R.mc.abs() < 3), ('φιλοξ φαβορι 3-8', (R.mc <= -3) & (R.mc > -8)), ('φιλοξ φαβορι 8-15', (R.mc <= -8) & (R.mc > -15)), ('φιλοξ φαβορι ≥15', R.mc <= -15)])
    block('ΔΙΑΦΩΝΙΑ ΜΟΝΤΕΛΟΥ−ΑΓΟΡΑΣ (μοντ − κλεισ) — ποιος εχει δικιο;', [('μοντ ≥4 πιο ψηλα για γηπ', R.gap >= 4), ('2…4', (R.gap >= 2) & (R.gap < 4)), ('−2…2', R.gap.abs() < 2),
                                                                         ('−4…−2', (R.gap <= -2) & (R.gap > -4)), ('μοντ ≥4 πιο χαμηλα', R.gap <= -4)])
    block('ΠΟΤΕ ΣΤΗ ΣΕΖΟΝ', [('αγων 1-5', R.gn <= 5), ('6-10', (R.gn > 5) & (R.gn <= 10)), ('11-20', (R.gn > 10) & (R.gn <= 20)), ('21+ (κανονικη)', (R.gn > 20) & ~R.po), ('πλει οφ', R.po)]
          + [(f'μηνας {m}', R.month == m) for m in (10, 11, 12, 1, 2, 3, 4, 5, 6)])
    block('ΝΕΟΦΕΡΜΕΝΕΣ', [('ματς με νεοφερμενη', R.new), ('χωρις', ~R.new)])
    W(''); W('## ΑΝΑ ΠΡΩΤΑΘΛΗΜΑ: ευρωπαικο πριν / μετα & ομαδες Ευρωπης')
    for lg in LGS:
        s = R[R.lg == lg]; W(f'  -- {NAME[lg]}')
        for lab, m in (('γηπ ευρωπαικο ΠΡΙΝ (μονο)', s.h_prev & ~s.a_prev), ('φιλοξ ευρωπαικο ΠΡΙΝ (μονο)', ~s.h_prev & s.a_prev),
                       ('γηπ ευρωπαικο ΜΕΤΑ (μονο)', s.h_next & ~s.a_next), ('φιλοξ ευρωπαικο ΜΕΤΑ (μονο)', ~s.h_next & s.a_next),
                       ('γηπ Ευρωπη vs οχι', s.h_eu & ~s.a_eu), ('φιλοξ Ευρωπη vs οχι', ~s.h_eu & s.a_eu)):
            line(lab, m, s)
    R.to_pickle('dom_bk_miss_R.pkl')
    W(''); W('## ΣΥΜΠΙΕΣΗ: κλιση πραγματικου πανω στην προβλεψη (1 = σωστη κλιμακα) & «τεντωμα» k·προβλεψη (LOSO ανα πρωταθλημα, ≥4/5)')
    for lg in LGS:
        s = R[R.lg == lg]; bm = np.polyfit(s.pr, s.act, 1)[0]; bk = np.polyfit(s.mc, s.act, 1)[0]; ratio = np.polyfit(s.pr, s.mc, 1)[0]
        KS = np.round(np.arange(.9, 1.61, .05), 2)
        rmk = lambda k, ys: float(np.sqrt(np.mean((s.act[s.y.isin(ys)] - k * s.pr[s.y.isin(ys)]) ** 2)))
        ch, dd = [], []
        for Y in EV:
            tr = [x for x in EV if x != Y]; k = min(KS, key=lambda k: rmk(k, tr)); ch.append(float(k)); dd.append(rmk(k, [Y]) - rmk(1.0, [Y]))
        W(f'  {NAME[lg]:9s} κλιση μοντελου {bm:.2f} · αγορας {bk:.2f} · αγορα/μοντελο {ratio:.2f} · LOSO k {ch} · RMSE {rmk(1.0, EV):.3f} → ' +
          f'{np.sqrt(np.mean([rmk(c, [Y]) ** 2 for c, Y in zip(ch, EV)])):.3f} · καλυτερα {sum(x < 0 for x in dd)}/5' + ('  ✓' if sum(x < 0 for x in dd) >= 4 else '  ✗'))
    open('dom_bk_miss_analysis_out.txt', 'w', encoding='utf-8').write(chr(10).join(O))

if __name__ == '__main__':
    main()
