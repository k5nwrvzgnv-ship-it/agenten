"""Vorschau: PDF -> Bilder immer, docx/pptx -> PDF nur, wenn LibreOffice installiert ist."""

import shutil
import tempfile
import unittest
from pathlib import Path

import pypdfium2
from PIL import Image

from renderer import arbeitsblatt, vorschau
from renderer.pruefung import lesen

A4_PT = (595, 842)


def leere_pdf(pfad: Path, seiten: int) -> Path:
    d = pypdfium2.PdfDocument.new()
    for _ in range(seiten):
        d.new_page(*A4_PT)
    d.save(pfad)
    d.close()
    return pfad


class TestBilder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_ein_bild_je_seite(self):
        bilder = vorschau.vorschau(leere_pdf(self.tmp / "blatt.pdf", 2), self.tmp / "aus")
        self.assertEqual([b.name for b in bilder], ["blatt-seite-01.png", "blatt-seite-02.png"])
        with Image.open(bilder[0]) as bild:
            self.assertEqual(bild.size, (827, 1170))  # A4 bei 100 dpi

    def test_hoechstens_max_seiten(self):
        alt = vorschau.MAX_SEITEN
        vorschau.MAX_SEITEN = 2
        try:
            self.assertEqual(len(vorschau.vorschau(leere_pdf(self.tmp / "lang.pdf", 3), self.tmp)), 2)
        finally:
            vorschau.MAX_SEITEN = alt

    def test_kaputte_pdf(self):
        (self.tmp / "kaputt.pdf").write_text("keine pdf")
        with self.assertRaisesRegex(vorschau.VorschauFehler, "kaputt.pdf: PDF lässt sich nicht öffnen"):
            vorschau.vorschau(self.tmp / "kaputt.pdf", self.tmp)

    def test_falsche_endung_und_fehlende_datei(self):
        with self.assertRaisesRegex(vorschau.VorschauFehler, "nur .docx"):
            vorschau.vorschau(self.tmp / "bild.png", self.tmp)
        with self.assertRaisesRegex(vorschau.VorschauFehler, "Datei fehlt"):
            vorschau.vorschau(self.tmp / "fehlt.docx", self.tmp)

    def test_ohne_libreoffice(self):
        (self.tmp / "a.docx").write_bytes(b"x")
        alt = vorschau.SOFFICE
        vorschau.SOFFICE = "gibt-es-nicht-soffice"
        try:
            with self.assertRaisesRegex(vorschau.VorschauFehler, "nicht installiert"):
                vorschau.vorschau(self.tmp / "a.docx", self.tmp)
        finally:
            vorschau.SOFFICE = alt


@unittest.skipUnless(shutil.which(vorschau.SOFFICE), "LibreOffice nicht installiert")
class TestLibreOffice(unittest.TestCase):
    def test_arbeitsblatt_als_bild(self):
        tmp = Path(tempfile.mkdtemp())
        beschreibung = lesen({"art": "arbeitsblatt", "titel": "Test", "bloecke": [{"typ": "absatz", "text": "Hallo"}]})
        docx = arbeitsblatt.bauen(beschreibung, tmp / "blatt.docx")
        bilder = vorschau.vorschau(docx, tmp / "aus")
        self.assertEqual([b.name for b in bilder], ["blatt-seite-01.png"])
        self.assertTrue((tmp / "aus" / "blatt.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
