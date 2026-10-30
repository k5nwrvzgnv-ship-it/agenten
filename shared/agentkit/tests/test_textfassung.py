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


if __name__ == "__main__":
    unittest.main()
