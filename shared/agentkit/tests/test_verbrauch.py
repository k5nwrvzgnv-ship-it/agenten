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

    def test_warnung_ist_kein_limit(self):
        # Fall 25.10.: allowed_warning bei 7d 76 %, 5h 21 % sperrte alle Läufe
        self.assertEqual(verbrauch.stufe(stand(0.21, 0.76, status="allowed_warning"), CFG), "sparen")
        self.assertEqual(verbrauch.stufe(stand(0.1, 0.1, status="allowed_warning"), CFG), "normal")
        self.assertTrue(verbrauch.gesperrt("rejected"))
        self.assertFalse(verbrauch.gesperrt("allowed_warning"))

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


class InstanzVerbrauchTest(unittest.TestCase):
    def test_heute_trennt_instanzen(self):
        with tempfile.TemporaryDirectory() as d:
            datei = Path(d) / "laeufe.jsonl"
            verbrauch.protokollieren({"agent": "uni", "instanz": None, "ok": True, "tokens": 10}, datei)
            verbrauch.protokollieren({"agent": "unterricht", "instanz": "lia", "ok": True, "tokens": 5}, datei)
            verbrauch.protokollieren({"agent": "uni", "ok": False, "tokens": 1}, datei)  # alter Eintrag ohne Feld
            heute = verbrauch.heute(datei)
            self.assertEqual(set(heute), {"uni", "lia/unterricht"})
            self.assertEqual(heute["uni"]["laeufe"], 2)


class EinstellungenInstanzTest(unittest.TestCase):
    def test_instanz_ergaenzt_nur_werkzeuge(self):
        with tempfile.TemporaryDirectory() as d:
            basis, eigen = Path(d) / "basis.toml", Path(d) / "eigen.toml"
            basis.write_text('[parallel]\nnormal = 2\n[werkzeuge]\nstandard = ["Read"]\n')
            cfg = einstellungen.lade(basis, eigen)  # ohne eigene Datei
            self.assertEqual(cfg["werkzeuge"], {"standard": ["Read"]})
            eigen.write_text('[werkzeuge]\nunterricht = ["Read", "WebSearch"]\n')
            cfg = einstellungen.lade(basis, eigen)
            self.assertEqual(cfg["werkzeuge"]["unterricht"], ["Read", "WebSearch"])
            self.assertEqual(cfg["parallel"]["normal"], 2)
            eigen.write_text("[parallel]\nnormal = 9\n")
            with self.assertRaises(ValueError):
                einstellungen.lade(basis, eigen)

    def test_webfetch_domains(self):
        cfg = {"webfetch": {"recherche": ["BPB.de", " archive.org"], "leer": [], "boese": ["https://x.de"]}}
        self.assertEqual(einstellungen.webfetch_domains(cfg, "recherche"), ["bpb.de", "archive.org"])
        self.assertIsNone(einstellungen.webfetch_domains(cfg, "uni"))
        self.assertIsNone(einstellungen.webfetch_domains({}, "uni"))
        for agent in ("leer", "boese"):
            with self.assertRaises(ValueError):
                einstellungen.webfetch_domains(cfg, agent)
        for falsch in ["*.bpb.de", "bpb.de/pfad", "bpb.de:443", "localhost", "bpb", ""]:
            with self.assertRaises(ValueError, msg=falsch):
                einstellungen.webfetch_domains({"webfetch": {"a": [falsch]}}, "a")

    def test_webfetch_aus_der_instanz(self):
        with tempfile.TemporaryDirectory() as d:
            basis, eigen = Path(d) / "basis.toml", Path(d) / "eigen.toml"
            basis.write_text('[werkzeuge]\nstandard = ["Read"]\n[webfetch]\nrecherche = ["bpb.de"]\n')
            self.assertEqual(einstellungen.lade(basis, eigen)["webfetch"], {"recherche": ["bpb.de"]})
            eigen.write_text('[webfetch]\nrecherche = ["zdf.de"]\n')
            self.assertEqual(einstellungen.webfetch_domains(einstellungen.lade(basis, eigen), "recherche"), ["zdf.de"])

    def test_echte_einstellungen_gueltig(self):
        cfg = einstellungen.lade()
        for agent in cfg.get("webfetch", {}):
            self.assertIn("WebFetch", einstellungen.werkzeuge(cfg, agent))
            self.assertTrue(einstellungen.webfetch_domains(cfg, agent))

    def test_weitergabe_nur_aus_der_eigenen_instanz(self):
        with tempfile.TemporaryDirectory() as d:
            basis, eigen = Path(d) / "basis.toml", Path(d) / "eigen.toml"
            basis.write_text('[werkzeuge]\nstandard = ["Read"]\n[weitergabe]\nuni = ["dokumente"]\n')
            self.assertTrue(einstellungen.weitergabe_erlaubt(einstellungen.lade(basis, basis), "uni", "dokumente"))
            self.assertFalse(einstellungen.weitergabe_erlaubt(einstellungen.lade(basis, basis), "dokumente", "uni"))
            cfg = einstellungen.lade(basis, eigen)  # andere Instanz ohne eigene Datei: keine Weitergabe
            self.assertFalse(einstellungen.weitergabe_erlaubt(cfg, "uni", "dokumente"))
            eigen.write_text('[weitergabe]\nunterricht = ["material"]\n')
            cfg = einstellungen.lade(basis, eigen)
            self.assertTrue(einstellungen.weitergabe_erlaubt(cfg, "unterricht", "material"))
            self.assertFalse(einstellungen.weitergabe_erlaubt(cfg, "uni", "dokumente"))

if __name__ == "__main__":
    unittest.main()
