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
        self.assertEqual((d["text"], d["gruendlich"], d["netz"], d["ort"]["stunde"]),
                         ("Was ist Vergeltung?", False, False, 2))
        self.assertTrue(schnittstelle.frage_pruefen({"id": fid, "text": "a", "netz": True})["netz"])
        self.assertFalse(schnittstelle.frage_pruefen({"id": fid, "text": "a", "netz": "ja"})["netz"])
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

    def test_dateien_stellen(self):
        hoch = self.ordner / "upload"
        hoch.mkdir()
        (hoch / "tmp1").write_bytes(b"x")
        fid = schnittstelle.frage_stellen("Was steht drin?", None, ordner=self.ordner,
                                          dateien=[("../Mein AB (neu).DOCX", hoch / "tmp1")])
        d = json.loads((self.ordner / "fragen" / f"{fid}.json").read_text(encoding="utf-8"))
        self.assertEqual(d["dateien"], ["Mein AB (neu).docx"])
        self.assertTrue((schnittstelle.dateien_ordner(fid, self.ordner) / "Mein AB (neu).docx").is_file())
        self.assertFalse((hoch / "tmp1").exists())
        self.assertEqual(json.loads((self.ordner / "fragen" / f"{fid}.json").read_text())["dateien"],
                         schnittstelle.frage_pruefen(d)["dateien"])

    def test_dateien_ungueltig(self):
        hoch = self.ordner / "upload"
        hoch.mkdir()
        klein, gross = hoch / "klein", hoch / "gross"
        klein.write_bytes(b"x")
        with open(gross, "wb") as f:
            f.truncate(schnittstelle.MAX_BYTES + 1)
        faelle = [[("a.xlsx", klein)], [("bild.jpg", klein)], [(f"{i}.pdf", klein) for i in range(4)],
                  [("a.pdf", klein), ("a.pdf", klein)], [("a.pdf", gross)], [("a.pdf", hoch / "fehlt")]]
        for dateien in faelle:
            with self.subTest(dateien=dateien[0][0]), self.assertRaises(schnittstelle.FrageFehler):
                schnittstelle.frage_stellen("x", None, ordner=self.ordner, dateien=dateien)
        self.assertFalse((self.ordner / "fragen").exists())
        self.assertFalse((self.ordner / "dateien").exists())
        self.assertTrue(klein.exists())
        for namen in (["../a.pdf"], [".a.pdf"], "a.pdf", [1]):
            with self.subTest(namen=namen), self.assertRaises(schnittstelle.FrageFehler):
                schnittstelle.frage_pruefen({"id": "0123456789ab", "text": "x", "dateien": namen})

    def test_aufraeumen_liegengebliebene_dateien(self):
        alt, neu = self.ordner / "dateien" / "aaaaaaaaaaaa", self.ordner / "dateien" / "bbbbbbbbbbbb"
        for d in (alt, neu):
            d.mkdir(parents=True)
            (d / "a.pdf").write_bytes(b"x")
        os.utime(alt, (time.time() - 2 * 86400,) * 2)
        self.assertEqual(chatverlauf.aufraeumen(self.ordner), 1)
        self.assertEqual([p.name for p in (self.ordner / "dateien").iterdir()], ["bbbbbbbbbbbb"])

    def test_kaputte_zeilen_und_leerer_ordner(self):
        self.assertEqual(chatverlauf.lesen(self.ordner), [])
        self.assertEqual(chatverlauf.aufraeumen(self.ordner), 0)
        (self.ordner / chatverlauf.DATEI).write_text('{"frage": "a"}\nnicht json\n[1]\n', encoding="utf-8")
        self.assertEqual(chatverlauf.lesen(self.ordner), [{"frage": "a"}])


if __name__ == "__main__":
    unittest.main()
