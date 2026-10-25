import json
import tempfile
import unittest
from pathlib import Path

import renderer
import webpruefung
from agentkit import abruf

DOMAINS = ["taz.de", "youtube.com", "gesetze-im-internet.de"]
SEITEN = {
    "https://taz.de/fall": "Titel\nDer Mann stahl drei Fahrräder und wurde zu Bewährung verurteilt.",
    "https://www.youtube.com/watch?v=x": "Norwegens Gefängnisse - Doku\nYouTube",
}
REGISTER = {
    "liszt": {"autor": "Franz von Liszt", "werk": "Zweckgedanke", "ausgabe": "ZStW 3",
              "gemeinfreiheit": {"verwendbar": True},
              "stellen": [{"seite": 41, "seiten": [41, 42], "zitat": "Die dritte Gruppe", "am_scan_pruefen": True}]},
    "gesperrt": {"gemeinfreiheit": {"verwendbar": False}, "stellen": [{"seite": 1, "zitat": "x"}]},
}


def seitentext(url):
    if url not in SEITEN:
        raise abruf.AbrufFehler(f"HTTP-Fehler 404 bei {url}")
    return SEITEN[url]


def beleg(url, zitat):
    return {"url": url, "zitat": zitat}


class BelegTest(unittest.TestCase):
    def setUp(self):
        self.stellen = webpruefung.register_stellen(REGISTER)

    def pruefe(self, b):
        return webpruefung.beleg_pruefen(b, DOMAINS, seitentext, self.stellen)

    def test_zitat_auf_der_seite(self):
        self.assertEqual(self.pruefe(beleg("https://taz.de/fall", "stahl drei  Fahrräder"))["status"], "bestanden")

    def test_zitat_umformuliert(self):
        e = self.pruefe(beleg("https://taz.de/fall", "stahl drei Räder"))
        self.assertEqual(e["status"], "durchgefallen")
        self.assertIn("nicht wörtlich", e["vermerk"])

    def test_nicht_ladbar(self):
        e = self.pruefe(beleg("https://taz.de/gibtsnicht", "x"))
        self.assertEqual(e["status"], "durchgefallen")
        self.assertIn("404", e["vermerk"])

    def test_nicht_auf_der_liste_wird_nicht_geladen(self):
        def verboten(url):
            raise AssertionError("darf nicht laden")
        e = webpruefung.beleg_pruefen(beleg("https://example.com/a", "x"), DOMAINS, verboten, self.stellen)
        self.assertEqual(e, {"status": "ungeprueft", "vermerk": webpruefung.NICHT_AUF_LISTE})

    def test_video_nur_titel(self):
        e = self.pruefe(beleg("https://www.youtube.com/watch?v=x", "Norwegens Gefängnisse - Doku"))
        self.assertEqual(e["status"], "bestanden")
        self.assertIn("Länge und Untertitel nicht geprüft", e["vermerk"])
        e = self.pruefe(beleg("https://www.youtube.com/watch?v=x", "Erfundener Titel"))
        self.assertEqual(e["status"], "durchgefallen")

    def test_register(self):
        self.assertEqual(self.pruefe({"register": "liszt:41"})["status"], "bestanden")
        self.assertEqual(self.pruefe({"register": "liszt:42"})["status"], "bestanden")  # zweite Seite der Stelle
        self.assertEqual(self.pruefe({"register": "liszt:7"})["status"], "durchgefallen")
        self.assertEqual(self.pruefe({"register": "gesperrt:1"})["status"], "durchgefallen")


ERGEBNIS = {"abschnitte": [
    {"titel": "B) Fälle", "aussagen": [
        {"text": "Ein Mann stahl drei Fahrräder.", "belege": [beleg("https://taz.de/fall", "stahl drei Fahrräder"),
                                                             beleg("https://example.com/x", "egal")]},
        {"text": "Erfundener Fall.", "belege": [beleg("https://taz.de/fall", "steht nicht da")]},
        {"text": "Nur ungeprüft belegt.", "belege": [beleg("https://example.com/y", "egal")]},
    ]},
    {"titel": "Liszt", "aussagen": [{"text": "Dritte Gruppe: Gelegenheitsverbrecher.", "belege": [{"register": "liszt:41"}]}]},
], "luecken": ["Kein Video gefunden."], "rueckfragen": ["Wie viele Stunden?"]}


class PruefenTest(unittest.TestCase):
    def daten(self):
        return webpruefung.pruefen(json.loads(json.dumps(ERGEBNIS)), DOMAINS, seitentext,
                                   webpruefung.register_stellen(REGISTER))

    def test_zahlen_und_belegt(self):
        d = self.daten()
        self.assertEqual(d["zahlen"], {"aussagen": 4, "belegt": 2, "unbelegt": 2, "bestanden": 2,
                                       "durchgefallen": 1, "ungeprueft": 2})
        self.assertEqual([s["belegt"] for s in d["abschnitte"][0]["aussagen"]], [True, False, False])
        self.assertEqual(len(webpruefung.durchgefallene(d)), 1)
        self.assertIn("steht nicht da", webpruefung.durchgefallene(d)[0])

    def test_beschreibung_gueltig_fuer_renderer(self):
        d = self.daten()
        b = webpruefung.beschreibung("Recherche vom 25.10.2026", d, REGISTER)
        renderer.pruefen(b)  # wirft BeschreibungUngueltig bei Formatfehlern
        texte = json.dumps(b, ensure_ascii=False)
        self.assertIn("Ein Mann stahl drei Fahrräder. [1; ungeprüft: 2]", texte)
        self.assertIn("Nicht belegt", texte)
        self.assertIn("Erfundener Fall.", texte)
        self.assertIn("Quelle nicht auf der Liste, ungeprüft", texte)
        self.assertIn("am Scan prüfen", texte)
        self.assertIn("Kein Video gefunden.", texte)
        self.assertIn("Wie viele Stunden?", texte)
        belegte = [x["text"] for x in b["bloecke"] if x["typ"] == "absatz"]
        self.assertFalse(any(t.startswith("Erfundener Fall.") for t in belegte))

    def test_viele_quellen_in_mehreren_listen(self):
        aussagen = [{"text": f"A{i}", "belege": [beleg("https://taz.de/fall", "stahl")]} for i in range(3)]
        d = {"abschnitte": [{"titel": "T", "aussagen": aussagen}], "luecken": [f"L{i}" for i in range(60)],
             "rueckfragen": []}
        b = webpruefung.beschreibung("T", webpruefung.pruefen(d, DOMAINS, seitentext, {}), {})
        renderer.pruefen(b)


class LesenTest(unittest.TestCase):
    def lesen(self, inhalt):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.json"
            p.write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt), encoding="utf-8")
            return webpruefung.lesen(p)

    def test_gut_und_standardwerte(self):
        d = self.lesen({"abschnitte": []})
        self.assertEqual((d["luecken"], d["rueckfragen"]), ([], []))

    def test_fehler_mit_ort(self):
        with self.assertRaises(webpruefung.WebFehler) as f:
            self.lesen({"abschnitte": [{"titel": "T", "aussagen": [{"text": "x", "belege": [{"url": "u"}]}]}],
                        "luecken": [""]})
        self.assertIn("abschnitte[0].aussagen[0].belege[0]", str(f.exception))
        self.assertIn("luecken", str(f.exception))
        for kaputt in ("{", [1], {"abschnitte": "x"}):
            with self.assertRaises(webpruefung.WebFehler):
                self.lesen(kaputt)


if __name__ == "__main__":
    unittest.main()
