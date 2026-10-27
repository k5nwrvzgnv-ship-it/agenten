import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mail

ORIGINAL = {"uid": 42, "von": "Prof. Jack <stefan.jack@bfh.ch>", "antwort_an": "stefan.jack@bfh.ch",
            "message_id": "<abc@bfh.ch>", "references": "<vorher@bfh.ch>", "betreff": "CAM-Übung", "text": "..."}


class TestPruefen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self._tmp.name)
        mail.mail_merken(ORIGINAL, self.ordner)

    def tearDown(self):
        self._tmp.cleanup()

    def test_neue_mail(self):
        d = mail.pruefen({"an": "Henri <henri@hnee.de>", "cc": ["HENRI@hnee.de", "x@hnee.de"],
                          "betreff": "  Gruppe\n Holzschutz ", "text": " Hallo\n", "begruendung": "Gruppenwahl",
                          "unbekannt": "weg"}, self.ordner)
        self.assertEqual(d, {"an": ["henri@hnee.de"], "cc": ["x@hnee.de"], "betreff": "Gruppe Holzschutz",
                             "text": "Hallo", "begruendung": "Gruppenwahl"})

    def test_antwort_bezug_aus_originalmail(self):
        d = mail.pruefen({"an": ["stefan.jack@bfh.ch"], "betreff": "AW: CAM-Übung", "text": "Danke",
                          "antwort_auf_uid": 42, "in_reply_to": "<gefaelscht@x>"}, self.ordner)
        self.assertEqual(d["in_reply_to"], "<abc@bfh.ch>")
        self.assertEqual(d["references"], "<vorher@bfh.ch> <abc@bfh.ch>")
        self.assertEqual(d["antwort_auf"], "Prof. Jack <stefan.jack@bfh.ch>: CAM-Übung")

    def test_fehler(self):
        gut = {"an": ["a@hnee.de"], "betreff": "B", "text": "T"}
        for kaputt, teil in [({"an": []}, "mindestens ein"), ({"an": ["kein-at"]}, "keine gültige"),
                             ({"an": ["a@b"]}, "keine gültige"), ({"betreff": ""}, "betreff"),
                             ({"text": " "}, "text"), ({"an": [f"{i}@hnee.de" for i in range(6)]}, "höchstens"),
                             ({"antwort_auf_uid": 7}, "nicht in data/mails"), ({"antwort_auf_uid": "x"}, "keine Zahl"),
                             ({"an": "a@hnee.de\nBcc: b@c.de"}, "keine gültige")]:
            with self.subTest(kaputt=kaputt), self.assertRaisesRegex(mail.MailFehler, teil):
                mail.pruefen({**gut, **kaputt}, self.ordner)
        with self.assertRaises(mail.MailFehler):
            mail.pruefen(["kein", "objekt"], self.ordner)


class TestAnzeigeUndBauen(unittest.TestCase):
    DATEN = {"an": ["stefan.jack@bfh.ch"], "cc": ["henri@hnee.de"], "betreff": "AW: CAM-Übung",
             "text": "Guten Tag Herr Jack,\nkann ich online teilnehmen?\n\nJan Kleinke", "begruendung": "Rückfrage",
             "in_reply_to": "<abc@bfh.ch>", "references": "<abc@bfh.ch>", "antwort_auf": "Jack: CAM-Übung"}

    def test_anzeige_zeigt_alles(self):
        text = mail.anzeige(self.DATEN)
        for teil in ("An: stefan.jack@bfh.ch", "Cc: henri@hnee.de", "Antwort auf: Jack: CAM-Übung",
                     "Betreff: AW: CAM-Übung", "kann ich online teilnehmen?", "(Warum: Rückfrage)"):
            self.assertIn(teil, text)

    def test_bauen(self):
        msg = mail.bauen(self.DATEN, "jkl298@hnee.de", "Jan Kleinke", jetzt=0)
        self.assertEqual(msg["From"], "Jan Kleinke <jkl298@hnee.de>")
        self.assertEqual(msg["To"], "stefan.jack@bfh.ch")
        self.assertEqual(msg["Cc"], "henri@hnee.de")
        self.assertEqual(msg["In-Reply-To"], "<abc@bfh.ch>")
        self.assertTrue(msg["Message-ID"].endswith("@hnee.de>"))
        self.assertIn("online teilnehmen", msg.get_content())
        self.assertIsNone(mail.bauen({**self.DATEN, "cc": [], "in_reply_to": None}, "a@hnee.de")["Cc"])


class TestSenden(unittest.TestCase):
    CFG = {"MAIL_ABSENDER": "jkl298@hnee.de", "MAIL_NAME": "Jan Kleinke", "IMAP_HOST": "mail.hnee.de",
           "HNEE_NUTZER": "jkl298", "HNEE_KENNWORT": "geheim"}
    DATEN = {"an": ["a@hnee.de"], "cc": [], "betreff": "Test", "text": "Hallo"}

    def test_senden_und_gesendet(self):
        with mock.patch.object(mail._mail.smtplib, "SMTP") as smtp, mock.patch.object(mail._mail.imaplib, "IMAP4_SSL") as imap:
            smtp.return_value.send_message.return_value = {}
            imap.return_value.__enter__.return_value.append.return_value = ("OK", [b""])
            ergebnis = mail.senden(self.CFG, self.DATEN)
        s = smtp.return_value
        smtp.assert_called_once_with("mail.hnee.de", 587, timeout=60)
        s.starttls.assert_called_once()
        s.login.assert_called_once_with("jkl298", "geheim")
        s.send_message.assert_called_once()
        self.assertEqual(imap.return_value.__enter__.return_value.append.call_args.args[0], '"Gesendete Elemente"')
        self.assertEqual(ergebnis, "Mail gesendet an a@hnee.de: Test")

    def test_gesendet_fehler_ist_kein_sendefehler(self):
        with mock.patch.object(mail._mail.smtplib, "SMTP") as smtp, \
             mock.patch.object(mail._mail.imaplib, "IMAP4_SSL", side_effect=OSError("weg")):
            smtp.return_value.send_message.return_value = {}
            self.assertIn("Kopie in Gesendet fehlgeschlagen", mail.senden(self.CFG, self.DATEN))

    def test_abgelehnte_empfaenger_und_ohne_absender(self):
        with mock.patch.object(mail._mail.smtplib, "SMTP") as smtp, mock.patch.object(mail._mail.imaplib, "IMAP4_SSL"):
            smtp.return_value.send_message.return_value = {"a@hnee.de": (550, b"x")}
            with self.assertRaisesRegex(mail.MailFehler, "abgelehnt"):
                mail.senden(self.CFG, self.DATEN)
        with self.assertRaisesRegex(mail.MailFehler, "MAIL_ABSENDER"):
            mail.senden({**self.CFG, "MAIL_ABSENDER": ""}, self.DATEN)

    def test_eintraege_in_env_gehen_vor(self):
        cfg = {**self.CFG, "MAIL_NUTZER": "anders", "MAIL_KENNWORT": "k2", "GESENDET_ORDNER": "Sent", "SMTP_PORT": ""}
        with mock.patch.object(mail._mail.smtplib, "SMTP") as smtp, mock.patch.object(mail._mail.imaplib, "IMAP4_SSL") as imap:
            smtp.return_value.send_message.return_value = {}
            imap.return_value.__enter__.return_value.append.return_value = ("OK", [b""])
            mail.senden(cfg, self.DATEN)
        smtp.return_value.login.assert_called_once_with("anders", "k2")
        self.assertEqual(imap.return_value.__enter__.return_value.append.call_args.args[0], '"Sent"')
