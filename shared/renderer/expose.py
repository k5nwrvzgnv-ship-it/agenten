"""Exposé als docx bauen, aus einer geprüften Beschreibung (pruefung.lesen).

Aufbau nach der Formatvorlage aus uni (Studienbeleg der HNEE, gemessen am 03.11.2026): Deckblatt mit Logo (aus dem
Profil), Einrichtung, Autorenzeile, Titel 22 pt und unten links dem Rahmen (Art, Semester, Studiengang, Modul,
Betreuung, Datum). Danach Text im Blocksatz mit Silbentrennung, Überschriften fett in Textgröße und nummeriert
(1, 1.1), Tabellen mit Linien nur oben, unter dem Kopf und unten, Literaturverzeichnis auf eigener Seite mit
hängendem Einzug. Keine Kopf- und Fußzeile, keine Seitenzahlen. Stellen "[OFFEN: ...]" sind fett und gelb
hinterlegt. Seite, Schrift und XML-Hilfen kommen aus arbeitsblatt.py, dessen Verhalten hier nicht geändert wird.
"""

import re
from pathlib import Path

from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from renderer import arbeitsblatt, design
from renderer.arbeitsblatt import _NACH_PBDR, _NACH_TBLBORDERS, _NACH_TCSHD, _breiten, _linie, _xml_zeile_wiederholen

OFFEN = re.compile(r"\[OFFEN:[^\]]*\]")
LINK = re.compile(r"https?://[^\s<>\"]+[^\s<>\".,;:)\]]")
TITEL_PT = 22
UNTERTITEL_PT = 14
TITELFARBE = "262626"  # wie in der Vorlage (Schwarz, 15 % heller)
RAHMEN_PT = 9
RAHMEN_ZEILE_PT = 14  # Zeilenabstand des Rahmens, gemessen
RAHMEN_OBEN_CM = 21.85  # Rahmen unten auf dem Deckblatt, vom oberen Seitenrand
DECKBLATT_ABSTAND_CM = 3.0  # vor Autorenzeile und Titel
TABELLE_PT = 10
TABELLENTITEL_PT = 9
TABELLENLINIE = ("12", "6")  # außen 1,5 pt, unter dem Kopf 0,75 pt (Achtelpunkte)
ABSTAND_NACH_PT = 10  # nach Absätzen, gemessen
UEBERSCHRIFT_ABSTAND_PT = {1: (12, 10), 2: (6, 6)}  # davor, danach
NUMMER_CM = 1.0  # Text der Überschrift nach der Nummer
LITERATUR_EINZUG_CM = 1.27  # hängend, APA
LITERATUR_ZEILENABSTAND = 1.88  # gemessen: 23,8 pt bei Arial 11
LITERATUR_TITEL = "Literaturverzeichnis"
# Einstellungen nach w:autoHyphenation (Reihenfolge des Schemas)
_NACH_SILBENTRENNUNG = ("w:consecutiveHyphenLimit", "w:hyphenationZone", "w:doNotHyphenateCaps",
                        "w:showEnvelope", "w:summaryLength", "w:clickAndTypeStyle", "w:defaultTableStyle",
                        "w:evenAndOddHeaders", "w:bookFoldRevPrinting", "w:bookFoldPrinting", "w:bookFoldPrintingSheets",
                        "w:drawingGridHorizontalSpacing", "w:drawingGridVerticalSpacing",
                        "w:displayHorizontalDrawingGridEvery", "w:displayVerticalDrawingGridEvery",
                        "w:doNotUseMarginsForDrawingGridOrigin", "w:drawingGridHorizontalOrigin",
                        "w:drawingGridVerticalOrigin", "w:doNotShadeFormData", "w:noPunctuationKerning",
                        "w:characterSpacingControl", "w:printTwoOnOne", "w:strictFirstAndLastChars",
                        "w:noLineBreaksAfter", "w:noLineBreaksBefore", "w:savePreviewPicture",
                        "w:doNotValidateAgainstSchema", "w:saveInvalidXml", "w:ignoreMixedContent",
                        "w:alwaysShowPlaceholderText", "w:doNotDemarcateInvalidXml", "w:saveXmlDataOnly",
                        "w:useXSLTWhenSaving", "w:saveThroughXslt", "w:showXMLTags", "w:alwaysMergeEmptyNamespace",
                        "w:updateFields", "w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr", "w:compat",
                        "w:docVars", "w:rsids", "w:attachedSchema", "w:themeFontLang",
                        "w:clrSchemeMapping", "w:doNotIncludeSubdocsInStats", "w:doNotAutoCompressPictures",
                        "w:forceUpgrade", "w:captions", "w:readModeInkLockDown", "w:smartTagType",
                        "w:shapeDefaults", "w:doNotEmbedSmartTags", "w:decimalSymbol",
                        "w:listSeparator")
_NACH_FRAMEPR = ("w:widowControl", "w:numPr", "w:suppressLineNumbers", "w:pBdr") + _NACH_PBDR


def bauen(beschreibung: dict, ziel: Path, profil: dict | None = None, vorlage: Path | None = None) -> Path:
    """Baut das Exposé nach `ziel` (.docx). `beschreibung` aus pruefung.lesen(), `profil` siehe design.py (Logo,
    Ränder), `vorlage` eine .docx (Seite und Ränder; Schriften kommen weiter aus dem Profil)."""
    profil = design.profil_lesen(profil)
    if profil["logo"] and not Path(profil["logo"]).is_file():
        raise ValueError(f"Logo {profil['logo']} gibt es nicht (Profil, Feld logo)")
    b = _Bau(profil, vorlage)
    b.deckblatt(beschreibung)
    for block in beschreibung["bloecke"]:
        getattr(b, block["typ"])(block)
    b.literatur(beschreibung["literatur"])
    b.d.save(ziel)
    return ziel


def offene_stellen(b: dict) -> list[str]:
    """Alle "[OFFEN: ...]" der Beschreibung in Lesereihenfolge (für den Kontrolltext)."""
    texte = [b["einrichtung"], *b["autoren"], b["titel"], b["untertitel"], b["rahmen"], *b["betreuung"], b["datum"]]
    for block in b["bloecke"]:
        texte += [block.get("text", ""), block.get("titel", "")] + block.get("punkte", [])
        texte += (block.get("kopf") or []) + [z for zeile in block.get("zeilen", []) for z in zeile]
    texte += b["literatur"]
    return [treffer for t in texte for treffer in OFFEN.findall(t or "")]


class _Bau(arbeitsblatt._Bau):
    """Wie das Arbeitsblatt, mit Deckblatt, eigenen Überschriften, Tabellen und Literatur."""

    def __init__(self, profil: dict, vorlage: Path | None):
        super().__init__(profil, vorlage)
        self.nummer = [0, 0]
        self.tabelle_nr = 0

    def _seite(self, s, querformat: bool):
        super()._seite(s, querformat)
        if not self.vorlage:
            p = self.profil
            s.top_margin, s.bottom_margin = Cm(p["rand_oben_cm"]), Cm(p["rand_unten_cm"])
            s.left_margin, s.right_margin = Cm(p["rand_links_cm"]), Cm(p["rand_rechts_cm"])

    def _stile(self):
        super()._stile()
        normal = self.d.styles["Normal"].paragraph_format
        normal.space_after = Pt(ABSTAND_NACH_PT)
        normal.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for ebene, (davor, danach) in UEBERSCHRIFT_ABSTAND_PT.items():
            stil = self.d.styles[f"Heading {ebene}"]
            stil.font.size = Pt(self.profil["schriftgroesse_pt"])
            stil.font.color.rgb = RGBColor(0, 0, 0)
            f = stil.paragraph_format
            f.space_before, f.space_after, f.keep_with_next = Pt(davor), Pt(danach), True
            f.alignment = WD_ALIGN_PARAGRAPH.LEFT
            f.left_indent, f.first_line_indent = Cm(NUMMER_CM), Cm(-NUMMER_CM)  # lange Titel unter dem Text
            f.tab_stops.add_tab_stop(Cm(NUMMER_CM))
        _xml_silbentrennung(self.d)

    # Deckblatt

    def deckblatt(self, b: dict):
        p = self.profil
        self.d.core_properties.title = b["titel"]
        if p["logo"]:
            logo = self._links()
            bild = logo.add_run().add_picture(p["logo"], width=Cm(p["logo_breite_cm"]))
            for seite in ("T", "B", "L", "R"):  # ohne Angabe rückt LibreOffice das Bild 0,32 cm ein
                bild._inline.set(f"dist{seite}", "0")
            logo.paragraph_format.space_after = Pt(0)
            self._links(b["einrichtung"]).paragraph_format.space_before = Pt(8)
        else:
            self._links(b["einrichtung"])
        self._links(" | ".join(b["autoren"])).paragraph_format.space_before = Cm(DECKBLATT_ABSTAND_CM)
        titel = self._links(b["titel"], groesse=TITEL_PT, farbe=TITELFARBE)
        titel.paragraph_format.space_before = Cm(DECKBLATT_ABSTAND_CM)
        if b["untertitel"]:
            self._links(b["untertitel"], groesse=UNTERTITEL_PT, farbe=TITELFARBE).paragraph_format.space_before = Pt(6)
        zeilen = b["rahmen"].split("\n") if b["rahmen"] else []
        if b["betreuung"]:
            zeilen.append("Betreuung: " + ", ".join(b["betreuung"]))
        zeilen.append(b["datum"])
        for i, zeile in enumerate(zeilen):
            absatz = self._links(zeile, groesse=RAHMEN_PT, fett=i == 0 and bool(b["rahmen"]))
            f = absatz.paragraph_format
            f.space_after, f.line_spacing = Pt(0), Pt(RAHMEN_ZEILE_PT)
            self._xml_rahmen_unten(absatz)
        self.d.add_section(WD_SECTION.NEW_PAGE)

    def _xml_rahmen_unten(self, absatz):
        """Absatz in einen Positionsrahmen fest unten auf dem Deckblatt (Absätze mit gleichem Rahmen bilden einen),
        damit die Lage nicht von der Länge des Titels abhängt."""
        rahmen = OxmlElement("w:framePr")
        breite = int(self.textbreite_cm / 2.54 * 1440)
        for name, wert in (("w", str(breite)), ("wrap", "notBeside"), ("vAnchor", "page"), ("hAnchor", "margin"),
                           ("xAlign", "left"), ("y", str(round(RAHMEN_OBEN_CM / 2.54 * 1440)))):
            rahmen.set(qn(f"w:{name}"), wert)
        absatz._p.get_or_add_pPr().insert_element_before(rahmen, *_NACH_FRAMEPR)

    # Blöcke (Name = typ in der Beschreibung)

    def ueberschrift(self, block: dict):
        ebene = block["ebene"]
        self.nummer[ebene - 1] += 1
        if ebene == 1:
            self.nummer[1] = 0
        p = self.d.add_heading(level=ebene)
        self._text(p, ".".join(str(n) for n in self.nummer[:ebene]) + "\t" + block["text"])

    def absatz(self, block: dict):
        for zeile in block["text"].split("\n"):  # je Zeile ein Absatz, sonst dehnt der Blocksatz die Zeile
            self._text(self.d.add_paragraph(), zeile)

    def liste(self, block: dict):
        name = "List Number" if block["nummeriert"] else "List Bullet"
        stil = self._stil(name)
        ohne_stil = stil is None or stil.element.pPr is None or stil.element.pPr.numPr is None
        absaetze = []
        for i, punkt in enumerate(block["punkte"], 1):
            if ohne_stil:  # Vorlage ohne Listenstil: Zeichen von Hand, mit hängendem Einzug
                p = self.d.add_paragraph(f"{i}.\t" if block["nummeriert"] else "•\t")
                p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(0.63), Cm(-0.63)
                p.paragraph_format.tab_stops.add_tab_stop(Cm(0.63))
            else:
                p = self.d.add_paragraph(style=name)
            self._text(p, punkt)
            p.paragraph_format.space_after = Pt(0)
            absaetze.append(p)
        absaetze[-1].paragraph_format.space_after = Pt(ABSTAND_NACH_PT)
        if block["nummeriert"] and not ohne_stil:
            arbeitsblatt._xml_nummerierung_neu(self.d, name, absaetze)

    def tabelle(self, block: dict):
        if block["titel"]:
            self.tabelle_nr += 1
            titel = self.d.add_paragraph()
            self._text(titel, f"Tabelle {self.tabelle_nr}: {block['titel']}", groesse=TABELLENTITEL_PT)
            f = titel.paragraph_format
            f.space_after, f.keep_with_next, f.alignment = Pt(3), True, WD_ALIGN_PARAGRAPH.LEFT
        zeilen = ([block["kopf"]] if block["kopf"] else []) + block["zeilen"]
        spalten = len(zeilen[0])
        t = self.d.add_table(rows=len(zeilen), cols=spalten)
        _xml_dreilinien(t)
        _breiten(t, _spaltenbreiten(zeilen, self.textbreite_cm))
        for nr, (reihe, werte) in enumerate(zip(t.rows, zeilen, strict=True)):
            ist_kopf = block["kopf"] is not None and nr == 0
            reihe.height, reihe.height_rule = Cm(0.6), WD_ROW_HEIGHT_RULE.AT_LEAST
            for zelle, wert in zip(reihe.cells, werte, strict=True):
                for i, zeile in enumerate(wert.split("\n")):
                    p = zelle.paragraphs[0] if i == 0 else zelle.add_paragraph()
                    f = p.paragraph_format
                    f.space_before, f.space_after, f.alignment = Pt(2), Pt(2), WD_ALIGN_PARAGRAPH.LEFT
                    self._text(p, zeile, groesse=TABELLE_PT, fett=ist_kopf)
                if ist_kopf:
                    _xml_zelle_linie_unten(zelle)
        if block["kopf"]:
            _xml_zeile_wiederholen(t.rows[0])
        unter = self.d.add_paragraph()  # trennt auch zwei Tabellen (siehe arbeitsblatt._abstand)
        unter.paragraph_format.space_after = Pt(0)

    def literatur(self, angaben: list[str]):
        if not angaben:
            return
        titel = self.d.add_heading(level=1)
        self._text(titel, LITERATUR_TITEL)
        f = titel.paragraph_format
        f.page_break_before, f.left_indent, f.first_line_indent = True, Cm(0), Cm(0)
        for angabe in angaben:
            p = self.d.add_paragraph()
            f = p.paragraph_format
            f.left_indent, f.first_line_indent = Cm(LITERATUR_EINZUG_CM), Cm(-LITERATUR_EINZUG_CM)
            f.line_spacing, f.space_after, f.alignment = LITERATUR_ZEILENABSTAND, Pt(0), WD_ALIGN_PARAGRAPH.LEFT
            rest = 0
            for treffer in LINK.finditer(angabe):
                self._text(p, angabe[rest:treffer.start()])
                self._link(p, treffer.group())
                rest = treffer.end()
            self._text(p, angabe[rest:])

    # Hilfen

    def _links(self, text: str = "", groesse: float | None = None, fett: bool = False, farbe: str | None = None):
        """Absatz des Deckblatts: linksbündig, ohne Abstand danach."""
        p = self.d.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        self._text(p, text, groesse=groesse, fett=fett, farbe=farbe)
        return p

    def _text(self, p, text: str, groesse: float | None = None, fett: bool = False, farbe: str | None = None):
        """Text als Runs anhängen, "[OFFEN: ...]" fett und gelb hinterlegt."""
        rest = 0
        teile = []
        for treffer in OFFEN.finditer(text):
            teile += [(text[rest:treffer.start()], False), (treffer.group(), True)]
            rest = treffer.end()
        teile.append((text[rest:], False))
        for teil, offen in teile:
            if not teil:
                continue
            run = p.add_run(teil)
            run.bold = fett or offen or None
            if offen:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            if groesse:
                run.font.size = Pt(groesse)
            if farbe:
                run.font.color.rgb = RGBColor.from_string(farbe)

    def _link(self, p, adresse: str):
        """Anklickbarer Link, gesetzt wie der übrige Text (so wie in der Vorlage)."""
        rid = p.part.relate_to(adresse, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
        link = OxmlElement("w:hyperlink")
        link.set(qn("r:id"), rid)
        run = OxmlElement("w:r")
        text = OxmlElement("w:t")
        text.text = adresse
        run.append(text)
        link.append(run)
        p._p.append(link)


def _spaltenbreiten(zeilen: list[list[str]], textbreite_cm: float) -> list[float]:
    """Breite nach dem längsten Inhalt der Spalte (4 bis 40 Zeichen), zusammen die Textbreite."""
    gewichte = [min(40, max(4, max(len(z[i]) for z in zeilen))) for i in range(len(zeilen[0]))]
    return [textbreite_cm * g / sum(gewichte) for g in gewichte]


def _xml_dreilinien(t):
    """Linien nur oben und unten an der Tabelle (die unter dem Kopf trägt die Kopfzeile)."""
    rahmen = OxmlElement("w:tblBorders")
    for seite in ("top", "left", "bottom", "right", "insideH", "insideV"):
        if seite in ("top", "bottom"):
            rahmen.append(_linie(seite, "single", TABELLENLINIE[0], "000000"))
        else:
            rahmen.append(_linie(seite, "nil", "0", "auto"))
    t._tbl.tblPr.insert_element_before(rahmen, *_NACH_TBLBORDERS)


def _xml_zelle_linie_unten(zelle):
    rahmen = OxmlElement("w:tcBorders")
    rahmen.append(_linie("bottom", "single", TABELLENLINIE[1], "000000"))
    zelle._tc.get_or_add_tcPr().insert_element_before(rahmen, "w:shd", *_NACH_TCSHD)


def _xml_silbentrennung(d):
    """Automatische Silbentrennung in Word (Sprache steht im Stil Normal)."""
    einstellungen = d.settings.element
    if einstellungen.find(qn("w:autoHyphenation")) is None:
        an = OxmlElement("w:autoHyphenation")
        einstellungen.insert_element_before(an, *_NACH_SILBENTRENNUNG)
