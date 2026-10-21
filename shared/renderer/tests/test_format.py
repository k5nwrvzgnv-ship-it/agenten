"""FORMAT.md bleibt richtig: Jedes JSON-Beispiel darin besteht die Prüfung."""

import re
import unittest
from pathlib import Path

from renderer import pruefen
from renderer.icons import NAMEN

FORMAT = Path(__file__).resolve().parent.parent / "FORMAT.md"


class TestFormat(unittest.TestCase):
    def test_beispiele_sind_gueltig(self):
        beispiele = re.findall(r"```json\n(.*?)```", FORMAT.read_text(encoding="utf-8"), re.S)
        self.assertEqual(len(beispiele), 2)
        for text in beispiele:
            self.assertEqual(pruefen(text), [], text[:60])

    def test_alle_icons_genannt(self):
        text = FORMAT.read_text(encoding="utf-8")
        self.assertEqual([n for n in NAMEN if f"`{n}`" not in text], [])


if __name__ == "__main__":
    unittest.main()
