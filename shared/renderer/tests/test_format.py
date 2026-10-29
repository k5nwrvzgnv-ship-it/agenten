"""FORMAT.md bleibt richtig: Jedes JSON-Beispiel darin besteht die Prüfung."""

import re
import tomllib
import unittest
from pathlib import Path

from renderer import design, pruefen
from renderer.icons import NAMEN

FORMAT = Path(__file__).resolve().parent.parent / "FORMAT.md"
BEISPIELE = Path(__file__).resolve().parent.parent / "beispiele"
PROFIL = BEISPIELE / "profil-lia-stil.toml"


class TestFormat(unittest.TestCase):
    def test_beispiele_sind_gueltig(self):
        beispiele = re.findall(r"```json\n(.*?)```", FORMAT.read_text(encoding="utf-8"), re.S)
        self.assertEqual(len(beispiele), 4)
        for text in beispiele:
            self.assertEqual(pruefen(text), [], text[:60])

    def test_beispieldateien_sind_gueltig(self):
        for datei in BEISPIELE.glob("*.json"):
            self.assertEqual(pruefen(datei.read_text(encoding="utf-8")), [], datei.name)

    def test_alle_icons_genannt(self):
        text = FORMAT.read_text(encoding="utf-8")
        self.assertEqual([n for n in NAMEN if f"`{n}`" not in text], [])


    def test_beispiel_profil(self):
        with open(PROFIL, "rb") as f:
            profil = design.profil_lesen(tomllib.load(f))
        self.assertEqual(profil["farben"]["akzent"], "C00000")
        self.assertEqual(profil["lehrkraft"], "")  # keine Daten einer Person im Renderer

    def test_beispiel_profil_zusammenfassung(self):
        with open(BEISPIELE / "profil-jan-zusammenfassung.toml", "rb") as f:
            profil = design.profil_lesen(tomllib.load(f))
        self.assertEqual((profil["schrift"], profil["schriftgroesse_pt"]), ("Calibri", 11))
        self.assertEqual(profil["erstellt_von"], "")  # trägt der Agent ein


if __name__ == "__main__":
    unittest.main()
