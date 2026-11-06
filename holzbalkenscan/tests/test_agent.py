"""Ablauf des Agenten mit Fake-Skripten statt des echten Verfahrens (keine 48-MP-Rechnung)."""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import agent
import pruefstand

BEISPIELE = Path(__file__).parent / "beispiele"

FAKE_PRUEFEN = f"""
import sys, pathlib
z = sys.argv[sys.argv.index("--bericht") + 1]
pathlib.Path(z).write_text(pathlib.Path({str(BEISPIELE / "vorpruefung_gebaut.txt")!r}).read_text())
sys.exit(1)
"""
FAKE_ZUSAMMEN = f"""
import sys, pathlib
z = pathlib.Path(sys.argv[sys.argv.index("--ziel") + 1])
z.with_suffix(".txt").write_text(pathlib.Path({str(BEISPIELE / "zusammenbau_iso800.txt")!r}).read_text())
sys.exit(1)
"""


def ohne_scope(python, skript, argumente, grenze, name):
    return [python, str(skript), *argumente]


class TestLauf(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.verfahren = self.tmp / "verfahren"
        self.verfahren.mkdir()
        (self.verfahren / "pruefen.py").write_text(FAKE_PRUEFEN)
        (self.verfahren / "zusammensetzen2.py").write_text(FAKE_ZUSAMMEN)
        self.daten = self.tmp / "data"
        reihe = self.daten / "reihen" / "ISO 800"
        reihe.mkdir(parents=True)
        (reihe / "bauteil.json").write_text("{}")
        for n in ("a.jpg", "b.jpg"):
            (reihe / n).write_bytes(b"")
        (self.daten / "referenz").mkdir()
        shutil.copy(BEISPIELE / "zusammenbau_iso800.txt", self.daten / "referenz" / "ISO 800.txt")

    def rechnen(self, jetzt, **mehr):
        return agent.lauf("bitte rechnen", "auftrag-1", daten=self.daten, jetzt=jetzt,
                          verfahren=self.verfahren, befehl=ohne_scope, **mehr)

    def test_lauf_gegen_referenz_und_dann_gegen_vorlauf(self):
        erg, text = self.rechnen(datetime(2026, 11, 7, 10, 0, 0))
        r = erg["reihen"]["ISO 800"]
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["vorpruefung"]["masstreue"], "GELB")
        self.assertEqual(r["zusammenbau"]["nahtversatz_median_mm"], 0.09)
        gespeichert = json.loads((self.daten / "laeufe" / "20261107-100000" / "lauf.json").read_text())
        self.assertEqual(gespeichert, erg)
        self.assertIn("gegen Referenzbericht: keine Änderung", text)
        self.assertIn("ISO 800: ok", agent.kurzfassung(erg))

        _, text2 = self.rechnen(datetime(2026, 11, 7, 11, 0, 0))
        self.assertIn("gegen Vorlauf 20261107-100000", text2)

    def test_zeitgrenze(self):
        (self.verfahren / "pruefen.py").write_text("import time; time.sleep(30)\n")
        erg, _ = self.rechnen(datetime(2026, 11, 7, 10, 0, 0), zeitgrenze_s=0.5)
        s = erg["reihen"]["ISO 800"]["schritte"]["vorpruefung"]
        self.assertEqual(s["status"], "zeitgrenze")
        self.assertEqual(erg["reihen"]["ISO 800"]["status"], "zeitgrenze")

    def test_keine_reihe(self):
        shutil.rmtree(self.daten / "reihen")
        erg, _ = self.rechnen(datetime(2026, 11, 7, 10, 0, 0))
        self.assertIn("keine Reihe", agent.kurzfassung(erg))


@unittest.skipUnless(shutil.which("systemd-run"), "systemd-run fehlt")
class TestSpeichergrenze(unittest.TestCase):
    def test_zu_grosser_schritt_bricht_nur_sich_ab(self):
        tmp = Path(tempfile.mkdtemp())
        skript = tmp / "gross.py"
        skript.write_text("b = bytearray(300 * 1024 * 1024)\n")
        cmd = pruefstand.befehl(sys.executable, skript, [], "60M", pruefstand.scope_name("test", tmp.name, "gross"))
        s = agent.schritt_ausfuehren(cmd, tmp, tmp / "aus.txt", 60)
        self.assertEqual(pruefstand.schritt_status("zusammenbau", s["exit"], s["zeit_um"], False), "speichergrenze")


if __name__ == "__main__":
    unittest.main()
