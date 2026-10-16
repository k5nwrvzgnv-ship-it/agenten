import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

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
