import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import bewertung  # noqa: E402
import eingabe  # noqa: E402
import pruefung  # noqa: E402
import seite  # noqa: E402
import texte  # noqa: E402
import vorfilter  # noqa: E402
from db import Speicher  # noqa: E402

SEITE = (HIER / "daten" / "suchseite.html").read_text(encoding="utf-8")


def anzeige(aid, titel="Rennrad", preis=100.0, top=False, datum="Heute, 10:00", text=""):
    return seite.Anzeige(id=aid, titel=titel, beschreibung=text, link=f"{seite.BASIS}/s-anzeige/x/{aid}",
                         preis_text=f"{preis:g} €" if preis is not None else "", preis=preis, vb=False,
                         plz="34128", ort="Kassel", datum=datum, top=top, gewerblich=False)


class SeiteTest(unittest.TestCase):
    def test_anzeigen_aus_echter_seite(self):
        liste = seite.anzeigen_lesen(SEITE)
        self.assertEqual(len(liste), 5)  # Werbeanzeige übersprungen
        a = liste[2]
        self.assertEqual(a.id, 3573105591)
        self.assertEqual(a.preis, 45.0)
        self.assertTrue(a.vb)
        self.assertEqual(a.plz, "24536")
        self.assertTrue(a.link.startswith("https://www.kleinanzeigen.de/s-anzeige/"))
        self.assertTrue(a.neu)
        self.assertFalse(a.top)
        self.assertTrue(liste[0].top)
        self.assertFalse(liste[0].neu)
        self.assertTrue(a.bild.startswith("https://img.kleinanzeigen.de/"))

    def test_seite_ohne_liste(self):
        with self.assertRaises(seite.SeitenFehler):
            seite.anzeigen_lesen("<html>Bitte bestätigen Sie, dass Sie kein Roboter sind</html>")

    def test_preise(self):
        self.assertEqual(seite.preis_lesen("1.200 € VB"), (1200.0, True))
        self.assertEqual(seite.preis_lesen("49 €"), (49.0, False))
        self.assertEqual(seite.preis_lesen("12,50 €"), (12.5, False))
        self.assertEqual(seite.preis_lesen(" Zu verschenken"), (0.0, False))
        self.assertEqual(seite.preis_lesen("VB"), (None, True))
        self.assertEqual(seite.preis_lesen(""), (None, False))

    def test_such_url(self):
        self.assertEqual(seite.such_url("Rennrad Größe 56"), "https://www.kleinanzeigen.de/s-rennrad-groesse-56/k0")
        self.assertEqual(seite.such_url("rennrad", 300), "https://www.kleinanzeigen.de/s-preis::300/rennrad/k0")
        self.assertEqual(seite.such_url("rennrad", 300, 4927, "34128", 30),
                         "https://www.kleinanzeigen.de/s-34128/preis::300/rennrad/k0l4927r30")

    def test_ort_id(self):
        self.assertEqual(seite.ort_id_lesen({"_0": "Deutschland", "_4927": "34128 Kassel"}, "34128"), 4927)
        self.assertIsNone(seite.ort_id_lesen({"_0": "Deutschland"}, "34128"))


class VorfilterTest(unittest.TestCase):
    def test_filtert(self):
        liste = [anzeige(1), anzeige(2, preis=500), anzeige(3, titel="Suche Rennrad"),
                 anzeige(4, top=True, datum="10.10.2026"), anzeige(5, text="Rahmen defekt"),
                 anzeige(6, preis=None), anzeige(7), anzeige(8, top=True)]
        raus = vorfilter.vorfiltern(liste, {7}, 300, ["defekt"])
        self.assertEqual([a.id for a in raus], [1, 6, 8])

    def test_ausschluss_nur_ganze_woerter(self):
        self.assertFalse(vorfilter.ausgeschlossen(anzeige(1, text="Nicht defekter Text"), ["defekt"]))
        self.assertTrue(vorfilter.ausgeschlossen(anzeige(1, titel="Ersatzteile Rennrad"), ["ersatzteile"]))

    def test_marktpreis_und_notfall(self):
        self.assertIsNone(vorfilter.marktpreis([100] * 7))
        self.assertEqual(vorfilter.marktpreis([0, 100, 100, 100, 200, 200, 200, 300, 300]), 200.0)
        k = [anzeige(1, preis=50), anzeige(2, preis=90), anzeige(3, preis=0), anzeige(4, preis=None)]
        self.assertEqual([a.id for a in vorfilter.notfall_schnaeppchen(k, 100)], [1])
        self.assertEqual(vorfilter.notfall_schnaeppchen(k, None), [])


class EingabeTest(unittest.TestCase):
    def test_details(self):
        d = eingabe.details_lesen("max 80 €, 30 km um 34128")
        self.assertEqual((d.max_preis, d.umkreis_km, d.plz), (80.0, 30, "34128"))
        d = eingabe.details_lesen("120")
        self.assertEqual((d.max_preis, d.umkreis_km, d.plz), (120.0, None, None))
        d = eingabe.details_lesen("34128 50km 99,50 Euro")
        self.assertEqual((d.max_preis, d.umkreis_km, d.plz), (99.5, 50, "34128"))
        d = eingabe.details_lesen("egal")
        self.assertEqual((d.max_preis, d.umkreis_km, d.plz), (None, None, None))

    def test_umkreis_und_ids(self):
        self.assertEqual(eingabe.umkreis_runden(25), 30)
        self.assertEqual(eingabe.umkreis_runden(999), 200)
        self.assertEqual(eingabe.chat_ids_lesen("123, -456 x 789"), {123, -456, 789})
        self.assertEqual(eingabe.chat_ids_lesen(""), set())

    def test_details_text(self):
        self.assertEqual(eingabe.details_text(80, 30, "34128"), "max. 80 €, 30 km um 34128")
        self.assertEqual(eingabe.details_text(None, None, None), "max. egal, ganz Deutschland")


class BewertungTest(unittest.TestCase):
    def test_json_lesen(self):
        self.assertEqual(bewertung.json_lesen('Hier:\n```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(bewertung.json_lesen('{"a": {"b": 2}}'), {"a": {"b": 2}})
        with self.assertRaises(bewertung.AntwortFehler):
            bewertung.json_lesen("kein json")

    def test_such_antwort(self):
        d = bewertung.such_antwort_pruefen(json.dumps({
            "titel": "", "beschreibung": "Rennrad RH 56", "begriffe": ["rennrad 56", "rennrad", "fahrrad"],
            "ausschluss": ["defekt", ""], "max_preis": 300, "marktwert": "viel"}))
        self.assertEqual(d["titel"], "rennrad 56")
        self.assertEqual(d["begriffe"], ["rennrad 56", "rennrad"])
        self.assertEqual(d["ausschluss"], ["defekt"])
        self.assertEqual(d["max_preis"], 300.0)
        self.assertIsNone(d["marktwert"])
        with self.assertRaises(bewertung.AntwortFehler):
            bewertung.such_antwort_pruefen('{"titel": "x"}')

    def test_bewertung(self):
        antwort = json.dumps({"bewertungen": [
            {"id": 1, "punkte": 90, "marktwert": 300, "grund": "Top"},
            {"id": "2", "punkte": 150, "marktwert": None, "grund": "x"},
            {"id": 99, "punkte": 90, "grund": "unbekannt"},
            {"id": 3, "punkte": "viel"}]})
        b = bewertung.bewertung_pruefen(antwort, {1, 2, 3})
        self.assertEqual(set(b), {1, 2})
        self.assertEqual(b[2]["punkte"], 100)
        paare = bewertung.treffer_auswaehlen([anzeige(1), anzeige(2), anzeige(3)], b)
        self.assertEqual([a.id for a, _ in paare], [2, 1])

    def test_prompt_enthaelt_anzeigen(self):
        p = bewertung.bewertungs_prompt({"titel": "Rennrad", "beschreibung": "RH 56", "marktwert": 400,
                                         "max_preis": 300}, [anzeige(7, text="a" * 1000)], 250)
        self.assertIn("id 7", p)
        self.assertIn("400 €", p)
        self.assertIn("250 €", p)
        self.assertLess(len(p), 3000)


class SpeicherTest(unittest.TestCase):
    def setUp(self):
        self.sp = Speicher(":memory:")
        self.sid = self.sp.suche_anlegen(1, {"titel": "Rennrad", "beschreibung": "x", "begriffe": ["rennrad"],
                                             "ausschluss": ["defekt"], "max_preis": None, "marktwert": 400})

    def test_suchen_je_nutzer(self):
        self.sp.suche_anlegen(2, {"titel": "Sofa", "beschreibung": "y", "begriffe": ["sofa"], "ausschluss": []})
        self.assertEqual(self.sp.entwurf(1)["id"], self.sid)
        self.assertIsNone(self.sp.suche(self.sid, chat_id=2))
        self.sp.suche_aendern(self.sid, status="aktiv", max_preis=300.0)
        self.assertIsNone(self.sp.entwurf(1))
        self.assertEqual([s["titel"] for s in self.sp.suchen(status="aktiv")], ["Rennrad"])
        self.assertEqual(self.sp.suche(self.sid)["ausschluss"], ["defekt"])
        with self.assertRaises(ValueError):
            self.sp.suche_aendern(self.sid, chat_id=5)

    def test_gesehen_und_loeschen(self):
        self.sp.gesehen_merken(self.sid, [(1, 10.0), (2, None), (1, 99.0)])
        self.assertEqual(self.sp.gesehen_ids(self.sid), {1, 2})
        self.assertEqual(self.sp.preise(self.sid), [10.0])
        self.sp.suche_loeschen(self.sid)
        self.assertEqual(self.sp.gesehen_ids(self.sid), set())

    def test_zaehler(self):
        self.assertEqual(self.sp.lauf_zaehlen("2026-11-15"), 1)
        self.assertEqual(self.sp.lauf_zaehlen("2026-11-15"), 2)
        self.assertEqual(self.sp.laeufe("2026-11-16"), 0)
        self.assertTrue(self.sp.grenze_erstmals("2026-11-15"))
        self.assertFalse(self.sp.grenze_erstmals("2026-11-15"))


class PruefungTest(unittest.TestCase):
    def setUp(self):
        self.sp = Speicher(":memory:")
        sid = self.sp.suche_anlegen(1, {"titel": "Rennrad", "beschreibung": "x", "begriffe": ["rennrad"],
                                        "ausschluss": [], "max_preis": 300.0, "marktwert": 400.0})
        self.suche = self.sp.suche(sid)
        self.prompts = []

    def claude(self, antwort):
        def f(prompt):
            self.prompts.append(prompt)
            return antwort
        return f

    def test_bewertet_und_meldet(self):
        liste = [anzeige(1, preis=150), anzeige(2, preis=250), anzeige(3, preis=900)]
        antwort = json.dumps({"bewertungen": [{"id": 1, "punkte": 88, "marktwert": 400, "grund": "billig"},
                                              {"id": 2, "punkte": 40, "marktwert": 300, "grund": "nein"}]})
        erg = pruefung.suche_pruefen(self.sp, self.suche, liste, self.claude(antwort), True)
        self.assertEqual(erg.kandidaten, 2)
        self.assertEqual(len(erg.meldungen), 1)
        self.assertIn("88/100", erg.meldungen[0])
        self.assertEqual(self.sp.gesehen_ids(self.suche["id"]), {1, 2, 3})
        # zweiter Durchgang: nichts Neues, kein Lauf
        erg = pruefung.suche_pruefen(self.sp, self.suche, liste, self.claude(antwort), True)
        self.assertFalse(erg.claude)
        self.assertEqual(len(self.prompts), 1)

    def test_fehler_laesst_kandidaten_offen(self):
        def kaputt(prompt):
            raise RuntimeError("Limit")
        with self.assertRaises(RuntimeError):
            pruefung.suche_pruefen(self.sp, self.suche, [anzeige(1)], kaputt, True)
        self.assertEqual(self.sp.gesehen_ids(self.suche["id"]), set())

    def test_tagesgrenze_nur_klare_schnaeppchen(self):
        liste = [anzeige(1, preis=280), anzeige(2, preis=100)]
        erg = pruefung.suche_pruefen(self.sp, self.suche, liste, self.claude("{}"), False)
        self.assertFalse(erg.claude)
        self.assertTrue(erg.notfall)
        self.assertEqual(len(erg.meldungen), 1)
        self.assertIn("Tagesgrenze", erg.meldungen[0])
        self.assertEqual(self.sp.gesehen_ids(self.suche["id"]), {1, 2})

    def test_zusammenfuehren(self):
        self.assertEqual([a.id for a in pruefung.zusammenfuehren([[anzeige(1), anzeige(2)], [anzeige(2), anzeige(3)]])],
                         [1, 2, 3])


class TexteTest(unittest.TestCase):
    def test_treffer_escaped(self):
        t = texte.treffer_text(anzeige(1, titel="Rad <b>&"), {"punkte": 80, "marktwert": 200, "grund": "gut"}, "R")
        self.assertIn("Rad &lt;b&gt;&amp;", t)
        self.assertIn("üblich ca. 200 €", t)
        self.assertIn('href="https://www.kleinanzeigen.de/s-anzeige/x/1"', t)

    def test_nacht(self):
        self.assertTrue(texte.ist_nacht(datetime(2026, 11, 15, 3), 1, 6))
        self.assertFalse(texte.ist_nacht(datetime(2026, 11, 15, 6), 1, 6))
        self.assertTrue(texte.ist_nacht(datetime(2026, 11, 15, 23), 23, 6))
        self.assertFalse(texte.ist_nacht(datetime(2026, 11, 15, 3), 0, 0))


if __name__ == "__main__":
    unittest.main()
