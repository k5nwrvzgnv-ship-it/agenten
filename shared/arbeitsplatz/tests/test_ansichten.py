import unittest

import ansichten

GEPRUEFT = {
    "fragen": [{"id": "F1", "frage": "Wie <wirkt> Borsalz?"}, {"id": "F2", "frage": "Kosten?"}],
    "aussagen": [{"id": "A1", "frage": "F1", "text": "Borsalz wirkt", "status": "gesichert",
                  "belege": [{"zitat": "wirkt gut", "url": "https://doi.org/x", "pruefung": {"status": "bestanden"}},
                             {"zitat": "z", "url": "javascript:alert(1)", "datei": "quellen/abc.txt", "seite": 3}]},
                 {"id": "A2", "frage": "F2", "text": "teuer", "status": "unbelegt", "fehlt": "Preisangabe"},
                 {"id": "A3", "frage": "F9", "text": "ohne Frage", "status": "einschaetzung"}],
    "offen": [{"frage": "F2", "warum": "keine Daten"}],
    "quellen": [{"titel": "Alt", "jahr": 1990, "zitierfaehig": True}, {"titel": "Neu", "jahr": 2020,
                "zitierfaehig": True, "doi": "10.1000/x"}, {"titel": "Blog", "url": "https://b.de"}],
    "luecken": [{"text": "Langzeit fehlt"}], "widersprueche": [{"worum": "Dosis", "ids": ["A1", "A2"]}],
    "literatursuche": {"datenbank": "Scopus", "suchen": [{"nr": 1, "titel": "t", "suchstring": "s"}]},
}


class TestRecherche(unittest.TestCase):
    def test_aussagen_und_filter(self):
        r = ansichten.recherche(GEPRUEFT, None, None, None)
        self.assertEqual(r["ansicht"], "aussagen")
        self.assertEqual(r["zahlen"]["gesichert"], 1)
        g = r["inhalt"]["gruppen"]
        self.assertEqual([x["id"] for x in g], ["F1", "F2", ""])
        self.assertEqual(g[1]["offen"], ["keine Daten"])
        belege = g[0]["aussagen"][0]["belege"]
        self.assertEqual((belege[0]["link"], belege[1]["link"], belege[1]["datei"]), ("https://doi.org/x", None, "abc"))
        r = ansichten.recherche(GEPRUEFT, "aussagen", "unbelegt", "F2")
        self.assertEqual([a["id"] for x in r["inhalt"]["gruppen"] for a in x["aussagen"]], ["A2"])
        r = ansichten.recherche(GEPRUEFT, "aussagen", "quatsch", "F1; drop")
        self.assertEqual((r["inhalt"]["status"], r["inhalt"]["frage"]), (None, None))

    def test_andere_reiter(self):
        q = ansichten.recherche(GEPRUEFT, "quellen", None, None)["inhalt"]
        self.assertEqual([x["titel"] for x in q], ["Neu", "Alt", "Blog"])
        self.assertEqual(q[0]["doi_link"], "https://doi.org/10.1000/x")
        self.assertEqual(ansichten.recherche(GEPRUEFT, "luecken", None, None)["inhalt"]["luecken"], ["Langzeit fehlt"])
        self.assertEqual(ansichten.recherche(GEPRUEFT, "suche", None, None)["inhalt"]["datenbank"], "Scopus")
        self.assertEqual(ansichten.recherche({}, "unbekannt", None, None)["ansicht"], "aussagen")

    def test_pfade_aus_daten_ansicht(self):
        self.assertEqual(ansichten.recherche_ordner({"recherche": "data/recherchen/x/recherche"}),
                         "data/recherchen/x/recherche")
        for falsch in [{"recherche": "data/recherchen/../../.env"}, {"recherche": "/etc"}, {"recherche": "data/x"},
                       {"recherche": "data/recherchen//x"}, {"recherche": 3}, None, "x"]:
            self.assertIsNone(ansichten.recherche_ordner(falsch))
        self.assertEqual(ansichten.modul_und_uebung({"modul": "holzschutz", "uebung": "20261109-120000-abcdef"}),
                         ("holzschutz", "20261109-120000-abcdef"))
        self.assertEqual(ansichten.modul_und_uebung({"modul": "holzschutz"}), ("holzschutz", None))
        for falsch in [{"modul": "../x"}, {"modul": "holzschutz", "uebung": "../../x"}, {}, None]:
            self.assertIsNone(ansichten.modul_und_uebung(falsch))
        self.assertEqual(ansichten.portal_link("holzschutz", "20261109-120000-abcdef"),
                         "https://uni.meldro.de/modul/holzschutz/uebung/20261109-120000-abcdef")

    def test_markdown(self):
        b = ansichten.markdown_bloecke("# Titel\n\nText **fett**\nweiter\n\n- a\n- b\n")
        self.assertEqual([x["art"] for x in b], ["kopf", "absatz", "punkte"])
        self.assertEqual(b[1]["teile"][1], {"text": "fett", "fett": True})
        self.assertEqual(len(b[2]["punkte"]), 2)


class TestPruefung(unittest.TestCase):
    def test_ergebnis(self):
        auswertung = {"gesamt": "Gut", "punkte": [{"titel": "P1", "stufe": "erfuellt", "stufe_text": "erfüllt"}],
                      "luecken": [{"thema": "t1", "was": "a"}, {"thema": "t2", "was": "b"}],
                      "karten_neu": [{"thema": "t1", "frage": "F?", "antwort": "A"}, {"thema": "t2", "frage": "G?"}],
                      "karten_faellig": [{"karte": "k1"}]}
        plan = {"themen": [{"id": "t1", "titel": "Thema 1", "score": 2}, {"id": "t2", "titel": "Thema 2", "score": 5}]}
        e = ansichten.pruefung(auswertung, {"neu": {"0": True}}, plan, [{"id": "k1", "frage": "Was ist k1?"}])
        self.assertEqual([x["titel"] for x in e["luecken"]], ["Thema 2", "Thema 1"])
        self.assertEqual([(x["titel"], x["uebernommen"]) for x in e["neu"]], [("Thema 1", True), ("Thema 2", False)])
        self.assertEqual(e["faellig"][0]["frage"], "Was ist k1?")
        self.assertEqual(e["offen"], 2)
        self.assertEqual(ansichten.pruefung({}, {}, {}, [])["punkte"], [])


if __name__ == "__main__":
    unittest.main()
