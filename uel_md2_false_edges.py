"""uel_md2_false_edges.py — 14/10/2026 (Στελιος: «παραδειγματα απο την αγωνιστικη του europa που ερχεται — με την τωρινη μηχανη ποια ειναι τα
πιθανα λαθη σε καθε αγωνα και βγαζουμε ψευτικα edges»). Europa League 2η αγωνιστικη (15/10). ΔΙΑΓΝΩΣΤΙΚΟ — τιποτα live.
Για καθε ματς η διαφορα γκολ της live μηχανης σπαει σε κομματια (απο euro_projections.json, hf & γ του αρχειου):
  ΕΔΡΑ (×hf/÷hf) · ΔΙΑΦΟΡΑ ΛΙΓΚΑΣ (ρ·D) · γ (ξεφουσκωμα λιγκας) · ΔΥΝΑΜΗ ΟΜΑΔΑΣ (ο,τι μενει: t_γηπ − t_φιλ)
ΔΙΟΡΘΩΜΕΝΗ (μονο για συγκριση) = live λ × exp(−0.54·Δt/2 − 0.32·D) (γηπ) και αντιστροφα (φιλ): οι συντελεστες «ποσο φουσκωμενο» που μετρησαμε
στο Europa κατηγορια Α με στοχο xG (euro_stretch_home_source: δυναμη ομαδας −0.54, διαφορα λιγκας −0.32, εδρα σωστη). Για Β/Γ το τεντωμα ειναι
ακομα μεγαλυτερο (Ben/γκολ+Elo ~ −0.8) — εδω εφαρμοζεται το ιδιο (συντηρητικα).
ΑΓΟΡΑ = τελευταια τιμη Pinnacle (euro_odds_hist) → διαφορα που δικαιολογει. Edge στη γραμμη της αγορας (φαβ σωστα τεταρτα, dog p_cover).
"""
import sys, json, math
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
import picks
import euro_shadow_scan as ES
sys.stdout.reconfigure(encoding='utf-8')
P = json.load(open('euro_projections.json', encoding='utf-8')); P80 = json.load(open('euro_projections_uel80.json', encoding='utf-8'))
HF, G = P['hfa'], P['lg_deflate']; DS = P['eu_draw_scale']
M80 = {m['mid']: m for m in P80['matches']}
ODDS = {}
for line in open('euro_odds_hist.jsonl', encoding='utf-8'):
    r = json.loads(line); ODDS[r['mid']] = r
BT, BD = -0.54, -0.32
def implied(T, L, oh, oa):
    q = (1 / oh) / (1 / oh + 1 / oa); lo, hi = -5.0, 5.0
    for _ in range(30):
        M = (lo + hi) / 2; pw, pp = ES.cover_q(ES.eu_dist(max((T + M) / 2, .05), max((T - M) / 2, .05), DS), 1, L)
        if pw / max(1 - pp, 1e-9) < q: lo = M
        else: hi = M
    return (lo + hi) / 2
def edges(xh, xa, L, oh, oa):
    D_ = ES.eu_dist(xh, xa, DS); out = {}
    for side, ln, o in ((1, L, oh), (-1, -L, oa)):
        pw, pp = ES.cover_q(D_, side, ln) if ln <= 0 else picks.p_cover(D_, side, ln)
        out[side] = ES.edge_of(pw, pp, o)
    return out
CAT = lambda m: 'Α' if m['src_h'] == 'FotMob' and m['src_a'] == 'FotMob' else ('Β' if 'FotMob' in (m['src_h'], m['src_a']) else 'Γ')
ms = sorted([m for m in P['matches'] if m['comp'] == 'EuropaLeague' and str(m['round']) == '2' and not m.get('finished')], key=lambda m: m['utc'])
rows = []
for m in ms:
    xh, xa, x0h, x0a = m['xgh'], m['xga'], m['xgh0'], m['xga0']
    c = 2 * (x0h * HF - xh); D = c / G if G else 0.0
    dt = math.log(x0h / x0a) - 2 * D
    home_part = (x0h * HF - x0a / HF) - (x0h - x0a)
    base_noD = x0h * math.exp(-D) - x0a * math.exp(D)
    lg_part = (x0h - x0a) - base_noD
    g_part = -c
    team_part = base_noD
    ch = xh * math.exp(BT * dt / 2 + BD * D); ca = xa * math.exp(-BT * dt / 2 - BD * D)
    o = ODDS.get(m['mid'])
    r = dict(m=m, cat=CAT(m), M=xh - xa, home=home_part, lg=lg_part, gam=g_part, team=team_part, CM=ch - ca)
    if o and o.get('line') is not None:
        L, oh, oa = o['line'], o['oh'], o['oa']
        r.update(L=L, oh=oh, oa=oa, mk=implied(xh + xa, L, oh, oa), e=edges(xh, xa, L, oh, oa), ce=edges(ch, ca, L, oh, oa), t=o['t'])
        m8 = M80.get(m['mid'])
        if m8: r['e80'] = edges(m8['xgh'], m8['xga'], L, oh, oa)
    rows.append(r)
print(f'EUROPA LEAGUE 2η αγωνιστικη (15/10) — live μηχανη (hf {HF:.3f}, γ {G}) · διαφορα γκολ ΑΠΟ ΤΗ ΣΚΟΠΙΑ ΤΟΥ ΓΗΠΕΔΟΥΧΟΥ')
print(f'{"ματς":42s} κατ  ΜΟΝΤΕΛΟ = εδρα + λιγκα + γ + ομαδα │ ΔΙΟΡΘ. │ ΑΓΟΡΑ (γραμμη)  │ edge μοντελου (γηπ/φιλ) → διορθωμενο')
for r in rows:
    m = r['m']; nm = f"{m['home'][:19]}-{m['away'][:19]}"
    s = f"{nm:42s} {r['cat']}   {r['M']:+.2f} = {r['home']:+.2f} {r['lg']:+.2f} {r['gam']:+.2f} {r['team']:+.2f} │ {r['CM']:+.2f} │"
    if 'mk' in r:
        s += f" {r['mk']:+.2f} ({r['L']:+.2f}) │ {100 * r['e'][1]:+5.1f}/{100 * r['e'][-1]:+5.1f} → {100 * r['ce'][1]:+5.1f}/{100 * r['ce'][-1]:+5.1f}"
    print(s)
json.dump([{k: (v if k != 'm' else {kk: v[kk] for kk in ('mid', 'home', 'away', 'utc', 'src_h', 'src_a', 'lg_h', 'lg_a')}) for k, v in r.items()} for r in rows],
          open('uel_md2_false_edges.json', 'w', encoding='utf-8'), ensure_ascii=False, default=float, indent=1)
