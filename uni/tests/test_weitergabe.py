import json
import tempfile
import unittest
from pathlib import Path

import weitergabe

ID = "20261022-120000-uni-abc123"
GUELTIG = {"art": "zusammenfassung", "titel": "Integrierter Holzschutz", "kurs": "Integrierter Holzschutz",
           "datum": "20.10.2026", "bloecke": [{"typ": "absatz", "text": "Holz kann abgebaut werden."}]}
BEHAUPTUNGEN = [{"nr": 1, "aussage": "Holz kann abgebaut werden.", "quellen": [{"art": "folie", "stelle": "4"}]},
                {"nr": 2, "aussage": "Exkursion am 27.10.", "kennzeichnung": "muendlich"}]
LISTE = f"data/weitergabe/{ID}/behauptungen.json"


class TestAusloeser(unittest.TestCase):
    def test_dokument_am_anfang(self):
        self.assertTrue(weitergabe.ist_dokumentauftrag("Dokument: Zusammenfassung IHS"))
        self.assertTrue(weitergabe.ist_dokumentauftrag("  dokument: klein geschrieben"))

    def test_sonst_nicht(self):
        self.assertFalse(weitergabe.ist_dokumentauftrag("Fass das Transkript-PDF zusammen"))
        self.assertFalse(weitergabe.ist_dokumentauftrag("Mach ein Dokument daraus"))
        self.assertFalse(weitergabe.ist_dokumentauftrag("Dokumente: ohne Doppelpunkt nach Dokument"))

    def test_format_abschnitt(self):
        md = "# Format\n## Arbeitsblatt\na\n## Zusammenfassung (docx)\nb\n### Unter\nc\n## Folien\nd"
        self.assertEqual(weitergabe.format_abschnitt(md), "## Zusammenfassung (docx)\nb\n### Unter\nc")
        self.assertEqual(weitergabe.format_abschnitt("## Zusammenfassung\nx"), "## Zusammenfassung\nx")
        with self.assertRaises(ValueError):
            weitergabe.format_abschnitt("# leer")

    def test_echtes_format(self):
        text = weitergabe.format_abschnitt(Path(weitergabe.pruefung.__file__).with_name("FORMAT.md").read_text())
        self.assertIn('"art": "zusammenfassung"', text)
        self.assertNotIn("## Folien", text)


class TestUebergabe(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self._tmp.name)
        self.ordner = weitergabe.dateien_ordner(self.hier, ID)
        self.ordner.mkdir(parents=True)
        (self.ordner / "zusammenfassung.json").write_text(json.dumps(GUELTIG))
        (self.ordner / "behauptungen.json").write_text(json.dumps(BEHAUPTUNGEN))

    def tearDown(self):
        self._tmp.cleanup()

    def uebergabe(self, daten):
        weitergabe.uebergabe_datei(self.hier, ID).write_text(json.dumps(daten) if not isinstance(daten, str) else daten)

    def fehler(self, daten) -> list[str]:
        self.uebergabe(daten)
        with self.assertRaises(weitergabe.UebergabeFehler) as f:
            weitergabe.uebergabe_pruefen(self.hier, ID)
        return f.exception.fehler

    def test_gueltig(self):
        self.uebergabe({"text": " Bitte als PDF bauen. ", "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json"]})
        text, dateien = weitergabe.uebergabe_pruefen(self.hier, ID)
        self.assertEqual(text, "Bitte als PDF bauen.")
        self.assertEqual(dateien, [(self.ordner / n).resolve() for n in ("behauptungen.json", "zusammenfassung.json")])

    def test_datei_fehlt(self):
        with self.assertRaises(weitergabe.UebergabeFehler) as f:
            weitergabe.uebergabe_pruefen(self.hier, ID)
        self.assertIn("fehlt", f.exception.fehler[0])

    def test_kaputtes_json(self):
        self.assertIn("nicht lesbar", self.fehler("{kaputt")[0])

    def test_kein_objekt(self):
        self.assertEqual(len(self.fehler([1, 2])), 1)

    def test_alle_fehler_auf_einmal(self):
        fehler = self.fehler({"text": "", "dateien": []})
        self.assertEqual(fehler, ["text fehlt oder ist leer", "dateien fehlt oder ist leer"])

    def test_text_zu_lang(self):
        f = self.fehler({"text": "x" * (weitergabe.MAX_TEXT + 1),
                         "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json"]})
        self.assertIn("text zu lang", f[0])

    def test_zu_viele_dateien(self):
        f = self.fehler({"text": "t", "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json"] * 3})
        self.assertIn("zu viele Dateien", f[0])

    def test_nur_aus_eigenem_ordner(self):
        eingang = self.hier / "data" / "eingang" / "x"
        eingang.mkdir(parents=True)
        (eingang / "Transkript.pdf").write_text("privat")
        f = self.fehler({"text": "t", "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json",
                                                  "data/eingang/x/Transkript.pdf",
                                                  f"data/weitergabe/{ID}/../../eingang/x/Transkript.pdf",
                                                  "/etc/passwd"]})
        self.assertEqual(len(f), 3)
        self.assertTrue(all("dürfen mit" in x for x in f))

    def test_symlink_nach_aussen(self):
        (self.hier / "geheim.txt").write_text("x")
        (self.ordner / "link.txt").symlink_to(self.hier / "geheim.txt")
        f = self.fehler({"text": "t", "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json",
                                                  f"data/weitergabe/{ID}/link.txt"]})
        self.assertEqual(len(f), 1)

    def test_fehlende_datei(self):
        f = self.fehler({"text": "t", "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json",
                                                  f"data/weitergabe/{ID}/weg.json"]})
        self.assertEqual(f, [f"data/weitergabe/{ID}/weg.json: Datei fehlt"])

    def test_beschreibung_wird_geprueft(self):
        (self.ordner / "zusammenfassung.json").write_text(json.dumps({**GUELTIG, "datum": "gestern"}))
        f = self.fehler({"text": "t", "dateien": [LISTE, f"data/weitergabe/{ID}/zusammenfassung.json"]})
        self.assertTrue(f and all(x.startswith(f"data/weitergabe/{ID}/zusammenfassung.json: ") for x in f))

    def test_ohne_beschreibung(self):
        (self.ordner / "notiz.txt").write_text("x")
        f = self.fehler({"text": "t", "dateien": [LISTE, f"data/weitergabe/{ID}/notiz.txt"]})
        self.assertEqual(f, ["keine Renderer-Beschreibung (.json) dabei"])


    def test_ohne_behauptungsliste(self):
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json"]})
        self.assertEqual(f, ["behauptungen.json fehlt"])


class TestBehauptungen(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(weitergabe.behauptungen_pruefen(json.dumps(BEHAUPTUNGEN)), [])

    def test_kein_json_oder_leer(self):
        self.assertIn("kein gültiges JSON", weitergabe.behauptungen_pruefen("{")[0])
        self.assertEqual(weitergabe.behauptungen_pruefen("[]"), ["muss eine nicht leere Liste sein"])

    def test_nr_und_aussage(self):
        f = weitergabe.behauptungen_pruefen(json.dumps([{"nr": 1, "aussage": "a"}, {"nr": 1, "aussage": "b"},
                                                        {"nr": [2], "aussage": "c"}, {"nr": 3}, "x"]))
        self.assertEqual(len(f), 4)
        self.assertTrue(f[0].startswith("[1].nr") and f[1].startswith("[2].nr"))
        self.assertEqual(f[2:], ["[3].aussage fehlt", "[4] ist kein Objekt"])

    def test_quellen_wie_im_renderer(self):
        f = weitergabe.behauptungen_pruefen(json.dumps([
            {"nr": 1, "aussage": "a", "quellen": [{"art": "folie", "stelle": "Folie 4"}]},
            {"nr": 2, "aussage": "b", "kennzeichnung": "vielleicht"},
            {"nr": 3, "aussage": "c", "seite": 4}]))
        self.assertTrue(f[0].startswith("[0].quellen"), f)
        self.assertTrue(any(x.startswith("[1].kennzeichnung") for x in f), f)
        self.assertIn("[2]: unbekannte Felder ['seite']", f)


if __name__ == "__main__":
    unittest.main()
