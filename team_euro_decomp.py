# -*- coding: utf-8 -*-
"""team_euro_decomp.py — 19/10/2026 (Στελιος: «Μποντο/Παρι: που οφειλεται η υποτιμηση; στα νουμερα τους, στο χαμηλο πρωταθλημα; εντος/εκτος;»).
Ευρωπαικα 2022-26 (σημερινη αλυσιδα, harness psg_europe_residual). Για καθε ομαδα και ομαδες της ιδιας λιγκας:
  ΔΙΑΦΟΡΑ γκολ πραγμ − μοντελο  =  [xG διαφορα − μοντελο] (ποιοτητα φασεων: το μοντελο υποτιμα τη δυναμη)  +  [γκολ − xG] (φινιρισμα/τερματοφυλακας/τυχη)
  ανα εδρα. + οι ΥΠΟΛΟΙΠΕΣ ομαδες της ιδιας λιγκας (αν υποαποδιδουν/υπεραποδιδουν ολες → θεμα λιγκας, αλλιως θεμα ομαδας)."""
import sys, os, json, glob
_s = open('psg_europe_residual.py', encoding='utf-8').read().split("P = D[D.team == 'Paris Saint-Germain']")[0]
_KEEP = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _KEEP
sys.stdout.reconfigure(encoding='utf-8')
XG = {}; LG = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items():
        sh = m.get('shots') or []; hid = int(m['home']['id'])
        if sh: XG[str(mid)] = (sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) == hid), sum(s['xg'] for s in sh if s.get('xg') is not None and int(s['tid']) != hid))
R = []
for i, mid in enumerate(MIDS):
    h, a = NM.get(str(mid), (None, None)); xg = XG.get(str(mid))
    if h is None or xg is None: continue
    for side, tm in ((1, h), (-1, a)):
        gf, ga = (GH[i], GA[i]) if side == 1 else (GA[i], GH[i]); mf, ma = (LH_N[i], LA_N[i]) if side == 1 else (LA_N[i], LH_N[i]); xf, xa = (xg[0], xg[1]) if side == 1 else (xg[1], xg[0])
        R.append(dict(team=tm, home=side == 1, sea=SEA[i], comp=COMP[i], rd=(gf - ga) - (mf - ma), rx=(xf - xa) - (mf - ma), fin=(gf - xf) - (ga - xa),
                      fin_f=gf - xf, fin_a=ga - xa, rx_f=xf - mf, rx_a=xa - ma))
D = pd.DataFrame(R)
def row(lab, y):
    if len(y) < 4: print(f'   {lab:30s} {len(y):3d} ματς (λιγα)'); return
    se = y.rd.std() / np.sqrt(len(y))
    print(f'   {lab:30s} {len(y):3d} ματς │ γκολ−μοντ {y.rd.mean():+.2f} ±{se:.2f} = xG−μοντ {y.rx.mean():+.2f} (επιθεση {y.rx_f.mean():+.2f} · αμυνα {-y.rx_a.mean():+.2f}) '
          f'+ φινιρισμα {y.fin.mean():+.2f} (βαζει {y.fin_f.mean():+.2f} · τρωει {-y.fin_a.mean():+.2f})')
GROUPS = {'Bodø/Glimt': ('Νορβηγια', ['Molde', 'Brann', 'Rosenborg', 'Viking', 'Lillestrøm', 'Tromsø', 'Fredrikstad', 'Sarpsborg 08', 'Vålerenga', 'Strømsgodset']),
          'Paris Saint-Germain': ('Γαλλια', ['Marseille', 'Lyon', 'Monaco', 'Lille', 'Lens', 'Nice', 'Rennes', 'Stade Brestois', 'Brest', 'Strasbourg', 'Toulouse', 'Nantes', 'Reims'])}
for team, (cn, others) in GROUPS.items():
    y = D[D.team == team]
    print(f'\n{"=" * 140}\n{team} — ευρωπαικα 2022-26 (με xG FotMob) · + = καλυτερα απο το μοντελο')
    row('ΟΛΑ', y); row('  εντος', y[y.home]); row('  εκτος', y[~y.home])
    for s in sorted(y.sea.unique()): row(f'  σεζον {s}', y[y.sea == s])
    o = D[D.team.isin(others)]
    print(f'   — αλλες ομαδες {cn} στην Ευρωπη ({", ".join(sorted(o.team.unique()))}) —')
    row(f'  ολες μαζι', o); row('    εντος', o[o.home]); row('    εκτος', o[~o.home])
