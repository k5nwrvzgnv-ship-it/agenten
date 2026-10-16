import tempfile
import unittest
from pathlib import Path

from agentkit import meldungen


class TestMeldungen(unittest.TestCase):
    def setUp(self):
        self.basis = Path(tempfile.mkdtemp())

    def test_ablauf(self):
        mid = meldungen.melden("uni", "Abgabe morgen", basis=self.basis)
        neu = meldungen.neue(basis=self.basis)
        self.assertEqual([(m["id"], m["agent"], m["text"]) for m in neu], [(mid, "uni", "Abgabe morgen")])
        self.assertEqual(meldungen.neue("einkauf", basis=self.basis), [])
        m = meldungen.als_gesendet(mid, basis=self.basis)
        self.assertIsNotNone(m["gesendet"])
        self.assertEqual(meldungen.neue(basis=self.basis), [])
        self.assertEqual(sorted(p.name for p in (self.basis / "gesendet").iterdir()), [f"{mid}.json"])

    def test_nicht_doppelt_senden(self):
        mid = meldungen.melden("uni", "x", basis=self.basis)
        meldungen.als_gesendet(mid, basis=self.basis)
        with self.assertRaises(meldungen.MeldungFehler):
            meldungen.als_gesendet(mid, basis=self.basis)

    def test_leer_und_ungueltig(self):
        with self.assertRaises(meldungen.MeldungFehler):
            meldungen.melden("uni", "  ", basis=self.basis)
        with self.assertRaises(meldungen.MeldungFehler):
            meldungen.melden("../x", "t", basis=self.basis)
        with self.assertRaises(meldungen.MeldungFehler):
            meldungen.als_gesendet("../../etc/passwd", basis=self.basis)


if __name__ == "__main__":
    unittest.main()
