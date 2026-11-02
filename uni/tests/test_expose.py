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
        {"typ": "absatz", "text": " ".join(["Wort"] * 700)},  # Umfang: mindestens 650 Wörter
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

    def test_umfang_zwei_bis_vier_seiten(self):
        lang = {**GUELTIG, "bloecke": GUELTIG["bloecke"] + [{"typ": "absatz", "text": " ".join(["x"] * 800)}]}
        self.assertIn("sind 1513: kürzen", expose.pruefen(json.dumps(lang))[0])
        kurz = {**GUELTIG, "bloecke": [b for b in GUELTIG["bloecke"] if len(b.get("text", "")) < 100]}
        self.assertIn("sind 13: ausführen", expose.pruefen(json.dumps(kurz))[0])
        viel = {**GUELTIG, "literatur": ["A (2020): T."] * 13,
                "bloecke": GUELTIG["bloecke"] + [{"typ": "ueberschrift", "text": "U", "ebene": 2}] * 6}
        fehler = "\n".join(expose.pruefen(json.dumps(viel)))
        self.assertIn("literatur: höchstens 12 Angaben, sind 13", fehler)
        self.assertIn("höchstens 6 Überschriften der Ebene 2, sind 7", fehler)

    def test_rahmen_mehrzeilig_bis_400_zeichen(self):
        d = {**GUELTIG, "rahmen": "Exposé | Wintersemester 2026/27\nStudiengang Holzingenieurwesen (M. Sc.)\n" + "x" * 300}
        self.assertEqual(expose.pruefen(json.dumps(d)), [])
        self.assertIn("rahmen: höchstens 400 Zeichen", expose.pruefen(json.dumps({**d, "rahmen": "x" * 401}))[0])

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

    def test_weitere_pruefung_nur_bei_gueltiger_beschreibung(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))
        b = expose.bauen(self.ordner, weitere=lambda d: [f"literatur[0]: {d['literatur'][0]} nicht geprüft"])
        self.assertEqual((b.dateien, b.ungueltig), ([], "- literatur[0]: Muster, A. (2020): Titel. Verlag. nicht geprüft"))
        self.assertEqual(len(expose.bauen(self.ordner, weitere=lambda d: []).dateien), 1)


if __name__ == "__main__":
    unittest.main()
