import json
import tempfile
import unittest
from pathlib import Path

import schnittstelle as s

BEZUG = "20261030-140944-unterricht-93e29e"


class Schnittstelle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.o = Path(self.tmp.name) / "data"

    def tearDown(self):
        self.tmp.cleanup()

    def test_aendern(self):
        wid = s.aendern(BEZUG, " Aufgabe 2 einfacher ", nr=1, seite=2, ordner=self.o)
        w = json.loads((self.o / "wuensche" / f"{wid}.json").read_text(encoding="utf-8"))
        self.assertEqual((w["art"], w["bezug"], w["nr"], w["eigene"], w["seite"], w["text"]),
                         ("aenderung", BEZUG, 1, None, 2, "Aufgabe 2 einfacher"))
        self.assertTrue(s.wartet(wid, self.o))
        self.assertIsNone(s.antwort_holen(wid, self.o))
        self.assertEqual(list((self.o / "tmp").iterdir()), [])

    def test_aendern_ungueltig(self):
        for kw in [{"bezug": "../x"}, {"text": " "}, {"text": "x" * 4001}, {"nr": -1}, {"nr": True},
                   {"eigene": 0}, {"seite": "2"}]:
            with self.subTest(kw=kw), self.assertRaises(s.WunschFehler):
                s.aendern(**{"bezug": BEZUG, "text": "x", **kw, "ordner": self.o})
        self.assertFalse((self.o / "wuensche").exists())

    def test_dokument_mit_dateien(self):
        quelle = Path(self.tmp.name) / "upload"
        quelle.write_bytes(b"x")
        wid = s.dokument("Checkliste", ort="ethik-8", dateien=[("../Mein Foto?.JPG", quelle)], ordner=self.o)
        w = s.wunsch_pruefen(json.loads((self.o / "wuensche" / f"{wid}.json").read_text(encoding="utf-8")))
        self.assertEqual((w["ort"], w["dateien"]), ("ethik-8", ["Mein Foto_.jpg"]))
        self.assertTrue((s.dateien_ordner(wid, self.o) / "Mein Foto_.jpg").is_file())
        self.assertFalse(quelle.exists())

    def test_dokument_ungueltig(self):
        quelle = Path(self.tmp.name) / "upload"
        quelle.write_bytes(b"x")
        for kw in [{"ort": "Ethik 8"}, {"dateien": [("a.exe", quelle)]}, {"dateien": [("a.pdf", quelle)] * 2},
                   {"dateien": [("a.pdf", Path(self.tmp.name) / "fehlt")]},
                   {"dateien": [(f"{i}.pdf", quelle) for i in range(6)]}]:
            with self.subTest(kw=kw), self.assertRaises(s.WunschFehler):
                s.dokument("x", **kw, ordner=self.o)
        self.assertTrue(quelle.exists())

    def test_pruefen(self):
        for w in [None, {"id": "x"}, {"id": "a" * 12, "art": "frage", "text": "x"},
                  {"id": "a" * 12, "art": "dokument", "text": "x", "dateien": "a.pdf"}]:
            with self.subTest(w=w), self.assertRaises(s.WunschFehler):
                s.wunsch_pruefen(w)
        self.assertFalse(s.wartet("../x", self.o))
        self.assertIsNone(s.antwort_holen("../x", self.o))


if __name__ == "__main__":
    unittest.main()
