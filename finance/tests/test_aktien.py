"""Tests für die Variante AKTIEN (schritte, ablauf, bericht) mit falschem Claude und falschem Abruf (ohne Netz)."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import renderer

import ablauf
import abrufer
import bericht
import quellen
import schritte
from tests.test_ablauf import FalschesClaude, annahme, laden, steht_in

HEUTE = date(2026, 11, 9)
A = schritte.AKTIEN

KURS = {"symbol": "NVDA", "waehrung": "USD", "kurs_aktuell": 191.2, "stand": "2026-11-09",
        "monatsschluss": [{"monat": "2021-11", "schluss": 32.6}, {"monat": "2026-10", "schluss": 190.0}]}
SEC = {"firma": "NVIDIA CORP", "cik": 1045810, "kennzahlen": {
    "umsatz": {"einheit": "USD", "jahre": [{"bis": "2026-01-25", "wert": 130497000000},
                                           {"bis": "2025-01-26", "wert": 60922000000}]},
    "operatives_ergebnis": {"einheit": "USD", "jahre": [{"bis": "2026-01-25", "wert": 81453000000}]},
    "ausstehende_aktien": {"einheit": "Stück", "stand": "2026-10-01", "wert": 24400000000}}}

AUSWAHL = {"thema": "Robotik und KI", "bereiche": [{"name": "Chips", "gewinn": "Engpass bei Rechenleistung",
                                                    "firmen": [{"name": "NVIDIA", "symbol": "NVDA", "land": "US",
                                                                "cik": 1045810, "themenanteil": "hoch",
                                                                "warum": "GPUs"},
                                                               {"name": "Fanuc", "symbol": "6954.T", "land": "JP",
                                                                "themenanteil": "hoch", "warum": "Roboter"}]}],
           "etfs": [{"name": "Robotik-ETF", "symbol": "BOTZ", "warum": "breit"}], "offene_punkte": ["Fanuc ohne SEC"]}


def kennzahlen(q_sec, q_kurs):
    umsatz = {"wert": 130.5, "einheit": "Mrd USD", "quelle": q_sec}
    marktkap = {"wert": 4665.28, "einheit": "Mrd USD", "berechnet": {"art": "produkt", "aus": [
        {"wert": 191.2, "einheit": "USD", "quelle": q_kurs}, {"wert": 24.4, "einheit": "Mrd Stück", "quelle": q_sec}]}}
    return {"firmen": [{"name": "NVIDIA", "symbol": "NVDA", "jahr": 2025, "waehrung": "USD", "umsatz": umsatz,
                        "operative_marge": {"wert": 0.6242, "einheit": "Anteil", "berechnet": {"art": "quotient", "aus": [
                            {"wert": 81.453, "einheit": "Mrd USD", "quelle": q_sec}, umsatz]}},
                        "marktkapitalisierung": marktkap}],
            "offene_punkte": ["Fanuc: kein Abschluss geladen"]}


BEWERTUNG = {"bewertungen": [{"name": "NVIDIA", "symbol": "NVDA", "bewertung": "teuer", "begruendung": "x",
                              "eingepreistes_wachstum": {"wert": 0.07, "einheit": "Anteil", "berechnet": {
                                  "art": "differenz", "aus": [annahme(0.09, "Anteil"), annahme(0.02, "Anteil")]}},
                              "risiken": ["Zyklus"]}]}
THESEN = {"hypothesen": [{"titel": "Breiter ETF statt Einzelaktie", "these": "t", "begruendung": "b",
                          "instrumente": [{"name": "Robotik-ETF", "symbol": "BOTZ"}], "gegenargument": "g",
                          "risiken": ["Klumpen"], "bis_jahr": 2031, "sicherheit": "mittel",
                          "szenarien": {k: {"rendite_pa": annahme(r, "Anteil"), "text": "x"}
                                        for k, r in (("pessimistisch", -0.05), ("basis", 0.06), ("optimistisch", 0.12))},
                          "abbruchkriterien": [{"text": "Marge unter 0.3", "pruefen_bis": "2027-12-31"}]}]}
PRUEFUNG = {"pruefungen": [{"hypothese": "Breiter ETF statt Einzelaktie",
                            "vergleich": [{"name": "MSCI World", "ergebnis": "e", "zahl": annahme(0.07, "Anteil")}],
                            "prognosen": [{"aussage": "a", "indikator": "SEC 1045810 umsatz Geschäftsjahr 2027",
                                           "erwartet": annahme(150, "Mrd USD"), "pruefen_ab": "2028-03-31"}]}]}


class Variante(unittest.TestCase):
    def test_praefix(self):
        self.assertEqual(schritte.variante_aus_text("aktien: Robotik und KI"), (A, "Robotik und KI"))
        self.assertEqual(schritte.variante_aus_text("Investment:  KI ")[0], A)
        self.assertEqual(schritte.variante_aus_text("Robotik in der Holzindustrie"),
                         (schritte.MARKT, "Robotik in der Holzindustrie"))

    def test_prompt_nennt_variante_und_uebersicht(self):
        p = schritte.prompt(schritte.schritt(2, A), "KI", "r", "q", [], v=A)
        self.assertIn("Anlagemöglichkeiten", p)
        self.assertIn("r/uebersicht.json", p)
        self.assertIn("Kennzahlen und Bewertung", p)
        self.assertNotIn("uebersicht.json", schritte.prompt(schritte.schritt(1, A), "KI", "r", "q", [], v=A))


class Pflichtfelder(unittest.TestCase):
    def test_auswahl_gueltig_und_abfragen(self):
        self.assertEqual(schritte.pflichtfelder(1, AUSWAHL, HEUTE, A), [])
        abfragen = schritte.aktien_abfragen(AUSWAHL)
        self.assertEqual([(a["art"], a.get("symbol") or a.get("cik")) for a in abfragen],
                         [("kurs", "NVDA"), ("sec", 1045810), ("kurs", "6954.T"), ("kurs", "BOTZ")])
        for a in abfragen:
            abrufer.anfrage_bauen(a, {})  # alle bauen sich ohne Fehler

    def test_auswahl_fehler(self):
        falsch = {"thema": "x", "bereiche": [{"name": "b", "firmen": [
            {"name": "n", "symbol": "nvda", "cik": "123", "themenanteil": "sehr"}]}], "etfs": [{}] * 6}
        f = schritte.pflichtfelder(1, falsch, HEUTE, A)
        self.assertTrue(any("symbol" in x for x in f))
        self.assertTrue(any(".cik" in x for x in f))
        self.assertTrue(any("themenanteil" in x for x in f))
        self.assertTrue(any(x.startswith("etfs") for x in f))

    def test_kennzahlen_pflicht(self):
        f = schritte.pflichtfelder(2, {"firmen": [{"name": "X", "umsatz": annahme(1)}]}, HEUTE, A)
        self.assertEqual(len(f), 2)

    def test_bewertung_und_thesen(self):
        self.assertEqual(schritte.pflichtfelder(3, BEWERTUNG, HEUTE, A), [])
        ohne = {"bewertungen": [{"bewertung": "billig", "eingepreistes_wachstum": annahme(0.1, "Anteil")}]}
        self.assertEqual(len(schritte.pflichtfelder(3, ohne, HEUTE, A)), 2)
        self.assertEqual(schritte.pflichtfelder(4, THESEN, HEUTE, A), [])
        leer = {"hypothesen": [{"titel": "t", "szenarien": {"basis": {"text": "x"}}}]}
        self.assertEqual(len(schritte.pflichtfelder(4, leer, HEUTE, A)), 4)

    def test_pruefung_ohne_entwuerfe(self):
        self.assertEqual(schritte.pflichtfelder(5, PRUEFUNG, HEUTE, A), [])
        mit = {"pruefungen": [dict(PRUEFUNG["pruefungen"][0], entwuerfe=[{"art": "x"}])]}
        self.assertIn("keine Entwürfe", schritte.pflichtfelder(5, mit, HEUTE, A)[0])


class Durchlauf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self.tmp.name)
        self.ordner = self.hier / "data" / "recherchen" / "a1"
        self.quellen = self.hier / "data" / "quellen"
        self.ordner.mkdir(parents=True)
        self.abgefragt = []

    def tearDown(self):
        self.tmp.cleanup()

    def abrufen(self, abfrage):
        self.abgefragt.append(abfrage)
        if abfrage["art"] == "kurs" and abfrage["symbol"] == "NVDA":
            return quellen.speichern(self.quellen, "kurs", "https://q/NVDA", json.dumps(KURS).encode(), "Kurs NVDA")
        if abfrage["art"] == "sec":
            return quellen.speichern(self.quellen, "sec", "https://s/1045810", json.dumps(SEC).encode(), "SEC NVIDIA")
        if abfrage["art"] == "eurostat":
            return quellen.speichern(self.quellen, "eurostat", "https://e/usd", b'{"value": {"0": 1.08}}', "EUR/USD")
        raise abrufer.AbfrageFehler("Kurs: keine Daten (Symbol prüfen)")

    def test_ganze_recherche(self):
        ids = {}

        class Claude(FalschesClaude):
            def __call__(inner, prompt):
                if "Schritt 2 von 5" in prompt and 2 not in inner.plan:
                    ueb = json.loads((self.ordner / schritte.UEBERSICHT).read_text())
                    ids["sec"] = ueb["abschluesse"][0]["quelle"]
                    ids["kurs"] = ueb["kurse"][0]["quelle"]
                    inner.plan[2] = [kennzahlen(ids["sec"], ids["kurs"])]
                return super().__call__(prompt)

        claude = Claude(self.ordner, {1: [AUSWAHL], 3: [BEWERTUNG], 4: [THESEN], 5: [PRUEFUNG]})
        erg = ablauf.recherche("Robotik und KI", self.hier, self.ordner, self.quellen, claude, laden, steht_in,
                               HEUTE, abrufen=self.abrufen, v=A)
        self.assertEqual([e.nr for e in erg], [1, 0, 2, 3, 4, 5])
        self.assertTrue(all(e.ok for e in erg), [e.fehler for e in erg])
        self.assertEqual(len(claude.prompts), 5)  # Primärdaten ohne Claude
        self.assertIn({"art": "eurostat", "datensatz": "ert_bil_eur_a", "filter": {"currency": "USD", "statinfo": "AVG"},
                       "von_jahr": 2020, "beschreibung": "Wechselkurs EUR/USD, Jahresdurchschnitt (Eurostat)"},
                      self.abgefragt)
        ueb = json.loads((self.ordner / schritte.UEBERSICHT).read_text())
        self.assertEqual(len(ueb["nicht_geladen"]), 2)  # 6954.T und BOTZ
        text = ablauf.bericht_text("Robotik und KI", erg, "x", A)
        self.assertIn("Fertig. 1 These:", text)
        self.assertIn("nichts gekauft", text)
        self.assertIn("aus Abschlüssen und Kursen", text)

        daten, abbruch = bericht.aus_ergebnissen(erg)
        metas = {m["id"]: m for m in quellen.alle(self.quellen)}
        b = bericht.beschreibung("Robotik und KI", daten, metas, HEUTE, abbruch, A)
        renderer.pruefen(b)
        self.assertEqual(b["rubrik"], "Anlagemöglichkeiten")
        self.assertEqual(len(b["offene_fragen"]), 2)
        m = bericht.modell_aktien("Robotik und KI", daten)
        renderer.pruefen(m)
        self.assertEqual([x["name"] for x in m["blaetter"]], ["Bewertung", "Szenarien"])
        self.assertEqual(m["blaetter"][0]["werte"][0]["umsatz"], 130.5)

    def test_fortsetzen_ohne_neue_abfragen(self):
        (self.ordner / "schritt1.json").write_text(json.dumps(AUSWAHL))
        ablauf.primaerdaten_aktien(self.ordner, self.quellen, self.abrufen)
        anzahl = len(self.abgefragt)
        (self.ordner / schritte.UEBERSICHT).unlink()
        erg = ablauf.primaerdaten_aktien(self.ordner, self.quellen, self.abrufen)
        self.assertEqual(len(self.abgefragt), anzahl)
        self.assertTrue((self.ordner / schritte.UEBERSICHT).exists())
        self.assertEqual(len(erg.quellen), 3)


if __name__ == "__main__":
    unittest.main()
