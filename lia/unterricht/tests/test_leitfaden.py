import tempfile
import unittest
from pathlib import Path

import leitfaden
import wissen
from agentkit.claude_lauf import Ergebnis


def eintrag(quelle: str, art: str, text: str | None = "x") -> wissen.Eintrag:
    return wissen.Eintrag(quelle=quelle, text=f"data/wissen/text/{quelle}.txt" if text else None, reihe="Ethik 7: Glück",
                          art=art, varianten=[], anfang="")


EINTRAEGE = [
    eintrag("UBs+Feedback/Feedback 1. UB Maier .docx", "Feedback"),
    eintrag("Ethik/7. Klasse/Reihe Glück /Reihe_Glück.docx", "Reihenplanung"),
    eintrag("Fachseminar_Ethik_Notizen.pages.txt", "Seminar und Notizen"),
    eintrag("UBs+Feedback/UB_5_Pohlmann.anonym.txt", "Unterrichtsentwurf (anonymisiert)"),
    eintrag("Ethik/7. Klasse/Reihe Glück /ABs/AB1.docx", "Arbeitsblatt"),
    eintrag("Ethik/Feedback_Ethik.docx", "Feedback"),
    eintrag("Ethik/7. Klasse/Reihe Lügen/Feedback SuS.docx", "Feedback"),
    eintrag("Ethik/8. Klasse/Reihe Strafe/Stoffverteilungsplan DS 11.docx", "Reihenplanung"),
    eintrag("Ethik/scan.pdf", "Reihenplanung", text=None),
]


class FalscherClaude:
    def __init__(self, ziel: Path | None, inhalt: str = "", ok: bool = True):
        self.ziel, self.inhalt, self.ok, self.prompts = ziel, inhalt, ok, []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append(prompt)
        if self.ziel:
            self.ziel.write_text(self.inhalt, encoding="utf-8")
        return Ergebnis(text="Quellen zu Folien sind dünn.", sitzung="s1", ok=self.ok, usd=2.5, tokens=500000)


class LeitfadenTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.ziel = self.hier / "data" / "wissen" / "leitfaden-entwurf.md"

    def test_quellen_waehlen(self):
        q = [e.quelle for e in leitfaden.quellen_waehlen(EINTRAEGE)]
        self.assertEqual(q, ["Fachseminar_Ethik_Notizen.pages.txt",
                             "Ethik/7. Klasse/Reihe Glück /Reihe_Glück.docx",
                             "UBs+Feedback/UB_5_Pohlmann.anonym.txt",
                             "UBs+Feedback/Feedback 1. UB Maier .docx"])

    def test_prompt(self):
        p = leitfaden.prompt(leitfaden.quellen_waehlen(EINTRAEGE), "data/wissen/leitfaden-entwurf.md")
        self.assertIn("- data/wissen/text/UBs+Feedback/UB_5_Pohlmann.anonym.txt.txt (Unterrichtsentwurf", p)
        self.assertIn("Nichts erfinden", p)
        self.assertIn("Keine Namen von Schüler*innen", p)
        self.assertIn("mit Write nach data/wissen/leitfaden-entwurf.md", p)
        self.assertNotIn("Feedback_Ethik", p)

    def test_erstellen(self):
        claude = FalscherClaude(self.ziel, "# Leitfaden\n" + "- Regel (Quelle)\n" * 200)
        f = leitfaden.erstellen(claude, EINTRAEGE, self.hier, self.ziel)
        self.assertEqual((f.entwurf, f.quellen, f.laeufe, f.usd, f.tokens), (self.ziel, 4, 1, 2.5, 500000))
        self.assertEqual(f.antwort, "Quellen zu Folien sind dünn.")
        self.assertEqual(len(claude.prompts), 1)

    def test_fehler(self):
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "Keine Quellen"):
            leitfaden.erstellen(FalscherClaude(self.ziel), [EINTRAEGE[4]], self.hier, self.ziel)
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "fehlgeschlagen"):
            leitfaden.erstellen(FalscherClaude(None, ok=False), EINTRAEGE, self.hier, self.ziel)
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "nicht geschrieben"):
            leitfaden.erstellen(FalscherClaude(None), EINTRAEGE, self.hier, self.ziel)
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "zu kurz"):
            leitfaden.erstellen(FalscherClaude(self.ziel, "# kurz"), EINTRAEGE, self.hier, self.ziel)

    def test_alter_entwurf_zaehlt_nicht(self):
        self.ziel.parent.mkdir(parents=True)
        self.ziel.write_text("alt " * 1000, encoding="utf-8")
        with self.assertRaisesRegex(leitfaden.LeitfadenFehler, "nicht geschrieben"):
            leitfaden.erstellen(FalscherClaude(None), EINTRAEGE, self.hier, self.ziel)


if __name__ == "__main__":
    unittest.main()
