"""Agent theater in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz), Einstieg des Dienstes lia-theater.

Holt die offenen Aufträge an theater und beantwortet sie einzeln (nachbesserung.py): vor allem Nachbesserungen aus
Lias Feedback zu einer Runde (Frage beantworten oder Ablauf und Spielfassung überarbeiten). Lia bekommt die Antwort
über ihre Zentrale. Scheitert ein Auftrag, bekommt Lia eine kurze Nachricht und Jan die Ursache als Meldung in
seiner Zentrale. Neue Runden startet weiter nur runde.py von Hand.
Aufruf: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz .venv/bin/python agent.py
"""

import tomllib
from pathlib import Path

import nachbesserung
from agentkit import auftraege, claude_lauf, config, log, meldungen, verbrauch

AGENT = "theater"
HIER = Path(__file__).resolve().parent
logger = log.hole_logger(HIER, AGENT)
NICHT_GEKLAPPT = "Das hat leider nicht geklappt. Jan ist informiert und kümmert sich."
LIMIT = "Gerade ist die Rechenzeit aufgebraucht. Bitte schick es ab {zeit} noch einmal."


def jan_melden(text: str, basis: Path | None = None) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent theater: {text}", basis=basis or config.KONTINGENT_DIR / "meldungen")


def claude_laufen(auftrag_id: str):
    def laufen(prompt: str, sitzung: str | None = None):
        return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", auftrag_id=auftrag_id,
                                  sitzung_fortsetzen=sitzung)
    return laufen


def umgebung(auftrag_id: str) -> nachbesserung.Umgebung:
    import renderer
    lies = lambda name: tomllib.loads((HIER / name).read_text(encoding="utf-8"))  # noqa: E731
    return nachbesserung.Umgebung(hier=HIER, vorgaben=lies("theater.toml"), profil=lies("profil.toml"),
                                  laufen=claude_laufen(auftrag_id), renderer_bauen=renderer.bauen)


def auftrag_bearbeiten(a: dict, bearbeiten=nachbesserung.bearbeiten, umgebung=umgebung, melden=jan_melden) -> None:
    try:
        e = bearbeiten(a, umgebung(a["id"]))
    except claude_lauf.LimitErreicht as f:
        logger.warning("Auftrag %s: %s", a["id"], f)
        auftraege.abschliessen(a["id"], LIMIT.format(zeit=verbrauch.zeit_text(f.reset)), status="fehlgeschlagen")
        melden(f"Anfrage von Lia nicht bearbeitet: {f}")
        return
    except Exception as f:  # jeder Abbruch: Lia bekommt eine Antwort, Jan die Ursache
        logger.exception("Auftrag %s fehlgeschlagen", a["id"])
        auftraege.abschliessen(a["id"], NICHT_GEKLAPPT, status="fehlgeschlagen")
        melden(f"Auftrag {a['id']} fehlgeschlagen: {type(f).__name__}: {f}")
        return
    hinweis = f", Hinweise: {'; '.join(e.hinweise)}" if e.hinweise else ""
    logger.info("Auftrag %s fertig: %d Läufe, %.2f USD, %d Dateien%s", a["id"], e.laeufe, e.usd, len(e.dateien), hinweis)
    auftraege.abschliessen(a["id"], e.text, sitzung=e.sitzung, dateien=e.dateien, daten=e.daten)


def auftraege_abarbeiten(**kw) -> None:
    gesehen = set()
    while neue := [a for a in auftraege.neue(AGENT) if a["id"] not in gesehen]:
        for a in neue:
            gesehen.add(a["id"])
            auftrag_bearbeiten(a, **kw)


if __name__ == "__main__":
    auftraege_abarbeiten()
