"""Arbeitsmappe bauen: Formeln je Zeile, Eingabeprüfung, Formate, fixierter Kopf, Druck, Texte bleiben Text."""

import copy
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from renderer import arbeitsmappe
from renderer.pruefung import lesen
from tests.test_pruefung import NOTEN

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def bauen(beschreibung: dict, profil: dict | None = None) -> dict[str, str]:
    """Baut die Mappe und gibt die XML-Teile als Text zurück (Name -> Inhalt)."""
    ziel = Path(tempfile.mkdtemp()) / "mappe.xlsx"
    arbeitsmappe.bauen(lesen(beschreibung), ziel, profil)
    with zipfile.ZipFile(ziel) as z:
        return {n: z.read(n).decode("utf-8") for n in z.namelist()}


def zelle(xml: str, adresse: str) -> str:
    treffer = re.search(rf'<c r="{adresse}"[^>]*?(/>|>.*?</c>)', xml)
    return treffer.group(0) if treffer else ""


class TestNotentabelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teile = bauen(NOTEN, {"farben": {"tabellenkopf": "EAEADA"}})
        cls.blatt = cls.teile["xl/worksheets/sheet1.xml"]

    def test_aufbau(self):
        # Zeile 1 Titel, 2 Hinweis, 3 Abstand, 4 Kopf, 5 bis 39 die 35 Zeilen
        texte = re.findall(r"<t[^>]*>(.*?)</t>", self.teile["xl/sharedStrings.xml"])
        self.assertEqual(texte[:4], ["Notenübersicht Ethik", "Notenpunkte 0 bis 15 eintragen.", "Nr.", "Name"])
        self.assertIn('<mergeCell ref="A1:J1"/>', self.blatt)
        self.assertIn('<mergeCell ref="A2:J2"/>', self.blatt)
        self.assertIn("<v>1</v>", zelle(self.blatt, "A5"))
        self.assertIn("<v>35</v>", zelle(self.blatt, "A39"))
        self.assertEqual(zelle(self.blatt, "A40"), "")

    def test_formeln_je_zeile(self):
        self.assertIn('<f>IF(COUNT(C5:G5)=0,"",AVERAGE(C5:G5))</f>', zelle(self.blatt, "H5"))
        self.assertIn('<f>IF(COUNT(C39:G39)=0,"",AVERAGE(C39:G39))</f>', zelle(self.blatt, "H39"))
        endnote = zelle(self.blatt, "J17")
        self.assertIn("IF(OR(COUNT(H17)=0,COUNT(I17)=0),H17,2/3*H17+1/3*I17)", endnote.replace("&quot;", '"'))
        # Leere Zeile: leerer Wert statt 0, damit auch ohne Neuberechnung nichts Falsches erscheint
        self.assertTrue(endnote.endswith("</f><v></v></c>"), endnote)

    def test_eingabepruefung(self):
        regeln = re.findall(r"<dataValidation .*?</dataValidation>", self.blatt)
        self.assertEqual(len(regeln), 6)  # Note 1-5 und LEK
        note1 = next(r for r in regeln if 'sqref="C5:C39"' in r)
        self.assertIn('type="whole"', note1)
        self.assertIn('error="Bitte eine ganze Zahl von 0 bis 15 eintragen."', note1)
        self.assertIn('allowBlank="1"', note1)
        self.assertIn("<formula1>0</formula1><formula2>15</formula2>", note1)

    def test_formate_und_farben(self):
        stile = self.teile["xl/styles.xml"]
        self.assertIn('formatCode="0.00"', stile)
        self.assertIn('rgb="FFEAEADA"', stile)  # Kopf aus dem Profil
        self.assertIn('rgb="FFF2F2F2"', stile)  # Rechenfelder (Standard)
        self.assertIn('<name val="Calibri"/>', stile)

    def test_fixiert_und_druck(self):
        self.assertIn('<pane xSplit="2" ySplit="4" topLeftCell="C5" activePane="bottomRight" state="frozen"/>',
                      self.blatt)
        self.assertIn('<pageSetUpPr fitToPage="1"/>', self.blatt)
        self.assertTrue('<pageSetup paperSize="9" orientation="landscape"/>' in self.blatt)  # eine Seite
        self.assertIn('<oddFooter>&amp;CSeite &amp;P von &amp;N</oddFooter>', self.blatt)
        mappe = self.teile["xl/workbook.xml"]
        self.assertIn("<definedName name=\"_xlnm.Print_Titles\" localSheetId=\"0\">Noten!$1:$4</definedName>", mappe)
        self.assertIn("<definedName name=\"_xlnm.Print_Area\" localSheetId=\"0\">Noten!$A$1:$J$39</definedName>",
                      mappe)

    def test_kein_blattschutz(self):
        self.assertNotIn("sheetProtection", self.blatt)


class TestEinzelheiten(unittest.TestCase):
    def blatt(self, **felder) -> dict:
        b = {"name": "Liste", "zeilen": 2, "spalten": [{"id": "a", "kopf": "A", "art": "text"}]}
        b.update(felder)
        return {"art": "arbeitsmappe", "titel": "Test", "blaetter": [b]}

    def test_text_mit_gleichheitszeichen_bleibt_text(self):
        d = self.blatt(titel="=HYPERLINK(\"http://x\")", hinweise=["=1+1", "https://example.com"],
                       spalten=[{"id": "a", "kopf": "=SUM(A1:A9)", "art": "text"}])
        teile = bauen(d)
        self.assertNotIn("<f>", teile["xl/worksheets/sheet1.xml"])
        self.assertNotIn("hyperlink", teile["xl/worksheets/sheet1.xml"].lower())
        self.assertIn("=SUM(A1:A9)", teile["xl/sharedStrings.xml"])

    def test_ohne_titel_und_hochformat(self):
        teile = bauen(self.blatt(hochformat=True))
        blatt = teile["xl/worksheets/sheet1.xml"]
        self.assertIn("<v>0</v>", zelle(blatt, "A1"))  # Kopf in Zeile 1 (erster gemeinsamer Text)
        self.assertIn('ySplit="1" topLeftCell="A2"', blatt)
        self.assertTrue('<pageSetup paperSize="9" orientation="portrait"/>' in blatt)
        self.assertNotIn("mergeCell", blatt)

    def test_pruefregeln(self):
        def regel(**spalte):
            return arbeitsmappe.pruefregel({"art": "zahl", "ganz": False, "min": None, "max": None,
                                            "max_zeichen": None, "nachkommastellen": None, **spalte})

        self.assertEqual(regel()["error_message"], "Bitte eine Zahl eintragen.")
        self.assertEqual(regel()["minimum"], -1e9)
        self.assertEqual(regel(min=0.5)["error_message"], "Bitte eine Zahl ab 0,5 eintragen.")
        self.assertEqual(regel(ganz=True, max=6)["error_message"], "Bitte eine ganze Zahl bis 6 eintragen.")
        self.assertEqual(regel(ganz=True, max=6)["validate"], "integer")
        text = arbeitsmappe.pruefregel({"art": "text", "max_zeichen": 20})
        self.assertEqual((text["validate"], text["value"]), ("length", 20))
        self.assertIsNone(arbeitsmappe.pruefregel({"art": "text", "max_zeichen": None}))

    def test_zahlformate(self):
        def fmt(**spalte):
            return arbeitsmappe.zahlformat({"art": "zahl", "ganz": False, "nachkommastellen": None, **spalte})

        self.assertIsNone(fmt())
        self.assertEqual(fmt(ganz=True), "0")
        self.assertEqual(fmt(nachkommastellen=0), "0")
        self.assertEqual(fmt(nachkommastellen=3), "0.000")
        self.assertEqual(fmt(art="rechnung", nachkommastellen=2), "0.00")

    def test_mehrere_blaetter(self):
        d = copy.deepcopy(NOTEN)
        d["blaetter"].append(self.blatt()["blaetter"][0])
        teile = bauen(d)
        self.assertIn('<sheet name="Liste" sheetId="2"', teile["xl/workbook.xml"])
        self.assertIn("xl/worksheets/sheet2.xml", teile)

    def test_konstante_rechnung_hat_wert(self):
        d = self.blatt(spalten=[{"id": "a", "kopf": "A", "art": "rechnung", "formel": "2 * 3"},
                                {"id": "b", "kopf": "B", "art": "rechnung", "formel": "anzahl(a)"}])
        blatt = bauen(d)["xl/worksheets/sheet1.xml"]
        self.assertIn("<f>2*3</f><v>6</v>", zelle(blatt, "A2"))
        self.assertIn("<f>COUNT(A2)</f><v>1</v>", zelle(blatt, "B2"))

    def test_proben_sonderfaelle(self):
        d = self.blatt(spalten=[
            {"id": "a", "kopf": "A", "art": "zahl", "min": -4},
            {"id": "b", "kopf": "B", "art": "zahl", "max": 0},
            {"id": "q", "kopf": "Quote", "art": "rechnung", "formel": "a / b", "nachkommastellen": 1}])
        zeilen = arbeitsmappe.proben(lesen(d)).split("\n")
        self.assertEqual(zeilen[1], "Probe 1 (alle Eingaben am Minimum): A -4; B 0 -> Quote #DIV/0!")
        self.assertEqual(zeilen[2], "Probe 2 (alle Eingaben am Maximum): A 10; B 0 -> Quote #DIV/0!")
        self.assertEqual(zeilen[4], "Probe 4 (jede zweite Eingabe leer, die übrigen in der Mitte): A 3; B leer "
                                    "-> Quote leer")
        self.assertEqual(arbeitsmappe.proben(lesen(self.blatt())), "")  # ohne Rechnung keine Probe
        ohne_eingabe = self.blatt(spalten=[{"id": "a", "kopf": "A", "art": "rechnung", "formel": "1/3"}])
        self.assertIn("keine Eingaben -> A 0,33", arbeitsmappe.proben(lesen(ohne_eingabe)))

    def test_lange_liste_auf_seitenbreite(self):
        blatt = bauen(self.blatt(zeilen=60))["xl/worksheets/sheet1.xml"]
        self.assertTrue('<pageSetup paperSize="9" fitToHeight="0" orientation="landscape"/>' in blatt)

    def test_massstab_eine_seite(self):
        kopf = [21, 13.5, 13.5, 15, 30]  # Lias Notentabelle: Titel, 2 Hinweise, Abstand, Kopf
        breiten = [5, 28, 9, 9, 9, 9, 9, 12, 9, 12]
        self.assertAlmostEqual(arbeitsmappe.massstab_eine_seite(kopf + [15] * 35, breiten, False), 0.80, delta=0.01)
        self.assertLess(arbeitsmappe.massstab_eine_seite(kopf + [15] * 60, breiten, False), arbeitsmappe.MIN_MASSSTAB)
        self.assertEqual(arbeitsmappe.massstab_eine_seite([15] * 3, [10], False), 1.0)
        # Hochformat: zu breit für eine Seite, die Breite bestimmt den Maßstab
        self.assertLess(arbeitsmappe.massstab_eine_seite([15] * 3, breiten, True), 0.9)

    def test_keine_vorlage(self):
        with self.assertRaisesRegex(ValueError, "Vorlagen gibt es für xlsx nicht"):
            arbeitsmappe.bauen(lesen(self.blatt()), Path(tempfile.mkdtemp()) / "x.xlsx", vorlage=Path("v.xlsx"))


if __name__ == "__main__":
    unittest.main()
