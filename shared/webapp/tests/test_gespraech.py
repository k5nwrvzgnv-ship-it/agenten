import unittest

import gespraech as g


def t(text, **f):
    return {"text": text, "fett": f.get("fett", False), "kursiv": f.get("kursiv", False), "code": f.get("code", False),
            **({"link": f["link"]} if "link" in f else {})}


class Bloecke(unittest.TestCase):
    def test_absatz_und_inline(self):
        self.assertEqual(g.bloecke("**Kant** sagt *Würde*\nund `x`."), [
            {"absatz": [t("Kant", fett=True), t(" sagt "), t("Würde", kursiv=True), t(" "), t("und "),
                        t("x", code=True), t(".")]}])
        # Sternchen mitten im Wort und einzelne bleiben stehen
        self.assertEqual(g.bloecke("3 * 4 und Lehrer*innen"), [{"absatz": [t("3 * 4 und Lehrer*innen")]}])

    def test_ueberschriften_listen_zitat_linie(self):
        b = g.bloecke("# A\n### B\n- eins\n  weiter\n- zwei\n1. erst\n2) dann\n> Zitat\n> zwei\n---\nEnde")
        self.assertEqual(b, [
            {"ueberschrift": [t("A")], "stufe": 2}, {"ueberschrift": [t("B")], "stufe": 3},
            {"punkte": [[t("eins"), t(" "), t("weiter")], [t("zwei")]], "nummeriert": False},
            {"punkte": [[t("erst")], [t("dann")]], "nummeriert": True},
            {"zitat": [t("Zitat zwei")]}, {"linie": True}, {"absatz": [t("Ende")]}])

    def test_tabelle(self):
        b = g.bloecke("Vergleich:\n| Theorie | Zweck |\n|---|:--:|\n| **Kant** | Vergeltung |\n| Feuerbach |\n\nNach")
        self.assertEqual(b, [
            {"absatz": [t("Vergleich:")]},
            {"tabelle": {"kopf": [[t("Theorie")], [t("Zweck")]],
                         "zeilen": [[[t("Kant", fett=True)], [t("Vergeltung")]], [[t("Feuerbach")], []]]}},
            {"absatz": [t("Nach")]}])
        # ohne Trennzeile keine Tabelle
        self.assertEqual(g.bloecke("| a | b |"), [{"absatz": [t("| a | b |")]}])

    def test_baustein(self):
        b = g.bloecke("Vorschlag:\n```baustein reihenfrage\nIst Strafe **gerecht**?\n```\n```baustein unbekannt\n- a\n```")
        self.assertEqual(b[0], {"absatz": [t("Vorschlag:")]})
        rf, tx = g.bausteine_von(b)
        self.assertEqual((rf["art"], rf["name"], rf["kopie"]), ("reihenfrage", "Reihenfrage", "Ist Strafe gerecht?"))
        self.assertEqual(rf["bloecke"], [{"absatz": [t("Ist Strafe "), t("gerecht", fett=True), t("?")]}])
        self.assertEqual((tx["art"], tx["kopie"]), ("text", "– a"))

    def test_code_und_offener_zaun(self):
        self.assertEqual(g.bloecke("```python\nx = '<b>'\n```"), [{"code": "x = '<b>'"}])
        self.assertEqual(g.bloecke("```baustein merksatz\nOffen"), [
            {"baustein": {"art": "merksatz", "name": "Merksatz", "bloecke": [{"absatz": [t("Offen")]}],
                          "kopie": "Offen"}}])
        self.assertEqual(g.bloecke(""), [])

    def test_links(self):
        self.assertEqual(g.bloecke("[KMK](https://kmk.org/a) und [x](javascript:1)"), [
            {"absatz": [t("KMK", link="https://kmk.org/a"), t(" und [x](javascript:1)")]}])
        self.assertEqual(g.klartext("Siehe [KMK](https://kmk.org) und **fett**\n1. eins"), "Siehe KMK und fett\n1. eins")


GRUPPEN = [{"gruppe_id": "ethik-8", "gruppe": "Klasse 8", "fach": "Ethik", "fach_id": "ethik", "archiv": False}]
REIHEN = [{"id": "strafe", "titel": "Straftheorien", "gruppe_id": "ethik-8", "gruppe": "Klasse 8", "fach": "Ethik",
           "archiv": False, "agenten": [], "stunden": [{"id": "s1", "thema": "Einstieg"}, {"id": "s2", "thema": ""}]}]


class Orte(unittest.TestCase):
    def test_orte_kette_darunter(self):
        o = g.orte(REIHEN, GRUPPEN)
        self.assertEqual(set(o), {"ethik-8", "strafe", "s1", "s2"})
        self.assertEqual((o["s1"]["name"], o["s1"]["pfad"], o["s1"]["link"]),
                         ("Stunde 1: Einstieg", "Ethik › Klasse 8 › Straftheorien › Stunde 1", "/reihe/strafe/stunde/1"))
        self.assertEqual(o["s2"]["name"], "Stunde 2")
        self.assertEqual([x["id"] for x in g.kette(o, "s2")], ["ethik-8", "strafe", "s2"])
        self.assertEqual(g.kette(o, "fehlt"), [])
        self.assertEqual(g.darunter(o, "ethik-8"), ["strafe", "s1", "s2"])
        theater = {**REIHEN[0], "id": "w", "agenten": ["theater"], "stunden": [{"id": "p1", "thema": "Akt 1"}]}
        self.assertEqual(g.orte([theater], GRUPPEN)["p1"]["name"], "Probe 1: Akt 1")


if __name__ == "__main__":
    unittest.main()
