# -*- coding: utf-8 -*-
"""dom_bk_coach_test.py — ΕΓΧΩΡΙΑ ΜΠΑΣΚΕΤ: ΑΛΛΑΓΗ ΠΡΟΠΟΝΗΤΗ ΜΕΣΑ ΣΤΗ ΣΕΖΟΝ (7/10/2026, Στελιος «οκ δες και αυτα»).
Δεδομενα: dom_coach_changes.json (244 αλλαγες μεσα στη σεζον, 6 λιγκες 2020-27). Προβλεψεις = τελικη βαση dom_bk_mech_v2. Αγορα = κλεισιμο.
Γεγονος = αποχωρηση προπονητη (ημερ. κενου, αλλιως διορισμου)· αλλαγες της ιδιας ομαδας σε ≤21 μερες = ΕΝΑ γεγονος (υπηρεσιακος → νεος).
Παραθυρα: 5 ματς ΠΡΙΝ · ματς 1-4 ΜΕΤΑ · ματς 5-10 ΜΕΤΑ. Ολα απο τη μερια της ομαδας που αλλαξε προπονητη.
ΣΥΓΚΡΙΣΗ: ομαδες με ≥4 ηττες στα 5 τελευταια ΧΩΡΙΣ αλλαγη (στα 10 ματς πριν/μετα), επομενα 4 ματς.
ΠΡΟ-ΔΗΛΩΜΕΝΟ (ΠΡΙΝ την εκτελεση): παραθυρο ΜΕΤΑ ΠΕΡΝΑ αν το υπολοιπο κλεισιματος εχει το ιδιο προσημο με τον μεσο ορο σε ≥4/5 σεζον 2021-26
  ΚΑΙ το ROI προς εκεινη τη μερια στο ΚΛΕΙΣΙΜΟ > 0 σε ≥4/5 σεζον. Εξοδος: dom_bk_coach_test_out.txt"""
import os
for _v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'): os.environ[_v] = '1'
import sys, io, contextlib, math, json, collections, re, unicodedata
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
STOP = {'basket', 'basketball', 'club', 'bc', 'cb', 'bk', 'sk', 'the', 'pallacanestro', 'olympique', 'baskets', 'spor', 'kulubu', 'sporting', 'athens', 'thessaloniki', 'istanbul'}
def toks(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return {w for w in re.split(r'[^a-z0-9]+', s) if len(w) >= 3 and w not in STOP}
MANUAL = {('BBL', 'MHP Riesen Ludwigsburg'): 'Ludwigsburg', ('BBL', 'EWE Baskets Oldenburg'): 'Oldenburg', ('BBL', 'Fraport Skyliners'): 'Frankfurt',
          ('BBL', 'Skyliners Frankfurt'): 'Frankfurt', ('BBL', 'Mitteldeutscher BC'): 'Syntainics MBC', ('BBL', 'Syntainics MBC'): 'Syntainics MBC',
          ('TBL', 'Tofaş'): 'Tofas', ('TBL', 'Tofas'): 'Tofas', ('TBL', 'Merkezefendi'): 'Denizli Basket', ('LNB', 'ASVEL'): 'Lyon-Villeurbanne',
          ('LNB', 'Metropolitans 92'): 'Boulogne-Levallois', ('LNB', 'JL Bourg'): 'JL Bourg', ('LNB', 'Élan Chalon'): 'Chalon/Saone'}

def _job(lg):
    pr, gn, new, fin = run(lg, *FINAL[lg]); return lg, pr

def main():
    from multiprocessing import Pool
    sys.stdout.reconfigure(encoding='utf-8')
    O = []
    def W(s=''): print(s, flush=True); O.append(str(s))
    with Pool(6) as pool: res = pool.map(_job, LGS)
    pred = np.full(len(G), np.nan)
    for lg, pr in res: m = G.lg.values == lg; pred[m] = pr[m]
    LGV, YV, HID, AID, HN, AN = G.lg.values, G.y.values, G.hid.values, G.aid.values, G.home.values, G.away.values
    TS = pd.to_datetime(G.t.values)
    # ---- ομαδες ανα (λιγκα, σεζον) ----
    names = collections.defaultdict(dict)
    for i in range(len(G)):
        if LGV[i] in LGS: names[(LGV[i], int(YV[i]))][HN[i]] = HID[i]; names[(LGV[i], int(YV[i]))][AN[i]] = AID[i]
    rows = [r for r in json.load(open('dom_coach_changes.json', encoding='utf-8'))['rows'] if r.get('in_season')]
    ev = collections.defaultdict(list); miss = []
    for r in rows:
        lg = r['league']; y = int(r['season'][:4]); cand = names.get((lg, y), {})
        d = r.get('vacancy_date') or r.get('appointment_date')
        if not d or not cand: continue
        nm = MANUAL.get((lg, r['team']))
        if nm in cand: tid = cand[nm]
        else:
            tt = toks(r['team']); sc = sorted(((len(tt & toks(n)) / max(1, min(len(tt), len(toks(n)))), n) for n in cand), reverse=True)
            if not sc or sc[0][0] < .5 or (len(sc) > 1 and sc[1][0] == sc[0][0]): miss.append(f"{lg} {r['season']} {r['team']}"); continue
            tid = cand[sc[0][1]]
        ev[(lg, y, tid)].append(pd.Timestamp(d))
    events = []
    for (lg, y, tid), ds in ev.items():
        ds = sorted(ds); last = None
        for d in ds:
            if last is None or (d - last).days > 21: events.append((lg, y, tid, d))
            last = d
    W(f'αλλαγες μεσα στη σεζον: {len(rows)} · γεγονοτα (ενωμενα ≤21 μερες) {len(events)} · χωρις αντιστοιχιση {len(miss)}: {miss[:25]}')
    # ---- ματς ανα ομαδα ----
    tg = collections.defaultdict(list)
    for i in range(len(G)):
        if LGV[i] in LGS: tg[(LGV[i], int(YV[i]), HID[i])].append(i); tg[(LGV[i], int(YV[i]), AID[i])].append(i)
    for k in tg: tg[k].sort(key=lambda i: TS[i])
    def row(i, tid):
        s = 1 if HID[i] == tid else -1
        if i not in MK or not np.isfinite(pred[i]): return None
        L, o1, o2 = MK[i]['cl']; v = (act[i] + L) * s; od = o1 if s == 1 else o2
        return dict(y=int(YV[i]), lg=LGV[i], rk=(act[i] - MK[i]['mc']) * s, rm=(act[i] - pred[i]) * s, gap=(pred[i] - MK[i]['mc']) * s,
                    u=(od - 1) if v > 0 else (0 if v == 0 else -1), uo=(-1 if v > 0 else (0 if v == 0 else (o2 if s == 1 else o1) - 1)))
    W_ = collections.defaultdict(list); evn = set()
    for lg, y, tid, d in events:
        g = tg.get((lg, y, tid), [])
        before = [i for i in g if TS[i] < d][-5:]; after = [i for i in g if TS[i] >= d]
        for i in g: evn.add((i, tid)) if abs((TS[i] - d).days) <= 40 else None
        for lab, L_ in (('ΠΡΙΝ (5)', before), ('ΜΕΤΑ 1-4', after[:4]), ('ΜΕΤΑ 5-10', after[4:10])):
            for i in L_:
                x = row(i, tid)
                if x: W_[lab].append(x)
    # ---- συγκριση: κακο σερι χωρις αλλαγη ----
    for (lg, y, tid), g in tg.items():
        res_ = [(G.hs.values[i] > G.as_.values[i]) == (HID[i] == tid) for i in g]
        for k in range(5, len(g) - 1):
            if sum(1 for w in res_[k - 5:k] if not w) >= 4 and not any((i, tid) in evn for i in g[max(0, k - 10):k + 4]):
                for i in g[k:k + 4]:
                    x = row(i, tid)
                    if x: W_['ΣΥΓΚΡΙΣΗ κακο σερι χωρις αλλαγη (επομενα 4)'].append(x)
                break
    W(''); W('παραθυρο · n · υπολοιπο κλεισιματος (+ = η ομαδα πηγε καλυτερα απο τη γραμμη) · μοντελο · διαφ. μοντ−αγορας · ROI ομαδας κλεισ. · ανα σεζον')
    for lab, L_ in W_.items():
        D = pd.DataFrame(L_); ins = D[D.y.isin(EV)]
        if len(ins) < 10: continue
        t = ins.rk.mean() / (ins.rk.std() / math.sqrt(len(ins)))
        sg = np.sign(ins.rk.mean()); py = {Y: D[D.y == Y].rk.mean() for Y in [2020] + EV if (D.y == Y).sum() >= 5}
        uy = {Y: (D[D.y == Y].u if sg > 0 else D[D.y == Y].uo).mean() for Y in EV if (D.y == Y).sum() >= 5}
        W(f'  {lab:44s} n {len(ins):4d} · υπολ. {ins.rk.mean():+.2f} (t {t:+.1f}) · μοντ {ins.rm.mean():+.2f} · διαφ {ins.gap.mean():+.2f} · ROI ομαδας {ins.u.mean()*100:+.1f}%')
        W('      ανα σεζον υπολ. ' + ' '.join(f'{Y % 100}:{v:+.1f}' for Y, v in py.items()) + f' · ROI {"ομαδας" if sg > 0 else "αντιπαλου"} ' + ' '.join(f'{Y % 100}:{v*100:+.0f}%' for Y, v in uy.items()))
        if lab.startswith('ΜΕΤΑ'):
            c1 = sum(1 for Y in EV if np.sign(py.get(Y, 0)) == sg) >= 4; c2 = sum(1 for Y in EV if uy.get(Y, -1) > 0) >= 4
            W(f'      ΚΡΙΣΗ (υπερ {"ομαδας" if sg > 0 else "αντιπαλου"}): προσημο ≥4/5 {"✓" if c1 else "✗"} · ROI ≥4/5 {"✓" if c2 else "✗"} → ' + ('ΠΕΡΝΑ' if c1 and c2 else '✗'))
    open('dom_bk_coach_test_out.txt', 'w', encoding='utf-8').write(chr(10).join(O))

if __name__ == '__main__':
    main()
