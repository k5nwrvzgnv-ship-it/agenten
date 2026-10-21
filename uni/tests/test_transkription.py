import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

import kurse
import transkription


class TestTranskription(unittest.TestCase):
    def test_offene(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp)
            (ziel / "K" / "A").mkdir(parents=True)
            alt, neu, fertig = ziel / "K/A/alt.mp4", ziel / "K/A/neu.MP3", ziel / "K/fertig.mp4"
            for p in (alt, neu, fertig, ziel / "K/folie.pdf", ziel / "K/A/.halb.mp4.tmp", ziel / "K/.versteckt.mp4"):
                p.write_bytes(b"x")
            (ziel / "K/fertig.mp4.txt").write_text("t")
            os.utime(alt, (1, 1))
            self.assertEqual(transkription.offene(ziel), [alt, neu])

    def test_passt_noch(self):
        nacht = datetime(2026, 10, 17, 1, 0)
        self.assertTrue(transkription.passt_noch(90 * 60, nacht))            # 3 h Rechnen, bis 4 Uhr
        self.assertFalse(transkription.passt_noch(4 * 3600, nacht))          # 8 h, über 7 Uhr hinaus
        self.assertFalse(transkription.passt_noch(60, datetime(2026, 10, 17, 7, 30)))
        self.assertFalse(transkription.passt_noch(60, datetime(2026, 10, 17, 13, 0)))

    def test_zeitmarke(self):
        self.assertEqual(transkription.zeitmarke(5.9), "[00:05]")
        self.assertEqual(transkription.zeitmarke(754), "[12:34]")
        self.assertEqual(transkription.zeitmarke(3725), "[1:02:05]")

    def test_grenzen(self):
        self.assertEqual(kurse.grenze_mb("Vorlesung.MP4"), kurse.MEDIEN_MAX_MB)
        self.assertEqual(kurse.grenze_mb("a.zip"), kurse.ZIP_MAX_MB)
        self.assertEqual(kurse.grenze_mb("a.pdf"), kurse.MAX_MB)


class TestStuecke(unittest.TestCase):
    # Kleine Zahlen statt 16 kHz und 10 min: rate 100, Stück 10 s, Suche ±2 s, Fenster 0,2 s
    ARGS = {"rate": 100, "stueck_s": 10, "suche_s": 2, "fenster_s": 0.2}

    def test_kurz_ein_stueck(self):
        self.assertEqual(transkription.schnitte(np.ones(1100), **self.ARGS), [0, 1100])
        self.assertEqual(transkription.schnitte(np.ones(0), **self.ARGS), [0, 0])

    def test_schnitt_in_der_stille(self):
        ton = np.ones(3500)
        ton[1080:1100] = 0  # Stille 0,8 s nach der Grenze bei 10 s
        grenzen = transkription.schnitte(ton, **self.ARGS)
        self.assertEqual(grenzen[0], 0)
        self.assertEqual(grenzen[-1], 3500)
        self.assertTrue(1080 <= grenzen[1] < 1100, grenzen)

    def test_grenzen_im_suchbereich(self):
        ton = np.random.default_rng(1).normal(size=10_000)
        grenzen = transkription.schnitte(ton, **self.ARGS)
        for alt, neu in zip(grenzen[:-2], grenzen[1:-1], strict=True):
            self.assertTrue(800 <= neu - alt <= 1200, grenzen)
        self.assertLessEqual(grenzen[-1] - grenzen[-2], 1000 + 200)

    def test_zeitmarken_mit_versatz(self):
        class Modell:
            def __init__(self):
                self.laengen = []

            def transcribe(self, ton, **_):
                self.laengen.append(len(ton))
                return [SimpleNamespace(start=1.0, text=" Hallo ")], None

        modell = Modell()
        ton = np.ones(transkription.RATE * 25 * 60, dtype=np.float32)  # 25 min: drei Stücke
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "v.mp4"
            transkription.transkribieren(pfad, modell, lesen=lambda p: ton)
            zeilen = (Path(tmp) / "v.mp4.txt").read_text(encoding="utf-8").splitlines()[2:]
        self.assertEqual(len(modell.laengen), 3)
        self.assertEqual(sum(modell.laengen), len(ton))
        self.assertTrue(max(modell.laengen) <= transkription.RATE * (transkription.STUECK_S + transkription.SUCHE_S))
        self.assertEqual(zeilen[0], "[00:01] Hallo")
        self.assertTrue(zeilen[1].startswith("[09:") or zeilen[1].startswith("[10:"), zeilen)


class TestVersuche(unittest.TestCase):
    def test_zaehlen_und_vergessen(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "data" / "v.json"
            self.assertEqual(transkription.versuche(datei, "K/a.mp4"), 0)
            transkription.versuch_merken(datei, "K/a.mp4")
            transkription.versuch_merken(datei, "K/a.mp4")
            transkription.versuch_merken(datei, "K/b.mp4")
            self.assertEqual(transkription.versuche(datei, "K/a.mp4"), 2)
            transkription.versuch_vergessen(datei, "K/a.mp4")
            self.assertEqual(transkription.versuche(datei, "K/a.mp4"), 0)
            self.assertEqual(transkription.versuche(datei, "K/b.mp4"), 1)
            transkription.versuch_vergessen(datei, "K/nie.mp4")  # kein Fehler

    def test_lauf_gibt_nach_abbruechen_auf(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "kurse"
            (ziel / "K").mkdir(parents=True)
            video = ziel / "K" / "a.mp4"
            video.write_bytes(b"x")
            datei = Path(tmp) / "v.json"
            for _ in range(transkription.MAX_VERSUCHE):
                transkription.versuch_merken(datei, "K/a.mp4")
            with mock.patch.multiple(transkription, ZIEL=ziel, VERSUCHE_DATEI=datei), \
                    mock.patch.object(transkription.meldungen, "melden") as melden, \
                    mock.patch.object(transkription, "logger"), \
                    mock.patch("faster_whisper.WhisperModel"), \
                    mock.patch.object(transkription, "transkribieren") as rechnen:
                transkription.lauf()
            rechnen.assert_not_called()
            melden.assert_called_once()
            self.assertIn("fehlgeschlagen", (ziel / "K" / "a.mp4.txt").read_text(encoding="utf-8"))
            self.assertEqual(transkription.versuche(datei, "K/a.mp4"), 0)
