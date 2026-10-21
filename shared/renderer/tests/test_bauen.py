"""Öffentliche Schnittstelle renderer.bauen() und Kontrolltext."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from renderer import BeschreibungUngueltig, Ergebnis, bauen, kontrolle, vorschau

BLATT = {"art": "arbeitsblatt", "titel": "Thema", "nummer": "3", "bloecke": [
    {"typ": "merksatz", "titel": "Merksatz:", "text": "Merk dir das."},
    {"typ": "material", "text": "Text"},
    {"typ": "aufgaben", "aufgaben": [
        {"text": "Kreuze an!", "antwort": {"art": "ankreuzen", "optionen": ["A", "B"]}},
        {"text": "Schreibe.", "antwort": {"art": "linien", "anzahl": 3}, "hilfe": "Tipp"},
        {"text": "Zeichne.", "antwort": {"art": "kasten", "hoehe_cm": 5}}]},
    {"typ": "liste", "punkte": ["x", "y"], "nummeriert": True},
    {"typ": "neue_seite", "querformat": True},
    {"typ": "ueberschrift", "text": "Tabelle", "ebene": 2},
    {"typ": "tabelle", "kopf": ["", "Singer"], "zeilen": [["Behauptung", ""]]}]}
FOLIEN = {"art": "folien", "titel": "Thema", "icon": "buch", "folien": [
    {"titel": "Eins", "icons": ["ziel"], "inhalt": [{"typ": "punkte", "punkte": ["a", "b"]},
                                                     {"typ": "satzanfang", "text": "Ich finde …"}]}]}
PROFIL = {"fach": "Ethik", "lehrkraft": "Frau Muster"}


class TestBauen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_kontrolltext_arbeitsblatt(self):
        e = bauen(json.dumps(BLATT), self.tmp / "blatt.docx", PROFIL, vorschau=False)
        self.assertIsInstance(e, Ergebnis)
        self.assertEqual((e.bilder, e.pdf, e.hinweise), ([], None, []))
        self.assertEqual(e.kontrolltext.split("\n"), [
            "| Ethik | Thema | Datum: |",
            "| Name: |",
            "| Frau Muster | Arbeitsblatt 3 |",
            "[Kasten] Merksatz:",
            "[Kasten] Merk dir das.",
            "[hinterlegt] Text",
            "Aufgaben:",
            "1.\tKreuze an!",
            "☐ A        ☐ B",
            "2.\tSchreibe.",
            "[3 Schreiblinien]",
            "3.\tZeichne.",
            "[leerer Kasten, 5.0 cm hoch]",
            "Aufgabe 2:\tTipp",
            "1. x",
            "2. y",
            "--- neue Seite (quer)",
            "## Tabelle",
            "| … | Singer |",
            "| Behauptung | … |",
        ])

    def test_kontrolltext_folien(self):
        e = bauen(FOLIEN, self.tmp / "f.pptx", vorschau=False)
        self.assertEqual(e.kontrolltext.split("\n"), [
            "--- Folie 1", "Thema", "[Icon: buch]",
            "--- Folie 2", "Eins", "[Icon: ziel]", "• a", "• b", "[Icon: zeigefinger]", "„Ich finde …“",
        ])

    def test_falsche_endung(self):
        with self.assertRaisesRegex(ValueError, "Für art 'folien' muss das Ziel auf .pptx enden"):
            bauen(FOLIEN, self.tmp / "f.docx", vorschau=False)

    def test_fehler_fuer_claude(self):
        with self.assertRaises(BeschreibungUngueltig):
            bauen({"art": "folien"}, self.tmp / "f.pptx", vorschau=False)
        self.assertEqual(list(self.tmp.iterdir()), [])  # nichts gebaut

    def test_vorschau_fehlt_ist_nur_hinweis(self):
        alt = vorschau.SOFFICE
        vorschau.SOFFICE = "gibt-es-nicht-soffice"
        try:
            with self.assertLogs("renderer", "WARNING"):
                e = bauen(BLATT, self.tmp / "blatt.docx", vorschau=True)
        finally:
            vorschau.SOFFICE = alt
        self.assertTrue(e.pfad.is_file())
        self.assertEqual(e.bilder, [])
        self.assertEqual(e.hinweise, ["Keine Vorschau: LibreOffice (soffice) ist nicht installiert"])

    @unittest.skipUnless(shutil.which(vorschau.SOFFICE), "LibreOffice nicht installiert")
    def test_mit_vorschau(self):
        e = bauen(FOLIEN, self.tmp / "f.pptx")
        self.assertEqual([b.name for b in e.bilder], ["f-seite-01.png", "f-seite-02.png"])
        self.assertEqual(e.bilder[0].parent, self.tmp / "f-vorschau")
        self.assertTrue(e.pdf.is_file())


class TestKontrolle(unittest.TestCase):
    def test_andere_endung(self):
        with self.assertRaisesRegex(ValueError, "nur .docx oder .pptx"):
            kontrolle.kontrolltext(Path("x.pdf"))


if __name__ == "__main__":
    unittest.main()
