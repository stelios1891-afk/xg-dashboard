"""ucl_early_honest.py — 16/10/2026 (Στελιος: «υπαρχει λογος να μην παιξουμε απο τωρα τα picks του Champions; σημερα Παρασκευη, τα ματς Τριτη-Τεταρτη»).
Το παλιο τεστ χρονισμου (euro_fix_threshold_timing) εβαζε την τιμη 168ω/πρωτη τιμη με μοντελο που ΗΞΕΡΕ ηδη τα εγχωρια ματς του Σαββατοκυριακου
(δυναμη ομαδων τη στιγμη της σεντρας). ΤΙΜΙΟΣ ΧΡΟΝΟΣ: δυναμη ομαδων οπως ηταν 4 (ή 7) μερες πριν (euro_variant_build SHIFT=4/7).
Champions League, κατηγορια Α, κανονες live: φαβορι ≥10% (σωστα τεταρτα, ≤−0.5) · αουτσαιντερ ≥4% (p_cover, ≥+0.5) · DNB ≥4% (γραμμη 0),
1.70-2.10, τιμη ΑΚΡΙΒΩΣ στο σημειο χρονου (Crown & SBOBET, μεσος). Σημεια: 168ω (μοντελο −7 μερες) · 120ω & 96ω (−4 μερες) · 72ω/48ω/24ω (κανονικο).
Συγκριση ιδιου σημειου με «μοντελο που ξερει» (σημερινο τεστ) vs «τιμιο». + κινηση αγορας ως το κλεισιμο (CLV σε γκολ υπεροχης).
"""
import sys, pickle
_s = open('uel_all_mechanisms.py', encoding='utf-8').read()
exec(_s[:_s.index("x = A[A.comp == 'EuropaLeague']")])
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
NL = chr(10)
x = A[A.comp == 'ChampionsLeague'].reset_index(drop=True); seas = sorted(x.sea.unique())
mids = [str(MIDS[int(i)]) for i in x.i]
LH, LA = x.lh.values, x.la.values
def ratio(dump, base):
    db = pickle.load(open(f'euro_blend_dump_{base}.pkl', 'rb')); dv = pickle.load(open(f'euro_blend_dump_{dump}.pkl', 'rb'))
    ib = {str(m): k for k, m in enumerate(db['MIDS'])}; iv = {str(m): k for k, m in enumerate(dv['MIDS'])}
    rh = np.array([dv['LH'][iv[m]] / db['LH'][ib[m]] if m in iv and m in ib and db['LH'][ib[m]] > 0 else 1.0 for m in mids])
    ra = np.array([dv['LA'][iv[m]] / db['LA'][ib[m]] if m in iv and m in ib and db['LA'][ib[m]] > 0 else 1.0 for m in mids])
    return LH * rh, LA * ra
H4 = ratio('sh4', 'base06'); H7 = ratio('sh7', 'base06')
print(f'αλλαγη μοντελου «τιμιο −4 μερες» vs «ξερει»: μεση |Δ υπεροχης| {np.mean(np.abs((H4[0] - H4[1]) - (LH - LA))):.3f} γκολ · −7 μερες {np.mean(np.abs((H7[0] - H7[1]) - (LH - LA))):.3f}')
CL = {}
for k_, m in enumerate(mids):
    for bk in ('Crown', 'SBOBET'): CL[(k_, bk)] = snapT(m, bk, 0)
def run(lh, la, h):
    out = []
    for k_ in range(len(x)):
        if x.cat[k_] != 'A': continue
        i = int(x.i[k_]); D_ = ES.eu_dist(lh[k_], la[k_], .85)
        for bk in ('Crown', 'SBOBET'):
            s = snapT(mids[k_], bk, h)
            if not s: continue
            L, oh, oa = s; c = CL[(k_, bk)]
            for side, ln, o in ((1, L, oh), (-1, -L, oa)):
                if not (1.70 <= o <= 2.10): continue
                if ln <= -0.5: kind = 'φαβ'; pw, pp = cover_q(D_, side, ln); th = .10
                elif ln >= 0.5: kind = 'dog'; pw, pp = picks.p_cover(D_, side, ln); th = .04
                elif abs(ln) < .01: kind = 'dnb'; pw, pp = cover_q(D_, side, ln); th = .04
                else: continue
                if edge(pw, pp, o) < th: continue
                clv = side * (implied_margin(i, *c) - implied_margin(i, L, oh, oa)) if c else np.nan
                out.append(dict(sea=x.sea[k_], bk=bk, kind=kind, pnl=picks.settle(GD[i], side, ln, o), clv=clv))
    return pd.DataFrame(out, columns=['sea', 'bk', 'kind', 'pnl', 'clv'])
def cellx(y):
    if len(y) == 0: return '—'
    m = y.groupby('bk').pnl.mean(); n = y.groupby('bk').size().mean(); s = y.groupby('sea').pnl.mean()
    return f'{n:4.0f} {100 * m.mean():+6.1f}% {m.mean() * n:+6.1f}μ {int((s > 0).sum())}/{len(s)} · CLV {y.clv.mean():+.3f}'
print(f'{NL}CHAMPIONS LEAGUE κατηγορια Α, 2223-2526 · κελι = picks ανα βιβλιο · ROI · μοναδες · θετικες σεζον · κινηση αγορας ως το κλεισιμο (+ = προς εμας)')
for h, hon, lab in ((168, H7, 'μοντελο −7 μερες'), (120, H4, 'μοντελο −4 μερες'), (96, H4, 'μοντελο −4 μερες'), (72, None, ''), (48, None, ''), (24, None, '')):
    P0 = run(LH, LA, h); P1 = run(*hon, h) if hon is not None else None
    print(f'{NL}── τιμη {h}ω πριν')
    for kind, nm in (('φαβ', 'ΦΑΒΟΡΙ ≥10%'), ('dog', 'ΑΟΥΤΣΑΙΝΤΕΡ ≥4%'), ('dnb', 'DNB ≥4%')):
        line = f'   {nm:16s} μοντελο που ΞΕΡΕΙ: {cellx(P0[P0.kind == kind]):48s}'
        if hon is not None:
            line += f' │ ΤΙΜΙΟ ({lab}): {cellx(P1[P1.kind == kind])}'
        print(line)
    if hon is not None:
        a, b = P0, P1
        print(f'   ΟΛΑ             μοντελο που ΞΕΡΕΙ: {cellx(a):48s} │ ΤΙΜΙΟ: {cellx(b)}')
        print(f'      ανα σεζον (μοναδες, μεσος βιβλιων) ξερει: ' + ' '.join(f'{s}: {a[a.sea == s].groupby("bk").pnl.sum().mean():+5.1f}' for s in seas) +
              ' │ τιμιο: ' + ' '.join(f'{s}: {b[b.sea == s].groupby("bk").pnl.sum().mean():+5.1f}' for s in seas))
    else:
        print(f'   ΟΛΑ             {cellx(P0)}')
