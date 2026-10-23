import tempfile
import unittest
from pathlib import Path

import verlauf
from tests.test_leitfaden import FalscherClaude, eintrag

EINTRAEGE = [
    eintrag("UBs+Feedback/UB_5_Pohlmann.anonym.txt", "Unterrichtsentwurf (anonymisiert)"),
    eintrag("UBs+Feedback/Kurzentwurf_7.15_Pohlmann.anonym.txt", "Unterrichtsentwurf (anonymisiert)"),
    eintrag("UBs+Feedback/UE_1_Pohlmann.anonym.txt", "Unterrichtsentwurf (anonymisiert)"),
    eintrag("UBs+Feedback/Feedback 1. UB Maier .docx", "Feedback"),
    eintrag("Ethik/Haluk Feedback Stunde 3 Lügen .docx", "Feedback"),
    eintrag("Ethik/Feedback_Ethik.docx", "Feedback"),  # Fragebogen für Schüler*innen: nicht
    eintrag("UBs+Feedback/Rosenberger_Hospiation_Reflexion.docx", "Sonstiges"),
    eintrag("Fachseminar_Ethik_Notizen.pages.txt", "Seminar und Notizen"),
    eintrag("Kriterien_gute_Unterrichtseinheit.txt", "Seminar und Notizen"),
    eintrag("Ethik/Tipps Max Examens.docx", "Seminar und Notizen"),  # nicht
    eintrag("Ethik/7. Klasse/Reihe Glück /Reihe_Glück.docx", "Reihenplanung"),  # nicht
    eintrag("UBs+Feedback/UB_4_Pohlmann.anonym.txt", "Unterrichtsentwurf (anonymisiert)", text=None),  # ohne Text
]


class VerlaufTest(unittest.TestCase):
    def test_quellen_waehlen(self):
        self.assertEqual([e.quelle for e in verlauf.quellen_waehlen(EINTRAEGE)], [
            "Kriterien_gute_Unterrichtseinheit.txt",
            "Fachseminar_Ethik_Notizen.pages.txt",
            "UBs+Feedback/UE_1_Pohlmann.anonym.txt",
            "UBs+Feedback/UB_5_Pohlmann.anonym.txt",
            "UBs+Feedback/Kurzentwurf_7.15_Pohlmann.anonym.txt",
            "Ethik/Haluk Feedback Stunde 3 Lügen .docx",
            "UBs+Feedback/Feedback 1. UB Maier .docx",
            "UBs+Feedback/Rosenberger_Hospiation_Reflexion.docx",
        ])

    def test_prompt(self):
        p = verlauf.prompt(verlauf.quellen_waehlen(EINTRAEGE), "data/wissen/entwicklung.md")
        self.assertIn("hat dieser Auswertung zugestimmt", p)
        self.assertIn("Vermutung, ausdrücklich als solche", p)
        self.assertIn("Keine Namen von", p)
        self.assertIn("mit Write nach data/wissen/entwicklung.md", p)
        self.assertNotIn("Feedback_Ethik", p)

    def test_erstellen(self):
        hier = Path(tempfile.mkdtemp())
        ziel = hier / "data" / "wissen" / "entwicklung.md"
        claude = FalscherClaude(ziel, "# Entwicklung\n" + "| Kriterium | o | + |\n" * 100)
        f = verlauf.erstellen(claude, EINTRAEGE, hier, ziel)
        self.assertEqual((f.entwurf, f.quellen), (ziel, 8))
        self.assertIn("data/wissen/entwicklung.md", claude.prompts[0])


if __name__ == "__main__":
    unittest.main()
