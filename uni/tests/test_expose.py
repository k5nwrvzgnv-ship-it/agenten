import json
import tempfile
import unittest
from pathlib import Path

import expose

GUELTIG = {
    "art": "expose", "titel": "Fehlstellen: Holzlamellen", "autoren": ["Jan Kleinke", "Felix Frankowiak"],
    "betreuung": ["Prof. Dr. Thomas Böhme"], "einrichtung": "HNEE", "rahmen": "Forschungsprojekt 2",
    "datum": "02.11.2026",
    "bloecke": [
        {"typ": "ueberschrift", "text": "Problemstellung"},
        {"typ": "absatz", "text": "Fehlstellen | Äste"},
        {"typ": "ueberschrift", "text": "Daten", "ebene": 2},
        {"typ": "liste", "punkte": ["Kamera", "Licht"], "nummeriert": True},
        {"typ": "ueberschrift", "text": "Zeitplan"},
        {"typ": "tabelle", "titel": "Plan", "kopf": ["Wann", "Was"], "zeilen": [["Nov.", "Aufnahmen"]]},
    ],
    "literatur": ["Muster, A. (2020): Titel. Verlag."],
}


class TestAusloeser(unittest.TestCase):
    def test_nur_mit_praefix(self):
        for text in ("Exposé: Lamellen", "  expose:Lamellen", "EXPOSÉ : x"):
            self.assertTrue(expose.ist_exposeauftrag(text), text)
        for text in ("Mach ein Exposé: Lamellen", "Exposee Lamellen", "Dokument: Exposé"):
            self.assertFalse(expose.ist_exposeauftrag(text), text)


class TestPruefen(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(expose.pruefen(json.dumps(GUELTIG)), [])

    def test_alle_fehler_auf_einmal(self):
        d = {**GUELTIG, "art": "zusammenfassung", "datum": "2.11.26", "autoren": [], "quellen": [],
             "bloecke": [{"typ": "ueberschrift", "text": "1. Einleitung", "ebene": 2},
                         {"typ": "absatz", "text": "x", "quellen": []},
                         {"typ": "tabelle", "kopf": ["a", "b"], "zeilen": [["1"]]},
                         {"typ": "bild"}]}
        fehler = "\n".join(expose.pruefen(json.dumps(d)))
        for teil in ("quellen: unbekanntes Feld", "art:", "datum:", "autoren:",
                     "bloecke[0].ebene: vor der ersten Ebene 2", "bloecke[0].text: ohne Nummer",
                     "bloecke[1].quellen: unbekanntes Feld", "bloecke[2].zeilen[0]: 1 Zellen, erwartet 2",
                     "bloecke[3].typ"):
            self.assertIn(teil, fehler)

    def test_kein_json(self):
        self.assertTrue(expose.pruefen("{kaputt")[0].startswith("kein gültiges JSON"))
        self.assertEqual(expose.pruefen("[]"), ["die Beschreibung muss ein JSON-Objekt sein"])


class TestMarkdown(unittest.TestCase):
    def test_nummeriert_mit_kopf_tabelle_literatur(self):
        md = expose.als_markdown(GUELTIG)
        for teil in ("# Fehlstellen: Holzlamellen", "Jan Kleinke, Felix Frankowiak",
                     "Betreuung: Prof. Dr. Thomas Böhme", "Stand: 02.11.2026", "## 1 Problemstellung",
                     "### 1.1 Daten", "1. Kamera\n2. Licht", "## 2 Zeitplan", "| Wann | Was |",
                     "| Nov. | Aufnahmen |", "## Literatur\n\n- Muster"):
            self.assertIn(teil, md)


class TestBauen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)

    def test_ohne_datei_nichts(self):
        self.assertEqual(expose.bauen(self.ordner), expose.Bericht())

    def test_einmal_bauen_und_titelwechsel(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))
        b = expose.bauen(self.ordner)
        self.assertEqual(b.dateien, [self.ordner / "fassung" / "Fehlstellen - Holzlamellen.md"])
        self.assertEqual(expose.bauen(self.ordner).dateien, [])  # unverändert: nicht noch einmal
        (self.ordner / "expose.json").write_text(json.dumps({**GUELTIG, "titel": "Neu"}))
        self.assertEqual(expose.bauen(self.ordner).dateien, [self.ordner / "fassung" / "Neu.md"])
        self.assertEqual([p.name for p in (self.ordner / "fassung").iterdir()], ["Neu.md"])

    def test_ungueltig_nicht_gebaut(self):
        (self.ordner / "expose.json").write_text(json.dumps({**GUELTIG, "datum": "x"}))
        b = expose.bauen(self.ordner)
        self.assertEqual(b.dateien, [])
        self.assertIn("- datum:", b.ungueltig)
        self.assertFalse((self.ordner / "fassung").exists())


if __name__ == "__main__":
    unittest.main()
