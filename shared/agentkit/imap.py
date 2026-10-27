"""Postfach per IMAP lesen, nur lesend (für uni und posteingang; Senden ist nicht Teil davon).

Der Ordner wird mit readonly geöffnet und Mails werden mit BODY.PEEK geholt,
damit nichts als gelesen markiert wird.

Neue Mails: Die Stand-Datei des Aufrufers merkt sich UIDVALIDITY und die höchste gesehene UID.
Beim ersten Lauf (oder wenn sich UIDVALIDITY ändert) wird nur diese Marke gesetzt,
alte Mails werden nicht nachgeholt.

    mails = imap.neue_mails(host, port, nutzer, kennwort, stand_datei=Path("data/postfach.json"))

Jede Mail ist ein dict (zerlege): uid, von, antwort_an, message_id, references, betreff, datum,
text (zusammengezogen, kurz), wortlaut (mit Absätzen, ohne zitierten Verlauf), anhaenge (Dateinamen).
"""

import email
import email.header
import email.policy
import email.utils
import imaplib
import json
import re
from html import unescape
from pathlib import Path

MAX_TEXT = 2000
MAX_WORTLAUT = 20_000
MAX_MAILS = 50


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


def zerlege(uid: int, roh: bytes) -> dict:
    n = email.message_from_bytes(roh, policy=email.policy.default)
    anhaenge = [_dekodiere(t.get_filename()) for t in n.iter_attachments() if t.get_filename()]
    datum = email.utils.parsedate_to_datetime(n["Date"]) if n["Date"] else None
    roh = _roh(n)
    return {
        "uid": uid,
        "von": _dekodiere(n["From"]),
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
