import tempfile
import time
import unittest
from pathlib import Path

from agentkit import einstellungen, verbrauch

CFG = einstellungen.lade()


def stand(h5, d7, status="allowed", reset=None):
    return {"status": status, "5h": h5, "7d": d7, "reset_5h": reset, "reset_7d": reset, "reset_status": reset}


class TestVerbrauch(unittest.TestCase):
    def setUp(self):
        self.datei = Path(tempfile.mkdtemp()) / "v" / "laeufe.jsonl"

    def test_stufen(self):
        self.assertEqual(verbrauch.stufe(None, CFG), "normal")
        self.assertEqual(verbrauch.stufe(stand(0.1, 0.38), CFG), "normal")
        self.assertEqual(verbrauch.stufe(stand(0.5, 0.1), CFG), "sparen")
        self.assertEqual(verbrauch.stufe(stand(0.1, 0.7), CFG), "sparen")
        self.assertEqual(verbrauch.stufe(stand(0.8, 0.1), CFG), "nur_auftraege")
        self.assertEqual(verbrauch.stufe(stand(0.1, 0.95), CFG), "nur_auftraege")
        self.assertEqual(verbrauch.stufe(stand(1.0, 0.5, status="rejected"), CFG), "limit")

    def test_event_umwandeln(self):
        info = {"status": "allowed", "resetsAt": 100, "unifiedWindows": {
            "five_hour": {"utilization": 0, "resetsAt": 100}, "seven_day": {"utilization": 0.38, "resetsAt": 200}}}
        a = verbrauch.auslastung_aus_event(info)
        self.assertEqual((a["5h"], a["7d"], a["reset_7d"]), (0, 0.38, 200))

    def test_letzter_stand_und_ablauf(self):
        self.assertIsNone(verbrauch.letzter_stand(self.datei))
        jetzt = time.time()
        verbrauch.protokollieren({"agent": "uni", "auslastung": stand(0.9, 0.2, reset=jetzt + 3600)}, self.datei)
        verbrauch.protokollieren({"agent": "uni", "ok": False}, self.datei)  # ohne Auslastung
        self.assertEqual(verbrauch.letzter_stand(self.datei)["5h"], 0.9)
        # nach dem Reset zählt das Fenster als 0, ein altes Limit gilt nicht mehr
        verbrauch.protokollieren({"agent": "uni", "auslastung": stand(1.0, 0.2, "rejected", reset=jetzt - 1)}, self.datei)
        s = verbrauch.letzter_stand(self.datei)
        self.assertEqual((s["5h"], s["status"]), (0.0, "allowed"))
        self.assertEqual(verbrauch.stufe(s, CFG), "normal")

    def test_heute_und_kaputte_zeile(self):
        verbrauch.protokollieren({"agent": "uni", "ok": True, "tokens": 100, "dauer_s": 60, "usd": 0.1}, self.datei)
        verbrauch.protokollieren({"agent": "uni", "ok": False, "tokens": 50, "dauer_s": 30, "usd": 0.05}, self.datei)
        with open(self.datei, "a") as f:
            f.write("{kaputt\n")
        h = verbrauch.heute(self.datei)["uni"]
        self.assertEqual((h["laeufe"], h["tokens"], h["fehler"]), (2, 150, 1))
        self.assertAlmostEqual(h["minuten"], 1.5)


class TestEinstellungen(unittest.TestCase):
    def test_kein_bash(self):
        cfg = {"werkzeuge": {"standard": ["Read"], "boese": ["Read", "Bash"]}}
        with self.assertRaises(ValueError):
            einstellungen.werkzeuge(cfg, "boese")
        self.assertEqual(einstellungen.werkzeuge(cfg, "unbekannt"), ["Read"])


if __name__ == "__main__":
    unittest.main()
