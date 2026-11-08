# -*- coding: utf-8 -*-
"""xi_formula_case.py — 21/10/2026 (Στελιος: «με τη φορμουλα που κατεληξες δειξε μου την επιρροη στα ματς της Λιβερπουλ και της Σιτι»).
ΦΟΡΜΟΥΛΑ (xi_variants_eval, LOSO 4/4): Δ ομαδας = 0.24 · Δ[μεσος ln(αξιας) των 11] + 0.31 · Δ[εμπιστοσυνη προπονητη]
  εμπιστοσυνη παικτη = στα 10 τελευταια ματς της ομαδας οπου ηταν στην αποστολη, μεριδιο λεπτων (λεπτα / 90)
  Δ = ενδεκαδα σημερα − φθινων (0.9) μεσος των προηγουμενων ενδεκαδων της ομαδας · αλλαγη υπεροχης = Δ γηπ − Δ φιλ (γκολ).
Πηγη: FotMob (ολα τα φετινα ματς της ομαδας, ολες οι διοργανωσεις) · αξια = marketValue του FotMob στην ενδεκαδα.
ΣΗΜ.: οι συντελεστες βγηκαν απο τα εγχωρια CORE7· στην Ευρωπη ισχυουν προσεγγιστικα. Η φορμουλα αλλαζει ΜΟΝΟ τη διαφορα, οχι το συνολο γκολ."""
import sys, json, math, time, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
import intl_fetch
from core7_lineups_fetch_lib import minutes_map
TEAMS = {8650: 'Λιβερπουλ', 8456: 'Μαντσεστερ Σιτι', 10205: 'Βιγιαρεαλ', 8563: 'ΑΕΚ'}
CASES = [('6106248', 8650, 10205), ('6106257', 8456, 8563)]
W_V, W_T = 0.24, 0.31


def J(u):
    return json.loads(intl_fetch.get(u))


def team_matches(tid):
    d = J(f'https://www.fotmob.com/api/data/teams?id={tid}')
    fx = ((d.get('fixtures') or {}).get('allFixtures') or {}).get('fixtures') or []
    out = []
    for f in fx:
        st = f.get('status') or {}
        if st.get('finished') and not st.get('cancelled'):
            out.append((st.get('utcTime') or f.get('utcTime'), str(f.get('id')), (f.get('tournament') or {}).get('name')))
    return sorted(out)


CACHE = {}
NAMES = {}
VALS = {}
LEAGUES = ('Premier League', 'LaLiga', 'Super League', 'Serie A', 'Bundesliga', 'Ligue 1')   # 21/10: η «συνηθισμενη» 11αδα & η εμπιστοσυνη ΜΟΝΟ απο ματς πρωταθληματος (οπως στο τεστ) — οχι φιλικα/κυπελλα
def lineup(mid):
    if mid in CACHE: return CACHE[mid]
    d = J(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'); mins = minutes_map(d)
    lu = (d.get('content') or {}).get('lineup') or {}; out = {}
    for side in ('homeTeam', 'awayTeam'):
        t = lu.get(side) or {}
        st = [(p['id'], p.get('name'), p.get('marketValue')) for p in (t.get('starters') or []) if p.get('id')]
        sb = [(p['id'], p.get('name'), p.get('marketValue')) for p in (t.get('subs') or []) if p.get('id')]
        out[t.get('id')] = dict(st=st, squad={p[0]: mins.get(p[0], 0) for p in st + sb}, val={p[0]: p[2] for p in st + sb}, name={p[0]: p[1] for p in st + sb})
    gen = d.get('general') or {}
    for v in out.values(): NAMES.update(v['name']); VALS.update({k: x for k, x in v['val'].items() if x})
    teams = (d.get('header') or {}).get('teams') or []
    sc = f"{teams[0].get('score')}-{teams[1].get('score')}" if len(teams) > 1 else ''
    CACHE[mid] = (out, gen.get('homeTeam', {}).get('name'), gen.get('awayTeam', {}).get('name'), sc)
    time.sleep(0.25)
    return CACHE[mid]


def team_series(tid):
    """για καθε φετινο ματς της ομαδας: Δαξια, Δεμπιστοσυνη, Δ ομαδας (με ΜΟΝΟ τα προηγουμενα ματς)."""
    rows, hist, base_v, base_t = [], [], None, None
    for utc, mid, comp in team_matches(tid):
        if comp == 'Club Friendlies': continue
        lu, hn, an, sc = lineup(mid)
        me = lu.get(tid)
        if not me or len(me['st']) < 11: continue
        last = hist[-10:]
        def trust(p):
            ins = [h[p] for h in last if p in h]
            return sum(ins) / (90.0 * len(ins)) if ins else 0.3
        vals = [v for _, _, v in me['st'] if v]
        V = sum(math.log(v) for v in vals) / len(vals) if vals else None
        T = sum(trust(p) for p, _, _ in me['st']) / len(me['st'])
        # 21/10: βαση = η ΣΥΝΗΘΙΣΜΕΝΗ 11αδα (11 με τα περισσοτερα λεπτα στα 10 τελευταια ματς πρωταθληματος) με τους ιδιους τυπους
        dV = dT = None
        if len(last) >= 3:
            usual = sorted({p for h in last for p in h}, key=lambda p: -sum(h.get(p, 0) for h in last))[:11]
            uv = [VALS.get(p) for p in usual if VALS.get(p)]
            if uv and V is not None: dV = V - sum(math.log(v) for v in uv) / len(uv)
            dT = T - sum(trust(p) for p in usual) / len(usual)
        out_xi = []
        if len(last) >= 3:
            usual = sorted({p for h in last for p in h}, key=lambda p: -sum(h.get(p, 0) for h in last))[:11]
            out_xi = [me['name'].get(p) or NAMES.get(p) or str(p) for p in usual if p not in {q for q, _, _ in me['st']}]
        rows.append(dict(utc=utc, mid=mid, comp=comp, sc=sc, hn=hn, an=an,
                         V=V, T=T, dV=dV, dT=dT, d=(W_V * dV + W_T * dT) if (dV is not None and dT is not None) else None,
                         n_new=sum(1 for p, _, _ in me['st'] if trust(p) < 0.5), out=out_xi))
        if any(str(comp).startswith(L) for L in LEAGUES):          # μονο ματς πρωταθληματος χτιζουν τη «συνηθισμενη»
            hist.append(me['squad'])
            if V is not None: base_v = V if base_v is None else 0.9 * base_v + 0.1 * V
            base_t = T if base_t is None else 0.9 * base_t + 0.1 * T
    return rows


S = {tid: team_series(tid) for tid in TEAMS}
for tid in (8650, 8456):
    print(f'\n{"=" * 120}\n{TEAMS[tid]} — φετινα ματς (ολες οι διοργανωσεις): Δ ενδεκαδας με τη φορμουλα (γκολ υπεροχης· − = πιο αδυναμη απο τη συνηθισμενη)')
    print(f'   {"ημερ.":10s} {"διοργ.":18s} {"ματς":44s} │ {"Δαξια":>6s} {"Δεμπ.":>6s} │ {"Δ ομαδας":>8s} │ βασικοι με χαμηλη εμπιστ. │ εκτος συνηθισμενης 11αδας')
    for r in S[tid]:
        dd = f"{r['d']:+8.2f}" if r['d'] is not None else f'{"—":>8s}'
        print(f"   {r['utc'][:10]:10s} {str(r['comp'])[:18]:18s} {(r['hn'] + ' - ' + r['an'] + ' ' + r['sc'])[:44]:44s} │ "
              + (f"{r['dV']:+6.2f}" if r['dV'] is not None else f'{"—":>6s}') + ' ' + (f"{r['dT']:+6.2f}" if r['dT'] is not None else f'{"—":>6s}')
              + f" │ {dd} │ {r['n_new']:^24d} │ {', '.join(r['out'][:6])}")
print(f'\n{"=" * 120}\nΤΑ ΧΘΕΣΙΝΑ ΜΑΤΣ (Champions League 20/10) — αλλαγη υπεροχης και τι θα σημαινε στις τιμες')
P = {str(m['mid']): m for m in json.load(open('euro_projections.json', encoding='utf-8'))['matches']}
H = {}
for l in open('euro_odds_hist.jsonl', encoding='utf-8'):
    r = json.loads(l); H.setdefault(str(r.get('mid')), []).append(r)
import picks, euro_shadow_scan as ES
def ed(pw, pp, o): return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)
for mid, h, a in CASES:
    rh = next((r for r in S[h] if r['mid'] == mid), None); ra = next((r for r in S[a] if r['mid'] == mid), None)
    m = P.get(mid, {}); xh, xa = m.get('xgh'), m.get('xga')
    dh = rh['d'] if rh and rh['d'] is not None else 0.0; da = ra['d'] if ra and ra['d'] is not None else 0.0
    shift = dh - da
    ko = m.get('utc', '')[:16]
    hist = [r for r in H.get(mid, []) if str(r.get('t', ''))[:16] <= ko.replace('Z', '')]
    c = hist[-1] if hist else {}
    print(f"\n   {TEAMS[h]} - {TEAMS[a]} · σκορ {m.get('score')} · Δ {TEAMS[h]} {dh:+.2f} · Δ {TEAMS[a]} {da:+.2f} → αλλαγη υπεροχης {shift:+.2f} γκολ")
    if xh is None or not c: continue
    L, oh, oa = c.get('line'), c.get('oh'), c.get('oa')
    for lab, sh in (('χωρις ενδεκαδα (μοντελο)', 0.0), ('με τη φορμουλα', shift)):
        hh, aa = xh + sh / 2, xa - sh / 2; d = ES.eu_dist(hh, aa, .85)
        side = 1 if L <= 0 else -1; ln = L if side == 1 else -L; o = oh if side == 1 else oa
        pw, pp = ES.cover_q(d, side, ln) if ln <= -0.5 else picks.p_cover(d, side, ln)
        pw2, pp2 = picks.p_cover(d, -side, -ln) if ln <= -0.5 else ES.cover_q(d, -side, -ln)
        o2 = oa if side == 1 else oh
        print(f"      {lab:26s} xG {hh:.2f}-{aa:.2f} (υπεροχη {hh - aa:+.2f}) │ κλεισιμο Pinnacle {L:+} → φαβ {o} edge {100 * ed(pw, pp, o):+.1f}% · αουτσ. {o2} edge {100 * ed(pw2, pp2, o2):+.1f}%")
