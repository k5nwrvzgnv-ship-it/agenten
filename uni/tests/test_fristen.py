import unittest
from datetime import datetime

import fristen


def ts(text: str) -> int:
    return int(datetime.strptime(text, "%d.%m.%Y %H:%M").timestamp())


def frist(faellig, letzte=0, erledigt=False, fid="assign-1"):
    return {"id": fid, "art": "Aufgabe", "kurs": "K", "name": "N", "faellig": faellig,
            "letzte_abgabe": letzte, "erledigt": erledigt, "url": "u"}


class TestFristen(unittest.TestCase):
    def test_zu_frueh_keine_erinnerung(self):
        self.assertEqual(fristen.faellige_erinnerungen([frist(ts("30.10.2026 23:59"))], set(), ts("16.10.2026 12:00")), [])

    def test_sieben_tage(self):
        e = fristen.faellige_erinnerungen([frist(ts("23.10.2026 23:59"))], set(), ts("16.10.2026 08:00"))
        self.assertEqual(len(e), 1)
        self.assertTrue(e[0][0].endswith(":7"))
        self.assertEqual(e[0][2], 7)

    def test_keine_doppelte_erinnerung(self):
        f = [frist(ts("23.10.2026 23:59"))]
        jetzt = ts("16.10.2026 08:00")
        schluessel = fristen.faellige_erinnerungen(f, set(), jetzt)[0][0]
        self.assertEqual(fristen.faellige_erinnerungen(f, {schluessel}, jetzt + 3600), [])

    def test_stufen_nacheinander(self):
        f = [frist(ts("23.10.2026 23:59"))]
        erinnert = set()
        stufen = []
        for tag in range(16, 24):
            for s, *_ in fristen.faellige_erinnerungen(f, erinnert, ts(f"{tag}.10.2026 08:00")):
                erinnert.add(s)
                stufen.append(s.rsplit(":", 1)[1])
        self.assertEqual(stufen, ["7", "2", "0"])

    def test_verpasste_stufe_nur_juengste(self):
        e = fristen.faellige_erinnerungen([frist(ts("17.10.2026 12:00"))], set(), ts("16.10.2026 08:00"))
        self.assertEqual([x[0].rsplit(":", 1)[1] for x in e], ["2"])

    def test_erledigt_wird_uebergangen(self):
        self.assertEqual(fristen.faellige_erinnerungen([frist(ts("17.10.2026 12:00"), erledigt=True)], set(),
                                                       ts("16.10.2026 08:00")), [])

    def test_nachfrist(self):
        # Fall vom 16.10.2026: fällig 00:00 vorbei, letzte Abgabe am 17.10. 12:49
        f = [frist(ts("16.10.2026 00:00"), letzte=ts("17.10.2026 12:49"))]
        e = fristen.faellige_erinnerungen(f, set(), ts("16.10.2026 11:45"))
        self.assertEqual(len(e), 1)
        self.assertTrue(e[0][3])
        self.assertEqual(e[0][2], 1)
        self.assertIn("Nachfrist endet morgen", fristen.als_text(f[0], 1, True, ts("17.10.2026 12:49")))

    def test_alles_vorbei(self):
        f = [frist(ts("15.10.2026 00:00"), letzte=ts("16.10.2026 00:00"))]
        self.assertEqual(fristen.faellige_erinnerungen(f, set(), ts("16.10.2026 11:00")), [])

    def test_termin_verschoben_neu_erinnern(self):
        alt = frist(ts("18.10.2026 12:00"))
        jetzt = ts("16.10.2026 08:00")
        erinnert = {fristen.faellige_erinnerungen([alt], set(), jetzt)[0][0]}
        neu = frist(ts("17.10.2026 12:00"))
        self.assertEqual(len(fristen.faellige_erinnerungen([neu], erinnert, jetzt)), 1)


if __name__ == "__main__":
    unittest.main()
