import json
import re
import tempfile
import unittest
from pathlib import Path

from agentkit import abruf
from agentkit.claude_lauf import Ergebnis

import recherche

ECK = {"thema": "Fehlstellen an Lamellen optisch erkennen",
       "fragen": [{"id": "F1", "fenster": "literatur", "frage": "Wie gut erkennen Modelle Äste?",
                   "anlass": "Jan 24:54"},
                  {"id": "F2", "fenster": "regelwerk", "frage": "Was regelt DIN 4074-1 zu Ästen?",
                   "anlass": "Henri 15:00"}]}
URL = "https://example.org/paper"
NORM = "data/normen/material/DIN 4074-1_2026-05-00_DE_3681261.pdf.txt"
LIT = {"aussagen": [{"frage": "F1", "art": "tatsache", "text": "YOLO erkennt Äste mit hoher Präzision.",
                     "belege": [{"url": URL, "zitat": "YOLO detects knots with high precision"}]},
                    {"frage": "F1", "art": "einschaetzung", "text": "Für Lamellen ist das übertragbar.", "belege": []}],
       "quellen": [{"url": URL, "titel": "Knot detection with YOLO", "autoren": ["Muster, A."], "jahr": 2023,
                    "doi": "10.1234/abc", "art": "artikel"}],
       "luecken": ["Keine Preise gefunden"]}
REG = {"aussagen": [{"frage": "F2", "art": "tatsache", "text": "Die Norm begrenzt Äste.",
                     "belege": [{"datei": NORM, "seite": 2, "zitat": "Äste sind nach Tabelle 1 zu begrenzen"}]}],
       "quellen": [], "luecken": []}
SEITE = "Abstract. YOLO detects knots  with high\nprecision on sawn timber. Uniﬁed detection."
META = {"titel": "Knot detection with YOLO", "jahr": 2023, "nachnamen": ["Muster"]}


def seitentext(url):
    if "fremd" in url:
        raise recherche.DomainNichtErlaubt("fremd")
    if "kaputt" in url:
        raise abruf.AbrufFehler("HTTP 404")
    return SEITE


class Ordner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.hier = Path(self._tmp.name)
        norm = self.hier / NORM
        norm.parent.mkdir(parents=True)
        norm.write_text("--- Seite 1\nVorwort\n--- Seite 2\nÄste sind nach Tabelle 1\nzu begrenzen.\n")


class TestDateienPruefen(Ordner):
    def test_eckpunkte(self):
        self.assertEqual(recherche.eckpunkte_pruefen(ECK), [])
        kaputt = {"thema": "", "x": 1, "fragen": [{"id": "F2", "fenster": "wetter", "frage": "?"}]}
        fehler = "\n".join(recherche.eckpunkte_pruefen(kaputt))
        for teil in ("x: unbekanntes Feld", "thema:", "fragen[0].id: muss F1", "fragen[0].fenster",
                     "fragen[0].anlass"):
            self.assertIn(teil, fehler)

    def test_fenster(self):
        self.assertEqual(recherche.fenster_pruefen(LIT, {"F1"}), [])
        kaputt = {"aussagen": [{"frage": "F9", "art": "tatsache", "text": "x", "belege": []},
                               {"frage": "F1", "art": "tatsache", "text": "y",
                                "belege": [{"url": "http://a.de", "zitat": "kurz"},
                                           {"url": "https://b.de/x", "zitat": "lang genug für ein Zitat"},
                                           {"datei": "d.txt", "seite": "2", "zitat": "lang genug für ein Zitat"}]}],
                  "quellen": [{"url": "https://c.de", "titel": "T", "jahr": 99, "doi": "abc"}]}
        fehler = "\n".join(recherche.fenster_pruefen(kaputt, {"F1"}))
        for teil in ("aussagen[0].frage", "aussagen[0]: eine Tatsache braucht", "belege[0].zitat",
                     "belege[0]: {url (https)", "belege[1]: url fehlt unter quellen", "belege[2]: {datei",
                     "quellen[0].jahr", "quellen[0].doi"):
            self.assertIn(teil, fehler)


class TestBelege(Ordner):
    def test_url(self):
        b = {"url": URL, "zitat": "YOLO detects knots with high precision"}
        self.assertEqual(recherche.beleg_pruefen(b, self.hier, seitentext)["status"], "bestanden")
        self.assertEqual(recherche.beleg_pruefen({**b, "zitat": "Unified detection."}, self.hier, seitentext)["status"],
                         "bestanden")  # Ligatur ﬁ aus dem PDF
        self.assertEqual(recherche.beleg_pruefen({**b, "zitat": "YOLO is perfect"}, self.hier, seitentext)["status"],
                         "durchgefallen")
        self.assertEqual(recherche.beleg_pruefen({**b, "url": "https://fremd.de"}, self.hier, seitentext)["status"],
                         "ungeprueft")
        p = recherche.beleg_pruefen({**b, "url": "https://kaputt.de"}, self.hier, seitentext)
        self.assertEqual((p["status"], p["vermerk"]), ("durchgefallen", "Seite nicht ladbar: HTTP 404"))

    def test_lokale_datei_seitengenau_und_nur_unter_data(self):
        b = {"datei": NORM, "seite": 2, "zitat": "Äste sind nach Tabelle 1 zu begrenzen"}
        self.assertEqual(recherche.beleg_pruefen(b, self.hier, seitentext)["status"], "bestanden")
        self.assertIn("nicht wörtlich auf dieser Seite",
                      recherche.beleg_pruefen({**b, "seite": 1}, self.hier, seitentext)["vermerk"])
        self.assertIn("gibt es in der Datei nicht",
                      recherche.beleg_pruefen({**b, "seite": 7}, self.hier, seitentext)["vermerk"])
        (self.hier / "geheim.txt").write_text(b["zitat"])
        self.assertIn("Datei gibt es nicht",
                      recherche.beleg_pruefen({**b, "datei": "data/../geheim.txt", "seite": None}, self.hier,
                                              seitentext)["vermerk"])

    def test_doi(self):
        q = LIT["quellen"][0]
        self.assertEqual(recherche.doi_vergleichen(q, META)["status"], "bestanden")
        p = recherche.doi_vergleichen(q, {"titel": "Something else entirely", "jahr": 2021, "nachnamen": ["Roe"]})
        for teil in ("Titel laut Crossref", "Jahr laut Crossref: 2021", "Autoren laut Crossref: Roe"):
            self.assertIn(teil, p["vermerk"])
        self.assertEqual(recherche.doi_pruefen({**q, "doi": None}, None)["status"], "ungeprueft")

    def test_allowlist(self):
        self.assertEqual(recherche._allowlist("https://a.b.de/x", None), ["a.b.de"])
        self.assertEqual(recherche._allowlist("https://www.mdpi.com/x", ["mdpi.com"]), ["mdpi.com"])
        with self.assertRaises(recherche.DomainNichtErlaubt):
            recherche._allowlist("https://evil.de", ["mdpi.com"])


class TestZusammenfuehren(Ordner):
    def geprueft(self, traegt="ja"):
        lit = recherche.fenster_belege_pruefen(json.loads(json.dumps(LIT)), self.hier, seitentext, lambda d: META)
        reg = recherche.fenster_belege_pruefen(json.loads(json.dumps(REG)), self.hier, seitentext, lambda d: META)
        fenster = {"literatur": lit, "regelwerk": reg}
        ids = [a["id"] for a in recherche.zur_gegenpruefung(fenster)]
        self.assertEqual(ids, ["literatur-1", "regelwerk-1"])  # Einschätzung ohne Beleg nicht
        gegen = {"urteile": [{"id": "literatur-1", "traegt": traegt, "fehlt": ""},
                             {"id": "regelwerk-1", "traegt": "ja", "fehlt": ""}], "widersprueche": [], "offen": []}
        return recherche.zusammenfuehren(ECK, fenster, gegen)

    def test_status_und_zitierfaehig(self):
        g = self.geprueft()
        self.assertEqual([a["status"] for a in g["aussagen"]], ["gesichert", "einschaetzung", "gesichert"])
        self.assertTrue(g["quellen"][0]["zitierfaehig"])
        g = self.geprueft("nein")
        self.assertEqual(g["aussagen"][0]["status"], "verworfen")
        self.assertFalse(g["quellen"][0]["zitierfaehig"])

    def test_literatur_nur_aus_geprueften_quellen(self):
        g = self.geprueft()
        ok = ["Muster, A. (2023): Knot detection with YOLO. https://doi.org/10.1234/ABC",
              "DIN 4074-1:2026-05 Sortierung von Holz nach der Tragfähigkeit"]
        self.assertEqual(recherche.literatur_pruefen(ok, g), [])
        fehler = recherche.literatur_pruefen(["Erfunden, B. (2020): Holz. Verlag."], g)
        self.assertIn("literatur[0]: 'Erfunden", fehler[0])

    def test_bericht(self):
        md = recherche.bericht(self.geprueft(), 3.5)
        for teil in ("# Recherchebericht: Fehlstellen", "3 Aussagen: 2 gesichert", "Kosten 3.50 USD",
                     "## F1: Wie gut", "**gesichert** (literatur-1)", "„YOLO detects knots with high precision“",
                     "**Einschätzung**", "## Lücken", "Keine Preise gefunden", "DOI 10.1234/abc"):
            self.assertIn(teil, md)


class TestDurchfuehren(Ordner):
    """Ganzer Ablauf mit Claude-Attrappe: jede Antwort schreibt die Datei, die der Prompt nennt."""

    def setUp(self):
        super().setUp()
        self.ordner = self.hier / "data" / "expose" / "k1"
        self.aufrufe = []

    def claude(self, antworten: dict, usd=1.0):
        def laufen(agent, hier, prompt, **kw):
            self.aufrufe.append((prompt, kw))
            name = re.search(r"recherche/(\w+)\.json", prompt).group(1)
            if antworten.get(name):
                (self.ordner / "recherche" / f"{name}.json").write_text(json.dumps(antworten[name].pop(0)))
            return Ergebnis(text="ok", sitzung=f"s{len(self.aufrufe)}", ok=True, usd=usd)
        return laufen

    def gegen(self):
        return {"urteile": [{"id": "literatur-1", "traegt": "ja", "fehlt": ""},
                            {"id": "regelwerk-1", "traegt": "teilweise", "fehlt": "Tabelle"}]}

    def test_ablauf_und_fortsetzen(self):
        falsch = json.loads(json.dumps(LIT))
        falsch["aussagen"][0]["belege"][0]["zitat"] = "YOLO is the gold standard for knots"
        antworten = {"eckpunkte": [ECK], "literatur": [falsch, falsch, LIT], "regelwerk": [REG, REG],
                     "gegenpruefung": [self.gegen()]}
        erg = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                     self.claude(antworten), seitentext, lambda d: META)
        prompts = [p for p, _ in self.aufrufe]
        self.assertEqual(len(prompts), 7)  # Eckpunkte, 2+1 Literatur, 2 Regelwerk, Gegenprüfung
        self.assertIn("Zitat steht nicht wörtlich", prompts[3])
        self.assertEqual(self.aufrufe[3][1]["sitzung_fortsetzen"], "s3")
        self.assertIsNone(self.aufrufe[6][1]["sitzung_fortsetzen"])  # Gegenprüfung in neuer Sitzung
        self.assertIn("literatur-1: YOLO erkennt", prompts[6])
        g = json.loads(erg.geprueft.read_text())
        self.assertEqual([a["status"] for a in g["aussagen"]], ["gesichert", "einschaetzung", "teilweise"])
        self.assertEqual(erg.usd, 7.0)
        self.assertIn("2 Fragen, 3 Aussagen (1 gesichert, 1 teilweise", erg.zeilen[0])
        self.assertTrue(erg.bericht.read_text().startswith("# Recherchebericht"))
        # neuer Anlauf: alles fertig, kein Claude-Lauf, gleiches Ergebnis
        self.aufrufe.clear()
        erg2 = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                      self.claude({}), seitentext, lambda d: META)
        self.assertEqual((self.aufrufe, erg2.usd), ([], 7.0))

    def test_kostengrenze_und_gescheitertes_fenster(self):
        antworten = {"eckpunkte": [ECK], "literatur": [{"kaputt": 1}], "gegenpruefung": []}
        with self.assertRaises(recherche.RechercheFehler) as f:  # kein Fenster mit Ergebnis
            recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                   self.claude(antworten, usd=4.0), seitentext, lambda d: META, grenze_usd=17)
        self.assertEqual(len(self.aufrufe), 4)  # Eckpunkte, Suche, weiter, Nachbesserung; Regelwerk nicht
        self.assertIn("Suchfenster Veröffentlichte Forschung gescheitert", str(f.exception))
        self.assertIn("Suchfenster Normen und Regelwerke nicht gestartet: Kostengrenze 17 USD (bisher 16.00 USD)",
                      str(f.exception))

    def test_ohne_ergebnis_fehler(self):
        with self.assertRaises(recherche.RechercheFehler):
            recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                   self.claude({"eckpunkte": [{"thema": ""}]}), seitentext, lambda d: META)


if __name__ == "__main__":
    unittest.main()
