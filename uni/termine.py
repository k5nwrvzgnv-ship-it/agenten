"""Termine aus Links: Python lädt die Seite, liest Veranstaltungen aus und baut eine .ics-Datei.

Schickt Jan einen Link (z. B. Anmeldebestätigung eines Webinars), lädt seite_holen() die Seite
(nur lesend, höchstens MAX_BYTES). veranstaltungen() liest schema.org-Events aus den
<script type="application/ld+json">-Blöcken (auch subEvent einer EventSeries), seitentext() den
lesbaren Text für Claude. ics() baut daraus einen Kalendereintrag, den Jan in Telegram antippt
und in seinen Kalender übernimmt. In Jans Kalender schreibt der Agent nicht selbst.

Ohne Netz testbar: alles außer seite_holen().
"""

import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

MAX_BYTES = 2_000_000
MAX_TEXT = 6000
LINK = re.compile(r"https?://[^\s<>\"']+")
DAUER = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")
STANDARD_DAUER = timedelta(hours=1)
ZONE = ZoneInfo("Europe/Berlin")


class TerminFehler(Exception):
    pass


@dataclass
class Veranstaltung:
    titel: str
    beginn: datetime
    ende: datetime
    ort: str
    beschreibung: str


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
        f"DTSTART:{v.beginn.astimezone(timezone.utc).strftime(utc)}",
        f"DTEND:{v.ende.astimezone(timezone.utc).strftime(utc)}",
        f"SUMMARY:{_ics_text(v.titel)}",
    ]
    if v.ort:
        zeilen.append(f"LOCATION:{_ics_text(v.ort)}")
    if link:
        zeilen.append(f"URL:{link}")
    if beschreibung.strip():
        zeilen.append(f"DESCRIPTION:{_ics_text(beschreibung.strip())}")
    zeilen += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(z for zeile in zeilen for z in _falten(zeile)) + "\r\n"


def dateiname(v: Veranstaltung) -> str:
    kurz = re.sub(r"[^A-Za-z0-9]+", "_", v.titel).strip("_")[:40] or "termin"
    return f"{v.beginn.astimezone(ZONE).strftime('%Y-%m-%d')}_{kurz}.ics"


def beschreiben(v: Veranstaltung) -> str:
    """Eine Zeile für Prompt und Meldung, Zeiten deutscher Zeit."""
    tage = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    b, e = v.beginn.astimezone(ZONE), v.ende.astimezone(ZONE)
    bis = e.strftime("%H:%M") if e.date() == b.date() else e.strftime("%d.%m.%Y %H:%M")
    return f"{v.titel}: {tage[b.weekday()]} {b.strftime('%d.%m.%Y %H:%M')}-{bis} Uhr"
