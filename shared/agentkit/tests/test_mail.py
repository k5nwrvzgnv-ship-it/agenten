import email
import email.policy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentkit import mail

ENTWURF = {"an": ["Frau Müller <m@x.de>", "m@x.de"], "cc": "M@X.de", "betreff": "  Termin   am Freitag ",
           "text": "Liebe Frau Müller,\n\nich muss absagen.\n", "begruendung": "Jan  ist krank", "uid": 5}
ORIGINAL = {"uid": 51740, "von": "Frau Müller <m@x.de>", "message_id": "<b@x.de>", "references": "<a@x.de>",
            "betreff": "Termin", "datum": "2026-10-26T10:00:00+01:00", "wortlaut": "Bis Freitag!", "ordner": "INBOX"}
CFG = {"MAIL_ABSENDER": "jan@kleinke.org", "MAIL_NAME": "Jan Kleinke", "SMTP_HOST": "smtp.test",
       "SMTP_PORT": "465", "IMAP_HOST": "imap.test", "IMAP_NUTZER": "jan@kleinke.org", "IMAP_KENNWORT": "geheim",
       "GESENDET_ORDNER": "Sent"}


class TestPruefen(unittest.TestCase):
    def test_neue_mail_nur_bekannte_felder(self):
        daten = mail.pruefen(ENTWURF)
        self.assertEqual(daten, {"an": ["m@x.de"], "cc": [], "betreff": "Termin am Freitag",
                                 "text": "Liebe Frau Müller,\n\nich muss absagen.", "begruendung": "Jan ist krank"})

    def test_antwort_aus_original(self):
        daten = mail.pruefen(ENTWURF, ORIGINAL)
        self.assertEqual(daten["in_reply_to"], "<b@x.de>")
        self.assertEqual(daten["references"], "<a@x.de> <b@x.de>")
        self.assertEqual(daten["antwort_auf"], "Frau Müller <m@x.de>: Termin")
        self.assertEqual(daten["antwort_auf_von"], "Frau Müller <m@x.de>")
        self.assertEqual(daten["antwort_auf_datum"], "2026-10-26T10:00:00+01:00")

    def test_pruefen_frage(self):
        daten = mail.pruefen({**ENTWURF, "pruefen": " ob  Freitag passt "})
        self.assertEqual(daten["pruefen"], "ob Freitag passt")
        self.assertTrue(mail.anzeige(daten).endswith("\n\nBitte prüfen: ob Freitag passt"))
        self.assertNotIn("pruefen", mail.pruefen(ENTWURF))
        with self.assertRaises(mail.MailFehler):
            mail.pruefen({**ENTWURF, "pruefen": "x" * 501})

    def test_fehler(self):
        for falsch in ("text", {**ENTWURF, "an": []}, {**ENTWURF, "an": ["kein-at"]}, {**ENTWURF, "an": 5},
                       {**ENTWURF, "betreff": ""}, {**ENTWURF, "text": " "}, {**ENTWURF, "betreff": "x" * 201},
                       {**ENTWURF, "an": [f"a{i}@x.de" for i in range(6)]}):
            with self.subTest(falsch=falsch), self.assertRaises(mail.MailFehler):
                mail.pruefen(falsch)
        with self.assertRaises(mail.MailFehler):
            mail.pruefen(ENTWURF, {**ORIGINAL, "message_id": ""})


class TestAnzeigeBauen(unittest.TestCase):
    def test_anzeige(self):
        text = mail.anzeige(mail.pruefen({**ENTWURF, "cc": ["c@y.de"]}, ORIGINAL))
        self.assertEqual(text.split("\n")[:4], ["An: m@x.de", "Cc: c@y.de", "Antwort auf: Frau Müller <m@x.de>: Termin",
                                                "Betreff: Termin am Freitag"])
        self.assertTrue(text.endswith("(Warum: Jan ist krank)"))

    def test_wortlaut(self):
        text = mail.wortlaut(ORIGINAL)
        self.assertIn("Datum: 26.10.2026 10:00", text)
        self.assertTrue(text.endswith("\n\nBis Freitag!"))
        self.assertTrue(mail.wortlaut({"text": "kurz"}).endswith("kurz"))

    def test_bauen(self):
        msg = mail.bauen(mail.pruefen(ENTWURF, ORIGINAL), "jan@kleinke.org", "Jan Kleinke", jetzt=0)
        n = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
        self.assertEqual(n["From"], "Jan Kleinke <jan@kleinke.org>")
        self.assertEqual(n["To"], "m@x.de")
        self.assertEqual(n["In-Reply-To"], "<b@x.de>")
        self.assertEqual(n["References"], "<a@x.de> <b@x.de>")
        self.assertTrue(n["Message-ID"].endswith("@kleinke.org>"))
        self.assertIn("ich muss absagen.", n.get_content())


class TestAnhaenge(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ordner = Path(tmp.name) / "uni"
        (self.ordner / "data").mkdir(parents=True)
        (self.ordner / ".env").write_text("KENNWORT=geheim")
        self.pdf = self.ordner / "data" / "Exposé Holz.pdf"
        self.pdf.write_bytes(b"%PDF-1.4 " + b"x" * 2048)
        (self.ordner / "data" / "notiz.txt").write_bytes("Grüße\n".encode())

    def pruefen(self, *dateien):
        return mail.pruefen(ENTWURF, anhaenge=list(dateien), ordner=self.ordner)

    def test_daten_und_anzeige(self):
        daten = self.pruefen("data/Exposé Holz.pdf", "data/Exposé Holz.pdf")
        (anhang,) = daten["anhaenge"]
        self.assertEqual((anhang["name"], anhang["groesse"]), ("Exposé Holz.pdf", 2057))
        self.assertEqual(anhang["sha256"], hashlib.sha256(self.pdf.read_bytes()).hexdigest())
        self.assertIn("Anhang: Exposé Holz.pdf (2 KB)", mail.anzeige(daten))
        self.assertEqual(mail.anhang_zeile({"name": "a", "groesse": 5}), "a (5 Byte)")
        self.assertEqual(mail.anhang_zeile({"name": "a", "groesse": 1572864}), "a (1,5 MB)")

    def test_ohne_anhaenge_kein_feld(self):
        self.assertNotIn("anhaenge", mail.pruefen(ENTWURF))

    def test_feld_aus_claudes_entwurf_wird_ignoriert(self):
        daten = mail.pruefen({**ENTWURF, "anhaenge": [".env"]}, ordner=self.ordner)
        self.assertNotIn("anhaenge", daten)

    def test_abgelehnte_dateien(self):
        (self.ordner.parent / "fremd.pdf").write_bytes(b"x")
        (self.ordner / "data" / "hinaus.pdf").symlink_to(self.ordner.parent / "fremd.pdf")
        (self.ordner / "data" / "tarnung.pdf").symlink_to(self.ordner / ".env")
        for datei in (".env", "../fremd.pdf", "data/hinaus.pdf", "data/tarnung.pdf", "data/fehlt.pdf", "data"):
            with self.subTest(datei), self.assertRaises(mail.MailFehler):
                self.pruefen(datei)

    def test_ohne_ordner_kein_stiller_verlust(self):
        with self.assertRaises(mail.MailFehler):
            mail.pruefen(ENTWURF, anhaenge=["data/notiz.txt"])

    def test_grenzen(self):
        with self.assertRaises(mail.MailFehler):
            self.pruefen(*[f"data/{i}.pdf" for i in range(mail.MAX_ANHAENGE + 1)])
        with mock.patch.object(mail, "MAX_ANHAENGE_BYTES", 2000), self.assertRaises(mail.MailFehler):
            self.pruefen("data/Exposé Holz.pdf")

    def test_bauen_haengt_an(self):
        daten = self.pruefen("data/Exposé Holz.pdf", "data/notiz.txt")
        msg = mail.bauen(daten, "jan@kleinke.org", jetzt=0)
        n = email.message_from_bytes(msg.as_bytes(), policy=email.policy.default)
        self.assertIn("ich muss absagen.", n.get_body().get_content())
        (a, b) = n.iter_attachments()
        self.assertEqual((a.get_filename(), a.get_content_type()), ("Exposé Holz.pdf", "application/pdf"))
        self.assertEqual(a.get_content(), self.pdf.read_bytes())
        self.assertEqual((b.get_filename(), b.get_content_type()), ("notiz.txt", "text/plain"))

    def test_geaenderte_oder_fehlende_datei_wird_nicht_gesendet(self):
        daten = self.pruefen("data/Exposé Holz.pdf")
        self.pdf.write_bytes(b"andere Fassung")
        with self.assertRaisesRegex(mail.MailFehler, "seit der Freigabe geändert"):
            mail.bauen(daten, "jan@kleinke.org")
        self.pdf.unlink()
        with self.assertRaisesRegex(mail.MailFehler, "nichts gesendet"):
            mail.bauen(daten, "jan@kleinke.org")
        aufrufe = []
        with mock.patch("smtplib.SMTP_SSL", FalscherServer("ssl", aufrufe)), self.assertRaises(mail.MailFehler):
            mail.senden(CFG, daten)
        self.assertEqual(aufrufe, [])

    def test_senden_nennt_anhang_und_kopie_enthaelt_ihn(self):
        aufrufe, kopien = [], []

        class Imap(FalscherServer):
            def append(self, ordner, flags, _zeit, roh):
                kopien.append(roh)
                return "OK", [b""]

        with mock.patch("smtplib.SMTP_SSL", FalscherServer("ssl", aufrufe)), \
                mock.patch("imaplib.IMAP4_SSL", Imap("imap", aufrufe)):
            ergebnis = mail.senden(CFG, self.pruefen("data/notiz.txt"))
        self.assertIn("(Anhang: notiz.txt (8 Byte))", ergebnis)
        self.assertEqual(len([a for a in aufrufe if a[1] == "send"]), 1)
        kopie = email.message_from_bytes(kopien[0], policy=email.policy.default)
        self.assertEqual([a.get_filename() for a in kopie.iter_attachments()], ["notiz.txt"])


class FalscherServer:
    """Ersatz für SMTP, SMTP_SSL und IMAP4_SSL: merkt sich alle Aufrufe in einer gemeinsamen Liste."""

    def __init__(self, art, aufrufe, abgelehnt=None):
        self.art, self.aufrufe, self.abgelehnt = art, aufrufe, abgelehnt or {}

    def __call__(self, host, port, timeout=None):
        self.aufrufe.append((self.art, host, port))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def starttls(self):
        self.aufrufe.append((self.art, "starttls"))

    def login(self, nutzer, kennwort):
        self.aufrufe.append((self.art, "login", nutzer, kennwort))

    def send_message(self, msg):
        self.aufrufe.append((self.art, "send", msg["To"]))
        return self.abgelehnt

    def append(self, ordner, flags, _zeit, _roh):
        self.aufrufe.append((self.art, "append", ordner, flags))
        return "OK", [b""]


class TestSenden(unittest.TestCase):
    def senden(self, cfg, abgelehnt=None):
        aufrufe = []
        with mock.patch("smtplib.SMTP_SSL", FalscherServer("ssl", aufrufe, abgelehnt)), \
                mock.patch("smtplib.SMTP", FalscherServer("smtp", aufrufe, abgelehnt)), \
                mock.patch("imaplib.IMAP4_SSL", FalscherServer("imap", aufrufe)):
            return mail.senden(cfg, mail.pruefen(ENTWURF)), aufrufe

    def test_ssl_bei_465_mit_imap_login_und_kopie(self):
        ergebnis, aufrufe = self.senden(CFG)
        self.assertEqual(aufrufe, [("ssl", "smtp.test", 465), ("ssl", "login", "jan@kleinke.org", "geheim"),
                                   ("ssl", "send", "m@x.de"), ("imap", "imap.test", 993),
                                   ("imap", "login", "jan@kleinke.org", "geheim"),
                                   ("imap", "append", '"Sent"', r"(\Seen)")])
        self.assertEqual(ergebnis, "Mail gesendet an m@x.de: Termin am Freitag")

    def test_starttls_sonst_und_eigener_login(self):
        cfg = {**CFG, "SMTP_PORT": "587", "MAIL_NUTZER": "m1", "MAIL_KENNWORT": "k1"}
        _, aufrufe = self.senden(cfg)
        self.assertEqual(aufrufe[:3], [("smtp", "smtp.test", 587), ("smtp", "starttls"), ("smtp", "login", "m1", "k1")])
        self.assertIn(("imap", "login", "m1", "k1"), aufrufe)

    def test_ohne_gesendet_ordner_keine_kopie(self):
        ergebnis, aufrufe = self.senden({k: v for k, v in CFG.items() if k != "GESENDET_ORDNER"})
        self.assertFalse([a for a in aufrufe if a[0] == "imap"])
        self.assertIn("keine Kopie in Gesendet", ergebnis)

    def test_fehler(self):
        with self.assertRaises(mail.MailFehler):
            self.senden({**CFG, "MAIL_ABSENDER": ""})
        with self.assertRaises(mail.MailFehler):
            self.senden({k: v for k, v in CFG.items() if k != "IMAP_KENNWORT"})
        with self.assertRaises(mail.MailFehler):
            self.senden(CFG, abgelehnt={"m@x.de": (550, b"nein")})


if __name__ == "__main__":
    unittest.main()
