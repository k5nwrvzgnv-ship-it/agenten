"""Termine aus Links: Python lädt die Seite, liest Veranstaltungen aus und baut eine .ics-Datei.

Schickt Jan einen Link (z. B. Anmeldebestätigung eines Webinars), lädt seite_holen() die Seite
(nur lesend, höchstens MAX_BYTES). veranstaltungen() liest schema.org-Events aus den
<script type="application/ld+json">-Blöcken (auch subEvent einer EventSeries), seitentext() den
lesbaren Text für Claude. ics() baut daraus einen Kalendereintrag, den Jan in Telegram antippt
und in seinen Kalender übernimmt. In Jans Kalender schreibt der Agent nicht selbst.

Termin-Vorschläge von Claude (aus Mails, Material, Aufträgen): Claude schreibt
data/entwuerfe/<schluessel>/termin_<n>.json, entwurf_pruefen() macht daraus eine Veranstaltung
(Zeiten ohne Zone gelten als deutsche Zeit, Datum ohne Uhrzeit = ganztägig), doppelt() gleicht mit
Jans Kalender ab. Erinnerungen werden VALARMs in der .ics.

Ohne Netz testbar: alles außer seite_holen().
"""

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

MAX_BYTES = 2_000_000
MAX_TEXT = 6000
LINK = re.compile(r"https?://[^\s<>\"']+")
DAUER = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")
STANDARD_DAUER = timedelta(hours=1)
ZONE = ZoneInfo("Europe/Berlin")
ERINNERUNGEN = (1440, 120)  # Minuten vorher: 1 Tag und 2 Stunden (Jan, 27.10.2026)
ERINNERUNGEN_GANZTAGS = (900,)  # Vortag 9 Uhr
MAX_ERINNERUNG = 14 * 1440
MAX_DAUER = timedelta(hours=24)
MAX_TAGE = 14


class TerminFehler(Exception):
    pass


@dataclass
class Veranstaltung:
    titel: str
    beginn: datetime
    ende: datetime
    ort: str
    beschreibung: str
    ganztags: bool = False  # dann zählen nur die Daten, ende ist der letzte Tag (einschließlich)
    erinnerungen: tuple[int, ...] = ()  # Minuten vor Beginn


def links(text: str) -> list[str]:
    return [u.rstrip(").,;") for u in LINK.findall(text)]


def seite_holen(url: str, timeout: int = 20) -> str:
    anfrage = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (uni-agent)"})
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:  # noqa: S310 – Jans Link, nur lesend
        roh = antwort.read(MAX_BYTES + 1)
        zeichensatz = antwort.headers.get_content_charset() or "utf-8"
    if len(roh) > MAX_BYTES:
        raise TerminFehler(f"Seite größer als {MAX_BYTES // 1_000_000} MB")
    return roh.decode(zeichensatz, errors="replace")


class _Leser(HTMLParser):
    """Sammelt JSON-LD-Blöcke und sichtbaren Text."""

    def __init__(self):
        super().__init__()
        self.jsonld, self.text, self._art = [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._art = "jsonld" if dict(attrs).get("type") == "application/ld+json" else "skript"
        elif tag in ("style", "noscript"):
            self._art = "skript"

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._art = None

    def handle_data(self, data):
        if self._art == "jsonld":
            self.jsonld.append(data)
        elif self._art is None and data.strip():
            self.text.append(" ".join(data.split()))


def _lesen(html: str) -> _Leser:
    leser = _Leser()
    leser.feed(html)
    return leser


def seitentext(html: str, max_zeichen: int = MAX_TEXT) -> str:
    text = "\n".join(_lesen(html).text)
    return text if len(text) <= max_zeichen else text[:max_zeichen] + "\n[... gekürzt]"


def dauer(text: str) -> timedelta | None:
    """ISO-8601-Dauer wie PT1H30M oder P1DT2H."""
    m = DAUER.match(text or "")
    if not m or not any(m.groups()):
        return None
    t, h, mi, s = (int(x or 0) for x in m.groups())
    return timedelta(days=t, hours=h, minutes=mi, seconds=s)


def _zeit(text: str) -> datetime | None:
    try:
        z = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return z if z.tzinfo else None  # ohne Zone ist der Termin nicht eindeutig


def _events(daten) -> list[dict]:
    if isinstance(daten, list):
        return [e for d in daten for e in _events(d)]
    if not isinstance(daten, dict):
        return []
    gefunden = []
    art = daten.get("@type")
    arten = art if isinstance(art, list) else [art]
    if any(isinstance(a, str) and a.endswith("Event") for a in arten) and daten.get("startDate"):
        gefunden.append(daten)
    for schluessel in ("@graph", "subEvent"):
        gefunden += _events(daten.get(schluessel))
    return gefunden


def veranstaltungen(html: str) -> list[Veranstaltung]:
    """Alle Events mit Beginn samt Zeitzone, ohne Doppelte, nach Beginn sortiert."""
    ergebnis = {}
    for block in _lesen(html).jsonld:
        try:
            daten = json.loads(block)
        except json.JSONDecodeError:
            continue
        for e in _events(daten):
            beginn = _zeit(e.get("startDate"))
            if not beginn:
                continue
            ende = _zeit(e.get("endDate")) or beginn + (dauer(e.get("duration")) or STANDARD_DAUER)
            ort = e.get("location") or ""
            if isinstance(ort, dict):
                ort = ort.get("url") or ort.get("name") or ""
            titel = " ".join(str(e.get("name") or "Termin").split())
            ergebnis[(titel, beginn)] = Veranstaltung(titel, beginn, ende, ort,
                                                      " ".join(str(e.get("description") or "").split()))
    return sorted(ergebnis.values(), key=lambda v: v.beginn)


def _ics_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _falten(zeile: str) -> list[str]:
    """Zeilen nach RFC 5545 auf 75 Bytes falten, ohne UTF-8-Zeichen zu zerschneiden."""
    teile, aktuell = [], ""
    for zeichen in zeile:
        grenze = 75 if not teile else 74
        if len((aktuell + zeichen).encode()) > grenze:
            teile.append(aktuell)
            aktuell = ""
        aktuell += zeichen
    teile.append(aktuell)
    return [teile[0]] + [" " + t for t in teile[1:]]


def ics(v: Veranstaltung, uid: str, link: str = "", jetzt: datetime | None = None) -> str:
    utc = "%Y%m%dT%H%M%SZ"
    jetzt = jetzt or datetime.now(timezone.utc)
    beschreibung = v.beschreibung + (f"\n\nLink: {link}" if link else "")
    zeilen = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//agenten//uni//DE", "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{jetzt.astimezone(timezone.utc).strftime(utc)}",
    ]
    if v.ganztags:
        zeilen += [f"DTSTART;VALUE=DATE:{v.beginn.strftime('%Y%m%d')}",
                   f"DTEND;VALUE=DATE:{(v.ende.date() + timedelta(days=1)).strftime('%Y%m%d')}"]
    else:
        zeilen += [f"DTSTART:{v.beginn.astimezone(timezone.utc).strftime(utc)}",
                   f"DTEND:{v.ende.astimezone(timezone.utc).strftime(utc)}"]
    zeilen.append(f"SUMMARY:{_ics_text(v.titel)}")
    if v.ort:
        zeilen.append(f"LOCATION:{_ics_text(v.ort)}")
    if link:
        zeilen.append(f"URL:{link}")
    if beschreibung.strip():
        zeilen.append(f"DESCRIPTION:{_ics_text(beschreibung.strip())}")
    for minuten in v.erinnerungen:
        zeilen += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_ics_text(v.titel)}",
                   f"TRIGGER:-PT{minuten}M", "END:VALARM"]
    zeilen += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(z for zeile in zeilen for z in _falten(zeile)) + "\r\n"


def uid(v: Veranstaltung) -> str:
    """Fest aus Titel und Beginn: derselbe Termin bekommt immer dieselbe UID."""
    return hashlib.sha1(f"{v.titel}|{v.beginn.isoformat()}".encode()).hexdigest()[:16] + "@uni.agenten"


def dateiname(v: Veranstaltung) -> str:
    kurz = re.sub(r"[^A-Za-z0-9]+", "_", v.titel)[:40].strip("_") or "termin"
    return f"{v.beginn.astimezone(ZONE).strftime('%Y-%m-%d')}_{kurz}.ics"


def beschreiben(v: Veranstaltung) -> str:
    """Eine Zeile für Prompt und Meldung, Zeiten deutscher Zeit."""
    tage = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    b, e = v.beginn.astimezone(ZONE), v.ende.astimezone(ZONE)
    if v.ganztags:
        bis = "" if e.date() == b.date() else f" bis {tage[e.weekday()]} {e.strftime('%d.%m.%Y')}"
        return f"{v.titel}: {tage[b.weekday()]} {b.strftime('%d.%m.%Y')}{bis} (ganztägig)"
    bis = e.strftime("%H:%M") if e.date() == b.date() else e.strftime("%d.%m.%Y %H:%M")
    return f"{v.titel}: {tage[b.weekday()]} {b.strftime('%d.%m.%Y %H:%M')}-{bis} Uhr"


def erinnerung_text(minuten: tuple[int, ...]) -> str:
    """'1 Tag und 2 Std. vorher' für die Meldung."""
    def eins(m: int) -> str:
        if m == 0:
            return "zu Beginn"
        if m % 1440 == 0:
            return f"{m // 1440} Tag{'e' if m >= 2880 else ''}"
        if m % 60 == 0:
            return f"{m // 60} Std."
        return f"{m} Min."
    teile = [eins(m) for m in minuten]
    if not teile:
        return "ohne Erinnerung"
    text = " und ".join([", ".join(teile[:-1]), teile[-1]] if len(teile) > 1 else teile)
    return f"Erinnerung {text}" + ("" if teile == ["zu Beginn"] else " vorher")


def _feld(entwurf: dict, name: str, max_laenge: int, pflicht: bool = False) -> str:
    wert = entwurf.get(name)
    wert = " ".join(str(wert).split()) if wert not in (None, "") else ""
    if pflicht and not wert:
        raise TerminFehler(f"{name} fehlt")
    if len(wert) > max_laenge:
        raise TerminFehler(f"{name}: höchstens {max_laenge} Zeichen")
    return wert


def _zeitpunkt(wert, name: str) -> tuple[datetime, bool]:
    """'2026-11-05T08:45' (deutsche Zeit, wenn ohne Zone) oder '2026-11-05' (ganztägig)."""
    if not isinstance(wert, str) or not wert.strip():
        raise TerminFehler(f"{name} fehlt")
    wert = wert.strip()
    try:
        if len(wert) == 10:
            return datetime.combine(date.fromisoformat(wert), datetime.min.time(), ZONE), True
        z = datetime.fromisoformat(wert)
    except ValueError:
        raise TerminFehler(f"{name}: kein Datum: {wert!r}") from None
    return (z if z.tzinfo else z.replace(tzinfo=ZONE)), False


def _erinnerungen(wert, ganztags: bool) -> tuple[int, ...]:
    if wert is None:
        return ERINNERUNGEN_GANZTAGS if ganztags else ERINNERUNGEN
    if not isinstance(wert, list) or len(wert) > 3 or not all(isinstance(m, int) and not isinstance(m, bool)
                                                               for m in wert):
        raise TerminFehler("erinnerungen_min: Liste mit höchstens 3 ganzen Zahlen")
    if any(m < 0 or m > MAX_ERINNERUNG for m in wert):
        raise TerminFehler(f"erinnerungen_min: 0 bis {MAX_ERINNERUNG} Minuten")
    return tuple(sorted(set(wert), reverse=True))


def entwurf_pruefen(entwurf: dict, jetzt: datetime) -> tuple[Veranstaltung, str]:
    """Termin-Entwurf von Claude prüfen. Gibt Veranstaltung und Begründung zurück."""
    if not isinstance(entwurf, dict):
        raise TerminFehler("Entwurf ist kein JSON-Objekt")
    titel = _feld(entwurf, "titel", 120, pflicht=True)
    beginn, ganztags = _zeitpunkt(entwurf.get("beginn"), "beginn")
    notiz = [str(entwurf.get("notiz") or "").strip()]
    if entwurf.get("ende") in (None, ""):
        ende = beginn if ganztags else beginn + STANDARD_DAUER
        if not ganztags:
            notiz.append("Ende unbekannt, 1 Stunde eingetragen.")
    else:
        ende, ende_ganztags = _zeitpunkt(entwurf.get("ende"), "ende")
        if ende_ganztags != ganztags:
            raise TerminFehler("beginn und ende: beide mit Uhrzeit oder beide nur Datum")
    if ganztags:
        if not timedelta(0) <= ende - beginn <= timedelta(days=MAX_TAGE - 1):
            raise TerminFehler(f"ende: am selben Tag wie beginn oder bis zu {MAX_TAGE - 1} Tage danach")
    elif not timedelta(0) < ende - beginn <= MAX_DAUER:
        raise TerminFehler("ende: nach beginn, höchstens 24 Stunden")
    letzter = ende + timedelta(days=1) if ganztags else ende
    if letzter <= jetzt:
        raise TerminFehler("Termin liegt in der Vergangenheit")
    if len(notiz[0]) > 1000:
        raise TerminFehler("notiz: höchstens 1000 Zeichen")
    quelle = _feld(entwurf, "quelle", 300)
    if quelle:
        notiz.append(f"Quelle: {quelle}")
    v = Veranstaltung(titel, beginn, ende, _feld(entwurf, "ort", 300), "\n\n".join(t for t in notiz if t),
                      ganztags, _erinnerungen(entwurf.get("erinnerungen_min"), ganztags))
    return v, _feld(entwurf, "begruendung", 300)


def _vergleichsform(titel: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]", "", titel.lower())


def doppelt(v: Veranstaltung, vorhandene) -> bool:
    """Steht der Termin schon im Kalender? Gleicher Beginn (±15 min, ganztägig: gleicher Tag) und
    ein Titel im anderen enthalten. vorhandene: Objekte mit beginn, titel, ganztags (agentkit.kalender)."""
    eigener = _vergleichsform(v.titel)
    for t in vorhandene:
        if t.ganztags != v.ganztags:
            continue
        if v.ganztags:
            gleich = t.beginn.date() == v.beginn.date()
        else:
            gleich = abs(t.beginn - v.beginn) <= timedelta(minutes=15)
        anderer = _vergleichsform(t.titel)
        if gleich and anderer and eigener and (anderer in eigener or eigener in anderer):
            return True
    return False
