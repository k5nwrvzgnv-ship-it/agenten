import json
import tempfile
import unittest
from pathlib import Path

import lernblatt

GUELTIG = {"art": "zusammenfassung", "titel": "Exkursion Hausschwamm", "kurs": "Integrierter Holzschutz",
           "datum": "27.10.2026", "bloecke": [{"typ": "absatz", "text": "Dem Hausschwamm das Holz entziehen.",
                                               "quellen": [{"art": "transkript", "stelle": "6"}]}]}


def pdf_attrappe(docx: Path, ziel: Path) -> Path:
    """Statt LibreOffice: legt nur eine Datei mit dem Namen an, den als_pdf liefern würde."""
    pdf = ziel / f"{docx.stem}.pdf"
    pdf.write_text("pdf")
    return pdf


class TestBauen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name) / "a1"
        self.ordner.mkdir()

    def schreiben(self, name, inhalt):
        (self.ordner / name).write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt))

    def bauen(self, **kw):
        return lernblatt.bauen_neue(self.ordner, {}, als_pdf=kw.pop("als_pdf", pdf_attrappe), **kw)

    def test_baut_echtes_docx_und_pdf_einmal(self):
        self.schreiben("blatt_1.json", GUELTIG)
        b = self.bauen()
        ausgang = self.ordner / "blatt_1"
        self.assertEqual(b.pdfs, [ausgang / "Exkursion Hausschwamm.pdf"])
        self.assertTrue((ausgang / "Exkursion Hausschwamm.docx").stat().st_size > 0)
        self.assertEqual((b.ungueltig, b.fehler), ({}, []))
        self.assertEqual(self.bauen().pdfs, [])  # unverändert: nicht noch einmal

    def test_geaendert_neu_gebaut_alte_fassung_weg(self):
        self.schreiben("blatt_1.json", GUELTIG)
        self.bauen()
        self.schreiben("blatt_1.json", {**GUELTIG, "titel": "Hausschwamm: Sanierung"})
        b = self.bauen()
        self.assertEqual([p.name for p in b.pdfs], ["Hausschwamm - Sanierung.pdf"])
        self.assertEqual(sorted(p.name for p in (self.ordner / "blatt_1").iterdir()),
                         ["Hausschwamm - Sanierung.docx", "Hausschwamm - Sanierung.pdf"])

    def test_ungueltige_gehen_an_claude_gueltige_trotzdem(self):
        self.schreiben("blatt_1.json", "{kein json")
        self.schreiben("blatt_2.json", {**GUELTIG, "bloecke": []})
        self.schreiben("blatt_3.json", {"art": "arbeitsblatt", "titel": "T",
                                        "bloecke": [{"typ": "absatz", "text": "x"}]})
        self.schreiben("blatt_4.json", GUELTIG)
        self.schreiben("notiz.json", "{kein blatt")  # andere Dateien zählen nicht
        b = self.bauen()
        self.assertEqual(sorted(b.ungueltig), ["blatt_1.json", "blatt_2.json", "blatt_3.json"])
        self.assertIn("bloecke", b.ungueltig["blatt_2.json"])
        self.assertIn('Lernblätter sind "zusammenfassung"', b.ungueltig["blatt_3.json"])
        self.assertEqual([p.parent.name for p in b.pdfs], ["blatt_4"])
        self.assertEqual(sorted(self.bauen().ungueltig), ["blatt_1.json", "blatt_2.json", "blatt_3.json"])

    def test_pdf_fehler_ist_fehler_des_agenten_und_wird_wiederholt(self):
        def kaputt(docx, ziel):
            raise lernblatt.vorschau.VorschauFehler("LibreOffice fehlt")

        self.schreiben("blatt_1.json", GUELTIG)
        b = self.bauen(als_pdf=kaputt)
        self.assertEqual((b.pdfs, b.ungueltig), ([], {}))
        self.assertEqual(b.fehler, ["blatt_1.json: LibreOffice fehlt"])
        self.assertEqual(len(self.bauen().pdfs), 1)  # nächster Lauf versucht es wieder

    def test_dateiname(self):
        self.assertEqual(lernblatt.dateiname("Holzschutz: Grundlagen"), "Holzschutz - Grundlagen")
        self.assertEqual(lernblatt.dateiname("A/B 27.10."), "A_B 27.10.")

    def test_ohne_ordner_nichts(self):
        b = lernblatt.bauen_neue(self.ordner / "fehlt", {})
        self.assertEqual((b.pdfs, b.ungueltig, b.fehler), ([], {}, []))


class TestFormat(unittest.TestCase):
    def test_echtes_format_abgelegt(self):
        quelle = Path(lernblatt.pruefung.__file__).with_name("FORMAT.md").read_text()
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "x" / "FORMAT.md"
            lernblatt.format_ablegen(quelle, ziel)
            text = ziel.read_text()
            self.assertIn("## Allgemein", text)
            self.assertIn('"art": "zusammenfassung"', text)
            self.assertNotIn("## Folien", text)
            self.assertNotIn("## Arbeitsblatt", text)
            vorher = ziel.stat().st_mtime_ns
            lernblatt.format_ablegen(quelle, ziel)
            self.assertEqual(ziel.stat().st_mtime_ns, vorher)


if __name__ == "__main__":
    unittest.main()
