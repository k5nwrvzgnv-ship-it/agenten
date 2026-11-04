"""Messlatte: Sätze getrennt und vollständig, Bewertung, Log, keine Inhalte im Prüfbericht, Werkzeug schickt nichts ans Portal."""

import ast
import json
import tempfile
import unittest
from pathlib import Path

import messung

FRAGEN = [{"id": f"F{i}", "frage": f"Frage {i}"} for i in range(1, 5)]


def _aussagen() -> list[dict]:
    aussagen = []
    for f in FRAGEN:
        for nr in range(6):
            aussagen.append({"id": f"{f['id']}-{nr}", "frage": f["id"], "status": "teilweise" if nr < 2 else "gesichert", "fenster": "scopus" if nr else "methoden",
                             "text": f"Aussage {f['id']} Nummer {nr} mit genug Text, damit der Anfang eindeutig bleibt",
                             "belege": [{"url": f"https://q.de/{f['id']}"}, {"url": "https://andere.de/x"}] if nr in (2, 3) else [] if nr < 2 else [{"url": "https://einzel.de"}]})
    return aussagen


def daten() -> dict:
    return {"pdf": True,
            "expose": {"literatur": ["a", "b", "c", "d"],
                       "bloecke": [{"typ": "ueberschrift", "text": "Eins"}, {"typ": "absatz", "text": "x [OFFEN: a] y"},
                                   {"typ": "ueberschrift", "text": "Zwei"}, {"typ": "absatz", "text": "[OFFEN: b]"},
                                   {"typ": "tabelle", "zeilen": [["1"], ["2"], ["3"]]}]},
            "geprueft": {"fragen": FRAGEN, "aussagen": _aussagen(),
                         "quellen": [{"titel": f"Ein langer Titel der Quelle {f['id']}", "url": f"https://q.de/{f['id']}"} for f in FRAGEN]
                         + [{"titel": "Doppelter Titel der Quelle", "url": "https://d.de/1"}, {"titel": "Doppelter Titel der Quelle", "url": "https://d.de/2"}],
                         "literatursuche": {"suchen": [{"nr": f"S{i}", "titel": f"Suche Nummer {i} zum Holz"} for i in range(1, 4)]}},
            "schriftverkehr": {"mails": [{"datum": "2026-10-21T10:00:00"}, {"datum": "2026-10-29T10:00:00"}, {"datum": "2026-10-26T09:00:00"}]},
            "plan": {"themen": [{"id": f"t{i}", "titel": f"Thema {i}", "score": i} for i in range(1, 6)]}}


class Saetze(unittest.TestCase):
    def test_beide_saetze_vollstaendig_und_verschieden(self):
        a, b = (messung.satz_bauen(daten(), s) for s in messung.SAETZE)
        self.assertTrue(all(a) and all(b))
        self.assertEqual([x.id for x in a], [x.id for x in b])
        for x, y in zip(a, b, strict=True):
            if x.beide:
                self.assertEqual(x.frage, y.frage)
            else:
                self.assertNotEqual(x.param, y.param, x.id)

    def test_auswahl_ist_stabil(self):
        self.assertEqual([x.param for x in messung.satz_bauen(daten(), "A")], [x.param for x in messung.satz_bauen(daten(), "A")])

    def test_was_der_andere_satz_gemessen_hat_kommt_nicht_noch_einmal(self):
        a = messung.satz_bauen(daten(), "A")
        benutzt = {x.id: {x.param} for x in a}
        for x, y in zip(a, messung.satz_bauen(daten(), "B", benutzt), strict=True):
            if not x.beide:
                self.assertNotEqual(x.param, y.param, x.id)

    def test_nichts_loesbares_gibt_none(self):
        leer = {"pdf": False}
        self.assertEqual(messung.satz_bauen(leer, "A"), [None] * len(messung.BAUSTEINE))
        self.assertIn("nicht in beiden", messung.saetze_pruefen(leer)["probleme"][0])

    def test_nur_eine_mail_reicht_nicht(self):
        d = daten()
        d["schriftverkehr"]["mails"] = d["schriftverkehr"]["mails"][:1]
        self.assertEqual(messung._k7_mail(d), [])

    def test_doppelte_titel_sind_keine_kandidaten(self):
        self.assertFalse([x for x in messung._k4_quelle(daten()) if "Doppelter" in x.frage])

    def test_quelle_zaehlt_aussagen(self):
        for x in messung._k4_quelle(daten()):
            self.assertEqual((x.loesung, x.mal), ("2", 2))

    def test_status_zaehlt_in_der_frage(self):
        self.assertEqual({x.loesung for x in messung._k3_status(daten())}, {"2"})

    def test_offene_stellen_je_abschnitt(self):
        self.assertEqual({x.param: x.loesung for x in messung._k2_offene_stellen(daten())}, {"Eins": "1", "Zwei": "1"})

    def test_aelteste_und_neueste_mail(self):
        self.assertEqual([x.loesung for x in messung._k7_mail(daten())], ["2026-10-21", "2026-10-29"])

    def test_pruefbericht_ohne_fragen_und_loesungen(self):
        text = json.dumps(messung.saetze_pruefen(daten()), ensure_ascii=False)
        d = daten()
        for satz in messung.SAETZE:
            for x in messung.satz_bauen(d, satz):
                self.assertNotIn(x.frage, text)
                if x.param:
                    self.assertNotIn(x.param, text)

    def test_ungleicher_aufwand_wird_gemeldet(self):
        d = daten()
        d["expose"]["literatur"] = list("abcdefghijklmn")
        self.assertTrue(any("umfang: Aufwand" in p for p in messung.saetze_pruefen(d)["probleme"]))


class Bewertung(unittest.TestCase):
    def test_zahl(self):
        for antwort, soll in (("12", True), (" 12 Stück", True), ("13", False), ("zwölf", False)):
            self.assertEqual(messung.antwort_richtig("zahl", "12", antwort), soll, antwort)

    def test_datum(self):
        for antwort, soll in (("29.10.2026", True), ("29.10.26", True), ("29.10.", True), ("29.10", True), ("2026-10-29", True), ("29. 10.", True),
                              ("28.10.", False), ("29.10.2025", False), ("Oktober", False)):
            self.assertEqual(messung.antwort_richtig("datum", "2026-10-29", antwort), soll, antwort)

    def test_text(self):
        titel = "Automatische Erkennung von Fehlstellen im Holz"
        self.assertTrue(messung.antwort_richtig("text", titel, titel))
        self.assertTrue(messung.antwort_richtig("text", titel, "S1: automatische Erkennung Fehlstellen Holz"))
        self.assertFalse(messung.antwort_richtig("text", titel, "Holz"))

    def test_leer_heisst_aufgegeben(self):
        aufgabe = messung.Aufgabe("x", "K1", "?", "zahl", "1", "p", "/")
        self.assertEqual(messung.bewerten(aufgabe, "  ", []), "aufgegeben")
        self.assertEqual(messung.bewerten(aufgabe, "1", None), "richtig")
        self.assertEqual(messung.bewerten(aufgabe, "2", None), "falsch")

    def test_pdf_nur_mit_aufruf_im_log(self):
        aufgabe = messung._k6_pdf(daten())[0]
        treffer = [{"pfad": aufgabe.seite, "status": 200, "methode": "GET"}]
        self.assertEqual(messung.bewerten(aufgabe, "ok", treffer), "richtig")
        self.assertEqual(messung.bewerten(aufgabe, "ok", []), "falsch")
        self.assertEqual(messung.bewerten(aufgabe, "ok", [{**treffer[0], "status": 404}]), "falsch")
        for status in (206, 304):  # Browser mit Teilabruf oder eigener Kopie: der Aufruf war trotzdem da
            self.assertEqual(messung.bewerten(aufgabe, "ok", [{**treffer[0], "status": status}]), "richtig")
        self.assertEqual(messung.bewerten(aufgabe, "ok", None), "ungeprueft")
        self.assertEqual(messung.bewerten(aufgabe, "", treffer), "aufgegeben")

    def test_zusammenfassung(self):
        ergebnisse = [{"bewertung": "richtig", "sekunden": 10.0, "aufrufe": 2, "heute_loesbar": True},
                      {"bewertung": "aufgegeben", "sekunden": 30.0, "aufrufe": 4, "heute_loesbar": False},
                      {"bewertung": "falsch", "sekunden": 20.0, "aufrufe": None, "heute_loesbar": True}]
        z = messung.zusammenfassen(ergebnisse)
        self.assertEqual((z["richtig"], z["aufgegeben"], z["falsch"], z["richtig_von_loesbar"], z["loesbar_gestellt"]), (1, 1, 1, 1, 2))
        self.assertEqual((z["sekunden_gesamt"], z["sekunden_median"], z["aufrufe_gesamt"]), (60.0, 20.0, 6))


class Log(unittest.TestCase):
    TEXT = ('1762268000.123456 vmd python[1]: INFO:     127.0.0.1:1 - "GET /projekt/fehlstellen HTTP/1.1" 200 OK\n'
            '1762268001.000000 vmd python[1]: INFO:     127.0.0.1:1 - "GET /statisch/stil.css HTTP/1.1" 200 OK\n'
            '1762268002.000000 vmd python[1]: INFO:     127.0.0.1:1 - "POST /modul/holzschutz/bewerten HTTP/1.1" 303 See Other\n'
            '1762268050.000000 vmd python[1]: INFO:     Started server process [1]\n'
            '-- No entries --\n')

    def test_zeilen(self):
        e = messung.log_lesen(self.TEXT)
        self.assertEqual([(x["methode"], x["pfad"], x["status"]) for x in e],
                         [("GET", "/projekt/fehlstellen", 200), ("GET", "/statisch/stil.css", 200), ("POST", "/modul/holzschutz/bewerten", 303)])

    def test_fenster_ohne_statisches(self):
        e = messung.log_lesen(self.TEXT)
        self.assertEqual([x["pfad"] for x in messung.im_fenster(e, 1762268000.7, 1762268001.5)], ["/projekt/fehlstellen"])
        self.assertEqual(messung.im_fenster(e, 1762268003, 1762268040), [])


class Nachweis(unittest.TestCase):
    def test_fehlt_und_ohne_inhalt(self):
        aufgabe = messung.Aufgabe("x", "K4", "?", "zahl", "2", "p", "/", ["GEHEIM", "zweiter"], mal=2)
        fehler = messung.nachweis_fehler(aufgabe, "GEHEIM zweiter")
        self.assertEqual(len(fehler), 1)
        self.assertNotIn("GEHEIM", fehler[0])
        self.assertEqual(messung.nachweis_fehler(aufgabe, "GEHEIM GEHEIM zweiter"), [])


class Ablage(unittest.TestCase):
    def test_benutzte_parameter_nur_aus_anderen_saetzen(self):
        with tempfile.TemporaryDirectory() as t:
            ordner = Path(t)
            messung._schreiben(ordner / "A-1.json", {"satz": "A", "fertig": True, "ergebnisse": [{"aufgabe": "x", "param": "p"}]})
            self.assertEqual(messung.benutzte_parameter(ordner, "B"), {"x": {"p"}})
            self.assertEqual(messung.benutzte_parameter(ordner, "A"), {})
            self.assertTrue(messung.fertige_messung(ordner, "A"))
            self.assertFalse(messung.fertige_messung(ordner, "B"))

    def test_rechte(self):
        with tempfile.TemporaryDirectory() as t:
            pfad = Path(t) / "neu" / "A.json"
            messung._schreiben(pfad, {"satz": "A"})
            self.assertEqual(pfad.stat().st_mode & 0o777, 0o600)
            self.assertEqual(pfad.parent.stat().st_mode & 0o777, 0o700)


class NurLesend(unittest.TestCase):
    def test_kein_netz_und_kein_web_dienst(self):
        quelle = Path(messung.__file__).read_text(encoding="utf-8")
        namen = set()
        for knoten in ast.walk(ast.parse(quelle)):
            if isinstance(knoten, ast.Import):
                namen |= {a.name.split(".")[0] for a in knoten.names}
            elif isinstance(knoten, ast.ImportFrom):
                namen.add((knoten.module or "").split(".")[0])
        self.assertFalse(namen & {"urllib", "http", "requests", "httpx", "socket", "app", "fastapi", "agentkit", "lernmodell_schreiben"})
        self.assertIn("messung", {p.stem for p in Path(messung.__file__).parent.glob("*.py")})

    def test_web_dienst_kennt_das_werkzeug_nicht(self):
        app = (Path(messung.__file__).parent / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("messung", app)


if __name__ == "__main__":
    unittest.main()
