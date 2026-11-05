"""Mails aus dem HNEE-Postfach senden, nur nach Jans Freigabe. Prüfen, Anzeigen, Bauen und Senden macht
agentkit.mail; hier steht nur, was uni anders hat.

Ablauf ("Claude denkt, Python handelt"):
1. Claude schreibt einen Entwurf als JSON nach data/entwuerfe/<schluessel>/mail_<n>.json:
   {"an": ["..."], "cc": [], "betreff": "...", "text": "...", "antwort_auf_uid": 1234, "begruendung": "..."}
   antwort_auf_uid: UID einer Mail aus data/mails/ (optional, dann wird es eine Antwort im selben Gespräch).
2. pruefen holt dazu die Originalmail aus data/mails/ und prüft mit agentkit.mail.pruefen. Der Agent legt den
   Entwurf in die Freigabe (typ "mail"), Jan sieht genau anzeige(daten).
3. Nach der Freigabe sendet senden genau einmal über SMTP (mail.hnee.de:587, STARTTLS). Ohne eigene Einträge
   in uni/.env gelten der HNEE-Login und der Ordner "Gesendete Elemente" für die Kopie.

Ohne Netz testbar: pruefen, mail_merken, mail_holen (anzeige, wortlaut, bauen: Tests in agentkit).
"""

import json
import re
from pathlib import Path

from agentkit import mail as _mail
from agentkit.mail import MailFehler, anzeige, bauen, wortlaut  # noqa: F401 – für agent.py

HIER = Path(__file__).resolve().parent
MAILS = HIER / "data" / "mails"
GESENDET_ORDNER = "Gesendete Elemente"
ANHANG_ERWAEHNT = re.compile(r"\b(?:anh[aä]ng\w*|angeh[aä]ngt\w*|anbei|beigef[uü]gt\w*|beiliegend\w*|attachment\w*"
                             r"|h[aä]ng\w*\b[^.!?\n]{0,40}?\ban)\b", re.IGNORECASE)
ANHANG_FEHLT = "Im Text steht ein Anhang, an der Mail hängt aber keine Datei."


def pruefen(entwurf: dict, mails_ordner: Path = MAILS, original: dict | None = None, anhaenge=None) -> dict:
    """Prüft einen Entwurf von Claude; der Gesprächsbezug kommt aus original (Mail aus dem Suchkontext) oder,
    bei antwort_auf_uid, aus der abgelegten Mail. anhaenge: Dateien aus Jans Auftrag (relativ zum uni-Ordner)."""
    if original is None and isinstance(entwurf, dict) and entwurf.get("antwort_auf_uid") not in (None, ""):
        original = mail_holen(entwurf["antwort_auf_uid"], mails_ordner)
    return _mail.pruefen(entwurf, original, anhaenge=anhaenge, ordner=HIER)


def anhang_warnung(daten: dict) -> dict:
    """Erwähnt der Text einen Anhang, ohne dass eine Datei dabei ist, steht das unter "Bitte prüfen" in der Freigabe.
    Aufrufen, wenn die Anhänge feststehen, also auch die des Vorgängers übernommen sind."""
    if daten.get("anhaenge") or not ANHANG_ERWAEHNT.search(daten["text"]):
        return daten
    return {**daten, "pruefen": " ".join(filter(None, (ANHANG_FEHLT, daten.get("pruefen"))))}


def senden(cfg: dict, daten: dict) -> str:
    """agentkit.mail.senden mit den HNEE-Vorgaben (Login, Gesendet-Ordner), Einträge in .env gehen vor."""
    vorgaben = {"MAIL_NUTZER": cfg.get("HNEE_NUTZER"), "MAIL_KENNWORT": cfg.get("HNEE_KENNWORT"),
                "GESENDET_ORDNER": GESENDET_ORDNER}
    return _mail.senden({**vorgaben, **{k: v for k, v in cfg.items() if v}}, daten)


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
