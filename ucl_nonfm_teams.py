"""ucl_nonfm_teams.py — 12/10/2026 (Στελιος: «οταν προβλεπουμε τις ομαδες χωρις FotMob απεναντι σε ομαδες με FotMob, πως πανε οι προβλεψεις μας
για αυτες τις ομαδες; αν πανε καλα, ισως εχουμε καλυτερη εικονα για τα Γ vs Γ, οπως Σαμπαχ - Σλαβια»).
ΔΙΑΓΝΩΣΤΙΚΟ, 4 σεζον (2223-2526), φαση λιγκας/ομιλων + νοκ-αουτ, ΚΛΕΙΣΙΜΟ Crown/SBOBET για την αγορα:
  1) UCL, κατηγορια Β: η ομαδα χωρις FotMob — επιθεση (ποσα βαζει) & αμυνα (ποσα τρωει) vs μοντελο / xG / αγορα
  2) ολες οι διοργανωσεις: ιδια ομαδα vs FotMob αντιπαλο ή vs αλλη χωρις FotMob (λαθος «κλιμακας» ή λαθος ομαδας;)
  3) ματς Γ (κανεις FotMob) σε ολες τις διοργανωσεις: συνολο & διαφορα πραγμ/μοντελο/αγορα + picks με κανονες UCL
  4) οι 4 φετινες ομαδες UCL χωρις FotMob (Σαμπαχ, Σαχταρ, Σλαβια, Σλοβαν) στα ευρωπαικα τους 4 σεζον
"""
import sys
src = open('uecl_categories.py', encoding='utf-8').read().split('import pickle as _pkl, collections')[0]
exec(src)
import collections
NL = chr(10)
LH_N, LA_N, sdist, cover_q, edge, snap_ah, GD = (u[k] for k in ('LH_N', 'LA_N', 'sdist', 'cover_q', 'edge', 'snap', 'GD'))
LH_N = np.asarray(LH_N, float); LA_N = np.asarray(LA_N, float); GD = np.asarray(GD, float)
V6 = _V; VI = _VI
LAB = {'shots': 'FotMob', 'griffis': 'Ben', 'goals': 'γκολ+Elo'}
CN = {'ChampionsLeague': 'UCL', 'EuropaLeague': 'UEL', 'ConferenceLeague': 'UECL'}
EUM = {}
for f in glob.glob('data_Europe_*.json'):
    for mid, m in json.load(open(f, encoding='utf-8')).items(): EUM[str(mid)] = m
def xg_side(m, tid):
    return sum(s['xg'] for s in (m.get('shots') or []) if s.get('xg') is not None and int(s['tid']) == tid)
def implied_margin(i, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); Tt = LH_N[i] + LA_N[i]; lo, hi = -5.0, 5.0
    for _ in range(26):
        M = (lo + hi) / 2
        pw, pp = cover_q(sdist(max((Tt + M) / 2, .05), max((Tt - M) / 2, .05)), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
S = []; MT = []
for i in range(len(MIDS)):
    j = VI.get(str(MIDS[i]))
    if j is None or LH_N[i] <= 0 or COMP[i] not in CN: continue
    m = EUM.get(str(MIDS[i]))
    if not m or not m.get('shots'): continue
    sh, sa = LAB.get(V6['src_h'][j], '?'), LAB.get(V6['src_a'][j], '?')
    hid, aid = int(m['home']['id']), int(m['away']['id'])
    s = snap_ah(MIDS[i], 'Crown', 0) or snap_ah(MIDS[i], 'SBOBET', 0)
    so = snap_ou(MIDS[i], 'Crown', 0) or snap_ou(MIDS[i], 'SBOBET', 0)
    kgd = implied_margin(i, *s) if s else np.nan; ktot = mtot(*so) if so else np.nan
    kh = (ktot + kgd) / 2 if np.isfinite(ktot) and np.isfinite(kgd) else np.nan; ka = (ktot - kgd) / 2 if np.isfinite(ktot) and np.isfinite(kgd) else np.nan
    c = 'Α' if sh == sa == 'FotMob' else ('Β' if 'FotMob' in (sh, sa) else 'Γ')
    for venue, team, src_, osrc, g, lam, lou, xg, k in (('εντος', m['home']['name'], sh, sa, GH[i], LH_N[i], OH[i], xg_side(m, hid), kh),
                                                     ('εκτος', m['away']['name'], sa, sh, GA[i], LA_N[i], OA[i], xg_side(m, aid), ka)):
        S.append(dict(i=i, comp=CN[COMP[i]], sea=SEA[i], ph=V6['phase'][j], cat=c, venue=venue, team=team, src=src_, osrc=osrc, g=g, lam=lam, lou=lou, xg=xg, k=k))
    MT.append(dict(i=i, comp=CN[COMP[i]], sea=SEA[i], ph=V6['phase'][j], cat=c, pair='+'.join(sorted((sh, sa))), tot=GH[i] + GA[i], mtot_=OH[i] + OA[i],
                   ktot=ktot, gd=GH[i] - GA[i], mgd=LH_N[i] - LA_N[i], kgd=kgd))
S = pd.DataFrame(S); MTD = pd.DataFrame(MT)
se = lambda a: a.std() / max(np.sqrt(len(a)), 1)
def row(x, lab, w=44):
    if len(x) < 8: return f'   {lab:{w}s} n{len(x):3d} (λιγα)'
    return (f'   {lab:{w}s} n{len(x):3d} · γκολ {x.g.mean():.2f} · μοντελο {x.lam.mean():.2f} ({(x.g - x.lam).mean():+.2f}±{se(x.g - x.lam):.2f}) · '
            f'xG {x.xg.mean():.2f} · αγορα {x.k.mean():.2f} ({(x.g - x.k).mean():+.2f})')
_OPP = {(r.i, r.venue): k for k, r in S.iterrows()}
def opp(x):                                  # η γραμμη του αντιπαλου καθε ομαδας (τα γκολ που ΤΡΩΕΙ η ομαδα)
    return S.loc[[_OPP[(r.i, 'εκτος' if r.venue == 'εντος' else 'εντος')] for r in x.itertuples()]]
# ===== 1 =====
print('1. CHAMPIONS LEAGUE, κατηγορια Β — η ομαδα ΧΩΡΙΣ FotMob απεναντι σε ομαδα με FotMob (+ = βαζει/τρωει περισσοτερα απ οσα λεμε)')
for srcn in ('Ben', 'γκολ+Elo', 'ολες'):
    x = S[(S.comp == 'UCL') & (S.cat == 'Β') & ((S.src == srcn) if srcn != 'ολες' else (S.src != 'FotMob'))]
    print(f'   {srcn}:')
    print(row(x, '      ΕΠΙΘΕΣΗ (γκολ που βαζει)'))
    print(row(opp(x), '      ΑΜΥΝΑ (γκολ που τρωει)'))
    if srcn == 'ολες':
        for v in ('εντος', 'εκτος'):
            y = x[x.venue == v]; print(row(y, f'      ΕΠΙΘΕΣΗ {v}')); print(row(opp(y), f'      ΑΜΥΝΑ {v}'))
y = MTD[(MTD.comp == 'UCL') & (MTD.cat == 'Β')]
print(f'   ΣΥΝΟΛΟ ματς Β (n{len(y)}): πραγμ {y.tot.mean():.2f} / μοντελο {y.mtot_.mean():.2f} / αγορα {y.ktot.mean():.2f} · '
      f'(στο live τα γκολ της ομαδας ΜΕ FotMob ×1.22 στα συνολα → διορθωνει το «τρωει»)')
# ===== 2 =====
print(NL + '2. ΟΛΕΣ ΟΙ ΔΙΟΡΓΑΝΩΣΕΙΣ (UCL+UEL+UECL): ομαδα χωρις FotMob — vs αντιπαλο ΜΕ FotMob ή vs αντιπαλο ΧΩΡΙΣ FotMob')
for srcn in ('Ben', 'γκολ+Elo'):
    for olab, om in (('vs ΜΕ FotMob', S.osrc == 'FotMob'), ('vs ΧΩΡΙΣ FotMob', S.osrc != 'FotMob')):
        x = S[(S.src == srcn) & om]
        print(row(x, f'{srcn} {olab} · ΕΠΙΘΕΣΗ')); print(row(opp(x), f'{srcn} {olab} · ΑΜΥΝΑ'))
print('   ανα διοργανωση (ολες οι πηγες χωρις FotMob):')
for cm in ('UCL', 'UEL', 'UECL'):
    for olab, om in (('vs ΜΕ', S.osrc == 'FotMob'), ('vs ΧΩΡΙΣ', S.osrc != 'FotMob')):
        x = S[(S.comp == cm) & (S.src != 'FotMob') & om]
        print(row(x, f'   {cm} {olab} FotMob · ΕΠΙΘΕΣΗ')); print(row(opp(x), f'   {cm} {olab} FotMob · ΑΜΥΝΑ'))
# ===== 3 =====
print(NL + '3. ΜΑΤΣ Γ (κανεις FotMob) — συνολο & διαφορα (γηπ−φιλοξ): πραγματικο / μοντελο / αγορα κλεισιματος')
def mline(y, lab):
    if len(y) < 5: return f'   {lab:28s} n{len(y):3d} (λιγα)'
    return (f'   {lab:28s} n{len(y):3d} · ΣΥΝΟΛΟ {y.tot.mean():.2f} / {y.mtot_.mean():.2f} / {y.ktot.mean():.2f} (πραγμ−μοντ {(y.tot - y.mtot_).mean():+.2f}±{se(y.tot - y.mtot_):.2f}) · '
            f'ΔΙΑΦΟΡΑ {y.gd.mean():+.2f} / {y.mgd.mean():+.2f} / {y.kgd.mean():+.2f} (πραγμ−μοντ {(y.gd - y.mgd).mean():+.2f}±{se(y.gd - y.mgd):.2f})')
G = MTD[MTD.cat == 'Γ']
print(mline(G, 'ΟΛΑ Γ'))
for cm in ('UCL', 'UEL', 'UECL'): print(mline(G[G.comp == cm], f'{cm}'))
for pr in sorted(G.pair.unique()): print(mline(G[G.pair == pr], pr))
print(mline(MTD[MTD.cat == 'Α'], '(συγκριση: ΟΛΑ Α)'))
print(mline(MTD[MTD.cat == 'Β'], '(συγκριση: ΟΛΑ Β)'))
# ακριβεια: ποιος πεφτει πιο κοντα, μοντελο ή αγορα (ΜΑΕ)
for c in ('Α', 'Β', 'Γ'):
    y = MTD[(MTD.cat == c) & MTD.ktot.notna() & MTD.kgd.notna()]
    print(f'   ακριβεια {c} (n{len(y)}): μεσο λαθος ΣΥΝΟΛΟΥ μοντελο {(y.tot - y.mtot_).abs().mean():.3f} vs αγορα {(y.tot - y.ktot).abs().mean():.3f} · '
          f'ΔΙΑΦΟΡΑΣ μοντελο {(y.gd - y.mgd).abs().mean():.3f} vs αγορα {(y.gd - y.kgd).abs().mean():.3f}')
# picks με κανονες UCL (φαβ ≥10% σωστα τεταρτα · dog 4-10% p_cover · over ≥4% · under ≥10%), πρωτη εμφανιση ≤72ω, 1.70-2.10, μεσος Crown/SBOBET
HS = (72, 60, 48, 36, 24, 18, 12, 8, 6, 4, 2, 1, 0)
def first_pick(i, bk):
    out = []
    D = sdist(max(LH_N[i], .05), max(LA_N[i], .05))
    got = set()
    for h in HS:
        s = snap_ah(MIDS[i], bk, h)
        if s:
            L, oh, oa = s
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10) or ('ah', side) in got: continue
                if ln <= -0.5: pw, pp = cover_q(D, side, ln); ok = edge(pw, pp, o) >= .10; kind = 'φαβορι'
                elif ln >= 0.5: pw, pp = picks.p_cover(D, side, ln); e = edge(pw, pp, o); ok = .04 <= e < .10; kind = 'αουτσαιντερ'
                else: continue
                if ok: got.add(('ah', side)); out.append((kind, picks.settle(GD[i], side, ln, o)))
        so = snap_ou(MIDS[i], bk, h)
        if so and ('ou',) not in got:
            L, o, un = so; td = ES.tot_dist(OH[i], OA[i], DRAW_SCALE); po, pu = ES.p_over(td, L)
            for over, oo, p, thr in ((True, o, po, .04), (False, un, pu, .10)):
                if 1.70 <= oo <= 2.10 and p * (oo - 1) * (1 - picks.MARGIN) - (1 - p - (1 - po - pu)) >= thr:
                    got.add(('ou',)); out.append(('over' if over else 'under', settle(GH[i] + GA[i], L, oo, over))); break
    return out
PR = []
for i in G.i:
    for bk in ('Crown', 'SBOBET'):
        for kind, pnl in first_pick(i, bk): PR.append(dict(i=i, bk=bk, kind=kind, pnl=pnl, comp=CN[COMP[i]], sea=SEA[i]))
PR = pd.DataFrame(PR)
print('   PICKS στα Γ με κανονες UCL (μεσος Crown/SBOBET):')
for k in ('φαβορι', 'αουτσαιντερ', 'over', 'under'):
    x = PR[PR.kind == k]
    if len(x) == 0: print(f'      {k:12s} —'); continue
    n = x.groupby('bk').size().mean(); r = x.groupby('bk').pnl.mean().mean()
    print(f'      {k:12s} {n:4.0f} picks {100 * r:+6.1f}% · μοναδες {r * n:+5.1f} · ανα σεζον ' + ' '.join(f'{s[2:]}:{100 * v:+.0f}' for s, v in x.groupby('sea').pnl.mean().items()))
# ===== 4 =====
print(NL + '4. ΟΙ 4 ΦΕΤΙΝΕΣ ΟΜΑΔΕΣ UCL ΧΩΡΙΣ FotMob — ευρωπαικα 4 σεζον (ολες οι διοργανωσεις)')
for nm in ('Sabah', 'Shakhtar', 'Slavia', 'Slovan'):
    x = S[S.team.str.contains(nm)]
    if len(x) == 0: print(f'   {nm}: κανενα ματς στο αρχειο'); continue
    o = opp(x)
    print(f'   {x.team.iloc[0]} ({x.src.iloc[0]}): {len(x)} ματς ({", ".join(f"{c} {n}" for c, n in x.comp.value_counts().items())})')
    print(f'      ΒΑΖΕΙ {x.g.mean():.2f} vs μοντελο {x.lam.mean():.2f} ({(x.g - x.lam).mean():+.2f}) xG {x.xg.mean():.2f} αγορα {x.k.mean():.2f} · '
          f'ΤΡΩΕΙ {o.g.mean():.2f} vs μοντελο {o.lam.mean():.2f} ({(o.g - o.lam).mean():+.2f}) xG {o.xg.mean():.2f} αγορα {o.k.mean():.2f}')
