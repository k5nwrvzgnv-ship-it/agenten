"""Vorlagen: Word- und PowerPoint-Dateien als Grundlage für gebaute Dateien.

Aus der Vorlage kommen Kopf- und Fußzeilen, Logo und Ränder (Word) bzw. Folienmaster, Hintergrund und Logo
(PowerPoint). Die Gestaltung der Inhalte (Schriften, Farben, Kästen) bleibt im Design-Profil. python-docx
und python-pptx öffnen .dotx/.potx nicht (anderer Inhaltstyp), darum wandelt umwandeln() sie vorher um.
Die Vorlagen selbst legt der Agent ab (`<agent>/data/vorlagen/`), nicht der Renderer.
"""

import shutil
import zipfile
from pathlib import Path

import docx
import pptx
from docx.oxml.ns import qn
from pptx.oxml.ns import qn as pqn

# Inhaltstyp des Hauptteils: Vorlage -> Dokument
_TYPEN = {
    ".dotx": (".docx", "wordprocessingml.template.main+xml", "wordprocessingml.document.main+xml"),
    ".potx": (".pptx", "presentationml.template.main+xml", "presentationml.presentation.main+xml"),
}
FOLIE_16_9 = (12192000, 6858000)  # EMU, wie folien.FOLIE_CM


def umwandeln(quelle: Path, ziel: Path) -> Path:
    """.dotx -> .docx, .potx -> .pptx (Inhaltstyp ändern); .docx/.pptx wird kopiert. Sonst ValueError."""
    quelle, ziel = Path(quelle), Path(ziel)
    endung = quelle.suffix.lower()
    if endung in (".docx", ".pptx"):
        _endung_pruefen(ziel, endung)
        shutil.copyfile(quelle, ziel)
        return ziel
    if endung not in _TYPEN:
        raise ValueError(f"{quelle.name}: Vorlagen nur als .dotx, .potx, .docx oder .pptx")
    neue_endung, alt, neu = _TYPEN[endung]
    _endung_pruefen(ziel, neue_endung)
    with zipfile.ZipFile(quelle) as rein, zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as raus:
        for eintrag in rein.infolist():
            daten = rein.read(eintrag.filename)
            if eintrag.filename == "[Content_Types].xml":
                if alt.encode() not in daten:
                    raise ValueError(f"{quelle.name}: keine gültige {endung}-Datei (Inhaltstyp fehlt)")
                daten = daten.replace(alt.encode(), neu.encode())
            raus.writestr(eintrag, daten)
    return ziel


def _endung_pruefen(ziel: Path, endung: str):
    if ziel.suffix.lower() != endung:
        raise ValueError(f"{ziel.name}: Ziel muss auf {endung} enden")


def word_grundlage(vorlage: Path) -> docx.document.Document:
    """Dokument aus der Vorlage mit leerem Inhalt. Kopf-/Fußzeilen, Ränder und Stile bleiben."""
    d = _oeffnen(vorlage, ".docx", docx.Document)
    koerper = d.element.body
    for el in list(koerper):
        if el.tag != qn("w:sectPr"):
            koerper.remove(el)
    return d


def powerpoint_grundlage(vorlage: Path) -> pptx.presentation.Presentation:
    """Präsentation aus der Vorlage ohne Folien. Master und Layouts bleiben. Nur 16:9, sonst ValueError."""
    prs = _oeffnen(vorlage, ".pptx", pptx.Presentation)
    if (prs.slide_width, prs.slide_height) != FOLIE_16_9:
        raise ValueError(f"{Path(vorlage).name}: Folienformat {prs.slide_width / 360000:.2f} x "
                         f"{prs.slide_height / 360000:.2f} cm, nötig ist 16:9 (33,87 x 19,05 cm)")
    liste = prs.slides._sldIdLst
    for eintrag in list(liste):
        prs.part.drop_rel(eintrag.get(pqn("r:id")))
        liste.remove(eintrag)
    return prs


def layout(prs, nur_titel: bool):
    """Layout ohne Platzhalter (leer) bzw. mit Titel als einzigem Inhalts-Platzhalter. Sucht nach Art der
    Platzhalter, nicht nach Namen: Vorlagen benennen Layouts in ihrer Sprache."""
    nebensache = {"DATE", "FOOTER", "SLIDE_NUMBER"}

    def arten(lay):
        return {ph.placeholder_format.type.name for ph in lay.placeholders} - nebensache

    gesucht = {"TITLE"} if nur_titel else set()
    for lay in prs.slide_layouts:
        if arten(lay) == gesucht:
            return lay
    if nur_titel:  # sonst das Layout mit Titel und den wenigsten weiteren Platzhaltern
        mit_titel = [lay for lay in prs.slide_layouts if "TITLE" in arten(lay)]
        if mit_titel:
            return min(mit_titel, key=lambda lay: len(arten(lay)))
    return min(prs.slide_layouts, key=lambda lay: len(arten(lay)))


def _oeffnen(vorlage: Path, endung: str, oeffner):
    vorlage = Path(vorlage)
    if vorlage.suffix.lower() != endung:
        raise ValueError(f"{vorlage.name}: Vorlage muss {endung} sein (vorher vorlage_umwandeln)")
    if not vorlage.is_file():
        raise ValueError(f"{vorlage}: Vorlage fehlt")
    return oeffner(vorlage)
