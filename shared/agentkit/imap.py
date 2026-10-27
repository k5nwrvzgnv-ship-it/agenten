"""Postfach per IMAP lesen, nur lesend (für uni und posteingang; Senden ist nicht Teil davon).

Der Ordner wird mit readonly geöffnet und Mails werden mit BODY.PEEK geholt,
damit nichts als gelesen markiert wird.

Neue Mails: Die Stand-Datei des Aufrufers merkt sich UIDVALIDITY und die höchste gesehene UID.
Beim ersten Lauf (oder wenn sich UIDVALIDITY ändert) wird nur diese Marke gesetzt,
alte Mails werden nicht nachgeholt.

    mails = imap.neue_mails(host, port, nutzer, kennwort, stand_datei=Path("data/postfach.json"))

Suchen (ohne Stand-Datei, neueste zuerst, Kriterien per UND, Umlaute erlaubt):

    mails = imap.suchen(host, port, nutzer, kennwort, "Sent", an="frau@x.de", text="Termin",
                        seit=date(2026, 9, 1), max_mails=20)

Ein Ordner, den es nicht gibt, liefert eine leere Liste (mit Warnung im Log), keinen Fehler.
Jede gefundene Mail hat zusätzlich das Feld "ordner".

Server ohne CHARSET UTF-8 (Exchange der HNEE antwortet [BADCHARSET]): Es wird ohne CHARSET erneut
gesucht, Umlaute umgeschrieben (ö -> oe, ß -> ss). Weil TO dort nichts findet (und TEXT nur den
Mailtext), wird an= nicht dem Server gegeben: Python holt To/Cc der übrigen Treffer (höchstens
MAX_PRUEFEN, neueste zuerst) und prüft sie (Teilstring, Groß-/Kleinschreibung und Umlaute egal).

Jede Mail ist ein dict (zerlege): uid, von, an (To und Cc, Liste), antwort_an, message_id, references,
betreff, datum, text (zusammengezogen, kurz), wortlaut (mit Absätzen, ohne zitierten Verlauf),
anhaenge (Dateinamen).
"""

import email
import email.header
import email.policy
import email.utils
import imaplib
import json
import logging
import re
import unicodedata
from datetime import date
from html import unescape
from pathlib import Path

MAX_TEXT = 2000
MAX_WORTLAUT = 20_000
MAX_MAILS = 50
MAX_PRUEFEN = 1000  # höchstens so viele Köpfe prüfen, wenn an= in Python gefiltert wird
KOPF_BLOCK = 200
UMSCHRIFT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})
MONATE = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

logger = logging.getLogger("agentkit.imap")


def _dekodiere(wert: str | None) -> str:
    if not wert:
        return ""
    return str(email.header.make_header(email.header.decode_header(wert)))


# Beginn des zitierten Verlaufs (Outlook, Thunderbird, Apple Mail), ab hier gehört der Text nicht mehr zur Mail
ZITAT = re.compile(r"^(-{2,}\s*(Ursprüngliche Nachricht|Original Message)\s*-{2,}"
                   r"|(Von|From):\s.*\n+(Gesendet|Sent|Datum|Date):\s"
                   r"|Am .{5,120} schrieb .{1,200}:$|On .{5,120} wrote:$)", re.M | re.I)


def _roh(nachricht: email.message.Message) -> str:
    """Text der Mail mit Zeilenumbrüchen (HTML: Absätze und <br> werden Umbrüche)."""
    teil = nachricht.get_body(preferencelist=("plain", "html")) if hasattr(nachricht, "get_body") else None
    if teil is None:
        return ""
    try:
        inhalt = teil.get_content()
    except (LookupError, UnicodeDecodeError):
        inhalt = teil.get_payload(decode=True).decode("utf-8", "replace")
    if teil.get_content_subtype() == "html":
        inhalt = re.sub(r"<(script|style).*?</\1>", " ", inhalt, flags=re.S | re.I)
        inhalt = re.sub(r"<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", inhalt, flags=re.I)
        inhalt = unescape(re.sub(r"<[^>]+>", " ", inhalt))
    return inhalt


def wortlaut(roh: str) -> str:
    """Für Jan zum Lesen und Weiterleiten: Absätze bleiben, zitierter Verlauf fällt weg."""
    zeilen = [" ".join(z.split()) for z in roh.replace("\r\n", "\n").split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(zeilen)).strip()
    if m := ZITAT.search(text):
        text = text[:m.start()].rstrip() + "\n\n[älterer Verlauf weggelassen]"
    return text[:MAX_WORTLAUT]


def _text(roh: str) -> str:
    return re.sub(r"\s+", " ", roh).strip()[:MAX_TEXT]


def _kopf_liste(n: email.message.Message, name: str) -> list[str]:
    """Adressen eines Kopffelds (To, Cc) einzeln, so wie sie dort stehen."""
    werte = [str(w) for w in n.get_all(name, [])]
    return [email.utils.formataddr(p) for p in email.utils.getaddresses(werte) if p[1]]


def zerlege(uid: int, roh: bytes) -> dict:
    n = email.message_from_bytes(roh, policy=email.policy.default)
    anhaenge = [_dekodiere(t.get_filename()) for t in n.iter_attachments() if t.get_filename()]
    datum = email.utils.parsedate_to_datetime(n["Date"]) if n["Date"] else None
    roh = _roh(n)
    return {
        "uid": uid,
        "von": _dekodiere(n["From"]),
        "an": [_dekodiere(a) for a in (*_kopf_liste(n, "To"), *_kopf_liste(n, "Cc"))],
        "antwort_an": email.utils.parseaddr(_dekodiere(n["Reply-To"] or n["From"]))[1],
        "message_id": (n["Message-ID"] or "").strip(),
        "references": " ".join((n["References"] or "").split()),
        "betreff": _dekodiere(n["Subject"]),
        "datum": datum.isoformat() if datum else "",
        "text": _text(roh),
        "wortlaut": wortlaut(roh),
        "anhaenge": anhaenge,
    }


def _lies_stand(stand_datei: Path) -> dict:
    return json.loads(stand_datei.read_text()) if stand_datei.exists() else {}


def _schreibe_stand(stand_datei: Path, stand: dict) -> None:
    stand_datei.parent.mkdir(parents=True, exist_ok=True)
    tmp = stand_datei.with_suffix(".tmp")
    tmp.write_text(json.dumps(stand))
    tmp.replace(stand_datei)


def neue_mails(host: str, port: int, nutzer: str, kennwort: str, stand_datei: Path,
               ordner: str = "INBOX", max_mails: int = MAX_MAILS) -> list[dict]:
    """Mails seit dem letzten Aufruf, älteste zuerst (höchstens max_mails pro Aufruf).

    Die Marke wird erst nach erfolgreichem Holen weitergesetzt. Bricht der
    Aufrufer danach ab, sind diese Mails trotzdem "gesehen". Dafür kommt keine
    Mail doppelt.
    """
    with imaplib.IMAP4_SSL(host, int(port)) as imap:
        imap.login(nutzer, kennwort)
        imap.select(ordner, readonly=True)
        uidvalidity = int(re.search(rb"\d+", imap.response("UIDVALIDITY")[1][0]).group())
        _, daten = imap.uid("search", None, "ALL")
        uids = sorted(int(u) for u in daten[0].split())
        hoechste = uids[-1] if uids else 0

        stand = _lies_stand(stand_datei)
        if stand.get("uidvalidity") != uidvalidity:
            _schreibe_stand(stand_datei, {"uidvalidity": uidvalidity, "letzte_uid": hoechste})
            return []

        neue = [u for u in uids if u > stand["letzte_uid"]][:max_mails]
        mails = []
        for uid in neue:
            _, teile = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
            roh = next((t[1] for t in teile if isinstance(t, tuple)), None)
            if roh:
                mails.append(zerlege(uid, roh))
        if neue:
            _schreibe_stand(stand_datei, {"uidvalidity": uidvalidity, "letzte_uid": neue[-1]})
        return mails


def _wert(s: str, literal_plus: bool) -> bytes:
    """Suchwert für IMAP SEARCH: ASCII als quoted string, sonst UTF-8 als Literal (LITERAL+) bzw. quoted."""
    roh = s.encode("utf-8")
    if literal_plus and not s.isascii():
        return b"{%d+}\r\n" % len(roh) + roh
    return b'"' + roh.replace(b"\\", b"\\\\").replace(b'"', b'\\"') + b'"'


def umschreiben(s: str) -> str:
    """Nur ASCII für Server ohne CHARSET: Umlaute ausgeschrieben, andere Akzente weg (é -> e)."""
    s = unicodedata.normalize("NFKD", s.translate(UMSCHRIFT))
    return s.encode("ascii", "ignore").decode()


def kriterien(von: str | None = None, an: str | None = None, text: str | None = None,
              seit: date | None = None, literal_plus: bool = False, nur_ascii: bool = False) -> list[bytes]:
    """Argumente für UID SEARCH (alle Kriterien per UND, ohne Kriterium ALL).

    Standard: für CHARSET UTF-8. nur_ascii: für Server ohne CHARSET, Werte umgeschrieben.
    """
    teile = []
    for name, wert in ((b"FROM", von), (b"TO", an), (b"TEXT", text)):
        wert = umschreiben(wert) if nur_ascii and wert else wert
        if wert and wert.strip():
            teile.append(name + b" " + _wert(" ".join(wert.split()), literal_plus))
    if seit:
        teile.append(f"SINCE {seit.day:02d}-{MONATE[seit.month - 1]}-{seit.year}".encode())
    return teile or [b"ALL"]


def _ordnername(ordner: str) -> str:
    return ordner if ordner.startswith('"') else '"' + ordner.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _vergleich(s: str) -> str:
    return umschreiben(" ".join(s.split())).lower()


def _empfaenger(imap, uids: list[int]) -> dict[int, list[str]]:
    """To und Cc je UID, in Blöcken geholt (nur Kopfzeilen, BODY.PEEK)."""
    ergebnis = {}
    for i in range(0, len(uids), KOPF_BLOCK):
        menge = ",".join(str(u) for u in uids[i:i + KOPF_BLOCK])
        _, teile = imap.uid("fetch", menge, "(UID BODY.PEEK[HEADER.FIELDS (TO CC)])")
        for t in teile:
            if isinstance(t, tuple) and (m := re.search(rb"UID (\d+)", t[0])):
                n = email.message_from_bytes(t[1], policy=email.policy.default)
                ergebnis[int(m.group(1))] = [_dekodiere(a) for a in (*_kopf_liste(n, "To"), *_kopf_liste(n, "Cc"))]
    return ergebnis


def suchen(host: str, port: int, nutzer: str, kennwort: str, ordner: str, *, von: str | None = None,
           an: str | None = None, text: str | None = None, seit: date | None = None,
           max_mails: int = 20) -> list[dict]:
    """Mails in einem Ordner, die alle Kriterien erfüllen, neueste zuerst (höchstens max_mails).

    von/an/text: Teilstrings wie in IMAP SEARCH FROM/TO/TEXT (Groß-/Kleinschreibung egal, Umlaute erlaubt).
    seit: Datum (SINCE, nach Eingangsdatum des Servers). Nur lesend, keine Stand-Datei.
    "Neueste" heißt höchste UID, also zuletzt im Ordner angekommen.
    Lehnt der Server den Suchbefehl aus anderem Grund als BADCHARSET ab: imaplib.IMAP4.error.
    """
    with imaplib.IMAP4_SSL(host, int(port)) as imap:
        imap.login(nutzer, kennwort)
        typ, antwort = imap.select(_ordnername(ordner), readonly=True)
        if typ != "OK":
            logger.warning("Ordner %r nicht lesbar: %s", ordner, antwort[0] if antwort else typ)
            return []
        literal_plus = "LITERAL+" in getattr(imap, "capabilities", ())
        typ, daten = imap.uid("search", "CHARSET", "UTF-8", *kriterien(von, an, text, seit, literal_plus))
        an_filtern = False
        if typ != "OK" and b"BADCHARSET" in b" ".join(d for d in daten if isinstance(d, bytes)).upper():
            an_filtern = bool(an and an.strip())
            logger.info("Server kann kein CHARSET UTF-8, suche in %r ohne (Umlaute umgeschrieben%s)", ordner,
                        ", an in Python" if an_filtern else "")
            typ, daten = imap.uid("search", *kriterien(von, None if an_filtern else an, text, seit, nur_ascii=True))
        if typ != "OK":
            raise imaplib.IMAP4.error(f"SEARCH in {ordner!r} abgelehnt: {daten[0] if daten else typ!r}")
        uids = sorted((int(u) for u in (daten[0] or b"").split()), reverse=True)
        if an_filtern:
            gesucht, koepfe = _vergleich(an), _empfaenger(imap, uids[:MAX_PRUEFEN])
            uids = [u for u in uids[:MAX_PRUEFEN] if any(gesucht in _vergleich(a) for a in koepfe.get(u, []))]
        mails = []
        for uid in uids[:max(0, max_mails)]:
            _, teile = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
            roh = next((t[1] for t in teile if isinstance(t, tuple)), None)
            if roh:
                mails.append({**zerlege(uid, roh), "ordner": ordner})
        return mails
