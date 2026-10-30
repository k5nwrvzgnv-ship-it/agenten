import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import agent
import nachbesserung
import stueck
from tests.test_runde import antworten, renderer_attrappe
from tests.test_stueck import TEXT

agent.logger.disabled = True  # Tests sollen nicht ins echte logs/ schreiben
HIER = Path(__file__).resolve().parents[1]
V = tomllib.loads((HIER / "theater.toml").read_text(encoding="utf-8"))
PROFIL = tomllib.loads((HIER / "profil.toml").read_text(encoding="utf-8"))
RUNDE = "runde-20261029-140740"
GUT = {"art": "antwort", "kern": "Die Fassung dauert etwa 37 Minuten.",
       "punkte": ["Etwa eine Minute ist Text aus dem Original.", "Der Rest sind eigene Szenen und Spiel."],
       "pruefen": ""}


def bewertung(stufe: str) -> dict:
    return {"kriterien": [{"id": k["id"], "stufe": stufe, "beleg": "Beleg", "verbesserung": "Besser"}
                          for k in V["kriterium"]], "staerken": ["Chor"], "wichtigste_aenderungen": ["Mehr Fallhöhe"]}


def auftrag(aid="20261030-111155-theater-5d88d5", bezug="20261029-150107-theater-0baec0",
            text="Nachbesserung zu deinem Ergebnis: Wie lange dauert die Fassung?"):
    return {"id": aid, "agent": "theater", "text": text, "bezug": bezug}


class Claude:
    """Schreibt der Reihe nach die vorgegebenen Dateien in den Ordner des Auftrags (je Lauf ein dict Name -> Daten)."""

    def __init__(self, hier: Path, aid: str, laeufe: list[dict]):
        self.ordner = hier / "data" / RUNDE / f"nachbesserung-{aid}"
        self.laeufe, self.prompts = list(laeufe), []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append((prompt, sitzung))
        for name, daten in self.laeufe.pop(0).items():
            (self.ordner / name).write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
        return SimpleNamespace(usd=0.25, tokens=1, dauer_s=1, ok=True, sitzung="s1")


class Grundlage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.runde = self.tmp / "data" / RUNDE
        (self.runde / "kontext").mkdir(parents=True)
        (self.runde / "kontext" / "vorgaben.md").write_text("Vorgaben", encoding="utf-8")
        self.einheiten = stueck.zerlegen(TEXT)
        (self.runde / "einheiten.json").write_text(json.dumps(stueck.als_dicts(self.einheiten)), encoding="utf-8")
        self.ablauf = antworten(self.einheiten, [m["id"] for m in V["muss"]])["ablauf.json"]
        (self.runde / "ablauf.json").write_text(json.dumps(self.ablauf), encoding="utf-8")
        (self.runde / "szenenkarte.json").write_text("{}", encoding="utf-8")
        (self.runde / "an_lia.json").write_text(json.dumps({"auftrag": "20261029-150107-theater-0baec0"}),
                                                encoding="utf-8")
        self.gebaut = []

    def umgebung(self, claude):
        return nachbesserung.Umgebung(hier=self.tmp, vorgaben=V, profil=PROFIL, laufen=claude,
                                      renderer_bauen=renderer_attrappe(self.gebaut))


class RundeFinden(Grundlage):
    def test_ueber_zustellung_an_lia(self):
        self.assertEqual(nachbesserung.runde_finden(auftrag(), self.tmp / "data"), self.runde)

    def test_ueber_frueheren_auftrag(self):
        (self.runde / "nachbesserung-20261030-120000-theater-aaaaaa").mkdir()
        a = auftrag(bezug="20261030-120000-theater-aaaaaa")
        self.assertEqual(nachbesserung.runde_finden(a, self.tmp / "data"), self.runde)

    def test_ueber_text(self):
        a = auftrag(bezug="20261030-120000-theater-bbbbbb", text=f"Frage zur Runde {RUNDE}")
        self.assertEqual(nachbesserung.runde_finden(a, self.tmp / "data"), self.runde)

    def test_keine_runde(self):
        a = auftrag(bezug=None, text="Frage ohne Runde (runde-20990101-000000)")
        with self.assertRaises(nachbesserung.NachbesserungFehler):
            nachbesserung.runde_finden(a, self.tmp / "data")

    def test_ablauf_nach_pruefung_und_nach_frueherem_auftrag(self):
        self.assertEqual(nachbesserung.ablauf_finden(self.runde, None), self.runde / "ablauf.json")
        (self.runde / "ergebnis.json").write_text(json.dumps({"ablauf": "ablauf-2.json"}), encoding="utf-8")
        self.assertEqual(nachbesserung.ablauf_finden(self.runde, "x"), self.runde / "ablauf-2.json")
        n = self.runde / "nachbesserung-20261030-120000-theater-aaaaaa"
        n.mkdir()
        (n / "stand.json").write_text(json.dumps({"ablauf": f"{n.name}/ablauf.json"}), encoding="utf-8")
        self.assertEqual(nachbesserung.ablauf_finden(self.runde, "20261030-120000-theater-aaaaaa"), n / "ablauf.json")


class Kennzahlen(Grundlage):
    def test_summen(self):
        text = nachbesserung.kennzahlen(self.ablauf, self.einheiten, V["rahmen"])
        self.assertIn("Spielzeit gesamt: 37 Min", text)
        self.assertIn("(2 von", text)  # zwei Originaleinheiten bleiben
        self.assertIn("Neuer Text: 4 Wörter", text)  # vier Bausteine mit „neu“
        self.assertIn("Spielzeit je Art: gemischt 10 Min, neu 27 Min", text)
        self.assertIn("Teil 0 (", text)


class Antwort(unittest.TestCase):
    def test_pruefen(self):
        self.assertEqual(nachbesserung.antwort_pruefen(GUT), [])
        fehler = nachbesserung.antwort_pruefen({"art": "x", "kern": "", "punkte": ["a"] * 4, "pruefen": "p" * 300})
        self.assertEqual(len(fehler), 4)

    def test_beispiel_haelt_sprachregel(self):
        self.assertEqual(nachbesserung.sprachbefunde(GUT), [])
        self.assertTrue(nachbesserung.sprachbefunde(dict(GUT, kern="Der Agent hat den Auftrag erledigt.")))

    def test_text_und_daten(self):
        a = dict(GUT, pruefen="Passt das so?")
        self.assertEqual(nachbesserung.text_fuer_lia(a).splitlines()[-1], "Passt das so?")
        self.assertEqual(nachbesserung.daten_fuer_lia(a)["pruefen"], "Passt das so?")
        self.assertNotIn("pruefen", nachbesserung.daten_fuer_lia(GUT))


class Bearbeiten(Grundlage):
    def test_frage_beantworten(self):
        a = auftrag()
        claude = Claude(self.tmp, a["id"], [{"antwort.json": GUT}])
        e = nachbesserung.bearbeiten(a, self.umgebung(claude))
        self.assertEqual(len(claude.prompts), 1)
        prompt = claude.prompts[0][0]
        self.assertIn("Wie lange dauert die Fassung?", prompt)
        self.assertIn(f"data/{RUNDE}/ablauf.json", prompt)
        self.assertIn("kennzahlen.md", prompt)
        self.assertIn(f"data/{RUNDE}/kontext/vorgaben.md", prompt)
        self.assertEqual(e.text.splitlines()[0], GUT["kern"])
        self.assertEqual(e.daten["punkte"], GUT["punkte"])
        self.assertEqual((e.dateien, e.laeufe, e.usd, e.sitzung, e.hinweise), ([], 1, 0.25, "s1", []))
        ordner = self.runde / f"nachbesserung-{a['id']}"
        self.assertTrue((ordner / "kennzahlen.md").exists())
        stand = json.loads((ordner / "stand.json").read_text(encoding="utf-8"))
        self.assertEqual(stand["ablauf"], "ablauf.json")

    def test_sprachregel_einmal_nachbessern_dann_trotzdem_senden(self):
        a = auftrag()
        schlecht = dict(GUT, kern="Der Agent hat den Auftrag erledigt.")
        claude = Claude(self.tmp, a["id"], [{"antwort.json": schlecht}, {"antwort.json": schlecht}])
        e = nachbesserung.bearbeiten(a, self.umgebung(claude))
        self.assertEqual(len(claude.prompts), 2)
        self.assertEqual(claude.prompts[1][1], "s1")
        self.assertIn("Sprachregel", claude.prompts[1][0])
        self.assertIn("Sprachregel", e.hinweise[0])
        self.assertEqual(e.text.splitlines()[0], schlecht["kern"])

    def test_harter_fehler_nach_nachbesserung(self):
        a = auftrag()
        claude = Claude(self.tmp, a["id"], [{"antwort.json": {"art": "?"}}, {"antwort.json": {"art": "?"}}])
        with self.assertRaises(nachbesserung.NachbesserungFehler):
            nachbesserung.bearbeiten(a, self.umgebung(claude))

    def test_ueberarbeitung_und_folgeauftrag(self):
        a = auftrag()
        neu = dict(self.ablauf, aenderungen=["Chor am Schluss kürzer, weil Lia es wollte"])
        neu["bausteine"] = [dict(b) for b in neu["bausteine"]]
        neu["bausteine"][3]["titel"] = "Neuer Schluss"
        ueberarbeitet = dict(GUT, art="ueberarbeitung", kern="Ich habe den Schluss gekürzt.")
        # erster Versuch ohne aenderungen: eine Nachbesserung
        claude = Claude(self.tmp, a["id"], [{"antwort.json": ueberarbeitet, "ablauf.json": self.ablauf},
                                            {"antwort.json": ueberarbeitet, "ablauf.json": neu},
                                            {"kritik-1.json": bewertung("gut")}])
        e = nachbesserung.bearbeiten(a, self.umgebung(claude))
        self.assertIn("aenderungen", claude.prompts[1][0])
        self.assertIn("Prüfrunde 1", claude.prompts[2][0])
        self.assertEqual([s for _, s in claude.prompts], [None, "s1", None])  # Prüfer in neuer Sitzung
        self.assertEqual(e.hinweise, [])
        self.assertEqual([d.name for d in e.dateien], list(nachbesserung.DOKUMENTE))
        self.assertEqual([g[0] for g in self.gebaut], list(nachbesserung.DOKUMENTE))
        ordner = self.runde / f"nachbesserung-{a['id']}"
        self.assertIn("Neuer Schluss", (ordner / "spielfassung.txt").read_text(encoding="utf-8"))
        # Folgeauftrag auf dieses Ergebnis arbeitet mit dem neuen Ablauf
        b = auftrag(aid="20261030-130000-theater-cccccc", bezug=a["id"])
        claude = Claude(self.tmp, b["id"], [{"antwort.json": GUT}])
        nachbesserung.bearbeiten(b, self.umgebung(claude))
        self.assertIn(f"{ordner.name}/ablauf.json", claude.prompts[0][0])

    def test_ueberarbeitung_nach_pruefung(self):
        a = auftrag()
        neu = dict(self.ablauf, aenderungen=["Akt 2 mit mehr Publikum"])
        zwei = dict(self.ablauf, aenderungen=["Fallhöhe in Akt 3 gesteigert"])
        ueberarbeitet = dict(GUT, art="ueberarbeitung", kern="Ich habe Akt 2 umgebaut.")
        claude = Claude(self.tmp, a["id"], [{"antwort.json": ueberarbeitet, "ablauf.json": neu},
                                            {"kritik-1.json": bewertung("ansatzweise")},
                                            {"ablauf-2.json": zwei},
                                            {"kritik-2.json": bewertung("gut")}])
        e = nachbesserung.bearbeiten(a, self.umgebung(claude))
        self.assertEqual([s for _, s in claude.prompts], [None, None, "s1", None])  # Autor bleibt in seiner Sitzung
        ordner = self.runde / f"nachbesserung-{a['id']}"
        stand = json.loads((ordner / "stand.json").read_text(encoding="utf-8"))
        self.assertEqual(stand["ablauf"], f"{ordner.name}/ablauf-2.json")
        doc = json.loads((ordner / "fuer-lia" / "2 Ablauf und Varianten.json").read_text(encoding="utf-8"))
        texte = json.dumps(doc, ensure_ascii=False)
        self.assertIn("Akt 2 mit mehr Publikum", texte)  # Lias Änderung
        self.assertIn("Fallhöhe in Akt 3 gesteigert", texte)  # nach der Prüfung
        self.assertIn("einmal überarbeitet", texte)
        self.assertEqual(e.laeufe, 4)

    def test_unter_gut_bleibt_als_hinweis(self):
        a = auftrag()
        neu = dict(self.ablauf, aenderungen=["A"])
        laeufe = [{"antwort.json": dict(GUT, art="ueberarbeitung"), "ablauf.json": neu}]
        for i in range(1, 4):
            laeufe.append({f"kritik-{i}.json": bewertung("ansatzweise")})
            if i < 3:
                laeufe.append({f"ablauf-{i + 1}.json": dict(self.ablauf, aenderungen=[f"Runde {i}"])})
        claude = Claude(self.tmp, a["id"], laeufe)
        e = nachbesserung.bearbeiten(a, self.umgebung(claude))
        self.assertIn("unter „gut“", e.hinweise[0])
        self.assertEqual(len(e.dateien), 2)


class Agent(Grundlage):
    def test_erfolg(self):
        e = nachbesserung.Ergebnis(text="T", daten={"kern": "T"}, sitzung="s1")
        with mock.patch.object(agent.auftraege, "abschliessen") as ab:
            agent.auftrag_bearbeiten(auftrag(), bearbeiten=lambda a, u: e, umgebung=lambda aid: None)
        ab.assert_called_once_with(auftrag()["id"], "T", sitzung="s1", dateien=[], daten={"kern": "T"})

    def test_fehler_lia_kurz_jan_ursache(self):
        def kaputt(a, u):
            raise nachbesserung.NachbesserungFehler("keine Runde")
        gemeldet = []
        with mock.patch.object(agent.auftraege, "abschliessen") as ab:
            agent.auftrag_bearbeiten(auftrag(), bearbeiten=kaputt, umgebung=lambda aid: None, melden=gemeldet.append)
        ab.assert_called_once_with(auftrag()["id"], agent.NICHT_GEKLAPPT, status="fehlgeschlagen")
        self.assertIn("keine Runde", gemeldet[0])

    def test_limit(self):
        def voll(a, u):
            raise agent.claude_lauf.LimitErreicht(None)
        gemeldet = []
        with mock.patch.object(agent.auftraege, "abschliessen") as ab:
            agent.auftrag_bearbeiten(auftrag(), bearbeiten=voll, umgebung=lambda aid: None, melden=gemeldet.append)
        self.assertIn("Rechenzeit", ab.call_args.args[1])
        self.assertEqual(len(gemeldet), 1)

    def test_texte_fuer_lia_halten_sprachregel(self):
        for text in (agent.NICHT_GEKLAPPT, agent.LIMIT.format(zeit="14:00 Uhr")):
            self.assertEqual(nachbesserung.sprache.pruefen(text, nachbesserung.sprache.LIA), [], text)


if __name__ == "__main__":
    unittest.main()
