"""Agent fehlstellenscan (Anzeige „Fehlstellen-Scan“): YOLO-Arbeit für das Forschungsprojekt Fehlstellen an Holz.

Aufteilung (Jan, 11.11.2026): Training von Hand auf Jans Mac (PyTorch, device="mps"). Der Server baut und prüft
Datensätze in kleinem Umfang (datensatz.py), wertet Läufe aus (auswertung.py) und macht später Vorhersagen.

Ein Lauf je Auftrag (agentkit.auftraege), ohne Timer und ohne Claude. Rechenschritte laufen später wie bei
holzbalkenscan in einem eigenen systemd-Scope mit MemoryMax (der Server hat keinen Swap). Solange noch nichts
gebaut ist, schließt der Agent jeden Auftrag mit einem Hinweis ab, statt ihn liegen zu lassen.
"""

import fcntl
import sys
from pathlib import Path

AGENT = "fehlstellenscan"
ANZEIGE = "Fehlstellen-Scan"
HIER = Path(__file__).resolve().parent
DATEN = HIER / "data"

NOCH_NICHT_GEBAUT = ("Fehlstellen-Scan kann noch nichts ausführen: Datensatz bauen und Auswertung sind noch nicht "
                     "gebaut (siehe fehlstellenscan/STATUS.md).")


def bearbeiten(text: str) -> tuple[str, str]:
    """Antwort auf einen Auftrag als (status, ergebnis). Vorerst gibt es noch keine Aufgabe."""
    return "fehlgeschlagen", NOCH_NICHT_GEBAUT


def main() -> int:
    from agentkit import auftraege, log

    logger = log.hole_logger(HIER, AGENT)
    DATEN.mkdir(exist_ok=True)
    with open(DATEN / "lauf.sperre", "w") as sperre:
        try:
            fcntl.flock(sperre, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.info("Ein anderer Lauf ist aktiv, Aufträge warten")
            return 0
        for a in auftraege.neue(AGENT):
            status, ergebnis = bearbeiten(a["text"])
            logger.info("Auftrag %s: %s", a["id"], status)
            auftraege.abschliessen(a["id"], ergebnis, status=status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
