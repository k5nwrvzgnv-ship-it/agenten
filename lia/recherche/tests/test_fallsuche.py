import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import agent
import fallsuche
from agentkit import claude_lauf
from tests.test_faelle import abgleich_eintrag, auswahl, kandidat, leitfrage
from tests.test_webpruefung import DOMAINS, REGISTER, seitentext

CFG = {"webfetch": {"recherche": DOMAINS}}
GUT = {"kandidaten": [kandidat()], "verworfen": [{"titel": "Containern", "grund": "L3", "regeln": ["L3"]}],
       "luecken": []}
FALSCH = {"kandidaten": [kandidat(zitat="stahl vier Räder")], "verworfen": [], "luecken": []}
UNGEPRUEFT = {"kandidaten": [kandidat(titel="Rapper", url="https://instagram.com/p/1")], "verworfen": [],
              "luecken": []}


class Claude:
    """Ersetzt claude_lauf. sammeln: je Fenster eine Liste von Antworten (pro Lauf eine; None = Datei nicht
    anfassen, "fehler" = Zeitlimit). Abgleich und Dossier: gültig, außer abgleich/dossier ist gesetzt."""

    def __init__(self, hier, sammeln, abgleich=None, dossier=None, usd=0.5):
        self.hier, self.sammeln, self.usd, self.prompts = hier, {k: list(v) for k, v in sammeln.items()}, usd, []
        self.abgleich, self.dossier = list(abgleich or []), list(dossier or [])
        self.fenster, self.ids = None, []

    def __call__(self, prompt, sitzung=None, art="anspruchsvoll"):
        self.prompts.append((prompt, sitzung, art))
        pfad = re.search(r"NUR in die Datei (\S+?),|Ergänze die Datei (\S+) |neu nach (\S+?),", prompt)
        pfad = self.hier / next(g for g in pfad.groups() if g)
        if "Suchfenster:" in prompt:
            self.fenster = re.search(r"sammeln-(\w+)\.json", prompt).group(1)
        if "abgleich.json" in str(pfad):
            self.ids = list(dict.fromkeys(re.findall(r'"id": "(F\d+)"', prompt))) or self.ids
            antwort = self.abgleich.pop(0) if self.abgleich else {"faelle": [abgleich_eintrag(i) for i in self.ids]}
        elif "dossier.json" in str(pfad):
            antwort = self.dossier.pop(0) if self.dossier else {
                "auswahl": [auswahl()], "leitfragen": [leitfrage(rlp=["strafe"])], "rueckfragen": []}
        else:
            antwort = self.sammeln[self.fenster].pop(0)
            if antwort == "fehler":
                raise claude_lauf.Zeitueberschreitung("Lauf nach 15 Minuten abgebrochen")
        if antwort is not None:
            pfad.write_text(json.dumps(antwort), encoding="utf-8")
        return claude_lauf.Ergebnis(text="fertig", sitzung=f"s-{len(self.prompts)}", ok=True, usd=self.usd)


class FallsucheTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.hier)
        (self.hier / "data").mkdir()
        (self.hier / "data/register.json").write_text(json.dumps(
            {"quellen": [dict(REGISTER["liszt"], id="liszt")]}), encoding="utf-8")
        k = self.hier / "kontext"
        k.mkdir()
        dateien = {
            "regelwerk.md": "## L\n- L1 Lerngruppe trifft.\n- L3 Containern meiden.\n## P\n- P3 Konkret.\n",
            "STATUS.md": "## Gelernte Regeln\n- 24.10.: Keine Tötung.\n",
            "leitfaden.md": "LEITFADEN",
            "reihen.toml": '[[reihe]]\nklasse = "8"\ntitel = "Straftheorien"\nbisherige_reihen = '
                           '["Klasse 7, Lüge: Sollte ich lügen, um einen Freund zu schützen?"]\n',
            "examen.toml": "[pruefung]\n", "vorbild.md": "VORBILD", "rubrik.toml": "RUBRIK",
            "rlp.toml": '[[stelle]]\nid = "strafe"\nseite = 24\ntext = "Strafe"\n',
        }
        for name, text in dateien.items():
            (k / name).write_text(text, encoding="utf-8")
        self.pfade = fallsuche.Pfade(regelwerk=k / "regelwerk.md", status_unterricht=k / "STATUS.md",
                                     leitfaden=k / "leitfaden.md", reihen=k / "reihen.toml",
                                     examen=k / "examen.toml", vorbild=k / "vorbild.md", rubrik=k / "rubrik.toml",
                                     rlp=k / "rlp.toml")
        self.meldungen, self.gebaut = [], []

    def ausfuehren(self, sammeln, fenster=("nachrichten", "urteile"), kosten=None, weiter=None, nur_dossier=False,
                   **mehr):
        self.claude = Claude(self.hier, sammeln, **mehr)
        return fallsuche.ausfuehren(hier=self.hier, fenster=list(fenster), weiter=weiter, nur_dossier=nur_dossier,
                                    laufen=self.claude,
                                    seitentext=seitentext, renderer_bauen=lambda b, z: self.gebaut.append((b, z)),
                                    melden=self.meldungen.append, cfg=CFG, kosten=kosten, pfade=self.pfade)

    def test_ganzer_ablauf(self):
        ordner = self.ausfuehren({"nachrichten": [GUT, None], "urteile": [UNGEPRUEFT, None]})
        arten = [p[0].split("\n")[0][:30] for p in self.claude.prompts]
        self.assertEqual(len(arten), 6)  # je Fenster Suche + weiter, Abgleich, Dossier
        self.assertEqual(self.claude.prompts[1][1], "s-1")  # weitersuchen in derselben Sitzung
        self.assertIsNone(self.claude.prompts[4][1])  # Abgleich: neue Sitzung
        self.assertIsNone(self.claude.prompts[5][1])  # Dossier: neue Sitzung
        erster = self.claude.prompts[0][0]
        for teil in ("L3 Containern meiden", "GR1: 24.10.: Keine Tötung", "Straftheorien", "taz.de"):
            self.assertIn(teil, erster)
        abgleich = self.claude.prompts[4][0]
        for teil in ("LEITFADEN", "VORBILD", "RUBRIK", '"id": "F01"', '"id": "F02"'):
            self.assertIn(teil, abgleich)
        dossier = self.claude.prompts[5][0]
        for teil in ("liszt:41", "Sollte ich lügen, um einen Freund zu schützen?", '"id": "V01"', "Containern"):
            self.assertIn(teil, dossier)
        e = json.loads((ordner / "ergebnis.json").read_text())
        self.assertEqual(e["zahlen"], {"fenster": 2, "faelle": 2, "belegt": 1, "ungeprueft": 1, "verworfen": 1,
                                       "nicht_belegt": 0})
        self.assertEqual(e["probleme"], [])
        self.assertEqual(self.gebaut[0][1], ordner / "Fallsuche Strafe.docx")
        self.assertIn("Muss jeder Dieb ins Gefängnis?", json.dumps(self.gebaut[0][0], ensure_ascii=False))
        self.assertIn("2 Fälle aus 2 Fenstern (1 mit geprüftem Zitat), 1 ausgewählt, 1 Leitfragen", self.meldungen[-1])
        self.assertIn("Kosten 3.00 USD in 6 Läufen", self.meldungen[-1])

    def test_nachbesserung_beim_sammeln(self):
        ordner = self.ausfuehren({"nachrichten": [FALSCH, None, GUT]}, fenster=["nachrichten"])
        self.assertIn("stahl vier Räder", self.claude.prompts[2][0])
        self.assertEqual(self.claude.prompts[2][1], "s-2")
        d = json.loads((ordner / "sammeln-nachrichten-geprueft.json").read_text())
        self.assertEqual(d["kandidaten"][0]["status"], "belegt")

    def test_fenster_scheitert_andere_laufen_weiter(self):
        self.ausfuehren({"nachrichten": ["fehler"], "urteile": [GUT, None]})
        self.assertIn("Fenster nachrichten gescheitert", self.meldungen[-1])
        self.assertIn("Fallsuche fertig", self.meldungen[-1])

    def test_nichts_gefunden_bricht_ab_und_meldet(self):
        with self.assertRaises(fallsuche.faelle.FallFehler):
            self.ausfuehren({"nachrichten": [FALSCH, None, FALSCH]}, fenster=["nachrichten"])
        self.assertIn("kein Fall mit Quelle", self.meldungen[-1])
        self.assertIn("--weiter", self.meldungen[-1])

    def test_reserve_fuer_abgleich_und_dossier(self):
        kosten = agent.Kosten(grenze=fallsuche.RESERVE_USD + fallsuche.LAUF_USD + 0.4)
        self.ausfuehren({"nachrichten": [GUT, None], "urteile": [GUT, None]}, kosten=kosten)
        # Erstes Fenster ohne weitersuchen (Budget), zweites ausgelassen, Abgleich und Dossier laufen
        self.assertEqual(len(self.claude.prompts), 3)
        self.assertIn("Fenster urteile ausgelassen", self.meldungen[-1])

    def test_teurer_lauf_frisst_reserve_nicht(self):
        # Wie am 27.10.: Ein Suchlauf kostet viel; der nächste startet nur, wenn LAUF_USD und Reserve frei bleiben
        kosten = agent.Kosten(grenze=15.0)
        self.ausfuehren({"nachrichten": [GUT, None], "urteile": [GUT, None]}, kosten=kosten, usd=4.5)
        # nachrichten (4,5) und weitersuchen (9,0 + 5 > 12: danach kein Suchlauf mehr), Abgleich, Dossier
        self.assertEqual(len(self.claude.prompts), 4)
        self.assertIn("Fenster urteile ausgelassen", self.meldungen[-1])
        self.assertIn("Fallsuche fertig", self.meldungen[-1])

    def test_abgleich_nachbesserung(self):
        kaputt = {"faelle": [abgleich_eintrag("F01", gesamt="super")]}
        ordner = self.ausfuehren({"nachrichten": [GUT, None]}, fenster=["nachrichten"], abgleich=[kaputt])
        self.assertIn("gesamt muss", self.claude.prompts[3][0])
        self.assertTrue((ordner / "ergebnis.json").exists())

    def test_dossier_bleibt_kaputt(self):
        kaputt = {"auswahl": [], "leitfragen": []}
        with self.assertRaises(fallsuche.faelle.FallFehler):
            self.ausfuehren({"nachrichten": [GUT, None]}, fenster=["nachrichten"], dossier=[kaputt, kaputt])
        self.assertIn("Dossier ohne gültige", self.meldungen[-1])

    def test_weiter_uebernimmt_fertige_fenster(self):
        with self.assertRaises(fallsuche.faelle.FallFehler):
            self.ausfuehren({"nachrichten": [GUT, None]}, fenster=["nachrichten"],
                            dossier=[{"auswahl": []}, {"auswahl": []}])
        ordner = next((self.hier / "data/fallsuche").iterdir())
        self.ausfuehren({}, fenster=["nachrichten"], weiter=ordner)
        self.assertEqual(len(self.claude.prompts), 2)  # nur Abgleich und Dossier
        self.assertTrue((ordner / "ergebnis.json").exists())

    def test_weiter_wiederholt_bezahlte_suche_nicht(self):
        # Wie am 27.10.: Suche bezahlt, dann Absturz bei der Belegprüfung
        def kaputt(url):
            raise RuntimeError("Absturz")
        self.claude = Claude(self.hier, {"nachrichten": [GUT, None]})
        with self.assertRaises(RuntimeError):
            fallsuche.ausfuehren(hier=self.hier, fenster=["nachrichten"], laufen=self.claude, seitentext=kaputt,
                                 renderer_bauen=lambda b, z: None, melden=self.meldungen.append, cfg=CFG,
                                 pfade=self.pfade)
        ordner = next((self.hier / "data/fallsuche").iterdir())
        self.ausfuehren({}, fenster=["nachrichten"], weiter=ordner)
        self.assertEqual(len(self.claude.prompts), 2)  # nur Abgleich und Dossier, keine neue Suche
        self.assertIn("1 mit geprüftem Zitat", self.meldungen[-1])

    def test_nur_dossier(self):
        ordner = self.ausfuehren({"nachrichten": [GUT, None]}, fenster=["nachrichten"])
        self.ausfuehren({}, weiter=ordner, nur_dossier=True)
        self.assertEqual(len(self.claude.prompts), 1)  # nur das Dossier, neue Sitzung
        self.assertIsNone(self.claude.prompts[0][1])
        self.assertIn("1 ausgewählt", self.meldungen[-1])

    def test_main_prueft_fenster(self):
        self.assertEqual(fallsuche.main(["fallsuche.py", "--fenster", "nachrichten,quatsch"]), 2)


if __name__ == "__main__":
    unittest.main()
