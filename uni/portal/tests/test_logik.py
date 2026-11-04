import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import app  # noqa: F401  (setzt den Pfad zu uni/lernmodell.py)
import lernmodell

import logik

JETZT = datetime(2026, 11, 4, 18, 0, tzinfo=ZoneInfo("Europe/Berlin"))


def modul(ordner: Path, anzahl: int) -> lernmodell.Modul:
    karten = [{"id": f"k{i}", "thema": f"t{i % 2}", "typ": "text", "frage": "f", "antwort": "a", "quelle": "q",
               "bild": None} for i in range(anzahl)]
    (ordner / "karten.json").write_text(json.dumps(karten), encoding="utf-8")
    return lernmodell.Modul(ordner)


class Formularschutz(unittest.TestCase):
    def test_herkunft(self):
        self.assertTrue(logik.herkunft_passt("https://uni.meldro.de", "uni.meldro.de", "same-origin"))
        self.assertTrue(logik.herkunft_passt("https://uni.meldro.de", "uni.meldro.de", None))
        self.assertFalse(logik.herkunft_passt("https://boese.example", "uni.meldro.de", None))
        self.assertFalse(logik.herkunft_passt("https://uni.meldro.de", "uni.meldro.de", "cross-site"))
        self.assertFalse(logik.herkunft_passt(None, "uni.meldro.de", None))
        self.assertFalse(logik.herkunft_passt("null", "uni.meldro.de", None))

    def test_token(self):
        self.assertTrue(logik.token_passt(b"a", logik.formular_token(b"a")))
        self.assertFalse(logik.token_passt(b"a", logik.formular_token(b"b")))
        self.assertFalse(logik.token_passt(b"a", ""))
        self.assertFalse(logik.token_passt(b"a", None))

    def test_port(self):
        self.assertEqual(logik.port_pruefen("8793"), 8793)
        for falsch in ("80", "70000", "abc"):
            with self.assertRaises(ValueError):
                logik.port_pruefen(falsch)

    def test_bewertung_lesen(self):
        self.assertEqual([logik.bewertung_lesen(w) for w in "1234"], [1, 2, 3, 4])
        for falsch in ("0", "5", "", None, "Gut"):
            self.assertIsNone(logik.bewertung_lesen(falsch))


class Sitzung(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.ordner = Path(t.name)

    def test_neue_sitzung_nimmt_auswahl_und_grenze_fuer_neue(self):
        m = modul(self.ordner, 20)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        self.assertEqual(len(s["warteschlange"]), lernmodell.NEUE_PRO_TAG)
        self.assertEqual(s["datum"], "2026-11-04")

    def test_bewerten_nimmt_karte_und_zaehlt(self):
        m = modul(self.ordner, 3)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        erste = s["warteschlange"][0]
        self.assertTrue(logik.bewertung_anwenden(s, m, erste, "0", 3, JETZT))
        self.assertNotIn(erste, s["warteschlange"])
        self.assertEqual((s["erledigt"], s["richtig"]), (1, 1))
        self.assertIn(erste, lernmodell.Modul(self.ordner).zustand)

    def test_nochmal_kommt_am_ende_einmal_neu(self):
        m = modul(self.ordner, 2)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        erste, zweite = s["warteschlange"]
        logik.bewertung_anwenden(s, m, erste, "0", 1, JETZT)
        self.assertEqual(s["warteschlange"], [zweite, erste])
        logik.bewertung_anwenden(s, m, zweite, "1", 3, JETZT)
        logik.bewertung_anwenden(s, m, erste, "2", 1, JETZT)  # zweites Nochmal: nicht noch einmal
        self.assertEqual(s["warteschlange"], [])

    def test_doppelklick_zaehlt_einmal(self):
        m = modul(self.ordner, 1)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        logik.bewertung_anwenden(s, m, "k0", "0", 1, JETZT)  # kommt nach Nochmal wieder
        self.assertFalse(logik.bewertung_anwenden(s, m, "k0", "0", 1, JETZT))
        self.assertEqual(len(lernmodell.Modul(self.ordner).verlauf), 1)

    def test_falsche_karte_zaehlt_nicht(self):
        m = modul(self.ordner, 2)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        self.assertFalse(logik.bewertung_anwenden(s, m, s["warteschlange"][1], "0", 3, JETZT))
        self.assertEqual(s["erledigt"], 0)

    def test_neuer_tag_neue_sitzung(self):
        m = modul(self.ordner, 3)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        logik.bewertung_anwenden(s, m, s["warteschlange"][0], "0", 3, JETZT)
        morgen = logik.sitzung_holen(s, m, "x", JETZT + timedelta(days=1))
        self.assertEqual(morgen["erledigt"], 0)

    def test_verschwundene_karte_faellt_raus(self):
        m = modul(self.ordner, 3)
        s = logik.sitzung_holen(None, m, "x", JETZT)
        s["warteschlange"].insert(0, "weg")
        s = logik.sitzung_holen(s, m, "x", JETZT)
        self.assertNotIn("weg", s["warteschlange"])

    def test_mehr_faellige_als_eine_runde_gehen_weiter(self):
        anzahl = lernmodell.MAX_KARTEN + 5
        m = modul(self.ordner, anzahl)
        for i in range(anzahl):
            m.bewerten(f"k{i}", 3, JETZT - timedelta(days=90))
        spaeter = JETZT
        m = lernmodell.Modul(self.ordner)
        s = logik.sitzung_holen(None, m, "x", spaeter)
        self.assertEqual(len(s["warteschlange"]), lernmodell.MAX_KARTEN)
        for nr in range(anzahl):
            s = logik.sitzung_holen(s, m, "x", spaeter)
            self.assertTrue(logik.bewertung_anwenden(s, m, s["warteschlange"][0], str(nr), 3, spaeter))
        self.assertEqual(logik.sitzung_holen(s, m, "x", spaeter)["warteschlange"], [])


class Ansicht(unittest.TestCase):
    def test_ganzes_bild(self):
        self.assertEqual(logik.ganzes_bild("a/pilz-1-frage.jpg"), "a/pilz-1-ganz.jpg")
        self.assertIsNone(logik.ganzes_bild("a/pilz.jpg"))
        self.assertIsNone(logik.ganzes_bild(None))

    def test_themen_nach_score_mit_stand(self):
        with tempfile.TemporaryDirectory() as t:
            m = modul(Path(t), 2)
            m.bewerten("k0", 3, JETZT)
            plan = {"themen": [{"id": "t1", "score": 2}, {"id": "t0", "score": 5}, {"id": "t9", "score": 3}]}
            zeilen = logik.themen_ansicht(plan, m)
        self.assertEqual([z["score"] for z in zeilen], [5, 3, 2])
        self.assertEqual([z["stand"] for z in zeilen], ["wackelig", "keine Karten", "nicht gesehen"])
        self.assertEqual((zeilen[0]["gesehen"], zeilen[0]["karten"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
