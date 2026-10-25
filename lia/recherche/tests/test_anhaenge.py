import os
import shutil
import tempfile
import unittest
from pathlib import Path

import anhaenge


class AnhaengeTest(unittest.TestCase):
    def setUp(self):
        self.wurzel = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.wurzel)
        (self.wurzel / "examen").mkdir()
        (self.wurzel / "instanz").mkdir()
        (self.wurzel / "examen" / ".venv").mkdir()
        self.gut = self.wurzel / "examen" / "vorbild.md"
        self.gut.write_text("Vorbild", encoding="utf-8")

    def grund(self, p):
        return anhaenge.grund(p, self.wurzel)

    def datei(self, rel, inhalt=b"x"):
        p = self.wurzel / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(inhalt)
        return p

    def test_aus_auftrag(self):
        text = "AUFGABE\nANHANG: /a/b.md\n  ANHANG:  /c d/e.pdf  \nkein ANHANG: hier\n"
        self.assertEqual(anhaenge.aus_auftrag(text), ["/a/b.md", "/c d/e.pdf"])

    def test_erlaubt(self):
        self.assertIsNone(self.grund(self.gut))

    def test_abgelehnt(self):
        faelle = {
            "examen/vorbild.md": "kein absoluter Pfad",
            str(self.wurzel / "fehlt.md"): "nicht gefunden",
            "/etc/hostname": "nicht unter",
            str(self.datei("instanz/x.md")): "gesperrt",
            str(self.datei("examen/.venv/x.md")): ".venv",
            str(self.datei("examen/.git/x.md")): ".git",
            str(self.datei("examen/.env.md")): ".env",
            str(self.datei("examen/skript.py")): "Endung .py",
            str(self.datei("examen/gross.pdf", b"x" * (anhaenge.MAX_BYTES + 1))): "größer",
        }
        for pfad, teil in faelle.items():
            self.assertIn(teil, self.grund(pfad) or "", pfad)
        self.assertIn("keine Datei", self.grund(str(self.datei("examen/ordner.md/x.txt").parent)))

    def test_symlink_nach_aussen(self):
        link = self.wurzel / "examen" / "link.md"
        os.symlink("/etc/hostname", link)
        self.assertIn("nicht unter", self.grund(str(link)))

    def test_kopieren_mit_textfassung_und_doppelten_namen(self):
        doc = self.datei("examen/a.docx")
        zweit = self.datei("unterricht/vorbild.md")
        ziel = self.wurzel / "ziel"
        kopiert, abgelehnt = anhaenge.kopieren(
            [str(self.gut), str(doc), str(zweit), str(self.gut), "/etc/hostname"], ziel, lambda p: "TEXT", self.wurzel)
        self.assertEqual([p.name for p in kopiert], ["vorbild.md", "a.docx", "a.docx.txt", "vorbild-2.md"])
        self.assertEqual((ziel / "a.docx.txt").read_text(encoding="utf-8"), "TEXT")
        self.assertEqual(len(abgelehnt), 1)
        self.assertIn("/etc/hostname", abgelehnt[0])

    def test_textfassung_scheitert_wird_gemeldet(self):
        pdf = self.datei("examen/b.pdf")

        def kaputt(p):
            raise ModuleNotFoundError("No module named 'pypdf'")
        kopiert, abgelehnt = anhaenge.kopieren([str(pdf)], self.wurzel / "ziel", kaputt, self.wurzel)
        self.assertEqual([p.name for p in kopiert], ["b.pdf"])
        self.assertIn("Textfassung nicht möglich", abgelehnt[0])


if __name__ == "__main__":
    unittest.main()
