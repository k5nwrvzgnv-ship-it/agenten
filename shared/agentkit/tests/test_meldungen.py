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

    def test_dateien(self):
        agenten = self.basis / "agenten"
        (agenten / "dokumente").mkdir(parents=True)
        (agenten / "dokumente" / "Folien.pptx").write_text("x")
        mid = meldungen.melden("dokumente", "Fertig", dateien=["Folien.pptx"], basis=self.basis,
                               agenten_dir=agenten)
        self.assertEqual(meldungen.neue(basis=self.basis)[0]["dateien"], ["Folien.pptx"])
        self.assertTrue(mid)
        with self.assertRaises(meldungen.MeldungFehler):
            meldungen.melden("dokumente", "x", dateien=["../../etc/passwd"], basis=self.basis,
                             agenten_dir=agenten)

    def test_knoepfe_und_dienst(self):
        mid = meldungen.melden("uni", "Heute 12:30 Holzschutz", knoepfe=[["Hingehen", "Nicht"]],
                               dienst="uni-lernen", basis=self.basis)
        m = meldungen.neue(basis=self.basis)[0]
        self.assertEqual((m["knoepfe"], m["dienst"]), ([["Hingehen", "Nicht"]], "uni-lernen"))
        self.assertTrue(meldungen.nimmt_antwort(m))
        with self.assertRaises(meldungen.MeldungFehler):
            meldungen.gesendete(mid, basis=self.basis)
        meldungen.als_gesendet(mid, basis=self.basis)
        self.assertEqual(meldungen.gesendete(mid, basis=self.basis)["knoepfe"], [["Hingehen", "Nicht"]])

    def test_ohne_knoepfe_keine_antwort(self):
        meldungen.melden("uni", "Frist morgen", basis=self.basis)
        m = meldungen.neue(basis=self.basis)[0]
        self.assertEqual((m["knoepfe"], m["dienst"]), ([], None))
        self.assertFalse(meldungen.nimmt_antwort(m))

    def test_knoepfe_ungueltig(self):
        for knoepfe in ([["x"]] * 11, [["x"] * 9], [[]], [[""]], [["x" * 41]], [["ok", 5]], ["Hingehen"]):
            with self.subTest(knoepfe=knoepfe), self.assertRaises(meldungen.MeldungFehler):
                meldungen.melden("uni", "t", knoepfe=knoepfe, basis=self.basis)
        for dienst in ("dokumente", "uni-", "uni-lernen.service", "uni-../x", "uni lernen"):
            with self.subTest(dienst=dienst), self.assertRaises(meldungen.MeldungFehler):
                meldungen.melden("uni", "t", dienst=dienst, basis=self.basis)
        self.assertEqual(meldungen.neue(basis=self.basis), [])


if __name__ == "__main__":
    unittest.main()
