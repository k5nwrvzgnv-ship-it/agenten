import json
import tempfile
import unittest
from pathlib import Path

import belege


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)
        (self.ordner / "skript.pdf.txt").write_text(
            "--- Seite 1\nRückschnitt mit Sicherheits-\nabstand 0,30 m\n--- Seite 2\nbei EHS 1,00 m\n--- Seite 3\nEnde")
        (self.ordner / "transkript.txt").write_text("--- Seite 1\nAlso das ist eine Prüfungsfrage.\n--- Seite 2\nx")
        self.reg = belege.Register({"SHB 01": "skript.pdf", "Transkript 17.11.": "transkript.txt",
                                    "Fehlt": "gibt_es_nicht.pdf"}, self.ordner)

    def tearDown(self):
        self.tmp.cleanup()

    def schreibe(self, name, daten):
        pfad = self.ordner / name
        pfad.write_text(json.dumps(daten, ensure_ascii=False) if not isinstance(daten, str) else daten)
        return pfad


class TestFundstelle(Basis):
    def test_gueltig(self):
        self.assertEqual(belege.stelle_pruefen(self.reg, "SHB 01 S. 1-2"), [])
        self.assertEqual(belege.stelle_pruefen(self.reg, "SHB 01 S. 2, Abschn. 8.2"), [])
        self.assertEqual(belege.fundstellen_pruefen(self.reg, "SHB 01 S. 1; Transkript 17.11. S. 2"), [])

    def test_abgelehnt(self):
        self.assertIn("nicht im Register", belege.stelle_pruefen(self.reg, "Huckfeldt S. 3")[0])
        self.assertIn("gibt es nicht", belege.stelle_pruefen(self.reg, "SHB 01 S. 4")[0])
        self.assertIn("fehlt", belege.stelle_pruefen(self.reg, "Fehlt S. 1")[0])
        self.assertIn("keine Fundstelle der Form", belege.stelle_pruefen(self.reg, "SHB 01")[0])
        self.assertEqual(belege.fundstellen_pruefen(self.reg, ""), ["keine Fundstelle"])
        self.assertEqual(belege.fundstellen_pruefen(self.reg, None), ["keine Fundstelle"])

    def test_zitat(self):
        # Silbentrennung und Zeilenumbruch werden vereinheitlicht
        self.assertEqual(belege.stelle_pruefen(self.reg, "SHB 01 S. 1", "Sicherheitsabstand 0,30 m"), [])
        self.assertIn("Zitat steht nicht", belege.stelle_pruefen(self.reg, "SHB 01 S. 2", "0,50 m")[0])
        self.assertEqual(belege.fundstellen_pruefen(self.reg, "SHB 01 S. 3; Transkript 17.11. S. 1",
                                                    "das ist eine Prüfungsfrage"), [])

    def test_pptx_folien(self):
        (self.ordner / "folien.pptx.txt").write_text("--- Folie 1\nA\n--- Folie 2\nAbstützung")
        reg = belege.Register({"HBB 04": "folien.pptx"}, self.ordner)
        self.assertEqual(belege.stelle_pruefen(reg, "HBB 04 Folie 2", "Abstützung"), [])
        self.assertIn("gibt es nicht", belege.stelle_pruefen(reg, "HBB 04 Folie 3")[0])

    def test_zahlen(self):
        self.assertEqual(belege.zahlen("4, 7-8"), [4, 7, 8])
        self.assertEqual(belege.zahlen("3–4"), [3, 4])


class TestLernblatt(Basis):
    def test_aussagen_ohne_quelle_abgelehnt(self):
        blatt = {"art": "zusammenfassung", "titel": "T", "kurs": "K", "datum": "17.11.2026", "bloecke": [
            {"typ": "ueberschrift", "text": "Ohne Quelle erlaubt"},
            {"typ": "absatz", "text": "belegt", "quellen": [{"art": "transkript", "stelle": "1"}]},
            {"typ": "absatz", "text": "unbelegt"},
            {"typ": "liste", "punkte": ["nackter Punkt", {"text": "Norm", "quellen": [{"art": "norm", "stelle": "SHB 01 S. 2"}]},
                                       {"text": "falsche Seite", "quellen": [{"art": "norm", "stelle": "SHB 01 S. 9"}]}]},
            {"typ": "hinweis", "art": "pruefungsrelevant", "text": "Folie", "quellen": [{"art": "folie", "stelle": "2"}]}],
            "selbsttest": [{"frage": "F", "loesung": "L"}], "offene_fragen": ["darf ohne Quelle sein"]}
        pfad = self.schreibe("blatt_1.json", blatt)
        self.schreibe("blatt_1.belege.json", {"transkript": "Transkript 17.11."})
        wo = [a.wo for a in belege.pruefen(self.reg, pfad)]
        self.assertEqual(wo, ["bloecke[2] absatz", "bloecke[3].punkte[0]", "bloecke[3].punkte[2]",
                              "bloecke[4] hinweis", "selbsttest[0]"])


class TestAndere(Basis):
    def test_karten(self):
        pfad = self.schreibe("karten.json", [
            {"id": "a", "quelle": "SHB 01 S. 1", "herkunft": "nacht"},
            {"id": "b", "quelle": "Infokarten Pilze S. 1", "herkunft": "nacht"},
            {"id": "c", "quelle": "irgendwas", "herkunft": "alt"}])
        self.assertEqual([a.wo for a in belege.pruefen(self.reg, pfad)], ["b", "c"])
        self.assertEqual([a.wo for a in belege.karten_pruefen(self.reg, pfad, "nacht")], ["b"])

    def test_muendlich(self):
        self.schreibe("rubrik.json", {"punkte": [{"id": "ihs-erkennen"}]})
        bew = {"rubrik": ["ihs-erkennen"], "erfuellt": "a", "teilweise": "b", "nicht": "c"}
        pfad = self.schreibe("muendlich.json", {"fragen": [
            {"thema": "x", "frage": "F", "musterantwort": "M", "quellen": ["SHB 01 S. 1"], "bewertung": bew},
            {"thema": "y", "frage": "F", "musterantwort": "", "quellen": [], "bewertung": {**bew, "rubrik": ["gibts-nicht"]}}]})
        gruende = [a.grund for a in belege.pruefen(self.reg, pfad)]
        self.assertEqual(len(gruende), 3)
        self.assertTrue(all(a.wo.startswith("Frage 2") for a in belege.pruefen(self.reg, pfad)))

    def test_plan_signale(self):
        pfad = self.schreibe("pruefungsplan.json", {"themen": [{"id": "t", "dozent_signale": [
            {"zitat": "Das ist eine Prüfungsfrage", "fundstelle": "Transkript 17.11. S. 1"},
            {"zitat": "steht da nicht", "fundstelle": "Transkript 17.11. S. 1"},
            {"zitat": "", "fundstelle": "Transkript 17.11. S. 1"}]}]})
        self.assertEqual([a.wo for a in belege.pruefen(self.reg, pfad)], ["t Signal 2", "t Signal 3"])

    def test_markdown(self):
        pfad = self.schreibe("z.md", "# Titel\n\nText ohne Punkt.\n- belegt (S. 1)\n- über zwei\n  Zeilen (S. 2)\n"
                                     "- ohne Angabe\n- zu weit (S. 7)\n")
        abl = belege.pruefen(self.reg, pfad, "Transkript 17.11.")
        self.assertEqual([a.wo for a in abl], ["Zeile 7", "Zeile 8"])

    def test_vortrag_aussagen_und_unbekannt(self):
        pfad = self.schreibe("vortrag.belege.json", [{"aussage": "A", "quellen": ["SHB 01 S. 2"]},
                                                     {"aussage": "B", "quellen": []}])
        self.assertEqual(len(belege.pruefen(self.reg, pfad)), 1)
        self.assertIn("unbekannte Dateiart", belege.pruefen(self.reg, self.schreibe("x.txt", "a"))[0].grund)


if __name__ == "__main__":
    unittest.main()
