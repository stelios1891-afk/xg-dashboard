"""euro_trip_examples.py — 16/10/2026 (Στελιος: «παραδειγματα αγωνων 2.500-3.500 και >3.500 χλμ — ποιες ομαδες ταξιδεψαν τοσο; ποσο ειναι ο μ.ο.
ταξιδιων προς Bodø, Qarabağ, Sabah, Kairat»). Ημερολογιο/αποστασεις: ucl_away_streak_deep (ευθεια απο την εδρα του φιλοξενουμενου)."""
import sys, os, json, glob, datetime as dt
_s = open('ucl_away_streak_deep.py', encoding='utf-8').read(); _s = _s[:_s.index("SEAS = ['2122'")]
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
nm = {}; dt_ = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items():
        nm[int(m['home']['id'])] = m['home']['name']; nm[int(m['away']['id'])] = m['away']['name']; dt_[str(k)] = m['date'][5:17]
for k, L in json.load(open('europe_fixtures.json', encoding='utf-8')).items():
    for m in L: nm.setdefault(int(m['hid']), m['hname']); nm.setdefault(int(m['aid']), m['aname'])
A = E[E.s == -1].copy()
A['home'] = [nm.get(int(G[m]['h']), G[m]['h']) for m in A.mid]; A['away'] = [nm.get(int(G[m]['a']), G[m]['a']) for m in A.mid]
A['score'] = [f"{G[m]['hs']}-{G[m]['as_']}" for m in A.mid]
CL = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
for lo, hi, lab in ((2500, 3500, '2.500-3.500 χλμ'), (3500, 99999, '≥3.500 χλμ')):
    y = A[(A.trip >= lo) & (A.trip < hi)].sort_values('trip', ascending=False)
    print(f'\n=== {lab}: {len(y)} ταξιδια · πιο συχνοι προορισμοι (γηπεδουχοι): ' + ', '.join(f'{k} {v}' for k, v in y.home.value_counts().head(12).items()))
    print('   πιο συχνοι ταξιδιωτες: ' + ', '.join(f'{k} {v}' for k, v in y.away.value_counts().head(10).items()))
    for r in y.head(14 if lo >= 3500 else 0).itertuples():
        print(f'   {r.sea} {CL[r.comp]:4s} {r.home} – {r.away} {r.score} · {r.trip:,.0f} χλμ')
    if lo < 3500:
        for r in y.sample(min(14, len(y)), random_state=1).sort_values('trip', ascending=False).itertuples():
            print(f'   {r.sea} {CL[r.comp]:4s} {r.home} – {r.away} {r.score} · {r.trip:,.0f} χλμ')
print('\n=== ΜΕΣΟ ΤΑΞΙΔΙ ΤΟΥ ΑΝΤΙΠΑΛΟΥ ΠΡΟΣ ΤΗΝ ΕΔΡΑ (ολα τα ευρωπαικα 2122-2526 + φετινα)')
def tid_of(name):
    return [t for t, n in nm.items() if n == name]
FX27 = json.load(open('europe_fixtures_2627.json', encoding='utf-8')) if os.path.exists('europe_fixtures_2627.json') else {}
for team in ('Bodø/Glimt', 'Qarabağ FK', 'Sabah FK', 'Kairat Almaty'):
    ids = tid_of(team)
    y = A[A.home == team]
    vs = [km(LOC.get(int(G[m]['a'])), LOC.get(int(G[m]['h']))) for m in y.mid]
    line = f'   {team:14s}: ιστορικα {len(y)} ματς, μ.ο. {np.mean(vs):,.0f} χλμ (ελαχ. {min(vs) if vs else 0:,.0f} · μεγ. {max(vs) if vs else 0:,.0f})' if len(y) else f'   {team:14s}: ιστορικα 0 ματς'
    cur = []
    for k, L in FX27.items():
        for m in L:
            if int(m['hid']) in ids:
                d = km(LOC.get(int(m['aid'])), LOC.get(int(m['hid'])))
                cur.append(f"{m['aname']} {d:,.0f}")
    print(line + (' · ΦΕΤΟΣ: ' + ', '.join(cur) if cur else ''))
