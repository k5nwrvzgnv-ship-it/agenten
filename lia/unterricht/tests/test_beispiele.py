import tempfile
import unittest
from pathlib import Path

import beispiele
import leitfaden
from tests.test_leitfaden import FalscherClaude

KATALOG = ("### Ethik 8: Helfen (data/wissen/text/Ethik/8. Klasse/Helfen/)\n- ABs/BBB_AB.docx.txt | Arbeitsblatt | BBB\n"
           "- ABs/AB_1.docx.txt | Arbeitsblatt | Singer\n- Außerdem, nur Dateinamen (...): x.txt\n")
LEITFADEN = "# So unterrichtet Lia\n\n## 7. Lias heutiger Stand\n- Kein Lückentext (entwicklung)\n"


class BeispieleTest(unittest.TestCase):
    def test_prompt(self):
        p = beispiele.prompt(KATALOG, LEITFADEN, "data/wissen/beispiele-vorschlag.md")
        for kurz, _ in beispiele.TYPEN:
            self.assertIn(f"- {kurz}: ", p)
        self.assertIn("## 7. Lias heutiger Stand", p)
        self.assertIn("- ABs/BBB_AB.docx.txt | Arbeitsblatt | BBB", p)
        self.assertIn("höchstens 25 Dateien", p)
        self.assertIn("mit Write nach data/wissen/beispiele-vorschlag.md", p)

    def test_erstellen(self):
        hier = Path(tempfile.mkdtemp())
        ziel = hier / "data" / "wissen" / "beispiele-vorschlag.md"
        claude = FalscherClaude(ziel, "## argumentieren: BBB\n" + "- Datei: ABs/BBB_AB.docx.txt\n" * 100)
        f = beispiele.erstellen(claude, KATALOG, LEITFADEN, hier, ziel)
        self.assertEqual((f.entwurf, f.quellen), (ziel, 3))
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "Kein freigegebener Leitfaden"):
            beispiele.erstellen(claude, KATALOG, "", hier, ziel)
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "Keine Quellen"):
            beispiele.erstellen(claude, "", LEITFADEN, hier, ziel)


if __name__ == "__main__":
    unittest.main()
