# -*- coding: utf-8 -*-
"""absence_log.py — 20/10/2026 (Στελιος: «καταγραφη απουσιων — δεν εχει αποδειχτει οτι η αγορα 2 μερες πριν εχει τιμολογησει σωστα μια
ενδεκαδα· π.χ. Σιτι-ΑΕΚ η τιμη της ΑΕΚ επεσε οταν βγηκε οτι ο Σεμενιο μενει εκτος»).
ΜΟΝΟ ΣΥΛΛΟΓΗ — δεν αλλαζει κανενα pick. Για καθε επερχομενο ματς CORE7 (match_projections_archive) και Ευρωπης (euro_projections) εως 7 μερες
μπροστα: λιστα «unavailable» του FotMob (τραυματιες / τιμωρημενοι + αναμενομενη επιστροφη) ανα ομαδα, ειδος ενδεκαδας (lastStarting11 =
προσωρινη, standard = ΕΠΙΣΗΜΗ) και οι βασικοι οταν ειναι επισημη. Γραφει στο absence_log.jsonl ΜΟΝΟ οταν κατι αλλαξε (με χρονοσφραγιδα) →
ξερουμε ΠΟΤΕ εμφανιστηκε καθε απουσια/ενδεκαδα, για να το βαλουμε διπλα στην κινηση της αγορας (odds_history / euro_odds_hist).
Ρυθμος (state: absence_log_state.json): ολα τα ματς ≤7 μερες καθε 3 ωρες · ματς ≤4 ωρες πριν τη σεντρα καθε 15′ (για την ωρα της επισημης)."""
import json, os, sys, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'absence_log.jsonl')
ST = os.path.join(ROOT, 'absence_log_state.json')
FULL_H, NEAR_H, NEAR_MIN, HORIZON_D = 3.0, 4.0, 15.0, 7
UTC = dt.timezone.utc


def _t(s):
    d = dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def upcoming(now):
    out = {}
    try:
        for fid, m in json.load(open(os.path.join(ROOT, 'match_projections_archive.json'), encoding='utf-8')).items():
            if m.get('score'):
                continue
            try:
                ko = _t(m.get('utc'))
            except Exception:
                continue
            if now < ko <= now + dt.timedelta(days=HORIZON_D):
                out[str(fid)] = (m.get('league'), ko, m.get('home'), m.get('away'))
    except Exception as e:
        print(f'absence_log: CORE7 προγραμμα σφαλμα {str(e)[:60]}')
    try:
        for m in json.load(open(os.path.join(ROOT, 'euro_projections.json'), encoding='utf-8')).get('matches', []):
            if m.get('finished'):
                continue
            try:
                ko = _t(m.get('utc'))
            except Exception:
                continue
            if now < ko <= now + dt.timedelta(days=HORIZON_D):
                out[str(m['mid'])] = (m.get('comp'), ko, m.get('home'), m.get('away'))
    except Exception as e:
        print(f'absence_log: Ευρωπη προγραμμα σφαλμα {str(e)[:60]}')
    return out


def snap(mid):
    import intl_fetch
    d = json.loads(intl_fetch.get(f'https://www.fotmob.com/api/data/matchDetails?matchId={mid}'))
    lu = (d.get('content') or {}).get('lineup') or {}
    rec = {'type': lu.get('lineupType')}
    for side, k in (('homeTeam', 'h'), ('awayTeam', 'a')):
        t = lu.get(side) or {}
        un = []
        for u in t.get('unavailable') or []:
            ua = u.get('unavailability') or {}
            un.append([u.get('id'), u.get('name'), ua.get('type'), ua.get('expectedReturn')])
        rec[k + '_out'] = sorted(un, key=lambda x: str(x[0]))
        if lu.get('lineupType') in ('standard', 'predicted'):          # standard = ΕΠΙΣΗΜΗ · predicted = προβλεπομενη του FotMob
            rec[k + '_xi'] = sorted(p.get('id') for p in (t.get('starters') or []) if p.get('id'))
    return rec


def main():
    now = dt.datetime.now(UTC)
    try:
        st = json.load(open(ST, encoding='utf-8'))
    except Exception:
        st = {}
    last_full = _t(st['last_full']) if st.get('last_full') else None
    full = last_full is None or (now - last_full).total_seconds() >= FULL_H * 3600
    U = upcoming(now)
    todo = []
    for mid, (comp, ko, h, a) in U.items():
        near = (ko - now).total_seconds() <= NEAR_H * 3600
        last = st.get('m', {}).get(mid, {}).get('t')
        due_near = near and (last is None or (now - _t(last)).total_seconds() >= NEAR_MIN * 60)
        if full or due_near:
            todo.append((mid, comp, ko, h, a))
    if not todo:
        print('absence_log: τιποτα για ελεγχο τωρα'); return
    st.setdefault('m', {}); n_new = n_err = 0
    with open(OUT, 'a', encoding='utf-8') as out:
        for mid, comp, ko, h, a in todo:
            try:
                rec = snap(mid)
            except Exception:
                n_err += 1; continue
            sig = json.dumps(rec, sort_keys=True, ensure_ascii=False)
            prev = st['m'].get(mid, {})
            if prev.get('sig') != sig:
                out.write(json.dumps(dict(t=now.isoformat()[:16], mid=mid, comp=comp, ko=ko.isoformat()[:16], home=h, away=a,
                                          hrs=round((ko - now).total_seconds() / 3600, 1), **rec), ensure_ascii=False) + '\n')
                n_new += 1
            st['m'][mid] = {'sig': sig, 't': now.isoformat()[:16], 'ko': ko.isoformat()[:16]}
            time.sleep(0.3)
    st['m'] = {k: v for k, v in st['m'].items() if _t(v['ko']) > now - dt.timedelta(days=2)}      # καθαρισμα παλιων
    if full:
        st['last_full'] = now.isoformat()
    json.dump(st, open(ST, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'absence_log: ελεγχθηκαν {len(todo)} ({"πληρες" if full else "κοντα στη σεντρα"}) · νεες εγγραφες {n_new} · σφαλματα {n_err}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
