"""gr_time.py — ΜΙΑ κοινη «ωρα Ελλαδας» για ολο το dashboard (21/10/2026, Στελιος: ολες οι ωρες σε ωρα Ελλαδας).
Τα αρχεια ειναι UTC (ISO, με ή χωρις 'Z'/offset· naive = UTC). Θερινη/χειμερινη σωστα: ZoneInfo('Europe/Athens'),
αλλιως ο κανονας της ΕΕ (τελευταια Κυριακη Μαρτιου/Οκτωβριου 01:00 UTC) — ΠΟΤΕ σταθερο +3."""
import datetime as _dt

DAYS = ['Δευ', 'Τρι', 'Τετ', 'Πεμ', 'Παρ', 'Σαβ', 'Κυρ']


def _parse(v):
    if isinstance(v, _dt.datetime):
        d = v
    else:
        s = str(v).strip().replace('Z', '+00:00').replace(' ', 'T')
        d = _dt.datetime.fromisoformat(s[:25] if '+' in s[10:] or s[19:20] == '-' else s[:19])
    return d.replace(tzinfo=_dt.timezone.utc) if d.tzinfo is None else d


def athens(v):
    """UTC (str ή datetime) → aware datetime σε ωρα Ελλαδας. Σηκωνει εξαιρεση αν δεν διαβαζεται."""
    d = _parse(v)
    try:
        from zoneinfo import ZoneInfo
        return d.astimezone(ZoneInfo('Europe/Athens'))
    except Exception:
        u = d.astimezone(_dt.timezone.utc)
        def last_sun(y, mo):
            x = _dt.datetime(y, mo, 31, 1, tzinfo=_dt.timezone.utc)
            return x - _dt.timedelta(days=(x.weekday() + 1) % 7)
        off = 3 if last_sun(u.year, 3) <= u < last_sun(u.year, 10) else 2
        return u.astimezone(_dt.timezone(_dt.timedelta(hours=off)))


def stamp(v, day=True):
    """«Τετ 21/10 13:16» (ή «21/10 13:16» με day=False). Κενο → ''· αδιαβαστο → η τιμη + ' UTC' (να μη φαινεται ψεμα)."""
    if v in (None, ''):
        return ''
    try:
        d = athens(v)
        return (DAYS[d.weekday()] + ' ' if day else '') + d.strftime('%d/%m %H:%M')
    except Exception:
        return f'{str(v)[:16].replace("T", " ")} UTC'


def date_str(v):
    """Ημερομηνια Ελλαδας 'YYYY-MM-DD' (για φιλτρα «σημερα/μηνας»)· αδιαβαστο → τα πρωτα 10 χαρακτηρες."""
    try:
        return athens(v).strftime('%Y-%m-%d')
    except Exception:
        return str(v)[:10]


def today():
    """Σημερινη ημερομηνια Ελλαδας (date)."""
    return athens(_dt.datetime.now(_dt.timezone.utc)).date()
