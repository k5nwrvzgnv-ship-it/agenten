"""Tests der Entwurfsanzeige (Zentrale und Gruppen-Bot zeigen Entwürfe damit)."""

import re
import unittest

from agentkit import entwurfsanzeige as ea


class TestEntwurfsanzeige(unittest.TestCase):
    def test_entwurf_zeigt_alles(self):
        e = {"agent": "posteingang", "typ": "mail", "titel": "Antwort", "inhalt": "x", "vorgaenger": None,
             "daten": {"an": ["prof@example.org"], "betreff": "Termin", "text": "Hallo " * 2000}}
        text = "".join(ea.entwurf_als_text(e))
        self.assertEqual(text.count("prof@example.org"), 1)
        self.assertEqual(text.count("Hallo"), 2000)
        self.assertTrue(text.startswith("<b>Posteingang</b> · Mail-Entwurf\n<b>An prof@example.org</b>\nTermin\n"))
        self.assertGreater(len(ea.entwurf_als_text(e)[0]), 1000)  # Kopf nicht allein in der ersten Nachricht
        kauf = ea.entwurf_als_text({"agent": "einkauf", "typ": "kauf", "titel": "Kabel <USB>", "inhalt": "x",
                                 "daten": {"preis": 12.5, "menge": [1, 2]}, "vorgaenger": "alt"})
        self.assertIn("Kauf-Entwurf, überarbeitet\n<b>Kabel &lt;USB&gt;</b>\nPreis: 12.5\nMenge: 1, 2\n\n"
                      "<blockquote>x</blockquote>", kauf[0])

    def test_entwurf_mail_aus_daten(self):
        text = "Sehr geehrter Herr Böhme,\n\nvielen Dank & bis bald.\n\nMit besten Grüßen\nJan"
        e = {"agent": "uni", "typ": "mail", "titel": "Mail: AW: Betreuung", "vorgaenger": None, "inhalt": "egal",
             "daten": {"an": ["boehme@example.org"], "cc": ["a@example.org"], "betreff": "AW: Betreuung",
                       "text": text, "begruendung": "Er hat zugesagt. Bitte prüfe, ob Freitag passt.",
                       "in_reply_to": "<x@example.org>", "antwort_auf_uid": 7, "bcc": [], "anhang": "plan.pdf",
                       "antwort_auf": "\"Böhme, Klaus\" <boehme@example.org>: AW: AW: Betreuung"}}
        (n,) = ea.entwurf_als_text(e)
        self.assertEqual(n.count("vielen Dank &amp; bis bald"), 1)
        self.assertIn("<b>An Klaus Böhme</b> (boehme@example.org)\nAW: Betreuung\n"
                      "<i>Antwort auf die Mail</i>\nCc: a@example.org\nAnhang: plan.pdf\n\n<blockquote>Sehr", n)
        self.assertTrue(n.endswith("</blockquote>\n\n<b>Bitte prüfen:</b> ob Freitag passt."))
        for weg in ("Details", "zugesagt", "x@example.org", "expandable"):
            self.assertNotIn(weg, n)
        termin = ea.entwurf_als_text({"agent": "uni", "typ": "termin", "titel": "T", "inhalt": "x", "vorgaenger": None,
                                   "daten": {"titel": "x"}})
        self.assertIn("Termin-Entwurf", termin[0])
        self.assertNotIn("Titel:", termin[0])

    def test_betreff_und_bezug(self):
        self.assertEqual(ea.betreff_kurz("AW: AW: Re: AW:Anfrage"), "Re: Anfrage")
        self.assertEqual(ea.betreff_kurz("WG: AW: Plan"), "Fwd: Plan")
        self.assertEqual(ea.betreff_kurz("Plan"), "Plan")
        self.assertEqual(ea.name_aus('"Oppermann, J." <j@x.de>'), ("J. Oppermann", "j@x.de"))
        self.assertEqual(ea.name_aus("j@x.de"), ("j@x.de", "j@x.de"))
        daten = {"an": ["a@x.de"], "betreff": "Re: Neu", "antwort_auf_von": "Frau B <b@x.de>",
                 "antwort_auf_datum": "2026-08-11T10:00:00+02:00", "antwort_auf": "Frau B <b@x.de>: AW: AW: Alt"}
        self.assertEqual(ea.bezug_text(daten), "Antwort auf die Mail von Frau B vom 11.08.2026: „Re: Alt“")
        self.assertEqual(ea.bezug_text({"an": ["a@x.de"], "in_reply_to": "<y>"}), "Antwort auf eine frühere Mail")
        self.assertEqual(ea.bezug_text({"an": ["a@x.de"]}), "")

    def test_warum_und_frage(self):
        self.assertEqual(ea.warum_und_frage({"begruendung": "A. Bitte prüfe, ob x stimmt. B."}),
                         ("A. B.", "ob x stimmt."))
        self.assertEqual(ea.warum_und_frage({"begruendung": "A.", "pruefen": "ob x stimmt"}), ("A.", "ob x stimmt"))
        self.assertEqual(ea.warum_und_frage({}), ("", ""))

    def test_html_aufteilen_schneidet_keine_tags(self):
        html = "<b>Kopf</b>\n\n<blockquote>" + "\n".join(f"Zeile {i} &amp; " + "x" * 50 for i in range(300)) \
            + "</blockquote>\n\n<blockquote expandable><b>Warum so</b>\n" + "y" * 2500 + "</blockquote>"
        stuecke = ea.html_aufteilen(html, 1000)
        self.assertGreater(len(stuecke), 10)
        for s in stuecke:
            self.assertLessEqual(len(s), 1000)
            self.assertEqual(s.count("<blockquote"), s.count("</blockquote>"), s[:80])
            self.assertEqual(s.count("<b>"), s.count("</b>"))
            self.assertNotRegex(s, r"&[a-z]*$|<[^>]*$")
        self.assertTrue(stuecke[1].startswith("<blockquote>Zeile"))
        self.assertTrue(stuecke[-1].startswith("<blockquote expandable>"))
        ohne = re.compile(r"<[^>]+>|\s")
        self.assertEqual(ohne.sub("", "".join(stuecke)), ohne.sub("", html))
        self.assertEqual(ea.html_aufteilen("<b>kurz</b>"), ["<b>kurz</b>"])


if __name__ == "__main__":
    unittest.main()
