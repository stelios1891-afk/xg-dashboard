# -*- coding: utf-8 -*-
"""core7_anchor_md1_diag.py — 19/10/2026 (Στελιος: «η αγκυρα σαν εργαλειο βοηθαει, αλλα χαλαει την προβλεψη οταν εχει ΠΕΡΙΣΣΟΤΕΡΗ
πληροφορια, δηλ. αρχιζοντας απο την 1η αγωνιστικη — γιατι;»).
ΥΠΟΘΕΣΗ «ΔΙΠΛΗΣ ΔΙΟΡΘΩΣΗΣ»: στις αγωνιστικες 1-6 το μοντελο ειναι κυριως το περσινο prior (μιξη K=8)· η αγκυρα μαθαινει τη διαφορα του
απο την αγορα. Μετα, καθως μπαινουν τα φετινα xG, το ιδιο το μοντελο διορθωνεται — αλλα η αγκυρα κραταει ακομα την παλια διορθωση → την
μετραμε δυο φορες (υπερ-διορθωση) στις 7-14. Αν ισχυει: (α) το ωμο μοντελο πλησιαζει μονο του την αγορα απο 1-6 σε 7-14, (β) η αγκυρα-απο-1η
βγαινει ΑΠΟ ΤΗΝ ΑΛΛΗ ΜΕΡΙΑ στις 7-14 (ξεπερνα την αγορα/πραγματικα), (γ) αγκυρα-απο-1η με «ξεχασμα» (παλια διορθωση σβηνει) το διορθωνει.
ΜΕΤΡΑ ανα παραθυρο (1-6 / 7-14 / 15+): μεροληψια μοντελου − πραγματικα γκολ, μοντελο − αγορα (κλεισιμο Crown), MAE, log-πιθανοφανεια συνολου.
ΕΚΔΟΧΕΣ: ωμο · απο 7η (σημερινη) · απο 1η · απο 1η με ξεχασμα 0.9 / 0.8 ανα ματς της ομαδας · απο 1η μισο βημα (λ .25).
Μονο ακριβεια — τα picks (τιμιος χρονος) ειναι ηδη στο core7_totals_anchor_md1_out (Γ1/Γ2)."""
import sys, os
_s = open('core7_totals_anchor_md1_test.py', encoding='utf-8').read()
_TO = sys.stdout; sys.stdout = open(os.devnull, 'w', encoding='utf-8'); exec(_s[:_s.index('rows = []; prestale = []')]); sys.stdout = _TO
sys.stdout.reconfigure(encoding='utf-8')
TGA = {}
for f in glob.glob('data_*_*.json'):
    try: d = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    if not isinstance(d, dict): continue
    for k, v in d.items():
        try: TGA[str(k)] = int(v['hs']) + int(v['as'])
        except Exception: pass
P['tg'] = P.mid.map(TGA)
def anch(start_md, lam=0.5, decay=1.0):
    out = np.zeros(len(P)); off = {}; cur = None
    for i, r in enumerate(P.itertuples()):
        k = (r.league, r.season)
        if k != cur: off = {}; cur = k
        t = r.xg_h + r.xg_a + off.get(r.home, 0) + off.get(r.away, 0); out[i] = t
        if r.md >= start_md and r.T_mkt == r.T_mkt:
            e = r.T_mkt - t
            for tm in (r.home, r.away):
                off[tm] = off.get(tm, 0) * decay + lam * e / 2
    return out
def loglik(T, s, tg):
    d = tdist((T + s) / 2, (T - s) / 2); return np.log(max(d[int(tg)], 1e-9))
V = [('ωμο μοντελο', P.xg_h.values + P.xg_a.values), ('απο 7η (σημερα)', anch(6)), ('απο 1η', anch(0)),
     ('απο 1η, ξεχασμα 0.9', anch(0, decay=0.9)), ('απο 1η, ξεχασμα 0.8', anch(0, decay=0.8)), ('απο 1η, μισο βημα λ.25', anch(0, lam=0.25))]
W = [('1-6', P.md < 6), ('7-14', (P.md >= 6) & (P.md < 14)), ('15+', P.md >= 14)]
ok = P.tg.notna() & P.T_mkt.notna()
S = (P.xg_h - P.xg_a).values
print('ΑΚΡΙΒΕΙΑ ΣΥΝΟΛΟΥ ΓΚΟΛ — CORE7 2223-2526 · ανα παραθυρο: μοντελο−πραγματικα · μοντελο−αγορα · MAE · log-πιθ. (ψηλοτερο = καλυτερο, ×1000 vs ωμο)')
base_ll = {}
for nm, T in V:
    parts = []
    for wl, wm in W:
        m = (ok & wm).values
        bias = np.mean(T[m] - P.tg.values[m]); gap = np.mean(T[m] - P.T_mkt.values[m]); mae = np.mean(np.abs(T[m] - P.tg.values[m]))
        ll = np.mean([loglik(T[i], S[i], P.tg.values[i]) for i in np.where(m)[0]])
        if nm == 'ωμο μοντελο': base_ll[wl] = ll
        parts.append(f'{wl}: {bias:+.2f} {gap:+.2f} {mae:.3f} {1000 * (ll - base_ll[wl]):+5.1f}')
    print(f'   {nm:24s} │ ' + ' │ '.join(parts))
mk = np.array([np.mean(P.T_mkt.values[(ok & wm).values] - P.tg.values[(ok & wm).values]) for _, wm in W])
print(f'   {"αγορα (κλεισιμο Crown)":24s} │ ' + ' │ '.join(f'{wl}: {b:+.2f}' for (wl, _), b in zip(W, mk)) + '   (αγορα − πραγματικα)')
print('\nΑΝΑ ΣΕΖΟΝ (7-14, μοντελο − πραγματικα):')
for nm, T in V[:3]:
    print(f'   {nm:24s} │ ' + ' · '.join(f'{sea}: {np.mean((T - P.tg.values)[(ok & (P.md >= 6) & (P.md < 14) & (P.season == sea)).values]):+.2f}'
                                         for sea in sorted(P.season.unique())))
# (α) διορθωνεται μονο του το ωμο μοντελο; ανα ομαδα: κενο μοντελο−αγορα 1-6 vs 7-14
g = P[ok].copy(); g['gap'] = (g.xg_h + g.xg_a) - g.T_mkt
rows = []
for (lg, sea), q in g.groupby(['league', 'season']):
    teams = set(q.home) | set(q.away)
    for tm in teams:
        qq = q[(q.home == tm) | (q.away == tm)]
        a = qq[qq.md < 6].gap.mean(); b = qq[(qq.md >= 6) & (qq.md < 14)].gap.mean()
        if a == a and b == b: rows.append((a, b))
R_ = np.array(rows)
sl = np.polyfit(R_[:, 0], R_[:, 1], 1)[0]
print(f'\n(α) ΔΙΟΡΘΩΝΕΤΑΙ ΜΟΝΟ ΤΟ ΤΟ ΜΟΝΤΕΛΟ; ανα ομαδα-σεζον (n {len(R_)}): κενο μοντελο−αγορα αγων. 1-6 μεσος {R_[:, 0].mean():+.2f} (|.| {np.abs(R_[:, 0]).mean():.2f}) '
      f'→ 7-14 μεσος {R_[:, 1].mean():+.2f} (|.| {np.abs(R_[:, 1]).mean():.2f}) · ποσο απο το κενο 1-6 μενει στις 7-14 (κλιση): {sl:.2f}')
print('   (κλιση 1 = το κενο μενει ολο → η αγκυρα απο 1η θα ηταν σωστη · κλιση ~0 = το μοντελο το διορθωνει μονο του → η αγκυρα απο 1η το μετρα ΔΥΟ φορες)')
