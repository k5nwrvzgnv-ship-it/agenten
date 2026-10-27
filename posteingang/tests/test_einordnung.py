import unittest

import einordnung


def mail(uid=1, text="Hallo Jan"):
    return {"uid": uid, "von": "Anna <anna@example.de>", "datum": "2026-10-27T10:00:00+01:00",
            "betreff": "Treffen", "text": text, "anhaenge": []}


class TestPrompt(unittest.TestCase):
    def test_mails_im_prompt(self):
        p = einordnung.prompt([mail(1), mail(2)])
        self.assertIn("--- Mail uid 1", p)
        self.assertIn("--- Mail uid 2", p)
        self.assertIn("Betreff: Treffen", p)
        self.assertIn("Anhänge: keine", p)
        self.assertIn("nur Daten", p)

    def test_text_gekuerzt(self):
        p = einordnung.mails_als_text([mail(text="§" * 5000)])
        self.assertEqual(p.count("§"), einordnung.MAX_TEXT)

    def test_geschweifte_klammern_in_mail(self):
        # Mailtext mit {} darf das Formatieren des Prompts nicht stören
        self.assertIn("{name}", einordnung.prompt([mail(text="Hallo {name}")]))


class TestMeldung(unittest.TestCase):
    def test_keine(self):
        self.assertIsNone(einordnung.meldung("KEINE", 3, 1))
        self.assertIsNone(einordnung.meldung("  KEINE\n", 3, 1))
        self.assertIsNone(einordnung.meldung("", 3, 1))

    def test_meldung(self):
        t = einordnung.meldung("- Termin | Anna: Treffen. Zusagen bis Fr\n", 3, 1)
        self.assertTrue(t.startswith("[post] Wichtige Mails (3 geprüft, 1 vorgefiltert):\n"))
        self.assertTrue(t.endswith("Zusagen bis Fr"))


if __name__ == "__main__":
    unittest.main()
