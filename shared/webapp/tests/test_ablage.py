import io
import tempfile
import unittest
from pathlib import Path

import ablage


class Ablage(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.instanz = Path(self._tmp.name) / "instanz"
        self.instanz.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_ort_und_namen(self):
        self.assertTrue(ablage.ort_gueltig("ethik-8-strafe"))
        for falsch in ("", "../x", "A", "a/b", ".x", "a" * 121):
            self.assertFalse(ablage.ort_gueltig(falsch), falsch)
        self.assertEqual(ablage.name_bereinigen("../../Kriterien:Theater.PDF"), "Kriterien_Theater.pdf")
        self.assertEqual(ablage.name_bereinigen(".env"), "env")

    def test_pruefen(self):
        self.assertEqual(ablage.pruefen("a.pdf", 10, 0), "")
        self.assertEqual(ablage.pruefen("IMG_1.HEIC", 10, 0), "heic")
        self.assertEqual(ablage.pruefen("a.exe", 10, 0), "art")
        self.assertEqual(ablage.pruefen("a.pdf", 0, 0), "leer")
        self.assertEqual(ablage.pruefen("a.pdf", ablage.MAX_BYTES + 1, 0), "gross")
        self.assertEqual(ablage.pruefen("a.pdf", 1, ablage.MAX_JE_ORT), "voll")

    def test_ablegen_liste_entfernen(self):
        name = ablage.ablegen(self.instanz, "kurs-12", "Bewertung.pdf", io.BytesIO(b"%PDF-1"))
        ablage.ablegen(self.instanz, "kurs-12", "Foto.JPG", io.BytesIO(b"jpg"))
        ablage.ablegen(self.instanz, "kurs-12", "Bewertung.pdf", io.BytesIO(b"%PDF-2"))  # gleicher Name ersetzt
        (self.instanz / "ablage" / "kurs-12" / ".versteckt.pdf").write_bytes(b"x")
        (self.instanz / "ablage" / "kurs-12" / "notiz.txt").write_bytes(b"x")
        namen = {d["name"]: d for d in ablage.liste(self.instanz, "kurs-12")}
        self.assertEqual(set(namen), {"Bewertung.pdf", "Foto.jpg"})
        self.assertEqual((namen["Foto.jpg"]["foto"], namen["Bewertung.pdf"]["art"]), (True, "PDF"))
        self.assertEqual(ablage.pfad(self.instanz, "kurs-12", name).read_bytes(), b"%PDF-2")
        for falsch in ("../kurs-12/Bewertung.pdf", ".versteckt.pdf", "notiz.txt", "fehlt.pdf"):
            self.assertIsNone(ablage.pfad(self.instanz, "kurs-12", falsch), falsch)
        self.assertIsNone(ablage.pfad(self.instanz, "../x", "Bewertung.pdf"))
        self.assertEqual(ablage.liste(self.instanz, "gibt-es-nicht"), [])
        self.assertTrue(ablage.entfernen(self.instanz, "kurs-12", "Bewertung.pdf"))
        self.assertFalse(ablage.entfernen(self.instanz, "kurs-12", "Bewertung.pdf"))
        with self.assertRaises(ValueError):
            ablage.ablegen(self.instanz, "../boese", "a.pdf", io.BytesIO(b"x"))

    def test_symlink_nicht(self):
        o = self.instanz / "ablage" / "r1"
        o.mkdir(parents=True)
        geheim = self.instanz / ".env"
        geheim.write_text("x")
        (o / "a.pdf").symlink_to(geheim)
        self.assertIsNone(ablage.pfad(self.instanz, "r1", "a.pdf"))
        self.assertEqual(ablage.liste(self.instanz, "r1"), [])


if __name__ == "__main__":
    unittest.main()
