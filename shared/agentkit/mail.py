"""Mails senden, nur nach Freigabe (verallgemeinert aus uni/mail.py, für posteingang und uni).

Ablauf ("Claude denkt, Python handelt"):
1. Claude schreibt einen Entwurf als JSON: {"an": ["..."], "cc": [], "betreff": "...", "text": "...",
   "begruendung": "...", "pruefen": "..."} (pruefen optional: eine offene Frage an Jan, z. B. "ob der Termin
   stimmt"; die Freigabe zeigt sie hervorgehoben). Soll es eine Antwort werden, sucht der Agent die Originalmail selbst heraus
   (ein dict wie agentkit.imap.zerlege, gebraucht werden message_id, references, von, betreff).
2. daten = mail.pruefen(entwurf, original) prüft ihn und gibt nur bekannte Felder zurück; In-Reply-To und
   References kommen aus dem Original, nicht von Claude. Der Agent legt daten in die Freigabe (typ "mail"),
   Jan sieht genau mail.anzeige(daten). mail.wortlaut(original) zeigt die Originalmail zum Nachlesen.
3. Nach der Freigabe: mail.senden(cfg, daten) baut die Mail (bauen) und sendet sie genau einmal,
   danach eine Kopie in den Gesendet-Ordner.

Anhänge bestimmt Python, nie Claude: mail.pruefen(entwurf, original, anhaenge=[...], ordner=<Agent-Ordner>) nimmt
die Dateien, die Jan dem Auftrag mitgegeben hat; ein Feld "anhaenge" in Claudes Entwurf wird ignoriert. Die daten
merken sich je Datei Pfad, Name, Größe und Prüfsumme. Weicht die Datei beim Senden ab, geht nichts raus: Gesendet
wird nur, was Jan freigegeben hat.

Werte in cfg (aus der .env des Agenten):
- MAIL_ABSENDER (Pflicht), MAIL_NAME (Anzeigename, optional)
- SMTP_HOST (Standard IMAP_HOST), SMTP_PORT (465: SMTP_SSL, sonst STARTTLS; Standard 587)
- MAIL_NUTZER/MAIL_KENNWORT für SMTP und IMAP (Standard IMAP_NUTZER/IMAP_KENNWORT)
- IMAP_HOST, IMAP_PORT (Standard 993), GESENDET_ORDNER (ohne Eintrag keine Kopie, das steht im Ergebnis)

Fehler im Entwurf oder beim Senden: MailFehler. Ohne Netz testbar: pruefen, anzeige, wortlaut, bauen.
"""

import email.policy
import email.utils
import hashlib
import imaplib
import mimetypes
import re
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from ._ablage import AblageFehler, anhaenge_pruefen

MAX_EMPFAENGER = 5
MAX_BETREFF = 200
MAX_TEXT = 20_000
MAX_PRUEFEN = 500
MAX_ANHAENGE = 5
MAX_ANHAENGE_BYTES = 15 * 1024 * 1024  # Limit des Servers unbekannt, Base64 macht die Mail ein Drittel größer
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


def _anhaenge(dateien, ordner) -> list[dict]:
    """Prüft die Dateien (agentkit._ablage.anhaenge_pruefen) und hält Pfad, Name, Größe und Prüfsumme fest."""
    dateien = list(dict.fromkeys(map(str, dateien or [])))
    if not dateien:
        return []
    if ordner is None:
        raise MailFehler("Anhänge ohne Agent-Ordner nicht möglich")
    if len(dateien) > MAX_ANHAENGE:
        raise MailFehler(f"höchstens {MAX_ANHAENGE} Anhänge")
    wurzel = Path(ordner).resolve()
    try:
        relativ = anhaenge_pruefen(wurzel, dateien)
    except AblageFehler as f:
        raise MailFehler(f"Anhang: {f}") from None
    ergebnis = []
    for pfad in (wurzel / r for r in relativ):
        inhalt = pfad.read_bytes()
        ergebnis.append({"pfad": str(pfad), "name": pfad.name, "groesse": len(inhalt),
                         "sha256": hashlib.sha256(inhalt).hexdigest()})
    if sum(a["groesse"] for a in ergebnis) > MAX_ANHAENGE_BYTES:
        raise MailFehler(f"Anhänge zusammen größer als {MAX_ANHAENGE_BYTES // 2**20} MB")
    return ergebnis


def anhang_zeile(anhang: dict) -> str:
    """'Exposé.pdf (112 KB)', für Anzeige und Freigabe."""
    groesse = anhang["groesse"]
    if groesse < 1024:
        text = f"{groesse} Byte"
    elif groesse < 1024 ** 2:
        text = f"{round(groesse / 1024)} KB"
    else:
        text = f"{groesse / 1024 ** 2:.1f} MB".replace(".", ",")
    return f"{anhang['name']} ({text})"


def pruefen(entwurf: dict, original: dict | None = None, anhaenge=None, ordner=None) -> dict:
    """Prüft einen Entwurf von Claude und gibt die daten für die Freigabe zurück (nur bekannte Felder).

    original: die Mail, auf die geantwortet wird (dict wie imap.zerlege), sonst None.
    anhaenge: Dateien, die mitgehen (von Python, nie aus Claudes Entwurf), relativ zu ordner (Agent-Ordner).
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
    pruefen_text = " ".join(str(entwurf.get("pruefen") or "").split())
    if len(pruefen_text) > MAX_PRUEFEN:
        raise MailFehler(f"pruefen: höchstens {MAX_PRUEFEN} Zeichen")
    if pruefen_text:
        daten["pruefen"] = pruefen_text
    if liste := _anhaenge(anhaenge, ordner):
        daten["anhaenge"] = liste
    if original is not None:
        if not isinstance(original, dict) or not str(original.get("message_id") or "").strip():
            raise MailFehler("Originalmail ohne Message-ID, Antwort nicht möglich")
        message_id = original["message_id"].strip()
        daten["in_reply_to"] = message_id
        daten["references"] = " ".join(x for x in (original.get("references"), message_id) if x)
        daten["antwort_auf"] = f"{original.get('von', '')}: {original.get('betreff', '')}"
        # nur für die Anzeige in der Freigabe (Name und Datum der Originalmail), gehen nicht mit raus
        daten["antwort_auf_von"] = str(original.get("von") or "")
        daten["antwort_auf_datum"] = str(original.get("datum") or "")
    return daten


def anzeige(daten: dict) -> str:
    """Kopf, Text und Begründung als Klartext (inhalt des Entwurfs). Telegram zeigt Mails aus den daten
    (shared/telegram/logik.py, entwurf_als_text)."""
    zeilen = [f"An: {', '.join(daten['an'])}"]
    if daten.get("cc"):
        zeilen.append(f"Cc: {', '.join(daten['cc'])}")
    if daten.get("antwort_auf"):
        zeilen.append(f"Antwort auf: {daten['antwort_auf']}")
    zeilen.append(f"Betreff: {daten['betreff']}")
    zeilen += [f"Anhang: {anhang_zeile(a)}" for a in daten.get("anhaenge") or []]
    zeilen += ["", daten["text"]]
    if daten.get("begruendung"):
        zeilen += ["", f"(Warum: {daten['begruendung']})"]
    if daten.get("pruefen"):
        zeilen += ["", f"Bitte prüfen: {daten['pruefen']}"]
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


def _anhang_lesen(anhang: dict) -> bytes:
    """Der Inhalt, den Jan freigegeben hat. Fehlt die Datei oder hat sie sich geändert: MailFehler."""
    try:
        inhalt = Path(anhang["pfad"]).read_bytes()
    except OSError as f:
        raise MailFehler(f"Anhang {anhang['name']} nicht lesbar ({type(f).__name__}), nichts gesendet") from None
    if hashlib.sha256(inhalt).hexdigest() != anhang["sha256"]:
        raise MailFehler(f"Anhang {anhang['name']} hat sich seit der Freigabe geändert, nichts gesendet")
    return inhalt


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
    for anhang in daten.get("anhaenge") or []:
        typ = mimetypes.guess_type(anhang["name"])[0] or "application/octet-stream"
        haupt, _, unter = typ.partition("/")
        msg.add_attachment(_anhang_lesen(anhang), maintype=haupt, subtype=unter, filename=anhang["name"])
    return msg


def _login(cfg: dict) -> tuple[str, str]:
    nutzer = cfg.get("MAIL_NUTZER") or cfg.get("IMAP_NUTZER")
    kennwort = cfg.get("MAIL_KENNWORT") or cfg.get("IMAP_KENNWORT")
    if not nutzer or not kennwort:
        raise MailFehler("MAIL_NUTZER/MAIL_KENNWORT (oder IMAP_NUTZER/IMAP_KENNWORT) fehlen in .env")
    return nutzer, kennwort


def senden(cfg: dict, daten: dict) -> str:
    """Sendet genau einmal. Fehlschlag beim Ablegen in Gesendet ist kein Sendefehler."""
    absender = cfg.get("MAIL_ABSENDER")
    if not absender:
        raise MailFehler("MAIL_ABSENDER fehlt in .env")
    host = cfg.get("SMTP_HOST") or cfg.get("IMAP_HOST")
    if not host:
        raise MailFehler("SMTP_HOST (oder IMAP_HOST) fehlt in .env")
    nutzer, kennwort = _login(cfg)
    msg = bauen(daten, absender, cfg.get("MAIL_NAME", ""))
    port = int(cfg.get("SMTP_PORT") or 587)
    if port == 465:
        smtp = smtplib.SMTP_SSL(host, port, timeout=60)
    else:
        smtp = smtplib.SMTP(host, port, timeout=60)
    with smtp:
        if port != 465:
            smtp.starttls()
        smtp.login(nutzer, kennwort)
        abgelehnt = smtp.send_message(msg)
    if abgelehnt:
        raise MailFehler(f"Server hat Empfänger abgelehnt: {', '.join(abgelehnt)}")
    ergebnis = f"Mail gesendet an {', '.join(daten['an'] + daten.get('cc', []))}: {daten['betreff']}"
    if daten.get("anhaenge"):
        ergebnis += f" (Anhang: {', '.join(anhang_zeile(a) for a in daten['anhaenge'])})"
    ordner = cfg.get("GESENDET_ORDNER")
    if not ordner or not cfg.get("IMAP_HOST"):
        return ergebnis + " (keine Kopie in Gesendet: GESENDET_ORDNER oder IMAP_HOST fehlt)"
    try:
        with imaplib.IMAP4_SSL(cfg["IMAP_HOST"], int(cfg.get("IMAP_PORT") or 993), timeout=60) as imap:
            imap.login(nutzer, kennwort)
            typ, _ = imap.append(f'"{ordner}"', r"(\Seen)", imaplib.Time2Internaldate(time.time()),
                                 msg.as_bytes())
            if typ != "OK":
                ergebnis += f" (Kopie in Gesendet abgelehnt: {typ})"
    except (OSError, imaplib.IMAP4.error) as f:
        ergebnis += f" (Kopie in Gesendet fehlgeschlagen: {type(f).__name__})"
    return ergebnis
