"""Renderer: aus einer JSON-Beschreibung (von Claude) eine docx- oder pptx-Datei bauen.

Gemeinsame Bibliothek für Jan und Lia, ohne Inhalte, Zugangsdaten oder Netz.
Eingebunden per agentkit.pth (`import renderer`). Format für Claude: FORMAT.md, Stand: STATUS.md.
"""

from renderer.pruefung import BeschreibungUngueltig, pruefen

__all__ = ["BeschreibungUngueltig", "pruefen"]
