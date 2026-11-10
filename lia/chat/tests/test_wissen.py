"""Lias Wissen im Gespräch: Lese-Ordner, Übersicht im Prompt, nur Neues bei fortgesetzter Sitzung, Lauf-Grenzen."""

import os
import tempfile
import time
import unittest
from pathlib import Path

import gespraechablage as ga
import gespraechlauf
import schnittstelle as sch
import wissen
from tests.test_gespraech import REIHE, Basis, Fake

KATALOG = ("### Allgemein (data/wissen/text/)\n"
           "- Kriterien_gute_Unterrichtseinheit.txt | Seminar und Notizen | Kriterien für eine gute …\n\n"
           "### Ethik / Kurs (1) (data/wissen/text/Ethik/Kurs (1)/)\n- AB1.txt | Arbeitsblatt | Aufgaben …\n")


def lia_anlegen(wurzel: Path) -> Path:
    """Kleines lia/ wie auf dem Server."""
    lia = wurzel / "lia"
    dateien = {
        "unterricht/STATUS.md": "# Status\n\n## Zweck\nMaterial für Lia\nüber mehrere Zeilen.\n\n## Stand\nx\n",
        "unterricht/leitfaden.md": "# So unterrichtet Lia\n",
        "unterricht/agent.py": "print()\n",
        "unterricht/.env": "GEHEIM=1\n",
        "unterricht/.venv/lib/x.txt": "x",
        "unterricht/logs/u.log": "x",
        "unterricht/data/wissen/katalog.md": KATALOG,
        "unterricht/data/wissen/text/Kriterien_gute_Unterrichtseinheit.txt": "Kriterien: Problemfrage …",
        "unterricht/data/wissen/eingang/Ethik/AB1.docx": "roh",
        "examen/rubrik.toml": "[[kriterium]]\n",
        "examen/data/reihe/runde-1/skizze.md": "Skizze",
        "auswertung/data/lia/chats.json": "[]",
        "chat/data/gespraeche/x.json": "{}",
        ".claude/worktrees/kopie/uni/notizen.md": "Jans Uni",
    }
    for rel, inhalt in dateien.items():
        p = lia / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding="utf-8")
    (lia / "komisch*ordner").mkdir()
    return lia


class Wissen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lia = lia_anlegen(Path(self.tmp.name))
        self.gespraeche = self.lia / "chat" / "data" / "gespraeche"

    def tearDown(self):
        self.tmp.cleanup()

    def test_lese_ordner_alles_von_lia_ausser_chat_und_versteckten(self):
        ordner = wissen.lese_ordner(self.lia, self.gespraeche)
        namen = [o.relative_to(self.lia.resolve()).as_posix() for o in ordner]
        self.assertEqual(namen, ["auswertung", "examen", "unterricht", "chat/data/gespraeche"])

    def test_karte(self):
        k = wissen.karte(self.lia, self.gespraeche)
        # Grundlagen mit vollem Pfad, nur vorhandene
        self.assertIn(f"- {self.lia}/unterricht/data/wissen/text/Kriterien_gute_Unterrichtseinheit.txt: Kriterien", k)
        self.assertIn(f"- {self.lia}/examen/rubrik.toml:", k)
        self.assertNotIn("seminar_vorbild", k)
        # Zweck aus STATUS.md in einer Zeile
        self.assertIn("- unterricht (" + str(self.lia / "unterricht/STATUS.md") + "): Material für Lia über mehrere "
                      "Zeilen.", k)
        # Katalog mit absoluten Ordnern, auch mit Klammern im Namen
        self.assertIn(f"### Ethik / Kurs (1) ({self.lia}/unterricht/data/wissen/text/Ethik/Kurs (1)/)", k)
        self.assertIn("sparen nur Platz", k)  # echter Lauf 10.11.: Claude hielt sie für unlesbar
        # weitere Dateien ohne Code, Zugangsdaten, .venv, Logs, Katalog-Ordner, chat, .claude
        self.assertIn(f"- {self.lia}/examen/data/reihe/runde-1/: skizze.md", k)
        self.assertIn("chats.json", k)
        for nicht in ("agent.py", ".env", "GEHEIM", "u.log", ".venv", "AB1.docx", "Jans Uni", "notizen.md",
                      "/chat/"):
            self.assertNotIn(nicht, k.split("### Weitere Dateien")[1], nicht)

    def test_dateiliste_fasst_tiefe_ordner_zusammen(self):
        for i in range(30):
            p = self.lia / "theater" / "data" / f"runde-{i:02d}" / "bilder" / f"seite-{i}.png"
            p.parent.mkdir(parents=True)
            p.write_bytes(b"x")
        fein = wissen.dateiliste(self.lia, grenze=100_000)
        self.assertIn("/theater/data/runde-07/bilder/: seite-7.png", fein)
        grob = wissen.dateiliste(self.lia, grenze=1_000)
        self.assertLessEqual(len(grob), 1_000)
        self.assertIn("weitere (.png)", grob)

    def test_andere_gespraeche_ohne_das_eigene(self):
        daten = Path(self.tmp.name) / "data"
        a = sch.gespraech_anlegen("Strafe planen", REIHE, ordner=daten)
        b = sch.gespraech_anlegen("Theater", None, ordner=daten)
        sch.nachricht(a, "Hallo", ordner=daten)
        sch.nachricht(b, "Hallo", ordner=daten)
        liste = wissen.gespraeche_liste(ga.ordner_von(daten), ohne=b)
        self.assertIn("- Strafe planen (zuletzt ", liste)
        self.assertIn(str(ga.datei(a, daten)), liste)
        self.assertNotIn("Theater", liste)

    def test_neu_in_karte(self):
        alt = "### A\n- a1\n\n### B\n#### B1\n- b1"
        neu = "### A\n- a1\n- a2\n\n### B\n#### B1\n- b1\n#### B2\n- b2"
        self.assertEqual(wissen.neu_in_karte(alt, neu), "### A\n- a2\n### B\n#### B2\n- b2")
        self.assertEqual(wissen.neu_in_karte(neu, neu), "")

    def test_prompt_teil(self):
        self.assertEqual(wissen.prompt_teil(""), "")
        voll = wissen.prompt_teil("### Grundlagen\n- x")
        self.assertIn("## Lias Wissen", voll)
        self.assertIn("Sag nie, du hättest keine Materialien", voll)
        self.assertIn("Namen von Schüler*innen", voll)
        self.assertTrue(wissen.prompt_teil("- neu.md", neu=False).startswith("Neu in Lias Ablage"))

    def test_fehlendes_lia(self):
        self.assertEqual(wissen.karte(self.lia / "fehlt", self.gespraeche), "")


class ImGespraech(Basis):
    def setUp(self):
        super().setUp()
        self.lia = lia_anlegen(Path(self.tmp.name))

    def test_erste_nachricht_mit_uebersicht_dann_nur_neues(self):
        g = sch.gespraech_anlegen("", REIHE, ordner=self.daten)
        sch.nachricht(g, "Hast du die Kriterien für eine gute Reihe?", ordner=self.daten)
        fake = Fake("Ja.", "Weiter.", "Noch.")
        self.abarbeiten(fake)
        p1 = fake.aufrufe[0]
        self.assertIn("## Lias Wissen", p1["prompt"])
        self.assertIn(str(self.lia / "unterricht/data/wissen/text/Kriterien_gute_Unterrichtseinheit.txt"),
                      p1["prompt"])
        self.assertLess(p1["prompt"].index("## Lias Wissen"), p1["prompt"].index("Lias Nachricht:"))
        lese = [str(o) for o in p1["lese_ordner"]]
        self.assertIn(str((self.lia / "unterricht").resolve()), lese)
        self.assertIn(str(ga.ordner_von(self.daten).resolve()), lese)
        self.assertNotIn(str((self.lia / "chat").resolve()), lese)
        self.assertTrue((ga.dateien_ordner(g, self.daten) / gespraechlauf.KARTE).exists())
        # fortgesetzt, nichts Neues: keine Übersicht
        sch.nachricht(g, "Und weiter?", ordner=self.daten)
        self.abarbeiten(fake)
        p2 = fake.aufrufe[1]
        self.assertFalse(p2["neu"])
        self.assertNotIn("Lias Wissen", p2["prompt"])
        self.assertNotIn("Neu in Lias Ablage", p2["prompt"])
        # neue Datei: nur sie geht mit, unter ihrer Überschrift
        neu = self.lia / "examen" / "data" / "reihe" / "runde-2" / "bogen.md"
        neu.parent.mkdir(parents=True)
        neu.write_text("Bogen")
        os.utime(neu, (time.time() + 10,) * 2)
        sch.nachricht(g, "Und jetzt?", ordner=self.daten)
        self.abarbeiten(fake)
        p3 = fake.aufrufe[2]
        self.assertIn("Neu in Lias Ablage", p3["prompt"])
        self.assertIn("runde-2/: bogen.md", p3["prompt"])
        self.assertIn("### Weitere Dateien", p3["prompt"])
        self.assertNotIn("Kriterien_gute", p3["prompt"])

    def test_verlorene_sitzung_bekommt_wieder_alles(self):
        g = sch.gespraech_anlegen("", None, ordner=self.daten)
        sch.nachricht(g, "Eins", ordner=self.daten)
        fake = Fake("A.")
        self.abarbeiten(fake)
        for p in self.sitzungen.iterdir():
            p.unlink()
        sch.nachricht(g, "Zwei", ordner=self.daten)
        self.abarbeiten(fake)
        self.assertTrue(fake.aufrufe[1]["neu"])
        self.assertIn("## Lias Wissen", fake.aufrufe[1]["prompt"])


class Grenzen(unittest.TestCase):
    def test_lauf_einstellungen_mit_wissen(self):
        cfg = {"werkzeuge": {}, "lauf": {}, "webfetch": {}}
        c = gespraechlauf.lauf_einstellungen(False, False, 0, cfg, wissen_an=True)
        self.assertEqual(c["werkzeuge"]["chat"], ["Read"])
        self.assertEqual((c["lauf"]["max_schritte"], c["lauf"]["max_minuten"]), (15, 6))
        c = gespraechlauf.lauf_einstellungen(False, False, 0, cfg, sonder=True, wissen_an=True)
        self.assertEqual((c["werkzeuge"]["chat"], c["lauf"]["max_schritte"]), ([""], 3))

    def test_claude_gespraech_reicht_ordner_durch(self):
        aufrufe = []
        alt = gespraechlauf.claude_lauf.laufen
        gespraechlauf.claude_lauf.laufen = lambda *a, **kw: aufrufe.append(kw)
        try:
            cfg = {"werkzeuge": {}, "lauf": {}, "webfetch": {}}
            alt_lade = gespraechlauf.einstellungen.lade
            gespraechlauf.einstellungen.lade = lambda: cfg
            try:
                gespraechlauf.claude_gespraech("p", gruendlich=False, kennung="k", lese_ordner=[Path("/a"), Path("/b")])
                gespraechlauf.claude_gespraech("p", gruendlich=False, kennung="k", lese_ordner=[Path("/a")])
            finally:
                gespraechlauf.einstellungen.lade = alt_lade
        finally:
            gespraechlauf.claude_lauf.laufen = alt
        self.assertEqual(aufrufe[0]["lese_ordner"], [Path("/a"), Path("/b")])
        self.assertEqual(aufrufe[0]["cfg"]["lauf"]["max_schritte"], 15)
        self.assertEqual(aufrufe[1]["cfg"]["lauf"]["max_schritte"], 3)


if __name__ == "__main__":
    unittest.main()
