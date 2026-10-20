"""Kalender lesen: Jans Apple-Kalender über öffentliche iCloud-Links (nur lesend).

Die Links stehen Komma-getrennt in KALENDER_ICS_URLS (shared/.env), webcal:// wird
zu https://. termine(von, bis) liefert alle Termine, die den Zeitraum berühren,
nach Beginn sortiert, Zeiten immer mit Zeitzone (Europe/Berlin, falls der Termin
keine eigene angibt).

Nur Python-Bordmittel. Unterstützt: Zeiten mit TZID, in UTC, ohne Zone und
ganztägig; DTEND oder DURATION; Wiederholungen DAILY, WEEKLY (mit BYDAY), MONTHLY
(mit BYMONTHDAY), YEARLY, jeweils mit INTERVAL, COUNT, UNTIL; RDATE, EXDATE,
einzeln geänderte Termine (RECURRENCE-ID) und abgesagte (STATUS:CANCELLED).
Unbekannte Regelteile: nur der erste Termin zählt, und es wird gewarnt.

Ohne Netz testbar: aus_text(ics_text, von, bis).
"""

import logging
import re
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import SHARED_DIR, lade_config

ZONE = ZoneInfo("Europe/Berlin")
MAX_WIEDERHOLUNGEN = 5000  # Schutz gegen endlose Regeln ohne UNTIL/COUNT
WOCHENTAGE = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
BEKANNTE_REGELTEILE = {
    "DAILY": {"FREQ", "INTERVAL", "COUNT", "UNTIL", "WKST"},
    "WEEKLY": {"FREQ", "INTERVAL", "COUNT", "UNTIL", "WKST", "BYDAY"},
    "MONTHLY": {"FREQ", "INTERVAL", "COUNT", "UNTIL", "WKST", "BYMONTHDAY"},
    "YEARLY": {"FREQ", "INTERVAL", "COUNT", "UNTIL", "WKST"},
}

logger = logging.getLogger("agentkit.kalender")


class KalenderFehler(Exception):
    pass


@dataclass(frozen=True)
class Termin:
    beginn: datetime
    ende: datetime
    titel: str
    ort: str
    ganztags: bool
    uid: str


def termine(von: datetime, bis: datetime, urls: list[str] | None = None) -> list[Termin]:
    """Termine aller Kalender im Zeitraum [von, bis). Ohne urls: KALENDER_ICS_URLS aus shared/.env."""
    if urls is None:
        wert = lade_config(SHARED_DIR).get("KALENDER_ICS_URLS", "")
        urls = [u.strip() for u in wert.split(",") if u.strip()]
    if not urls:
        raise KalenderFehler("KALENDER_ICS_URLS ist leer")
    ergebnis = []
    for nr, url in enumerate(urls, 1):
        ergebnis += aus_text(_laden(url, nr), von, bis)
    return sorted(ergebnis, key=lambda t: (t.beginn, t.titel))


def _laden(url: str, nr: int) -> str:
    # Die Adresse ist ein geheimer Link: in Fehlern nur die Nummer nennen.
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    try:
        with urllib.request.urlopen(url, timeout=30) as antwort:
            return antwort.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise KalenderFehler(f"Kalender {nr} nicht abrufbar: {e}") from None


# ---------- Zerlegen ----------

def _zeilen(text: str) -> list[tuple[str, dict[str, str], str]]:
    """Entfaltete Zeilen als (NAME, {PARAM: wert}, wert)."""
    text = re.sub(r"\r?\n[ \t]", "", text)
    zeilen = []
    for zeile in text.splitlines():
        kopf, doppelpunkt, wert = zeile.partition(":")
        if not doppelpunkt:
            continue
        name, *params = kopf.split(";")
        zeilen.append((name.upper(), dict(p.split("=", 1) for p in params if "=" in p), wert))
    return zeilen


def _ereignisse(text: str) -> list[list[tuple[str, dict, str]]]:
    """Die Zeilen jedes VEVENT (VTIMEZONE und VALARM bleiben außen vor)."""
    ereignisse, aktuell, tiefe = [], None, 0
    for name, params, wert in _zeilen(text):
        if name == "BEGIN" and wert.upper() == "VEVENT":
            aktuell, tiefe = [], 0
        elif aktuell is None:
            continue
        elif name == "BEGIN":
            tiefe += 1
        elif name == "END" and wert.upper() == "VEVENT":
            ereignisse.append(aktuell)
            aktuell = None
        elif name == "END":
            tiefe -= 1
        elif tiefe == 0:
            aktuell.append((name, params, wert))
    return ereignisse


def _text(wert: str) -> str:
    return re.sub(r"\\([nN\\;,])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), wert)


def _zone(params: dict) -> ZoneInfo:
    tzid = params.get("TZID", "").strip('"')
    if not tzid:
        return ZONE
    try:
        return ZoneInfo(tzid)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("Unbekannte Zeitzone %r, nehme %s", tzid, ZONE.key)
        return ZONE


def _zeitpunkt(wert: str, params: dict) -> tuple[datetime, bool]:
    """(Zeitpunkt mit Zone, ganztägig). Ganztägig heißt: 0 Uhr in ZONE."""
    wert = wert.strip()
    if params.get("VALUE") == "DATE" or len(wert) == 8:
        return datetime.combine(datetime.strptime(wert, "%Y%m%d").date(), time(), ZONE), True
    if wert.endswith("Z"):
        return datetime.strptime(wert, "%Y%m%dT%H%M%SZ").replace(tzinfo=ZoneInfo("UTC")), False
    return datetime.strptime(wert, "%Y%m%dT%H%M%S").replace(tzinfo=_zone(params)), False


def _dauer(wert: str) -> timedelta:
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", wert.strip())
    if not m:
        raise ValueError(f"Unbekannte Dauer {wert!r}")
    w, d, h, mi, s = (int(x or 0) for x in m.groups()[1:])
    dauer = timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)
    return -dauer if m.group(1) == "-" else dauer


def _liste(zeilen, name: str) -> list[datetime]:
    werte = []
    for n, params, wert in zeilen:
        if n == name and params.get("VALUE") != "PERIOD":
            werte += [_zeitpunkt(w, params)[0] for w in wert.split(",") if w.strip()]
    return werte


# ---------- Wiederholungen ----------

def _plus_monate(d: date, monate: int, tag: int) -> date | None:
    jahr, monat = divmod(d.month - 1 + monate, 12)
    try:
        return date(d.year + jahr, monat + 1, tag)
    except ValueError:  # 31. im Februar usw.: diesen Monat gibt es den Tag nicht
        return None


def _tage(start: date, regel: dict[str, str], bis: date):
    """Tage der Wiederholung ab start (inklusive), aufsteigend, höchstens bis."""
    freq = regel["FREQ"]
    schritt = int(regel.get("INTERVAL", "1"))
    if freq == "DAILY":
        tag = start
        while tag <= bis:
            yield tag
            tag += timedelta(days=schritt)
    elif freq == "WEEKLY":
        tage = sorted({WOCHENTAGE.index(t[-2:]) for t in regel["BYDAY"].split(",")} if "BYDAY" in regel
                      else {start.weekday()})
        montag = start - timedelta(days=start.weekday())
        while montag <= bis:
            for t in tage:
                tag = montag + timedelta(days=t)
                if start <= tag <= bis:
                    yield tag
            montag += timedelta(weeks=schritt)
    elif freq in ("MONTHLY", "YEARLY"):
        monate = schritt * (12 if freq == "YEARLY" else 1)
        tage = sorted(int(t) for t in regel["BYMONTHDAY"].split(",")) if "BYMONTHDAY" in regel else [start.day]
        n = 0
        while (erster := _plus_monate(start, n, 1)) and erster <= bis:
            for t in tage:
                tag = _plus_monate(start, n, t)
                if tag and start <= tag <= bis:
                    yield tag
            n += monate


def _wiederholungen(beginn: datetime, rrule: str, bis: datetime, uid: str) -> list[datetime]:
    regel = dict(teil.split("=", 1) for teil in rrule.upper().split(";") if "=" in teil)
    freq = regel.get("FREQ", "")
    unbekannt = set(regel) - BEKANNTE_REGELTEILE.get(freq, set())
    if freq not in BEKANNTE_REGELTEILE or unbekannt or any(re.match(r"[+-]?\d", t) for t in
                                                           regel.get("BYDAY", "").split(",") if t):
        logger.warning("Wiederholung von %s nicht unterstützt (%s), nur erster Termin", uid, rrule)
        return [beginn]
    ende = bis
    if "UNTIL" in regel:
        until = regel["UNTIL"]
        if len(until) == 8:  # nur Datum: der ganze Tag zählt noch
            grenze = datetime.combine(datetime.strptime(until, "%Y%m%d").date(), time(23, 59, 59), beginn.tzinfo)
        else:
            grenze = _zeitpunkt(until, {})[0] if until.endswith("Z") else \
                datetime.strptime(until, "%Y%m%dT%H%M%S").replace(tzinfo=beginn.tzinfo)
        ende = min(ende, grenze)
    anzahl = int(regel["COUNT"]) if "COUNT" in regel else None
    zeiten = []
    for tag in _tage(beginn.date(), regel, ende.astimezone(beginn.tzinfo).date()):
        zeit = datetime.combine(tag, beginn.timetz())  # gleiche Uhrzeit vor Ort, auch über die Zeitumstellung
        if zeit > ende or len(zeiten) >= MAX_WIEDERHOLUNGEN or (anzahl is not None and len(zeiten) >= anzahl):
            break
        zeiten.append(zeit)
    if len(zeiten) >= MAX_WIEDERHOLUNGEN:
        logger.warning("Wiederholung von %s nach %d Terminen abgeschnitten", uid, MAX_WIEDERHOLUNGEN)
    return zeiten


# ---------- Zusammensetzen ----------

def aus_text(text: str, von: datetime, bis: datetime) -> list[Termin]:
    """Termine aus einem iCalendar-Text, die den Zeitraum [von, bis) berühren, nach Beginn sortiert."""
    von, bis = (z if z.tzinfo else z.replace(tzinfo=ZONE) for z in (von, bis))
    ereignisse = _ereignisse(text)
    geaendert = {(_wert(e, "UID"), _liste(e, "RECURRENCE-ID")[0]) for e in ereignisse if _liste(e, "RECURRENCE-ID")}
    ergebnis = []
    for e in ereignisse:
        uid = _wert(e, "UID")
        if _wert(e, "STATUS").upper() == "CANCELLED":
            continue
        try:
            ergebnis += _termine_eines(e, uid, von, bis, geaendert)
        except (ValueError, KeyError) as f:
            logger.warning("Termin %s übersprungen: %s", uid or "?", f)
    return sorted(ergebnis, key=lambda t: (t.beginn, t.titel))


def _wert(zeilen, name: str) -> str:
    return next((w for n, _, w in zeilen if n == name), "")


def _termine_eines(e, uid: str, von: datetime, bis: datetime, geaendert: set) -> list[Termin]:
    start = next((z for z in e if z[0] == "DTSTART"), None)
    if start is None:
        raise ValueError("kein DTSTART")
    _, start_params, start_wert = start
    beginn, ganztags = _zeitpunkt(start_wert, start_params)
    ende_zeile = next((z for z in e if z[0] == "DTEND"), None)
    if ende_zeile:
        dauer = _zeitpunkt(ende_zeile[2], ende_zeile[1])[0] - beginn
    elif _wert(e, "DURATION"):
        dauer = _dauer(_wert(e, "DURATION"))
    else:
        dauer = timedelta(days=1) if ganztags else timedelta()

    rrule = _wert(e, "RRULE")
    if rrule and not _liste(e, "RECURRENCE-ID"):
        zeiten = _wiederholungen(beginn, rrule, bis, uid)
    else:
        zeiten = [beginn]
    zeiten += _liste(e, "RDATE")
    weg = set(_liste(e, "EXDATE"))
    if not _liste(e, "RECURRENCE-ID"):  # einzeln geänderte Termine stehen als eigenes VEVENT
        weg |= {z for u, z in geaendert if u == uid}

    titel, ort = _text(_wert(e, "SUMMARY")), _text(_wert(e, "LOCATION"))
    termine_ = []
    for zeit in sorted(set(zeiten)):
        if zeit in weg:
            continue
        if ganztags:  # 0 Uhr bleibt 0 Uhr, auch über die Zeitumstellung
            ende = datetime.combine(zeit.date() + timedelta(days=dauer.days), time(), ZONE)
        else:
            ende = zeit + dauer
        if zeit < bis and (ende > von or (ende == zeit and zeit >= von)):
            termine_.append(Termin(zeit.astimezone(ZONE), ende.astimezone(ZONE), titel, ort, ganztags, uid))
    return termine_
