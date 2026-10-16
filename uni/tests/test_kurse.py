import tempfile
import unittest
from pathlib import Path

import kurse


class TestKurse(unittest.TestCase):
    def test_sicherer_name(self):
        self.assertEqual(kurse.sicherer_name("../../etc/passwd"), "_.._etc_passwd")
        self.assertEqual(kurse.sicherer_name(".."), "_")
        self.assertEqual(kurse.sicherer_name("Folie 3: Holz/Beton?.pdf"), "Folie 3_ Holz_Beton_.pdf")
        self.assertEqual(kurse.sicherer_name(""), "_")

    def test_html_zu_text(self):
        self.assertEqual(kurse.html_zu_text("<p>Klausur am <b>12.02.</b></p><p>Raum&nbsp;5</p>"),
                         "Klausur am 12.02.\nRaum\xa05")
        self.assertEqual(kurse.html_zu_text(None), "")

    def test_textfassungen(self):
        import docx
        import openpyxl
        import pptx
        ordner = Path(tempfile.mkdtemp())
        d = docx.Document()
        d.add_paragraph("Hausarbeit Holzschutz")
        d.save(ordner / "a.docx")
        p = pptx.Presentation()
        for titel in ("Einleitung", "Brettsperrholz"):
            p.slides.add_slide(p.slide_layouts[0]).shapes.title.text = titel
        p.save(ordner / "b.pptx")
        w = openpyxl.Workbook()
        w.active.title = "Messwerte"
        w.active.append(["Feuchte", 12.5])
        w.save(ordner / "c.xlsx")
        self.assertEqual(kurse.als_text(ordner / "a.docx"), "Hausarbeit Holzschutz")
        self.assertEqual(kurse.als_text(ordner / "b.pptx"), "--- Folie 1\nEinleitung\n--- Folie 2\nBrettsperrholz")
        self.assertEqual(kurse.als_text(ordner / "c.xlsx"), "--- Blatt Messwerte\nFeuchte | 12.5")
        self.assertTrue(kurse._textfassung(ordner / "b.pptx", erneuern=False))
        self.assertTrue((ordner / "b.pptx.txt").exists())
        (ordner / "x.pdf").write_bytes(b"%PDF")
        self.assertFalse(kurse._textfassung(ordner / "x.pdf", erneuern=False))


if __name__ == "__main__":
    unittest.main()
