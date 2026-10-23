import tempfile
import unittest
from pathlib import Path

import normen

DECKBLATT = """--- Seite 1
DEUTSCHE NORM Dezember 2016
DIN EN 350
ICS 79.040
Ersatz für DIN EN 350-1:1994-10
Dauerhaftigkeit von Holz und Holzprodukten
Nautos-Lizenz HNEE 2026-10-23
--- Seite 2
Inhalt DIN EN 335
--- Seite 3
Text"""


class TestErkennen(unittest.TestCase):
    def test_deckblatt(self):
        self.assertEqual(normen.kennung(DECKBLATT), "DIN EN 350")
        self.assertEqual(normen.ausgabe(DECKBLATT), "2016-12")
        self.assertEqual(normen.eintrag("a.pdf", DECKBLATT),
                         {"datei": "a.pdf", "kennung": "DIN EN 350", "ausgabe": "2016-12", "seiten": 3, "lesbar": True})

    def test_varianten(self):
        self.assertEqual(normen.kennung("--- Seite 1\nDIN 68 800-1:2019-06"), "DIN 68800-1")
        self.assertEqual(normen.ausgabe("--- Seite 1\nDIN 68 800-1:2019-06"), "2019-06")
        self.assertEqual(normen.kennung("--- Seite 1\nDIN EN ISO 14044:2021-02"), "DIN EN ISO 14044")
        self.assertEqual(normen.ausgabe("--- Seite 1\nLizenz 2026-10-23"), None)
        nautos = "--- Seite 1\nJuni\t2019DEUTSCHE\tNORM\nDIN\t68800-1\nErsatz\tfür\nDIN\t68800-1:2011-10"
        self.assertEqual((normen.kennung(nautos), normen.ausgabe(nautos)), ("DIN 68800-1", "2019-06"))
        self.assertIsNone(normen.kennung("--- Seite 1\nkeine Norm\n--- Seite 2\nDIN 4108-3"))

    def test_nautos_dateiname(self):
        self.assertEqual(normen.aus_dateiname("eurocode5/DIN EN 1995-1-1-NA_2013-08-00_DE_2025142.pdf"),
                         ("DIN EN 1995-1-1/NA", "2013-08"))
        self.assertEqual(normen.aus_dateiname("DIN EN 1995-1-1-A2_2014-07-00_DE_2151247.pdf"),
                         ("DIN EN 1995-1-1/A2", "2014-07"))
        self.assertEqual(normen.aus_dateiname("DIN EN 350 Berichtigung 1_2017-05-00_DE_2646996.pdf"),
                         ("DIN EN 350 Berichtigung 1", "2017-05"))
        self.assertEqual(normen.aus_dateiname("DIN_68800-1_2019-06-00_DE_3045931.pdf"), ("DIN 68800-1", "2019-06"))
        self.assertIsNone(normen.aus_dateiname("en350.pdf"))
        e = normen.eintrag("DIN EN 335_2013-06-00_DE_1919741.pdf", "--- Seite 1\nErsatz für DIN EN 335-1")
        self.assertEqual((e["kennung"], e["ausgabe"]), ("DIN EN 335", "2013-06"))
        e = normen.eintrag("DIN EN 335_2013-06-00_DE_1919741.pdf", None)
        self.assertEqual((e["kennung"], e["lesbar"]), ("DIN EN 335", False))

    def test_unlesbar(self):
        for text in (None, "(Kein Text gefunden, vermutlich ein Scan.)", "(Textfassung fehlgeschlagen: x)"):
            self.assertFalse(normen.eintrag("b.pdf", text)["lesbar"])


class TestVerzeichnis(unittest.TestCase):
    def test_sortiert_und_unlesbar(self):
        text = normen.verzeichnis([
            {"datei": "z.pdf", "kennung": None, "ausgabe": None, "seiten": 0, "lesbar": False},
            {"datei": "b.pdf", "kennung": "DIN EN 350", "ausgabe": "2016-12", "seiten": 3, "lesbar": True},
            {"datei": "a.pdf", "kennung": "DIN 68800-1", "ausgabe": None, "seiten": 40, "lesbar": True}])
        zeilen = [z for z in text.splitlines() if z.startswith("- ")]
        self.assertEqual(zeilen, ["- DIN 68800-1, 40 Seiten: a.pdf (Textfassung a.pdf.txt)",
                                  "- DIN EN 350, Ausgabe 2016-12, 3 Seiten: b.pdf (Textfassung b.pdf.txt)",
                                  "- z.pdf: KEIN TEXT (Scan oder geschützt), PDF mit Read ansehen: z.pdf"])

    def test_leer(self):
        self.assertIn("noch keine Normen", normen.verzeichnis([]))


class TestAufbereiten(unittest.TestCase):
    def test_nur_neue_melden(self):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "holzschutz").mkdir()
            (ordner / "holzschutz" / "en350.pdf").write_bytes(b"%PDF")
            (ordner / "notiz.txt").write_text("keine Norm")

            def textfassung(pfad, erneuern):
                pfad.with_name(pfad.name + ".txt").write_text(DECKBLATT)
                return True

            neu = normen.aufbereiten(ordner, textfassung=textfassung)
            self.assertEqual([e["datei"] for e in neu], ["holzschutz/en350.pdf"])
            self.assertIn("DIN EN 350", (ordner / "uebersicht.md").read_text())
            self.assertEqual(normen.aufbereiten(ordner, textfassung=textfassung), [])
            self.assertEqual(normen.aufbereiten(ordner / "fehlt"), [])
