import imaplib
import json
import tempfile
import unittest
from datetime import date
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
        self.assertEqual(m["an"], [])

    def test_an_aus_to_und_cc(self):
        mail = (b"From: jan@kleinke.org\r\nTo: =?utf-8?q?Frau_M=C3=BCller?= <m@x.de>, b@y.de\r\n"
                b"Cc: c@z.de\r\nSubject: x\r\n\r\nHallo")
        self.assertEqual(imap.zerlege(1, mail)["an"], ["Frau Müller <m@x.de>", "b@y.de", "c@z.de"])

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


class SuchImap(FalschesImap):
    """Wie FalschesImap, aber select kann scheitern und search merkt sich die Kriterien."""

    def __init__(self, uids, ordner_da=True, capabilities=("IMAP4REV1",)):
        super().__init__(uids)
        self.ordner_da, self.capabilities = ordner_da, capabilities

    def select(self, ordner, readonly=False):
        self.aufrufe.append(("select", ordner, readonly))
        return ("OK", [b"3"]) if self.ordner_da else ("NO", [b"Mailbox doesn't exist"])

    def uid(self, befehl, *args):
        if befehl == "search":
            self.aufrufe.append(("search", *args))
        return super().uid(befehl, *args)


class ExchangeImap(SuchImap):
    """Wie der Exchange der HNEE: kein CHARSET UTF-8, jede UID hat ihren eigenen Empfänger."""

    def __init__(self, empfaenger: dict[int, str]):
        super().__init__(list(empfaenger))
        self.empfaenger = empfaenger

    def uid(self, befehl, *args):
        if befehl == "search":
            self.aufrufe.append(("search", *args))
            if args[:1] == ("CHARSET",):
                return "NO", [b"[BADCHARSET (US-ASCII)] The specified charset is not supported."]
            return "OK", [b" ".join(str(u).encode() for u in self.uids)]
        self.aufrufe.append(("fetch", args[0], args[1]))
        if "HEADER.FIELDS" in args[1]:
            antwort = []
            for nr, u in enumerate(args[0].split(","), 1):
                antwort += [(b"%d (UID %s BODY[HEADER.FIELDS (TO CC)] {9}" % (nr, u.encode()),
                             f"To: {self.empfaenger[int(u)]}\r\n\r\n".encode("utf-8")), b")"]
            return "OK", antwort
        roh = f"From: jkl298@hnee.de\r\nTo: {self.empfaenger[int(args[0])]}\r\nSubject: x\r\n\r\nHallo"
        return "OK", [(b"1 (BODY[] {10}", roh.encode()), b")"]


class TestSuchen(unittest.TestCase):
    def suchen(self, falsch, ordner="INBOX", **kw):
        with mock.patch("imaplib.IMAP4_SSL", falsch):
            return imap.suchen("host", 993, "jan", "geheim", ordner, **kw)

    def test_neueste_zuerst_mit_ordner_lesend(self):
        falsch = SuchImap([3, 10, 7])
        mails = self.suchen(falsch, "Sent", an="m@x.de", max_mails=2)
        self.assertEqual([m["uid"] for m in mails], [10, 7])
        self.assertEqual({m["ordner"] for m in mails}, {"Sent"})
        self.assertEqual(mails[0]["betreff"], "Prüfungsanmeldung")
        self.assertIn(("select", '"Sent"', True), falsch.aufrufe)
        self.assertIn(("search", "CHARSET", "UTF-8", b'TO "m@x.de"'), falsch.aufrufe)
        self.assertTrue(all(a[2] == "(BODY.PEEK[])" for a in falsch.aufrufe if a[0] == "fetch"))

    def test_kriterien_und_verknuepft(self):
        self.assertEqual(imap.kriterien(von="Frau  Müller", text='sag "ab"', seit=date(2026, 9, 3)),
                         ['FROM "Frau Müller"'.encode(), b'TEXT "sag \\"ab\\""', b"SINCE 03-Sep-2026"])
        self.assertEqual(imap.kriterien(an="müller", literal_plus=True), [b"TO {7+}\r\nm\xc3\xbcller"])
        self.assertEqual(imap.kriterien(von=" "), [b"ALL"])

    def test_literal_plus_wenn_server_kann(self):
        falsch = SuchImap([1], capabilities=("IMAP4REV1", "LITERAL+"))
        self.suchen(falsch, von="Müller", an="x@y.de")
        self.assertIn(("search", "CHARSET", "UTF-8", b"FROM {7+}\r\nM\xc3\xbcller", b'TO "x@y.de"'), falsch.aufrufe)

    def test_unbekannter_ordner_leer_mit_log(self):
        falsch = SuchImap([1, 2], ordner_da=False)
        with self.assertLogs("agentkit.imap", "WARNING"):
            self.assertEqual(self.suchen(falsch, "Gibtsnicht", text="x"), [])
        self.assertFalse([a for a in falsch.aufrufe if a[0] in ("search", "fetch")])

    def test_keine_treffer(self):
        self.assertEqual(self.suchen(SuchImap([])), [])

    def test_badcharset_ohne_charset_umgeschrieben(self):
        falsch = ExchangeImap({5: "a@hnee.de"})
        self.assertEqual(len(self.suchen(falsch, von="Böhme", text="Straße")), 1)
        self.assertIn(("search", b'FROM "Boehme"', b'TEXT "Strasse"'), falsch.aufrufe)

    def test_badcharset_an_in_python_gefiltert(self):
        falsch = ExchangeImap({3: "=?iso-8859-1?Q?B=F6hme=2C_Thomas?= <thomas.x@hnee.de>", 7: "Jahreis <j@hnee.de>",
                               9: '"Boehme, Thomas" <tb@hnee.de>', 11: "x@hnee.de"})
        mails = self.suchen(falsch, "Gesendete Elemente", an="BÖHME", text="Bachelor", max_mails=5)
        self.assertEqual([m["uid"] for m in mails], [9, 3])
        self.assertIn(("search", b'TEXT "Bachelor"'), falsch.aufrufe)
        self.assertIn(("fetch", "11,9,7,3", "(UID BODY.PEEK[HEADER.FIELDS (TO CC)])"), falsch.aufrufe)
        self.assertEqual(sorted(a[1] for a in falsch.aufrufe if a[0] == "fetch" and a[2] == "(BODY.PEEK[])"),
                         ["3", "9"])
        self.assertEqual([m["uid"] for m in self.suchen(ExchangeImap({3: "boehme@x.de", 9: "Boehme <b@x.de>"}),
                                                        an="boehme", max_mails=1)], [9])

    def test_andere_ablehnung_ist_fehler(self):
        falsch = SuchImap([1])
        falsch.uid = lambda befehl, *args: ("NO", [b"Search failed"])
        with self.assertRaises(imaplib.IMAP4.error):
            self.suchen(falsch, text="x")

    def test_umschreiben(self):
        self.assertEqual(imap.umschreiben("Böhme Ärger Straße Café"), "Boehme Aerger Strasse Cafe")
        self.assertEqual(imap.kriterien(an="Müller", nur_ascii=True), [b'TO "Mueller"'])


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
