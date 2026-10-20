"""Dienst uni-lernen: tägliche Abfrage fälliger Karten über Telegram, ohne Claude.

Läuft per Timer alle 15 Minuten und nach jedem Klick (die Zentrale startet uni-lernen.service).
Ablauf einer Abfrage (Zustand in data/lernen/sitzung.json):
1. Ab START_STUNDE, wenn gerade kein Termin im Kalender läuft: Auswahl aus dem Lernermodell
   (höchstens ca. 10 Minuten, fällige vor neuen, über Themen gemischt), erste Frage mit
   [Antwort zeigen] [Später]. Jan kann auch per Antwort auf die Nachricht selbst antworten.
2. Antwort mit Quelle und [Nochmal] [Schwer] [Gut] [Leicht]; die Bewertung geht ins FSRS-Modell.
   "Nochmal" stellt die Karte am Ende der Abfrage einmal neu.
3. Nach der letzten Karte eine kurze Bilanz. "Später" fragt nach PAUSE erneut (bis ENDE_STUNDE).
Nur Klicks und Antworten auf die zuletzt gesendete Meldung zählen, ältere werden ignoriert.
"""

import fcntl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from agentkit import auftraege, kalender, log, meldungen

import lernmodell

AGENT = "uni"
DIENST = "uni-lernen"
HIER = Path(__file__).resolve().parent
LERNEN = HIER / "data" / "lernen"
SITZUNG = LERNEN / "sitzung.json"
MODULE = ("holzschutz",)  # Pilot; weitere Module kommen hier dazu
ZONE = ZoneInfo("Europe/Berlin")
START_STUNDE, ENDE_STUNDE = 18, 22
PAUSE = timedelta(hours=1)
logger = log.hole_logger(HIER, DIENST)

ZEIGEN, SPAETER = "Antwort zeigen", "Später"
FRAGE_KNOEPFE = [[ZEIGEN, SPAETER]]
BEWERTEN_KNOEPFE = [list(lernmodell.BEWERTUNGEN)]


@dataclass
class Nachricht:
    text: str
    knoepfe: list[list[str]] = field(default_factory=list)
    dateien: list[str] = field(default_factory=list)


def _frage(s: dict, m: lernmodell.Modul) -> Nachricht:
    k = m.karten[s["warteschlange"][0]]
    gesamt = s["erledigt"] + len(s["warteschlange"])
    titel = m.themen.get(k["thema"], {}).get("titel", k["thema"])
    kopf = ""
    if s["erledigt"] == 0 and s["phase"] != "pause":
        minuten = max(1, round(gesamt * lernmodell.SEKUNDEN_PRO_KARTE / 60))
        kopf = f"Wiederholung heute: {gesamt} Karten, ca. {minuten} Minuten.\n\n"
    s["phase"] = "frage"
    text = (f"{kopf}Karte {s['erledigt'] + 1}/{gesamt} · {titel} (Wichtigkeit {m.score(k['thema'])}/5)\n\n"
            f"{k['frage']}\n\nErst selbst antworten (im Kopf oder als Antwort auf diese Nachricht), dann aufdecken.")
    return Nachricht(text, FRAGE_KNOEPFE, [k["bild"]] if k.get("bild") else [])


def _bilanz(s: dict) -> Nachricht:
    s["phase"] = "fertig"
    return Nachricht(f"Fertig für heute: {s['erledigt']} Karten, {s['richtig']} davon gewusst (Gut oder Leicht).")


def zeitschritt(s: dict | None, m: lernmodell.Modul, jetzt: datetime, belegt) -> tuple[dict | None, Nachricht | None]:
    """Vom Timer: Abfrage beginnen oder nach einer Pause fortsetzen. belegt() fragt den Kalender."""
    heute = jetzt.date().isoformat()
    if s and s["datum"] == heute:
        if s["phase"] == "pause" and jetzt >= datetime.fromisoformat(s["pause_bis"]) and jetzt.hour < ENDE_STUNDE:
            return s, _frage(s, m)
        return s, None
    if not START_STUNDE <= jetzt.hour < ENDE_STUNDE or belegt():
        return s, None
    neu = {"datum": heute, "modul": m.ordner.name, "warteschlange": m.auswahl(jetzt), "wiederholt": [],
           "phase": "fertig", "meldung": None, "erledigt": 0, "richtig": 0, "pause_bis": None}
    if not neu["warteschlange"]:
        return neu, None  # heute nichts fällig; nicht alle 15 Minuten neu rechnen
    return neu, _frage(neu, m)


def weiter(s: dict, m: lernmodell.Modul, text: str, jetzt: datetime) -> tuple[dict, Nachricht | None]:
    """Jans Klick oder Antwort auf die zuletzt gesendete Meldung verarbeiten."""
    text = text.strip()
    if s["phase"] == "pause":  # Jan meldet sich vor Ablauf der Pause
        return s, _frage(s, m)
    if s["phase"] == "frage":
        if text == SPAETER:
            s["phase"], s["pause_bis"] = "pause", (jetzt + PAUSE).isoformat()
            return s, Nachricht(f"Okay, ich frage um {(jetzt + PAUSE):%H:%M} Uhr wieder.")
        k = m.karten[s["warteschlange"][0]]
        eigene = f"\n\nDeine Antwort: {text}" if text != ZEIGEN else ""
        s["phase"] = "antwort"
        return s, Nachricht(f"{k['antwort']}\n\nQuelle: {k['quelle']}{eigene}\n\nWie gut wusstest du es?",
                            BEWERTEN_KNOEPFE)
    if s["phase"] == "antwort":
        bewertung = next((w for b, w in lernmodell.BEWERTUNGEN.items() if b.lower() == text.lower()), None)
        if bewertung is None:
            return s, Nachricht("Bitte mit einem Knopf bewerten.", BEWERTEN_KNOEPFE)
        karte_id = s["warteschlange"].pop(0)
        m.bewerten(karte_id, bewertung, jetzt)
        s["erledigt"] += 1
        s["richtig"] += bewertung >= lernmodell.RICHTIG_AB
        if bewertung == 1 and karte_id not in s["wiederholt"]:
            s["warteschlange"].append(karte_id)
            s["wiederholt"].append(karte_id)
        return s, _frage(s, m) if s["warteschlange"] else _bilanz(s)
    return s, None


def _belegt(jetzt: datetime) -> bool:
    try:
        return any(not t.ganztags and t.beginn <= jetzt + timedelta(minutes=15) and t.ende > jetzt
                   for t in kalender.termine(jetzt, jetzt + timedelta(minutes=30)))
    except kalender.KalenderFehler as f:
        logger.warning("Kalender nicht lesbar, frage trotzdem: %s", f)
        return False


def _senden(s: dict, n: Nachricht | None) -> None:
    if n is None:
        return
    mid = meldungen.melden(AGENT, n.text, dateien=[HIER / d for d in n.dateien] or None,
                           knoepfe=n.knoepfe or None, dienst=DIENST if n.knoepfe else None)
    if n.knoepfe:
        s["meldung"] = mid


def main() -> None:
    LERNEN.mkdir(parents=True, exist_ok=True)
    with open(LERNEN / ".lock", "w") as sperre:
        fcntl.flock(sperre, fcntl.LOCK_EX)  # Timer und Klick können gleichzeitig starten
        jetzt = datetime.now(ZONE)
        s = lernmodell.lies_json(SITZUNG, None)
        m = lernmodell.Modul(LERNEN / (s["modul"] if s else MODULE[0]))
        for a in auftraege.neue(AGENT, dienst=DIENST):
            if s and a.get("meldung") and a["meldung"] == s["meldung"]:
                s, n = weiter(s, m, a["text"], jetzt)
                _senden(s, n)
                ergebnis = "verarbeitet"
            else:
                ergebnis = "ignoriert: gehört nicht zur aktuellen Abfrage"
            if s:
                lernmodell.schreibe_json(SITZUNG, s)
            auftraege.abschliessen(a["id"], ergebnis)
            logger.info("Auftrag %s (%s): %s", a["id"], a["text"][:30], ergebnis)
        s, n = zeitschritt(s, m, jetzt, lambda: _belegt(jetzt))
        if s:
            _senden(s, n)
            lernmodell.schreibe_json(SITZUNG, s)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 – Fehler loggen, Dienst als fehlgeschlagen markieren
        logger.exception("uni-lernen fehlgeschlagen")
        raise
