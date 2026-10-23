"""Unipostfach (Exchange der HNEE) per IMAP lesen. Nur lesend (Senden: mail.py, nur nach Freigabe).

Der Posteingang wird mit readonly geöffnet und Mails werden mit BODY.PEEK geholt,
damit nichts als gelesen markiert wird.

Neue Mails: data/postfach.json merkt sich UIDVALIDITY und die höchste gesehene UID.
Beim ersten Lauf (oder wenn sich UIDVALIDITY ändert) wird nur diese Marke gesetzt,
alte Mails werden nicht nachgeholt (am 16.10.2026 rund 6000 Mails, über 5000 ungelesen).
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

HIER = Path(__file__).resolve().parent
STAND_DATEI = HIER / "data" / "postfach.json"
MAX_TEXT = 2000
MAX_MAILS = 50


def _dekodiere(wert: str | None) -> str:
    if not wert:
        return ""
    return str(email.header.make_header(email.header.decode_header(wert)))


def _text(nachricht: email.message.Message) -> str:
    teil = nachricht.get_body(preferencelist=("plain", "html")) if hasattr(nachricht, "get_body") else None
    if teil is None:
        return ""
    try:
        inhalt = teil.get_content()
    except (LookupError, UnicodeDecodeError):
        inhalt = teil.get_payload(decode=True).decode("utf-8", "replace")
    if teil.get_content_subtype() == "html":
        inhalt = unescape(re.sub(r"<(script|style).*?</\1>|<[^>]+>", " ", inhalt, flags=re.S | re.I))
    return re.sub(r"\s+", " ", inhalt).strip()[:MAX_TEXT]


def zerlege(uid: int, roh: bytes) -> dict:
    n = email.message_from_bytes(roh, policy=email.policy.default)
    anhaenge = [_dekodiere(t.get_filename()) for t in n.iter_attachments() if t.get_filename()]
    datum = email.utils.parsedate_to_datetime(n["Date"]) if n["Date"] else None
    return {
        "uid": uid,
        "von": _dekodiere(n["From"]),
        "antwort_an": email.utils.parseaddr(_dekodiere(n["Reply-To"] or n["From"]))[1],
        "message_id": (n["Message-ID"] or "").strip(),
        "references": " ".join((n["References"] or "").split()),
        "betreff": _dekodiere(n["Subject"]),
        "datum": datum.isoformat() if datum else "",
        "text": _text(n),
        "anhaenge": anhaenge,
    }


def _lies_stand() -> dict:
    return json.loads(STAND_DATEI.read_text()) if STAND_DATEI.exists() else {}


def _schreibe_stand(stand: dict) -> None:
    STAND_DATEI.parent.mkdir(exist_ok=True)
    tmp = STAND_DATEI.with_suffix(".tmp")
    tmp.write_text(json.dumps(stand))
    tmp.replace(STAND_DATEI)


def neue_mails(cfg: dict) -> list[dict]:
    """Mails seit dem letzten Aufruf, älteste zuerst (höchstens MAX_MAILS pro Aufruf).

    Die Marke wird erst nach erfolgreichem Holen weitergesetzt. Bricht der
    Aufrufer danach ab, sind diese Mails trotzdem "gesehen". Dafür kommt keine
    Mail doppelt.
    """
    with imaplib.IMAP4_SSL(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993))) as imap:
        imap.login(cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"])
        imap.select("INBOX", readonly=True)
        uidvalidity = int(re.search(rb"\d+", imap.response("UIDVALIDITY")[1][0]).group())
        _, daten = imap.uid("search", None, "ALL")
        uids = sorted(int(u) for u in daten[0].split())
        hoechste = uids[-1] if uids else 0

        stand = _lies_stand()
        if stand.get("uidvalidity") != uidvalidity:
            _schreibe_stand({"uidvalidity": uidvalidity, "letzte_uid": hoechste})
            return []

        neue = [u for u in uids if u > stand["letzte_uid"]][:MAX_MAILS]
        mails = []
        for uid in neue:
            _, teile = imap.uid("fetch", str(uid), "(BODY.PEEK[])")
            roh = next((t[1] for t in teile if isinstance(t, tuple)), None)
            if roh:
                mails.append(zerlege(uid, roh))
        if neue:
            _schreibe_stand({"uidvalidity": uidvalidity, "letzte_uid": neue[-1]})
        return mails
