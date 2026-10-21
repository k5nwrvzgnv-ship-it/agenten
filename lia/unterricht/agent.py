"""Platzhalter-Agent unterricht in Lias Instanz (AGENTKIT_INSTANZ=lia/shared).

Bestätigt jeden Auftrag und sagt, dass die Funktion bald kommt. Ruft Claude nicht auf.
Die Art des Auftrags steht im Feld quelle (portal-material, portal-woche, portal-frage, portal-text).
"""

from pathlib import Path

from agentkit import auftraege, log

AGENT = "unterricht"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)

ANTWORTEN = {
    "portal-material": "Dein Materialwunsch ist angekommen. Das Erstellen von Material kommt bald, "
                       "bis dahin sammle ich deine Wünsche.",
    "portal-woche": "Der Wochenüberblick kommt bald. Dein Wunsch ist notiert.",
    "portal-frage": "Deine Frage ist angekommen. Antworten kommen bald, bis dahin sammle ich sie.",
}
STANDARD = "Ist angekommen. Diese Funktion kommt bald."


def antwort(auftrag: dict) -> str:
    return ANTWORTEN.get(auftrag.get("quelle"), STANDARD)


def auftraege_abarbeiten() -> None:
    for a in auftraege.neue(AGENT):
        auftraege.abschliessen(a["id"], antwort(a), status="erledigt")
        logger.info("Auftrag %s bestätigt (%s)", a["id"], a.get("quelle"))


if __name__ == "__main__":
    auftraege_abarbeiten()
