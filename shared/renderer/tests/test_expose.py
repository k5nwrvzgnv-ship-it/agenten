"""Exposé: Prüfung (Fehler mit Pfad für Claude) und Bauen als docx (Deckblatt, Text, Literatur)."""

import copy
import unittest

from renderer import pruefen
from renderer.pruefung import lesen

EX = {
    "art": "expose",
    "titel": "Fehlstellen an Lamellen",
    "untertitel": "Ein Prototyp",
    "autoren": ["Anna Muster (Matr.-Nr. 1)", "Ben Beispiel (Matr.-Nr. [OFFEN: Nummer])"],
    "betreuung": ["Prof. Dr. C. Doe"],
    "einrichtung": "Fachbereich Holz",
    "rahmen": "Exposé | Wintersemester 2026/27\nStudiengang Holz (M. Sc.)\nModul Projekt",
    "datum": "02.11.2026",
    "bloecke": [
        {"typ": "ueberschrift", "text": "Ausgangslage"},
        {"typ": "absatz", "text": "Äste mindern die Festigkeit (Muster & Beispiel, 2021). [OFFEN: Zahl] Prozent."},
        {"typ": "ueberschrift", "text": "Ziel", "ebene": 2},
        {"typ": "liste", "punkte": ["Bilder", "Modell"], "nummeriert": True},
        {"typ": "ueberschrift", "text": "Vorgehen"},
        {"typ": "liste", "punkte": ["eins", "zwei"]},
        {"typ": "tabelle", "titel": "Zeitplan", "kopf": ["Zeitraum", "Schritt"],
         "zeilen": [["November", "Aufnahme"], ["Dezember", ""]]},
        {"typ": "tabelle", "zeilen": [["a", "b"]]},
    ],
    "literatur": ["Muster, A., & Beispiel, B. (2021). Titel. Verlag. https://doi.org/10.1000/xyz",
                  "Doe, C. (2020). Ohne Link. Verlag."],
}


def mit(**aenderungen) -> dict:
    """Kopie von EX, z. B. mit(b1={...}) ersetzt bloecke[1], mit(datum=...) ein Feld oben."""
    e = copy.deepcopy(EX)
    for name, wert in aenderungen.items():
        if name[0] == "b" and name[1:].isdigit():
            e["bloecke"][int(name[1:])] = wert
        else:
            e[name] = wert
    return e


class TestPruefung(unittest.TestCase):
    def test_gueltig_mit_standardwerten(self):
        b = lesen({"art": "expose", "titel": "T", "autoren": ["A"], "einrichtung": "E", "datum": "01.02.2026",
                   "bloecke": [{"typ": "tabelle", "zeilen": [["x"]]}]})
        self.assertEqual(b, {"art": "expose", "titel": "T", "untertitel": "", "einrichtung": "E", "rahmen": "",
                             "datum": "01.02.2026", "autoren": ["A"], "betreuung": [],
                             "bloecke": [{"typ": "tabelle", "titel": "", "kopf": None, "zeilen": [["x"]]}],
                             "literatur": []})

    def test_voll_gueltig(self):
        self.assertEqual(pruefen(EX), [])
        b = lesen(EX)
        self.assertEqual(b["bloecke"][3], {"typ": "liste", "nummeriert": True, "punkte": ["Bilder", "Modell"]})
        self.assertEqual(b["bloecke"][2]["ebene"], 2)

    def test_pflichtfelder(self):
        self.assertEqual(pruefen({"art": "expose"}),
                         ["titel: fehlt", "autoren: fehlt", "einrichtung: fehlt", "datum: fehlt", "bloecke: fehlt"])

    def test_kopf_fehler(self):
        f = pruefen(mit(autoren=[], betreuung=["x" * 101], datum="2.11.2026", rahmen="", quellen=[]))
        self.assertIn("quellen: unbekanntes Feld, erlaubt sind: art, titel, autoren, "
                      "einrichtung, datum, bloecke, untertitel, betreuung, rahmen, literatur", f)
        self.assertIn("autoren: muss 1 bis 8 Einträge haben, hat 0", f)
        self.assertIn("betreuung[0]: zu lang (101 Zeichen, höchstens 100)", f)
        self.assertIn('datum: muss ein Datum wie "20.10.2026" sein (TT.MM.JJJJ), ist "2.11.2026"', f)
        self.assertIn("rahmen: darf nicht leer sein", f)
        self.assertEqual(pruefen(mit(betreuung=[], literatur=[])), [])

    def test_bloecke_anderer_arten_nicht_erlaubt(self):
        f = pruefen(mit(b1={"typ": "hinweis", "art": "organisatorisch", "text": "x"}))
        self.assertEqual(f, ['bloecke[1].typ: muss einer von "ueberschrift", "absatz", "liste", "tabelle" sein, '
                             'ist "hinweis"'])

    def test_ueberschriften(self):
        f = pruefen(mit(b0={"typ": "ueberschrift", "text": "1.1 Start", "ebene": 2}))
        self.assertIn("bloecke[0].text: ohne Nummer schreiben, die Nummer setzt der Renderer", f)
        self.assertIn("bloecke[0].ebene: Ebene 2 vor der ersten Überschrift der Ebene 1, erst eine Überschrift "
                      "mit ebene 1 setzen", f)
        self.assertIn("bloecke[2].ebene: muss eine ganze Zahl von 1 bis 2 sein, ist 3",
                      pruefen(mit(b2={"typ": "ueberschrift", "text": "x", "ebene": 3})))

    def test_keine_belege(self):
        f = pruefen(mit(b1={"typ": "absatz", "text": "So gesagt [Transkript S. 4].", "quellen": []}))
        self.assertIn("bloecke[1].quellen: unbekanntes Feld, erlaubt sind: typ, text", f)
        self.assertIn("bloecke[1].text: Beleg aus Transkript oder Folien im Text, der gehört nicht ins Exposé "
                      "(nur ins Protokoll)", f)
        self.assertEqual(pruefen(mit(b3={"typ": "liste", "punkte": [{"text": "a"}]})),
                         ['bloecke[3].punkte[0]: muss ein Text sein, ist {"text": "a"}'])

    def test_tabelle(self):
        f = pruefen(mit(b6={"typ": "tabelle", "kopf": ["a", "b"], "zeilen": [["1"]], "erste_spalte_fett": True}))
        self.assertIn("bloecke[6].erste_spalte_fett: unbekanntes Feld, erlaubt sind: typ, zeilen, titel, kopf", f)
        self.assertIn("bloecke[6].zeilen[0]: hat 1 Zellen, erwartet 2 (wie kopf)", f)
        f = pruefen(mit(b6={"typ": "tabelle", "zeilen": [list("abcdefghi")]}))
        self.assertEqual(f, ["bloecke[6].zeilen[0]: muss 1 bis 8 Einträge haben, hat 9"])

    def test_literatur(self):
        f = pruefen(mit(literatur=["", "x" * 1001] + ["y"] * 49))
        self.assertEqual(f, ["literatur: muss 0 bis 50 Einträge haben, hat 51"])
        f = pruefen(mit(literatur=["", "x" * 1001]))
        self.assertEqual(f, ["literatur[0]: darf nicht leer sein", "literatur[1]: zu lang (1001 Zeichen, höchstens 1000)"])


if __name__ == "__main__":
    unittest.main()
