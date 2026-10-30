"""Dateien eines Ergebnisses: Downloads und Seitenvorschau, mit Pfadprüfung gegen den Agent-Ordner.

Ergebnisdateien stehen im Auftrag als Pfade relativ zum Agent-Ordner (lia/<agent>/). Die Vorschau legt der
Renderer daneben ab: <ordner>/<stem>-vorschau/<stem>-seite-01.png ... und <stem>.pdf.

Jeder Pfad wird geprüft, bevor die App ihn ausliefert: aufgelöst (auch Symlinks), muss im Agent-Ordner liegen,
kein "..", nichts Verstecktes (.env, .venv/), nur erlaubte Endungen, muss eine Datei sein. Sonst None (404).
"""

import re
from pathlib import Path

from agentkit._ablage import AGENT_MUSTER

DOWNLOAD_ENDUNGEN = {".pdf", ".docx", ".pptx", ".xlsx"}
SEITEN_ENDUNGEN = {".png"}


def agent_ordner(instanz: Path, agent: str | None) -> Path | None:
    """lia/<agent>/ neben der Instanz. Nur gültige Agentennamen."""
    if not agent or not AGENT_MUSTER.match(agent):
        return None
    return instanz.parent / agent


def sicher(wurzel: Path, relativ: str | Path, endungen: set[str]) -> Path | None:
    """Pfad einer Datei im Agent-Ordner oder None, wenn er dort nicht hingehört."""
    rel = Path(relativ)
    if rel.is_absolute() or ".." in rel.parts or any(teil.startswith(".") for teil in rel.parts):
        return None
    if rel.suffix.lower() not in endungen:
        return None
    wurzel = wurzel.resolve()
    pfad = (wurzel / rel).resolve()
    if not pfad.is_relative_to(wurzel) or pfad.suffix.lower() not in endungen or not pfad.is_file():
        return None
    return pfad


def vorschau_ordner(relativ: str) -> Path:
    datei = Path(relativ)
    return datei.parent / f"{datei.stem}-vorschau"


def vorschau_pdf(wurzel: Path, relativ: str) -> Path | None:
    return sicher(wurzel, vorschau_ordner(relativ) / f"{Path(relativ).stem}.pdf", {".pdf"})


def vorschau_seiten(wurzel: Path, relativ: str) -> list[Path]:
    """Seitenbilder des Renderers, nach Seitenzahl sortiert. Fehlt der Ordner: leer."""
    rel_ordner = vorschau_ordner(relativ)
    if Path(relativ).is_absolute() or ".." in Path(relativ).parts:
        return []
    ordner = wurzel / rel_ordner
    if not ordner.is_dir():
        return []
    muster = re.compile(re.escape(Path(relativ).stem) + r"-seite-(\d+)\.png")
    treffer = sorted((int(m.group(1)), p.name) for p in ordner.iterdir() if (m := muster.fullmatch(p.name)))
    return [p for _, name in treffer if (p := sicher(wurzel, rel_ordner / name, SEITEN_ENDUNGEN))]


def vorschau_info(wurzel: Path | None, pfade: list[str]) -> list[tuple[bool, bool, int]]:
    """Für logik.dateien_ansicht: je Datei (Datei darf ausgeliefert werden, Vorschau-PDF da, Anzahl Seiten)."""
    if wurzel is None:
        return [(False, False, 0)] * len(pfade)
    return [(sicher(wurzel, p, DOWNLOAD_ENDUNGEN) is not None, vorschau_pdf(wurzel, p) is not None,
             len(vorschau_seiten(wurzel, p))) for p in pfade]
