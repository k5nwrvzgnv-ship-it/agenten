import shutil
import tempfile
import unittest
from pathlib import Path

import dateien

ERLAUBT = dateien.DOWNLOAD_ENDUNGEN


class TestDateien(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.agent = self.tmp / "theater"
        self.ordner = self.agent / "data" / "runde" / "fuer-lia"
        self.ordner.mkdir(parents=True)
        (self.ordner / "1 Szenenkarte.docx").write_bytes(b"x")
        (self.tmp / "draussen.pdf").write_bytes(b"x")

    def test_agent_ordner(self):
        instanz = self.tmp / "instanz"
        self.assertEqual(dateien.agent_ordner(instanz, "theater"), self.agent)
        for falsch in (None, "", "..", "the/ater", "Theater", "../x"):
            self.assertIsNone(dateien.agent_ordner(instanz, falsch), falsch)

    def test_sicher_erlaubt(self):
        self.assertEqual(dateien.sicher(self.agent, "data/runde/fuer-lia/1 Szenenkarte.docx", ERLAUBT),
                         (self.ordner / "1 Szenenkarte.docx").resolve())

    def test_sicher_verweigert(self):
        (self.agent / ".env").write_text("x")
        (self.agent / "notiz.txt").write_text("x")
        (self.agent / "link.pdf").symlink_to(self.tmp / "draussen.pdf")
        (self.agent / "data" / "verlinkt").symlink_to(self.tmp)
        for falsch in ("../draussen.pdf", str(self.tmp / "draussen.pdf"), ".env", "notiz.txt", "fehlt.pdf",
                       "data/runde/../../../draussen.pdf", "link.pdf", "data/verlinkt/draussen.pdf",
                       "data/runde/fuer-lia"):
            self.assertIsNone(dateien.sicher(self.agent, falsch, ERLAUBT), falsch)

    def test_vorschau(self):
        v = self.ordner / "1 Szenenkarte-vorschau"
        v.mkdir()
        for n in (1, 2, 10):
            (v / f"1 Szenenkarte-seite-{n:02d}.png").write_bytes(b"x")
        (v / "1 Szenenkarte-seite-3.png.txt").write_bytes(b"x")
        (v / "anderes-seite-01.png").write_bytes(b"x")
        (v / "1 Szenenkarte.pdf").write_bytes(b"x")
        rel = "data/runde/fuer-lia/1 Szenenkarte.docx"
        self.assertEqual([p.name for p in dateien.vorschau_seiten(self.agent, rel)],
                         ["1 Szenenkarte-seite-01.png", "1 Szenenkarte-seite-02.png", "1 Szenenkarte-seite-10.png"])
        self.assertEqual(dateien.vorschau_pdf(self.agent, rel), (v / "1 Szenenkarte.pdf").resolve())
        self.assertEqual(dateien.vorschau_info(self.agent, [rel, "data/fehlt.pdf"]), [(True, True, 3),
                                                                                       (False, False, 0)])
        self.assertEqual(dateien.vorschau_info(None, [rel]), [(False, False, 0)])

    def test_vorschau_ausserhalb_leer(self):
        v = self.tmp / "draussen-vorschau"
        v.mkdir()
        (v / "draussen-seite-01.png").write_bytes(b"x")
        self.assertEqual(dateien.vorschau_seiten(self.agent, "../draussen.pdf"), [])
        self.assertIsNone(dateien.vorschau_pdf(self.agent, "../draussen.pdf"))


if __name__ == "__main__":
    unittest.main()
