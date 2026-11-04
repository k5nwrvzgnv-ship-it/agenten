"""Schriftverkehr eines Projekts: Auszug aus dem Postfach, nur mit den eingetragenen Kontaktpersonen, für das Portal.

Das Portal bekommt keinen Zugang zum Postfach und liest data/mails nicht. Es sieht nur diesen Auszug. Der Agent
sucht lesend (agentkit.imap: readonly, BODY.PEEK) und schreibt je Projekt:

  data/projekte/<projekt>/kontakte.json        {"seit": "JJJJ-MM-TT", "kontakte": [{"name": ..., "adresse": ...}]}
  data/projekte/<projekt>/schriftverkehr.json  {"stand", "seit", "gekappt", "kontakte", "mails"}

Nur Mails ab "seit": Mit einer Kontaktperson kann es auch älteren Schriftwechsel geben, der nicht zum Projekt gehört.
Schlägt eine Suche fehl, bleibt der alte Auszug stehen (agent.py meldet den Fehler des Schritts).
"""

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MAX_JE_SUCHE = 50
ZONE = ZoneInfo("Europe/Berlin")
ADRESSE = re.compile(r"^[^@\s<>\"',;]+@[^@\s<>\"',;]+\.[^@\s<>\"',;]+$")


class KontakteFehler(Exception):
    """kontakte.json hat nicht die verlangte Form."""


def kontakte_lesen(datei: Path) -> tuple[date, list[dict]]:
    daten = json.loads(Path(datei).read_text(encoding="utf-8"))
    try:
        seit = date.fromisoformat(daten["seit"])
    except (KeyError, TypeError, ValueError) as f:
        raise KontakteFehler(f"{datei}: seit fehlt oder ist kein Datum") from f
    kontakte = []
    for k in daten.get("kontakte") or []:
        adresse = str(k.get("adresse") or "").strip().lower() if isinstance(k, dict) else ""
        if not ADRESSE.match(adresse):  # eine Teiladresse würde bei der Suche fremde Mails treffen
            raise KontakteFehler(f"{datei}: ungültige Adresse {adresse!r}")
        kontakte.append({"name": str(k.get("name") or adresse), "adresse": adresse})
    return seit, kontakte


def _ortszeit(datum) -> str:
    """Datum der Mail in deutscher Zeit, damit die Reihenfolge stimmt. Unlesbar: leer (steht dann unten)."""
    try:
        wert = datetime.fromisoformat(str(datum))
    except ValueError:
        return ""
    return (wert if wert.tzinfo is None else wert.astimezone(ZONE)).strftime("%Y-%m-%dT%H:%M")


def _eintrag(mail: dict, kontakt: dict, richtung: str) -> dict:
    return {"kontakt": kontakt["adresse"], "richtung": richtung, "von": str(mail.get("von") or ""),
            "an": [str(a) for a in mail.get("an") or []], "betreff": str(mail.get("betreff") or "").strip(),
            "datum": _ortszeit(mail.get("datum")), "text": str(mail.get("wortlaut") or mail.get("text") or ""),
            "anhaenge": [str(a) for a in mail.get("anhaenge") or []]}


def auszug_bauen(seit: date, kontakte: list[dict], suchen, eingang: tuple[str, ...], gesendet: str, jetzt: datetime) -> dict:
    """suchen(ordner, von=, an=, seit=, max_mails=) wie agentkit.imap.suchen. Doppelte (gleiche Message-ID) nur einmal."""
    mails, gesehen, gekappt = [], set(), False
    for kontakt in kontakte:
        suchen_je = [(o, {"von": kontakt["adresse"]}, "von") for o in eingang] + [(gesendet, {"an": kontakt["adresse"]}, "an")]
        for ordner, kriterium, richtung in suchen_je:
            treffer = suchen(ordner, seit=seit, max_mails=MAX_JE_SUCHE, **kriterium)
            gekappt = gekappt or len(treffer) >= MAX_JE_SUCHE
            for mail in treffer:
                schluessel = mail.get("message_id") or (ordner, mail.get("uid"))
                if schluessel not in gesehen:
                    gesehen.add(schluessel)
                    mails.append(_eintrag(mail, kontakt, richtung))
    return {"stand": jetzt.astimezone(ZONE).strftime("%Y-%m-%dT%H:%M"), "seit": seit.isoformat(), "gekappt": gekappt,
            "kontakte": kontakte, "mails": mails}


def schreiben(ziel: Path, auszug: dict) -> None:
    """Atomar und nur für den Besitzer lesbar: Der Auszug enthält Mailtexte."""
    tmp = ziel.with_name(ziel.name + ".tmp")
    tmp.touch(mode=0o600)
    tmp.write_text(json.dumps(auszug, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(ziel)


def abgleichen(kontakte_datei: Path, suchen, eingang: tuple[str, ...], gesendet: str, jetzt: datetime) -> dict:
    seit, kontakte = kontakte_lesen(kontakte_datei)
    auszug = auszug_bauen(seit, kontakte, suchen, eingang, gesendet, jetzt)
    schreiben(Path(kontakte_datei).with_name("schriftverkehr.json"), auszug)
    return auszug
