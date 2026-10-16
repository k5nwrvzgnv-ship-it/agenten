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


if __name__ == "__main__":
    unittest.main()
