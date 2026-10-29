"""Öffentliche Schnittstelle renderer.bauen() und Kontrolltext."""

import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from renderer import BeschreibungUngueltig, Ergebnis, bauen, kontrolle, vorschau
from tests.test_pruefung import NOTEN

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

    def test_kontrolltext_arbeitsmappe(self):
        e = bauen(NOTEN, self.tmp / "noten.xlsx", vorschau=False)
        zeilen = e.kontrolltext.split("\n")
        pruefung = "Eingabe, Prüfung ganze Zahl 0 bis 15, Meldung „Bitte eine ganze Zahl von 0 bis 15 eintragen.“, Format 0"
        self.assertEqual(zeilen[:7], [
            "=== Blatt „Noten“ (A4 quer auf Seitenbreite, fixiert bis Zeile 4 und Spalte B, 35 Zeilen zum Ausfüllen "
            "ab Zeile 5)",
            "Zeile 1: Notenübersicht Ethik",
            "Zeile 2: Notenpunkte 0 bis 15 eintragen.",
            "A „Nr.“ (Breite 5): laufende Nummer 1 bis 35, Format 0",
            "B „Name“ (Breite 28): Eingabe, ohne Prüfung",
            f"C „Note 1“ (Breite 9): {pruefung}",
            f"D „Note 2“ (Breite 9): {pruefung}",
        ])
        self.assertEqual(zeilen[10], 'H „Durchschnitt“ (Breite 12): Rechnung =WENN(ANZAHL(C5:G5)=0;"";MITTELWERT(C5:G5)), '
                                     "gleich in allen Zeilen bis 39, Format 0.00, hinterlegt F2F2F2")
        self.assertEqual(zeilen[11], f"I „LEK“ (Breite 9): {pruefung}")
        self.assertTrue(zeilen[12].startswith("J „Endnote“ (Breite 12): Rechnung =WENN(UND("), zeilen[12])
        self.assertEqual(zeilen[13], "Probe für Blatt „Noten“ (vom Renderer nachgerechnet, steht nicht in der Datei):")
        self.assertEqual(zeilen[16], "Probe 3 (aufsteigend vom Minimum zum Maximum): Note 1 0; Note 2 3; Note 3 6; "
                                     "Note 4 9; Note 5 12; LEK 15 -> Durchschnitt 6,00; Endnote 9,00")
        self.assertEqual(len(zeilen), 19)

    def test_kontrolle_findet_abweichende_formel(self):
        e = bauen(NOTEN, self.tmp / "noten.xlsx", vorschau=False)
        ziel = self.tmp / "geaendert.xlsx"
        with zipfile.ZipFile(e.pfad) as quelle, zipfile.ZipFile(ziel, "w") as neu:
            for name in quelle.namelist():
                inhalt = quelle.read(name)
                if name == "xl/worksheets/sheet1.xml":
                    inhalt = inhalt.replace(b"AVERAGE(C17:G17)", b"AVERAGE(C17:F17)")
                neu.writestr(name, inhalt)
        self.assertIn("ABWEICHEND in Zeile 17", kontrolle.kontrolltext(ziel))

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

    @unittest.skipUnless(shutil.which(vorschau.SOFFICE), "LibreOffice nicht installiert")
    def test_mit_vorschau_arbeitsmappe(self):
        e = bauen(NOTEN, self.tmp / "noten.xlsx")
        self.assertEqual(e.hinweise, [])
        self.assertEqual([b.name for b in e.bilder], ["noten-seite-01.png", "noten-seite-02.png"])  # 35 Zeilen
        self.assertTrue(e.pdf.is_file())


class TestKontrolle(unittest.TestCase):
    def test_andere_endung(self):
        with self.assertRaisesRegex(ValueError, "nur .docx, .pptx oder .xlsx"):
            kontrolle.kontrolltext(Path("x.pdf"))


if __name__ == "__main__":
    unittest.main()
