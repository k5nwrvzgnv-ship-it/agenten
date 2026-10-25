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
    """Ersetzt claude_lauf. Recherche/Nachbesserung: nächste Antwort aus antworten. Prüflauf: Urteile aus
    traegt (id -> (wert, fehlt)), sonst "ja"; traegt_kaputt schreibt beim ersten Prüflauf Unsinn."""

    def __init__(self, hier, antworten, usd=0.5, ok=True, traegt=None, traegt_kaputt=False):
        self.hier, self.antworten, self.usd, self.ok, self.prompts = hier, list(antworten), usd, ok, []
        self.traegt, self.traegt_kaputt = traegt or {}, traegt_kaputt

    def __call__(self, prompt, sitzung=None, art="anspruchsvoll"):
        self.prompts.append((prompt, sitzung, art))
        pfad = re.search(r"NUR in die Datei (\S+?),|neu nach (\S+?),|VOLLSTÄNDIGE Datei (\S+) neu", prompt)
        pfad = next(g for g in pfad.groups() if g)
        if "Prüfe für jede Aussage" in prompt or "jede id genau einmal" in prompt:
            if self.traegt_kaputt:
                self.traegt_kaputt = False
                teil = prompt.split("AUSSAGEN (JSON):")[-1].split("Schreibe NUR")[0]
                self.ids = list(dict.fromkeys(re.findall(r'"id": "(a\d+-\d+)"', teil)))
                (self.hier / pfad).write_text('{"urteile": [{"id": "zz", "traegt": "vielleicht"}]}')
            else:
                teil = prompt.split("AUSSAGEN (JSON):")[-1].split("Schreibe NUR")[0]
                ids = list(dict.fromkeys(re.findall(r'"id": "(a\d+-\d+)"', teil))) or self.ids
                self.ids = ids
                urteile = [{"id": i, "traegt": self.traegt.get(i, ("ja", ""))[0], "fehlt": self.traegt.get(i, ("ja", ""))[1]}
                           for i in ids]
                (self.hier / pfad).write_text(json.dumps({"urteile": urteile}), encoding="utf-8")
        else:
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

    def ausfuehren(self, antworten, anhang=(), **mehr):
        self.claude = Claude(self.hier, antworten, **mehr)
        return webauftrag.ausfuehren(self.auftrag, hier=self.hier, laufen=self.claude, seitentext=seitentext,
                                     renderer_bauen=lambda b, ziel: self.gebaut.append((b, ziel)),
                                     melden=self.meldungen.append, cfg=CFG, anhang=list(anhang),
                                     als_text=lambda p: "TEXT", anhang_wurzel=self.hier)

    def test_alles_bestanden_ohne_nachbesserung(self):
        ordner = self.ausfuehren([GUT])
        self.assertEqual(len(self.claude.prompts), 2)  # Recherche und Prüflauf
        self.assertEqual(self.claude.prompts[1][1:], (None, "routine"))  # neue Sitzung, günstig
        prompt = self.claude.prompts[0][0]
        self.assertIn("Finde reale Fälle.", prompt)
        self.assertIn("liszt:41", prompt)
        self.assertIn("taz.de, youtube.com", prompt)
        self.assertEqual((self.hier / "data/web").resolve(), ordner.parent.resolve())
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["zahlen"]["belegt"], 2)
        self.assertEqual(self.gebaut[0][1], ordner / "Recherche.docx")
        self.assertIn("2 von 2 Aussagen belegt", self.meldungen[-1])
        self.assertIn("Kosten 1.00 USD in 2 Läufen", self.meldungen[-1])
        self.assertIn("2 ja, 0 teilweise, 0 nein", self.meldungen[-1])

    def test_nachbesserung_in_derselben_sitzung(self):
        ordner = self.ausfuehren([FALSCH, GUT])
        self.assertEqual(len(self.claude.prompts), 3)
        self.assertEqual(self.claude.prompts[1][1], "s1")
        self.assertIn("stahl drei Räder", self.claude.prompts[1][0])
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["erste_pruefung"]["durchgefallen"], 1)
        self.assertEqual(d["zahlen"]["durchgefallen"], 0)
        self.assertTrue((ordner / "ergebnis_1.json").exists())
        self.assertIn("erste Prüfung: 0/1/0", self.meldungen[-1])

    def test_nach_nachbesserung_noch_falsch_bleibt_unbelegt(self):
        ordner = self.ausfuehren([FALSCH, FALSCH])
        self.assertEqual(len(self.claude.prompts), 2)  # nur eine Nachbesserung, kein Prüflauf (nichts belegt)
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

    def test_traegt_nein_und_teilweise(self):
        ordner = self.ausfuehren([GUT], traegt={"a0-0": ("nein", "Fahrräder: es waren Roller")})
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["traegt_zahlen"], {"ja": 1, "teilweise": 0, "nein": 1, "nicht_geprueft": 0})
        self.assertEqual(d["zahlen"]["belegt"], 1)  # nein -> unbelegt; Liszt-Aussage ist Register, "ja"
        b = json.dumps(self.gebaut[-1][0], ensure_ascii=False)
        self.assertIn("Zitat trägt die Aussage nicht: Fahrräder: es waren Roller", b)
        self.ausfuehren([GUT], traegt={"a0-0": ("teilweise", "Anzahl drei")})
        self.assertIn("Detail nicht belegt: Anzahl drei", json.dumps(self.gebaut[-1][0], ensure_ascii=False))

    def test_traegt_kaputt_eine_nachbesserung(self):
        ordner = self.ausfuehren([GUT], traegt_kaputt=True)
        self.assertEqual([p[2] for p in self.claude.prompts], ["anspruchsvoll", "routine", "routine"])
        self.assertEqual(json.loads((ordner / "geprueft.json").read_text())["traegt_zahlen"]["ja"], 2)

    def test_anhaenge(self):
        erlaubt = self.hier / "vorbild.md"
        erlaubt.write_text("Vorbild", encoding="utf-8")
        (self.hier / "x.docx").write_bytes(b"docx")
        self.auftrag.write_text(f"AUFGABE\nANHANG: {erlaubt}\nANHANG: /etc/passwd\n", encoding="utf-8")
        ordner = self.ausfuehren([GUT], anhang=[str(self.hier / "x.docx"), str(self.hier / ".env")])
        self.assertEqual(sorted(p.name for p in (ordner / "anhaenge").iterdir()), ["vorbild.md", "x.docx", "x.docx.txt"])
        prompt = self.claude.prompts[0][0]
        self.assertIn(f"data/web/{ordner.name}/anhaenge/vorbild.md", prompt)
        self.assertIn("anhaenge/x.docx.txt", prompt)
        self.assertIn("Abgelehnte Anhänge: /etc/passwd: nicht unter", self.meldungen[-1])
        self.assertIn(".env", self.meldungen[-1])

    def test_nur_traegt_auf_fertigen_auftrag(self):
        ordner = self.ausfuehren([GUT])
        d = json.loads((ordner / "geprueft.json").read_text())
        for k in ("traegt_zahlen",):
            d.pop(k)
        (ordner / "geprueft.json").write_text(json.dumps(d))
        claude = Claude(self.hier, [], traegt={"a0-0": ("teilweise", "Ort")})
        webauftrag.nur_traegt(ordner, hier=self.hier, laufen=claude, melden=self.meldungen.append,
                              renderer_bauen=lambda b, z: self.gebaut.append((b, z)))
        self.assertEqual(len(claude.prompts), 1)
        self.assertTrue((ordner / "geprueft_vor_traegt.json").exists())
        self.assertIn("1 ja, 1 teilweise", self.meldungen[-1])
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            webauftrag.nur_traegt(ordner, hier=self.hier, laufen=claude, melden=self.meldungen.append,
                                  renderer_bauen=lambda b, z: None)

    def test_zwei_auftraege_in_derselben_sekunde(self):
        a, b = self.ausfuehren([GUT]), self.ausfuehren([GUT])
        self.assertNotEqual(a, b)

    def test_id(self):
        self.assertEqual(webauftrag.auftrag_id(Path("Lias Auftrag 1.txt"), datetime(2026, 10, 25, 9, 5, 1)),
                         "20261025-090501-lias-auftrag-1")


if __name__ == "__main__":
    unittest.main()
