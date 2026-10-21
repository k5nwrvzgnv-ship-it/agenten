"""Arbeitsblatt als docx bauen, aus einer geprüften Beschreibung (pruefung.lesen) und einem Design-Profil.

Aufbau nach Lias Vorbild: Kopf-Tabelle (Fach, Thema, Nummer, Lehrkraft, Datum, Name), Merksatz im Kasten,
Material farbig hinterlegt, nummerierte Aufgaben mit Antwortplatz, Hilfen klein darunter.
python-docx kann keine Rahmen, Schattierung, Zellverbund-Details oder Nummerierungs-Neustarts. Das steht hier
als kleines XML (Funktionen mit _xml_ im Namen), jeweils an der Stelle, die das Schema verlangt.
"""

from pathlib import Path

import docx
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from renderer import design

SEITE_CM = (21.0, 29.7)
RAND_CM = 2.0
RAND_OBEN_UNTEN_CM = 1.75
KOPF_SPALTEN_CM = (3.75, 8.0, 4.25)  # Fach/Lehrkraft, Thema/Nummer, Datum/Name (wie Lias Vorbild)
EINZUG_AUFGABE_CM = 1.3  # Text der Aufgabe, die Nummer steht bei 0,6 cm
HILFE_PT = 9
UEBERSCHRIFT_PT = {1: 14, 2: 12, 3: 11}
LINIENFARBE = "404040"
ANKREUZ_ZEICHEN = ("Wingdings", "F070")  # Kästchen mit dickem Rand, wie bei Lia
SPRACHE = "de-DE"  # Rechtschreibprüfung beim Bearbeiten in Word

# Word verlangt die Reihenfolge der Kindelemente aus dem Schema: neue Elemente vor diesen einfügen.
_NACH_TBLBORDERS = ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription")
_NACH_PBDR = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap", "w:overflowPunct",
              "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi", "w:adjustRightInd", "w:snapToGrid",
              "w:spacing", "w:ind", "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
              "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
              "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")
_NACH_PSHD = _NACH_PBDR[1:]
_NACH_TCSHD = ("w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark", "w:headers",
               "w:cellIns", "w:cellDel", "w:cellMerge", "w:tcPrChange")


def bauen(beschreibung: dict, ziel: Path, profil: dict | None = None) -> Path:
    """Baut das Arbeitsblatt nach `ziel` (.docx). `beschreibung` aus pruefung.lesen(), `profil` siehe design.py."""
    b = _Bau(design.profil_lesen(profil))
    b.kopf(beschreibung["titel"], beschreibung["nummer"])
    for block in beschreibung["bloecke"]:
        getattr(b, block["typ"])(block)
    b.d.save(ziel)
    return ziel


class _Bau:
    """Baut ein Dokument Block für Block. Merkt sich die laufende Aufgabennummer und die Textbreite."""

    def __init__(self, profil: dict):
        self.profil = profil
        self.aufgabe_nr = 0
        self.d = docx.Document()
        self._seite(self.d.sections[0], querformat=False)
        self._stile()

    @property
    def textbreite_cm(self) -> float:
        s = self.d.sections[-1]
        return round((s.page_width - s.left_margin - s.right_margin) / 360000, 2)

    # Seite und Stile

    def _seite(self, s, querformat: bool):
        breite, hoehe = SEITE_CM if not querformat else SEITE_CM[::-1]
        s.orientation = WD_ORIENT.LANDSCAPE if querformat else WD_ORIENT.PORTRAIT
        s.page_width, s.page_height = Cm(breite), Cm(hoehe)
        s.left_margin = s.right_margin = Cm(RAND_CM)
        s.top_margin = s.bottom_margin = Cm(RAND_OBEN_UNTEN_CM)

    def _stile(self):
        p = self.profil
        self.d.core_properties.author = ""  # sonst "python-docx"
        self.d.core_properties.last_modified_by = ""
        _xml_standardschrift(self.d, p["schrift"])
        normal = self.d.styles["Normal"]
        _xml_schrift(normal, p["schrift"])
        normal.font.size = Pt(p["schriftgroesse_pt"])
        f = normal.paragraph_format
        f.line_spacing, f.space_before, f.space_after = p["zeilenabstand"], Pt(0), Pt(0)
        _xml_sprache(normal)
        for ebene, groesse in UEBERSCHRIFT_PT.items():
            stil = self.d.styles[f"Heading {ebene}"]
            _xml_schrift(stil, p["schrift"])
            stil.font.size, stil.font.bold, stil.font.italic = Pt(groesse), True, False
            stil.font.color.rgb = RGBColor(0, 0, 0)
            stil.paragraph_format.space_before, stil.paragraph_format.space_after = Pt(12), Pt(3)

    # Kopf

    def kopf(self, titel: str, nummer: str):
        """Tabelle wie bei Lia: | Fach | Thema (farbig) | Datum: | / | | | Name: | / | Lehrkraft | Nummer | |."""
        p = self.profil
        self.d.core_properties.title = titel
        t = self.d.add_table(rows=3, cols=3)
        _xml_rahmen(t)
        _breiten(t, KOPF_SPALTEN_CM)
        for reihe, hoehe in zip(t.rows, (0.75, 0.75, 0.5), strict=True):
            reihe.height, reihe.height_rule = Cm(hoehe), WD_ROW_HEIGHT_RULE.AT_LEAST
        fach = t.cell(0, 0).merge(t.cell(1, 0))
        thema = t.cell(0, 1).merge(t.cell(1, 1))
        name = t.cell(1, 2).merge(t.cell(2, 2))
        fach.paragraphs[0].add_run(p["fach"])
        thema.paragraphs[0].add_run(titel)
        thema.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        thema.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _xml_zelle_farbe(thema, p["farben"]["thema"])
        t.cell(0, 2).paragraphs[0].add_run("Datum:")
        name.paragraphs[0].add_run("Name:")
        t.cell(2, 0).paragraphs[0].add_run(p["lehrkraft"])
        unten = t.cell(2, 1).paragraphs[0]
        unten.add_run(f"{p['nummer_text']} {nummer}".strip())
        unten.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self._abstand()

    # Blöcke (Name = typ in der Beschreibung)

    def ueberschrift(self, block: dict):
        self.d.add_heading(block["text"], level=block["ebene"])

    def absatz(self, block: dict):
        self.d.add_paragraph(block["text"])

    def anweisung(self, block: dict):
        p = self.d.add_paragraph()
        p.add_run(block["text"]).bold = True
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.keep_with_next = True

    def merksatz(self, block: dict):
        # Absätze mit gleichem Rahmen fassen Word und LibreOffice zu einem Kasten zusammen.
        for p in self._mit_titel(block):
            _xml_absatz_rahmen(p, "thickThinSmallGap", "12", "000000", ("top", "left", "bottom", "right"),
                               abstand="4")
            _xml_absatz_farbe(p, self.profil["farben"]["merksatz"])
        self._abstand()

    def material(self, block: dict):
        for p in self._mit_titel(block):
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY  # Blocksatz wie bei Lia
            _xml_absatz_farbe(p, self.profil["farben"]["material"])

    def liste(self, block: dict):
        stil = "List Number" if block["nummeriert"] else "List Bullet"
        absaetze = [self.d.add_paragraph(punkt, style=stil) for punkt in block["punkte"]]
        if block["nummeriert"]:
            _xml_nummerierung_neu(self.d, stil, absaetze)

    def tabelle(self, block: dict):
        zeilen = ([block["kopf"]] if block["kopf"] else []) + block["zeilen"]
        t = self.d.add_table(rows=len(zeilen), cols=len(zeilen[0]))
        _xml_rahmen(t)
        _breiten(t, [self.textbreite_cm / len(zeilen[0])] * len(zeilen[0]))
        for nr, (reihe, werte) in enumerate(zip(t.rows, zeilen, strict=True)):
            ist_kopf = block["kopf"] is not None and nr == 0
            if block["zeilenhoehe_cm"] and not ist_kopf:
                reihe.height, reihe.height_rule = Cm(block["zeilenhoehe_cm"]), WD_ROW_HEIGHT_RULE.AT_LEAST
            for spalte, (zelle, wert) in enumerate(zip(reihe.cells, werte, strict=True)):
                run = zelle.paragraphs[0].add_run(wert)
                run.bold = ist_kopf or (block["erste_spalte_fett"] and spalte == 0)
        if block["kopf"]:
            _xml_zeile_wiederholen(t.rows[0])
        self._abstand()

    def neue_seite(self, block: dict):
        self._seite(self.d.add_section(WD_SECTION.NEW_PAGE), querformat=block["querformat"])

    def aufgaben(self, block: dict):
        if block["titel"]:
            p = self.d.add_paragraph()
            p.add_run(block["titel"]).bold = True
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.keep_with_next = True
        hilfen = []
        for aufgabe in block["aufgaben"]:
            self.aufgabe_nr += 1
            self._aufgabe(aufgabe, self.aufgabe_nr)
            if aufgabe["hilfe"]:
                hilfen.append((self.aufgabe_nr, aufgabe["hilfe"]))
        for i, (nr, text) in enumerate(hilfen):
            p = self.d.add_paragraph()
            p.paragraph_format.space_before = Pt(14 if i == 0 else 0)
            p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(1.6), Cm(-1.6)
            p.paragraph_format.tab_stops.add_tab_stop(Cm(1.6))
            p.add_run(f"Aufgabe {nr}:\t").bold = True
            p.add_run(text)
            for run in p.runs:
                run.font.size = Pt(HILFE_PT)

    def _aufgabe(self, aufgabe: dict, nr: int):
        p = self.d.add_paragraph()
        f = p.paragraph_format
        f.space_before = Pt(8)
        f.left_indent, f.first_line_indent = Cm(EINZUG_AUFGABE_CM), Cm(-0.7)
        f.tab_stops.add_tab_stop(Cm(EINZUG_AUFGABE_CM))
        p.add_run(f"{nr}.\t{aufgabe['text']}").bold = True
        antwort = aufgabe["antwort"]
        if antwort is None:
            return
        f.keep_with_next = True  # Aufgabe nicht von ihrem Antwortplatz trennen
        art = antwort["art"]
        if art == "linien":
            self._linien(antwort["anzahl"])
        elif art == "kasten":
            self._kasten(antwort["hoehe_cm"])
        elif art == "ankreuzen":
            self._ankreuzen(antwort["optionen"])
        else:
            for satz in antwort["saetze"]:
                anfang = self.d.add_paragraph(satz["anfang"])
                anfang.paragraph_format.space_before = Pt(6)
                anfang.paragraph_format.keep_with_next = True
                self._linien(satz["linien"])

    def _ankreuzen(self, optionen: list[str]):
        p = self.d.add_paragraph()
        p.paragraph_format.left_indent = Cm(EINZUG_AUFGABE_CM)
        p.paragraph_format.space_before = Pt(4)
        for i, option in enumerate(optionen):
            _xml_symbol(p, *ANKREUZ_ZEICHEN)
            p.add_run(f" {option}" + ("        " if i < len(optionen) - 1 else ""))

    def _linien(self, anzahl: int):
        for i in range(anzahl):
            linie = self.d.add_paragraph()
            f = linie.paragraph_format
            f.line_spacing = Cm(self.profil["linienabstand_cm"])  # Länge heißt: genau diese Höhe
            f.space_before = f.space_after = 0
            f.keep_with_next = i < anzahl - 1
            _xml_absatz_rahmen(linie, "single", "4", LINIENFARBE, ("bottom", "between"), abstand="1")

    def _kasten(self, hoehe_cm: float):
        t = self.d.add_table(rows=1, cols=1)
        _xml_rahmen(t)
        reihe = t.rows[0]
        reihe.height, reihe.height_rule = Cm(hoehe_cm), WD_ROW_HEIGHT_RULE.EXACTLY
        _breiten(t, [self.textbreite_cm])
        self._abstand()

    # Hilfen

    def _mit_titel(self, block: dict) -> list:
        """Titel fett (falls vorhanden) und je Zeile des Texts ein Absatz. Nicht mit Zeilenumbruch in einem
        Absatz: Im Blocksatz würde die Zeile davor über die ganze Breite gezogen."""
        absaetze = []
        if block["titel"]:
            absaetze.append(self.d.add_paragraph())
            absaetze[0].add_run(block["titel"]).bold = True
        absaetze += [self.d.add_paragraph(zeile) for zeile in block["text"].split("\n")]
        return absaetze

    def _abstand(self):
        """Leerer Absatz, z. B. nach jeder Tabelle: Zwei Tabellen hintereinander verschmelzen in Word."""
        self.d.add_paragraph()


def _breiten(t, breiten_cm):
    """Spaltenbreiten fest setzen: im Raster (das liest LibreOffice) und in jeder Zelle (das liest Word)."""
    t.autofit = False
    for spalte, breite in zip(t.columns, breiten_cm, strict=True):
        spalte.width = Cm(breite)
        for zelle in spalte.cells:
            zelle.width = Cm(breite)


def _xml_standardschrift(d, name: str):
    """Schrift der Dokument-Standards setzen und die Theme-Schrift entfernen (sie hätte Vorrang)."""
    standard = d.styles.element.find(qn("w:docDefaults"))
    if standard is None:
        return
    for rfonts in standard.iter(qn("w:rFonts")):
        _rfonts_setzen(rfonts, name)


def _xml_schrift(stil, name: str):
    stil.font.name = name
    _rfonts_setzen(stil.element.rPr.rFonts, name)


def _rfonts_setzen(rfonts, name: str):
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rfonts.attrib.pop(qn(attr), None)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def _xml_sprache(stil):
    rpr = stil.element.get_or_add_rPr()
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.insert_element_before(lang, "w:eastAsianLayout", "w:specVanish", "w:oMath")
    lang.set(qn("w:val"), SPRACHE)


def _linie(name: str, art: str, staerke: str, farbe: str, abstand: str = "0"):
    linie = OxmlElement(f"w:{name}")
    linie.set(qn("w:val"), art)
    linie.set(qn("w:sz"), staerke)  # Achtelpunkte
    linie.set(qn("w:space"), abstand)
    linie.set(qn("w:color"), farbe)
    return linie


def _xml_rahmen(t):
    """Einfache schwarze Linien um und in der Tabelle, unabhängig von den Stilen der Vorlage."""
    rahmen = OxmlElement("w:tblBorders")
    for seite in ("top", "left", "bottom", "right", "insideH", "insideV"):
        rahmen.append(_linie(seite, "single", "4", "000000"))
    t._tbl.tblPr.insert_element_before(rahmen, *_NACH_TBLBORDERS)


def _xml_absatz_rahmen(p, art: str, staerke: str, farbe: str, seiten: tuple, abstand: str):
    """Rahmen um einen Absatz. Für Schreiblinien 'bottom' und 'between': Word fasst Absätze mit gleichem Rahmen
    zu einer Gruppe zusammen und zeichnet den unteren Rahmen sonst nur unter dem letzten."""
    rahmen = OxmlElement("w:pBdr")
    for seite in seiten:
        rahmen.append(_linie(seite, art, staerke, farbe, abstand))
    p._p.get_or_add_pPr().insert_element_before(rahmen, *_NACH_PBDR)


def _schattierung(farbe: str):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), farbe)
    return shd


def _xml_absatz_farbe(p, farbe: str):
    p._p.get_or_add_pPr().insert_element_before(_schattierung(farbe), *_NACH_PSHD)


def _xml_zelle_farbe(zelle, farbe: str):
    zelle._tc.get_or_add_tcPr().insert_element_before(_schattierung(farbe), *_NACH_TCSHD)


def _xml_symbol(p, schrift: str, zeichen: str):
    """Zeichen aus einer Symbolschrift (w:sym), so wie Word es selbst für Wingdings speichert."""
    sym = OxmlElement("w:sym")
    sym.set(qn("w:font"), schrift)
    sym.set(qn("w:char"), zeichen)
    p.add_run()._r.append(sym)


def _xml_zeile_wiederholen(reihe):
    """Kopfzeile der Tabelle auf jeder Seite wiederholen."""
    kopf = OxmlElement("w:tblHeader")
    kopf.set(qn("w:val"), "true")
    reihe._tr.get_or_add_trPr().append(kopf)


def _xml_nummerierung_neu(d, stil: str, absaetze):
    """Nummerierte Liste bei 1 beginnen. Ohne das zählt Word über alle Listen des Stils weiter."""
    nummerierung = d.part.numbering_part.element
    stil_num = d.styles[stil].element.pPr.numPr.numId.val
    abstrakt = nummerierung.num_having_numId(stil_num).abstractNumId.val
    neu = nummerierung.add_num(abstrakt)
    neu.add_lvlOverride(ilvl=0).add_startOverride(1)
    for p in absaetze:
        p._p.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = neu.numId
