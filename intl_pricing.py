"""
intl_pricing.py — ΣΩΣΤΗ τιμολογηση OVER για τις εθνικες (25/9/2026, αποφαση Στελιου).

Ο παλιος τυπος (P(συνολο > floor(γραμμη)) × τιμη − 1) αγνοουσε push και μισα:
  x.25 και x.75 μετρουσαν σαν x.5, οι ακεραιες (2.0, 3.0) σαν x.5 με το push ως ηττα.
Τεστ 25/9 (intl_window_test.py OVER_FORMULA=live|proper): closing ROI +11.6→+16.4% (Crown), +12.3→+16.8% (SBOBET), μοναδες ×2·
72ω ROI 14.4→12.0 / 15.8→13.5 με ιδιες περιπου μοναδες. Ο Στελιος διαλεξε τον σωστο τυπο (πραγματικο edge σε καθε γραμμη).

Εκκαθαριση που αντιστοιχει:  x.5 = κερδος/ηττα · ακεραια = push επιστρεφει · x.25 / x.75 = μισο στις δυο διπλανες γραμμες.
"""
import math


def _pk(T, k):
    return math.exp(-T) * T ** k / math.factorial(k)


def over_ev(T, line, odds):
    """Αναμενομενη αποδοση (edge) ενος over στη γραμμη `line` με δεκαδικη τιμη `odds`, οταν το συνολο γκολ ~ Poisson(T)."""
    q = round(float(line) * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9:                      # x.25 / x.75 -> μισο/μισο
        return 0.5 * over_ev(T, q - 0.25, odds) + 0.5 * over_ev(T, q + 0.25, odds)
    pw = 1 - sum(_pk(T, k) for k in range(int(math.floor(q)) + 1))      # κερδιζει: συνολο > γραμμη
    pp = _pk(T, int(q)) if float(q).is_integer() else 0.0               # push: συνολο == ακεραια γραμμη
    return pw * (odds - 1) - (1 - pw - pp)


def over_p_equiv(T, line, odds):
    """«Ισοδυναμη» πιθανοτητα: αυτη που, στην ιδια τιμη, δινει το ιδιο edge με ενα απλο (χωρις push) over. Για προβολη στο dashboard."""
    return (over_ev(T, line, odds) + 1) / odds


def over_fair(T, line):
    """Fair τιμη (edge 0) του over στη γραμμη — λυση της over_ev(T, line, o) = 0."""
    lo, hi = 1.01, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if over_ev(T, line, mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------- HANDICAP (25/9/2026, αποφαση Στελιου: σωστα τεταρτα και στο AH των εθνικων) ----------------
# Παλια: picks.p_cover στη γραμμη → +x.25 μετρουσε σαν +x.5, −x.75 σαν −x.5 κλπ (τεταρτα = κοντινοτερη μιση).
# Σωστα: x.25 / x.75 = μισο πονταρισμα σε καθε διπλανη γραμμη (οπως πληρωνει το βιβλιο και οπως εκκαθαριζει το picks.settle).
# Τεστ 25/9 (intl_window_test.py AH_FORMULA=proper, intl_ah_quarter_out.txt): ROI 72ω +3.6→+5.3% (Crown), +4.2→+5.2% (SBOBET)·
# κερδιζει φαβορι −x.25, κοβει φαβορι −x.75· ΧΑΝΕΙ dog +x.25 (αντισταθμιστικο λαθος: το μοντελο υποτιμα «φαβορι +1»).
# ΕΚΚΡΕΜΕΙ: διορθωση του μοντελου στα στενα αποτελεσματα· αν δεν δουλεψει → εξεταση dog +x.25 με τον παλιο τροπο.
# Τα ΕΓΧΩΡΙΑ μενουν με picks.p_cover (τεστ 21/9 εκει ❌).
def _parts(ud):
    return [ud] if (ud * 4) % 2 == 0 else [ud - 0.25, ud + 0.25]


def ah_ev(dist, side, ud, odds, margin=0.0):
    """Edge AH με σωστα τεταρτα. dist = κατανομη διαφορας γκολ (picks.gd_dist), side 1 γηπεδουχος / −1 φιλοξενουμενος,
    ud = handicap της πλευρας, margin = ποσοστο που αφαιρειται απο το κερδος (picks.MARGIN στο live)."""
    import picks
    e = 0.0
    for L in _parts(ud):
        pw, pp = picks.p_cover(dist, side, L)
        e += (pw * (odds - 1) * (1 - margin) - (1 - pw - pp)) / len(_parts(ud))
    return e


def ah_fair(dist, side, ud):
    """Fair τιμη (edge 0, χωρις margin) της πλευρας στη γραμμη ud, με σωστα τεταρτα. None αν δεν οριζεται."""
    import picks
    sw = sl = 0.0
    for L in _parts(ud):
        pw, pp = picks.p_cover(dist, side, L); sw += pw; sl += 1 - pw - pp
    return round(1 + sl / sw, 2) if sw > 0 else None


def settle_over(total, line, odds):
    """Αποτελεσμα (μοναδες ανα 1 πονταρισμα) ενος over: x.5 κερδος/ηττα, ακεραια push = 0, x.25/x.75 μισο/μισο."""
    q = round(float(line) * 4) / 4
    if abs(q * 2 - round(q * 2)) > 1e-9:
        return 0.5 * settle_over(total, q - 0.25, odds) + 0.5 * settle_over(total, q + 0.25, odds)
    if total > q:
        return odds - 1
    return 0.0 if abs(total - q) < 1e-9 else -1.0
