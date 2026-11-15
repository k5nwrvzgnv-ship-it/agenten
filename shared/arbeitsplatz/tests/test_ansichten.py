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


def projekt_basis():
    """Kleine Wissensbasis wie aus lia/recherche: ein Fall mit Webbeleg, eine Stelle aus dem Register."""
    from agentkit import recherche
    ok = {"status": "bestanden", "grund": ""}
    b = recherche.neu("milde-taten", "Milde <Taten>", "lia", "recherche", fach="Ethik")
    recherche.einarbeiten(b, {"art": "suche", "datum": "2026-11-14T13:07:48", "usd": 2.6268, "modell": "opus",
                              "zusammenfassung": "Sechs Fälle."}, {
        "fragen": [{"id": "F1", "frage": "Welche Fälle?"}],
        "quellen": [{"url": "https://www.presseportal.de/x", "titel": "Freibad"}],
        "aussagen": [
            {"frage": "F1", "art": "fall", "text": "Einbruch ins Freibad.",
             "belege": [{"url": "https://www.presseportal.de/x", "zitat": "brachen ein", "pruefung": ok}],
             "traegt": {"urteil": "teilweise", "fehlt": "Alter"}},
            {"frage": None, "art": "tatsache", "text": "Kant: Mittel.",
             "belege": [{"register": "kant", "zitat": "niemals", "seite": 331, "pruefung": ok}],
             "traegt": {"urteil": "ja", "fehlt": ""}},
            {"frage": "F1", "art": "fall", "text": "Graffiti.",
             "belege": [{"url": "javascript:alert(1)", "zitat": "z", "pruefung": {"status": "durchgefallen",
                                                                              "grund": "nicht auf der Seite"}}]}],
        "luecken": ["Kein Fall aus Berlin."], "rueckfragen": ["Auch 18-Jährige?"]})
    recherche.entscheiden(b, "jan", "sperren", "Q3")
    return b, recherche.zahlen(b)


class TestProjekt(unittest.TestCase):
    def test_aussagen(self):
        b, z = projekt_basis()
        p = ansichten.projekt(b, z, None, None, None)
        self.assertEqual((p["ansicht"], p["fuer"], p["fach"], p["usd"], p["laeufe"]),
                         ("aussagen", "Lia", "Ethik", "2,63 USD", 1))
        g = p["inhalt"]["gruppen"]
        self.assertEqual([x["id"] for x in g], ["F1", ""])
        fall = g[0]["aussagen"][0]
        self.assertEqual((fall["art"], fall["status"], fall["fehlt"], fall["lauf"]), ("Fall", "teilweise", "Alter", 1))
        self.assertEqual((fall["belege"][0]["name"], fall["belege"][0]["link"]), ("Freibad", "https://www.presseportal.de/x"))
        graffiti = g[0]["aussagen"][1]["belege"][0]
        self.assertEqual((graffiti["link"], graffiti["bestanden"], graffiti["gesperrt"], graffiti["vermerk"]),
                         (None, False, True, "nicht auf der Seite"))
        kant = g[1]["aussagen"][0]
        self.assertEqual((kant["status"], kant["belege"][0]["name"], kant["belege"][0]["link"]),
                         ("gesichert", "Register kant", None))
        nur = ansichten.projekt(b, z, "aussagen", "gesichert", "F1")["inhalt"]
        self.assertEqual((nur["frage"], nur["status"], nur["anzahl"]), ("F1", "gesichert", 0))

    def test_quellen_offen_laeufe(self):
        b, z = projekt_basis()
        q = ansichten.projekt(b, z, "quellen", None, None)["inhalt"]
        self.assertEqual([(x["id"], x["stuetzt"], x["gesperrt"]) for x in q],
                         [("Q1", 1, False), ("Q2", 1, False), ("Q3", 0, True)])
        self.assertTrue(q[1]["register"])
        self.assertEqual(q[1]["url"], "")
        o = ansichten.projekt(b, z, "offen", None, None)["inhalt"]
        self.assertEqual((o["luecken"][0]["text"], o["rueckfragen"][0]["lauf"], o["widersprueche"]),
                         ("Kein Fall aus Berlin.", 1, []))
        lauf = ansichten.projekt(b, z, "laeufe", None, None)["inhalt"][0]
        self.assertEqual((lauf["art"], lauf["datum"], lauf["usd"], lauf["neu_aussagen"], lauf["zusammenfassung"]),
                         ("Suche", "14.11.2026 13:07", "2,63 USD", 3, "Sechs Fälle."))
        self.assertEqual(ansichten.projekt(b, z, "unsinn", None, None)["ansicht"], "aussagen")

    def test_zeile_und_formate(self):
        b, z = projekt_basis()
        zeile = ansichten.projekt_zeile(b, "lia", z)
        self.assertEqual((zeile["titel"], zeile["fuer"], zeile["laeufe"], zeile["zuletzt"], zeile["aussagen"]),
                         ("Milde <Taten>", "Lia", 1, "14.11.2026 13:07", 3))
        self.assertEqual(ansichten.datum_text("2026-11-02"), "02.11.2026")
        self.assertEqual(ansichten.datum_text(None), "")
        self.assertEqual(ansichten.usd_text(None), "")


if __name__ == "__main__":
    unittest.main()
