"""Agent dokumente: baut Dokumente für Jan aus JSON-Beschreibungen von Claude (Renderer in shared/renderer/).

Ein Lauf (gestartet von der Zentrale nach einem Auftrag, kein Timer): offene Aufträge abarbeiten.
Bisher kann der Agent nur Zusammenfassungen von Vorlesungen (zusammenfassen.py), auch auf Auftrag von uni
(Feld von, Behauptungsliste behauptungen.json im Anhang). Ergebnis: PDF und docx in data/ausgang/<auftrag-id>/,
die Zentrale schickt beides an Jan. Antwortet Jan darauf, setzt der Agent die Sitzung fort und baut neu.
"""

import tomllib
from pathlib import Path

import renderer
from agentkit import auftraege, claude_lauf, log

import eingang
import zusammenfassen as z

AGENT = "dokumente"
HIER = Path(__file__).resolve().parent
AUSGANG = HIER / "data" / "ausgang"
PROFIL = HIER / "profil-zusammenfassung.toml"
VORLAGE = HIER / "data" / "vorlagen" / "zusammenfassung.docx"  # Word-Vorlage mit Logo, benutzt, wenn vorhanden
FORMAT = HIER.parent / "shared" / "renderer" / "FORMAT.md"
logger = log.hole_logger(HIER, AGENT)
log.hole_logger(HIER, "renderer")  # Warnungen des Renderers (z. B. Vorschau) ins selbe Log-Verzeichnis

WARTEN = (claude_lauf.LimitErreicht, claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon, claude_lauf.Pausiert)


def claude_fuer(auftrag_id: str):
    def claude(prompt: str, sitzung: str | None):
        e = claude_lauf.laufen(AGENT, HIER, prompt, art="anspruchsvoll", auftrag_id=auftrag_id,
                               sitzung_fortsetzen=sitzung)
        logger.info("Claude-Lauf %s: ok=%s, %d Schritte, %d Tokens", auftrag_id, e.ok, e.schritte, e.tokens)
        return e.text, e.sitzung, e.ok
    return claude


def bauen(beschreibung: dict, ziel: Path):
    profil = tomllib.loads(PROFIL.read_text(encoding="utf-8"))
    return renderer.bauen(beschreibung, ziel, profil=profil, vorlage=VORLAGE if VORLAGE.is_file() else None)


def bearbeiten(a: dict) -> None:
    start = z.ursprung(a, auftraege.erledigter) if a.get("sitzung") else a
    for datei in a.get("dateien") or []:
        eingang.vorbereiten(HIER / datei)
    behauptungen = z.behauptungsliste_finden(a.get("dateien") or []) \
        or z.behauptungsliste_finden(start.get("dateien") or [])
    anzahl = len(z.behauptungen_lesen((HIER / behauptungen).read_text(encoding="utf-8"))) if behauptungen else 0
    fertig = z.erstellen(a, AUSGANG / a["id"], HIER, claude_fuer(a["id"]), bauen,
                         z.format_abschnitt(FORMAT.read_text(encoding="utf-8")), behauptungen, a.get("sitzung"))
    logger.info("Auftrag %s fertig: %s (%d Kontrollen)", a["id"], fertig.pdf.name, fertig.kontrollen)
    auftraege.abschliessen(a["id"], z.ergebnistext(fertig, anzahl), sitzung=fertig.sitzung,
                           dateien=[fertig.pdf, fertig.docx])


def auftraege_abarbeiten() -> None:
    for a in auftraege.neue(AGENT, dienst=None):
        logger.info("Auftrag %s%s", a["id"], f" von {a['von']}" if a.get("von") else "")
        try:
            bearbeiten(a)
        except WARTEN as f:
            logger.info("Auftrag %s wartet: %s", a["id"], f)  # bleibt in neu/, nächster Lauf
            return
        except (z.ZusammenfassungFehler, claude_lauf.LaufFehler) as f:
            logger.warning("Auftrag %s fehlgeschlagen: %s", a["id"], f)
            auftraege.abschliessen(a["id"], str(f), status="fehlgeschlagen")
        except Exception as f:  # noqa: BLE001 – Fehler des Agenten (Profil, Vorlage, Renderer): Jan bekommt ihn
            logger.exception("Auftrag %s: Fehler im Agenten", a["id"])
            auftraege.abschliessen(a["id"], f"Fehler im Agenten ({type(f).__name__}): {f}\n"
                                   "Details: dokumente/logs/dokumente.log", status="fehlgeschlagen")


if __name__ == "__main__":
    auftraege_abarbeiten()
