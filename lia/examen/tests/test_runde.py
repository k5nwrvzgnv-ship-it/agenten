import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import grundlagen
import pruefer
import runde
import skizzen
import versionen

REGISTER = {"quellen": [
    {"id": "kant", "werk": "Kant, MdS", "gemeinfreiheit": {"verwendbar": True},
     "stellen": [{"seite": 333, "zitat": "Selbst wenn sich die bürgerliche Gesellschaft …", "position": "Vergeltung"}]},
    {"id": "liszt", "werk": "Liszt, Zweckgedanke", "gemeinfreiheit": {"verwendbar": True},
     "stellen": [{"seite": 31, "zitat": "Nur die notwendige Strafe ist gerecht.", "am_scan_pruefen": True}]},
    {"id": "gesperrt", "werk": "X", "gemeinfreiheit": {"verwendbar": False},
     "stellen": [{"seite": 1, "zitat": "nicht verwenden"}]},
]}
RLP_IDS = {"strafe_problemfragen", "urteilen_e", "argumentieren_e"}
EXAMEN_OFFEN = {"pruefung": {"stundenzahl": "", "pruefungsstunde_in_reihe": ""}}
runde.logger.disabled = True  # Tests sollen nicht ins echte logs/ schreiben


def stunden(n=8, ps=5):
    persp = ["individuell", "gesellschaftlich", "ideengeschichtlich"]
    return [{"nr": i, "thema": f"Thema {i}", "ziel": "erläutern", "perspektive": persp[i % 3],
             "quellen": ["kant:333"] if i == 2 else [], "pruefungsstunde": i == ps} for i in range(1, n + 1)]


def skizze(k):
    return {"kennung": k, "titel": f"Variante {k}", "grundentscheidung": "Fall zuerst", "reihenfrage": "Warum strafen?",
            "abschlussaufgabe": "Urteil zu einem Fall", "rlp": ["strafe_problemfragen", "urteilen_e"],
            "stunden": stunden(), "differenzierung": "drei Niveaus", "risiken": "zu viel Text",
            "fall": "Tim stiehlt zum dritten Mal. Soll er ins Gefängnis?", "abschlussfall": "Ana fährt schwarz.",
            "material_fehlt": ["Stunde 1: Fall als Audio"]}


GUT = {"annahmen": ["8 Stunden"], "skizzen": [skizze(k) for k in "ABC"]}


def rubrik():
    return grundlagen.rubrik_laden()


def bewertung(k, stufe="gut"):
    r = rubrik()
    return {"kennung": k, "bewertung": [{"kriterium": c["id"], "stufe": stufe, "beleg": "weil"} for c in r["kriterium"]],
            "kolloquiumsfragen": [f"Frage {i}?" for i in range(5)], "staerkste_schwaeche": "Einstieg"}


class SkizzenTest(unittest.TestCase):
    def test_quellen_nur_verwendbare(self):
        q = skizzen.quellen_aus_register(REGISTER)
        self.assertEqual(sorted(q), ["kant:333", "liszt:31"])
        self.assertTrue(q["liszt:31"][0]["am_scan_pruefen"])

    def pruefen(self, daten, examen=EXAMEN_OFFEN):
        return skizzen.pruefen(daten, RLP_IDS, {"kant:333", "liszt:31"}, examen)

    def test_gut(self):
        self.assertEqual(self.pruefen(GUT), [])

    def test_fehler(self):
        faelle = {
            "kennung A, B, C": lambda d: d["skizzen"].pop(),
            "RLP-id 'erfunden'": lambda d: d["skizzen"][0]["rlp"].append("erfunden"),
            "2 bis 4 RLP-ids": lambda d: d["skizzen"][0].update(rlp=["urteilen_e"]),
            "'platon:1' steht nicht im Register": lambda d: d["skizzen"][1]["stunden"][0]["quellen"].append("platon:1"),
            "Perspektive fehlt (ideengeschichtlich)": lambda d: [
                st.update(perspektive="individuell") for st in d["skizzen"][2]["stunden"] if st["perspektive"] == "ideengeschichtlich"],
            "11 Stunden, erwartet 8 bis 10": lambda d: d["skizzen"][0].update(stunden=stunden(11)),
            "nicht fortlaufend": lambda d: d["skizzen"][0]["stunden"][3].update(nr=9),
            "genau eine Stunde": lambda d: d["skizzen"][0]["stunden"][0].update(pruefungsstunde=True),
            "reihenfrage fehlt": lambda d: d["skizzen"][0].update(reihenfrage=" "),
            "annahmen fehlt": lambda d: d.update(annahmen=[]),
            "eine Seite": lambda d: d["skizzen"][0].update(risiken="x" * 3000),
            "fall fehlt": lambda d: d["skizzen"][0].pop("fall"),
            "abschlussfall hat 601 Zeichen": lambda d: d["skizzen"][0].update(abschlussfall="x" * 601),
            "material_fehlt muss eine Liste": lambda d: d["skizzen"][0].update(material_fehlt="Audio"),
            "Abkürzungen ausschreiben oder nur erlaubte verwenden: AB": lambda d: d["skizzen"][0]["stunden"][0].update(
                thema="AB für SuS", ziel="erläutern (AFB II)"),
        }
        for erwartet, aendern in faelle.items():
            daten = copy.deepcopy(GUT)
            aendern(daten)
            with self.subTest(erwartet):
                self.assertTrue(any(erwartet in f for f in self.pruefen(daten)), self.pruefen(daten))

    def test_feste_stundenzahl_und_pruefungsstunde(self):
        examen = {"pruefung": {"stundenzahl": "8", "pruefungsstunde_in_reihe": "6"}}
        fehler = self.pruefen(GUT, examen)
        self.assertEqual(fehler, [f"Skizze {k}: Prüfungsstunde muss Stunde 6 sein, markiert: [5]" for k in "ABC"])
        daten = copy.deepcopy(GUT)
        daten["annahmen"] = []  # bei fester Stundenzahl nicht nötig
        for s in daten["skizzen"]:
            s["stunden"] = stunden(8, ps=6)
        self.assertEqual(self.pruefen(daten, examen), [])

    def test_darstellen_mit_quellen(self):
        md = skizzen.darstellen(GUT["skizzen"][0], {"strafe_problemfragen": {"abschnitt": "3.3"},
                                                    "urteilen_e": {"stufe": "E"}},
                                skizzen.quellen_aus_register(REGISTER))
        self.assertIn("## Skizze A: Variante A", md)
        self.assertIn("**5 (Prüfung)**", md)
        self.assertIn("urteilen_e (E)", md)
        self.assertIn("„Selbst wenn sich die bürgerliche Gesellschaft …“", md)
        self.assertIn("**Fall:** Tim stiehlt", md)
        self.assertIn("- Stunde 1: Fall als Audio", md)

    def test_fremde_kuerzel(self):
        self.assertEqual(skizzen.fremde_kuerzel(["BBB nach AFB III, StGB, AB und UB", "SuS"]), ["AB"])

    def test_kontext_und_prompt(self):
        k = skizzen.kontext(rubrik(), grundlagen.auszug_laden(), {"pruefung": {"bundesland": "Berlin", "termin": ""}},
                            "- titel: Strafe", skizzen.quellen_aus_register(REGISTER), "- Regel", "Leitfaden")
        self.assertIn("- bundesland: Berlin", k)
        self.assertNotIn("termin", k)
        self.assertIn("(OCR-Quelle, Lia prüft am Scan)", k)
        p = skizzen.prompt(k, "/x/skizzen.json", EXAMEN_OFFEN)
        self.assertIn("/x/skizzen.json", p)
        self.assertIn("8 bis 10 Stunden", p)

    def test_antwort_lesen(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "s.json"
            with self.assertRaisesRegex(skizzen.SkizzenFehler, "nicht geschrieben"):
                skizzen.antwort_lesen(pfad)
            pfad.write_text("{kaputt", encoding="utf-8")
            with self.assertRaisesRegex(skizzen.SkizzenFehler, "kein JSON"):
                skizzen.antwort_lesen(pfad)


class PrueferTest(unittest.TestCase):
    def test_gut(self):
        daten = {"skizzen": [bewertung(k) for k in "ABC"]}
        self.assertEqual(pruefer.pruefen(daten, rubrik(), ["A", "B", "C"]), [])

    def test_fehler(self):
        faelle = {
            "Kriterien fehlen": lambda d: d["skizzen"][0]["bewertung"].pop(),
            "Kriterien doppelt": lambda d: d["skizzen"][0]["bewertung"].append(dict(d["skizzen"][0]["bewertung"][0])),
            "unbekannte Kriterien": lambda d: d["skizzen"][0]["bewertung"].append({"kriterium": "x", "stufe": "gut", "beleg": "b"}),
            "Stufe 'super'": lambda d: d["skizzen"][1]["bewertung"][0].update(stufe="super"),
            "beleg fehlt": lambda d: d["skizzen"][1]["bewertung"][0].update(beleg=""),
            "genau 5 Kolloquiumsfragen": lambda d: d["skizzen"][2]["kolloquiumsfragen"].pop(),
            "genau diese Skizzen": lambda d: d["skizzen"].pop(),
        }
        for erwartet, aendern in faelle.items():
            daten = {"skizzen": [bewertung(k) for k in "ABC"]}
            aendern(daten)
            with self.subTest(erwartet):
                fehler = pruefer.pruefen(daten, rubrik(), ["A", "B", "C"])
                self.assertTrue(any(erwartet in f for f in fehler), fehler)

    def test_unter_schwelle_und_darstellen(self):
        b = bewertung("A")
        b["bewertung"][0]["stufe"] = "ansatzweise"
        self.assertEqual(pruefer.unter_schwelle(b, rubrik()), [b["bewertung"][0]["kriterium"]])
        md = pruefer.darstellen(b, rubrik())
        self.assertIn("1 von 15 Kriterien", md)
        self.assertIn("**ansatzweise**", md)
        self.assertIn("5. Frage 4?", md)


class VersionenTest(unittest.TestCase):
    def test_sichern(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "reihe"
            (repo / "runde-1").mkdir(parents=True)
            (repo / "runde-1" / "a.md").write_text("eins", encoding="utf-8")
            c1 = versionen.sichern(repo, "Runde 1")
            self.assertEqual(versionen.sichern(repo, "nichts neu"), c1)
            (repo / "runde-1" / "a.md").write_text("zwei", encoding="utf-8")
            c2 = versionen.sichern(repo, "Runde 2")
            self.assertNotEqual(c1, c2)
            log = subprocess.run(["git", "-C", str(repo), "log", "--format=%s|%an"], capture_output=True, text=True).stdout
            self.assertIn("Runde 2|Agent examen", log)
            self.assertIn("Runde 1|Agent examen", log)


class RundeTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        basis = Path(d.name)
        (basis / "register.json").write_text(json.dumps(REGISTER), encoding="utf-8")
        (basis / "reihen.toml").write_text('[[reihe]]\nklasse = "8"\ntitel = "Straftheorien (in Planung)"\n',
                                          encoding="utf-8")
        (basis / "STATUS.md").write_text("## Gelernte Regeln\n- kurz\n## Anderes\nnein\n", encoding="utf-8")
        (basis / "leitfaden.md").write_text("Leitfaden", encoding="utf-8")
        self.pfade = runde.Pfade(hier=basis, repo=basis / "reihe", reihen=basis / "reihen.toml",
                                 regeln=basis / "STATUS.md", leitfaden=basis / "leitfaden.md",
                                 register=basis / "register.json")
        self.prompts = []

    def attrappe(self, skizzen_daten, pruefung_daten, usd=0.5):
        """Claude-Attrappe: schreibt je nach Prompt die erwartete Datei (Listen = Antwort je Versuch)."""
        def laufen(prompt, sitzung=None):
            self.prompts.append((prompt, sitzung))
            if "Grobskizzen" in prompt and "Prüfer" not in prompt or (sitzung == "s-skizzen"):
                pfad, daten, s = self.pfade.repo / "runde-1" / "skizzen.json", skizzen_daten, "s-skizzen"
            else:
                pfad, daten, s = self.pfade.repo / "runde-1" / "pruefung.json", pruefung_daten, "s-pruefer"
            pfad.write_text(json.dumps(daten.pop(0) if isinstance(daten, list) else daten), encoding="utf-8")
            return SimpleNamespace(usd=usd, tokens=1, dauer_s=1.0, ok=True, sitzung=s)
        return laufen

    def test_ganze_runde(self):
        pr = {"skizzen": [bewertung(k) for k in "ABC"]}
        pr["skizzen"][0]["bewertung"][0]["stufe"] = "nicht erkennbar"
        z = runde.runde_eins(self.pfade, self.attrappe(GUT, pr))
        self.assertEqual(len(self.prompts), 2)
        self.assertIn("Variante A", self.prompts[1][0])  # Prüfer sieht die Skizzen
        self.assertIsNone(self.prompts[1][1])  # Prüfer in neuer Sitzung
        self.assertEqual(z["skizzen"][0], ("A", "Variante A", 1))
        self.assertAlmostEqual(z["usd"], 1.0)
        ordner = self.pfade.repo / "runde-1"
        self.assertTrue((ordner / "skizze-C.md").exists())
        self.assertIn("### Prüfung Skizze B", (ordner / "bericht.md").read_text(encoding="utf-8"))
        self.assertIn("Runde 1", runde.melden_text(z))
        self.assertTrue((self.pfade.repo / ".git").exists())

    def test_nachbesserung_dann_gut(self):
        schlecht = copy.deepcopy(GUT)
        schlecht["skizzen"][0]["rlp"] = ["erfunden", "urteilen_e"]
        runde.runde_eins(self.pfade, self.attrappe([schlecht, GUT], {"skizzen": [bewertung(k) for k in "ABC"]}))
        self.assertEqual(self.prompts[1][1], "s-skizzen")  # Nachbesserung in derselben Sitzung
        self.assertIn("erfunden", self.prompts[1][0])

    def test_abbruch_nach_zweitem_fehler(self):
        schlecht = copy.deepcopy(GUT)
        schlecht["skizzen"].pop()
        with self.assertRaisesRegex(runde.RundenFehler, "nach Nachbesserung noch fehlerhaft"):
            runde.runde_eins(self.pfade, self.attrappe([schlecht, copy.deepcopy(schlecht)], {}))

    def test_kostengrenze(self):
        schlecht = copy.deepcopy(GUT)
        schlecht["skizzen"].pop()
        with self.assertRaisesRegex(runde.RundenFehler, "Kostengrenze"):
            runde.runde_eins(self.pfade, self.attrappe([schlecht, GUT], {}, usd=9.0))

    def test_hilfen(self):
        self.assertEqual(runde.abschnitt(self.pfade.regeln, "Gelernte Regeln"), "- kurz")
        self.assertIn("- klasse: 8", runde.reihe_text(self.pfade.reihen, "Straftheorien"))
        with self.assertRaisesRegex(runde.RundenFehler, "genau eine"):
            runde.reihe_text(self.pfade.reihen, "Helfen")

    def test_main_meldet_abbruch(self):
        gemeldet = []

        def kaputt():
            raise runde.RundenFehler("kaputt")

        alt = runde.runde_eins
        runde.runde_eins = kaputt
        try:
            self.assertEqual(runde.main(gemeldet.append), 1)
        finally:
            runde.runde_eins = alt
        self.assertEqual(gemeldet, ["Runde 1 abgebrochen: kaputt"])


if __name__ == "__main__":
    unittest.main()
