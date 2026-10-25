import gzip
import hashlib
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import agent
import seitenbild
from agentkit import abruf, claude_lauf
from tests.test_abschrift import ANDERE_SEITE, LESUNG, OCR_S2

ID = "scanx"
D = f"https://archive.org/download/{ID}/{ID}"
QUELLEN = f'''[abruf]
allowlist = ["archive.org"]

[[quelle]]
id = "liszt"
art = "primaertext"
autor = "Franz von Liszt"
todesjahr_autor = 1919
herausgeber_entfaellt = "Zeitschriftenaufsatz"
werk = "Zweckgedanke"
ausgabe = "ZStW 3"
scan_id = "{ID}"
druckseiten = [1, 3]
scan_versatz = -1
scan_von_hand = {{ "1" = 10 }}
urls = ["{D}_page_numbers.json", "{D}_hocr_searchtext.txt.gz", "{D}_hocr_pageindex.json.gz"]
'''
SEITE1 = "Der  alte  ©egenfafe  ber  pl)t(ofop^if(^en  Sßeltanfdjauung,  ber  in bem  einen  §raar  eng  begrenzten"
TEXTE = [SEITE1, OCR_S2, ANDERE_SEITE]  # Scan-Seiten n10, n11, n12 = Druckseiten 1, 2, 3


def _dateien():
    text = "".join(TEXTE)
    index, pos = [[0, 0, 0, 0]] * 10, 0
    for t in TEXTE:
        index.append([pos, pos + len(t), 0, 0])
        pos += len(t)
    zahlen = {"pages": [{"leafNum": 12, "pageNumber": "2", "confidence": 100},
                        {"leafNum": 13, "pageNumber": "3", "confidence": 100}]}
    aus = {f"{D}_page_numbers.json": json.dumps(zahlen).encode(),
           f"{D}_hocr_searchtext.txt.gz": gzip.compress(text.encode()),
           f"{D}_hocr_pageindex.json.gz": gzip.compress(json.dumps(index).encode())}
    for n in (10, 11, 12):
        aus[f"https://archive.org/download/{ID}/page/n{n}.jpg"] = f"BILD n{n}".encode()
    return aus


def laden(url, allowlist, cache_dir):
    abruf.pruefen(url, allowlist)
    inhalt = _dateien()[url]
    return abruf.Ergebnis(inhalt, {"url": url, "abgerufen": "2026-10-25T10:00:00+02:00",
                                   "sha256": hashlib.sha256(inhalt).hexdigest(), "content_type": None}, True)


class Claude:
    """Auswahl: eine Stelle auf S. 2. Abschriften: der Reihe nach aus abschriften."""

    def __init__(self, hier, auswahl, abschriften):
        self.hier, self.auswahl, self.abschriften, self.prompts = hier, auswahl, list(abschriften), []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append((prompt, sitzung))
        datei = self.hier / re.search(r"NUR in die Datei (\S+?),", prompt).group(1)
        if "Noch KEIN Zitat" in prompt:
            datei.write_text(json.dumps({"stellen": self.auswahl}), encoding="utf-8")
        else:
            nrn = [int(n) for n in re.findall(r"- Stelle (\d+):", prompt)]
            text = self.abschriften.pop(0)
            datei.write_text(json.dumps({"stellen": [{"nr": n, "zitat": text} for n in nrn]}), encoding="utf-8")
        return claude_lauf.Ergebnis(text="fertig", sitzung=f"s{len(self.prompts)}", ok=True, usd=0.3)


AUSWAHL = [{"seiten": [2], "anfang": "Die Geschichte des", "ende": "verborgen bleiben.",
            "position": "Zweckstrafe", "zweck": "Gegenposition zu Kant."}]


class AblaufTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.hier)
        (self.hier / "quellen.toml").write_text(QUELLEN, encoding="utf-8")
        self.meldungen = []

    def lauf(self, abschriften, auswahl=AUSWAHL):
        self.claude = Claude(self.hier, auswahl, abschriften)
        fehler = agent.lauf(self.hier, laden=laden, melden=self.meldungen.append, jahr=2026,
                            claude=self.claude, reihen=self.hier / "fehlt.toml")
        reg = json.loads((self.hier / "data/register.json").read_text())["quellen"][0]
        return fehler, reg

    def test_zwei_gleiche_abschriften(self):
        fehler, reg = self.lauf([LESUNG, LESUNG])
        self.assertEqual(fehler, [])
        self.assertEqual(reg["gemeinfreiheit"]["status"], "frei")
        self.assertEqual(reg["scan"]["2"], f"https://archive.org/details/{ID}/page/n11")
        s = reg["stellen"][0]
        self.assertEqual((s["seite"], s["zitat"], s["am_scan_pruefen"], s["geprueft"]), (2, LESUNG, True, False))
        self.assertEqual(s["scan_link"], {"2": f"https://archive.org/details/{ID}/page/n11"})
        self.assertEqual(s["pruefung"]["abschriften_gleich"], "2 von 2")
        self.assertGreaterEqual(s["pruefung"]["ocr_aehnlichkeit"], s["pruefung"]["schwelle"])
        # drei Läufe: Auswahl, zwei Abschriften in getrennten Sitzungen ohne OCR
        self.assertEqual(len(self.claude.prompts), 3)
        self.assertTrue(all(p[1] is None for p in self.claude.prompts))
        for prompt, _ in self.claude.prompts[1:]:
            self.assertIn("data/bilder/liszt/s2.jpg", prompt)
            self.assertNotIn("data/text/", prompt)
        self.assertEqual((self.hier / "data/bilder/liszt/s2.jpg").read_bytes(), b"BILD n11")
        self.assertIn("liszt: 1 Stellen vom Scan", self.meldungen[-1])
        self.assertIn("nur 1 Stellen", self.meldungen[-1])
        self.assertIn("Kosten: 0.90 USD in 3 Claude-Läufen", self.meldungen[-1])

    def test_dritte_entscheidet(self):
        abweichend = LESUNG.replace("verstanden", "verstauben")
        _, reg = self.lauf([LESUNG, abweichend, LESUNG])
        self.assertEqual(len(self.claude.prompts), 4)
        self.assertEqual(reg["stellen"][0]["pruefung"]["abschriften_gleich"], "2 von 3")

    def test_alle_ungleich_verworfen(self):
        _, reg = self.lauf([LESUNG, LESUNG.replace("kann", "darf"), LESUNG.replace("kann", "soll")])
        self.assertEqual(reg["stellen"], [])
        self.assertIn("kann / darf", self.meldungen[-1])

    def test_falsche_seite_verworfen(self):
        auswahl = [dict(AUSWAHL[0], seiten=[3])]
        _, reg = self.lauf([LESUNG, LESUNG], auswahl)
        self.assertEqual(reg["stellen"], [])
        self.assertIn("passt nicht zur OCR", self.meldungen[-1])

    def test_unleserlich_kein_dritter_lauf(self):
        _, reg = self.lauf(["Die [?] des Strafrechts " * 5, "Die Geschichte des Strafrechts " * 5])
        self.assertEqual(len(self.claude.prompts), 3)
        self.assertEqual(reg["stellen"], [])

    def test_auswahl_wird_nach_abbruch_wiederverwendet(self):
        class Abbruch(Claude):
            def __call__(self, prompt, sitzung=None):
                if "Noch KEIN Zitat" not in prompt:
                    raise claude_lauf.LimitErreicht(None)
                return super().__call__(prompt, sitzung)

        self.claude = Abbruch(self.hier, AUSWAHL, [])
        fehler = agent.lauf(self.hier, laden=laden, melden=self.meldungen.append, jahr=2026,
                            claude=self.claude, reihen=self.hier / "fehlt.toml")
        self.assertIn("Kontingent", fehler[0])
        _, reg = self.lauf([LESUNG, LESUNG])
        self.assertEqual(len(self.claude.prompts), 2)  # nur die zwei Abschriften, keine neue Auswahl
        self.assertEqual(len(reg["stellen"]), 1)

    def test_abschriften_werden_wiederverwendet(self):
        self.lauf([LESUNG, LESUNG])
        reg = json.loads((self.hier / "data/register.json").read_text())
        del reg["quellen"][0]["kernstellen"]
        reg["quellen"][0]["stellen"] = []
        (self.hier / "data/register.json").write_text(json.dumps(reg))
        _, neu = self.lauf([])
        self.assertEqual(len(self.claude.prompts), 0)  # Auswahl und beide Abschriften aus dem Speicher
        self.assertEqual(len(neu["stellen"]), 1)

    def test_kein_zweiter_versuch(self):
        self.lauf([LESUNG, LESUNG])
        _, reg = self.lauf([])
        self.assertEqual(len(self.claude.prompts), 0)
        self.assertEqual(len(reg["stellen"]), 1)


class AuswahlTest(unittest.TestCase):
    def pruefen(self, stellen):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.json"
            p.write_text(json.dumps({"stellen": stellen}), encoding="utf-8")
            return seitenbild.auswahl_pruefen(p, 1, 47)

    def test_gueltig_und_ungueltig(self):
        gut = dict(AUSWAHL[0])
        stellen = [gut, dict(gut, seiten=[3, 4]), dict(gut, seiten=[3, 5]), dict(gut, seiten=[48]),
                   dict(gut, seiten=[]), dict(gut, anfang=" "), "kaputt"]
        ok, schlecht = self.pruefen(stellen)
        self.assertEqual([s["seiten"] for s in ok], [[2], [3, 4]])
        self.assertEqual([s["nr"] for s in ok], [1, 2])
        self.assertEqual(len(schlecht), 5)

    def test_hoechstens_fuenf(self):
        ok, schlecht = self.pruefen([AUSWAHL[0]] * 7)
        self.assertEqual(len(ok), 5)
        self.assertIn("2 Stellen über 5", schlecht[0])

    def test_datei_fehlt(self):
        with self.assertRaises(seitenbild.SeitenbildFehler):
            seitenbild.auswahl_pruefen(Path("/nicht/da.json"), 1, 2)

    def test_neu_gezaehlt_nach_reihenfolge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text(json.dumps({"stellen": [{"nr": 1, "zitat": "Text"}]}), encoding="utf-8")
            self.assertEqual(seitenbild.abschriften_lesen(p, [2]), {2: "Text"})
            self.assertEqual(seitenbild.abschriften_lesen(p, [2, 3]), {1: "Text"})  # Anzahl passt nicht
            self.assertEqual(seitenbild.abschriften_lesen(p), {1: "Text"})

    def test_laenge(self):
        auswahl = {"seiten": [2], "position": "p", "zweck": "z"}
        stelle, grund = seitenbild.stelle_pruefen(auswahl, ["Kurz.", "Kurz."], {2: OCR_S2}, {"2": "l"})
        self.assertIsNone(stelle)
        self.assertIn("Länge", grund)


if __name__ == "__main__":
    unittest.main()
