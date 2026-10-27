import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentkit import imap

MAIL = (b"From: =?utf-8?q?Pr=C3=BCfungsamt?= <pa@hnee.de>\r\n"
        b"Subject: =?utf-8?q?Pr=C3=BCfungsanmeldung?=\r\n"
        b"Date: Fri, 16 Oct 2026 09:00:00 +0200\r\n"
        b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=X\r\n\r\n"
        b"--X\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
        b"<p>Anmeldung bis <b>30.10.</b></p><style>p{}</style>\r\n"
        b"--X\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename=liste.pdf\r\n\r\n"
        b"JVBERi0=\r\n--X--\r\n")


class TestImap(unittest.TestCase):
    def test_zerlege(self):
        m = imap.zerlege(7, MAIL)
        self.assertEqual(m["uid"], 7)
        self.assertEqual(m["betreff"], "Prüfungsanmeldung")
        self.assertIn("Prüfungsamt", m["von"])
        self.assertEqual(m["text"], "Anmeldung bis 30.10.")
        self.assertEqual(m["anhaenge"], ["liste.pdf"])
        self.assertTrue(m["datum"].startswith("2026-10-16T09:00"))
        self.assertEqual(m["wortlaut"], "Anmeldung bis 30.10.")

    def test_wortlaut_mit_absaetzen_ohne_verlauf(self):
        roh = ("Sehr geehrter Herr Kleinke,\r\n\r\nich übernehme   die Betreuung.\r\n\r\n\r\n\r\nGrüße\r\nT. Böhme\r\n"
               "\r\nVon: Jan Kleinke <j@hnee.de>\r\nGesendet: Montag, 26. Oktober 2026\r\nAnfrage")
        self.assertEqual(imap.wortlaut(roh), "Sehr geehrter Herr Kleinke,\n\nich übernehme die Betreuung.\n\n"
                                                 "Grüße\nT. Böhme\n\n[älterer Verlauf weggelassen]")
        self.assertEqual(imap.wortlaut("Ja.\nAm 26.10.2026 um 10:00 schrieb Jan Kleinke:\n> Frage"),
                         "Ja.\n\n[älterer Verlauf weggelassen]")
        outlook = "BG, TB.\n\nVon: Kleinke, Jan <j@hnee.de>\n\nGesendet: Mittwoch, 21. Oktober 2026 12:57\n\nAn: B"
        self.assertEqual(imap.wortlaut(outlook), "BG, TB.\n\n[älterer Verlauf weggelassen]")

    def test_html_umbrueche(self):
        mail = (b"From: a@hnee.de\r\nSubject: x\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
                b"<p>Hallo,</p><p>Zeile 1<br>Zeile 2</p>")
        self.assertEqual(imap.zerlege(1, mail)["wortlaut"], "Hallo,\nZeile 1\nZeile 2")


class FalschesImap:
    """Ersatz für imaplib.IMAP4_SSL: merkt sich Aufrufe, liefert feste UIDs."""

    def __init__(self, uids, uidvalidity=5):
        self.uids, self.uidvalidity, self.aufrufe = uids, uidvalidity, []

    def __call__(self, host, port):
        self.aufrufe.append(("verbinden", host, port))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def login(self, nutzer, kennwort):
        self.aufrufe.append(("login", nutzer, kennwort))

    def select(self, ordner, readonly=False):
        self.aufrufe.append(("select", ordner, readonly))

    def response(self, _):
        return "UIDVALIDITY", [str(self.uidvalidity).encode()]

    def uid(self, befehl, *args):
        if befehl == "search":
            return "OK", [b" ".join(str(u).encode() for u in self.uids)]
        self.aufrufe.append(("fetch", args[0], args[1]))
        return "OK", [(b"1 (BODY[] {10}", MAIL), b")"]


class TestNeueMails(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stand = Path(self.tmp.name) / "data" / "postfach.json"

    def tearDown(self):
        self.tmp.cleanup()

    def holen(self, falsch, **kw):
        with mock.patch("imaplib.IMAP4_SSL", falsch):
            return imap.neue_mails("host", 993, "jan", "geheim", self.stand, **kw)

    def test_erster_lauf_setzt_nur_marke(self):
        self.assertEqual(self.holen(FalschesImap([1, 2, 3])), [])
        self.assertEqual(json.loads(self.stand.read_text()), {"uidvalidity": 5, "letzte_uid": 3})

    def test_nur_neue_lesend_und_mit_peek(self):
        self.holen(FalschesImap([1, 2, 3]))
        falsch = FalschesImap([1, 2, 3, 4, 5])
        mails = self.holen(falsch)
        self.assertEqual([m["uid"] for m in mails], [4, 5])
        self.assertIn(("select", "INBOX", True), falsch.aufrufe)
        self.assertIn(("login", "jan", "geheim"), falsch.aufrufe)
        self.assertTrue(all(a[2] == "(BODY.PEEK[])" for a in falsch.aufrufe if a[0] == "fetch"))
        self.assertEqual(json.loads(self.stand.read_text())["letzte_uid"], 5)
        self.assertEqual(self.holen(FalschesImap([1, 2, 3, 4, 5])), [])

    def test_hoechstens_max_mails(self):
        self.holen(FalschesImap([1]))
        mails = self.holen(FalschesImap([1, 2, 3, 4]), max_mails=2)
        self.assertEqual([m["uid"] for m in mails], [2, 3])
        self.assertEqual([m["uid"] for m in self.holen(FalschesImap([1, 2, 3, 4]))], [4])

    def test_neue_uidvalidity_setzt_marke_neu(self):
        self.holen(FalschesImap([1, 2]))
        self.assertEqual(self.holen(FalschesImap([7, 8], uidvalidity=6)), [])
        self.assertEqual(json.loads(self.stand.read_text()), {"uidvalidity": 6, "letzte_uid": 8})


if __name__ == "__main__":
    unittest.main()
