import json
import tempfile
import unittest
from pathlib import Path

import scopus

KOPF = ('"Authors","Author full names","Title","Year","Source title","Cited by","DOI","Link","Abstract",'
        '"Author Keywords","Index Keywords","Document Type","EID"\n')
A = ('"Xie C.; van der Berg J.-P.","Xie, Chenhui (1)","Knot detection with YOLO","2023","Wood Science","12",'
     '"10.1234/ABC","https://www.scopus.com/x?eid=1","YOLO detects knots with high precision. © 2023 Verlag.",'
     '"knots; YOLO","wood","Article","2-s2.0-1"\n')
B = ('"Roe J.","Roe, Jane (2)","Grading lumber by eye","2018","Forest Products Journal","",'
     '"","https://www.scopus.com/x?eid=2","[No abstract available]","","","Conference paper","2-s2.0-2"\n')
C = ('"Lee K.","Lee, Kim (3)","Review of wood inspection","2021","Holzforschung","40",'
     '"10.5555/rev","https://www.scopus.com/x?eid=3","Reviews of machine vision for wood.","","","Review","2-s2.0-3"\n')
PROTOKOLL = """Scopus-Export, Datum: 02.11.2026
S1 | 1.234 | 300 | eins.csv | viele themenfremde Treffer
S2 | 2 | 2 | zwei.csv |
"""


class Hilfen(unittest.TestCase):
    def test_autoren(self):
        self.assertEqual(scopus.autoren("Xie C.; van der Berg J.-P.; [No author name available]"),
                         ["Xie, C.", "van der Berg, J.-P."])

    def test_schluessel_doi_ohne_gross_klein(self):
        self.assertEqual(scopus.schluessel("https://doi.org/10.1234/ABC"), scopus.schluessel("https://doi.org/10.1234/abc"))
        self.assertEqual(scopus.schluessel("https://www.scopus.com/x"), "https://www.scopus.com/x")

    def test_protokoll(self):
        datum, s = scopus.protokoll_lesen(PROTOKOLL)
        self.assertEqual(datum, "02.11.2026")
        self.assertEqual(s["S1"], {"gesamt": 1234, "exportiert": 300, "datei": "eins.csv",
                                   "vermerk": "viele themenfremde Treffer"})
        self.assertEqual(s["S2"]["vermerk"], "")
        self.assertFalse(scopus.ist_protokoll("Bitte Scopus einbauen."))


class Einlesen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.o = Path(self.tmp.name)
        (self.o / "eins.csv").write_text("﻿" + KOPF + A + B, encoding="utf-8")
        (self.o / "zwei.csv").write_text(KOPF + A + C, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ohne_dateien_none(self):
        with tempfile.TemporaryDirectory() as leer:
            self.assertIsNone(scopus.einlesen(Path(leer)))

    def test_doppelte_zusammen_und_nach_zitationen(self):
        e = scopus.einlesen(self.o)
        self.assertEqual([t["eid"] for t in e.treffer], ["2-s2.0-3", "2-s2.0-1", "2-s2.0-2"])
        a = e.treffer[1]
        self.assertEqual(a["suchen"], ["eins", "zwei"])
        self.assertEqual((a["url"], a["doi"], a["autoren"][0], a["jahr"]),
                         ("https://doi.org/10.1234/ABC", "10.1234/ABC", "Xie, C.", 2023))
        b = e.treffer[2]
        self.assertEqual((b["url"], b["abstract"], b["zitiert"]), ("https://www.scopus.com/x?eid=2", "", 0))

    def test_protokoll_und_suchen_ordnen_zu(self):
        (self.o / scopus.PROTOKOLL).write_text(PROTOKOLL, encoding="utf-8")
        (self.o / scopus.SUCHEN).write_text(json.dumps({"S1": {"titel": "Deep Learning",
                                                              "suchstring": "TITLE-ABS-KEY(knot*)"}}))
        e = scopus.einlesen(self.o)
        self.assertEqual(list(e.suchen), ["S1", "S2"])
        self.assertEqual((e.suchen["S1"]["gesamt"], e.suchen["S1"]["exportiert"], e.suchen["S1"]["titel"]),
                         (1234, 2, "Deep Learning"))
        self.assertEqual(e.datum, "02.11.2026")
        self.assertEqual(e.treffer[1]["suchen"], ["S1", "S2"])
        b = scopus.beschreibung(e)
        self.assertEqual((b["arbeiten_ohne_doppelte"], b["suchen"][0]["suchstring"]), (3, "TITLE-ABS-KEY(knot*)"))
        bericht = "\n".join(scopus.uebersicht_md(e, {scopus.schluessel("https://doi.org/10.1234/abc")}))
        self.assertIn("| S1 | Deep Learning | 1234 | 2 | 1 | viele themenfremde Treffer |", bericht)
        self.assertIn("- S1: `TITLE-ABS-KEY(knot*)`", bericht)
        self.assertIn("als Quelle verwendet: 1 Arbeiten", bericht)

    def test_abstracts_und_kandidaten(self):
        e = scopus.einlesen(self.o)
        ab = scopus.abstracts(e)
        self.assertIn("YOLO detects knots", ab[scopus.schluessel("https://doi.org/10.1234/abc")])
        md = scopus.kandidaten_md(e)
        self.assertIn("### SC0002 | 2023 | zitiert 12 | eins, zwei", md)
        self.assertIn("url: https://doi.org/10.1234/ABC", md)

    def test_kein_export(self):
        (self.o / "fremd.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        with self.assertRaises(scopus.ScopusFehler):
            scopus.einlesen(self.o)


class Vorschlag(unittest.TestCase):
    def test_suchstring(self):
        self.assertEqual(scopus.suchstring_fehler('TITLE-ABS-KEY(a AND NOT ("b (c" OR d*)) AND PUBYEAR > 2017 '
                                                  'AND DOCTYPE(re)'), [])
        fehler = "\n".join(scopus.suchstring_fehler('knot AND AUTHOR(x) AND "offen'))
        for teil in ("muss mit TITLE-ABS-KEY(", "Anführungszeichen", "nicht AUTHOR"):
            self.assertIn(teil, fehler)
        self.assertIn("Klammern", scopus.suchstring_fehler("TITLE-ABS-KEY((a OR b)")[0])

    def test_suchen_pruefen(self):
        gut = {"S1": {"titel": "A", "fragen": ["F7"], "suchstring": "TITLE-ABS-KEY(a)"},
               "S2": {"titel": "B", "fragen": ["F8"], "suchstring": "TITLE-ABS-KEY(b)"},
               "S3": {"titel": "C", "fragen": ["F7", "F8"], "suchstring": "TITLE-ABS-KEY(c)"}}
        self.assertEqual(scopus.suchen_pruefen(gut, {"F7", "F8"}), [])
        self.assertIn("3 bis 10", scopus.suchen_pruefen({"S1": gut["S1"]}, {"F7"})[0])
        schlecht = {"S1": gut["S1"], "S3": {**gut["S2"], "fragen": ["F1"]}, "S4": {"titel": "", "suchstring": 1}}
        fehler = "\n".join(scopus.suchen_pruefen(schlecht, {"F7", "F8"}))
        for teil in ("S3: Schlüssel muss S2", "S3.fragen", "S4.titel", "S4.suchstring: Text"):
            self.assertIn(teil, fehler)

    def test_chrome_prompt_und_anleitung(self):
        suchen = {"S1": {"titel": "Äste", "suchstring": "TITLE-ABS-KEY(knot*)"},
                  "S2": {"titel": "Reviews", "suchstring": "TITLE-ABS-KEY(wood) AND DOCTYPE(re)"}}
        p = scopus.chrome_prompt("Fehlstellen an Lamellen", suchen)
        for teil in ("Gib niemals Zugangsdaten ein", "Exposés: Fehlstellen an Lamellen", "Reihenfolge S1 bis S2",
                     "S1 Äste\nTITLE-ABS-KEY(knot*)", "die ersten 300", "<Nr> | <Trefferzahl gesamt>",
                     "Lade keine Volltexte"):
            self.assertIn(teil, p)
        a = scopus.anleitung("Fehlstellen", 2)
        self.assertIn("2 Suchen in Scopus", a)
        self.assertIn("agents-user:~/agenten/uni/data/scopus/", a)
        # Protokoll, wie Chrome es ausgeben soll, liest protokoll_lesen
        self.assertEqual(scopus.protokoll_lesen("S1 | 1234 | 300 | scopus_export_a.csv | viele fremde")[1]["S1"]
                         ["datei"], "scopus_export_a.csv")


class Uebernehmen(unittest.TestCase):
    def test_csv_und_protokoll(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "eins.csv").write_text(KOPF + A, encoding="utf-8")
            (t / "bild.png").write_bytes(b"x")
            ziel = t / "kette" / scopus.ORDNER
            neu = scopus.uebernehmen([t / "eins.csv", t / "bild.png"], PROTOKOLL, ziel)
            self.assertEqual(neu, [ziel / "eins.csv"])
            self.assertFalse((t / "eins.csv").exists())
            self.assertIn("S1 | 1.234", (ziel / scopus.PROTOKOLL).read_text())
            self.assertEqual(scopus.uebernehmen([t / "bild.png"], PROTOKOLL, ziel), [])

    def test_protokoll_als_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "zwei.csv").write_text(KOPF + C, encoding="utf-8")
            (t / "protokoll.txt").write_text(PROTOKOLL, encoding="utf-8")
            (t / "notiz.txt").write_text("nur eine Notiz", encoding="utf-8")
            ziel = t / "kette"
            scopus.uebernehmen([t / "zwei.csv", t / "protokoll.txt", t / "notiz.txt"], "Scopus einbauen", ziel)
            self.assertEqual(scopus.einlesen(ziel).suchen["S2"]["gesamt"], 2)
            self.assertFalse((t / "protokoll.txt").exists())
            self.assertTrue((t / "notiz.txt").exists())


if __name__ == "__main__":
    unittest.main()
