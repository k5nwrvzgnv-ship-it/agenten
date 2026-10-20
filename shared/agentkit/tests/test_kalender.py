import unittest
from datetime import datetime
from unittest import mock

from agentkit import kalender
from agentkit.kalender import ZONE, aus_text


def ics(*ereignisse: str) -> str:
    teile = ["BEGIN:VCALENDAR", "VERSION:2.0",
             # Zeitzonen-Block mit eigener RRULE: darf nicht als Termin zählen
             "BEGIN:VTIMEZONE", "TZID:Europe/Berlin", "BEGIN:DAYLIGHT", "DTSTART:19810329T020000",
             "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT", "END:VTIMEZONE"]
    for e in ereignisse:
        teile += ["BEGIN:VEVENT", *e.strip().splitlines(), "END:VEVENT"]
    return "\r\n".join(teile + ["END:VCALENDAR"]) + "\r\n"


def z(*teile) -> datetime:
    return datetime(*teile, tzinfo=ZONE)


OKTOBER = (z(2026, 10, 1), z(2026, 11, 1))


class TestEinzeltermine(unittest.TestCase):
    def test_vorlesung_mit_ort_und_faltung(self):
        text = ics("UID:a\nDTSTART;TZID=Europe/Berlin:20261020T091500\nDTEND;TZID=Europe/Berlin:20261020T104500\n"
                   "SUMMARY:Holzschutz\\, Teil 1\nLOCATION:Haus 2\n  Raum 105")
        (t,) = aus_text(text, *OKTOBER)
        self.assertEqual((t.beginn, t.ende), (z(2026, 10, 20, 9, 15), z(2026, 10, 20, 10, 45)))
        self.assertEqual((t.titel, t.ort, t.ganztags), ("Holzschutz, Teil 1", "Haus 2 Raum 105", False))

    def test_utc_und_andere_zone(self):
        text = ics("UID:u\nDTSTART:20261020T080000Z\nDURATION:PT1H30M\nSUMMARY:UTC",
                   "UID:p\nDTSTART;TZID=Europe/Paris:20261021T100000\nDTEND;TZID=Europe/Paris:20261021T110000\n"
                   "SUMMARY:Paris")
        utc, paris = aus_text(text, *OKTOBER)
        self.assertEqual((utc.beginn, utc.ende), (z(2026, 10, 20, 10), z(2026, 10, 20, 11, 30)))
        self.assertEqual(paris.beginn, z(2026, 10, 21, 10))
        self.assertEqual(utc.beginn.tzinfo, ZONE)

    def test_ganztags_und_ohne_zone(self):
        text = ics("UID:g\nDTSTART;VALUE=DATE:20261024\nDTEND;VALUE=DATE:20261026\nSUMMARY:Exkursion",
                   "UID:f\nDTSTART:20261022T140000\nSUMMARY:Ohne Zone")
        exkursion, ohne = sorted(aus_text(text, *OKTOBER), key=lambda t: t.titel)
        # 26.10. ist nach der Zeitumstellung: Ende trotzdem 0 Uhr
        self.assertEqual((exkursion.beginn, exkursion.ende, exkursion.ganztags),
                         (z(2026, 10, 24), z(2026, 10, 26), True))
        self.assertEqual((ohne.beginn, ohne.ende), (z(2026, 10, 22, 14), z(2026, 10, 22, 14)))

    def test_zeitraum_und_abgesagt(self):
        text = ics("UID:a\nDTSTART:20260930T230000\nDTEND:20261001T010000\nSUMMARY:ragt hinein",
                   "UID:b\nDTSTART:20261101T000000\nDTEND:20261101T010000\nSUMMARY:danach",
                   "UID:c\nDTSTART:20261005T100000\nSTATUS:CANCELLED\nSUMMARY:abgesagt",
                   "UID:d\nSUMMARY:kaputt")
        with self.assertLogs("agentkit.kalender", "WARNING"):
            self.assertEqual([t.titel for t in aus_text(text, *OKTOBER)], ["ragt hinein"])

    def test_alarm_im_termin_stoert_nicht(self):
        text = ics("UID:a\nDTSTART:20261005T100000\nSUMMARY:mit Alarm\nBEGIN:VALARM\nTRIGGER:-PT15M\n"
                   "DESCRIPTION:Alarm\nEND:VALARM")
        (t,) = aus_text(text, *OKTOBER)
        self.assertEqual(t.titel, "mit Alarm")


class TestWiederholungen(unittest.TestCase):
    def test_woechentlich_ueber_zeitumstellung_mit_until(self):
        text = ics("UID:w\nDTSTART;TZID=Europe/Berlin:20261013T091500\nDTEND;TZID=Europe/Berlin:20261013T104500\n"
                   "RRULE:FREQ=WEEKLY;UNTIL=20261103T081500Z\nSUMMARY:SHB")
        beginne = [t.beginn for t in aus_text(text, z(2026, 10, 1), z(2027, 1, 1))]
        self.assertEqual(beginne, [z(2026, 10, d, 9, 15) for d in (13, 20, 27)] + [z(2026, 11, 3, 9, 15)])

    def test_woechentlich_mehrere_tage_count_exdate(self):
        text = ics("UID:w\nDTSTART:20261005T080000\nRRULE:FREQ=WEEKLY;BYDAY=MO,WE;COUNT=4\n"
                   "EXDATE:20261007T080000\nSUMMARY:x")
        tage = [t.beginn.day for t in aus_text(text, *OKTOBER)]
        self.assertEqual(tage, [5, 12, 14])

    def test_taeglich_mit_intervall_und_zeitraum(self):
        text = ics("UID:t\nDTSTART:20260901T070000\nRRULE:FREQ=DAILY;INTERVAL=10\nSUMMARY:x")
        self.assertEqual([t.beginn.day for t in aus_text(text, *OKTOBER)], [1, 11, 21, 31])

    def test_monatlich_und_jaehrlich(self):
        text = ics("UID:m\nDTSTART;VALUE=DATE:20260131\nRRULE:FREQ=MONTHLY;COUNT=3\nSUMMARY:m",
                   "UID:j\nDTSTART;VALUE=DATE:20241020\nRRULE:FREQ=YEARLY\nSUMMARY:Geburtstag")
        monatlich = [t.beginn.date().isoformat() for t in aus_text(text, z(2026, 1, 1), z(2027, 1, 1))
                     if t.titel == "m"]
        self.assertEqual(monatlich, ["2026-01-31", "2026-03-31", "2026-05-31"])  # Februar/April ohne 31.
        (g,) = [t for t in aus_text(text, *OKTOBER) if t.titel == "Geburtstag"]
        self.assertEqual(g.beginn, z(2026, 10, 20))

    def test_einzeln_geaendert(self):
        text = ics("UID:w\nDTSTART:20261006T100000\nRRULE:FREQ=WEEKLY;COUNT=3\nSUMMARY:Vorlesung",
                   "UID:w\nRECURRENCE-ID:20261013T100000\nDTSTART:20261014T120000\nSUMMARY:Vorlesung verlegt")
        self.assertEqual([(t.beginn, t.titel) for t in aus_text(text, *OKTOBER)],
                         [(z(2026, 10, 6, 10), "Vorlesung"), (z(2026, 10, 14, 12), "Vorlesung verlegt"),
                          (z(2026, 10, 20, 10), "Vorlesung")])

    def test_unbekannte_regel_nur_erster_termin(self):
        text = ics("UID:x\nDTSTART:20261005T100000\nRRULE:FREQ=MONTHLY;BYDAY=1MO\nSUMMARY:x")
        with self.assertLogs("agentkit.kalender", "WARNING"):
            self.assertEqual(len(aus_text(text, z(2026, 10, 1), z(2027, 1, 1))), 1)


class TestLaden(unittest.TestCase):
    def test_fehler_ohne_adresse(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("kaputt")):
            with self.assertRaises(kalender.KalenderFehler) as f:
                kalender.termine(*OKTOBER, urls=["webcal://geheim.example/abc"])
        self.assertNotIn("geheim", str(f.exception))
        self.assertIn("Kalender 1", str(f.exception))

    def test_leer(self):
        with self.assertRaises(kalender.KalenderFehler):
            kalender.termine(*OKTOBER, urls=[])


if __name__ == "__main__":
    unittest.main()
