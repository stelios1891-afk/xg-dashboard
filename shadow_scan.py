# -*- coding: utf-8 -*-
"""shadow_scan.py — ΣΚΙΩΔΗΣ καταγραφη τριων συστηματων picks (2627), χωρις να αγγιζει το live.

Σε καθε τρεξιμο (scanner workflow, μετα το scan_value): για καθε επερχομενο CORE7 ματς
με ratings + τρεχουσα γραμμη (odds_history_state.json), υπολογιζει και τις ΤΡΕΙΣ εκδοχες:
  A  = σημερινο live: picks.p_cover ως εχει (λαθος τεταρτα), φιλτρα edge>=10%/1.70-2.10/γραμμη>=0.5
  C  = καθαρο: σωστο quarter pricing, ΜΟΝΟ x.0/x.5 γραμμες, edge>=10%
  B2 = διορθωμενο: σωστο quarter pricing + logit shrink στο pw (ΕΙΛΙΚΡΙΝΕΣ edge)
Παραμετροι B2 (a, b): μεσος των 4 folds του pw_shrink τεστ πανω στο ΚΑΝΟΝΙΚΟ engine
(europe_test_preds, ραμπα χαρακα): a=-0.139, b=0.305 — βαθμονομημενοι ΜΟΝΟ στο σφαλμα καλυψης.

Γραφει shadow_picks.jsonl (append) ΜΟΝΟ οταν αλλαξει κατι για το ματς (γραμμη/αποδοση/xg),
με state στο shadow_state.json. Καταγραφει ΚΑΙ τη πλευρα του φαβορι (πληροφοριακα — κλειστη
υποθεση, αλλα τζαμπα δεδομενα). Η αξιολογηση γινεται απο το shadow_report.py στη 15η.
ΚΑΜΙΑ αλλαγη σε picks.py / scan_value / toa_live.
"""
import sys, os, json, math, datetime
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard'))

import picks
import build_data

OUT = 'shadow_picks.jsonl'
STATE_F = 'shadow_state.json'
A_SHRINK = dict(a=-0.139, b=0.305)
HORIZON_DAYS = 6
EDGE_FLOOR_B2 = 0.00      # καταγραφουμε καθε dog με μη-αρνητικο ειλικρινες edge (για ολα τα κατωφλια μετα)


def p_cover_quarter(dist, side, line):
    parts = [line] if (line * 4) % 2 == 0 else [line - 0.25, line + 0.25]
    pw = pp = 0.0
    for L in parts:
        w, p = picks.p_cover(dist, side, L)
        pw += w / len(parts); pp += p / len(parts)
    return pw, pp


def edge_of(pw, pp, o):
    return pw * (o - 1) * (1 - picks.MARGIN) - (1 - pw - pp)


def shrink_pw(pw):
    pwc = min(max(pw, 1e-6), 1 - 1e-6)
    z = A_SHRINK['a'] + A_SHRINK['b'] * math.log(pwc / (1 - pwc))
    return 1.0 / (1.0 + math.exp(-z))


def ltype(h):
    f = round(h - math.floor(h), 2)
    return {0.0: 'x.0', 0.5: 'x.5', 0.25: 'x.25', 0.75: 'x.75'}.get(f, '???')


def in_band(o):
    return picks.OMIN <= o <= picks.OMAX


if __name__ == '__main__':
    try:
        with open(STATE_F, encoding='utf-8') as fh:
            state = json.load(fh)
    except Exception:
        state = {}
    try:
        with open('odds_history_state.json', encoding='utf-8') as fh:
            ostate = json.load(fh)
    except Exception:
        raise SystemExit('odds_history_state.json δεν βρεθηκε — τρεξε μετα τον scanner.')

    Mp, id2name = picks.load_matches(list(build_data.LEAGUE_FOTMOB), [build_data.RATINGS_SEASON_DEFAULT])
    Mc, id2c = picks.load_matches(list(build_data.LEAGUE_FOTMOB), [build_data.CURRENT_SEASON])
    id2name.update(id2c)
    name2id = {v: k for k, v in id2name.items()}

    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.isoformat(timespec='minutes')
    horizon = now + datetime.timedelta(days=HORIZON_DAYS)
    n_new = 0
    with open(OUT, 'a', encoding='utf-8') as fh:
        for lg in list(build_data.LEAGUE_FOTMOB):
            try:
                LR = build_data.league_ratings(lg, Mp, Mc, id2name=id2name, name2id=name2id)
            except Exception as e:
                print(f'{lg}: ratings σφαλμα {type(e).__name__}', flush=True)
                continue
            for f in LR['fixtures']:
                try:
                    ko = datetime.datetime.fromisoformat(str(f.get('utc')).replace('Z', '+00:00'))
                except Exception:
                    continue
                if not (now < ko <= horizon):
                    continue
                H = int(f.get('home_id') or 0); A = int(f.get('away_id') or 0)
                sig = (ostate.get(f'{H}_{A}') or {}).get('sig')
                if not sig or sig[0] is None or sig[1] is None or sig[2] is None:
                    continue
                line, oh, oa = float(sig[0]), float(sig[1]), float(sig[2])
                rh = LR['blended'].get(H); ra = LR['blended'].get(A)
                if not rh or not ra:
                    continue
                pf = build_data._predict_ratings(rh, ra, LR['lg_shots'], LR['lg_xgps'], LR['hf'])
                xh = min(max(pf['home_adj_xg'], 0.05), 6.0)
                xa = min(max(pf['away_adj_xg'], 0.05), 6.0)
                # dog = η πλευρα που ΠΑΙΡΝΕΙ το χαντικαπ (ud >= 0.5) — μονο αυτη παιζει το live
                if line >= 0.5:
                    dside, ud, o_dog, o_fav = 1, line, oh, oa
                elif line <= -0.5:
                    dside, ud, o_dog, o_fav = -1, -line, oa, oh
                else:
                    continue
                dist = picks.gd_dist(xh, xa)
                pwA, ppA = picks.p_cover(dist, dside, ud)
                pwQ, ppQ = p_cover_quarter(dist, dside, ud)
                pwS = shrink_pw(pwQ)
                lt = ltype(ud)
                e_A = edge_of(pwA, ppA, o_dog)
                e_C = edge_of(pwQ, ppQ, o_dog)
                e_B2 = edge_of(pwS, ppQ, o_dog)
                # φαβορι (συμπληρωμα των διορθωμενων πιθανοτητων του dog)
                pwSf = max(1.0 - pwS - ppQ, 0.0)
                e_B2f = edge_of(pwSf, ppQ, o_fav)
                isA = bool(in_band(o_dog) and e_A >= picks.EDGE)
                isC = bool(in_band(o_dog) and lt in ('x.0', 'x.5') and e_C >= picks.EDGE)
                keep = isA or isC or (in_band(o_dog) and e_B2 >= EDGE_FLOOR_B2) \
                    or (in_band(o_fav) and e_B2f >= 0.02)
                if not keep:
                    continue
                key = f'{H}_{A}'
                sig_now = [round(line, 2), round(oh, 2), round(oa, 2), round(xh, 3), round(xa, 3)]
                if state.get(key) == sig_now:
                    continue          # τιποτα δεν αλλαξε απο την τελευταια καταγραφη
                state[key] = sig_now
                fh.write(json.dumps(dict(
                    t=ts, lg=lg, hid=H, aid=A,
                    home=f.get('home_name'), away=f.get('away_name'), ko=str(f.get('utc')),
                    line=line, oh=oh, oa=oa, xh=round(xh, 3), xa=round(xa, 3),
                    dside=dside, ud=ud, lt=lt,
                    e_A=round(e_A, 4), e_C=round(e_C, 4), e_B2=round(e_B2, 4),
                    isA=isA, isC=isC,
                    o_fav=o_fav, e_B2f=round(e_B2f, 4),
                    pwA=round(pwA, 4), pwQ=round(pwQ, 4), pwS=round(pwS, 4), ppQ=round(ppQ, 4)),
                    ensure_ascii=False) + '\n')
                n_new += 1
    with open(STATE_F, 'w', encoding='utf-8') as fh:
        json.dump(state, fh)
    print(f'shadow: {n_new} νεες εγγραφες ({ts})')
