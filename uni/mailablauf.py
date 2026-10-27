"""Mail-Entwürfe im Stil von Jans bisherigem Schriftwechsel (Ablauf wie posteingang, über agentkit.mailauftrag).

Rein, ohne Netz. agent.py verbindet es mit dem HNEE-Postfach (agentkit.imap.suchen) und dem Kalender.

Drei Wege führen zu einem Entwurf, alle laufen danach gleich (agent.mail_entwerfen):
1. Auftrag von Jan: prompt_erkennen lässt Claude entscheiden, ob der Auftrag nur eine Mail ist, und im selben
   Lauf die Suchbegriffe nennen (erkennen_lesen). Kein Mail-Auftrag: normaler Auftrag.
2. Mail-Wunsch aus einem anderen Lauf (Auftrag, neue Mails, Material): Claude schreibt nur
   data/entwuerfe/<schluessel>/mail_<n>.json mit {"auftrag": "...", "antwort_auf_uid": 1234}, Python sucht
   dann selbst Kontext und Stil und lässt den Entwurf schreiben (wunsch_lesen, original_einfuegen).
3. Ändern: mailauftrag.prompt_aendern mit dem gespeicherten Kontext, dazu optional ein Regelvorschlag (regel_aus).
"""

import json
from datetime import datetime

from agentkit import mailauftrag

UNI = mailauftrag.Postfach(
    agent="Uni-Agent",
    beschreibung="Hochschulpostfach jkl298@hnee.de an der HNE Eberswalde: Lehrende, Verwaltung, Kommilitonen",
    eingang=("INBOX", "Archive"), gesendet="Gesendete Elemente", max_tage_zurueck=1100, unterschrift=None)

MAX_WUNSCH = 3000

PROMPT_ERKENNEN = """Entscheide zuerst, ob Jans Auftrag unten nur darum geht, eine Mail zu schreiben oder zu
beantworten (z. B. "antworte Böhme auf seine Rückfragen", "schreib Henri wegen der Gruppe", "sag Frau X den
Termin ab"). Gehört mehr dazu (etwas nachschlagen, zusammenfassen, erklären, lernen, ein Dokument) oder geht es
gar nicht um eine Mail, antworte nur:
{"mail": false}
Geht es nur um eine Mail, antworte wie unten verlangt und füg dem JSON-Objekt "mail": true hinzu.

"""

REGEL_HINWEIS = """

Drückt Jans Kommentar eine allgemeine Regel aus (Ton, Anrede, Länge, an wen nicht), füg dem JSON-Objekt
zusätzlich "regel": {"regel": "eine Zeile", "anlass": "kurz"} hinzu. Jan bestätigt sie getrennt."""


class WunschFehler(Exception):
    """Ein Mail-Wunsch (mail_<n>.json mit "auftrag") hat nicht die verlangte Form."""


def _objekt(text: str):
    anfang, ende = text.find("{"), text.rfind("}")
    if anfang < 0 or ende < anfang:
        return None
    try:
        return json.loads(text[anfang:ende + 1])
    except json.JSONDecodeError:
        return None


def prompt_erkennen(text: str, heute) -> str:
    return PROMPT_ERKENNEN + mailauftrag.prompt_suche(text, heute, UNI)


def erkennen_lesen(text: str) -> dict | None:
    """Suchbegriffe, wenn Claude den Auftrag als Mail erkannt hat, sonst None.

    Unlesbare Antwort oder Mail ohne Suchbegriffe: mailauftrag.AuftragFehler.
    """
    roh = _objekt(text)
    if not isinstance(roh, dict):
        raise mailauftrag.AuftragFehler("Erkennung: kein JSON-Objekt")
    if roh.get("mail") is not True:
        return None
    return mailauftrag.suche_lesen(text, UNI)


def wunsch_lesen(roh) -> tuple[str, int | None]:
    """(auftrag, antwort_auf_uid) aus einem Mail-Wunsch."""
    if not isinstance(roh, dict):
        raise WunschFehler("kein JSON-Objekt")
    auftrag = str(roh.get("auftrag") or "").strip()
    if not auftrag or len(auftrag) > MAX_WUNSCH:
        raise WunschFehler(f"auftrag: 1 bis {MAX_WUNSCH} Zeichen")
    uid = roh.get("antwort_auf_uid")
    if uid in (None, ""):
        return auftrag, None
    try:
        return auftrag, int(uid)
    except (TypeError, ValueError):
        raise WunschFehler(f"antwort_auf_uid: keine Zahl: {uid!r}") from None


def original_einfuegen(kontext: dict, original: dict, ordner: str = "INBOX") -> str:
    """Die Mail, auf die geantwortet werden soll, sicher in den Kontext. Gibt ihren Schlüssel zurück.

    Findet die Suche sie schon (gleiche Message-ID), bleibt ihr Schlüssel, sonst kommt sie als m0 an den Anfang.
    """
    mid = (original.get("message_id") or "").strip()
    for m in kontext["mails"]:
        if mid and (m.get("message_id") or "").strip() == mid:
            return m["schluessel"]
    kontext["mails"].insert(0, {**original, "ordner": original.get("ordner") or ordner, "schluessel": "m0"})
    return "m0"


def wunsch_text(auftrag: str, original: dict | None, schluessel: str | None) -> str:
    """Auftragstext für prompt_entwurf: der Wunsch, bei einer Antwort mit Verweis auf die Mail im Kontext."""
    if not original:
        return auftrag
    datum = original.get("datum", "")
    try:
        datum = datetime.fromisoformat(datum).strftime("%d.%m.%Y")
    except ValueError:
        pass
    return (f"{auftrag}\n\nEs ist eine Antwort auf die Mail von {original.get('von', '')} vom {datum} "
            f"(Betreff: {original.get('betreff', '')}), im Kontext {schluessel}: antwort_auf = \"{schluessel}\".")


def regel_aus(text: str) -> dict | None:
    """{"regel", "anlass"} aus Claudes Antwort beim Ändern, sonst None."""
    roh = _objekt(text)
    r = roh.get("regel") if isinstance(roh, dict) else None
    if not isinstance(r, dict) or not str(r.get("regel") or "").strip():
        return None
    return {"regel": " ".join(str(r["regel"]).split()), "anlass": " ".join(str(r.get("anlass") or "").split())}
