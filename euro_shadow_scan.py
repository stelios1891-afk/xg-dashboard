# -*- coding: utf-8 -*-
"""euro_shadow_scan.py — Σκιωδης καταγραφη ευρωπαικων picks (League Phase 2627).

Τρεχει στον scanner μετα το euro_odds_scan. Για καθε επερχομενο καλυμμενο ματς με αποδοσεις:
υπολογιζει με το ΣΗΜΕΡΙΝΟ live stack (projections = V4+prior-EU w=2· pricing με EU draw
scale 0.85) τα edges για OUTSIDER και ΦΑΒΟΡΙ, με ΔΥΟ τιμολογησεις:
  e_live  = picks.p_cover ως εχει (το quarter συμψηφιστικο — οπως η εγχωρια live μηχανη)
  e_clean = σωστο quarter-aware split
Append-on-change στο euro_shadow.jsonl (state: euro_shadow_state.json). ΚΑΜΙΑ κριση εδω —
ο φακελος κρινεται στο τελος της League Phase.
"""
import os, json, datetime, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picks

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ_F = os.path.join(ROOT, 'euro_projections.json')
PROJ80_F = os.path.join(ROOT, 'euro_projections_uel80.json')   # 9/10/2026: UEL μηχανη 80% xG (euro_live_projections με EURO_BLEND=0.8)
UEL_HF_EDGE = 0.04          # 9/10/2026 (Στελιος «βαλτο κανονικα»): UEL ΦΑΒΟΡΙ ΕΝΤΟΣ = ΚΑΝΟΝΙΚΑ picks (μικρο stake)
UEL_HF_WIN = (12.0, 36.0)   # εισοδος ~24ω πριν (backtest 24ω: 49 picks +24.2%, 4/4 σεζον, Crown +32 / SBOBET +19)
ODDS_F = os.path.join(ROOT, 'euro_odds_latest.json')
OUT_F = os.path.join(ROOT, 'euro_shadow.jsonl')
ST_F = os.path.join(ROOT, 'euro_shadow_state.json')


def eu_dist(xgh, xga, scale):
    dist = picks.gd_dist(max(xgh, 0.05), max(xga, 0.05))
    px = dist.get(0, 0.0)
    if px <= 0 or px >= 1 or scale == 1.0:
        return dist
    k = (1.0 - scale * px) / (1.0 - px)
    return {g: (p * scale if g == 0 else p * k) for g, p in dist.items()}


def cover_q(dist, side, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pw = pp = 0.0
    for L in parts:
        for k, p in dist.items():
            m = (k if side == 1 else -k) + L
            if m > 0.01:
                pw += p / len(parts)
            elif abs(m) <= 0.01:
                pp += p / len(parts)
    return pw, pp


def edge_of(pw, pp, o):
    return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)


PICK_HORIZON_H = 200      # 10/10/2026: picks & σκια ΜΟΝΟ για ματς ως 200ω μπροστα (οπως πριν)· οι τιμες καταγραφονται πλεον ως 30 μερες
                          # (euro_odds_scan PIN_HOURS_AHEAD) μονο για το Market Watch.


def tot_dist(lh, la, scale=1.0):
    """Κατανομη συνολου γκολ. 10/10 (Στελιος «περνα το»): ΙΔΙΟ βαρος ισοπαλιων με το χαντικαπ —
    ×DRAW_BOOST στη διαγωνιο, μετα συνολικη μαζα ισοπαλιας ×scale (eu_draw_scale), τα υπολοιπα αναλογικα."""
    import math
    F = [math.factorial(i) for i in range(13)]
    ph = [math.exp(-max(lh, .05)) * max(lh, .05) ** i / F[i] for i in range(13)]
    pa = [math.exp(-max(la, .05)) * max(la, .05) ** j / F[j] for j in range(13)]
    M = {}; s = 0.0
    for i in range(13):
        for j in range(13):
            p = ph[i] * pa[j] * (picks.DRAW_BOOST if i == j else 1.0)
            M[(i, j)] = p; s += p
    D = sum(M[(i, i)] for i in range(13)) / s
    k = (1.0 - scale * D) / (1.0 - D) if 0 < D < 1 else 1.0
    tot = {}
    for (i, j), p in M.items():
        tot[i + j] = tot.get(i + j, 0.0) + p / s * (scale if i == j else k)
    return tot


def p_over(tot, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    po = pu = 0.0
    for L in parts:
        for t, p in tot.items():
            if t > L + 0.01:
                po += p / len(parts)
            elif t < L - 0.01:
                pu += p / len(parts)
    return po, pu


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        P = json.load(open(PROJ_F, encoding='utf-8'))
        O = json.load(open(ODDS_F, encoding='utf-8')).get('odds', {})
    except Exception as e:
        print(f'λειπουν αρχεια ({e}) — τιποτα')
        return
    scale = float(P.get('eu_draw_scale', 1.0))
    try:
        st = json.load(open(ST_F, encoding='utf-8'))
    except Exception:
        st = {}
    n_new = 0
    with open(OUT_F, 'a', encoding='utf-8') as out:
        for m in P.get('matches', []):
            if not m.get('covered') or m.get('finished'):
                continue
            mk = O.get(str(m['mid']))
            if not mk or mk.get('line') is None:
                continue
            try:
                ko = datetime.datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00'))
            except Exception:
                continue
            if ko < now or (ko - now).total_seconds() > PICK_HORIZON_H * 3600:
                continue
            lf, oh, oa = float(mk['line']), mk.get('oh'), mk.get('oa')
            if not oh or not oa:
                continue
            dist = eu_dist(m['xgh'], m['xga'], scale)
            rec = dict(t=now.isoformat()[:16], ko=m['utc'], mid=str(m['mid']),
                       comp=m['comp'], rnd=m.get('round'),
                       home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                       src_h=m.get('src_h'), src_a=m.get('src_a'),
                       xgh=m['xgh'], xga=m['xga'], line=lf, oh=oh, oa=oa,
                       tl=mk.get('tl'), to=mk.get('to'), tu=mk.get('tu'))
            for side, ln, o, tag in ((1, lf, oh, 'h'), (-1, -lf, oa, 'a')):
                pw, pp = picks.p_cover(dist, side, ln)
                rec[f'e_live_{tag}'] = round(edge_of(pw, pp, o), 4)
                pw2, pp2 = cover_q(dist, side, ln)
                rec[f'e_clean_{tag}'] = round(edge_of(pw2, pp2, o), 4)
            rec['dside'] = 1 if lf > 0 else (-1 if lf < 0 else (1 if oh > oa else -1))
            # σκια OVERS (συνθεση W2 πεναλτι-0.76, καθαρο quarter pricing) — γραμμη σκιας 10/9
            if mk.get('tl') is not None and m.get('xgh_ou') is not None:
                td = tot_dist(m['xgh_ou'], m['xga_ou'], scale)
                po, pu = p_over(td, float(mk['tl']))
                rec['xgh_ou'] = m['xgh_ou']; rec['xga_ou'] = m['xga_ou']
                if mk.get('to'):
                    rec['e_ov_w2'] = round(po * (mk['to'] - 1) * (1 - picks.MARGIN) - pu, 4)
                if mk.get('tu'):
                    rec['e_un_w2'] = round(pu * (mk['tu'] - 1) * (1 - picks.MARGIN) - po, 4)
            sig = f"{lf}|{oh}|{oa}|{rec['xgh']:.2f}|{rec['xga']:.2f}"
            if st.get(rec['mid']) == sig:
                continue
            st[rec['mid']] = sig
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            n_new += 1
    json.dump(st, open(ST_F, 'w', encoding='utf-8'))
    print(f'euro shadow: {n_new} νεες/αλλαγμενες εγγραφες')

    # ---------------- VALUE PICKS (beta) για το dashboard ----------------
    # Μηχανισμος οπως συμφωνηθηκε 10/9/2026 (Στελιος): ΜΟΝΟ ματς FotMob+FotMob,
    # τιμολογηση as-live (P(X)x0.85 · dogs p_cover ως εχει · ΦΑΒΟΡΙ σωστα τεταρτα απο 30/9), ζωνη 1.70-2.10,
    # OUTSIDERS: παιρνει >=0.5 & edge >= 10% · ΦΑΒΟΡΙ: δινει >=0.5 & edge >= 4%
    # (τα κατωφλια αντισταθμιζουν τη γνωστη μεροληψια των δηλωμενων edges ανα πλευρα).
    # Σημανση 🎯 στη γραμμη -0.75 των φαβορι (το τυφλο ευρημα Crown+Pinnacle).
    # UCL ΦΑΒΟΡΙ @10 (11/9/2026, αποφαση Στελιου με το UCL_FAV_SCALE=1.16): τα εξτρα
    # fav edges 4-10% που γενναει η κλιμακα ειναι δημοσια πληροφορια (~0 μειον γκανιοτα,
    # backtest −6.4%±12)· στο @10 τα νεα picks ηταν +1.0% και τα κοινα +29%.
    # UCL DOGS @4 (11/9/2026, ετυμηγορια Fable 5.1 — αποφαση απο ΑΡΧΗ, οχι απο τα 6 ματς):
    # το @10 ηταν αντιβαρο στα φουσκωμενα dog edges· το κ ΕΙΝΑΙ η διορθωση του φουσκωματος
    # (bias @4 +0.28→+0.15 ns, κοινα edges 27→19) => @10 πανω σε ξεφουσκωμενη κλιμακα =
    # διπλη συσφιξη. Η ζωνη 4-10% σημαινεται band='4-10' ως χωριστο ρευμα· ΚΑΝΟΝΑΣ
    # (προ-γραμμενος): επανεξεταση ΜΟΝΟ σε n>=15 με CLV (αρνητικο t<−1.5 => πισω στο @10)·
    # το ROI της ζωνης γραφεται αλλα ΔΕΝ αποφασιζει· προ Ιανουαριου αλλαγη ΜΟΝΟ προς
    # αυστηροτερο. UEL/UECL dogs μενουν @10.
    # UEL = ΣΚΙΑ (18/9/2026, εντολη Στελιου «θελω να βλεπω τα picks του Europa ακομα και αν δεν τα
    # παιζουμε επισημα»): τα UEL picks ΓΡΑΦΟΝΤΑΙ κανονικα (ιδια κατωφλια @10/@4) αλλα φερουν
    # no_play=True + note — δεν παιζονται (b=0.02 στο κλεισιμο, κλειστο 11/9), δειχνονται μονο.
    EDGE_DOG, EDGE_FAV, EDGE_OVER = 0.10, 0.04, 0.04
    # UNDER (10/10/2026, Στελιος «περνα 4% για over και 10% για under»): ΜΟΝΟ Champions League, edge ≥10%
    # (LOSO 4 σεζον: 10% σε 3/4 · εκτος δειγματος +10.3% / 100 picks — ucl_totals_threshold_loso)· ενα pick συνολων ανα ματς (ledger).
    EDGE_UNDER_UCL = 0.10
    # OVER CONFERENCE κατηγορια Α (12/10/2026, Στελιος «παμε στο -2%»): uecl_over_low_threshold — η αγορα ΚΑΙ το μοντελο υποτιμουν
    # τα γκολ στα UECL FotMob+FotMob (xG +0.10/πλευρα, τυφλο over +14.5% 4/4)· ζωνες 4→2→0→−2% ολες ✓ κανονα UCL (θετικες 2 βιβλια,
    # ≥3/4 σεζον, 2 νεας μορφης), −2→−4% ✗ → κατωφλι −2% (106 picks +26.5%, +28.2μ). Ελεγχος ανα αγωνιστικη: uecl_monitor.py.
    EDGE_OVER_UECL = -0.02
    # CONFERENCE ΚΑΤΗΓΟΡΙΑ Β (μια ομαδα χωρις FotMob) — 13/10/2026, Στελιος «βαλε και τα under και τα αουτσαιντερ Β κανονικα»:
    #  ΑΟΥΤΣΑΙΝΤΕΡ = η ομαδα ΧΩΡΙΣ FotMob οταν παιρνει ≥0.5, p_cover, edge ≥10%, ΧΩΡΙΣ διορθωση (uecl_b_dog_test: 63 picks +25.2% 4/4,
    #   Κ1-Κ4 + γειτονικα 5/5, τυφλα +15.4%, αξια xG +8.7%· αιτια = στο UEL/UECL οι αποστασεις κλεινουν, compression_battery). Φαβορι Β ΠΟΤΕ (−23.5%).
    #  UNDER ≥14% (uecl_battery: 42 picks +42.9% 4/5, CLV +0.10 γκολ 65% προς εμας, αξια xG +13.7%· η αγορα πεφτει 12→8ω πριν).
    #  Over Β ΟΧΙ (−1.7%). Ματς Γ (καμια FotMob) εκτος.
    EDGE_DOG_UECL_B = 0.10
    EDGE_UNDER_UECL_B = 0.14
    # UNDER EUROPA κατηγορια Α (16/10/2026, Στελιος «να τα βαλουμε και αυτα σκια»): ΣΚΙΑ μονο (no_play, οχι Telegram, rule uel_under_shadow).
    # uel_totals_mechanisms / uel_late_under_test: under ≥10% ≤72ω 54 picks +20.5% (Crown +18 / SBOBET +23), θετικο 4/4 σεζον·
    # ΑΛΛΑ αξια xG +2.6% (γκολ 2.49 vs xG 3.0) → κυριως φινιρισμα· με φετινα ευρωπαικα 0.5 (live) +15%.
    EDGE_UNDER_UEL = 0.10
    EDGE_DNB_UCL = 0.04            # 10/10/2026: DNB (γραμμη 0) μονο UCL, FotMob και οι 2
    NO_PLAY_NOTE = 'ΣΚΙΑ — δεν παιζεται (UEL κλειστο 11/9: b=0.02 στο κλεισιμο)'
    EDGE_FAV_UCL = 0.10
    LATE2H_UCL = 2.0               # 13/10/2026: UCL χαντικαπ που πρωτοβγαινει <2ω πριν = καταγραφη (rule late2h)
    EDGE_DOG_UCL = 0.04
    # OVERS στα picks (εντολη Στελιου 10/9): συνθεση W2 (πεναλτι 0.76, ζευγος xgh_ou/xga_ou),
    # ΜΟΝΟ FotMob ματς, καθαρο quarter pricing στη γραμμη της αγορας, κατωφλι 4%.
    picks_out = []
    # UEL ΦΑΒΟΡΙ ΕΝΤΟΣ (9/10/2026, uel_homefav_methods/_market): μιξη 80% xG για τα εγχωρια ratings (LOSO 4/4),
    # σωστα τεταρτα, edge ≥4%, γηπεδουχος δινει ≥0.5, 1.70-2.10, FotMob+FotMob, εισοδος 12-36ω πριν (~24ω).
    # ΚΑΝΟΝΙΚΟ pick (no_play=False, rule='uel_home_fav'). Ολα τα αλλα UEL μενουν σκια. Χωρις το αρχειο 80% → τιποτα.
    try:
        L80 = {str(x['mid']): (x['xgh'], x['xga']) for x in json.load(open(PROJ80_F, encoding='utf-8')).get('matches', [])
               if x.get('covered') and x.get('xgh') is not None}
    except Exception:
        L80 = {}
    for m in P.get('matches', []):
        if not m.get('covered') or m.get('finished'):
            continue
        # 10/10/2026: ματς με ομαδα χωρις FotMob (Ben / γκολ+Elo) → ΜΟΝΟ UCL OVER (ucl_totals_sources: +30.8% 4/4·
        # under −22.9% 0/4, UEL/UECL δεν επαναλαμβανεται· διορθωση χασματος ✗ ucl_gap_totals_test). Χαντικαπ/under: μονο FotMob+FotMob.
        fm_both = m.get('src_h') == 'FotMob' and m.get('src_a') == 'FotMob'
        fm_one = (m.get('src_h') == 'FotMob') != (m.get('src_a') == 'FotMob')
        if not fm_both and not (fm_one and m['comp'] in ('ChampionsLeague', 'ConferenceLeague')):   # 13/10: + UECL Β (μονο dogs χωρις FotMob & under)
            continue                     # 10/10: ματς χωρις FotMob ΚΑΙ στις 2 ομαδες (κατηγορια Γ) → εκτος (Στελιος «αστα στην ακρη»)
        mk = O.get(str(m['mid']))
        if not mk or mk.get('line') is None:
            continue
        try:
            ko = datetime.datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00'))
        except Exception:
            continue
        if ko < now or (ko - now).total_seconds() > PICK_HORIZON_H * 3600:     # 10/10: τιμες ως 30 μερες = μονο παρακολουθηση
            continue
        lf = float(mk['line'])
        dist = eu_dist(m['xgh'], m['xga'], scale)
        for side, ln, o, team in (((1, lf, mk.get('oh'), m['home']),
                                   (-1, -lf, mk.get('oa'), m['away'])) if fm_both else ()):
            if not o or not (1.70 <= o <= 2.10):
                continue
            role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else None)
            # 10/10/2026 (Στελιος «περνα μονο τα dnb κανονικα σαν picks»): ΜΟΝΟ UCL, κυρια γραμμη 0 (DNB), edge ≥4%.
            # ucl_other_lines_deep: Κ1-Κ4 ✓ (84 picks +20.2%, LOSO +20.1%, μοντελο 64% / πραγμ 65% / αγορα 50%)·
            # xG (ucl_other_lines_xg): ιδιο ειδος με τα live φαβορι. Τα −0.25 / +0.25 ΟΧΙ (1/4, 2/4).
            if role is None and m['comp'] == 'ChampionsLeague' and abs(ln) < 0.01:
                role = 'dnb'
            if role is None:
                continue
            # 30/9/2026 (Στελιος): ΦΑΒΟΡΙ = ΣΩΣΤΑ τεταρτα (cover_q), ΑΟΥΤΣΑΙΝΤΕΡ = p_cover ως εχει.
            # quarters_all_markets / intl_quarters_compare: και στις 3 αγορες τα φαβορι κερδιζουν με σωστα τεταρτα
            # (Ευρωπη UCL+UECL +11.0% → +18.4%, φευγουν 25 picks −18% 0/4), τα dogs με τον παλιο (+12.0% vs −4.2%).
            pw, pp = cover_q(dist, side, ln) if role in ('fav', 'dnb') else picks.p_cover(dist, side, ln)
            edge = edge_of(pw, pp, o)
            thr_fav = EDGE_FAV_UCL if m['comp'] == 'ChampionsLeague' else EDGE_FAV
            thr_dog = EDGE_DOG_UCL if m['comp'] == 'ChampionsLeague' else EDGE_DOG
            if (role == 'dog' and edge >= thr_dog) or (role == 'fav' and edge >= thr_fav) or (role == 'dnb' and edge >= EDGE_DNB_UCL):
                picks_out.append(dict(
                    mid=str(m['mid']), comp=m['comp'], rnd=m.get('round'), ko=m['utc'],
                    home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                    team=team, side=int(side), line=round(ln, 2), odds=round(float(o), 2),
                    edge=round(edge, 4), role=role,
                    band=('4-10' if (role == 'dog' and m['comp'] == 'ChampionsLeague'
                                     and edge < EDGE_DOG) else None),
                    proj_odds=round((1 - pp) / pw, 3) if pw > 0 else None,
                    tag75=bool(role == 'fav' and abs(ln + 0.75) < 0.01),
                    xgh=m['xgh'], xga=m['xga'], when=mk.get('when'), lim=mk.get('lim'),
                    no_play=(m['comp'] == 'EuropaLeague'),
                    note=(NO_PLAY_NOTE if m['comp'] == 'EuropaLeague' else None)))
        # --- ΣΚΙΑ (10/10/2026, Στελιος «το 3»): κατηγορια Β (UCL, μια ομαδα χωρις FotMob) — χαντικαπ ΥΠΕΡ της ομαδας FotMob («μεγαλη»)
        # οταν ειναι φαβορι (≤−0.5), σωστα τεταρτα, edge ≥10%, 1.70-2.10, ΧΩΡΙΣ διορθωση (ucl_nonfm_fix_test: 27 picks +6.1%, λιγα).
        # ΚΑΤΑΓΡΑΦΗ μονο (no_play): οχι Telegram, δεν μετραει.
        if fm_one and m['comp'] == 'ChampionsLeague':
            big = 1 if m.get('src_h') == 'FotMob' else -1
            ln = lf if big == 1 else -lf
            o = mk.get('oh') if big == 1 else mk.get('oa')
            if o and 1.70 <= float(o) <= 2.10 and ln <= -0.5:
                pw, pp = cover_q(dist, big, ln)
                e_b = edge_of(pw, pp, float(o))
                if e_b >= EDGE_FAV_UCL:
                    picks_out.append(dict(
                        mid=str(m['mid']), comp=m['comp'], rnd=m.get('round'), ko=m['utc'],
                        home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                        team=(m['home'] if big == 1 else m['away']), side=int(big), line=round(ln, 2), odds=round(float(o), 2),
                        edge=round(e_b, 4), role='fav', band=None,
                        proj_odds=round((1 - pp) / pw, 3) if pw > 0 else None,
                        tag75=False, xgh=m['xgh'], xga=m['xga'], when=mk.get('when'), lim=mk.get('lim'),
                        rule='nonfm_fav_shadow', src=f"{m.get('src_h')}/{m.get('src_a')}", no_play=True,
                        note='👁 ΣΚΙΑ — χάντικαπ υπέρ μεγάλης, ομάδα χωρίς FotMob (καταγραφή, δεν παίζεται)'))
        # --- CONFERENCE Β: ΑΟΥΤΣΑΙΝΤΕΡ ΧΩΡΙΣ FotMob (κανονικο pick, 13/10/2026) ---
        if fm_one and m['comp'] == 'ConferenceLeague':
            sm = -1 if m.get('src_h') == 'FotMob' else 1                 # πλευρα της ομαδας ΧΩΡΙΣ FotMob
            ln = lf if sm == 1 else -lf
            o = mk.get('oh') if sm == 1 else mk.get('oa')
            if o and 1.70 <= float(o) <= 2.10 and ln >= 0.5:
                pw, pp = picks.p_cover(dist, sm, ln)
                e_d = edge_of(pw, pp, float(o))
                if e_d >= EDGE_DOG_UECL_B:
                    picks_out.append(dict(
                        mid=str(m['mid']), comp=m['comp'], rnd=m.get('round'), ko=m['utc'],
                        home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                        team=(m['home'] if sm == 1 else m['away']), side=int(sm), line=round(ln, 2), odds=round(float(o), 2),
                        edge=round(e_d, 4), role='dog', band=None,
                        proj_odds=round((1 - pp) / pw, 3) if pw > 0 else None,
                        tag75=False, xgh=m['xgh'], xga=m['xga'], when=mk.get('when'), lim=mk.get('lim'),
                        rule='uecl_b_dog', src=f"{m.get('src_h')}/{m.get('src_a')}", no_play=False,
                        note='Conference Β — αουτσάιντερ χωρίς FotMob'))
        # --- UEL ΦΑΒΟΡΙ ΕΝΤΟΣ (κανονικο pick) ---
        if m['comp'] == 'EuropaLeague' and str(m['mid']) in L80:
            hb = (ko - now).total_seconds() / 3600
            o = mk.get('oh')
            if lf <= -0.5 and o and 1.70 <= float(o) <= 2.10:
                x8h, x8a = L80[str(m['mid'])]
                d8 = eu_dist(x8h, x8a, scale)
                pw, pp = cover_q(d8, 1, lf)
                e8 = edge_of(pw, pp, float(o))
                if e8 >= UEL_HF_EDGE:
                    live = UEL_HF_WIN[0] <= hb <= UEL_HF_WIN[1]
                    picks_out.append(dict(
                        mid=str(m['mid']), comp=m['comp'], rnd=m.get('round'), ko=m['utc'],
                        home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                        team=m['home'], side=1, line=round(lf, 2), odds=round(float(o), 2),
                        edge=round(e8, 4), role='fav', band=None,
                        proj_odds=round((1 - pp) / pw, 3) if pw > 0 else None,
                        tag75=bool(abs(lf + 0.75) < 0.01),
                        xgh=round(x8h, 3), xga=round(x8a, 3), when=mk.get('when'), lim=mk.get('lim'),
                        rule=('uel_home_fav' if live else 'uel_home_fav_wait'),
                        no_play=not live,
                        note=('⭐ UEL φαβορί εντός — κανονικό pick (μικρό stake), είσοδος ~24ω πριν' if live else
                              (f'⏳ UEL φαβορί εντός — γίνεται κανονικό 12-36ω πριν τη σέντρα (τώρα {hb:.0f}ω), αν μείνει edge ≥4%'
                               if hb > UEL_HF_WIN[1] else '⌛ UEL φαβορί εντός — πέρασε το παράθυρο εισόδου (12-36ω)'))))
        # --- OVERS (W2) ---
        if ((fm_both or m['comp'] == 'ChampionsLeague') and m.get('xgh_ou') is not None and mk.get('tl') is not None and mk.get('to')
                and 1.70 <= float(mk['to']) <= 2.10):      # 13/10: over στα ματς χωρις FotMob ΜΟΝΟ UCL (UECL Β over −1.7%)
            td = tot_dist(m['xgh_ou'], m['xga_ou'], scale)
            po, pu = p_over(td, float(mk['tl']))
            e_o = po * (float(mk['to']) - 1) * (1 - picks.MARGIN) - pu
            thr_over = EDGE_OVER_UECL if (m['comp'] == 'ConferenceLeague' and fm_both) else EDGE_OVER
            if e_o >= thr_over:
                picks_out.append(dict(
                    mid=str(m['mid']), comp=m['comp'], rnd=m.get('round'), ko=m['utc'],
                    home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                    team=f"Over {float(mk['tl']):.2f}", side=0,
                    line=round(float(mk['tl']), 2), odds=round(float(mk['to']), 2),
                    edge=round(e_o, 4), role='over',
                    proj_odds=round((1 - max(1 - po - pu, 0)) / po, 3) if po > 0 else None,
                    tag75=False,
                    xgh=m['xgh_ou'], xga=m['xga_ou'], when=mk.get('when'), lim=mk.get('lim'),
                    no_play=(m['comp'] == 'EuropaLeague'),
                    src=(None if fm_both else f"{m.get('src_h')}/{m.get('src_a')}"),
                    note=(NO_PLAY_NOTE if m['comp'] == 'EuropaLeague' else
                          (None if fm_both else 'ομάδα χωρίς FotMob — μόνο over (10/10)'))))
        # --- UNDERS (W2 + ισοπαλιες ×scale) — UCL FotMob+FotMob ≥10% · 13/10: + CONFERENCE Β (μια χωρις FotMob) ≥14% ---
        uecl_b = fm_one and m['comp'] == 'ConferenceLeague'
        uel_u = fm_both and m['comp'] == 'EuropaLeague'                                          # 16/10: UEL Α = σκια
        if (((fm_both and m['comp'] == 'ChampionsLeague') or uecl_b or uel_u) and m.get('xgh_ou') is not None and mk.get('tl') is not None
                and mk.get('tu') and 1.70 <= float(mk['tu']) <= 2.10):
            td = tot_dist(m['xgh_ou'], m['xga_ou'], scale)
            po, pu = p_over(td, float(mk['tl']))
            e_u = pu * (float(mk['tu']) - 1) * (1 - picks.MARGIN) - po
            if e_u >= (EDGE_UNDER_UECL_B if uecl_b else (EDGE_UNDER_UEL if uel_u else EDGE_UNDER_UCL)):
                picks_out.append(dict(
                    mid=str(m['mid']), comp=m['comp'], rnd=m.get('round'), ko=m['utc'],
                    home=m['home'], away=m['away'], hid=m['hid'], aid=m['aid'],
                    team=f"Under {float(mk['tl']):.2f}", side=0,
                    line=round(float(mk['tl']), 2), odds=round(float(mk['tu']), 2),
                    edge=round(e_u, 4), role='under',
                    proj_odds=round((1 - max(1 - po - pu, 0)) / pu, 3) if pu > 0 else None,
                    tag75=False,
                    xgh=m['xgh_ou'], xga=m['xga_ou'], when=mk.get('when'), lim=mk.get('lim'),
                    rule=('uecl_b_under' if uecl_b else ('uel_under_shadow' if uel_u else None)),
                    src=(f"{m.get('src_h')}/{m.get('src_a')}" if uecl_b else None),
                    no_play=uel_u,
                    note=('Conference Β — under' if uecl_b else ('👁 ΣΚΙΑ — Europa under κατηγορίας Α (καταγραφή, δεν παίζεται)' if uel_u else None))))
    hf = {p['mid'] for p in picks_out if str(p.get('rule') or '').startswith('uel_home_fav')}
    picks_out = [p for p in picks_out if not (p['mid'] in hf and p['comp'] == 'EuropaLeague' and p['side'] == 1
                                              and p['role'] == 'fav' and not p.get('rule'))]
    # UCL ΧΑΝΤΙΚΑΠ ΤΕΛΕΥΤΑΙΟΥ 2ΩΡΟΥ = ΚΑΤΑΓΡΑΦΗ (13/10/2026, Στελιος «περνα το 1» — «επηρεαζεται απο ενδεκαδες που το μοντελο δεν ξερει»):
    # φαβορι/αουτσαιντερ Champions League που ΠΡΩΤΟΒΓΑΙΝΟΥΝ < 2ω πριν τη σεντρα → no_play, rule='late2h' (ημερολογιο ναι, Telegram οχι).
    # ucl_last2h_test / ucl_late_picks_table: χαντικαπ −13% (21, 2022-26) / −28% (14, νεα μορφη, 0/2)· φαβορι περνα κριτηρια (1ω & 3ω, 2 βιβλια).
    # «Πρωτη εμφανιση» = δεν υπαρχει ηδη στο euro_picks_ledger (ενα κλειδι ανα ματς/πλευρα)· αν γραφτηκε late2h, μενει late2h ως τη σεντρα.
    try:
        _led = {}
        for _ln in open(os.path.join(ROOT, 'euro_picks_ledger.jsonl'), encoding='utf-8'):
            if _ln.strip():
                _r = json.loads(_ln); _led[_r.get('key')] = _r
    except Exception:
        _led = {}
    for p in picks_out:
        if p['comp'] != 'ChampionsLeague' or p.get('role') not in ('fav', 'dog') or p.get('no_play') or p.get('rule'):
            continue
        prev = _led.get(f"{p['mid']}|{p['side']}")
        try:
            hb = (datetime.datetime.fromisoformat(str(p['ko']).replace('Z', '+00:00')) - now).total_seconds() / 3600
        except Exception:
            continue
        if (prev is not None and prev.get('rule') == 'late2h') or (prev is None and 0 < hb < LATE2H_UCL):
            p.update(no_play=True, rule='late2h',
                     note='📝 βγήκε στο τελευταίο 2ωρο — καταγραφή, δεν παίζεται (ενδεκάδες· ιστορικά UCL χάντικαπ εδώ −13%)')
    # 16/10/2026 (Στελιος «καντο ναι»): ΣΕΡΙ ΕΚΤΟΣ / ΚΟΥΡΑΣΗ — ΜΟΝΟ ΕΝΔΕΙΞΗ + ΣΚΙΑ, ΟΧΙ στο μοντελο (fatigue_flags.py).
    # (α) καρτα/Telegram: «⚠ <φιλοξ.>: 3ο εκτος στη σειρα · ξεκουραση · χλμ» σε ΚΑΘΕ ευρωπαικο pick του ματς.
    # (β) σκια UCL «A»: φιλοξ. με σερι ≥3 → υπεροχη +0.17 υπερ γηπεδουχου (ucl_away3_penalty_test)· γραφεται στο fatigue_shadow.jsonl
    #     η πρωτη ≤72ω αποτιμηση καθε πλευρας (χωρις/με ποινη), ΙΔΙΟΙ κανονες με τα UCL picks (FotMob+FotMob). Δεν αλλαζει picks/Telegram.
    try:
        import fatigue_flags as FF
        _fst = {}
        for m in P.get('matches', []):
            if m.get('covered') and not m.get('finished') and m.get('hid') and m.get('aid'):
                _s = FF.away_state(m['aid'], m['hid'], m['utc'])
                if _s:
                    _fst[str(m['mid'])] = (_s, FF.note(m['away'], _s))
        for p in picks_out:
            _n = (_fst.get(str(p['mid'])) or (None, None))[1]
            if _n:
                p['fatigue'] = _n
        _sh = []
        for m in P.get('matches', []):
            mid_ = str(m['mid']); fs_ = _fst.get(mid_)
            if (m.get('comp') != 'ChampionsLeague' or not fs_ or fs_[0]['streak'] < FF.STREAK_MIN
                    or m.get('src_h') != 'FotMob' or m.get('src_a') != 'FotMob'):
                continue
            mk = O.get(mid_) or {}
            try:
                ko = datetime.datetime.fromisoformat(str(m['utc']).replace('Z', '+00:00'))
            except Exception:
                continue
            hb = (ko - now).total_seconds() / 3600
            if not (0 < hb <= FF.ENTRY_H) or mk.get('line') is None:
                continue
            ph, pa = FF.shift(m['xgh'], m['xga'], FF.D_UCL)
            cands = []
            for tag, (xh_, xa_) in (('base', (m['xgh'], m['xga'])), ('pen', (ph, pa))):
                d_ = eu_dist(xh_, xa_, scale)
                for side, ln, o in ((1, float(mk['line']), mk.get('oh')), (-1, -float(mk['line']), mk.get('oa'))):
                    if not o or not (1.70 <= float(o) <= 2.10):
                        continue
                    role = 'fav' if ln <= -0.5 else ('dog' if ln >= 0.5 else ('dnb' if abs(ln) < 0.01 else None))
                    if role is None:
                        continue
                    pw, pp = cover_q(d_, side, ln) if role in ('fav', 'dnb') else picks.p_cover(d_, side, ln)
                    e_ = edge_of(pw, pp, float(o))
                    thr = EDGE_FAV_UCL if role == 'fav' else (EDGE_DOG_UCL if role == 'dog' else EDGE_DNB_UCL)
                    cands.append((tag, str(side), role, round(ln, 2), float(o), round(e_, 4), e_ >= thr))
                if m.get('xgh_ou') is not None and mk.get('tl') is not None:
                    oh_, oa_ = (FF.shift(m['xgh_ou'], m['xga_ou'], FF.D_UCL) if tag == 'pen' else (m['xgh_ou'], m['xga_ou']))
                    po, pu = p_over(tot_dist(oh_, oa_, scale), float(mk['tl']))
                    for side, o, thr in (('over', mk.get('to'), EDGE_OVER), ('under', mk.get('tu'), EDGE_UNDER_UCL)):
                        if not o or not (1.70 <= float(o) <= 2.10):
                            continue
                        w_, l_ = (po, pu) if side == 'over' else (pu, po)
                        e_ = w_ * (float(o) - 1) * (1 - picks.MARGIN) - l_
                        cands.append((tag, side, side, float(mk['tl']), float(o), round(e_, 4), e_ >= thr))
            for side in {c[1] for c in cands}:
                b = next((c for c in cands if c[0] == 'base' and c[1] == side), None)
                q = next((c for c in cands if c[0] == 'pen' and c[1] == side), None)
                if not ((b and b[6]) or (q and q[6])):
                    continue
                _sh.append(dict(key=f"uclA|{mid_}|{side}", var='UCL A (σερι≥3, δ 0.17)', seen=now.isoformat(timespec='minutes'),
                                hours_before=round(hb, 1), mid=mid_, comp=m['comp'], ko=str(m['utc'])[:16], home=m['home'], away=m['away'],
                                streak=fs_[0]['streak'], rest=fs_[0]['rest'], km14=fs_[0]['km14'], side=side,
                                role=(q or b)[2], line=(q or b)[3], odds=(q or b)[4],
                                edge_base=(b[5] if b else None), pick_base=bool(b and b[6]),
                                edge_pen=(q[5] if q else None), pick_pen=bool(q and q[6])))
        _nsh = FF.shadow_write(_sh)
        if _fst:
            print(f"σερι εκτος: {sum(1 for v in _fst.values() if v[1])} ματς με φιλοξ. 3ο+ εκτος · σκια UCL A νεες εγγραφες {_nsh}")
    except Exception as _e:
        print(f'σερι εκτος/σκια ΣΦΑΛΜΑ (μη κρισιμο): {type(_e).__name__}: {_e}')
    picks_out.sort(key=lambda p: p['ko'])
    json.dump(dict(scanned_at=now.isoformat()[:16], picks=picks_out,
                   rules=dict(edge_dog=EDGE_DOG, edge_fav=EDGE_FAV, edge_fav_ucl=EDGE_FAV_UCL,
                              edge_dog_ucl=EDGE_DOG_UCL, edge_over=EDGE_OVER, edge_over_uecl=EDGE_OVER_UECL, edge_under_ucl=EDGE_UNDER_UCL, edge_dog_uecl_b=EDGE_DOG_UECL_B, edge_under_uecl_b=EDGE_UNDER_UECL_B, edge_dnb_ucl=EDGE_DNB_UCL, late2h_ucl_hours=LATE2H_UCL,
                              zone=[1.70, 2.10],
                              no_play_comps=['EuropaLeague'],
                              uel_home_fav=dict(edge=UEL_HF_EDGE, hours=list(UEL_HF_WIN), blend_xg=0.8,
                                                note='εξαιρεση: UEL φαβορι εντος παιζονται κανονικα (9/10)'),
                              src='FotMob+FotMob', pricing='as-live (w2 + X x0.85 · dogs p_cover · φαβορι σωστα τεταρτα 30/9)')),
              open(os.path.join(ROOT, 'euro_value_latest.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print(f'euro value picks (beta): {len(picks_out)} '
          f'({sum(1 for p in picks_out if p["role"]=="fav")} fav / '
          f'{sum(1 for p in picks_out if p["role"]=="dog")} dog, {sum(1 for p in picks_out if p["role"]=="dnb")} dnb, '
          f'{sum(1 for p in picks_out if p["role"]=="over")} over / {sum(1 for p in picks_out if p["role"]=="under")} under, '
          f'{sum(1 for p in picks_out if p["tag75"])} στο -0.75, '
          f'{sum(1 for p in picks_out if p.get("no_play"))} UEL σκια/δεν παιζονται, '
          f'{sum(1 for p in picks_out if p.get("rule") == "uel_home_fav")} UEL φαβ εντος ΚΑΝΟΝΙΚΑ)')


if __name__ == '__main__':
    main()
