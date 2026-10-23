"""Agent unterricht in Lias Instanz (AGENTKIT_INSTANZ=lia/instanz).

Die Art des Auftrags steht im Feld quelle (portal-material, portal-woche, portal-frage, portal-text).
- portal-material: Material auf Zuruf (material.py, Skill einzelmaterial). Lia bekommt die docx- oder
  pptx-Datei mit Begleittext. Scheitert es, erfährt Jan die Ursache als Meldung in seiner Zentrale.
  Lias laufende Reihen (reihen.toml) gehen mit; ist die Datei fehlerhaft, läuft er ohne sie und Jan erfährt es.
  Ebenso der Katalog von Lias früherem Material (data/wissen/katalog.md, wissen.py) und der Leitfaden
  (leitfaden.md), falls vorhanden.
- alles andere: Platzhalter, bestätigt mit "kommt bald", ohne Claude.
"""

import tomllib
from pathlib import Path

import leitfaden
import material
import reihen
import renderer
import wissen
from agentkit import auftraege, claude_lauf, config, log, meldungen, verbrauch

AGENT = "unterricht"
HIER = Path(__file__).resolve().parent
PROFIL = HIER / "profil.toml"
logger = log.hole_logger(HIER, AGENT)

ANTWORTEN = {
    "portal-woche": "Der Wochenüberblick kommt bald. Dein Wunsch ist notiert.",
    "portal-frage": "Deine Frage ist angekommen. Antworten kommen bald, bis dahin sammle ich sie.",
}
STANDARD = "Ist angekommen. Diese Funktion kommt bald."
NICHT_GEKLAPPT = "Das Material konnte ich leider nicht erstellen. Jan ist informiert."
LIMIT = "Gerade ist das gemeinsame Kontingent aufgebraucht. Bitte schick den Wunsch ab {zeit} noch einmal."


def antwort(auftrag: dict) -> str:
    return ANTWORTEN.get(auftrag.get("quelle"), STANDARD)


def jan_melden(text: str, basis: Path | None = None) -> None:
    """Meldung in Jans Instanz (seine Zentrale), nicht in Lias."""
    meldungen.melden(AGENT, f"Lia, Agent unterricht: {text}", basis=basis or config.KONTINGENT_DIR / "meldungen")


def profil_laden() -> dict:
    with open(PROFIL, "rb") as f:
        return tomllib.load(f)


def reihen_laden() -> list[dict]:
    """Reihenkontext; ist reihen.toml fehlerhaft, ohne ihn weiter (Lia soll trotzdem Material bekommen)."""
    try:
        return reihen.laden(HIER / "reihen.toml")
    except reihen.ReihenFehler as e:
        logger.error("Reihenkontext fehlt: %s", e)
        jan_melden(f"reihen.toml fehlerhaft, Material ohne Reihenkontext: {e}")
        return []


def claude_laufen(auftrag_id: str):
    def laufen(prompt: str, sitzung: str | None = None):
        return claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", auftrag_id=auftrag_id,
                                  sitzung_fortsetzen=sitzung)
    return laufen


def material_auftrag(a: dict, bearbeiten=material.bearbeiten) -> None:
    try:
        f = bearbeiten(a, HIER, profil_laden(), laufen=claude_laufen(a["id"]), bauen=renderer.bauen,
                       reihen=reihen_laden(), katalog=wissen.katalog_laden(HIER / "data" / "wissen" / "katalog.md"),
                       leitfaden=leitfaden.laden(HIER / "leitfaden.md"))
    except claude_lauf.LimitErreicht as e:
        logger.warning("Auftrag %s: %s", a["id"], e)
        auftraege.abschliessen(a["id"], LIMIT.format(zeit=verbrauch.zeit_text(e.reset)),
                               status="fehlgeschlagen")
        jan_melden(f"Materialwunsch von Lia nicht bearbeitet: {e}")
        return
    except (material.MaterialFehler, claude_lauf.LaufFehler) as e:
        logger.error("Auftrag %s fehlgeschlagen: %s", a["id"], e)
        auftraege.abschliessen(a["id"], NICHT_GEKLAPPT, status="fehlgeschlagen")
        jan_melden(f"Materialwunsch {a['id']} fehlgeschlagen: {e}")
        return
    hinweis = f", Hinweise: {'; '.join(f.hinweise)}" if f.hinweise else ""
    logger.info("Auftrag %s fertig: %s, %d Läufe, %.2f USD, %d Tokens%s",
                a["id"], f.datei.name, f.laeufe, f.usd, f.tokens, hinweis)
    auftraege.abschliessen(a["id"], f.begleittext, sitzung=f.sitzung, dateien=[f.datei])


def auftraege_abarbeiten() -> None:
    gesehen = set()
    while neue := [a for a in auftraege.neue(AGENT) if a["id"] not in gesehen]:
        for a in neue:
            gesehen.add(a["id"])
            try:
                if a.get("quelle") == "portal-material":
                    material_auftrag(a)
                else:
                    auftraege.abschliessen(a["id"], antwort(a), status="erledigt")
                    logger.info("Auftrag %s bestätigt (%s)", a["id"], a.get("quelle"))
            except Exception as e:  # z. B. Fehler im Renderer: Lia bekommt eine Antwort, Jan die Ursache
                logger.exception("Auftrag %s: unerwarteter Fehler", a["id"])
                auftraege.abschliessen(a["id"], NICHT_GEKLAPPT, status="fehlgeschlagen")
                jan_melden(f"Unerwarteter Fehler bei Auftrag {a['id']}: {type(e).__name__}: {e}")


if __name__ == "__main__":
    auftraege_abarbeiten()
