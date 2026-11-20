"""unterlagen.py: Verweise prüfen, Dateien finden, nichts außerhalb der Wurzeln."""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import unterlagen


class TestPruefen(unittest.TestCase):
    def test_erlaubt(self):
        for gut in ("fehlstellenscan/docs/markt.md", "fehlstellenscan/docs", "uni/data/projekte/x/wissen.md",
                    "fehlstellenscan/data/gruppe/dateien"):
            with self.subTest(gut=gut):
                self.assertTrue(unterlagen.erlaubt(gut))
        for schlecht in ("fehlstellenscan/.env", "uni/.env", "fehlstellenscan/docs/../.env", "/etc/passwd",
                         "fehlstellenscan/data/laeufe", "fehlstellenscan", "uni/data/projekte/.x/a.md", "",
                         "fehlstellenscan\\docs\\a.md", "./fehlstellenscan/docs/a.md", 3, None):
            with self.subTest(schlecht=schlecht):
                self.assertFalse(unterlagen.erlaubt(schlecht))

    def test_pruefen(self):
        daten = {"verweise": {"markt": ["fehlstellenscan/docs/markt.md", {"pfad": "uni/.env"},
                                        {"pfad": "fehlstellenscan/unterlagen", "titel": "  Literatur  "}, 7],
                              "Böse": ["fehlstellenscan/docs/a.md"], "leer": ["uni/.env"], "x": "kein-liste"}}
        self.assertEqual(unterlagen.pruefen(daten), {"markt": [
            {"pfad": "fehlstellenscan/docs/markt.md", "titel": ""},
            {"pfad": "fehlstellenscan/unterlagen", "titel": "Literatur"}]})
        self.assertEqual(unterlagen.pruefen([]), {})
        self.assertEqual(unterlagen.pruefen({"verweise": []}), {})


class TestDateien(unittest.TestCase):
    def setUp(self):
        self.haupt = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.haupt)
        docs = self.haupt / "fehlstellenscan" / "docs"
        docs.mkdir(parents=True)
        (docs / "markt.md").write_text("Vorspann\n# Markt der Kappscanner\nText", encoding="utf-8")
        (docs / ".geheim.md").write_text("x")
        (docs / "skript.py").write_text("x")
        (self.haupt / "fehlstellenscan" / ".env").write_text("TOKEN=1")
        gruppe = self.haupt / "fehlstellenscan" / "data" / "gruppe" / "dateien"
        for nr, name in (("206", "foto_206.jpg"), ("221", "009-JBH_V1.pdf")):
            (gruppe / nr).mkdir(parents=True)
            (gruppe / nr / name).write_bytes(b"x")
        alt = time.time() - 3600
        os.utime(gruppe / "221" / "009-JBH_V1.pdf", (alt, alt))
        (gruppe / "221" / "tief" / "tiefer").mkdir(parents=True)
        (gruppe / "221" / "tief" / "tiefer" / "zu-tief.png").write_bytes(b"x")
        (gruppe / "link.md").symlink_to(self.haupt / "fehlstellenscan" / ".env")
        projekt = self.haupt / "uni" / "data" / "projekte" / "fehlstellen"
        projekt.mkdir(parents=True)
        (projekt / "kontakte.json").write_text("{}")
        (projekt / "schriftverkehr.json").write_text(json.dumps({"stand": "2026-11-20T13:00", "seit": "2026-10-01",
            "gekappt": False, "mails": [
                {"betreff": "Alt", "datum": "2026-10-21T12:00", "richtung": "an", "von": "Jan", "an": ["B"], "text": "a"},
                {"betreff": "Neu", "datum": "2026-11-16T13:05", "richtung": "von", "von": "B", "an": "Jan", "text": "n"},
                "kaputt"]}), encoding="utf-8")
        (self.haupt / "geheim.md").write_text("x")
        self.verweise = unterlagen.pruefen({"verweise": {"o": [
            "fehlstellenscan/docs/markt.md", {"pfad": "fehlstellenscan/data/gruppe/dateien", "titel": "Aus der Gruppe"},
            "uni/data/projekte/fehlstellen/schriftverkehr.json", "uni/data/projekte/fehlstellen/kontakte.json",
            "fehlstellenscan/docs/fehlt.md", "fehlstellenscan/docs"]}})["o"]

    def test_eintraege(self):
        z = unterlagen.eintraege(self.haupt, self.verweise)
        self.assertEqual([(x["nr"], x["titel"], x["art"], x["fehlt"]) for x in z], [
            ("0", "Markt der Kappscanner", "text", False),
            ("1-0", "foto_206", "bild", False),  # neueste zuerst
            ("1-1", "009-JBH_V1", "seiten", False),
            ("2", "Schriftverkehr", "mails", False),
            ("4", "fehlt.md", "", True),
            ("5-0", "Markt der Kappscanner", "text", False)])  # kontakte.json, .geheim.md, skript.py nicht
        self.assertEqual(z[1]["unter"], "Aus der Gruppe")

    def test_finden(self):
        self.assertEqual(unterlagen.finden(self.haupt, self.verweise, "0")[0].name, "markt.md")
        self.assertEqual(unterlagen.finden(self.haupt, self.verweise, "1-1")[0].name, "009-JBH_V1.pdf")
        for nr in ("1", "1-2", "3", "4", "0-0", "9", "", "../0", "1-x"):
            with self.subTest(nr=nr):
                self.assertIsNone(unterlagen.finden(self.haupt, self.verweise, nr))

    def test_nichts_ausserhalb(self):
        """Symlink aus der Wurzel hinaus und .env bleiben draußen, auch wenn sie jemand einträgt."""
        namen = [p.name for p in unterlagen.dateien_von(self.haupt, "fehlstellenscan/data/gruppe/dateien")]
        self.assertEqual(namen, ["foto_206.jpg", "009-JBH_V1.pdf"])
        self.assertIsNone(unterlagen.aufloesen(self.haupt, "fehlstellenscan/data/gruppe/dateien/link.md"))
        self.assertEqual(unterlagen.dateien_von(self.haupt, "fehlstellenscan/data/gruppe/dateien/link.md"), [])

    def test_mails(self):
        post = unterlagen.mails(self.haupt / "uni/data/projekte/fehlstellen/schriftverkehr.json")
        self.assertEqual([(m["betreff"], m["von_mir"], m["an"]) for m in post["mails"]],
                         [("Neu", False, ["Jan"]), ("Alt", True, ["B"])])
        self.assertEqual((post["stand"], post["seit"], post["gekappt"]), ("2026-11-20T13:00", "2026-10-01", False))
        kaputt = self.haupt / "uni/data/projekte/fehlstellen/x.json"
        kaputt.write_text("[]")
        with self.assertRaises(ValueError):
            unterlagen.mails(kaputt)


if __name__ == "__main__":
    unittest.main()
