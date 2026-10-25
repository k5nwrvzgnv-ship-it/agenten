import json
import re
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import agent
import webauftrag
from agentkit import claude_lauf
from tests.test_webpruefung import DOMAINS, REGISTER, beleg, seitentext

CFG = {"webfetch": {"recherche": DOMAINS}}
GUT = {"abschnitte": [{"titel": "B) Fälle", "aussagen": [
    {"text": "Ein Mann stahl drei Fahrräder.", "belege": [beleg("https://taz.de/fall", "stahl drei Fahrräder")]},
    {"text": "Liszt: Gelegenheitsverbrecher.", "belege": [{"register": "liszt:41"}]}]}],
    "luecken": ["Kein Video gefunden."], "rueckfragen": []}
FALSCH = {"abschnitte": [{"titel": "B) Fälle", "aussagen": [
    {"text": "Ein Mann stahl drei Fahrräder.", "belege": [beleg("https://taz.de/fall", "stahl drei Räder")]}]}]}


class Claude:
    def __init__(self, hier, antworten, usd=0.5, ok=True):
        self.hier, self.antworten, self.usd, self.ok, self.prompts = hier, list(antworten), usd, ok, []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append((prompt, sitzung))
        pfad = re.search(r"(?:NUR in die Datei|neu nach) (\S+?),", prompt).group(1)
        antwort = self.antworten.pop(0)
        if antwort is not None:
            (self.hier / pfad).write_text(json.dumps(antwort), encoding="utf-8")
        return claude_lauf.Ergebnis(text="fertig", sitzung="s1", ok=self.ok, usd=self.usd)


class WebauftragTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.hier)
        (self.hier / "data").mkdir()
        (self.hier / "data/register.json").write_text(json.dumps(
            {"quellen": [dict(REGISTER["liszt"], id="liszt")]}), encoding="utf-8")
        self.auftrag = self.hier / "auftrag.txt"
        self.auftrag.write_text("AUFGABE\nFinde reale Fälle.", encoding="utf-8")
        self.meldungen, self.gebaut = [], []

    def ausfuehren(self, antworten, **mehr):
        self.claude = Claude(self.hier, antworten, **mehr)
        return webauftrag.ausfuehren(self.auftrag, hier=self.hier, laufen=self.claude, seitentext=seitentext,
                                     renderer_bauen=lambda b, ziel: self.gebaut.append((b, ziel)),
                                     melden=self.meldungen.append, cfg=CFG)

    def test_alles_bestanden_ohne_nachbesserung(self):
        ordner = self.ausfuehren([GUT])
        self.assertEqual(len(self.claude.prompts), 1)
        prompt = self.claude.prompts[0][0]
        self.assertIn("Finde reale Fälle.", prompt)
        self.assertIn("liszt:41", prompt)
        self.assertIn("taz.de, youtube.com", prompt)
        self.assertEqual((self.hier / "data/web").resolve(), ordner.parent.resolve())
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["zahlen"]["belegt"], 2)
        self.assertEqual(self.gebaut[0][1], ordner / "Recherche.docx")
        self.assertIn("2 von 2 Aussagen belegt", self.meldungen[-1])
        self.assertIn("Kosten 0.50 USD in 1 Läufen", self.meldungen[-1])

    def test_nachbesserung_in_derselben_sitzung(self):
        ordner = self.ausfuehren([FALSCH, GUT])
        self.assertEqual(len(self.claude.prompts), 2)
        self.assertEqual(self.claude.prompts[1][1], "s1")
        self.assertIn("stahl drei Räder", self.claude.prompts[1][0])
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["erste_pruefung"]["durchgefallen"], 1)
        self.assertEqual(d["zahlen"]["durchgefallen"], 0)
        self.assertTrue((ordner / "ergebnis_1.json").exists())
        self.assertIn("erste Prüfung: 0/1/0", self.meldungen[-1])

    def test_nach_nachbesserung_noch_falsch_bleibt_unbelegt(self):
        ordner = self.ausfuehren([FALSCH, FALSCH])
        self.assertEqual(len(self.claude.prompts), 2)  # nur eine Nachbesserung
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual((d["zahlen"]["belegt"], d["zahlen"]["unbelegt"]), (0, 1))
        self.assertIn("Nicht belegt", json.dumps(self.gebaut[0][0], ensure_ascii=False))

    def test_keine_datei_bricht_ab_und_meldet(self):
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            self.ausfuehren([None])
        self.assertIn("abgebrochen", self.meldungen[-1])

    def test_kostengrenze(self):
        kosten = agent.Kosten(grenze=0.4)
        self.claude = Claude(self.hier, [FALSCH, GUT])
        with self.assertRaises(agent.KostenGrenze):
            webauftrag.ausfuehren(self.auftrag, hier=self.hier, laufen=self.claude, seitentext=seitentext,
                                  renderer_bauen=lambda b, z: None, melden=self.meldungen.append, cfg=CFG,
                                  kosten=kosten)
        self.assertEqual(len(self.claude.prompts), 1)
        self.assertIn("Kostengrenze", self.meldungen[-1])

    def test_lauf_nicht_ok_aber_datei_da(self):
        self.ausfuehren([GUT], ok=False)  # z. B. max_turns erreicht, Datei schon geschrieben
        self.assertIn("2 von 2 Aussagen belegt", self.meldungen[-1])

    def test_id(self):
        self.assertEqual(webauftrag.auftrag_id(Path("Lias Auftrag 1.txt"), datetime(2026, 10, 25, 9, 5, 1)),
                         "20261025-090501-lias-auftrag-1")


if __name__ == "__main__":
    unittest.main()
