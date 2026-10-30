import json
import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import agent
import nachbesserung
import neuauftrag
import runde
import stueck
import wunsch
from agentkit import sprache
from tests.test_runde import Claude, aufbauen, renderer_attrappe

agent.logger.disabled = True
runde.logger.disabled = True
HIER = Path(__file__).resolve().parents[1]
V = tomllib.loads((HIER / "theater.toml").read_text(encoding="utf-8"))
PROFIL = tomllib.loads((HIER / "profil.toml").read_text(encoding="utf-8"))
SPIELFASSUNG = """Spielfassung: Der nackte Wahnsinn
Länge: 35–40 Minuten
Spieler*innen: 16
Was bleiben muss: die Sardinen
und der Kaktus
Reihe: ds-kurs-12"""
SZENE = "Szenenaufgabe: Türen-Chaos\nMethode: Slow Motion\nSzene: B02\nMaterial: Sardinenteller"


def a(text, aid="20261030-160000-theater-abcdef", **kw):
    return {"id": aid, "agent": "theater", "text": text, "quelle": "portal-theater", **kw}


class Wunsch(unittest.TestCase):
    def test_art(self):
        self.assertEqual(wunsch.art(a(SPIELFASSUNG)), "spielfassung")
        self.assertEqual(wunsch.art(a("  szenenaufgabe: x")), "szenenaufgabe")
        self.assertIsNone(wunsch.art({"text": "Nachbesserung zu deinem Ergebnis: kürzer", "quelle": "feedback"}))
        self.assertIsNone(wunsch.art(a("Kürzer bitte", bezug="20261030-150000-theater-aaaaaa")))
        with self.assertRaises(wunsch.WunschFehler):
            wunsch.art(a("Mach was"))

    def test_angaben(self):
        g = wunsch.spielfassung_angaben(SPIELFASSUNG)
        self.assertEqual((g["stueck"], g["minuten_min"], g["minuten_max"], g["spieler"]),
                         ("Der nackte Wahnsinn", 35, 40, 16))
        self.assertEqual(g["bleiben"], "die Sardinen\nund der Kaktus")

    def test_angaben_fehlen_und_einzelwert(self):
        g = wunsch.spielfassung_angaben("Spielfassung:")
        self.assertEqual((g["stueck"], g["minuten_min"], g["spieler"], g["bleiben"]), ("", None, None, None))
        g = wunsch.spielfassung_angaben("Spielfassung: Noises Off\nDauer: 30 Min")
        self.assertEqual((g["minuten_min"], g["minuten_max"]), (28, 32))

    def test_unplausibel(self):
        for zeile in ("Länge: 300 Minuten", "Länge: lang", "Spieler*innen: viele", "Spieler: 99"):
            with self.assertRaises(wunsch.WunschFehler, msg=zeile):
                wunsch.spielfassung_angaben(f"Spielfassung: x\n{zeile}")

    def test_stueck_passt(self):
        titel = V["stueck"]["titel"]
        for ok in ("", "Der nackte Wahnsinn", "„Der nackte Wahnsinn“ (Frayn)", "nackte wahnsinn", "Noises Off"):
            self.assertTrue(wunsch.stueck_passt(ok, titel), ok)
        self.assertFalse(wunsch.stueck_passt("Romeo und Julia", titel))

    def test_anpassen(self):
        g = wunsch.spielfassung_angaben("Spielfassung:\nLänge: 20–25 Minuten\nSpieler*innen: 12\nWas bleiben muss: Tür")
        v = wunsch.anpassen(V, g)
        self.assertEqual(V["rahmen"]["spieler"], 18)  # Original unverändert
        self.assertEqual((v["rahmen"]["minuten_min"], v["rahmen"]["minuten_max"], v["rahmen"]["spieler"]), (20, 25, 12))
        self.assertEqual([t["minuten"] for t in v["rahmen"]["teile"]], [2.0, 6.0, 6.0, 6.0])  # 3/10 * 45/75
        ensemble = next(k for k in v["kriterium"] if k["id"] == "ensemble")
        self.assertIn("12 SuS", ensemble["name"])
        self.assertNotIn("18", ensemble["frage"] + ensemble["gut"])
        self.assertIn("Tür", v["kriterium"][-1]["frage"])
        self.assertEqual(wunsch.anpassen(V, wunsch.spielfassung_angaben("Spielfassung:")), V)


class Spielfassung(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        aufbauen(self.tmp)
        self.gebaut = []

    def u(self, claude):
        return nachbesserung.Umgebung(hier=self.tmp, vorgaben=V, profil=PROFIL, laufen=claude,
                                      renderer_bauen=renderer_attrappe(self.gebaut))

    def test_ganze_runde_an_lia(self):
        claude = Claude(self.tmp)
        e = neuauftrag.bearbeiten(a(SPIELFASSUNG), self.u(claude))
        ordner = next((self.tmp / "data").glob("runde-*"))
        self.assertEqual([d.name for d in e.dateien], list(runde.DOKUMENTE))
        self.assertEqual(json.loads((ordner / "an_lia.json").read_text())["auftrag"], a(SPIELFASSUNG)["id"])
        vorgaben = (ordner / "kontext" / "vorgaben.md").read_text(encoding="utf-8")
        self.assertIn("16 SuS", vorgaben)
        self.assertIn("und der Kaktus", vorgaben)
        v = json.loads((ordner / "vorgaben.json").read_text(encoding="utf-8"))
        self.assertEqual(v["kriterium"][-1]["id"], "auftrag")
        self.assertTrue(any("die Sardinen" in p for p, _ in claude.prompts if "Rubrik" in p or "auftrag" in p))
        self.assertEqual(e.laeufe, len(claude.prompts))
        self.assertEqual(e.daten["pruefen"], "")
        self.assertIn("Hier ist deine neue Spielfassung.", e.text)
        self.assertIn(f"An Lia geschickt (Auftrag {a(SPIELFASSUNG)['id']})", e.fuer_jan)
        sichtbar = "\n".join([e.daten["kern"], *e.daten["punkte"]])
        self.assertEqual(sprache.pruefen(sichtbar, sprache.LIA), [])
        # Lias Rückmeldung zur neuen Runde findet sie über an_lia.json, mit deren Vorgaben
        self.assertEqual(nachbesserung.runde_finden({"id": "x", "bezug": a(SPIELFASSUNG)["id"]}, self.tmp / "data"),
                         ordner)
        self.assertEqual(runde.vorgaben_der_runde(ordner, V)["rahmen"]["spieler"], 16)

    def test_fortsetzen_behaelt_wunsch(self):
        with self.assertRaises(runde.RundenFehler):
            runde.runde(aufbauen_pfade(self.tmp), laufen=Claude(self.tmp, usd=3.0),
                        renderer_bauen=renderer_attrappe([]), grenze=5.0,
                        wunsch=wunsch.spielfassung_angaben(SPIELFASSUNG))
        ordner = next((self.tmp / "data").glob("runde-*"))
        (ordner / "kontext" / "vorgaben.md").unlink()
        runde.runde(aufbauen_pfade(self.tmp), laufen=Claude(self.tmp), renderer_bauen=renderer_attrappe([]),
                    fortsetzen=ordner.name)
        self.assertIn("und der Kaktus", (ordner / "kontext" / "vorgaben.md").read_text(encoding="utf-8"))

    def test_anderes_stueck_kein_lauf(self):
        claude = Claude(self.tmp)
        with self.assertRaisesRegex(neuauftrag.NeuesStueck, "Romeo"):
            neuauftrag.bearbeiten(a("Spielfassung: Romeo und Julia"), self.u(claude))
        self.assertEqual(claude.prompts, [])

    def test_falsche_laenge_bricht_ab(self):
        # Attrappe liefert 37 Minuten, Lia will 20–25: Ablauf besteht Pythons Prüfung nicht
        with self.assertRaisesRegex(nachbesserung.NachbesserungFehler, "Runde: Ablauf"):
            neuauftrag.bearbeiten(a("Spielfassung:\nLänge: 20–25 Minuten"), self.u(Claude(self.tmp)))


def aufbauen_pfade(tmp: Path) -> runde.Pfade:
    return runde.Pfade(hier=tmp, vorgaben=tmp / "theater.toml", nachricht=tmp / "data" / "vorgaben" / "nachricht.md",
                       texte=tmp / "data" / "text", profil=tmp / "profil.toml")


class Szenenaufgabe(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        aufbauen(self.tmp)
        runde.runde(aufbauen_pfade(self.tmp), laufen=Claude(self.tmp), renderer_bauen=renderer_attrappe([]))
        self.runde = next((self.tmp / "data").glob("runde-*"))
        (self.runde / "an_lia.json").write_text(json.dumps({"auftrag": "20261029-150107-theater-0baec0",
                                                            "zeit": "2026-10-29T15:01:07"}), encoding="utf-8")
        self.einheiten = stueck.aus_dicts(json.loads((self.runde / "einheiten.json").read_text(encoding="utf-8")))
        self.gebaut = []

    def u(self, claude):
        return nachbesserung.Umgebung(hier=self.tmp, vorgaben=V, profil=PROFIL, laufen=claude,
                                      renderer_bauen=renderer_attrappe(self.gebaut))

    def claude(self, antworten_):
        prompts, rest = [], list(antworten_)

        def laufen(prompt, sitzung=None):
            prompts.append((prompt, sitzung))
            pfad = re.search(r"Datei (data/runde-\S+?/aufgabe\.json)", prompt).group(1)
            (self.tmp / pfad).write_text(json.dumps(rest.pop(0), ensure_ascii=False), encoding="utf-8")
            return SimpleNamespace(usd=0.4, tokens=1, dauer_s=1, ok=True, sitzung="s9")
        laufen.prompts = prompts
        return laufen

    def blatt(self, titel="Szenenaufgabe: Türen-Chaos", stellen=None):
        return {"blatt": {"art": "arbeitsblatt", "titel": titel,
                          "bloecke": [{"typ": "anweisung", "text": "Spielt die Szene in Zeitlupe!"}]},
                "text_aus_dem_stueck": stellen if stellen is not None else [{"von": 2, "bis": 3}]}

    def test_arbeitsblatt_mit_originaltext(self):
        claude = self.claude([self.blatt()])
        (self.tmp / "data" / "eingang" / "x").mkdir(parents=True)
        bild = self.tmp / "data" / "eingang" / "x" / "skizze.png"
        bild.write_bytes(b"png")
        e = neuauftrag.bearbeiten(a(SZENE, dateien=["data/eingang/x/skizze.png"]), self.u(claude))
        prompt = claude.prompts[0][0]
        self.assertIn("Slow Motion", prompt)
        self.assertIn("data/eingang/x/skizze.png (Bild", prompt)
        self.assertIn("spielfassung.txt", prompt)
        self.assertIn("B1", prompt)  # Ablauf als Kurzfassung
        self.assertEqual([d.name for d in e.dateien], ["Szenenaufgabe Türen-Chaos.docx"])
        b = json.loads(e.dateien[0].with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(b["bloecke"][1], {"typ": "ueberschrift", "text": "Text aus dem Stück"})
        nach_nr = {x.nr: x for x in self.einheiten}
        self.assertIn(stueck.zeile(nach_nr[2]), b["bloecke"][2]["text"])
        self.assertEqual((e.laeufe, e.usd, e.sitzung), (1, 0.4, "s9"))
        self.assertEqual(sprache.pruefen("\n".join([e.daten["kern"], e.daten["pruefen"]]), sprache.LIA), [])

    def test_nachbesserung_dann_abbruch(self):
        claude = self.claude([self.blatt(stellen=[{"von": 99999, "bis": 1}]), self.blatt(stellen=[{"von": 0}])])
        with self.assertRaisesRegex(nachbesserung.NachbesserungFehler, "noch fehlerhaft"):
            neuauftrag.bearbeiten(a(SZENE), self.u(claude))
        self.assertIn("text_aus_dem_stueck 1", claude.prompts[1][0])
        self.assertEqual(claude.prompts[1][1], "s9")

    def test_zu_viel_text(self):
        self.assertTrue(any("höchstens" in f for f in neuauftrag.aufgabe.szenen_pruefen(
            self.blatt(stellen=[{"von": 1, "bis": 200}]), 2253)))

    def test_rueckmeldung_ueberarbeitet_die_szenenaufgabe(self):
        neuauftrag.bearbeiten(a(SZENE), self.u(self.claude([self.blatt()])))
        claude = self.claude([self.blatt(titel="Szenenaufgabe: Türen-Chaos 2", stellen=[])])
        r = a("Nachbesserung zu deinem Ergebnis: kürzer", aid="20261030-170000-theater-bbbbbb",
              bezug="20261030-160000-theater-abcdef", quelle="feedback")
        e = neuauftrag.bearbeiten(r, self.u(claude))
        self.assertIn("meldet zurück", claude.prompts[0][0])
        self.assertIn("szenenaufgabe-20261030-160000-theater-abcdef/fuer-lia/Szenenaufgabe Türen-Chaos.json",
                      claude.prompts[0][0])
        self.assertEqual(e.dateien[0].parent.parent.name, "szenenaufgabe-20261030-170000-theater-bbbbbb")

    def test_gilt_letzter_echter_stand(self):
        for name, ablauf in (("nachbesserung-20261030-111155-theater-5d88d5", "neu.json"),
                             ("nachbesserung-probe-20261030", "probe.json")):
            (self.runde / name).mkdir()
            (self.runde / name / "stand.json").write_text(json.dumps({"ablauf": ablauf}), encoding="utf-8")
        self.assertEqual(neuauftrag.gilt_in(self.runde), self.runde / "neu.json")

    def test_ohne_zustellung(self):
        (self.runde / "an_lia.json").unlink()
        with self.assertRaisesRegex(nachbesserung.NachbesserungFehler, "Noch keine Runde"):
            neuauftrag.bearbeiten(a(SZENE), self.u(self.claude([])))


class Agent(unittest.TestCase):
    def test_erfolg_meldet_jan(self):
        e = nachbesserung.Ergebnis(text="T", daten={}, fuer_jan="Runde fertig")
        gemeldet = []
        with mock.patch.object(agent.auftraege, "abschliessen"):
            agent.auftrag_bearbeiten(a(SPIELFASSUNG), bearbeiten=lambda x, u: e, umgebung=lambda aid: None,
                                     melden=gemeldet.append)
        self.assertEqual(gemeldet, ["Runde fertig"])

    def test_neues_stueck(self):
        def neu(x, u):
            raise neuauftrag.NeuesStueck("kein Text für Romeo")
        gemeldet = []
        with mock.patch.object(agent.auftraege, "abschliessen") as ab:
            agent.auftrag_bearbeiten(a("Spielfassung: Romeo"), bearbeiten=neu, umgebung=lambda aid: None,
                                     melden=gemeldet.append)
        ab.assert_called_once_with(a("")["id"], neuauftrag.NEUES_STUECK_LIA, status="fehlgeschlagen")
        self.assertIn("Romeo", gemeldet[0])
        self.assertEqual(sprache.pruefen(neuauftrag.NEUES_STUECK_LIA, sprache.LIA), [])

    def test_standard_ist_neuauftrag(self):
        self.assertIs(agent.auftrag_bearbeiten.__defaults__[0], neuauftrag.bearbeiten)


if __name__ == "__main__":
    unittest.main()
