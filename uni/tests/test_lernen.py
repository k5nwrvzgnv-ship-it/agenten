import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import lernen
import lernmodell
from tests.test_lernmodell import JETZT, anlegen  # JETZT: 20.10.2026 18:00

FREI = lambda: False  # noqa: E731
BELEGT = lambda: True  # noqa: E731


class TestAbfrage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name) / "holzschutz"
        self.ordner.mkdir()
        anlegen(self.ordner, [("p1", "pilze"), ("g1", "gk")], {"pilze": 5, "gk": 4})
        self.m = lernmodell.Modul(self.ordner)

    def tearDown(self):
        self.tmp.cleanup()

    def starten(self):
        s, n = lernen.zeitschritt(None, self.m, JETZT, FREI)
        return s, n

    def test_start_erst_ab_18_uhr_und_ohne_termin(self):
        self.assertEqual(lernen.zeitschritt(None, self.m, JETZT - timedelta(hours=1), FREI), (None, None))
        self.assertEqual(lernen.zeitschritt(None, self.m, JETZT, BELEGT), (None, None))
        self.assertEqual(lernen.zeitschritt(None, self.m, JETZT.replace(hour=22), FREI), (None, None))
        s, n = self.starten()
        self.assertEqual(s["warteschlange"], ["p1", "g1"])
        self.assertIn("Wiederholung heute: 2 Karten", n.text)
        self.assertIn("Karte 1/2", n.text)
        self.assertIn("F p1", n.text)
        self.assertEqual(n.knoepfe, lernen.FRAGE_KNOEPFE)

    def test_nur_einmal_am_tag(self):
        s, _ = self.starten()
        self.assertEqual(lernen.zeitschritt(s, self.m, JETZT + timedelta(minutes=15), FREI), (s, None))
        s2, n = lernen.zeitschritt(s, self.m, JETZT + timedelta(days=1), FREI)
        self.assertEqual(s2["datum"], "2026-10-21")

    def test_nichts_faellig(self):
        for i in ("p1", "g1"):
            self.m.bewerten(i, 4, JETZT - timedelta(hours=1))
        s, n = self.starten()
        self.assertIsNone(n)
        self.assertEqual(s["phase"], "fertig")

    def test_durchlauf_mit_nochmal(self):
        s, _ = self.starten()
        s, n = lernen.weiter(s, self.m, lernen.ZEIGEN, JETZT)
        self.assertIn("A p1", n.text)
        self.assertNotIn("Deine Antwort", n.text)
        self.assertEqual(n.knoepfe, lernen.BEWERTEN_KNOEPFE)
        s, n = lernen.weiter(s, self.m, "Nochmal", JETZT)
        self.assertEqual(s["warteschlange"], ["g1", "p1"])
        self.assertIn("Karte 2/3", n.text)
        s, n = lernen.weiter(s, self.m, "Braunfäule, weil ...", JETZT)  # eigene Antwort
        self.assertIn("Deine Antwort: Braunfäule, weil ...", n.text)
        s, n = lernen.weiter(s, self.m, "gut", JETZT)  # Groß-/Kleinschreibung egal
        s, n = lernen.weiter(s, self.m, lernen.ZEIGEN, JETZT)
        s, n = lernen.weiter(s, self.m, "Nochmal", JETZT)  # zweites Nochmal: nicht noch einmal anhängen
        self.assertEqual(s["warteschlange"], [])
        self.assertEqual(s["phase"], "fertig")
        self.assertIn("3 Karten, 1 davon gewusst", n.text)
        verlauf = (self.ordner / "verlauf.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(z)["bewertung"] for z in verlauf], [1, 3, 1])

    def test_ungueltige_bewertung(self):
        s, _ = self.starten()
        s, _ = lernen.weiter(s, self.m, lernen.ZEIGEN, JETZT)
        s, n = lernen.weiter(s, self.m, "keine Ahnung", JETZT)
        self.assertEqual(s["phase"], "antwort")
        self.assertEqual(n.knoepfe, lernen.BEWERTEN_KNOEPFE)

    def test_spaeter(self):
        s, _ = self.starten()
        s, n = lernen.weiter(s, self.m, lernen.SPAETER, JETZT)
        self.assertEqual(s["phase"], "pause")
        self.assertIn("19:00", n.text)
        self.assertIsNone(lernen.zeitschritt(s, self.m, JETZT + timedelta(minutes=30), FREI)[1])
        s, n = lernen.zeitschritt(s, self.m, JETZT + timedelta(hours=1), FREI)
        self.assertEqual(s["phase"], "frage")
        self.assertIn("F p1", n.text)
        self.assertNotIn("Wiederholung heute", n.text)

    def test_spaeter_nicht_nach_22_uhr(self):
        s, _ = lernen.zeitschritt(None, self.m, JETZT.replace(hour=21, minute=30), FREI)
        s, _ = lernen.weiter(s, self.m, lernen.SPAETER, JETZT.replace(hour=21, minute=30))
        self.assertIsNone(lernen.zeitschritt(s, self.m, JETZT.replace(hour=22, minute=30), FREI)[1])

    def test_antwort_waehrend_pause(self):
        s, _ = self.starten()
        s, _ = lernen.weiter(s, self.m, lernen.SPAETER, JETZT)
        s, n = lernen.weiter(s, self.m, "doch jetzt", JETZT)
        self.assertEqual(s["phase"], "frage")

    def test_bildkarte_schickt_bild(self):
        karten = json.loads((self.ordner / "karten.json").read_text())
        karten[0] |= {"typ": "bild", "bild": "data/lernen/holzschutz/bilder/pilz-1-frage.jpg"}
        (self.ordner / "karten.json").write_text(json.dumps(karten))
        _, n = lernen.zeitschritt(None, lernmodell.Modul(self.ordner), JETZT, FREI)
        self.assertEqual(n.dateien, ["data/lernen/holzschutz/bilder/pilz-1-frage.jpg"])


if __name__ == "__main__":
    unittest.main()
