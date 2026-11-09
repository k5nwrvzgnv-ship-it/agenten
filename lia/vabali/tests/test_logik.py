import unittest
from datetime import date

import logik

ARTIKEL = [
    {"Artikel_ID": 2214, "Name": "Ganzkörpermassage 80 Min.", "Dauer": 80, "Doppelanwendung": False, "buchbar": True},
    {"Artikel_ID": 2102, "Name": "Ganzkörpermassage 50 Min.", "Dauer": 50, "Doppelanwendung": False, "buchbar": True},
    {"Artikel_ID": 2872, "Name": "Partnermassage 80 Min.", "Dauer": 80, "Doppelanwendung": True, "buchbar": True},
    {"Artikel_ID": 2216, "Name": "Abhyanga 80 Min.", "Dauer": 80, "Doppelanwendung": False, "buchbar": False},
]


class TestLogik(unittest.TestCase):
    def test_artikel_nur_80_einzeln_buchbar(self):
        self.assertEqual([a["Artikel_ID"] for a in logik.passende_artikel(ARTIKEL, 80, False)], [2214])
        self.assertEqual([a["Artikel_ID"] for a in logik.passende_artikel(ARTIKEL, 80, True)], [2872])

    def test_zeiten_bis_einschliesslich_grenze(self):
        moegliche = {"21:00:00": [1744], "14:00:00": [1], "09:30:00": [2], "14:10:00": [3], "11:00:00": []}
        self.assertEqual(logik.passende_zeiten(moegliche, "14:00"), ["09:30", "14:00"])

    def test_offene_tage(self):
        tage = ["2026-12-01", "2026-12-02", "2026-12-03"]
        self.assertEqual(logik.offene_tage(tage, date(2026, 12, 2)), ["2026-12-02", "2026-12-03"])
        self.assertEqual(logik.offene_tage(tage, date(2026, 12, 4)), [])

    def test_neue_termine(self):
        alt = {("2026-12-01", "10:00", "A")}
        aktuell = {("2026-12-02", "09:00", "A"), ("2026-12-01", "10:00", "A"), ("2026-12-01", "12:00", "A")}
        self.assertEqual(logik.neue_termine(alt, aktuell), [("2026-12-01", "12:00", "A"), ("2026-12-02", "09:00", "A")])

    def test_meldungstext(self):
        text = logik.meldungstext([("2026-12-01", "10:30", "Ganzkörpermassage 80 Min.")], "https://x")
        self.assertIn("ein Massagetermin frei", text)
        self.assertIn("- Di 01.12. 10:30 Uhr: Ganzkörpermassage 80 Min.", text)
        self.assertIn("Buchen: https://x", text)
        zwei = logik.meldungstext([("2026-12-01", "10:30", "A"), ("2026-12-06", "09:00", "B")], "https://x")
        self.assertIn("Massagetermine frei", zwei)
        self.assertIn("- So 06.12. 09:00 Uhr: B", zwei)

    def test_meldungstext_fasst_massagen_je_zeit_zusammen(self):
        text = logik.meldungstext([("2026-12-01", "10:30", "Hot Stone 80"), ("2026-12-01", "10:30", "Aromaöl 80")],
                                  "https://x")
        self.assertIn("ein Massagetermin frei", text)
        self.assertIn("- Di 01.12. 10:30 Uhr: Aromaöl 80, Hot Stone 80", text)


if __name__ == "__main__":
    unittest.main()
