"""Lias eigene Formatvorlage (board-plan.md 7): Liegt in data/vorlagen/ eine Word- oder PowerPoint-Vorlage
(.dotx/.docx bzw. .potx/.pptx), baut der Renderer Arbeitsblätter bzw. Folien auf ihr auf (Kopf- und Fußzeilen,
Logo, Ränder, Folienmaster; die Gestaltung der Inhalte bleibt im Profil). Ohne Vorlage wie bisher.

Mehrere Vorlagen einer Sorte: die neueste gilt, die anderen nennt der Hinweis. .dotx/.potx wandelt der Renderer
in data/vorlagen/umgewandelt/ um (python-docx öffnet sie sonst nicht), neu nur, wenn die Vorlage neuer ist.
"""

import zipfile
from pathlib import Path

from renderer import vorlage_umwandeln

ORDNER = Path("data") / "vorlagen"
SORTEN = {".docx": (".dotx", ".docx"), ".pptx": (".potx", ".pptx")}  # Endung des Ergebnisses -> Vorlagen


def waehlen(hier: Path, endung: str) -> tuple[Path | None, list[str]]:
    """(Vorlage für ein Ergebnis mit dieser Endung oder None, Hinweise). Für .xlsx gibt es keine Vorlage.
    ValueError, wenn die Vorlage kaputt ist (der Aufrufer baut dann ohne sie)."""
    ordner = hier / ORDNER
    if endung not in SORTEN or not ordner.is_dir():
        return None, []
    kandidaten = sorted((p for p in ordner.iterdir() if p.is_file() and p.suffix.lower() in SORTEN[endung]
                         and not p.name.startswith((".", "~$"))), key=lambda p: p.stat().st_mtime, reverse=True)
    if not kandidaten:
        return None, []
    vorlage = kandidaten[0]
    hinweise = [f"Vorlage {vorlage.name}"]
    if len(kandidaten) > 1:
        hinweise.append("weitere Vorlagen nicht genutzt: " + ", ".join(p.name for p in kandidaten[1:]))
    if vorlage.suffix.lower() == endung:
        return vorlage, hinweise
    ziel = ordner / "umgewandelt" / (vorlage.stem + endung)
    if not ziel.exists() or ziel.stat().st_mtime < vorlage.stat().st_mtime:
        ziel.parent.mkdir(exist_ok=True)
        try:
            vorlage_umwandeln(vorlage, ziel)
        except (ValueError, zipfile.BadZipFile, OSError) as e:
            ziel.unlink(missing_ok=True)
            raise ValueError(f"Vorlage {vorlage.name}: {e}") from None
    return ziel, hinweise
