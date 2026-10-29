"""Renderer: aus einer JSON-Beschreibung (von Claude) eine docx-, pptx- oder xlsx-Datei bauen
(Arbeitsblatt, Folien, Zusammenfassung, Arbeitsmappe).

Gemeinsame Bibliothek für Jan und Lia, ohne Inhalte, Zugangsdaten oder Netz.
Eingebunden per agentkit.pth (`import renderer`). Format für Claude: FORMAT.md, Stand: STATUS.md.

    from renderer import bauen, BeschreibungUngueltig
    try:
        ergebnis = bauen(beschreibung_von_claude, ausgang / "blatt.docx", profil=profil)
    except BeschreibungUngueltig as e:
        ...  # str(e) an Claude zurückgeben, Claude korrigiert die Beschreibung
    ergebnis.kontrolltext, ergebnis.bilder  # Claude zur Kontrolle zeigen
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from renderer.pruefung import BeschreibungUngueltig, lesen, pruefen

__all__ = ["BeschreibungUngueltig", "Ergebnis", "bauen", "pruefen", "vorlage_umwandeln"]

ENDUNGEN = {"arbeitsblatt": ".docx", "folien": ".pptx", "zusammenfassung": ".docx", "arbeitsmappe": ".xlsx"}
log = logging.getLogger("renderer")


@dataclass
class Ergebnis:
    pfad: Path  # die gebaute Datei
    kontrolltext: str  # Inhalt in Lesereihenfolge (kontrolle.py)
    bilder: list[Path] = field(default_factory=list)  # Vorschau: ein PNG je Seite bzw. Folie
    pdf: Path | None = None  # PDF aus der Vorschau (Ersatzschriften des Servers, siehe STATUS.md)
    hinweise: list[str] = field(default_factory=list)  # z. B. warum die Vorschau fehlt


def bauen(beschreibung: dict | str, ziel: Path, profil: dict | None = None, vorlage: Path | None = None,
          vorschau: bool = True) -> Ergebnis:
    """Prüft die Beschreibung, baut die Datei nach `ziel` und liefert Kontrolltext und Vorschau.

    BeschreibungUngueltig: Fehler in Claudes Beschreibung (zurück an Claude). ValueError oder
    design.ProfilUngueltig: Fehler des Agenten (falsche Endung, Profil, Vorlage). Die Vorschau landet in
    `<ziel ohne Endung>-vorschau/`; scheitert sie, steht der Grund in `hinweise`, die Datei gibt es trotzdem.
    """
    from renderer import arbeitsblatt, arbeitsmappe, folien, kontrolle, zusammenfassung
    from renderer import vorschau as vorschau_modul

    b = lesen(beschreibung)
    ziel = Path(ziel)
    if ziel.suffix.lower() != ENDUNGEN[b["art"]]:
        raise ValueError(f"{ziel.name}: Für art {b['art']!r} muss das Ziel auf {ENDUNGEN[b['art']]} enden")
    modul = {"arbeitsblatt": arbeitsblatt, "folien": folien, "zusammenfassung": zusammenfassung,
             "arbeitsmappe": arbeitsmappe}[b["art"]]
    modul.bauen(b, ziel, profil, vorlage)
    ergebnis = Ergebnis(ziel, kontrolle.kontrolltext(ziel))
    if b["art"] == "arbeitsmappe" and arbeitsmappe.proben(b):
        ergebnis.kontrolltext += "\n" + arbeitsmappe.proben(b)
    if vorschau:
        ordner = ziel.parent / f"{ziel.stem}-vorschau"
        try:
            ergebnis.bilder = vorschau_modul.vorschau(ziel, ordner)
            ergebnis.pdf = ordner / f"{ziel.stem}.pdf"
        except vorschau_modul.VorschauFehler as e:
            log.warning("Keine Vorschau für %s: %s", ziel.name, e)
            ergebnis.hinweise.append(f"Keine Vorschau: {e}")
    return ergebnis


def vorlage_umwandeln(quelle: Path, ziel: Path) -> Path:
    """Vorlage (.dotx/.potx oder schon .docx/.pptx) als .docx/.pptx speichern, siehe vorlagen.py."""
    from renderer import vorlagen

    return vorlagen.umwandeln(quelle, ziel)
