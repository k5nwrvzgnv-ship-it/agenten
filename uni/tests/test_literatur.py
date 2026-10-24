import tempfile
import unittest
from pathlib import Path

import literatur


class TestEintrag(unittest.TestCase):
    def test_titel(self):
        self.assertEqual(literatur.titel("idh/R05_T02_F02_Holzschutz--Bauliche-Massnahmen_2023-01.pdf"),
                         "R05 T02 F02 Holzschutz – Bauliche Massnahmen 2023-01")
        self.assertEqual(literatur.titel("kit/Blass_Sandhaas_Ingenieurholzbau_2016.pdf"),
                         "Blass Sandhaas Ingenieurholzbau 2016")

    def test_eintrag(self):
        e = literatur.eintrag("kit/buch.pdf", "--- Seite 1\nA\n--- Seite 2\nB")
        self.assertEqual((e["herkunft"], e["seiten"], e["lesbar"]), ("kit", 2, True))
        self.assertEqual(literatur.eintrag("buch.pdf", None)["herkunft"], "")
        self.assertFalse(literatur.eintrag("a.pdf", "(Kein Text gefunden, vermutlich ein Scan.)")["lesbar"])


class TestVerzeichnis(unittest.TestCase):
    def test_sortiert_und_unlesbar(self):
        text = literatur.verzeichnis([
            literatur.eintrag("kit/b.pdf", "--- Seite 1\nx"),
            literatur.eintrag("idh/scan.pdf", None),
            literatur.eintrag("lose.pdf", "--- Seite 1\nx")])
        zeilen = [z for z in text.splitlines() if z.startswith("- ")]
        self.assertEqual(zeilen, ["- lose, 1 Seiten: lose.pdf (Textfassung lose.pdf.txt)",
                                  "- idh: scan: KEIN TEXT (Scan oder geschützt), PDF mit Read ansehen: idh/scan.pdf",
                                  "- kit: b, 1 Seiten: kit/b.pdf (Textfassung kit/b.pdf.txt)"])

    def test_leer(self):
        self.assertIn("noch keine Literatur", literatur.verzeichnis([]))


class TestAufbereiten(unittest.TestCase):
    def test_nur_neue_melden(self):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "kit").mkdir()
            (ordner / "kit" / "buch.pdf").write_bytes(b"%PDF")

            def textfassung(pfad, erneuern):
                pfad.with_name(pfad.name + ".txt").write_text("--- Seite 1\nHolz")
                return True

            neu = literatur.aufbereiten(ordner, textfassung=textfassung)
            self.assertEqual([e["datei"] for e in neu], ["kit/buch.pdf"])
            self.assertIn("kit: buch, 1 Seiten", (ordner / "uebersicht.md").read_text())
            self.assertEqual(literatur.aufbereiten(ordner, textfassung=textfassung), [])
            self.assertEqual(literatur.aufbereiten(ordner / "fehlt"), [])


if __name__ == "__main__":
    unittest.main()
