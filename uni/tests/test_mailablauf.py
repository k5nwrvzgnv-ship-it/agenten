import unittest
from datetime import date

import mailablauf
from agentkit import mailauftrag

BOEHME = {"uid": 11077, "von": '"Böhme, Thomas" <Thomas.Boehme@hnee.de>', "message_id": "<b@hnee.de>",
          "betreff": "AW: Anfrage Betreuung", "datum": "2026-10-26T09:44:02+01:00", "text": "Lieber Herr Kleinke"}


class TestErkennen(unittest.TestCase):
    def test_prompt_enthaelt_entscheidung_und_suche(self):
        p = mailablauf.prompt_erkennen("antworte Böhme", date(2026, 10, 28))
        self.assertIn('{"mail": false}', p)
        self.assertIn("antworte Böhme", p)
        self.assertIn("Hochschulpostfach jkl298@hnee.de", p)
        self.assertIn("1100", p)

    def test_keine_mail(self):
        self.assertIsNone(mailablauf.erkennen_lesen('{"mail": false}'))
        self.assertIsNone(mailablauf.erkennen_lesen('```json\n{"mail": "ja", "personen": ["Boehme"]}\n```'))

    def test_mail_mit_suchbegriffen(self):
        suche = mailablauf.erkennen_lesen('{"mail": true, "personen": ["Boehme"], "stichworte": ["Holzlamellen"], '
                                          '"tage_zurueck": 5000, "kalender_tage": 14}')
        self.assertEqual(suche["personen"], ["Boehme"])
        self.assertEqual(suche["tage_zurueck"], 1100)

    def test_unlesbar(self):
        for text in ("kein json", '["liste"]', '{"mail": true}'):
            with self.subTest(text=text), self.assertRaises(mailauftrag.AuftragFehler):
                mailablauf.erkennen_lesen(text)


class TestWunsch(unittest.TestCase):
    def test_lesen(self):
        self.assertEqual(mailablauf.wunsch_lesen({"auftrag": " Antwort ", "antwort_auf_uid": "11077"}),
                         ("Antwort", 11077))
        self.assertEqual(mailablauf.wunsch_lesen({"auftrag": "Neu", "antwort_auf_uid": None}), ("Neu", None))
        for kaputt in ([], {"auftrag": ""}, {"auftrag": "x" * 3001}, {"auftrag": "a", "antwort_auf_uid": "x"}):
            with self.subTest(kaputt=kaputt), self.assertRaises(mailablauf.WunschFehler):
                mailablauf.wunsch_lesen(kaputt)

    def test_original_schon_gefunden(self):
        kontext = {"mails": [{"message_id": "<a@x>", "schluessel": "m1"}, {"message_id": "<b@hnee.de>", "schluessel": "m2"}]}
        self.assertEqual(mailablauf.original_einfuegen(kontext, BOEHME), "m2")
        self.assertEqual(len(kontext["mails"]), 2)

    def test_original_fehlt_kommt_als_m0(self):
        kontext = {"mails": [{"message_id": "<a@x>", "schluessel": "m1"}]}
        self.assertEqual(mailablauf.original_einfuegen(kontext, BOEHME), "m0")
        self.assertEqual(kontext["mails"][0]["ordner"], "INBOX")
        self.assertEqual(kontext["mails"][0]["uid"], 11077)

    def test_wunsch_text(self):
        self.assertEqual(mailablauf.wunsch_text("Danke sagen", None, None), "Danke sagen")
        t = mailablauf.wunsch_text("Danke sagen", BOEHME, "m0")
        self.assertIn("vom 26.10.2026", t)
        self.assertIn('antwort_auf = "m0"', t)


class TestRegel(unittest.TestCase):
    def test_regel_aus(self):
        self.assertEqual(mailablauf.regel_aus('{"entwurf": {}, "regel": {"regel": " Lehrende  siezen ", "anlass": "x"}}'),
                         {"regel": "Lehrende siezen", "anlass": "x"})
        for text in ('{"entwurf": {}}', '{"regel": "nur text"}', '{"regel": {"regel": " "}}', "kein json"):
            with self.subTest(text=text):
                self.assertIsNone(mailablauf.regel_aus(text))


if __name__ == "__main__":
    unittest.main()
