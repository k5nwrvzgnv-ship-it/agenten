import json
import tempfile
import unittest
from pathlib import Path

import weitergabe

ID = "20261022-120000-uni-abc123"
GUELTIG = {"art": "zusammenfassung", "titel": "Integrierter Holzschutz", "kurs": "Integrierter Holzschutz",
           "datum": "20.10.2026", "bloecke": [{"typ": "absatz", "text": "Holz kann abgebaut werden."}]}


class TestAusloeser(unittest.TestCase):
    def test_dokument_am_anfang(self):
        self.assertTrue(weitergabe.ist_dokumentauftrag("Dokument: Zusammenfassung IHS"))
        self.assertTrue(weitergabe.ist_dokumentauftrag("  dokument: klein geschrieben"))

    def test_sonst_nicht(self):
        self.assertFalse(weitergabe.ist_dokumentauftrag("Fass das Transkript-PDF zusammen"))
        self.assertFalse(weitergabe.ist_dokumentauftrag("Mach ein Dokument daraus"))
        self.assertFalse(weitergabe.ist_dokumentauftrag("Dokumente: ohne Doppelpunkt nach Dokument"))


class TestUebergabe(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self._tmp.name)
        self.ordner = weitergabe.dateien_ordner(self.hier, ID)
        self.ordner.mkdir(parents=True)
        (self.ordner / "zusammenfassung.json").write_text(json.dumps(GUELTIG))

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
        self.uebergabe({"text": " Bitte als PDF bauen. ", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json"]})
        text, dateien = weitergabe.uebergabe_pruefen(self.hier, ID)
        self.assertEqual(text, "Bitte als PDF bauen.")
        self.assertEqual(dateien, [(self.ordner / "zusammenfassung.json").resolve()])

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
                         "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json"]})
        self.assertIn("text zu lang", f[0])

    def test_zu_viele_dateien(self):
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json"] * 6})
        self.assertIn("zu viele Dateien", f[0])

    def test_nur_aus_eigenem_ordner(self):
        eingang = self.hier / "data" / "eingang" / "x"
        eingang.mkdir(parents=True)
        (eingang / "Transkript.pdf").write_text("privat")
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json",
                                                  "data/eingang/x/Transkript.pdf",
                                                  f"data/weitergabe/{ID}/../../eingang/x/Transkript.pdf",
                                                  "/etc/passwd"]})
        self.assertEqual(len(f), 3)
        self.assertTrue(all("dürfen mit" in x for x in f))

    def test_symlink_nach_aussen(self):
        (self.hier / "geheim.txt").write_text("x")
        (self.ordner / "link.txt").symlink_to(self.hier / "geheim.txt")
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json",
                                                  f"data/weitergabe/{ID}/link.txt"]})
        self.assertEqual(len(f), 1)

    def test_fehlende_datei(self):
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json",
                                                  f"data/weitergabe/{ID}/weg.json"]})
        self.assertEqual(f, [f"data/weitergabe/{ID}/weg.json: Datei fehlt"])

    def test_beschreibung_wird_geprueft(self):
        (self.ordner / "zusammenfassung.json").write_text(json.dumps({**GUELTIG, "datum": "gestern"}))
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/zusammenfassung.json"]})
        self.assertTrue(f and all(x.startswith(f"data/weitergabe/{ID}/zusammenfassung.json: ") for x in f))

    def test_ohne_beschreibung(self):
        (self.ordner / "notiz.txt").write_text("x")
        f = self.fehler({"text": "t", "dateien": [f"data/weitergabe/{ID}/notiz.txt"]})
        self.assertEqual(f, ["keine Renderer-Beschreibung (.json) dabei"])


if __name__ == "__main__":
    unittest.main()
