import unittest
from datetime import datetime, timedelta, timezone

import termine

SEITE = """<html><head><title>Webinar</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"EventSeries","name":"Reihe","subEvent":[
 {"@type":"Event","name":"BauBuche in der Praxis: Witterungsschutz","description":"Schutz, Planung; Montage",
  "startDate":"2026-11-17T10:00:00+01:00","duration":"PT1H30M",
  "location":{"@type":"VirtualLocation","url":"https://beispiel.de/webinar"}}]}
</script>
<script type="application/ld+json">{kaputt</script>
<script>var x = "kein Text";</script><style>p{}</style>
</head><body><h1>Danke für die Anmeldung</h1><p>Bis bald</p></body></html>"""


class TestVeranstaltungen(unittest.TestCase):
    def test_subevent_mit_dauer(self):
        (v,) = termine.veranstaltungen(SEITE)
        self.assertEqual(v.titel, "BauBuche in der Praxis: Witterungsschutz")
        self.assertEqual(v.beginn, datetime(2026, 11, 17, 9, 0, tzinfo=timezone.utc))
        self.assertEqual(v.ende - v.beginn, timedelta(hours=1, minutes=30))
        self.assertEqual(v.ort, "https://beispiel.de/webinar")

    def test_enddatum_graph_und_doppelte(self):
        e = ('{"@type":"Event","name":"A","startDate":"2026-12-01T18:00:00+01:00",'
             '"endDate":"2026-12-01T20:00:00+01:00","location":"Hörsaal 1"}')
        seite = (f'<script type="application/ld+json">{{"@graph":[{e}]}}</script>'
                 f'<script type="application/ld+json">{e}</script>')
        (v,) = termine.veranstaltungen(seite)
        self.assertEqual((v.ende - v.beginn).seconds, 7200)
        self.assertEqual(v.ort, "Hörsaal 1")

    def test_ohne_zeitzone_oder_ohne_event(self):
        seite = ('<script type="application/ld+json">[{"@type":"Event","name":"A","startDate":"2026-12-01T18:00"},'
                 '{"@type":"Organization","name":"B"}]</script>')
        self.assertEqual(termine.veranstaltungen(seite), [])
        self.assertEqual(termine.veranstaltungen("<p>nichts</p>"), [])

    def test_seitentext_ohne_skripte(self):
        text = termine.seitentext(SEITE)
        self.assertIn("Danke für die Anmeldung", text)
        self.assertNotIn("kein Text", text)
        self.assertNotIn("startDate", text)


class TestHilfen(unittest.TestCase):
    def test_dauer(self):
        self.assertEqual(termine.dauer("PT1H30M"), timedelta(minutes=90))
        self.assertEqual(termine.dauer("P1DT2H"), timedelta(days=1, hours=2))
        self.assertIsNone(termine.dauer("P"))
        self.assertIsNone(termine.dauer(None))

    def test_links(self):
        self.assertEqual(termine.links("Schau (https://a.de/x?y=1). Und http://b.de"),
                         ["https://a.de/x?y=1", "http://b.de"])

    def test_beschreiben_deutsche_zeit(self):
        (v,) = termine.veranstaltungen(SEITE)
        self.assertEqual(termine.beschreiben(v),
                         "BauBuche in der Praxis: Witterungsschutz: Di 17.11.2026 10:00-11:30 Uhr")
        self.assertEqual(termine.dateiname(v), "2026-11-17_BauBuche_in_der_Praxis_Witterungsschutz.ics")


class TestIcs(unittest.TestCase):
    def test_aufbau(self):
        (v,) = termine.veranstaltungen(SEITE)
        text = termine.ics(v, "abc@uni", link="https://beispiel.de/anmeldung",
                           jetzt=datetime(2026, 10, 23, 12, tzinfo=timezone.utc))
        self.assertTrue(text.endswith("\r\n"))
        zeilen = text.split("\r\n")
        self.assertIn("DTSTART:20261117T090000Z", zeilen)
        self.assertIn("DTEND:20261117T103000Z", zeilen)
        self.assertIn("UID:abc@uni", zeilen)
        self.assertIn("URL:https://beispiel.de/anmeldung", zeilen)
        self.assertIn(r"DESCRIPTION:Schutz\, Planung\; Montage\n\nLink: https://beispiel.de/anmeldung",
                      text.replace("\r\n ", ""))

    def test_falten_nach_bytes(self):
        v = termine.Veranstaltung("Ü" * 100, datetime(2026, 1, 1, tzinfo=timezone.utc),
                                  datetime(2026, 1, 1, 1, tzinfo=timezone.utc), "", "")
        for zeile in termine.ics(v, "x").split("\r\n"):
            self.assertLessEqual(len(zeile.encode()), 75)
        self.assertIn("SUMMARY:" + "Ü" * 100, termine.ics(v, "x").replace("\r\n ", ""))
