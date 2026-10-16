"""Beispiel-Gerüst für <name>/agent.py. Zeigt, wie agentkit zusammenspielt.

Ein Lauf: 1. freigegebene Entwürfe ausführen, 2. Aufträge abarbeiten.
Zeitgesteuerte Aufgaben kommen je nach Agent dazu.
"""

from pathlib import Path

from agentkit import auftraege, claude_lauf, config, freigabe, log

AGENT = "<name>"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
cfg = config.lade_config(HIER)


def ausfuehren(entwurf: dict) -> str:
    """Hier handelt der Python-Code nach Jans Freigabe (Mail senden usw.). Gibt das Ergebnis zurück."""
    raise NotImplementedError(entwurf["typ"])


def freigegebene_ausfuehren() -> None:
    for e in freigabe.zur_ausfuehrung(AGENT):
        try:
            freigabe.ausfuehrung_beginnen(e["id"], kauf_limit_euro=cfg.get("KAUF_LIMIT_EURO"))
        except freigabe.FreigabeFehler as f:
            logger.warning("Nicht ausgeführt: %s", f)
            continue
        try:
            ergebnis = ausfuehren(e)
            freigabe.ausfuehrung_abschliessen(e["id"], ergebnis, erfolgreich=True)
        except Exception as f:  # noqa: BLE001 – jeder Fehler wird Jan gemeldet
            logger.exception("Ausführung %s fehlgeschlagen", e["id"])
            freigabe.ausfuehrung_abschliessen(e["id"], f"Fehler: {f}", erfolgreich=False)


def auftraege_abarbeiten() -> None:
    for a in auftraege.neue(AGENT):
        try:
            e = claude_lauf.laufen(AGENT, HIER, a["text"], art="anspruchsvoll", auftrag_id=a["id"],
                                   lernsitzung=a["modus"] == "lernen")
        except (claude_lauf.LimitErreicht, claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon) as f:
            logger.info("Auftrag %s wartet: %s", a["id"], f)  # bleibt in neu/, nächster Lauf
            return
        except claude_lauf.LaufFehler as f:
            auftraege.abschliessen(a["id"], str(f), status="fehlgeschlagen")
            continue
        # Hier aus e.text bzw. den von Claude geschriebenen Dateien Entwürfe anlegen:
        # freigabe.neuer_entwurf(AGENT, titel, inhalt, typ="mail", daten={...})
        auftraege.abschliessen(a["id"], e.text if e.ok else f"Fehler: {e.text}",
                               status="erledigt" if e.ok else "fehlgeschlagen")


if __name__ == "__main__":
    freigegebene_ausfuehren()
    auftraege_abarbeiten()
