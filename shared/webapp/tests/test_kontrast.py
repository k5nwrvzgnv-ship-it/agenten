"""Lesbarkeit von ruhig.css (Untersuchung 11/2026, B19): Kontrast der grauen Schrift und Trefferflächen für Finger.

Gerechnet, nicht am Gerät gesehen: Kontrast nach WCAG 2 (relative Leuchtdichte), Grenze 4,5 für normale Schrift.
ruhig.css liegt zweimal (Web-App und Arbeitsplatz) und muss gleich bleiben.
"""

import re
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2]
DATEIEN = [SHARED / "webapp" / "statisch" / "ruhig.css", SHARED / "arbeitsplatz" / "statisch" / "ruhig.css"]
MINDEST = 4.5


def leuchtdichte(farbe: str) -> float:
    kanaele = [int(farbe[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [k / 12.92 if k <= 0.03928 else ((k + 0.055) / 1.055) ** 2.4 for k in kanaele]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def kontrast(a: str, b: str) -> float:
    hell, dunkel = sorted((leuchtdichte(a), leuchtdichte(b)), reverse=True)
    return (hell + 0.05) / (dunkel + 0.05)


def farben(css: str) -> dict[str, dict[str, str]]:
    """Farbvariablen aus :root, hell und dunkel."""
    hell = css[css.index(":root {"):css.index("@media (prefers-color-scheme: dark)")]
    dunkel = css[css.index("@media (prefers-color-scheme: dark)"):css.index("* { box-sizing")]
    return {name: dict(re.findall(r"--([a-z]+): (#[0-9a-f]{6})", teil)) for name, teil in (("hell", hell), ("dunkel", dunkel))}


class KontrastTest(unittest.TestCase):
    def test_rechnung(self):
        self.assertAlmostEqual(kontrast("#000000", "#ffffff"), 21.0, places=1)
        self.assertAlmostEqual(kontrast("#8c8b87", "#ffffff"), 3.41, places=2)  # alter Wert von --sehrleise

    def test_beide_dateien_gleich(self):
        self.assertEqual(DATEIEN[0].read_text(encoding="utf-8"), DATEIEN[1].read_text(encoding="utf-8"))

    def test_graue_schrift_ist_lesbar(self):
        je = farben(DATEIEN[0].read_text(encoding="utf-8"))
        for modus, f in je.items():
            for schrift in ("fg", "leise", "sehrleise"):
                for grund in ("bg", "flaeche"):
                    wert = kontrast(f[schrift], f[grund])
                    self.assertGreaterEqual(wert, MINDEST, f"{modus}: --{schrift} auf --{grund} hat nur {wert:.2f}")

    def test_abstufung_bleibt(self):
        """--sehrleise bleibt heller als --leise (im Dunklen: dunkler), sonst verliert die Oberfläche ihre Stufen."""
        je = farben(DATEIEN[0].read_text(encoding="utf-8"))
        self.assertGreater(leuchtdichte(je["hell"]["sehrleise"]), leuchtdichte(je["hell"]["leise"]))
        self.assertLess(leuchtdichte(je["dunkel"]["sehrleise"]), leuchtdichte(je["dunkel"]["leise"]))

    def test_trefferflaechen_fuer_finger(self):
        css = DATEIEN[0].read_text(encoding="utf-8")
        bloecke = re.findall(r"@media \(pointer: coarse\) \{(.*?)\n\}", css, flags=re.S)
        block = next((b for b in bloecke if "min-height: 44px" in b), None)
        self.assertIsNotNone(block, "Regel für pointer: coarse mit 44 px fehlt")
        selektoren = block[:block.index("{ min-height: 44px")]
        for s in (".knopf,", ".knopf-leise", ".knopf-klein", ".knopf-gross", ".baum-eintrag", ".rzeile", ".punkte-knopf"):
            self.assertIn(s, selektoren)
        self.assertNotIn("min-height: 44px", css.replace(block, ""))  # am Rechner bleibt die Oberfläche kompakt


if __name__ == "__main__":
    unittest.main()
