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
ABSTRACT = "Only the abstract says that knots in lamellae are found reliably."
SCOPUS_CSV = ('"Authors","Title","Year","Source title","Cited by","DOI","Link","Abstract","EID"\n'
              f'"Muster A.","Knot detection with YOLO","2023","Wood Science","12","10.1234/ABC","https://x",'
              f'"{ABSTRACT}","2-s2.0-1"\n')
SC = {"aussagen": [{"frage": "F1", "art": "tatsache", "text": "Äste in Lamellen werden zuverlässig erkannt.",
                    "belege": [{"url": "https://doi.org/10.1234/abc", "zitat": "knots in lamellae are found reliably"}]}],
      "quellen": [{"url": "https://doi.org/10.1234/abc", "titel": "Knot detection with YOLO", "autoren": ["Muster, A."],
                   "jahr": 2023, "doi": "10.1234/ABC", "art": "artikel"}],
      "luecken": ["Keine Studie mit Smartphones"]}
SUCHEN = {f"S{i}": {"titel": f"Suche {i}", "fragen": ["F1"], "suchstring": f'TITLE-ABS-KEY(knot* AND "wood {i}")'}
          for i in (1, 2, 3)}


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

    def test_abstract_aus_scopus(self):
        ab = {"doi:10.1234/abc": ABSTRACT}
        b = {"url": "https://doi.org/10.1234/ABC", "zitat": "knots in lamellae are found reliably"}
        p = recherche.beleg_pruefen(b, self.hier, seitentext, ab)
        self.assertEqual((p["status"], p["vermerk"]), ("bestanden", "Zitat im Abstract laut Scopus-Export gefunden"))
        p = recherche.beleg_pruefen({**b, "zitat": "YOLO detects knots with high precision"}, self.hier, seitentext, ab)
        self.assertEqual(p["vermerk"], "Zitat auf der Seite gefunden")  # nicht im Abstract: Seite laden
        self.assertEqual(recherche.beleg_pruefen(b, self.hier, seitentext)["status"], "durchgefallen")

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

    def test_nachgereichte_norm_aus_der_ablage(self):
        g = self.geprueft()
        norm = ["DIN EN 14080:2013-09, Holzbauwerke – Brettschichtholz und Balkenschichtholz"]
        self.assertEqual(len(recherche.literatur_pruefen(norm, g)), 1)
        self.assertEqual(recherche.literatur_pruefen(norm, g, {"DIN EN 14080"}), [])
        self.assertEqual(len(recherche.literatur_pruefen(["DIN EN 9999:2020"], g, {"DIN EN 14080"})), 1)

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
            name = re.search(r"recherche/([\w/]+)\.json", prompt).group(1)
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

    def test_scopus_als_nachtrag(self):
        antworten = {"eckpunkte": [ECK], "literatur": [LIT, LIT], "regelwerk": [REG, REG],
                     "gegenpruefung": [self.gegen()]}
        recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"}, self.claude(antworten),
                               seitentext, lambda d: META)
        export = self.ordner / "recherche" / "scopus"
        export.mkdir()
        (export / "eins.csv").write_text(SCOPUS_CSV)
        self.aufrufe.clear()
        gegen = self.gegen()
        gegen["urteile"].append({"id": "scopus-1", "traegt": "ja", "fehlt": ""})
        erg = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                     self.claude({"scopus": [SC, SC], "gegenpruefung": [gegen]}), seitentext,
                                     lambda d: META)
        prompts = [p for p, _ in self.aufrufe]
        self.assertEqual(len(prompts), 3)  # Scopus, weiter, Gegenprüfung noch einmal
        for teil in ("data/expose/k1/recherche/scopus.md enthält 1 Arbeiten", "recherche/literatur-geprueft.json",
                     "F1 (literatur)"):
            self.assertIn(teil, prompts[0])
        self.assertNotIn("F2 (regelwerk): Was", prompts[0].split("Alle Fragen")[0])
        self.assertIn("scopus-1: Äste in Lamellen", prompts[2])
        g = json.loads(erg.geprueft.read_text())
        a = next(a for a in g["aussagen"] if a["id"] == "scopus-1")
        self.assertEqual((a["status"], a["belege"][0]["pruefung"]["vermerk"]),
                         ("gesichert", "Zitat im Abstract laut Scopus-Export gefunden"))
        self.assertEqual(g["literatursuche"]["arbeiten_ohne_doppelte"], 1)
        md = erg.bericht.read_text()
        for teil in ("## Systematische Literatursuche (Scopus)", "als Quelle verwendet: 1 Arbeiten",
                     "- Systematische Literatursuche (Scopus): Keine Studie mit Smartphones"):
            self.assertIn(teil, md)
        self.assertEqual(recherche.literatur_pruefen(["Muster (2023). https://doi.org/10.1234/abc"], g), [])

    def test_scopus_nachtrag_offen(self):
        r = self.ordner / "recherche"
        (r / "scopus").mkdir(parents=True)
        self.assertFalse(recherche.scopus_nachtrag(self.ordner))  # noch keine Recherche
        (r / "stand.json").write_text(json.dumps({"usd": 1.0, "fertig": ["eckpunkte", "scopus"]}))
        self.assertFalse(recherche.scopus_nachtrag(self.ordner))  # kein Export
        (r / "scopus" / "eins.csv").write_text(SCOPUS_CSV)
        self.assertFalse(recherche.scopus_nachtrag(self.ordner))  # schon ausgewertet
        self.assertTrue(recherche.scopus_nachtrag(self.ordner, neu=True))  # neue Dateien: noch einmal
        self.assertEqual(json.loads((r / "stand.json").read_text())["fertig"], ["eckpunkte"])

    def test_scopus_suchen_gehen_als_chrome_prompt_an_jan(self):
        gemeldet = []
        antworten = {"eckpunkte": [ECK], "scopus/suchen": [SUCHEN], "literatur": [LIT, LIT], "regelwerk": [REG, REG],
                     "gegenpruefung": [self.gegen()]}
        erg = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                     self.claude(antworten), seitentext, lambda d: META,
                                     melden=lambda text, datei: gemeldet.append((text, datei)))
        self.assertIn("F1 (literatur)", self.aufrufe[1][0])
        self.assertNotIn("F2 (regelwerk)", self.aufrufe[1][0])
        self.assertEqual(len(self.aufrufe), 7)
        (text, datei), = gemeldet
        self.assertIn("3 Suchen in Scopus", text)
        self.assertIn('S2 Suche 2\nTITLE-ABS-KEY(knot* AND "wood 2")', datei.read_text())
        self.assertNotIn("Scopus", erg.bericht.read_text())  # ohne Export kein Abschnitt
        self.aufrufe.clear()
        recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"}, self.claude({}), seitentext,
                               lambda d: META, melden=lambda text, datei: gemeldet.append((text, datei)))
        self.assertEqual((self.aufrufe, len(gemeldet)), ([], 1))  # neuer Anlauf: nicht noch einmal

    def test_ungueltige_scopus_suchen_keine_meldung(self):
        gemeldet = []
        kaputt = {"S1": {"titel": "x", "fragen": ["F1"], "suchstring": "AUTHOR(x)"}}
        antworten = {"eckpunkte": [ECK], "scopus/suchen": [kaputt, kaputt], "literatur": [LIT, LIT],
                     "regelwerk": [REG, REG], "gegenpruefung": [self.gegen()]}
        erg = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                     self.claude(antworten), seitentext, lambda d: META,
                                     melden=lambda text, datei: gemeldet.append((text, datei)))
        self.assertEqual(gemeldet, [])
        self.assertIn("Keine Scopus-Suchen vorgeschlagen", "\n".join(erg.zeilen))
        self.assertFalse((self.ordner / "recherche" / "scopus" / "suchen.json").exists())

    def test_meldung_scheitert_recherche_laeuft_weiter(self):
        def melden(text, datei):
            raise OSError("Zentrale weg")
        antworten = {"eckpunkte": [ECK], "scopus/suchen": [SUCHEN], "literatur": [LIT, LIT], "regelwerk": [REG, REG],
                     "gegenpruefung": [self.gegen()]}
        erg = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                     self.claude(antworten), seitentext, lambda d: META, melden=melden)
        self.assertIn("Scopus-Prompt nicht gemeldet (Zentrale weg), liegt unter data/expose/k1/recherche/scopus/"
                      "chrome-prompt.txt", "\n".join(erg.zeilen))

    def test_export_im_eingang_wird_im_ersten_durchgang_ausgewertet(self):
        eingang = self.hier / "data" / "scopus"
        eingang.mkdir(parents=True)
        (eingang / "eins.csv").write_text(SCOPUS_CSV)
        (eingang / "scopus_protokoll.txt").write_text("Scopus-Export, Datum: 03.11.2026\nS1 | 57 | 1 | eins.csv |\n")
        gegen = self.gegen()
        gegen["urteile"].append({"id": "scopus-1", "traegt": "ja", "fehlt": ""})
        antworten = {"eckpunkte": [ECK], "literatur": [LIT, LIT], "regelwerk": [REG, REG], "scopus": [SC, SC],
                     "gegenpruefung": [gegen]}
        erg = recherche.durchfuehren(self.hier, self.ordner, {"id": "k1", "text": "Exposé: x"},
                                     self.claude(antworten), seitentext, lambda d: META, eingang=eingang)
        self.assertEqual(list(eingang.iterdir()), [])
        md = erg.bericht.read_text()
        self.assertIn("Suche in Scopus am 03.11.2026", md)
        self.assertIn("| S1 | eins.csv | 57 | 1 |", md)

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
