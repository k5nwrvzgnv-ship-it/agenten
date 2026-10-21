"""Arbeitsblatt als docx: bauen, wieder öffnen, Inhalt und Aufbau prüfen."""

import itertools
import tempfile
import unittest
from pathlib import Path

import docx
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn

from renderer import arbeitsblatt
from renderer.pruefung import lesen

BLATT = {
    "art": "arbeitsblatt",
    "titel": "Der kategorische Imperativ",
    "kopfzeile": ["Name", "Klasse", "Datum"],
    "bloecke": [
        {"typ": "ueberschrift", "text": "Einstieg"},
        {"typ": "absatz", "text": "Erste Zeile\nzweite Zeile"},
        {"typ": "liste", "punkte": ["Maxime", "Gesetz"]},
        {"typ": "liste", "punkte": ["eins", "zwei"], "nummeriert": True},
        {"typ": "ueberschrift", "text": "Arbeitsauftrag", "ebene": 2},
        {"typ": "liste", "punkte": ["noch eins"], "nummeriert": True},
        {"typ": "tabelle", "kopf": ["Begriff", "Erklärung"], "zeilen": [["Maxime", ""], ["Pflicht", "aus Achtung"]]},
        {"typ": "aufgabe", "text": "Erkläre den Begriff.", "antwort": {"art": "linien", "anzahl": 3}},
        {"typ": "aufgabe", "text": "Zeichne ein Schaubild.", "antwort": {"art": "kasten", "hoehe_cm": 6.5}},
        {"typ": "aufgabe", "text": "Lies den Text."},
    ],
}


def bauen(beschreibung=BLATT) -> docx.document.Document:
    ziel = Path(tempfile.mkdtemp()) / "blatt.docx"
    arbeitsblatt.bauen(lesen(beschreibung), ziel)
    return docx.Document(ziel)


def absaetze(d, stil=None):
    return [p for p in d.paragraphs if stil is None or p.style.name == stil]


def cm(laenge) -> float:
    """Word speichert in Zwanzigstel-Punkt: auf 0,01 cm vergleichen."""
    return round(laenge.cm, 2)


def num_id(p):
    return p._p.pPr.numPr.numId.val


class TestArbeitsblatt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = bauen()

    def test_seite_a4_und_eigenschaften(self):
        s = self.d.sections[0]
        self.assertEqual((cm(s.page_width), cm(s.page_height)), (21, 29.7))
        self.assertEqual(cm(s.left_margin), 2)
        self.assertEqual(self.d.core_properties.title, "Der kategorische Imperativ")
        self.assertEqual(self.d.core_properties.author, "")
        self.assertEqual(self.d.styles["Normal"].element.rPr.find(qn("w:lang")).get(qn("w:val")), "de-DE")

    def test_titel_und_ueberschriften(self):
        self.assertEqual(self.d.paragraphs[0].text, "Der kategorische Imperativ")
        self.assertEqual(self.d.paragraphs[0].style.name, "Title")
        self.assertEqual([p.text for p in absaetze(self.d, "Heading 1")], ["Einstieg"])
        self.assertEqual([p.text for p in absaetze(self.d, "Heading 2")], ["Arbeitsauftrag"])

    def test_absatz_mit_zeilenumbruch(self):
        p = [p for p in self.d.paragraphs if p.text.startswith("Erste Zeile")][0]
        self.assertEqual(p.text, "Erste Zeile\nzweite Zeile")
        self.assertEqual(len(p._p.findall(".//" + qn("w:br"))), 1)

    def test_listen(self):
        self.assertEqual([p.text for p in absaetze(self.d, "List Bullet")], ["Maxime", "Gesetz"])
        nummeriert = absaetze(self.d, "List Number")
        self.assertEqual([p.text for p in nummeriert], ["eins", "zwei", "noch eins"])
        # jede nummerierte Liste beginnt neu bei 1: eigene Nummerierung je Liste, mit Start 1
        self.assertEqual(num_id(nummeriert[0]), num_id(nummeriert[1]))
        self.assertNotEqual(num_id(nummeriert[1]), num_id(nummeriert[2]))
        nummerierung = self.d.part.numbering_part.element
        for p in (nummeriert[0], nummeriert[2]):
            start = nummerierung.num_having_numId(num_id(p)).find(".//" + qn("w:startOverride"))
            self.assertEqual(start.get(qn("w:val")), "1")

    def test_tabelle(self):
        t = self.d.tables[0]
        self.assertEqual([[z.text for z in r.cells] for r in t.rows],
                         [["Begriff", "Erklärung"], ["Maxime", ""], ["Pflicht", "aus Achtung"]])
        self.assertTrue(all(run.bold for z in t.rows[0].cells for run in z.paragraphs[0].runs))
        self.assertIsNotNone(t.rows[0]._tr.trPr.find(qn("w:tblHeader")))
        self.assertIsNotNone(t._tbl.tblPr.find(qn("w:tblBorders")))

    def test_aufgaben_nummeriert(self):
        aufgaben = [p.text for p in self.d.paragraphs if p.text.startswith("Aufgabe")]
        self.assertEqual(aufgaben, ["Aufgabe 1: Erkläre den Begriff.", "Aufgabe 2: Zeichne ein Schaubild.",
                                    "Aufgabe 3: Lies den Text."])

    def test_antwortlinien(self):
        linien = [p for p in self.d.paragraphs if p._p.pPr is not None and p._p.pPr.find(qn("w:pBdr")) is not None]
        self.assertEqual(len(linien), 3)
        for p in linien:
            rahmen = p._p.pPr.find(qn("w:pBdr"))
            self.assertIsNotNone(rahmen.find(qn("w:bottom")))
            self.assertIsNotNone(rahmen.find(qn("w:between")))  # sonst nur eine Linie unter der Gruppe
            self.assertEqual(cm(p.paragraph_format.line_spacing), 0.9)
            self.assertEqual(p.paragraph_format.line_spacing_rule, WD_LINE_SPACING.EXACTLY)
        aufgabe = [p for p in self.d.paragraphs if p.text.startswith("Aufgabe 1")][0]
        self.assertTrue(aufgabe.paragraph_format.keep_with_next)
        self.assertEqual([p.paragraph_format.keep_with_next for p in linien], [True, True, False])

    def test_kasten(self):
        kasten = self.d.tables[1]
        self.assertEqual((len(kasten.rows), len(kasten.columns)), (1, 1))
        self.assertEqual(cm(kasten.rows[0].height), 6.5)
        self.assertEqual(kasten.rows[0].height_rule, WD_ROW_HEIGHT_RULE.EXACTLY)
        self.assertIsNotNone(kasten._tbl.tblPr.find(qn("w:tblBorders")))

    def test_tabellen_nie_direkt_hintereinander(self):
        koerper = list(self.d.element.body)
        for vorher, nachher in itertools.pairwise(koerper):
            self.assertFalse(vorher.tag == nachher.tag == qn("w:tbl"))

    def test_kopfzeile(self):
        kopf = self.d.sections[0].header
        self.assertEqual([z.text for z in kopf.tables[0].rows[0].cells], ["Name: \t", "Klasse: \t", "Datum: \t"])
        self.assertTrue(kopf.tables[0].rows[0].cells[0].paragraphs[0].runs[1].underline)

    def test_ohne_kopfzeile(self):
        d = dict(BLATT, kopfzeile=None)
        del d["kopfzeile"]
        self.assertEqual(bauen(d).sections[0].header.tables, [])

    def test_xml_reihenfolge_nach_schema(self):
        """Word lehnt Dateien mit falscher Reihenfolge ab: pBdr vor spacing, tblBorders vor tblLook."""
        for p in self.d.paragraphs:
            namen = [k.tag for k in p._p.pPr] if p._p.pPr is not None else []
            if qn("w:pBdr") in namen and qn("w:spacing") in namen:
                self.assertLess(namen.index(qn("w:pBdr")), namen.index(qn("w:spacing")))
        for t in self.d.tables:
            namen = [k.tag for k in t._tbl.tblPr]
            self.assertLess(namen.index(qn("w:tblBorders")), namen.index(qn("w:tblLook")))


if __name__ == "__main__":
    unittest.main()
