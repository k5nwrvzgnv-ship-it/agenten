import unittest

import postfach

MAIL = (b"From: =?utf-8?q?Pr=C3=BCfungsamt?= <pa@hnee.de>\r\n"
        b"Subject: =?utf-8?q?Pr=C3=BCfungsanmeldung?=\r\n"
        b"Date: Fri, 16 Oct 2026 09:00:00 +0200\r\n"
        b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=X\r\n\r\n"
        b"--X\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
        b"<p>Anmeldung bis <b>30.10.</b></p><style>p{}</style>\r\n"
        b"--X\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename=liste.pdf\r\n\r\n"
        b"JVBERi0=\r\n--X--\r\n")


class TestPostfach(unittest.TestCase):
    def test_zerlege(self):
        m = postfach.zerlege(7, MAIL)
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
        self.assertEqual(postfach.wortlaut(roh), "Sehr geehrter Herr Kleinke,\n\nich übernehme die Betreuung.\n\n"
                                                 "Grüße\nT. Böhme\n\n[älterer Verlauf weggelassen]")
        self.assertEqual(postfach.wortlaut("Ja.\nAm 26.10.2026 um 10:00 schrieb Jan Kleinke:\n> Frage"),
                         "Ja.\n\n[älterer Verlauf weggelassen]")
        outlook = "BG, TB.\n\nVon: Kleinke, Jan <j@hnee.de>\n\nGesendet: Mittwoch, 21. Oktober 2026 12:57\n\nAn: B"
        self.assertEqual(postfach.wortlaut(outlook), "BG, TB.\n\n[älterer Verlauf weggelassen]")

    def test_html_umbrueche(self):
        mail = (b"From: a@hnee.de\r\nSubject: x\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
                b"<p>Hallo,</p><p>Zeile 1<br>Zeile 2</p>")
        self.assertEqual(postfach.zerlege(1, mail)["wortlaut"], "Hallo,\nZeile 1\nZeile 2")


if __name__ == "__main__":
    unittest.main()
