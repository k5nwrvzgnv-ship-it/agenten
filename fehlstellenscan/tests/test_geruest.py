"""Prüft das Gerüst von fehlstellenscan. Kein Test darf PyTorch oder ultralytics importieren."""

import ast
import sys
import unittest
from pathlib import Path

import agent
import auswertung  # noqa: F401 – muss sich laden lassen
import datensatz  # noqa: F401 – muss sich laden lassen

HIER = Path(__file__).resolve().parent.parent
SCHWER = {"torch", "ultralytics", "torchvision"}


class TestGeruest(unittest.TestCase):
    def test_name(self):
        self.assertEqual(agent.AGENT, "fehlstellenscan")
        self.assertEqual(agent.ANZEIGE, "Fehlstellen-Scan")

    def test_auftrag_vorerst_mit_hinweis(self):
        status, ergebnis = agent.bearbeiten("irgendwas")
        self.assertEqual(status, "fehlgeschlagen")
        self.assertIn("noch nicht gebaut", ergebnis)

    def test_kein_schweres_paket_im_code(self):
        for datei in [*HIER.glob("*.py"), *HIER.glob("tests/*.py")]:
            baum = ast.parse(datei.read_text(encoding="utf-8"))
            for knoten in ast.walk(baum):
                if isinstance(knoten, ast.Import):
                    namen = {n.name.split(".")[0] for n in knoten.names}
                elif isinstance(knoten, ast.ImportFrom) and knoten.module:
                    namen = {knoten.module.split(".")[0]}
                else:
                    continue
                self.assertFalse(namen & SCHWER, f"{datei.name} importiert {namen & SCHWER}")

    def test_nichts_schweres_geladen(self):
        self.assertFalse(SCHWER & set(sys.modules))


if __name__ == "__main__":
    unittest.main()
