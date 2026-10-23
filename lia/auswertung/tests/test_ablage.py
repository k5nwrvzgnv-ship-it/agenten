import stat
import tempfile
import unittest
from pathlib import Path

import ablage


def rechte(pfad: Path) -> int:
    return stat.S_IMODE(pfad.stat().st_mode)


class Datenordner(unittest.TestCase):
    def test_legt_ordner_mit_700_an(self):
        with tempfile.TemporaryDirectory() as t:
            pfad = ablage.datenordner(Path(t) / "data" / "export")
            self.assertTrue(pfad.is_dir())
            self.assertEqual(rechte(pfad), 0o700)

    def test_vorhandener_ordner_wird_verschaerft(self):
        with tempfile.TemporaryDirectory() as t:
            pfad = Path(t) / "data"
            pfad.mkdir(mode=0o755)
            ablage.datenordner(pfad)
            self.assertEqual(rechte(pfad), 0o700)


class Schreiben(unittest.TestCase):
    def test_datei_mit_600(self):
        with tempfile.TemporaryDirectory() as t:
            ordner = ablage.datenordner(Path(t) / "data")
            datei = ordner / "a.json"
            ablage.schreiben(datei, "{}")
            self.assertEqual(datei.read_text(encoding="utf-8"), "{}")
            self.assertEqual(rechte(datei), 0o600)
            self.assertFalse((ordner / "a.json.tmp").exists())

    def test_ueberschreibt(self):
        with tempfile.TemporaryDirectory() as t:
            datei = ablage.datenordner(Path(t) / "data") / "a.txt"
            ablage.schreiben(datei, "alt")
            ablage.schreiben(datei, "neu")
            self.assertEqual(datei.read_text(encoding="utf-8"), "neu")

    def test_ungeschuetzter_ordner_wird_abgelehnt(self):
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t) / "offen"
            ordner.mkdir()
            ordner.chmod(0o755)
            with self.assertRaises(ablage.AblageFehler):
                ablage.schreiben(ordner / "a.txt", "x")
            self.assertFalse((ordner / "a.txt").exists())

    def test_fehlender_ordner(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ablage.AblageFehler):
                ablage.schreiben(Path(t) / "fehlt" / "a.txt", "x")
