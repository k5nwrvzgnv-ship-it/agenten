import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

from agentkit import textfassung

NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
DOKUMENT = f"""<w:document {NS}><w:body>
<w:p><w:r><w:t>Aufgabe 1: </w:t></w:r><w:commentRangeStart w:id="0"/><w:r><w:t>Erkläre Kants</w:t></w:r>
<w:r><w:t> Vergeltung.</w:t></w:r><w:commentRangeEnd w:id="0"/></w:p>
<w:p><w:commentRangeStart w:id="1"/><w:r><w:t>Bild</w:t></w:r><w:commentRangeEnd w:id="1"/></w:p>
</w:body></w:document>"""
KOMMENTARE = f"""<w:comments {NS}>
<w:comment w:id="0" w:author="Lia"><w:p><w:r><w:t>Zu schwer für Klasse 8.</w:t></w:r></w:p>
<w:p><w:r><w:t>Bitte mit Beispiel.</w:t></w:r></w:p></w:comment>
<w:comment w:id="1" w:author="Lia"><w:p><w:r><w:t>raus</w:t></w:r></w:p></w:comment>
</w:comments>"""


class TestWordKommentare(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def docx(self, kommentare=True):
        pfad = self.tmp / "Blatt.docx"
        with zipfile.ZipFile(pfad, "w") as z:
            z.writestr("word/document.xml", DOKUMENT)
            if kommentare:
                z.writestr("word/comments.xml", KOMMENTARE)
        return pfad

    def test_kommentare_mit_stelle(self):
        self.assertEqual(textfassung.word_kommentare(self.docx()), [
            {"stelle": "Erkläre Kants Vergeltung.", "kommentar": "Zu schwer für Klasse 8.\nBitte mit Beispiel.",
             "autor": "Lia"},
            {"stelle": "Bild", "kommentar": "raus", "autor": "Lia"}])

    def test_ohne_kommentare_und_andere_formate(self):
        self.assertEqual(textfassung.word_kommentare(self.docx(kommentare=False)), [])
        self.assertEqual(textfassung.word_kommentare(self.tmp / "x.pdf"), [])

    def test_kaputt(self):
        (self.tmp / "kaputt.docx").write_text("kein zip")
        with self.assertRaises(ValueError):
            textfassung.word_kommentare(self.tmp / "kaputt.docx")
        with self.assertRaises(ValueError):
            textfassung.word_absaetze(self.tmp / "kaputt.docx")

    def test_absaetze_ohne_pakete(self):
        self.assertEqual(textfassung.word_absaetze(self.docx()), ["Aufgabe 1: Erkläre Kants Vergeltung.", "Bild"])
        self.assertEqual(textfassung.word_absaetze(self.tmp / "x.pdf"), [])

    def test_kommentare_nach_endung(self):
        self.assertEqual(textfassung.kommentare(self.docx()), textfassung.word_kommentare(self.docx()))
        (self.tmp / "notiz.txt").write_text("Text")
        self.assertEqual(textfassung.kommentare(self.tmp / "notiz.txt"), [])


# Seite 1: zwei Zeilen links, eine Randnotiz rechts in Zeile 1, eine Zeile per cm um 100 nach unten verschoben.
SEITE_1 = (b"BT /F1 12 Tf 72 700 Td (Erste Zeile mit Holz.) Tj ET "
           b"BT /F1 12 Tf 400 700 Td (Randnotiz) Tj ET "
           b"BT /F1 12 Tf 72 680 Td (Zweite Zeile bleibt.) Tj ET "
           b"q 1 0 0 1 0 -100 cm BT /F1 12 Tf 72 700 Td (Verschobene Zeile.) Tj ET Q")
SEITE_2 = b"BT /F1 12 Tf 72 700 Td (Seite zwei.) Tj ET"


@unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf fehlt in dieser Umgebung")
class TestPdfKommentare(unittest.TestCase):
    def setUp(self):
        from pypdf import PdfWriter, annotations
        from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject,
                                   TextStringObject)
        self.tmp = Path(tempfile.mkdtemp())
        schrift = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                    NameObject("/Subtype"): NameObject("/Type1"),
                                    NameObject("/BaseFont"): NameObject("/Helvetica")})
        w = PdfWriter()
        for inhalt in (SEITE_1, SEITE_2):
            seite = w.add_blank_page(595, 842)
            strom = DecodedStreamObject()
            strom.set_data(inhalt)
            seite[NameObject("/Contents")] = w._add_object(strom)
            seite[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): w._add_object(schrift)})})

        def markierung(vierecke, kommentar=None, autor=None):
            quad = ArrayObject(FloatObject(z) for v in vierecke for z in v)
            a = annotations.Highlight(rect=(72, 590, 300, 715), quad_points=quad)
            if kommentar is not None:
                a[NameObject("/Contents")] = TextStringObject(kommentar)
            if autor is not None:
                a[NameObject("/T")] = TextStringObject(autor)
            return a

        zeile_1 = (72, 712, 250, 712, 72, 697, 250, 697)
        zeile_2 = (72, 692, 300, 692, 72, 677, 300, 677)
        verschoben = (72, 612, 300, 612, 72, 597, 300, 597)
        w.add_annotation(0, markierung([zeile_1], "Welches Holz?", "Jan"))
        w.add_annotation(0, markierung([zeile_2, verschoben], "Zwei Zeilen\r\nmit Umbruch\r", "Jan"))
        w.add_annotation(0, markierung([zeile_1]))
        w.add_annotation(0, markierung([zeile_2], "  "))
        notiz = annotations.Text(rect=(500, 700, 520, 720), text=" Allgemeine Notiz ")
        notiz[NameObject("/T")] = TextStringObject("Lia")
        w.add_annotation(0, notiz)
        link = annotations.Link(rect=(72, 697, 250, 712), url="https://example.org")
        link[NameObject("/Contents")] = TextStringObject("Link-Text")
        w.add_annotation(1, link)
        popup = annotations.Popup(rect=(300, 300, 400, 400))
        popup[NameObject("/Contents")] = TextStringObject("Popup-Text")
        w.add_annotation(1, popup)
        w.add_annotation(1, annotations.FreeText(text="Freitext auf Seite 2", rect=(72, 500, 300, 520)))
        self.pdf = self.tmp / "Expose.pdf"
        with open(self.pdf, "wb") as f:
            w.write(f)

    def test_markierungen_und_notizen(self):
        erwartet = [
            {"seite": 1, "stelle": "Erste Zeile mit Holz.", "kommentar": "Welches Holz?", "autor": "Jan"},
            {"seite": 1, "stelle": "Zweite Zeile bleibt. Verschobene Zeile.", "kommentar": "Zwei Zeilen\nmit Umbruch",
             "autor": "Jan"},
            {"seite": 1, "stelle": "", "kommentar": "Allgemeine Notiz", "autor": "Lia"},
            {"seite": 2, "stelle": "", "kommentar": "Freitext auf Seite 2", "autor": ""}]
        self.assertEqual(textfassung.pdf_kommentare(self.pdf), erwartet)
        self.assertEqual(textfassung.kommentare(self.pdf), erwartet)

    def test_ohne_kommentare_und_andere_formate(self):
        from pypdf import PdfWriter
        w = PdfWriter()
        w.add_blank_page(595, 842)
        with open(self.tmp / "leer.pdf", "wb") as f:
            w.write(f)
        self.assertEqual(textfassung.pdf_kommentare(self.tmp / "leer.pdf"), [])
        self.assertEqual(textfassung.pdf_kommentare(self.tmp / "x.docx"), [])

    def test_kaputt(self):
        (self.tmp / "kaputt.pdf").write_text("kein pdf")
        with self.assertRaises(ValueError):
            textfassung.pdf_kommentare(self.tmp / "kaputt.pdf")
        with self.assertRaises(ValueError):
            textfassung.kommentare(self.tmp / "kaputt.pdf")


if __name__ == "__main__":
    unittest.main()
