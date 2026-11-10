import json
import tempfile
import unittest
from pathlib import Path

import logik

BLATT = {"art": "arbeitsblatt", "titel": "Warum strafen wir?", "bloecke": [
    {"typ": "anweisung", "text": "Lies den Fall."},
    {"typ": "material", "titel": "Fall", "text": "Tom nimmt ein Fahrrad."},
    {"typ": "aufgaben", "aufgaben": [{"text": "Was ist passiert?"}, {"text": "Wie soll Tom bestraft werden?"}]},
]}


class Beschreibung(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.o = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_json_neben_der_datei(self):
        (self.o / "3 Spielfassung.json").write_text("{}")
        (self.o / "beschreibung.json").write_text("{}")
        self.assertEqual(logik.beschreibung_finden(self.o / "3 Spielfassung.docx"), self.o / "3 Spielfassung.json")

    def test_unterricht_haupt_und_zusatz(self):
        for n in ("beschreibung.json", "beschreibung-niveau-1.json", "beschreibung-erwartungshorizont.json"):
            (self.o / n).write_text("{}")
        self.assertEqual(logik.beschreibung_finden(self.o / "Arbeitsblatt Strafe.docx"), self.o / "beschreibung.json")
        self.assertEqual(logik.beschreibung_finden(self.o / "Arbeitsblatt Strafe (Niveau 1).docx"),
                         self.o / "beschreibung-niveau-1.json")
        self.assertEqual(logik.beschreibung_finden(self.o / "Lernerfolgskontrolle X (Erwartungshorizont).docx"),
                         self.o / "beschreibung-erwartungshorizont.json")

    def test_keine(self):
        self.assertIsNone(logik.beschreibung_finden(self.o / "Rollen.docx"))

    def test_profil(self):
        self.assertEqual([logik.profil_agent(a) for a in ("unterricht", "theater", "schnell")],
                         ["unterricht", "theater", "unterricht"])


class Antwort(unittest.TestCase):
    def test_formen(self):
        a = logik.antwort_lesen('```json\n{"aenderungen": [{"loeschen": "bloecke[0]"}], "antwort": "Weg."}\n```')
        self.assertEqual((a["art"], a["antwort"]), ("aenderungen", "Weg."))
        self.assertEqual(logik.antwort_lesen('Hier: {"zu_gross": "Braucht Recherche."}'),
                         {"art": "zu_gross", "grund": "Braucht Recherche."})
        b = logik.antwort_lesen(json.dumps({"beschreibung": BLATT, "antwort": "Neu."}))
        self.assertEqual(b["beschreibung"], BLATT)

    def test_fehler(self):
        for text in ["kein json", "[1]", '{"aenderungen": []}', '{"beschreibung": 3}', '{"x": 1}', "{kaputt}"]:
            with self.subTest(text=text), self.assertRaises(logik.AntwortFehler):
                logik.antwort_lesen(text)


class Aenderungen(unittest.TestCase):
    def test_pfade(self):
        self.assertEqual(logik.pfad_zerlegen("bloecke[2].aufgaben[1].text"), ["bloecke", 2, "aufgaben", 1, "text"])
        for falsch in ["", "[1]", "bloecke..x", "bloecke[a]", "bloecke[1]x", 3, "a.[1]"]:
            with self.subTest(pfad=falsch), self.assertRaises(logik.AenderungFehler):
                logik.pfad_zerlegen(falsch)

    def test_setzen_loeschen_einfuegen_auf_das_original(self):
        neu = logik.aenderungen_anwenden(BLATT, [
            {"loeschen": "bloecke[0]"},
            {"setzen": "bloecke[2].aufgaben[1].text", "wert": "Welche Strafe ist gerecht?"},
            {"einfuegen": "bloecke[2]", "wert": {"typ": "anweisung", "text": "Arbeite allein."}},
            {"einfuegen": "bloecke[3]", "wert": {"typ": "merksatz", "text": "Strafe soll gerecht sein."}},
            {"einfuegen": "bloecke[2].aufgaben[0]", "wert": {"text": "Lies genau."}},
            {"setzen": "titel", "wert": "Strafe"},
        ])
        self.assertEqual(neu["titel"], "Strafe")
        self.assertEqual([b["typ"] for b in neu["bloecke"]], ["material", "anweisung", "aufgaben", "merksatz"])
        self.assertEqual([a["text"] for a in neu["bloecke"][2]["aufgaben"]],
                         ["Lies genau.", "Was ist passiert?", "Welche Strafe ist gerecht?"])
        self.assertEqual(BLATT["bloecke"][0]["text"], "Lies den Fall.")  # Original bleibt

    def test_neues_feld_erlaubt(self):
        neu = logik.aenderungen_anwenden(BLATT, [{"setzen": "nummer", "wert": "3"}])
        self.assertEqual(neu["nummer"], "3")

    def test_alle_fehler_auf_einmal(self):
        with self.assertRaises(logik.AenderungFehler) as f:
            logik.aenderungen_anwenden(BLATT, [
                {"loeschen": "bloecke[9]"}, {"setzen": "bloecke[0].x.y", "wert": 1}, {"einfuegen": "bloecke[5]",
                                                                                     "wert": {}},
                {"loeschen": "titel"}, {"setzen": "titel"}, {"setzen": "titel", "loeschen": "titel"}, "x"])
        text = str(f.exception)
        for nr in range(7):
            self.assertIn(f"aenderungen[{nr}]", text)


class Texte(unittest.TestCase):
    def test_uebersicht(self):
        u = logik.uebersicht(BLATT)
        self.assertIn("bloecke[1] (material): Fall", u)
        self.assertIn("  bloecke[2].aufgaben[1]: Wie soll Tom bestraft werden?", u)

    def test_format_abschnitte(self):
        md = "# F\nEinleitung\n## Allgemein\nA\n## Arbeitsblatt (docx)\nB\n## Folien\nC\n"
        self.assertEqual(logik.format_abschnitte(md, ["arbeitsblatt"]), "# F\nEinleitung\n## Allgemein\nA\n"
                                                                         "## Arbeitsblatt (docx)\nB")
        with self.assertRaises(ValueError):
            logik.format_abschnitte(md, ["arbeitsmappe"])

    def test_echte_format_md_hat_alle_abschnitte(self):
        md = (Path(logik.__file__).resolve().parents[2] / "shared" / "renderer" / "FORMAT.md").read_text("utf-8")
        text = logik.format_abschnitte(md, list(logik.ABSCHNITT))
        self.assertIn("## Arbeitsmappe", text)

    def test_prompt_aenderung(self):
        p = logik.prompt_aenderung("Aufgabe 2 einfacher", BLATT, "FORMAT", ["Kurz."], "Blatt.docx", 2)
        for teil in ["„Blatt.docx“, Seite 2", "Aufgabe 2 einfacher", "bloecke[2] (aufgaben)", "- Kurz.", "zu_gross"]:
            self.assertIn(teil, p)

    def test_prompt_dokument_und_ort(self):
        ort = {"fach": {"name": "Ethik"}, "klasse": {"name": "8", "lerngruppe": "lebhaft"},
               "reihe": {"titel": "Strafe", "reihenfrage": "Warum strafen wir?"}, "stunde": {"nr": 2, "thema": "Fall"}}
        t = logik.ort_text(ort)
        self.assertEqual(t, "Fach: Ethik\nKlasse: 8\nLerngruppe: lebhaft\nReihe: Strafe\nReihenfrage: Warum strafen wir?"
                            "\nStunde 2: Fall")
        p = logik.prompt_dokument("Checkliste", t, "--- Datei: a.pdf\nx", ["/f/a.jpg"], "FORMAT", [])
        for teil in ["Checkliste", "Reihenfrage", "a.pdf", "/f/a.jpg", "arbeitsmappe"]:
            self.assertIn(teil, p)
        self.assertNotIn("Lias Regeln", p)
        self.assertEqual(logik.ort_text(None), "")

    def test_dateiname_notiz_nachbesserung(self):
        self.assertEqual(logik.dateiname({"art": "arbeitsblatt", "titel": "Checkliste: Wandertag!"}),
                         "Arbeitsblatt Checkliste Wandertag.docx")
        self.assertEqual(logik.dateiname({"art": "arbeitsmappe", "titel": "Gruppen"}), "Tabelle Gruppen.xlsx")
        self.assertEqual(logik.dateiname({"art": "folien", "titel": "Folien zu Kant"}), "Folien zu Kant.pptx")
        self.assertTrue(logik.notiz("x" * 500).startswith("Schnell geändert: "))
        self.assertLessEqual(len(logik.notiz("x" * 500)), logik.MAX_NOTIZ)
        t = logik.nachbesserung_text({"id": "a1", "text": "Blatt zu Kant"}, "B.docx", "Neue Quelle", "Grundlage X.")
        self.assertIn("(Auftrag a1)", t)
        self.assertIn("Zur Datei „B.docx“: Neue Quelle", t)
        self.assertTrue(t.endswith("Grundlage X."))


if __name__ == "__main__":
    unittest.main()
