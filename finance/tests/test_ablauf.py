"""Tests für schritte.py und ablauf.py mit falschem Claude und falschem Webabruf (ohne Netz, ohne agentkit)."""

import json
import tempfile
import unittest
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import ablauf
import abrufer
import quellen
import schritte

HEUTE = date(2026, 11, 9)
SEITE = "Geschäftsbericht 2025. Der Umsatz stieg auf 1.234,5 Mio EUR, die EBIT-Marge lag bei 8,2 %."


def annahme(wert, einheit="EUR"):
    return {"wert": wert, "einheit": einheit, "annahme": "Plausibler Wert, im Test angenommen"}


def web(wert, zitat="die EBIT-Marge lag bei 8,2 %", url="https://firma.de/gb"):
    return {"wert": wert, "einheit": "%", "quelle": {"url": url, "zitat": zitat, "beschreibung": "GB 2025"}}


def markt():
    return {"wert": 24e6, "einheit": "EUR", "berechnet": {"art": "produkt", "aus": [
        annahme(1200, "Betriebe"), annahme(0.25, "Anteil"), annahme(80000)]}}


GUELTIG = {
    1: {"thema": "Robotik", "stufen": [{"name": "Hersteller", "firmen": [{"name": "X", "jahr": 2025,
                                                                           "marge": web(8.2)}]}]},
    2: {"luecken": [{"titel": "L1", "belege": [{"zahl": annahme(1)}, {"zahl": annahme(2)}]}]},
    3: {"luecken": [{"titel": "L1", "bleibt": "ja", "marktgroesse": markt()}]},
    4: {"hypothesen": [{"titel": "Nachrüstung", "these": "x", "begruendung": "y", "sicherheit": "mittel",
                        "szenarien": {"pessimistisch": {"umsatz": annahme(1)}, "basis": {"umsatz": annahme(2)},
                                      "optimistisch": {"umsatz": annahme(3)}},
                        "abbruchkriterien": [{"text": "Weniger als 5 Anfragen", "pruefen_bis": "2027-06-30"}]}]},
    5: {"pruefungen": [{"hypothese": "Nachrüstung", "prognosen": [
        {"aussage": "a", "indikator": "GENESIS 42131", "erwartet": annahme(5), "pruefen_ab": "2027-12-31"}],
        "entwuerfe": [{"art": "angebotsanfrage", "an": "Sägewerk", "betreff": "b", "text": "t"}]}]},
}


@dataclass
class Lauf:
    ok: bool
    text: str


class FalschesClaude:
    """Schreibt je Lauf die nächste vorbereitete Datei des Schritts aus dem Prompt."""

    def __init__(self, ordner: Path, plan: dict[int, list[dict]]):
        self.ordner, self.plan, self.prompts = ordner, {k: list(v) for k, v in plan.items()}, []

    def __call__(self, prompt: str):
        self.prompts.append(prompt)
        if "Vorbereitung für Schritt 2: Primärdaten" in prompt:
            (self.ordner / ablauf.ABFRAGEN).write_text(json.dumps(self.plan[0].pop(0)))
            return Lauf(True, "ok")
        nr = int(prompt.split("Schritt ")[1].split(" ")[0])
        (self.ordner / f"schritt{nr}.json").write_text(json.dumps(self.plan[nr].pop(0)))
        return Lauf(True, "ok")


def laden(url):
    if url == "https://firma.de/gb":
        return ablauf.Web(SEITE.encode(), SEITE, "html")
    raise ablauf.WebFehler("HTTP 404")


def steht_in(zitat, text):
    return zitat in text


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self.tmp.name)
        self.ordner = self.hier / "data" / "recherchen" / "a1"
        self.quellen = self.hier / "data" / "quellen"
        self.ordner.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def recherche(self, claude):
        return ablauf.recherche("Robotik", self.hier, self.ordner, self.quellen, claude, laden, steht_in, HEUTE)


class TestAblauf(Basis):
    def test_alle_schritte_gueltig(self):
        claude = FalschesClaude(self.ordner, {n: [d] for n, d in GUELTIG.items()})
        erg = self.recherche(claude)
        self.assertEqual([e.ok for e in erg], [True] * 5, [e.fehler for e in erg])
        self.assertEqual(len(claude.prompts), 5)
        self.assertIn("data/recherchen/a1/schritt1.json", claude.prompts[1])  # vorige Schritte werden genannt
        text = ablauf.bericht_text("Robotik", erg, "data/recherchen/a1")
        self.assertIn("Fertig. 1 Hypothese:", text)
        self.assertIn("Nachrüstung (Sicherheit mittel)", text)

    def test_webquelle_wird_abgelegt_und_ersetzt(self):
        claude = FalschesClaude(self.ordner, {1: [GUELTIG[1]]})
        e = ablauf.schritt_ausfuehren(schritte.schritt(1), "Robotik", self.hier, self.ordner, self.quellen,
                                      claude, laden, steht_in, HEUTE)
        self.assertTrue(e.ok, e.fehler)
        gespeichert = json.loads((self.ordner / "schritt1.json").read_text())
        qid = gespeichert["stufen"][0]["firmen"][0]["marge"]["quelle"]
        self.assertTrue(quellen.ist_id(qid))
        self.assertEqual(quellen.meta(self.quellen, qid)["art"], "web")
        self.assertEqual(len(e.hinweise), 1)  # Webquelle: kein Rohdatenabgleich

    def test_nachbesserung_mit_fehlerliste(self):
        falsch = {"thema": "Robotik", "stufen": [{"name": "H", "umsatz": 12.5}]}
        claude = FalschesClaude(self.ordner, {1: [falsch, GUELTIG[1]]})
        e = ablauf.schritt_ausfuehren(schritte.schritt(1), "Robotik", self.hier, self.ordner, self.quellen,
                                      claude, laden, steht_in, HEUTE)
        self.assertTrue(e.ok)
        self.assertEqual(e.laeufe, 2)
        self.assertIn("wurde abgelehnt", claude.prompts[1])
        self.assertIn("stufen[0].umsatz: nackte Zahl 12.5", claude.prompts[1])

    def test_abbruch_nach_drei_versuchen(self):
        falsch = {"thema": "Robotik", "stufen": [{"name": "H", "marge": web(9.9)}]}  # 9,9 steht nicht im Zitat
        claude = FalschesClaude(self.ordner, {1: [falsch] * 3})
        erg = self.recherche(claude)
        self.assertEqual(len(erg), 1)
        self.assertFalse(erg[0].ok)
        self.assertEqual(erg[0].laeufe, 3)
        self.assertIn("steht nicht im Zitat", erg[0].fehler[0])
        self.assertIn("Abgebrochen bei Schritt 1", ablauf.bericht_text("Robotik", erg, "x"))

    def test_zitat_nicht_auf_seite_und_seite_nicht_ladbar(self):
        daten = {"a": web(8.2, zitat="erfundenes Zitat 8,2"), "b": web(8.2, url="https://weg.de/x")}
        f = ablauf.webquellen_aufloesen(daten, self.quellen, laden, steht_in)
        self.assertEqual(len(f), 2)
        self.assertIn("nicht wörtlich", f[0])
        self.assertIn("HTTP 404", f[1])

    def test_fortsetzen_ohne_neuen_lauf(self):
        (self.ordner / "schritt1.json").write_text(json.dumps(GUELTIG[1]))
        claude = FalschesClaude(self.ordner, {n: [d] for n, d in GUELTIG.items() if n > 1})
        erg = self.recherche(claude)
        self.assertTrue(erg[-1].ok)
        self.assertEqual(erg[0].laeufe, 0)
        self.assertEqual(len(claude.prompts), 4)

    def test_claude_lauf_fehlgeschlagen(self):
        erg = self.recherche(lambda p: Lauf(False, "Zeitlimit"))
        self.assertFalse(erg[0].ok)
        self.assertIn("Zeitlimit", erg[0].fehler[0])


    def test_lauf_ohne_ergebnis_wird_wiederholt(self):
        claude = FalschesClaude(self.ordner, {1: [GUELTIG[1]]})
        antworten = [Lauf(False, ""), None]

        def laufen(prompt):
            a = antworten.pop(0)
            return a if a else claude(prompt)

        e = ablauf.schritt_ausfuehren(schritte.schritt(1), "Robotik", self.hier, self.ordner, self.quellen,
                                      laufen, laden, steht_in, HEUTE)
        self.assertTrue(e.ok, e.fehler)
        self.assertEqual(e.laeufe, 2)
        self.assertIn("Grenze der Arbeitsschritte", claude.prompts[0])


class FalscherAbruf:
    """Gibt für gültige Jobsuche-Abfragen eine ID, sonst AbfrageFehler."""

    def __init__(self):
        self.abfragen = []

    def __call__(self, abfrage):
        self.abfragen.append(abfrage)
        if abfrage.get("art") == "jobsuche":
            return f"Q-20261109-jobsuche-{len(self.abfragen):06x}"
        raise abrufer.AbfrageFehler("tabelle: ungültiger Wert")


JOB = {"art": "jobsuche", "was": "Robotik", "beschreibung": "Stellen"}
FALSCH = {"art": "genesis", "tabelle": "x", "beschreibung": "Produktion"}


class TestPrimaerdaten(Basis):
    def phase(self, claude, abruf):
        return ablauf.primaerdaten("Robotik", self.hier, self.ordner, self.quellen, claude, abruf)

    def test_fehlgeschlagene_abfrage_wird_einmal_nachgebessert(self):
        claude = FalschesClaude(self.ordner, {0: [{"abfragen": [JOB, FALSCH]}, {"abfragen": [dict(JOB, wo="Bayern")]}]})
        abruf = FalscherAbruf()
        e = self.phase(claude, abruf)
        self.assertTrue(e.ok)
        self.assertEqual((e.laeufe, len(e.quellen), e.hinweise), (2, 2, []))
        self.assertIn("abfragen[1]: tabelle: ungültiger Wert", claude.prompts[1])
        gespeichert = json.loads((self.ordner / ablauf.ABFRAGEN_ERGEBNIS).read_text())["ergebnisse"]
        self.assertEqual([("id" in g) for g in gespeichert], [True, False, True])

    def test_bleibende_fehler_brechen_nicht_ab_und_fortsetzen_ohne_lauf(self):
        claude = FalschesClaude(self.ordner, {0: [{"abfragen": [FALSCH]}, {"abfragen": [FALSCH]}]})
        e = self.phase(claude, FalscherAbruf())
        self.assertTrue(e.ok)
        self.assertEqual(len(e.hinweise), 1)
        e2 = self.phase(lambda p: self.fail("kein Lauf beim Fortsetzen"), FalscherAbruf())
        self.assertEqual(e2.laeufe, 0)

    def test_recherche_mit_primaerdaten(self):
        plan = {n: [d] for n, d in GUELTIG.items()}
        plan[0] = [{"abfragen": [JOB]}]
        claude = FalschesClaude(self.ordner, plan)
        erg = ablauf.recherche("Robotik", self.hier, self.ordner, self.quellen, claude, laden, steht_in, HEUTE,
                               abrufen=FalscherAbruf())
        self.assertEqual([e.nr for e in erg], [1, 0, 2, 3, 4, 5])
        self.assertTrue(all(e.ok for e in erg), [e.fehler for e in erg])
        self.assertIn("davon 1 aus Statistiken", ablauf.bericht_text("Robotik", erg, "x"))


class TestSchritte(unittest.TestCase):
    def test_prompt_arbeitsweise_und_grenzen_schritt5(self):
        p = schritte.prompt(schritte.schritt(5), "Robotik", "data/recherchen/a1", "data/quellen", [])
        self.assertIn("höchstens 30 Arbeitsschritte", p)
        self.assertIn("höchstens zwei Vergleichsfirmen", p)
        a = schritte.abfragen_prompt("Robotik", "data/recherchen/a1", ["abfragen[0]: x"])
        self.assertIn("data/recherchen/a1/abfragen.json", a)
        self.assertIn("abfragen[0]: x", a)

    def test_pflichtfelder(self):
        self.assertIn("mindestens zwei Belege", schritte.pflichtfelder(2, {"luecken": [{"belege": []}]}, HEUTE)[0])
        f = schritte.pflichtfelder(3, {"luecken": [{"bleibt": "vielleicht", "marktgroesse": annahme(1)}]}, HEUTE)
        self.assertEqual(len(f), 2)
        f = schritte.pflichtfelder(5, {"pruefungen": [{"prognosen": [{"erwartet": annahme(1),
                                                                       "pruefen_ab": "2026-01-01"}]}]}, HEUTE)
        self.assertIn("in der Zukunft", f[0])

    def test_prompt_enthaelt_regeln_und_quellen(self):
        metas = [{"id": "Q-20261109-genesis-abcdef", "art": "genesis", "abgerufen": "2026-11-09T12:00:00+01:00",
                  "beschreibung": "Produktion", "endung": "json"}]
        p = schritte.prompt(schritte.schritt(2), "Robotik", "data/recherchen/a1", "data/quellen", metas)
        self.assertIn("Schritt 2 von 5", p)
        self.assertIn("data/quellen/Q-20261109-genesis-abcdef.roh.json", p)
        self.assertIn("Keine nackten Zahlen", p)

    def test_lesen_mit_markdown_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "s.json"
            pfad.write_text('```json\n{"a": 1}\n```')
            self.assertEqual(schritte.lesen(pfad), ({"a": 1}, None))
            pfad.write_text("[1]")
            self.assertEqual(schritte.lesen(pfad)[1], "Ergebnis muss ein JSON-Objekt sein")


if __name__ == "__main__":
    unittest.main()
