import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import chatverlauf
import schnittstelle


class Schnittstelle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_frage_stellen_und_antwort_holen(self):
        ort = {"reihe": "ethik-8-straftheorien", "stunde": 2, "chip": "Ethik › 8", "materialien": ["AB"]}
        fid = schnittstelle.frage_stellen("  Was ist Vergeltung? ", ort, ordner=self.ordner)
        self.assertTrue(schnittstelle.wartet(fid, self.ordner))
        d = json.loads((self.ordner / "fragen" / f"{fid}.json").read_text(encoding="utf-8"))
        self.assertEqual((d["text"], d["gruendlich"], d["ort"]["stunde"]), ("Was ist Vergeltung?", False, 2))
        self.assertEqual(list((self.ordner / "tmp").iterdir()), [])
        self.assertIsNone(schnittstelle.antwort_holen(fid, self.ordner))
        schnittstelle.antwort_schreiben({"id": fid, "ok": True, "text": "Antwort"}, self.ordner)
        self.assertEqual(schnittstelle.antwort_holen(fid, self.ordner)["text"], "Antwort")
        self.assertIsNone(schnittstelle.antwort_holen("../x", self.ordner))
        self.assertFalse(schnittstelle.wartet("../x", self.ordner))

    def test_ungueltige_fragen(self):
        for text, ort in (("", None), ("x" * 4001, None), ("a", {"stunde": 1}), ("a", {"reihe": "r", "x": 1}),
                          ("a", {"reihe": "r", "stunde": "2"}), ("a", {"reihe": "r", "materialien": [1]}),
                          ("a", "ethik")):
            with self.subTest(text=text[:5], ort=ort), self.assertRaises(schnittstelle.FrageFehler):
                schnittstelle.frage_stellen(text, ort, ordner=self.ordner)
        self.assertFalse((self.ordner / "fragen").exists())

    def test_frage_pruefen_id(self):
        with self.assertRaises(schnittstelle.FrageFehler):
            schnittstelle.frage_pruefen({"id": "abc", "text": "x"})
        f = schnittstelle.frage_pruefen({"id": "0123456789ab", "text": "x", "gruendlich": "ja", "ort": None})
        self.assertFalse(f["gruendlich"])


class Verlauf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_am_ort_bis_zum_ortswechsel(self):
        e = [{"reihe": "a", "frage": "1"}, {"reihe": None, "frage": "2"}, {"reihe": "a", "frage": "3"},
             {"reihe": "a", "frage": "4"}]
        self.assertEqual([x["frage"] for x in chatverlauf.am_ort(e, "a")], ["3", "4"])
        self.assertEqual(chatverlauf.am_ort(e, None), [])
        self.assertEqual([x["frage"] for x in chatverlauf.am_ort(e, "a", anzahl=1)], ["4"])

    def test_aufraeumen_nach_30_tagen(self):
        heute = datetime.now().astimezone()
        alt = (heute - timedelta(days=31)).isoformat()
        neu = (heute - timedelta(days=29)).isoformat()
        for zeit in (alt, neu, "kaputt"):
            chatverlauf.anhaengen(self.ordner, {"zeit": zeit, "frage": zeit})
        (self.ordner / "antworten").mkdir()
        alte_antwort = self.ordner / "antworten" / "a.json"
        alte_antwort.write_text("{}")
        os.utime(alte_antwort, (time.time() - 40 * 86400,) * 2)
        (self.ordner / "antworten" / "b.json").write_text("{}")
        weg = chatverlauf.aufraeumen(self.ordner, heute=heute)
        self.assertEqual(weg, 3)
        self.assertEqual([e["frage"] for e in schnittstelle.verlauf(self.ordner)], [neu])
        self.assertEqual([p.name for p in (self.ordner / "antworten").iterdir()], ["b.json"])

    def test_kaputte_zeilen_und_leerer_ordner(self):
        self.assertEqual(chatverlauf.lesen(self.ordner), [])
        self.assertEqual(chatverlauf.aufraeumen(self.ordner), 0)
        (self.ordner / chatverlauf.DATEI).write_text('{"frage": "a"}\nnicht json\n[1]\n', encoding="utf-8")
        self.assertEqual(chatverlauf.lesen(self.ordner), [{"frage": "a"}])


if __name__ == "__main__":
    unittest.main()
