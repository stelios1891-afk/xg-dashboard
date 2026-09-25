"""
intl_consensus.py — ΚΑΝΟΝΑΣ LIVE ΕΘΝΙΚΩΝ (25/9/2026, αποφαση Στελιου): παιζεται ενα pick οταν το δινουν ΤΟΥΛΑΧΙΣΤΟΝ 2 απο τα 3 μοντελα
(Μ1 H+αξια / Μ2 Αγκυρα / Μ3 Αγκυρα+αξια), σε handicap (dog ΚΑΙ φαβορι) και over. Οχι 1Χ2.
Τεστ: intl_model_choice_final.py (72ω, σωστα τεταρτα): συναινεση ≥2/3 +10.3% Crown / +10.8% SBOBET, 5/5 σεζον, οι περισσοτερες μοναδες.
ΕΚΚΡΕΜΕΙ: dog +x.25 (μετα τα σωστα τεταρτα ≈0) — διορθωση στενων νικων του μοντελου αργοτερα.

Διαβαζει τα picks-κειμενα του intl_dashboard_build (ιδιοι κανονες/τιμολογηση με το tab), ωστε να μη διαφερει ποτε απο αυτα που φαινονται.
"""
import re

RX_AH = re.compile(r'^(DOG|FAV) ([12]) ([+-]?\d+(?:\.\d+)?) @(\d+(?:\.\d+)?) \(([^,]+), ([+-]?\d+)%\)')
RX_OV = re.compile(r'^OVER (\d+(?:\.\d+)?) @(\d+(?:\.\d+)?) \(([^,]+), ([+-]?\d+)%\)')
VERS = (('H', 'over', 'Μ1'), ('A', 'over_A', 'Μ2'), ('AV', 'over_AV', 'Μ3'))
NEED = 2


def parse(pick):
    """κειμενο pick του build -> λιστα {mkt, role, side, line, odds, book, edge}. Αγνοει 1Χ2, «εκτος κανονα», νεκρα."""
    out = []
    for part in [p.strip() for p in str(pick or '').split(' · ') if p.strip()]:
        m = RX_AH.match(part)
        if m:
            role, s, line, odds, book, e = m.groups()
            out.append(dict(mkt='AH', role='dog' if role == 'DOG' else 'fav', side=int(s), line=float(line), odds=float(odds),
                            book=book.strip(), edge=int(e) / 100))
            continue
        m = RX_OV.match(part)
        if m:
            line, odds, book, e = m.groups()
            out.append(dict(mkt='OVER', role='over', side=0, line=float(line), odds=float(odds), book=book.strip(), edge=int(e) / 100))
    return out


def model_picks(picks):
    """{'Μ1': [...], 'Μ2': [...], 'Μ3': [...]} απο το dict picks ενος ματς."""
    return {lab: parse(picks.get(v, '')) + parse(picks.get(ov, '')) for v, ov, lab in VERS}


def consensus(picks, need=NEED):
    """Picks οπου συμφωνουν ≥need μοντελα (ιδια αγορα & πλευρα). Τιμη/γραμμη απο το μοντελο με το ΜΙΚΡΟΤΕΡΟ edge (συντηρητικα)."""
    mp = model_picks(picks); groups = {}
    for lab, ps in mp.items():
        for p in ps:
            groups.setdefault((p['mkt'], p['side']), []).append((lab, p))
    out = []
    for (mkt, side), lst in groups.items():
        labs = sorted({lab for lab, _ in lst})
        if len(labs) < need:
            continue
        lab0, p0 = min(lst, key=lambda z: z[1]['edge'])
        out.append(dict(p0, models='+'.join(labs), n=len(labs), edges={lab: p['edge'] for lab, p in lst}))
    return sorted(out, key=lambda d: (d['mkt'], d['side']))


def label(c, home, away):
    """ανθρωπινο κειμενο: «Ελβετια −1.25 @1.89» ή «Over 2.25 @2.03»."""
    if c['mkt'] == 'OVER':
        return f"Over {c['line']:g} @{c['odds']:.2f}"
    team = home if c['side'] == 1 else away
    return f"{team} {c['line']:+g} @{c['odds']:.2f}"


def late_note(hours):
    """υποσημειωση για picks που πρωτοεμφανιστηκαν στις 2 τελευταιες ωρες πριν τη σεντρα (αποφαση Στελιου 25/9: μπαινουν, με σημειωση)."""
    if hours is None or hours >= 2:
        return ''
    return 'μπήκε <1 ώρα πριν' if hours < 1 else 'μπήκε ~1-2 ώρες πριν'
