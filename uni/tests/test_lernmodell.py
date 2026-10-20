import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import lernmodell

JETZT = datetime(2026, 10, 20, 18, 0, tzinfo=ZoneInfo("Europe/Berlin"))


def anlegen(ordner: Path, karten: list[tuple[str, str]], themen: dict[str, int]) -> None:
    (ordner / "karten.json").write_text(json.dumps(
        [{"id": i, "thema": t, "typ": "text", "frage": f"F {i}", "antwort": f"A {i}", "quelle": "q", "bild": None}
         for i, t in karten]), encoding="utf-8")
    (ordner / "pruefungsplan.json").write_text(json.dumps(
        {"themen": [{"id": t, "score": s} for t, s in themen.items()]}), encoding="utf-8")


class TestModul(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)
        anlegen(self.ordner, [("p1", "pilze"), ("p2", "pilze"), ("p3", "pilze"), ("d1", "dach"), ("g1", "gk")],
                {"pilze": 5, "gk": 5, "dach": 3})

    def tearDown(self):
        self.tmp.cleanup()

    def test_bewerten_speichert_und_plant_in_tagen(self):
        m = lernmodell.Modul(self.ordner)
        faellig = m.bewerten("p1", lernmodell.BEWERTUNGEN["Gut"], JETZT)
        self.assertGreaterEqual(faellig - JETZT, timedelta(days=1))
        neu = lernmodell.Modul(self.ordner)
        self.assertIn("p1", neu.zustand)
        self.assertEqual(neu.verlauf[0]["thema"], "pilze")

    def test_nochmal_kommt_am_naechsten_tag(self):
        m = lernmodell.Modul(self.ordner)
        faellig = m.bewerten("p1", lernmodell.BEWERTUNGEN["Nochmal"], JETZT)
        self.assertLessEqual(faellig - JETZT, timedelta(days=1))

    def test_ungueltig(self):
        m = lernmodell.Modul(self.ordner)
        with self.assertRaises(lernmodell.LernFehler):
            m.bewerten("gibtsnicht", 3, JETZT)
        with self.assertRaises(lernmodell.LernFehler):
            m.bewerten("p1", 7, JETZT)

    def test_neue_nach_score_dann_reihenfolge(self):
        m = lernmodell.Modul(self.ordner)
        self.assertEqual(m.neue(), ["p1", "p2", "p3", "g1", "d1"])

    def test_neue_schwaches_thema_zuerst(self):
        m = lernmodell.Modul(self.ordner)
        m.bewerten("p1", 1, JETZT)  # Pilze falsch, gk noch ohne Bewertung
        self.assertEqual(m.neue()[0], "p2")
        m.bewerten("g1", 4, JETZT)
        self.assertEqual(m.neue(), ["p2", "p3", "d1"])

    def test_auswahl_faellige_vor_neuen_und_gemischt(self):
        m = lernmodell.Modul(self.ordner)
        gestern = JETZT - timedelta(days=3)
        m.bewerten("d1", 1, gestern)
        auswahl = m.auswahl(JETZT)
        self.assertEqual(auswahl[0], "d1")
        self.assertEqual(set(auswahl), {"d1", "p1", "p2", "p3", "g1"})
        self.assertEqual(auswahl[:3], ["d1", "p1", "g1"])  # reihum über die Themen

    def test_auswahl_grenzen(self):
        m = lernmodell.Modul(self.ordner)
        self.assertEqual(len(m.auswahl(JETZT, max_karten=2)), 2)
        m.bewerten("p1", 3, JETZT)
        m.bewerten("p2", 3, JETZT)
        self.assertEqual(m.neue_heute(JETZT), 2)
        self.assertEqual(len(m.auswahl(JETZT, neue_max=3)), 1)  # 2 von 3 neuen heute schon gesehen

    def test_status(self):
        m = lernmodell.Modul(self.ordner)
        self.assertEqual(m.status("pilze"), "nicht gesehen")
        m.bewerten("d1", 4, JETZT)
        self.assertEqual(m.status("dach"), "wackelig")  # einmal 'Leicht' reicht nicht
        t = JETZT
        for _ in range(2):
            t = m.zustand["d1"].due
            m.bewerten("d1", 4, t)
        self.assertEqual(m.status("dach"), "sitzt")
        m.bewerten("d1", 1, t + timedelta(days=30))
        self.assertEqual(m.status("dach"), "wackelig")

    def test_trefferquote_und_behaltensrate(self):
        m = lernmodell.Modul(self.ordner)
        m.bewerten("p1", 3, JETZT)
        m.bewerten("p2", 1, JETZT)
        m.bewerten("p1", 2, JETZT + timedelta(days=2))
        m.bewerten("p2", 3, JETZT + timedelta(days=2))
        self.assertEqual(m.trefferquote(), (2, 4))
        self.assertEqual(m.trefferquote("pilze", seit=JETZT + timedelta(days=1)), (1, 2))
        self.assertEqual(m.behaltensrate(), (2, 2))  # 'Schwer' gilt als behalten, nur Wiederholungen zählen

    def test_verwaister_zustand_wird_ignoriert(self):
        m = lernmodell.Modul(self.ordner)
        m.bewerten("p1", 1, JETZT - timedelta(days=5))
        anlegen(self.ordner, [("p2", "pilze")], {"pilze": 5})  # Karte p1 wurde ersetzt
        self.assertEqual(lernmodell.Modul(self.ordner).faellige(JETZT), [])


class TestMischen(unittest.TestCase):
    def test_reihum(self):
        thema = {"a1": "a", "a2": "a", "a3": "a", "b1": "b", "c1": "c"}
        self.assertEqual(lernmodell.mischen(list(thema), thema.get), ["a1", "b1", "c1", "a2", "a3"])


if __name__ == "__main__":
    unittest.main()
