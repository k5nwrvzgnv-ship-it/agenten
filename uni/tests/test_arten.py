"""Aufträge mit Art aus dem Arbeitsplatz: arten.py (reine Logik) und agent.art_auftrag (Ablauf, ohne echtes Claude)."""

import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import agent
import arten
import karten
import recherche
from agentkit.claude_lauf import Ergebnis, KeinPlatz
from tests.test_recherche import ECK, LIT, META, REG, seitentext

ID = "20261110-150000-uni-abc123"
PLAN = {"modul": "Holzschutz und Sanierung", "kurse": ["IHS"], "bildquellen": [],
        "themen": [{"id": "faeuletypen", "titel": "Fäuletypen: Braun-, Weiß-, Moderfäule", "score": 5},
                   {"id": "pilze-bestimmen", "titel": "Hausfäulepilze bestimmen", "score": 5},
                   {"id": "chemischer-holzschutz", "titel": "Vorbeugender chemischer Holzschutz", "score": 3}]}
RUBRIK = {"modul": "holzschutz", "punkte": [{"id": "ihs-mechanismen", "titel": "Mechanismen", "themen": ["faeuletypen"]}]}
GEPRUEFT = {"thema": "Fehlstellen optisch erkennen", "fragen": [{"id": "F1"}, {"id": "F2"}],
            "aussagen": [{"text": "YOLO erkennt Äste.", "status": "gesichert"},
                         {"text": "Übertragbar.", "status": "einschaetzung"},
                         {"text": "Norm begrenzt Äste.", "status": "teilweise"}],
            "zahlen": {"gesichert": 1, "teilweise": 1, "verworfen": 0, "unbelegt": 0, "einschaetzung": 1,
                       "quellen_zitierfaehig": 1},
            "luecken": [{"fenster": "daten", "text": "kein Datensatz"}], "widersprueche": []}
TRANSKRIPT = "Prüferin: Erklären Sie die Braunfäule.\nPrüfling: " + "Die Braunfäule baut vor allem die Cellulose ab. " * 6
AUSWERTUNG = {"gesamt": "Solide Grundlagen, Bekämpfung fehlt.",
              "punkte": [{"id": "ihs-mechanismen", "stufe": "teilweise", "begruendung": "Braunfäule erklärt.",
                          "zitate": ["Die Braunfäule baut vor allem die Cellulose ab."]}],
              "luecken": [{"thema": "faeuletypen", "was": "Moderfäule", "zitat": ""}],
              "karten_neu": [], "karten_faellig": []}


def daten_von(abschliessen) -> dict:
    return abschliessen.call_args.kwargs.get("daten")


class TestLogik(unittest.TestCase):
    def test_feld_ohne_gross_klein_und_umlaute(self):
        a = {"felder": {"Thema": " Lamellen ", "Größe": "x"}}
        self.assertEqual(arten.feld(a, "thema"), "Lamellen")
        self.assertEqual(arten.feld(a, "groesse"), "x")
        self.assertEqual(arten.feld(a, "Umfang"), "")
        self.assertEqual(arten.feld({}, "Thema"), "")

    def test_text_mit_feldern_ergaenzt_nur_fehlende(self):
        a = {"text": "Art: Research-Bericht\nThema: Lamellen", "felder": {"Thema": "Lamellen", "Umfang": "kurz"}}
        self.assertEqual(arten.text_mit_feldern(a), "Art: Research-Bericht\nThema: Lamellen\nUmfang: kurz")

    def test_umfang(self):
        self.assertEqual(arten.umfang(""), arten.UMFANG["kurz"])
        self.assertEqual(arten.umfang("Gründlich (bis 50 USD)"), arten.UMFANG["gruendlich"])

    def test_modul(self):
        module = {"holzschutz": "Holzschutz"}
        self.assertEqual(arten.modul_waehlen("", module), "holzschutz")
        self.assertEqual(arten.modul_waehlen("HOLZSCHUTZ", module), "holzschutz")
        with self.assertRaisesRegex(arten.ArtFehler, "Möglich: Holzschutz"):
            arten.modul_waehlen("Statik", module)
        with self.assertRaisesRegex(arten.ArtFehler, "Modul fehlt"):
            arten.modul_waehlen("", {**module, "statik": "Statik"})

    def test_themen_und_score(self):
        self.assertIsNone(arten.themen_waehlen("", PLAN["themen"]))
        self.assertEqual(arten.themen_waehlen("faeuletypen, hausfäulepilze", PLAN["themen"]),
                         {"faeuletypen", "pilze-bestimmen"})
        with self.assertRaisesRegex(arten.ArtFehler, "Statik"):
            arten.themen_waehlen("Statik", PLAN["themen"])
        self.assertEqual((arten.score_waehlen("3 (auch Nebenthemen)"), arten.score_waehlen("")), (3, 4))

    def test_uebung_id(self):
        self.assertEqual(arten.uebung_id(ID), "20261110-150000-abc123")
        with self.assertRaises(arten.ArtFehler):
            arten.uebung_id("kaputt")

    def test_daten_recherche(self):
        d = arten.daten_recherche(GEPRUEFT)
        self.assertEqual(set(d), {"titel", "kern", "punkte", "pruefen"})
        self.assertEqual(d["titel"], "Recherche: Fehlstellen optisch erkennen")
        self.assertEqual(d["punkte"], ["YOLO erkennt Äste."])
        self.assertIn("1 Lücken", d["pruefen"])

    def test_daten_expose(self):
        d = arten.daten_expose({"titel": "Lamellen", "literatur": ["a", "b"], "bloecke": [
            {"typ": "ueberschrift", "text": "Ausgangslage"}, {"typ": "ueberschrift", "text": "Unter", "ebene": 2},
            {"typ": "absatz", "text": "Werk [OFFEN: Name des Werks] und [OFFEN: Zeitplan]"},
            {"typ": "tabelle", "kopf": ["Zeit"], "zeilen": [["[OFFEN: Termin]"]]}]})
        self.assertEqual((d["titel"], d["punkte"]), ("Lamellen", ["Ausgangslage"]))
        self.assertIn("3 offenen Stellen", d["kern"])
        self.assertIn("Name des Werks; Zeitplan; Termin", d["pruefen"])
        self.assertIn("kein gültiges", arten.daten_expose(None)["kern"])

    def test_daten_pruefung(self):
        d = arten.daten_pruefung("Holzschutz", AUSWERTUNG, {"teilweise": "teilweise"}, "Übung 1", False)
        self.assertEqual(d["kern"], AUSWERTUNG["gesamt"])
        self.assertTrue(d["punkte"][0].startswith("ihs-mechanismen: teilweise."))
        self.assertIn("nicht bestätigt", d["pruefen"])


class Ablauf(unittest.TestCase):
    """agent mit HIER im Temp-Ordner, abschliessen als Attrappe, keine Meldungen."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.hier = Path(self._tmp.name)
        self.abschliessen = mock.MagicMock()
        for p in (mock.patch.object(agent, "HIER", self.hier),
                  mock.patch.object(agent.auftraege, "abschliessen", self.abschliessen),
                  mock.patch.object(agent.meldungen, "melden", lambda *a, **kw: "m1")):
            p.start()
            self.addCleanup(p.stop)

    def auftrag(self, art, felder=None, **mehr):
        return {"id": ID, "text": f"Art: {art}", "modus": "erledigen", "quelle": "arbeitsplatz", "ort": "holzschutz",
                "art": art, "felder": felder or {}, **mehr}


class TestWeiche(Ablauf):
    def test_ohne_art_wie_bisher(self):
        a = {"id": ID, "text": "Exposé: Lamellen", "modus": "erledigen", "dateien": ["t.vtt"]}
        with mock.patch.object(agent, "art_auftrag") as art, mock.patch.object(agent, "expose_auftrag") as ex:
            agent.auftrag_bearbeiten(a)
        art.assert_not_called()
        ex.assert_called_once()

    def test_art_ohne_text_deuten(self):
        """Ein Text, der wie eine andere Auftragsart aussieht, zählt nicht: die Art entscheidet."""
        a = self.auftrag("expose", {"Thema": "Lamellen"}, text="Dokument: Transkript IHS", dateien=["t.vtt"])
        with mock.patch.object(agent, "expose_auftrag") as ex, mock.patch.object(agent, "dokument_auftrag") as dok:
            self.assertTrue(agent.auftrag_bearbeiten(a))
        dok.assert_not_called()
        self.assertEqual(ex.call_args.args[0]["text"], "Dokument: Transkript IHS\nThema: Lamellen")

    def test_unbekannte_art_ohne_claude(self):
        with mock.patch.object(agent.claude_lauf, "laufen") as laufen:
            self.assertTrue(agent.art_auftrag(self.auftrag("praesentation")))
        laufen.assert_not_called()
        self.assertEqual(self.abschliessen.call_args.kwargs["status"], "fehlgeschlagen")
        self.assertIn("kann uni nicht", self.abschliessen.call_args.args[1])

    def test_expose_ohne_transkript(self):
        with mock.patch.object(agent, "expose_auftrag") as ex:
            agent.art_auftrag(self.auftrag("expose", {"Thema": "Lamellen"}))
        ex.assert_not_called()
        self.assertIn("Besprechungstranskript", self.abschliessen.call_args.args[1])

    def test_nachbesserung_expose_in_der_kette(self):
        start = self.auftrag("expose", dateien=["t.vtt"])
        a = self.auftrag("expose", id="20261110-160000-uni-def456", sitzung="s1", bezug=ID)
        with mock.patch.object(agent, "expose_auftrag") as ex, mock.patch.object(agent, "ursprung", return_value=start):
            agent.art_auftrag(a)
        self.assertEqual(ex.call_args.args[1], start)

    def test_nachbesserung_anderer_arten_nicht(self):
        with mock.patch.object(agent, "recherche_auftrag") as r:
            agent.art_auftrag(self.auftrag("recherche", sitzung="s1", bezug="x"))
        r.assert_not_called()
        self.assertIn("neuen Auftrag", self.abschliessen.call_args.args[1])

    def test_warten_laesst_auftrag_liegen(self):
        with mock.patch.object(agent, "lernkarten_auftrag", side_effect=KeinPlatz("voll")):
            self.assertFalse(agent.art_auftrag(self.auftrag("lernkarten")))
        self.abschliessen.assert_not_called()


class TestRecherche(Ablauf):
    def test_bericht_mit_daten(self):
        r = self.hier / "data" / "recherchen" / ID / "recherche"
        r.mkdir(parents=True)
        (r / "geprueft.json").write_text(json.dumps(GEPRUEFT))
        (r / "Recherchebericht.md").write_text("# Recherchebericht")
        erg = recherche.Ergebnis(geprueft=r / "geprueft.json", bericht=r / "Recherchebericht.md", usd=3.0,
                                 zeilen=["Recherche: 2 Fragen"])
        with mock.patch.object(agent.recherche, "durchfuehren", return_value=erg) as d:
            agent.recherche_auftrag(self.auftrag("recherche", {"Thema": "Lamellen"}), netz=("s", "m"))
        self.assertEqual(d.call_args.kwargs, {"grenze_usd": 15.0, "zweck": "bericht", "fragen_max": 8,
                                              "fenster_max": 2})
        daten = daten_von(self.abschliessen)
        self.assertEqual(daten["ansicht"], {"recherche": f"data/recherchen/{ID}/recherche"})
        self.assertEqual(self.abschliessen.call_args.kwargs["dateien"], [r / "Recherchebericht.md"])
        self.assertIn("Recherche: 2 Fragen", self.abschliessen.call_args.args[1])

    def test_gescheitert(self):
        with mock.patch.object(agent.recherche, "durchfuehren", side_effect=recherche.RechercheFehler("nichts")):
            agent.recherche_auftrag(self.auftrag("recherche", {"Thema": "x"}), netz=("s", "m"))
        self.assertEqual(self.abschliessen.call_args.kwargs["status"], "fehlgeschlagen")

    def test_durchfuehren_als_bericht(self):
        """Eckpunkte aus Jans Thema, Umfang geprüft (eine Nachbesserung), Prompts ohne Exposé."""
        ordner, aufrufe = self.hier / "data" / "recherchen" / ID, []
        antworten = {"eckpunkte": [ECK, {**ECK, "fragen": ECK["fragen"][:1]}], "literatur": [LIT, LIT],
                     "gegenpruefung": [{"urteile": [{"id": "literatur-1", "traegt": "ja", "fehlt": ""}]}]}

        def laufen(agent_name, hier, prompt, **kw):
            aufrufe.append(prompt)
            name = re.search(r"recherche/([\w/]+)\.json", prompt).group(1)
            if antworten.get(name):
                (ordner / "recherche" / f"{name}.json").write_text(json.dumps(antworten[name].pop(0)))
            return Ergebnis(text="ok", sitzung=f"s{len(aufrufe)}", ok=True, usd=1.0)
        erg = recherche.durchfuehren(self.hier, ordner, {"id": ID, "text": "Thema: Lamellen"}, laufen, seitentext,
                                     lambda d: META, zweck="bericht", fragen_max=8, fenster_max=1)
        self.assertIn("Research-Bericht", aufrufe[0])
        self.assertNotIn("Besprechungstranskript", aufrufe[0])
        self.assertIn("höchstens 1 verschiedene Suchfenster", aufrufe[1])
        self.assertTrue(all("Exposé" not in p for p in aufrufe[2:]))
        self.assertIn("Recherche für einen Research-Bericht", aufrufe[2])
        self.assertEqual(json.loads(erg.geprueft.read_text())["zahlen"]["gesichert"], 1)

    def test_expose_prompts_unveraendert(self):
        self.assertIn("{zweck}", recherche.PROMPT_SUCHE)
        self.assertEqual(recherche.ZWECK["expose"], "ein Exposé")
        self.assertIsNotNone(REG)


class TestLernkarten(Ablauf):
    def setUp(self):
        super().setUp()
        lernen = self.hier / "data" / "lernen"
        (lernen / "holzschutz").mkdir(parents=True)
        (lernen / "holzschutz" / "pruefungsplan.json").write_text(json.dumps(PLAN))
        p = mock.patch.object(karten, "LERNEN", lernen)
        p.start()
        self.addCleanup(p.stop)

    def test_karten_mit_themen(self):
        neu = [{"id": "faeuletypen-1", "frage": "Woran erkennst du Braunfäule?"}]
        erzeugen = mock.MagicMock(return_value={"neu": neu, "gueltig": 1, "fehler": ["Karte 2: Bild fehlt"], "text": "1"})
        agent.lernkarten_auftrag(self.auftrag("lernkarten", {"Modul": "Holzschutz und Sanierung",
                                                             "Themen": "Fäuletypen", "Wichtigkeit ab": "5"}),
                                 erzeugen=erzeugen)
        self.assertEqual(erzeugen.call_args.args, ("holzschutz", 5))
        self.assertEqual(erzeugen.call_args.kwargs["themen"], {"faeuletypen"})
        self.assertEqual(erzeugen.call_args.kwargs["auftrag_id"], ID)
        daten = daten_von(self.abschliessen)
        self.assertEqual(daten["punkte"], ["Woran erkennst du Braunfäule?"])
        self.assertEqual(daten["ansicht"], {"modul": "holzschutz"})
        self.assertIn("1 Entwürfe verworfen", daten["pruefen"])

    def test_unbekanntes_thema(self):
        erzeugen = mock.MagicMock()
        agent.art_auftrag(self.auftrag("lernkarten", {"Themen": "Statik"}))
        erzeugen.assert_not_called()
        self.assertEqual(self.abschliessen.call_args.kwargs["status"], "fehlgeschlagen")

    def test_erzeugen_ergebnis_nur_gewaehlte_themen(self):
        ordner = karten.LERNEN / "holzschutz"
        entwurf = [{"thema": "faeuletypen", "typ": "text", "frage": "F1?", "antwort": "A", "quelle": "S. 1"},
                   {"thema": "pilze-bestimmen", "typ": "text", "frage": "F2?", "antwort": "A", "quelle": "S. 2"}]
        prompts = []

        def laufen(agent_name, hier, prompt, **kw):
            prompts.append((prompt, kw))
            (ordner / "karten_entwurf.json").write_text(json.dumps(entwurf))
            return Ergebnis(text="2 Karten", sitzung="s", ok=True)
        r = karten.erzeugen_ergebnis("holzschutz", 4, themen={"faeuletypen"}, hinweis="nur Fälle", laufen=laufen,
                                     auftrag_id=ID, lernen=karten.LERNEN, hier=self.hier)
        self.assertEqual([k["frage"] for k in r["neu"]], ["F1?"])
        self.assertEqual(len(r["fehler"]), 1)
        self.assertIn("Nur diese Themen (id): faeuletypen", prompts[0][0])
        self.assertIn("Wunsch von Jan: nur Fälle", prompts[0][0])
        self.assertEqual(prompts[0][1]["auftrag_id"], ID)
        # zweiter Lauf mit derselben Karte: nichts neu
        r = karten.erzeugen_ergebnis("holzschutz", 4, themen={"faeuletypen"}, laufen=laufen, lernen=karten.LERNEN,
                                     hier=self.hier)
        self.assertEqual(r["neu"], [])
        self.assertEqual(karten.module(karten.LERNEN), {"holzschutz": "Holzschutz und Sanierung"})


class TestPruefung(Ablauf):
    def setUp(self):
        super().setUp()
        self.modul = self.hier / "data" / "lernen" / "holzschutz"
        self.modul.mkdir(parents=True)
        (self.modul / "rubrik.json").write_text(json.dumps(RUBRIK))
        self.uebung = self.modul / "uebungen" / "20261110-150000-abc123"

    def test_auswertung_ueber_portal_weg(self):
        auswerten = mock.MagicMock(return_value=(json.loads(json.dumps(AUSWERTUNG)), {"usd": 0.3, "laeufe": 1}))
        a = self.auftrag("pruefung", {"Modul": "Holzschutz", "Transkript": TRANSKRIPT})
        agent.pruefung_auftrag(a, auswerten=auswerten, jetzt=datetime(2026, 11, 10, 15, 0))
        self.assertEqual(auswerten.call_args.args, (self.modul, self.uebung))
        self.assertEqual(auswerten.call_args.kwargs, {"warten_s": 0})
        self.assertTrue((self.uebung / "transkript.txt").read_text().startswith("Prüferin:"))
        stand = json.loads((self.uebung / "stand.json").read_text())
        self.assertEqual((stand["stand"], stand["auftrag"], stand["usd"]), ("fertig", ID, 0.3))
        self.assertTrue((self.uebung / "auswertung.json").exists())
        daten = daten_von(self.abschliessen)
        self.assertEqual(daten["ansicht"], {"modul": "holzschutz", "uebung": "20261110-150000-abc123"})
        self.assertEqual(daten["kern"], AUSWERTUNG["gesamt"])
        self.assertIn("Rubrik ist noch nicht bestätigt", daten["pruefen"])
        # neuer Anlauf (z. B. Ergebnis schon da): kein zweiter bezahlter Lauf
        auswerten.reset_mock()
        agent.pruefung_auftrag(a, auswerten=auswerten)
        auswerten.assert_not_called()
        self.assertEqual(daten_von(self.abschliessen)["kern"], AUSWERTUNG["gesamt"])

    def test_transkript_als_datei(self):
        (self.hier / "data" / "eingang").mkdir(parents=True)
        (self.hier / "data" / "eingang" / "t.txt").write_text(TRANSKRIPT)
        auswerten = mock.MagicMock(return_value=(AUSWERTUNG, {}))
        agent.pruefung_auftrag(self.auftrag("pruefung", dateien=["data/eingang/t.txt"]), auswerten=auswerten)
        self.assertIn("Cellulose", (self.uebung / "transkript.txt").read_text())

    def test_transkript_fehlt_oder_zu_kurz(self):
        agent.art_auftrag(self.auftrag("pruefung"))
        self.assertIn("Transkript fehlt", self.abschliessen.call_args.args[1])
        agent.art_auftrag(self.auftrag("pruefung", {"Transkript": "zu kurz"}))
        self.assertIn("zu kurz", self.abschliessen.call_args.args[1])
        self.assertFalse(self.uebung.exists())

    def test_geparkt_wartet_gescheitert_schliesst_ab(self):
        _, aw, _, _ = agent._portal()
        a = self.auftrag("pruefung", {"Transkript": TRANSKRIPT})
        with mock.patch.object(aw, "auswerten", side_effect=aw.Geparkt("Plätze belegt")):
            self.assertFalse(agent.art_auftrag(dict(a)))
        self.abschliessen.assert_not_called()
        self.assertEqual(json.loads((self.uebung / "stand.json").read_text())["stand"], "wartet")
        with mock.patch.object(aw, "auswerten", side_effect=aw.Gescheitert("keine Rubrik")):
            self.assertTrue(agent.art_auftrag(dict(a)))
        self.assertEqual(self.abschliessen.call_args.kwargs["status"], "fehlgeschlagen")
        self.assertEqual(json.loads((self.uebung / "stand.json").read_text())["stand"], "fehlgeschlagen")


class TestExposeDaten(unittest.TestCase):
    """expose_auftrag gibt daten nur bei Aufträgen mit Art mit (Telegram bleibt unverändert)."""

    def test_nur_mit_art(self):
        from tests.test_agent import TestExpose
        fall = TestExpose("test_erster_lauf_haengt_fassung_an")
        fall.setUp()
        self.addCleanup(fall.doCleanups)
        a = {"id": "20261022-120000-uni-abc123", "text": "Exposé: Lamellen", "modus": "erledigen"}
        agent.expose_auftrag(a, a, laufen=fall.claude(fall.gueltig), netz=("s", "m"))
        self.assertIsNone(fall.abschliessen.call_args.kwargs["daten"])
        agent.expose_auftrag({**a, "art": "expose"}, a, laufen=fall.claude(fall.gueltig), netz=("s", "m"))
        daten = fall.abschliessen.call_args.kwargs["daten"]
        self.assertEqual(daten["titel"], fall.gueltig["titel"])
        self.assertEqual(set(daten), {"titel", "kern", "punkte", "pruefen"})


if __name__ == "__main__":
    unittest.main()
