"""Kalender lesen (öffentliche iCloud-Links) und neue Termine eintragen (CalDAV).

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

Schreiben: eintragen(titel, beginn, ende, agent=...) legt einen NEUEN Termin in Jans
iCloud-Kalender an (CalDAV, PUT mit If-None-Match: *), ändert und löscht nie.
Zugang aus shared/.env: ICLOUD_APPLE_ID, ICLOUD_APP_PASSWORT (App-spezifisches
Passwort von appleid.apple.com) und ICLOUD_KALENDER (Anzeigename des Kalenders).
Fehlt etwas, oder passt der Name auf keinen oder mehrere Kalender: KalenderFehler,
nichts wird geraten. Steht unter der UID schon ein Termin: TerminSchonDa (nichts
überschrieben). Ohne uid wird sie fest aus Titel und Beginn gebildet (feste_uid),
derselbe Termin entsteht so nicht doppelt. Nur nach Freigabe aufrufen (Entwurfstyp
"termin"). ics(...) baut den Kalendertext, auch für .ics-Anhänge.
"""

import base64
import hashlib
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
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


# ---------- Schreiben: .ics-Text ----------

def feste_uid(titel: str, beginn: datetime | date, domain: str = "agenten") -> str:
    """Fest aus Titel und Beginn: derselbe Termin bekommt immer dieselbe UID."""
    return hashlib.sha1(f"{titel}|{beginn.isoformat()}".encode()).hexdigest()[:16] + "@" + domain


def _ics_wert(text: str) -> str:
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


def ics(titel: str, beginn: datetime, ende: datetime, uid: str, ort: str = "", beschreibung: str = "",
        ganztags: bool = False, erinnerungen: tuple[int, ...] = (), link: str = "",
        methode: str | None = "PUBLISH", jetzt: datetime | None = None) -> str:
    """Ein Termin als iCalendar-Text (CRLF, gefaltet).

    ganztags: nur die Daten zählen, ende ist der letzte Tag (einschließlich).
    erinnerungen: Minuten vor Beginn, je eine VALARM. methode=None für CalDAV
    (dort ist METHOD verboten), "PUBLISH" für .ics-Anhänge zum Antippen.
    """
    utc = "%Y%m%dT%H%M%SZ"
    jetzt = jetzt or datetime.now(timezone.utc)
    beschreibung = beschreibung + (f"\n\nLink: {link}" if link else "")
    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//agenten//agentkit//DE"]
    if methode:
        zeilen.append(f"METHOD:{methode}")
    zeilen += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{jetzt.astimezone(timezone.utc).strftime(utc)}"]
    if ganztags:
        zeilen += [f"DTSTART;VALUE=DATE:{beginn.strftime('%Y%m%d')}",
                   f"DTEND;VALUE=DATE:{(_als_datum(ende) + timedelta(days=1)).strftime('%Y%m%d')}"]
    else:
        zeilen += [f"DTSTART:{beginn.astimezone(timezone.utc).strftime(utc)}",
                   f"DTEND:{ende.astimezone(timezone.utc).strftime(utc)}"]
    zeilen.append(f"SUMMARY:{_ics_wert(titel)}")
    if ort:
        zeilen.append(f"LOCATION:{_ics_wert(ort)}")
    if link:
        zeilen.append(f"URL:{link}")
    if beschreibung.strip():
        zeilen.append(f"DESCRIPTION:{_ics_wert(beschreibung.strip())}")
    for minuten in erinnerungen:
        zeilen += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_ics_wert(titel)}",
                   f"TRIGGER:-PT{minuten}M", "END:VALARM"]
    zeilen += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(z for zeile in zeilen for z in _falten(zeile)) + "\r\n"


def _als_datum(wert: datetime | date) -> date:
    return wert.date() if isinstance(wert, datetime) else wert


def termin_pruefen(titel: str, beginn: datetime | date, ende: datetime | date, ganztags: bool,
                   erinnerungen: tuple[int, ...]) -> None:
    """Grobe Plausibilität vor dem Eintragen, sonst KalenderFehler."""
    if not titel.strip():
        raise KalenderFehler("Termin ohne Titel")
    if ganztags:
        if _als_datum(ende) < _als_datum(beginn):
            raise KalenderFehler("Ende liegt vor dem Beginn")
    else:
        if not (isinstance(beginn, datetime) and isinstance(ende, datetime)):
            raise KalenderFehler("Termin mit Uhrzeit braucht datetime für Beginn und Ende")
        if beginn.tzinfo is None or ende.tzinfo is None:
            raise KalenderFehler("Beginn und Ende brauchen eine Zeitzone")
        if ende <= beginn:
            raise KalenderFehler("Ende liegt nicht nach dem Beginn")
    if any(not isinstance(m, int) or isinstance(m, bool) or m < 0 for m in erinnerungen):
        raise KalenderFehler(f"Erinnerungen müssen Minuten >= 0 sein: {erinnerungen!r}")


# ---------- Schreiben: CalDAV ----------

CALDAV_URL = "https://caldav.icloud.com/"
CALDAV_DOMAIN = "icloud.com"  # Zugangsdaten gehen nur an diese Domain (und Unterdomains), nur https
MAX_WEITERLEITUNGEN = 5
DAV, CALDAV = "DAV:", "urn:ietf:params:xml:ns:caldav"
PROPFIND_PRINCIPAL = (b'<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:">'
                      b'<d:prop><d:current-user-principal/></d:prop></d:propfind>')
PROPFIND_HOME = (b'<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:" '
                 b'xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><c:calendar-home-set/></d:prop></d:propfind>')
PROPFIND_KALENDER = (b'<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:" '
                     b'xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop><d:displayname/><d:resourcetype/>'
                     b'<c:supported-calendar-component-set/></d:prop></d:propfind>')


class TerminSchonDa(KalenderFehler):
    """Unter dieser UID steht schon ein Termin im Kalender, nichts wurde überschrieben."""


def eintragen(titel: str, beginn: datetime | date, ende: datetime | date, *, agent: str, ort: str = "",
              notiz: str = "", uid: str | None = None, ganztags: bool = False,
              erinnerungen: tuple[int, ...] = (), config: dict[str, str] | None = None) -> str:
    """Neuen Termin in Jans iCloud-Kalender anlegen, gibt die UID zurück.

    agent: wer ihn anlegt, steht in der Notiz ("angelegt vom Uni-Agenten").
    config: statt shared/.env (Tests). Fehler: KalenderFehler, TerminSchonDa.
    """
    termin_pruefen(titel, beginn, ende, ganztags, tuple(erinnerungen))
    cfg = config if config is not None else lade_config(SHARED_DIR)
    fehlend = [k for k in ("ICLOUD_APPLE_ID", "ICLOUD_APP_PASSWORT", "ICLOUD_KALENDER") if not cfg.get(k)]
    if fehlend:
        raise KalenderFehler(f"Fehlende Werte in shared/.env: {', '.join(fehlend)}")
    zugang = (cfg["ICLOUD_APPLE_ID"], cfg["ICLOUD_APP_PASSWORT"])
    uid = uid or feste_uid(titel, beginn)
    vermerk = f"angelegt vom {agent[:1].upper()}{agent[1:]}-Agenten"
    text = ics(titel, beginn, ende, uid, ort=ort, beschreibung=f"{notiz.strip()}\n\n{vermerk}".strip(),
               ganztags=ganztags, erinnerungen=tuple(erinnerungen), methode=None)

    ziel = urllib.parse.urljoin(kalender_finden(zugang, cfg["ICLOUD_KALENDER"]),
                                urllib.parse.quote(uid, safe="") + ".ics")
    status, _, _ = _anfrage("PUT", ziel, zugang, text.encode(),
                            {"Content-Type": "text/calendar; charset=utf-8", "If-None-Match": "*"})
    if status == 412:
        raise TerminSchonDa(f"Termin steht schon im Kalender (UID {uid})")
    if status not in (200, 201, 204):
        raise KalenderFehler(f"Termin nicht angelegt: iCloud antwortet mit HTTP {status}")
    logger.info("Termin eingetragen: %s, %s (UID %s)", titel, beginn.isoformat(), uid)
    return uid


def kalender_finden(zugang: tuple[str, str], name: str) -> str:
    """URL des Kalenders mit diesem Anzeigenamen: principal -> calendar-home-set -> Kalender."""
    status, url, inhalt = _anfrage("PROPFIND", CALDAV_URL, zugang, PROPFIND_PRINCIPAL, {"Depth": "0"})
    _pruefe_207(status, "Anmeldung")
    principal = urllib.parse.urljoin(url, _href(inhalt, f"{{{DAV}}}current-user-principal"))
    status, url, inhalt = _anfrage("PROPFIND", principal, zugang, PROPFIND_HOME, {"Depth": "0"})
    _pruefe_207(status, "Kalenderliste")
    home = urllib.parse.urljoin(url, _href(inhalt, f"{{{CALDAV}}}calendar-home-set"))
    status, url, inhalt = _anfrage("PROPFIND", home, zugang, PROPFIND_KALENDER, {"Depth": "1"})
    _pruefe_207(status, "Kalenderliste")
    return urllib.parse.urljoin(url, kalender_waehlen(kalenderliste(inhalt), name))


def _pruefe_207(status: int, schritt: str) -> None:
    if status != 207:
        raise KalenderFehler(f"iCloud ({schritt}): unerwartete Antwort HTTP {status}")


def _xml(inhalt: bytes) -> ET.Element:
    try:
        return ET.fromstring(inhalt)
    except ET.ParseError as e:
        raise KalenderFehler(f"Antwort von iCloud nicht lesbar: {e}") from None


def _href(inhalt: bytes, eigenschaft: str) -> str:
    """Erste href unterhalb der Eigenschaft (z. B. current-user-principal) in einer Multistatus-Antwort."""
    for knoten in _xml(inhalt).iter(eigenschaft):
        href = knoten.find(f"{{{DAV}}}href")
        if href is not None and (href.text or "").strip():
            return href.text.strip()
    raise KalenderFehler(f"iCloud nennt keine Adresse für {eigenschaft.split('}')[-1]}")


def kalenderliste(inhalt: bytes) -> list[tuple[str, str]]:
    """(href, Anzeigename) aller Kalender mit Terminen (VEVENT) aus einer PROPFIND-Antwort (Depth 1)."""
    ergebnis = []
    for antwort in _xml(inhalt).iter(f"{{{DAV}}}response"):
        href = (antwort.findtext(f"{{{DAV}}}href") or "").strip()
        typ = antwort.find(f".//{{{DAV}}}resourcetype")
        if not href or typ is None or typ.find(f"{{{CALDAV}}}calendar") is None:
            continue
        komponenten = antwort.find(f".//{{{CALDAV}}}supported-calendar-component-set")
        if komponenten is not None and "VEVENT" not in {k.get("name") for k in komponenten}:
            continue  # z. B. Listen der Erinnerungen-App (nur VTODO)
        ergebnis.append((href, (antwort.findtext(f".//{{{DAV}}}displayname") or "").strip()))
    return ergebnis


def kalender_waehlen(kalender: list[tuple[str, str]], name: str) -> str:
    """href des Kalenders mit genau diesem Anzeigenamen, sonst KalenderFehler (nichts raten)."""
    treffer = [href for href, anzeige in kalender if anzeige == name.strip()]
    if len(treffer) == 1:
        return treffer[0]
    namen = ", ".join(sorted({a for _, a in kalender if a})) or "keine"
    if not treffer:
        raise KalenderFehler(f"Kein Kalender namens {name!r} (ICLOUD_KALENDER). Vorhanden: {namen}")
    raise KalenderFehler(f"{len(treffer)} Kalender heißen {name!r}, bitte einen umbenennen")


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Weiterleitungen prüft _anfrage selbst


_OEFFNER = urllib.request.build_opener(_KeineWeiterleitung)


def _host_erlaubt(url: str) -> bool:
    teile = urllib.parse.urlsplit(url)
    host = (teile.hostname or "").lower()
    return teile.scheme == "https" and (host == CALDAV_DOMAIN or host.endswith("." + CALDAV_DOMAIN))


def _anfrage(methode: str, url: str, zugang: tuple[str, str], daten: bytes,
             kopf: dict[str, str]) -> tuple[int, str, bytes]:
    """Eine CalDAV-Anfrage mit Basic-Auth, folgt Weiterleitungen nur innerhalb von icloud.com.

    Gibt (Status, endgültige URL, Inhalt) zurück. 401 und Netzfehler: KalenderFehler.
    """
    anmeldung = "Basic " + base64.b64encode(f"{zugang[0]}:{zugang[1]}".encode()).decode()
    for _ in range(MAX_WEITERLEITUNGEN + 1):
        if not _host_erlaubt(url):
            raise KalenderFehler(f"Adresse außerhalb von iCloud abgelehnt: {url}")
        anfrage = urllib.request.Request(url, data=daten, method=methode, headers={
            **kopf, "Authorization": anmeldung, "User-Agent": "agenten-kalender/1.0"})
        try:
            with _OEFFNER.open(anfrage, timeout=30) as antwort:
                return antwort.status, antwort.geturl(), antwort.read()
        except urllib.error.HTTPError as e:
            status, ziel = e.code, e.headers.get("Location")
            if status in (301, 302, 303, 307, 308) and ziel:
                url = urllib.parse.urljoin(url, ziel)
                continue
            if status == 401:
                raise KalenderFehler("iCloud lehnt die Anmeldung ab: ICLOUD_APPLE_ID oder "
                                     "ICLOUD_APP_PASSWORT prüfen") from None
            return status, url, e.read()
        except (OSError, ValueError) as e:
            raise KalenderFehler(f"iCloud nicht erreichbar: {e}") from None
    raise KalenderFehler("Zu viele Weiterleitungen bei iCloud")
