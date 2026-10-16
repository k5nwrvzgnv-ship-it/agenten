import tempfile
import unittest
from datetime import date
from pathlib import Path

import transkripte

HEUTE = date(2026, 10, 17)
KURSE = ["Bauklimatik", "Holzbau im Bestand", "Holzbaukonstruktion II", "Fertigung im Holzbau 1 (BBHbf01) 26_27"]


class TestKopf(unittest.TestCase):
    def test_kopf(self):
        self.assertEqual(transkripte.kopf_lesen("Transkript Bauklimatik 14.10.\nHallo", HEUTE),
                         ("Bauklimatik", date(2026, 10, 14), "Hallo"))
        self.assertEqual(transkripte.kopf_lesen("transkript: Holzbau im Bestand 2.9.25", HEUTE)[:2],
                         ("Holzbau im Bestand", date(2025, 9, 2)))
        self.assertEqual(transkripte.kopf_lesen("Transkript Bauklimatik", HEUTE)[1], HEUTE)
        text = "Transkript Bauklimatik\n\nAngehängte Dateien von Jan (im Agent-Ordner):\n- data/eingang/x/a.txt"
        self.assertEqual(transkripte.kopf_lesen(text, HEUTE), ("Bauklimatik", HEUTE, ""))
        with self.assertRaises(transkripte.TranskriptFehler):
            transkripte.kopf_lesen("Transkript Bauklimatik 31.02.", HEUTE)

    def test_ist_transkript(self):
        self.assertTrue(transkripte.ist_transkript("  Transkript Bauklimatik"))
        self.assertFalse(transkripte.ist_transkript("Was steht im Transkript?"))

    def test_kurs_finden(self):
        self.assertEqual(transkripte.kurs_finden("bauklimatik", KURSE), ["Bauklimatik"])
        self.assertEqual(transkripte.kurs_finden("Holzbau", KURSE), KURSE[1:])
        self.assertEqual(transkripte.kurs_finden("holzbau bestand", KURSE), ["Holzbau im Bestand"])
        self.assertEqual(transkripte.kurs_finden("Fertigung Holzbau", KURSE), [KURSE[3]])
        self.assertEqual(transkripte.kurs_finden("", KURSE), [])


class TestAblegen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = Path(self.tmp.name)
        self.ziel = self.agent / "data" / "kurse"
        for k in KURSE:
            (self.ziel / k).mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_text_in_nachricht(self):
        a = {"text": "Transkript Bauklimatik 14.10.\nHeute: U-Wert. Klausur am 3.2.", "dateien": []}
        kurs, pfade = transkripte.ablegen(a, self.agent, self.ziel, HEUTE)
        self.assertEqual(kurs, "Bauklimatik")
        self.assertEqual(pfade, [self.ziel / "Bauklimatik/transkripte/2026-10-14_transkript.txt"])
        self.assertIn("Klausur am 3.2.", pfade[0].read_text())
        # zweimal derselbe Auftrag (nach Wartepause): keine Kopie
        self.assertEqual(transkripte.ablegen(a, self.agent, self.ziel, HEUTE)[1], pfade)
        # anderer Inhalt am selben Tag: eigene Datei
        a2 = {"text": "Transkript Bauklimatik 14.10.\nZweite Vorlesung", "dateien": []}
        self.assertEqual(transkripte.ablegen(a2, self.agent, self.ziel, HEUTE)[1][0].name, "2026-10-14_transkript-2.txt")

    def test_datei(self):
        (self.agent / "data/eingang/x").mkdir(parents=True)
        (self.agent / "data/eingang/x/v.txt").write_text("Text aus Datei")
        a = {"text": "Transkript holzbau bestand\n\nAngehängte Dateien von Jan (im Agent-Ordner):\n- data/eingang/x/v.txt",
             "dateien": ["data/eingang/x/v.txt"]}
        kurs, pfade = transkripte.ablegen(a, self.agent, self.ziel, HEUTE)
        self.assertEqual(kurs, "Holzbau im Bestand")
        self.assertIn("Text aus Datei", pfade[0].read_text())

    def test_fehler(self):
        with self.assertRaisesRegex(transkripte.TranskriptFehler, "nicht eindeutig"):
            transkripte.ablegen({"text": "Transkript Holzbau\nx", "dateien": []}, self.agent, self.ziel, HEUTE)
        with self.assertRaisesRegex(transkripte.TranskriptFehler, "nicht gefunden"):
            transkripte.ablegen({"text": "Transkript Mathe\nx", "dateien": []}, self.agent, self.ziel, HEUTE)
        with self.assertRaisesRegex(transkripte.TranskriptFehler, "Kein Transkript-Text"):
            transkripte.ablegen({"text": "Transkript Bauklimatik", "dateien": []}, self.agent, self.ziel, HEUTE)
