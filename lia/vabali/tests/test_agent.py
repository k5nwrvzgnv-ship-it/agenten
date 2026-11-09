import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import agent
from abfrage import AbfrageFehler

SUCHE = {"tage": ["2026-12-01", "2026-12-02"], "beginn_bis": "14:00", "dauer_minuten": 80, "partner": False,
         "link": "https://x"}
ARTIKEL = [{"Artikel_ID": 1, "Name": "Ganzkörper 80", "Dauer": 80, "Doppelanwendung": False, "buchbar": True}]


class FalscheAbfrage:
    def __init__(self, zeiten: dict, fehler: bool = False):
        self.zeiten_je_tag = zeiten
        self.fehler = fehler
        self.tage = []

    def artikel(self, datum):
        if self.fehler:
            raise AbfrageFehler("kaputt")
        self.tage.append(datum)
        return ARTIKEL

    def zeiten(self, datum, artikel_id):
        return self.zeiten_je_tag.get(datum, {})


class TestLauf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stand = Path(self.tmp.name) / "data" / "stand.json"
        self.lia, self.jan = [], []

    def tearDown(self):
        self.tmp.cleanup()

    def lauf(self, abfrage, heute=date(2026, 11, 10)):
        agent.lauf(SUCHE, heute, abfrage, self.stand, lia=self.lia.append, jan=self.jan.append)

    def test_meldet_neue_nur_einmal(self):
        abfrage = FalscheAbfrage({"2026-12-01": {"10:00:00": [1], "21:00:00": [2]}})
        self.lauf(abfrage)
        self.assertEqual(len(self.lia), 1)
        self.assertIn("Di 01.12. 10:00 Uhr", self.lia[0])
        self.assertNotIn("21:00", self.lia[0])
        self.lauf(abfrage)  # nichts Neues
        self.assertEqual(len(self.lia), 1)
        self.lauf(FalscheAbfrage({"2026-12-01": {"10:00:00": [1]}, "2026-12-02": {"09:00:00": [1]}}))
        self.assertEqual(len(self.lia), 2)
        self.assertIn("Mi 02.12. 09:00", self.lia[1])
        self.assertNotIn("01.12.", self.lia[1])

    def test_wieder_frei_wird_wieder_gemeldet(self):
        self.lauf(FalscheAbfrage({"2026-12-01": {"10:00:00": [1]}}))
        self.lauf(FalscheAbfrage({}))
        self.lauf(FalscheAbfrage({"2026-12-01": {"10:00:00": [1]}}))
        self.assertEqual(len(self.lia), 2)

    def test_fehler_einmal_an_jan_stand_bleibt(self):
        self.lauf(FalscheAbfrage({"2026-12-01": {"10:00:00": [1]}}))
        self.lauf(FalscheAbfrage({}, fehler=True))
        self.lauf(FalscheAbfrage({}, fehler=True))
        self.assertEqual(len(self.jan), 1)
        self.assertIn("kaputt", self.jan[0])
        self.assertEqual(json.loads(self.stand.read_text())["frei"], [["2026-12-01", "10:00", "Ganzkörper 80"]])
        self.lauf(FalscheAbfrage({"2026-12-01": {"10:00:00": [1]}}))
        self.assertEqual(len(self.jan), 2)
        self.assertIn("klappt wieder", self.jan[1])
        self.assertEqual(len(self.lia), 1)  # derselbe Termin nicht noch einmal

    def test_vergangene_tage_nicht_abfragen(self):
        abfrage = FalscheAbfrage({})
        self.lauf(abfrage, heute=date(2026, 12, 2))
        self.assertEqual(abfrage.tage, ["2026-12-02"])
        abfrage = FalscheAbfrage({})
        self.lauf(abfrage, heute=date(2026, 12, 3))
        self.assertEqual(abfrage.tage, [])


if __name__ == "__main__":
    unittest.main()
