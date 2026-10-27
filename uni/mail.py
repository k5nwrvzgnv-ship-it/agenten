"""Mails aus dem HNEE-Postfach senden, nur nach Jans Freigabe.

Ablauf ("Claude denkt, Python handelt"):
1. Claude schreibt einen Entwurf als JSON nach data/entwuerfe/<schluessel>/mail_<n>.json:
   {"an": ["..."], "cc": [], "betreff": "...", "text": "...", "antwort_auf_uid": 1234, "begruendung": "..."}
   antwort_auf_uid: UID einer Mail aus data/mails/ (optional, dann wird es eine Antwort im selben Gespräch).
2. Python prüft ihn (pruefen) und legt ihn in die Freigabe (agentkit.freigabe, typ "mail").
   Jan sieht in Telegram genau anzeige(daten) und tippt Freigeben, Ablehnen oder Ändern.
3. Nach der Freigabe baut Python die Mail aus den freigegebenen daten (bauen) und sendet sie einmal
   über SMTP (mail.hnee.de:587, STARTTLS, HNEE-Login), danach eine Kopie nach "Gesendete Elemente".

Ohne Netz testbar: pruefen, anzeige, wortlaut, bauen, mail_merken, mail_holen.
"""

import email.policy
import email.utils
import imaplib
import json
import re
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

HIER = Path(__file__).resolve().parent
MAILS = HIER / "data" / "mails"
MAX_EMPFAENGER = 5
MAX_BETREFF = 200
MAX_TEXT = 20_000
ADRESSE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


class MailFehler(Exception):
    pass


def _adressen(wert, feld: str) -> list[str]:
    if wert in (None, "", []):
        return []
    liste = [wert] if isinstance(wert, str) else wert
    if not isinstance(liste, list) or not all(isinstance(a, str) for a in liste):
        raise MailFehler(f"{feld}: Liste von Adressen erwartet")
    ergebnis = []
    for roh in liste:
        adresse = email.utils.parseaddr(roh)[1].strip()
        if not ADRESSE.match(adresse):
            raise MailFehler(f"{feld}: keine gültige Adresse: {roh!r}")
        if adresse.lower() not in (a.lower() for a in ergebnis):
            ergebnis.append(adresse)
    return ergebnis


def pruefen(entwurf: dict, mails_ordner: Path = MAILS) -> dict:
    """Prüft einen Entwurf von Claude und gibt die daten für die Freigabe zurück (nur bekannte Felder).

    Bei einer Antwort kommen In-Reply-To und References aus der gespeicherten Originalmail, nicht von Claude.
    """
    if not isinstance(entwurf, dict):
        raise MailFehler("Entwurf ist kein JSON-Objekt")
    an = _adressen(entwurf.get("an"), "an")
    cc = [a for a in _adressen(entwurf.get("cc"), "cc") if a.lower() not in (x.lower() for x in an)]
    if not an:
        raise MailFehler("an: mindestens ein Empfänger nötig")
    if len(an) + len(cc) > MAX_EMPFAENGER:
        raise MailFehler(f"höchstens {MAX_EMPFAENGER} Empfänger")
    betreff = " ".join(str(entwurf.get("betreff") or "").split())
    text = str(entwurf.get("text") or "").strip()
    if not betreff or len(betreff) > MAX_BETREFF:
        raise MailFehler(f"betreff: 1 bis {MAX_BETREFF} Zeichen")
    if not text or len(text) > MAX_TEXT:
        raise MailFehler(f"text: 1 bis {MAX_TEXT} Zeichen")
    daten = {"an": an, "cc": cc, "betreff": betreff, "text": text,
             "begruendung": " ".join(str(entwurf.get("begruendung") or "").split())}
    uid = entwurf.get("antwort_auf_uid")
    if uid not in (None, ""):
        original = mail_holen(uid, mails_ordner)
        if not original.get("message_id"):
            raise MailFehler(f"antwort_auf_uid {uid}: Originalmail ohne Message-ID")
        daten["in_reply_to"] = original["message_id"]
        daten["references"] = " ".join(x for x in (original.get("references"), original["message_id"]) if x)
        daten["antwort_auf"] = f"{original.get('von', '')}: {original.get('betreff', '')}"
    return daten


def anzeige(daten: dict) -> str:
    """Was Jan in Telegram sieht: Kopf und vollständiger Text."""
    zeilen = [f"An: {', '.join(daten['an'])}"]
    if daten.get("cc"):
        zeilen.append(f"Cc: {', '.join(daten['cc'])}")
    if daten.get("antwort_auf"):
        zeilen.append(f"Antwort auf: {daten['antwort_auf']}")
    zeilen += [f"Betreff: {daten['betreff']}", "", daten["text"]]
    if daten.get("begruendung"):
        zeilen += ["", f"(Warum: {daten['begruendung']})"]
    return "\n".join(zeilen)


def wortlaut(original: dict) -> str:
    """Die Originalmail als eigene Telegram-Nachricht (zum Lesen und Weiterleiten).

    Ältere abgelegte Mails haben nur den zusammengezogenen text ohne Absätze.
    """
    datum = original.get("datum", "")
    try:
        datum = datetime.fromisoformat(datum).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        pass
    zeilen = [f"Von: {original.get('von', '')}", f"Datum: {datum}", f"Betreff: {original.get('betreff', '')}"]
    if original.get("anhaenge"):
        zeilen.append(f"Anhänge: {', '.join(original['anhaenge'])}")
    return "\n".join(zeilen) + "\n\n" + (original.get("wortlaut") or original.get("text") or "(kein Text)")


def bauen(daten: dict, absender: str, name: str = "", jetzt: float | None = None) -> EmailMessage:
    msg = EmailMessage(policy=email.policy.SMTP)
    msg["From"] = email.utils.formataddr((name, absender)) if name else absender
    msg["To"] = ", ".join(daten["an"])
    if daten.get("cc"):
        msg["Cc"] = ", ".join(daten["cc"])
    msg["Subject"] = daten["betreff"]
    msg["Date"] = email.utils.formatdate(jetzt if jetzt is not None else time.time(), localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=absender.rpartition("@")[2])
    if daten.get("in_reply_to"):
        msg["In-Reply-To"] = daten["in_reply_to"]
        msg["References"] = daten.get("references") or daten["in_reply_to"]
    msg.set_content(daten["text"])
    return msg


def senden(cfg: dict, daten: dict) -> str:
    """Sendet genau einmal. Fehlschlag beim Ablegen in Gesendet ist kein Sendefehler."""
    absender = cfg.get("MAIL_ABSENDER")
    if not absender:
        raise MailFehler("MAIL_ABSENDER fehlt in uni/.env")
    msg = bauen(daten, absender, cfg.get("MAIL_NAME", ""))
    host = cfg.get("SMTP_HOST") or cfg["IMAP_HOST"]
    with smtplib.SMTP(host, int(cfg.get("SMTP_PORT", 587)), timeout=60) as smtp:
        smtp.starttls()
        smtp.login(cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"])
        abgelehnt = smtp.send_message(msg)
    if abgelehnt:
        raise MailFehler(f"Server hat Empfänger abgelehnt: {', '.join(abgelehnt)}")
    ergebnis = f"Mail gesendet an {', '.join(daten['an'] + daten.get('cc', []))}: {daten['betreff']}"
    try:
        with imaplib.IMAP4_SSL(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT", 993)), timeout=60) as imap:
            imap.login(cfg["HNEE_NUTZER"], cfg["HNEE_KENNWORT"])
            ordner = cfg.get("GESENDET_ORDNER", "Gesendete Elemente")
            imap.append(f'"{ordner}"', r"(\Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    except (OSError, imaplib.IMAP4.error) as f:
        ergebnis += f" (Kopie in Gesendet fehlgeschlagen: {type(f).__name__})"
    return ergebnis


def mail_merken(mail: dict, ordner: Path = MAILS) -> None:
    """Gelesene Mail ablegen (data/mails/<uid>.json), damit Claude darauf antworten kann."""
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / f"{int(mail['uid'])}.json").write_text(json.dumps(mail, ensure_ascii=False, indent=1))


def mail_holen(uid, ordner: Path = MAILS) -> dict:
    try:
        pfad = ordner / f"{int(uid)}.json"
    except (TypeError, ValueError):
        raise MailFehler(f"antwort_auf_uid: keine Zahl: {uid!r}") from None
    if not pfad.exists():
        raise MailFehler(f"antwort_auf_uid {uid}: Mail nicht in data/mails/")
    return json.loads(pfad.read_text())
