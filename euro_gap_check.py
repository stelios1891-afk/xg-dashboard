# -*- coding: utf-8 -*-
"""euro_gap_check.py — 5/11/2026 (Στελιος: «ελεγξε το ναι»): ειναι σωστο το χασμα Βελγιο–Νορβηγια που δινει το μοντελο (St.Truiden–Brann: +1.25 απο τα 1.84 γκολ υπεροχης);
Α. ΑΠΟ ΠΟΥ ΒΓΑΙΝΕΙ: επιπεδο λιγκας s (αξιες παικτων / ClubElo) vs μεσο Elo της χωρας · τι λεει το Elo για το συγκεκριμενο ματς.
Β. ΑΠΟΚΛΙΣΗ ΑΝΑ ΛΙΓΚΑ: ευρωπαικα 2223-2526, ομαδα της λιγκας vs αλλη λιγκα, απο τη σκοπια της ομαδας: πραγματικη διαφορα γκολ (90′) & xG − μοντελο (live-οπως, 60% + Μ8) · αγορα κλεισιματος − μοντελο. Αρνητικο = η ομαδα μενει ΚΑΤΩ απο το μοντελο.
Γ. Βελγος vs Νορβηγος ματς προς ματς. Δ. ΜΑΤΣ ΣΑΝ ΑΥΤΟ: χασμα ≥0.2 υπερ της μιας πλευρας ΚΑΙ το μοντελο ≥0.5 γκολ πανω απο την αγορα προς την ιδια πλευρα: ποιος εχει δικιο.
ΚΡΙΣΗ: χασμα φουσκωμενο αν βελγικες μενουν κατω ή νορβηγικες πανω απο το μοντελο με απόκλιση >2 σφαλματα."""
import sys, math
_src = open('euro_clean_rules.py', encoding='utf-8').read()
exec(_src[:_src.index('# ---------- ΧΑΝΤΙΚΑΠ LIVE')])
from euro_engine import GAMMA_PLAYER, player_offsets
POFF = player_offsets()
LGH = np.array([_V['lg_h'][_VI[m]] if m in _VI else '?' for m in MIDS]) if 'lg_h' in _V else None
LGA = np.array([_V['lg_a'][_VI[m]] if m in _VI else '?' for m in MIDS]) if 'lg_a' in _V else None
print('κλειδια euro_v6', list(_V.keys())[:20])
assert LGH is not None
NM = {}
for f in glob.glob('data_Europe_*.json'):
    for k, m in json.load(open(f, encoding='utf-8')).items(): NM[str(k)] = (m['home']['name'], m['away']['name'], (m.get('date') or '')[:18])
C = pd.read_csv('clubelo_current.csv')
CC = {'Belgium': 'BEL', 'Eliteserien': 'NOR'}
print('\nΑ. ΕΠΙΠΕΔΟ ΛΙΓΚΑΣ (s = −γ·offset αξιων παικτων· μεγαλυτερο = δυνατοτερη)')
S = {lg: -GAMMA_PLAYER * v for lg, v in POFF.items()}
_ord = sorted(S, key=lambda k: -S[k])
for lg in _ord: print(f'   {lg:26s} s {S[lg]:+.3f}' + ('   ◄' if lg in CC else ''))
for lg, cc in CC.items():
    x = C[C.country == cc].sort_values('elo', ascending=False); print(f'   Elo {lg}: μεσο κορυφης-8 {x.elo.head(8).mean():.0f} · μεσο ολων {x.elo.mean():.0f} · n {len(x)}')
def elo_of(key):
    x = C[C.name.str.contains(key, case=False, na=False)]; return x[['name', 'elo']].values.tolist()
print('   St.Truiden', elo_of('Truiden'), '· Brann', elo_of('Brann'))
_e1 = elo_of('Truiden'); _e2 = elo_of('Brann')
if _e1 and _e2:
    dE = _e1[0][1] - _e2[0][1]; lx = math.sqrt(2.416 * 1.213); hf = 1.1419
    print(f'   ΜΟΝΟ Elo για St.Truiden–Brann: ΔElo {dE:+.0f} → υπεροχη {lx * math.exp(.1831 * dE / 100) * hf - lx * math.exp(-.1831 * dE / 100) / hf:+.2f} γκολ (μοντελο +1.84, αγορα ~+0.8)')
# ---- ανα ματς
LL = P6['INS']; rows = []
for i, mid in enumerate(MIDS):
    if LGH[i] == '?' or LGA[i] == '?' or LGH[i] == LGA[i]: continue
    fr = []
    for bk in ('Crown', 'SBOBET'):
        c = snap(mid, bk, 0)
        if c: fr.append(fair(c[0], c[1], c[2]))
    x = XG.get(mid)
    rows.append(dict(i=i, mid=mid, sea=SEA[i], comp=COMP[i], lh=LGH[i], la=LGA[i], m=LL[0][i] - LL[1][i], k=np.mean(fr) if fr else np.nan, gd=GD[i], xd=(x[0] - x[1]) if x else np.nan, sh=S.get(LGH[i], np.nan), sa=S.get(LGA[i], np.nan)))
A = pd.DataFrame(rows)
def persp(lg):
    a = A[A.lh == lg].assign(sg=1.); b = A[A.la == lg].assign(sg=-1.); z = pd.concat([a, b])
    return z.assign(r_g=z.sg * (z.gd - z.m), r_x=z.sg * (z.xd - z.m), r_k=z.sg * (z.k - z.m), ms=z.sg * z.m)
def line(z, lab):
    n = len(z); se = lambda c: z[c].std() / np.sqrt(z[c].notna().sum())
    return f"{lab:26s} n{n:4d} · μοντελο {z.ms.mean():+.2f} · γκολ−μοντελο {z.r_g.mean():+.2f} ±{se('r_g'):.2f} · xG−μοντελο {z.r_x.mean():+.2f} ±{se('r_x'):.2f} · αγορα−μοντελο {z.r_k.mean():+.2f} ±{se('r_k'):.2f}"
print('\nΒ. ΑΠΟΚΛΙΣΗ ΑΝΑ ΛΙΓΚΑ (απο τη σκοπια της ομαδας της λιγκας, γκολ/ματς· αρνητικο = κατω απο το μοντελο)')
L = sorted(set(A.lh) | set(A.la), key=lambda g: -len(persp(g)))
for g in L:
    z = persp(g)
    if len(z) >= 25 or g in CC: print('   ' + line(z, g) + ('   ◄' if g in CC else ''))
for g in CC:
    z = persp(g); print(f'\n   {g} ανα σεζον/διοργανωση')
    for s in SEAS:
        if (z.sea == s).any(): print('      ' + line(z[z.sea == s], s))
    for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'):
        if (z.comp == c).any(): print('      ' + line(z[z.comp == c], c))
    z2 = z.assign(hn=[NM[m][0] for m in z.mid], an=[NM[m][1] for m in z.mid]); tm = collections_tm = {}
    z2['team'] = np.where(z2.sg > 0, z2.hn, z2.an)
    for t, q in z2.groupby('team'):
        if len(q) >= 4: print(f"         {t[:22]:22s} n{len(q):3d} · μοντελο {q.ms.mean():+.2f} · γκολ−μοντ {q.r_g.mean():+.2f} · xG−μοντ {q.r_x.mean():+.2f} · αγορα−μοντ {q.r_k.mean():+.2f}")
print('\nΓ. ΒΕΛΓΟΣ vs ΝΟΡΒΗΓΟΣ (απο τη σκοπια του Βελγου)')
BN = A[((A.lh == 'Belgium') & (A.la == 'Eliteserien')) | ((A.lh == 'Eliteserien') & (A.la == 'Belgium'))]
for r in BN.itertuples():
    sg = 1 if r.lh == 'Belgium' else -1; print(f"   {r.sea} {NM[r.mid][0][:18]:18s} - {NM[r.mid][1][:18]:18s} μοντελο {sg * r.m:+.2f} · αγορα {sg * r.k:+.2f} · γκολ {sg * r.gd:+.0f} · xG {sg * r.xd:+.2f}")
if not len(BN): print('   κανενα')
print('\nΔ. ΜΑΤΣ ΣΑΝ ΑΥΤΟ: η μια λιγκα s ≥0.2 πανω ΚΑΙ το μοντελο ≥Χ γκολ πανω απο την αγορα προς τη δυνατη λιγκα (απο τη σκοπια της δυνατης λιγκας)')
Q = A.dropna(subset=['sh', 'sa', 'k']).copy(); Q['D'] = Q.sh - Q.sa; Q = Q[Q.D.abs() >= .2]; Q['sg'] = np.sign(Q.D)
for c in ('m', 'k', 'gd', 'xd'): Q[c + 's'] = Q.sg * Q[c]
Q['exc'] = Q.ms - Q.ks
def dd(z, lab):
    if not len(z): return
    print(f"   {lab:40s} n{len(z):4d} · μοντελο {z.ms.mean():+.2f} · αγορα {z.ks.mean():+.2f} · πραγματικα γκολ {z.gds.mean():+.2f} ±{z.gds.std() / np.sqrt(len(z)):.2f} · xG {z.xds.mean():+.2f} ±{z.xds.std() / np.sqrt(z.xds.notna().sum()):.2f} · |γκολ−μοντ| {(z.gds - z.ms).abs().mean():.2f} vs |γκολ−αγορα| {(z.gds - z.ks).abs().mean():.2f}")
for lab, m in (('ΟΛΑ με χασμα ≥0.2', Q.exc > -99), ('μοντελο πανω απο αγορα ≥0.25', Q.exc >= .25), ('≥0.5', Q.exc >= .5), ('≥0.75', Q.exc >= .75), ('≥1.0', Q.exc >= 1.0), ('μοντελο ΚΑΤΩ απο αγορα', Q.exc < 0)):
    dd(Q[m], lab)
Z = Q[Q.exc >= .5]
print('   ≥0.5 ανα διοργανωση/σεζον:')
for c in ('ChampionsLeague', 'EuropaLeague', 'ConferenceLeague'): dd(Z[Z.comp == c], '   ' + c)
for s in SEAS: dd(Z[Z.sea == s], '   ' + s)
print('   ≥0.5 οταν FotMob+FotMob:'); dd(Z[FM[Z.i.values]], '   Α')
print('   ≥0.5 UECL ματς:')
for r in Z[Z.comp == 'ConferenceLeague'].sort_values('exc', ascending=False).head(14).itertuples():
    print(f"      {r.sea} {NM[r.mid][0][:17]:17s}-{NM[r.mid][1][:17]:17s} μοντ {r.ms:+.2f} αγορα {r.ks:+.2f} γκολ {r.gds:+.0f} xG {r.xds:+.2f}")
# ---- Ε. Χωρις Bodø/ανα ομαδα Δανιας · ROI κλεισιματος «ματς σαν αυτο» · κανονες live κοντρα σε Δανους/Νορβηγους
print('\nΕ. ΧΩΡΙΣ ΤΙΣ ΚΟΡΥΦΑΙΕΣ')
for g, drop in (('Eliteserien', ('Bodø/Glimt',)), ('DanishSuperLiga', ('FC København', 'FC Midtjylland'))):
    z = persp(g); z = z.assign(team=np.where(z.sg > 0, [NM[m][0] for m in z.mid], [NM[m][1] for m in z.mid]))
    print('   ' + line(z, g + ' ολες')); print('   ' + line(z[~z.team.isin(drop)], g + ' χωρις κορυφαιες'))
    for t, q in z.groupby('team'):
        if g == 'DanishSuperLiga' and len(q) >= 4: print(f"         {t[:22]:22s} n{len(q):3d} · μοντελο {q.ms.mean():+.2f} · γκολ−μοντ {q.r_g.mean():+.2f} · xG−μοντ {q.r_x.mean():+.2f} · αγορα−μοντ {q.r_k.mean():+.2f}")
print('\nΣΤ. ROI ΣΤΟ ΚΛΕΙΣΙΜΟ, υπερ της δυνατης λιγκας (μεσος Crown/SBOBET), οταν μοντελο ≥Χ πανω απο αγορα')
def roi_close(z):
    r = []
    for q in z.itertuples():
        side = int(q.sg)
        for bk in ('Crown', 'SBOBET'):
            c = snap(q.mid, bk, 0)
            if c:
                ln = c[0] if side == 1 else -c[0]; o = c[1] if side == 1 else c[2]; r.append((q.sea, picks.settle(float(q.gd), side, ln, o)))
    return pd.DataFrame(r, columns=['sea', 'pnl'])
for T in (.25, .5, .75, 1.0):
    y = roi_close(Q[Q.exc >= T]); print(f"   ≥{T:.2f}: {len(y) / 2:5.1f} picks ROI {100 * y.pnl.mean():+6.1f}% {y.pnl.sum() / 2:+6.1f}μ │ " + ' '.join(f"{s[2:]}:{100 * y[y.sea == s].pnl.mean():+.0f}" for s in SEAS if (y.sea == s).any()))
print('\nΖ. ΚΑΝΟΝΕΣ LIVE (καθαρη μηχανη): τα picks ΚΟΝΤΡΑ σε ομαδα Δανιας/Νορβηγιας και ΥΠΕΡ ομαδας τους')
NORD = ('DanishSuperLiga', 'Eliteserien')
def opp_nord(z, against=True):
    k = []
    for r in z.itertuples():
        own, opp = (LGH[r.i], LGA[r.i]) if r.side == 1 else (LGA[r.i], LGH[r.i])
        k.append((opp if against else own) in NORD)
    return z[np.array(k, bool)] if len(z) else z
_uel_h = lambda i: 1
for lab, pack, thr in (('UCL φαβορι ≥4%', seq_ah(P6['INS'], GD, UCLA, 'fav', H_UCL, True), .04), ('UEL φαβορι εντος ≥4% (80%)', seq_ah(P8['INS'], GD, UELA, 'fav', H_UEL, sidefn=_uel_h), .04), ('UECL Α φαβορι ≥4%', seq_ah(P6['INS'], GD, ECA, 'fav', H_72), .04),
                       ('UCL αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, UCLA, 'dog', H_UCL, True), .10), ('UECL Α αουτσαιντερ ≥10%', seq_ah(P6['INS'], GD, ECA, 'dog', H_72), .10)):
    z = at(pack, thr); a = opp_nord(z, True); b = opp_nord(z, False)
    print(f'   {lab:30s} ΟΛΑ {desc(z)}'); print(f'      κοντρα σε Δανια/Νορβηγια {desc(a)}'); print(f'      υπερ Δανιας/Νορβηγιας   {desc(b)}')
_f = at(seq_ah(P6['INS'], GD, (COMP != 'x') & FM, 'fav', H_72), .04)
print('   ΟΛΑ τα φαβορι Ευρωπης ≥4% (72ω, 60%) κοντρα σε Δανια/Νορβηγια:', desc(opp_nord(_f, True)))
_t = opp_nord(_f, True); print('      ανα αντιπαλη λιγκα: ' + ' · '.join(f"{g}: {len(q) / 2:.0f}p {100 * q.pnl.mean():+.0f}%" for g, q in _t.assign(o=[(LGA[r.i] if r.side == 1 else LGH[r.i]) for r in _t.itertuples()]).groupby('o')))
