"""Dateien eines Auftrags vorbereiten: Textfassung und Seitenbilder."""

import tempfile
import unittest
from pathlib import Path

import docx
from PIL import Image

import eingang

# Kleinstes PDF mit einer Textzeile (pdfium baut die fehlende Querverweistabelle selbst)
PDF_MIT_TEXT = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
                b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R"
                b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
                b"4 0 obj<</Length 41>>stream\nBT /F1 12 Tf 20 100 Td (Holzschutz) Tj ET\nendstream endobj\n"
                b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")


class TestEingang(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_docx_bekommt_textfassung(self):
        d = docx.Document()
        d.add_paragraph("Bläuepilze")
        d.save(self.tmp / "a.docx")
        neu = eingang.vorbereiten(self.tmp / "a.docx")
        self.assertEqual(neu, [self.tmp / "a.docx.txt"])
        self.assertEqual(neu[0].read_text(), "Bläuepilze")

    def test_pdf_text_und_bilder(self):
        (self.tmp / "f.pdf").write_bytes(PDF_MIT_TEXT)
        txt, *bilder = eingang.vorbereiten(self.tmp / "f.pdf")
        self.assertIn("--- Seite 1\nHolzschutz", txt.read_text())
        self.assertEqual([b.parent.name for b in bilder], ["f-seiten"])
        self.assertEqual(eingang.vorbereiten(self.tmp / "f.pdf")[1:], bilder)  # zweiter Aufruf: nichts neu

    def test_scan_ohne_text(self):
        Image.new("RGB", (200, 300), "white").save(self.tmp / "scan.pdf")
        txt, bild = eingang.vorbereiten(self.tmp / "scan.pdf")
        self.assertIn("Kein Text gefunden", txt.read_text())
        self.assertTrue(bild.is_file())

    def test_andere_dateien_bleiben(self):
        (self.tmp / "t.md").write_text("x")
        self.assertEqual(eingang.vorbereiten(self.tmp / "t.md"), [])


if __name__ == "__main__":
    unittest.main()
