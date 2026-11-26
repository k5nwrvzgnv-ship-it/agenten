"""Klassenliste als Datei: umbenennen, Farbe, neu, löschen (zusammenlegen) und zurück, dazu das Umschreiben der
Labels in der Kette."""

import json
import tempfile
import unittest
from pathlib import Path

from aufnahme import kette as k
from aufnahme import klassen as kl


class TestKlassen(unittest.TestCase):
    def test_standard_passt_zur_alten_liste(self):
        d = kl.standard()
        self.assertEqual(kl.schluessel_liste(d), k.KLASSEN)
        self.assertEqual(kl.gruppen(d), ["Ast", "Riss", "Loch", "Fuge", "Metall", "Weitere"])
        self.assertEqual(len(kl.aktive_ids(d)), 18)

    def test_umbenennen_behaelt_id_und_schluessel(self):
        d = kl.standard()
        kl.aendern(d, 0, name="  Ast   gesund ")
        x = kl.klasse(d, 0)
        self.assertEqual((x["name"], x["schluessel"], x["id"]), ("Ast gesund", "live_knot", 0))
        with self.assertRaises(ValueError):
            kl.aendern(d, 1, name="ast GESUND")        # doppelt, ohne Groß/klein
        with self.assertRaises(ValueError):
            kl.aendern(d, 1, name="   ")

    def test_farbe_und_gruppe(self):
        d = kl.standard()
        kl.aendern(d, 4, farbe_neu="#AABBCC")
        self.assertEqual(kl.klasse(d, 4)["farbe"], "#aabbcc")
        kl.aendern(d, 4, farbe_neu=None)
        self.assertIsNone(kl.klasse(d, 4)["farbe"])
        with self.assertRaises(ValueError):
            kl.aendern(d, 4, farbe_neu="rot")
        kl.aendern(d, 4, gruppe="Ast")                 # Riss in die Gruppe Ast: freies Muster
        self.assertNotIn(kl.klasse(d, 4)["muster"], ["", "9 4", "3 3", "12 3 3 3", "5 4"])
        self.assertNotIn("Riss", kl.gruppen(d))

    def test_gruppe_umbenennen(self):
        d = kl.standard()
        kl.gruppe_umbenennen(d, "Weitere", "Sonstiges")
        self.assertEqual(kl.gruppen(d)[-1], "Sonstiges")
        with self.assertRaises(ValueError):
            kl.gruppe_umbenennen(d, "Ast", "Riss")

    def test_neu_bekommt_neue_id_und_steht_in_der_gruppe(self):
        d = kl.standard()
        x = kl.neu(d, "Schraube", "Metall")
        self.assertEqual((x["id"], x["schluessel"]), (18, "schraube"))
        self.assertEqual(kl.schluessel_liste(d)[18], "schraube")
        reihe = [y["id"] for y in d["klassen"]]
        self.assertEqual(reihe[reihe.index(11) + 1], 18)
        y = kl.neu(d, "Fäule weiß", "Pilz")             # neue Gruppe ans Ende
        self.assertEqual((y["schluessel"], kl.gruppen(d)[-1]), ("faeule_weiss", "Pilz"))

    def test_geloeschte_id_kommt_nie_wieder(self):
        d = kl.standard()
        x = kl.neu(d, "Test", "Weitere")
        kl.weg(d, x["id"])
        self.assertEqual(kl.neu(d, "Test", "Weitere")["id"], x["id"] + 1)
        self.assertNotEqual(kl.klasse(d, x["id"] + 1)["schluessel"], "test")

    def test_weg_mit_objekten_braucht_ziel(self):
        d = kl.standard()
        with self.assertRaises(ValueError):
            kl.weg(d, 5, anzahl=3)
        with self.assertRaises(ValueError):
            kl.weg(d, 5, ziel=5, anzahl=3)
        kl.weg(d, 5, ziel=4, anzahl=3)
        self.assertNotIn(5, kl.aktive_ids(d))
        self.assertEqual(kl.schluessel_liste(d)[5], "quartzity")   # Nummern fürs Training bleiben
        self.assertEqual(kl.zurueck(d), {"id": 5, "in": 4})
        self.assertIn(5, kl.aktive_ids(d))
        with self.assertRaises(ValueError):
            kl.zurueck(d)

    def test_objekte_umhaengen_und_zurueck(self):
        o = [{"k": 5}, {"k": 4}, {"k": 5}]
        self.assertEqual(kl.objekte_umhaengen(o, 5, 4), 2)
        self.assertEqual(o, [{"k": 4, "kv": 5}, {"k": 4}, {"k": 4, "kv": 5}])
        self.assertEqual(kl.objekte_zurueck(o, 5, 4), 2)
        self.assertEqual(o, [{"k": 5}, {"k": 4}, {"k": 5}])

    def test_gelesen_lehnt_kaputtes_ab(self):
        for roh in (None, {}, {"klassen": []}, {"klassen": [{"id": 1, "schluessel": "a"}, {"id": 1, "schluessel": "b"}]},
                    {"klassen": [{"id": True, "schluessel": "a"}]}):
            with self.assertRaises(ValueError):
                kl.gelesen(roh)


class TestKetteKlassen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name) / "aufnahmen"
        (self.ordner / "B001" / "labels").mkdir(parents=True)
        self.datei = self.ordner / "B001" / "labels" / "f1.json"
        dreieck = [[0.1, 0.1], [0.3, 0.1], [0.2, 0.4]]
        self.datei.write_text(json.dumps({"objekte": [{"k": 5, "ok": True, "p": dreieck},
                                                      {"k": 0, "ok": False, "p": dreieck}]}))
        self.kette = k.Kette(self.ordner, lambda i: {}, lambda: [])

    def tearDown(self):
        self.tmp.cleanup()

    def test_ohne_datei_gilt_startfassung(self):
        self.assertEqual(self.kette.namen(), k.KLASSEN)
        self.assertEqual(self.kette.klassen_stand("henri")["zahl"], {5: 1, 0: 1})

    def test_zusammenlegen_schreibt_labels_um_und_zurueck(self):
        with self.assertRaises(ValueError):
            self.kette.klassen_aendern({"art": "weg", "id": 5})
        s = self.kette.klassen_aendern({"art": "weg", "id": 5, "in": 4}, "jan")
        self.assertEqual(s["zahl"], {4: 1, 0: 1})
        self.assertEqual(s["zurueck"]["anzahl"], 1)
        objekte = json.loads(self.datei.read_text())["objekte"]
        self.assertEqual((objekte[0]["k"], objekte[0]["kv"]), (4, 5))
        self.assertTrue((self.ordner / "klassen.json").exists())
        s = self.kette.klassen_aendern({"art": "zurueck"})
        self.assertEqual(s["zahl"], {5: 1, 0: 1})
        self.assertNotIn("kv", json.loads(self.datei.read_text())["objekte"][0])

    def test_neue_klasse_ist_beim_speichern_gueltig(self):
        self.kette.klassen_aendern({"art": "neu", "name": "Schraube", "gruppe": "Metall"})
        d = [{"k": 18, "ok": True, "p": [[0.1, 0.1], [0.3, 0.1], [0.2, 0.4]]}]
        self.assertEqual(k.objekte_pruefen(d, k.kl.aktive_ids(self.kette.klassen()))[0]["k"], 18)
        self.kette.klassen_aendern({"art": "weg", "id": 18})
        with self.assertRaises(ValueError):
            k.objekte_pruefen(d, k.kl.aktive_ids(self.kette.klassen()))

    def test_unbekannte_aenderung(self):
        with self.assertRaises(ValueError):
            self.kette.klassen_aendern({"art": "alles"})


class TestObjektFelder(unittest.TestCase):
    P = [[0.1, 0.1], [0.3, 0.1], [0.2, 0.4]]

    def test_vorlabel_und_messung_bleiben(self):
        o = k.objekte_pruefen([{"k": 1, "ok": False, "p": self.P, "c": 0.4412, "q": "kodytek-seg1-n1280",
                                "m": [{"min": 14.5, "max": 22}, {"von": "felix", "min": 15, "max": None}],
                                "fremd": "weg"}], von="henri")[0]
        self.assertEqual(o["c"], 0.4412)
        self.assertEqual(o["q"], "kodytek-seg1-n1280")
        self.assertEqual(o["m"], [{"von": "henri", "min": 14.5, "max": 22.0}, {"von": "felix", "min": 15.0, "max": None}])
        self.assertNotIn("fremd", o)

    def test_leere_messung_faellt_weg_und_mac_ohne_namen(self):
        o = k.objekte_pruefen([{"k": 1, "ok": True, "p": self.P, "m": [{"min": None, "max": None}]}])[0]
        self.assertNotIn("m", o)
        o = k.objekte_pruefen([{"k": 1, "ok": True, "p": self.P, "m": [{"min": 3}]}])[0]
        self.assertEqual(o["m"][0]["von"], "mac")

    def test_falsche_werte(self):
        for zu in ({"c": 1.5}, {"c": True}, {"m": [{"min": -1}]}, {"m": [{"min": 1, "von": "<x>"}]}, {"q": 5},
                   {"m": "viel"}):
            with self.assertRaises(ValueError, msg=zu):
                k.objekte_pruefen([{"k": 1, "ok": True, "p": self.P, **zu}])


if __name__ == "__main__":
    unittest.main()
