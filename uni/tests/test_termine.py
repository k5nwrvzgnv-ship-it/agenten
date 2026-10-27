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


class TestEntwurfPruefen(unittest.TestCase):
    JETZT = datetime(2026, 10, 27, 11, 0, tzinfo=termine.ZONE)

    def pruefen(self, **felder):
        return termine.entwurf_pruefen(felder, self.JETZT)

    def test_ohne_zone_deutsche_zeit_und_ohne_ende(self):
        v, warum = self.pruefen(titel="Exkursion", beginn="2026-10-27T14:00", ort="Berlin", quelle="Mail Lautner",
                                begruendung="Pflichttermin")
        self.assertEqual(v.beginn, datetime(2026, 10, 27, 13, 0, tzinfo=timezone.utc))
        self.assertEqual(v.ende - v.beginn, timedelta(hours=1))
        self.assertEqual(v.erinnerungen, (1440, 120))
        self.assertEqual(v.beschreibung, "Ende unbekannt, 1 Stunde eingetragen.\n\nQuelle: Mail Lautner")
        self.assertEqual(warum, "Pflichttermin")

    def test_ganztags(self):
        v, _ = self.pruefen(titel="Anmeldeschluss KI-Ethik", beginn="2026-11-04")
        self.assertTrue(v.ganztags)
        self.assertEqual(v.erinnerungen, (900,))
        self.assertEqual(termine.beschreiben(v), "Anmeldeschluss KI-Ethik: Mi 04.11.2026 (ganztägig)")
        text = termine.ics(v, "x")
        self.assertIn("DTSTART;VALUE=DATE:20261104\r\n", text)
        self.assertIn("DTEND;VALUE=DATE:20261105\r\n", text)
        v, _ = self.pruefen(titel="Tagung", beginn="2026-11-04", ende="2026-11-06", erinnerungen_min=[])
        self.assertIn("bis Fr 06.11.2026", termine.beschreiben(v))
        self.assertNotIn("VALARM", termine.ics(v, "x"))

    def test_fehler(self):
        for felder, meldung in [
            ({"beginn": "2026-11-01T10:00"}, "titel fehlt"),
            ({"titel": "A"}, "beginn fehlt"),
            ({"titel": "A", "beginn": "morgen"}, "kein Datum"),
            ({"titel": "A", "beginn": "2026-10-26T10:00"}, "Vergangenheit"),
            ({"titel": "A", "beginn": "2026-11-01T10:00", "ende": "2026-11-01T09:00"}, "nach beginn"),
            ({"titel": "A", "beginn": "2026-11-01T10:00", "ende": "2026-11-03T10:00"}, "24 Stunden"),
            ({"titel": "A", "beginn": "2026-11-01", "ende": "2026-11-01T12:00"}, "beide"),
            ({"titel": "A", "beginn": "2026-11-01T10:00", "erinnerungen_min": [1, 2, 3, 4]}, "höchstens 3"),
            ({"titel": "A", "beginn": "2026-11-01T10:00", "erinnerungen_min": ["1 Tag"]}, "ganzen Zahlen"),
            ({"titel": "A", "beginn": "2026-11-01T10:00", "erinnerungen_min": [-5]}, "0 bis"),
        ]:
            with self.subTest(felder=felder), self.assertRaisesRegex(termine.TerminFehler, meldung):
                termine.entwurf_pruefen(felder, self.JETZT)

    def test_heute_ganztags_gilt_noch(self):
        v, _ = self.pruefen(titel="A", beginn="2026-10-27")
        self.assertTrue(v.ganztags)

    def test_erinnerung_text(self):
        self.assertEqual(termine.erinnerung_text((1440, 120)), "Erinnerung 1 Tag und 2 Std. vorher")
        self.assertEqual(termine.erinnerung_text((2880, 1440, 30)), "Erinnerung 2 Tage, 1 Tag und 30 Min. vorher")
        self.assertEqual(termine.erinnerung_text(()), "ohne Erinnerung")
        self.assertEqual(termine.erinnerung_text((0,)), "Erinnerung zu Beginn")

    def test_valarm_und_uid(self):
        v, _ = self.pruefen(titel="A", beginn="2026-11-01T10:00", erinnerungen_min=[120, 1440, 120])
        self.assertEqual(v.erinnerungen, (1440, 120))
        text = termine.ics(v, termine.uid(v))
        self.assertEqual(text.count("BEGIN:VALARM"), 2)
        self.assertIn("TRIGGER:-PT1440M", text)
        self.assertEqual(termine.uid(v), termine.uid(self.pruefen(titel="A", beginn="2026-11-01T10:00")[0]))


class TestDoppelt(unittest.TestCase):
    def test_abgleich(self):
        from types import SimpleNamespace as T
        z = termine.ZONE
        v = termine.Veranstaltung("Exkursion Homag (CAM)", datetime(2026, 11, 5, 8, 45, tzinfo=z),
                                  datetime(2026, 11, 5, 14, tzinfo=z), "", "")
        self.assertTrue(termine.doppelt(v, [T(titel="exkursion homag", beginn=datetime(2026, 11, 5, 9, 0, tzinfo=z),
                                              ganztags=False)]))
        self.assertFalse(termine.doppelt(v, [T(titel="Exkursion Homag", beginn=datetime(2026, 11, 5, 10, tzinfo=z),
                                               ganztags=False)]))
        self.assertFalse(termine.doppelt(v, [T(titel="CAM Vorlesung", beginn=datetime(2026, 11, 5, 8, 45, tzinfo=z),
                                               ganztags=False)]))
