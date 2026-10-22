"""Prüfung der Beschreibung: gültige Beschreibungen mit Standardwerten, klare Fehler mit Pfad."""

import copy
import json
import unittest

from renderer import BeschreibungUngueltig, pruefen
from renderer.pruefung import lesen

BLATT = {
    "art": "arbeitsblatt",
    "titel": "Muss ich Fremden in Not genauso helfen wie Nahestehenden?",
    "nummer": "5",
    "bloecke": [
        {"typ": "merksatz", "titel": "Merksatz zu Peter Singer:", "text": "Ist die Not groß ..."},
        {"typ": "anweisung", "text": "Lies das Beispiel und bearbeite die Aufgaben!"},
        {"typ": "material", "titel": "Beispiel", "text": "Yasmins großer Bruder ...\nzweite Zeile"},
        {"typ": "aufgaben", "aufgaben": [
            {"text": "Unterstreiche im Text!", "hilfe": "Zeilen 1-2"},
            {"text": "Kreuze an!", "antwort": {"art": "ankreuzen", "optionen": ["Bruder", "Obdachlose"]}},
            {"text": "Begründe!", "antwort": {"art": "satzanfaenge", "saetze": [
                {"anfang": "Nach Peter Singer sollte Yasmin", "linien": 2}, {"anfang": "Zum Beispiel", "linien": 3}]}},
            {"text": "Erkläre.", "antwort": {"art": "linien", "anzahl": 5}},
            {"text": "Zeichne.", "antwort": {"art": "kasten", "hoehe_cm": 6.5}},
        ]},
        {"typ": "neue_seite", "querformat": True},
        {"typ": "ueberschrift", "text": "Wem sollte Yasmin helfen?"},
        {"typ": "tabelle", "kopf": ["", "Singer"], "zeilen": [["Behauptung", ""]], "zeilenhoehe_cm": 4,
         "erste_spalte_fett": True},
        {"typ": "absatz", "text": "Text"},
        {"typ": "liste", "punkte": ["a", "b"]},
    ],
}

FOLIEN = {
    "art": "folien",
    "titel": "Der kategorische Imperativ",
    "folien": [{"titel": "Was ist eine Maxime?", "inhalt": [{"typ": "punkte", "punkte": ["Regel", "subjektiv"]}]},
               {"titel": "Fragen?", "icons": ["frage"], "inhalt": [{"typ": "zentriert", "absaetze": ["Fragen?"]}]}],
}


def blatt_mit(**aenderungen):
    """Kopie von BLATT, Blöcke per Index ersetzbar: blatt_mit(b2={...})."""
    d = copy.deepcopy(BLATT)
    for name, wert in aenderungen.items():
        if name.startswith("b") and name[1:].isdigit():
            d["bloecke"][int(name[1:])] = wert
        else:
            d[name] = wert
    return d


def aufgaben(*liste, **mehr):
    return {"typ": "aufgaben", "aufgaben": list(liste), **mehr}


class TestGueltig(unittest.TestCase):
    def test_arbeitsblatt_mit_standardwerten(self):
        e = lesen(BLATT)
        self.assertEqual(e["nummer"], "5")
        b = e["bloecke"]
        self.assertEqual(b[0], {"typ": "merksatz", "titel": "Merksatz zu Peter Singer:", "text": "Ist die Not groß ..."})
        self.assertEqual(b[1], {"typ": "anweisung", "text": "Lies das Beispiel und bearbeite die Aufgaben!"})
        a = b[3]
        self.assertEqual(a["titel"], "Aufgaben:")
        self.assertEqual(a["aufgaben"][0], {"text": "Unterstreiche im Text!", "antwort": None, "hilfe": "Zeilen 1-2"})
        self.assertEqual(a["aufgaben"][1]["antwort"], {"art": "ankreuzen", "optionen": ["Bruder", "Obdachlose"]})
        self.assertEqual(a["aufgaben"][2]["antwort"]["saetze"][1], {"anfang": "Zum Beispiel", "linien": 3})
        self.assertEqual(a["aufgaben"][3]["hilfe"], "")
        self.assertEqual(b[4], {"typ": "neue_seite", "querformat": True})
        self.assertEqual(b[5]["ebene"], 1)
        self.assertEqual((b[6]["zeilenhoehe_cm"], b[6]["erste_spalte_fett"]), (4, True))
        self.assertEqual(b[8]["nummeriert"], False)

    def test_ohne_optionale_felder(self):
        d = blatt_mit(b0={"typ": "merksatz", "text": "x"}, b4={"typ": "neue_seite"},
                      b6={"typ": "tabelle", "zeilen": [["a", "b"], ["c", "d"]]})
        del d["nummer"]
        e = lesen(d)
        self.assertEqual(e["nummer"], "")
        self.assertEqual(e["bloecke"][0]["titel"], "")
        self.assertEqual(e["bloecke"][4]["querformat"], False)
        self.assertEqual(e["bloecke"][6], {"typ": "tabelle", "kopf": None, "zeilen": [["a", "b"], ["c", "d"]],
                                           "zeilenhoehe_cm": None, "erste_spalte_fett": False})

    def test_aufgaben_ohne_ueberschrift(self):
        e = lesen(blatt_mit(b3=aufgaben({"text": "x"}, titel="")))
        self.assertEqual(e["bloecke"][3]["titel"], "")

    def test_folien_mit_standardwerten(self):
        e = lesen(FOLIEN)
        self.assertEqual((e["untertitel"], e["icon"]), ("", None))
        self.assertEqual(e["folien"][0]["icons"], [])
        self.assertEqual(e["folien"][1]["inhalt"][0]["absaetze"],
                         [[{"text": "Fragen?", "fett": False, "farbe": None, "unterstrichen": False}]])

    def test_json_text_und_dict_gleich(self):
        self.assertEqual(lesen(json.dumps(BLATT)), lesen(BLATT))
        self.assertEqual(pruefen(json.dumps(FOLIEN)), [])

    def test_eingabe_bleibt_unveraendert(self):
        d = copy.deepcopy(BLATT)
        lesen(d)
        self.assertEqual(d, BLATT)


class TestFehler(unittest.TestCase):
    def fehler(self, beschreibung) -> list[str]:
        f = pruefen(beschreibung)
        self.assertTrue(f, "Fehler erwartet")
        return f

    def test_kaputtes_json_mit_zeile_und_spalte(self):
        f = self.fehler('{\n  "art": "folien",\n  "titel": "x"\n  "folien": []\n}')
        self.assertEqual(len(f), 1)
        self.assertIn("kein gültiges JSON (Zeile 4, Spalte 3", f[0])

    def test_doppeltes_feld(self):
        self.assertIn('Beschreibung: Feld "titel" kommt in einem Objekt doppelt vor',
                      self.fehler('{"art": "folien", "titel": "a", "titel": "b", "folien": [{"titel": "x"}]}'))

    def test_kein_objekt(self):
        self.assertEqual(self.fehler("[1, 2]"), ["Beschreibung: muss ein Objekt {...} sein, ist [1, 2]"])

    def test_art_fehlt_oder_falsch(self):
        self.assertEqual(self.fehler({"titel": "x"}), ['art: fehlt, erlaubt sind "arbeitsblatt", "folien" oder "zusammenfassung"'])
        self.assertEqual(self.fehler({"art": "brief"}),
                         ['art: muss "arbeitsblatt", "folien" oder "zusammenfassung" sein, ist "brief"'])

    def test_unbekanntes_feld_mit_tippfehler_hinweis(self):
        f = self.fehler(blatt_mit(b8={"typ": "liste", "punkt": ["a"]}))
        self.assertIn('bloecke[8].punkt: unbekanntes Feld (gemeint: "punkte"?), erlaubt sind: typ, punkte, nummeriert',
                      f)
        self.assertIn("bloecke[8].punkte: fehlt", f)

    def test_alte_felder_sind_fehler(self):
        f = self.fehler(blatt_mit(kopfzeile=["Name"], b5={"typ": "aufgabe", "text": "x"}))
        self.assertIn("kopfzeile: unbekanntes Feld, erlaubt sind: art, titel, bloecke, nummer", f)
        self.assertIn('bloecke[5].typ: muss einer von "ueberschrift", "absatz", "liste", "tabelle", "merksatz", '
                      '"anweisung", "material", "aufgaben", "neue_seite" sein, ist "aufgabe" (gemeint: "aufgaben"?)', f)

    def test_alle_fehler_auf_einmal(self):
        d = blatt_mit(titel="", b5={"typ": "ueberschrift", "text": "x", "ebene": 4},
                      b3=aufgaben({"text": "x", "antwort": {"art": "linien", "anzahl": "fünf"}}))
        self.assertEqual(self.fehler(d), [
            "titel: darf nicht leer sein",
            'bloecke[3].aufgaben[0].antwort.anzahl: muss eine ganze Zahl von 1 bis 30 sein, ist "fünf"',
            "bloecke[5].ebene: muss eine ganze Zahl von 1 bis 3 sein, ist 4",
        ])

    def test_exception_nennt_alle_fehler(self):
        with self.assertRaises(BeschreibungUngueltig) as ctx:
            lesen({"art": "folien", "folien": []})
        self.assertEqual(ctx.exception.fehler, ["titel: fehlt", "folien: muss 1 bis 50 Einträge haben, hat 0"])
        self.assertEqual(str(ctx.exception),
                         "Beschreibung ungültig, bitte korrigieren:\n- titel: fehlt\n"
                         "- folien: muss 1 bis 50 Einträge haben, hat 0")

    def test_falsche_typen(self):
        f = self.fehler(blatt_mit(nummer=5, b1={"typ": "anweisung", "text": 5},
                                  b8={"typ": "liste", "punkte": ["a"], "nummeriert": "ja"}, b4={"typ": "neue_seite",
                                                                                                "querformat": 1},
                                  b6="Tabelle"))
        self.assertIn("nummer: muss ein Text sein, ist 5", f)
        self.assertIn("bloecke[1].text: muss ein Text sein, ist 5", f)
        self.assertIn('bloecke[8].nummeriert: muss true oder false sein, ist "ja"', f)
        self.assertIn("bloecke[4].querformat: muss true oder false sein, ist 1", f)
        self.assertIn('bloecke[6]: muss ein Objekt {...} sein, ist "Tabelle"', f)

    def test_aufgaben_fehler(self):
        f = self.fehler(blatt_mit(b3=aufgaben("x", {"txt": "y"}, {"text": "z", "hilfe": ""})))
        self.assertEqual(f, [
            'bloecke[3].aufgaben[0]: muss ein Objekt {...} sein, ist "x"',
            'bloecke[3].aufgaben[1].txt: unbekanntes Feld (gemeint: "text"?), erlaubt sind: text, antwort, hilfe',
            "bloecke[3].aufgaben[1].text: fehlt",
            "bloecke[3].aufgaben[2].hilfe: darf nicht leer sein",
        ])
        self.assertEqual(self.fehler(blatt_mit(b3=aufgaben())),
                         ["bloecke[3].aufgaben: muss 1 bis 20 Einträge haben, hat 0"])

    def test_wahrheitswert_ist_keine_zahl(self):
        self.assertEqual(self.fehler(blatt_mit(b3=aufgaben({"text": "x",
                                                            "antwort": {"art": "kasten", "hoehe_cm": True}}))),
                         ["bloecke[3].aufgaben[0].antwort.hoehe_cm: muss eine Zahl von 1 bis 25 sein, ist true"])

    def test_nan_ist_keine_zahl(self):
        text = json.dumps(BLATT).replace('"hoehe_cm": 6.5', '"hoehe_cm": NaN')
        self.assertEqual(self.fehler(text),
                         ["bloecke[3].aufgaben[4].antwort.hoehe_cm: muss eine Zahl von 1 bis 25 sein, ist NaN"])

    def test_antwortarten(self):
        def antwort_fehler(antwort):
            return self.fehler(blatt_mit(b3=aufgaben({"text": "x", "antwort": antwort})))

        p = "bloecke[3].aufgaben[0].antwort"
        self.assertEqual(antwort_fehler({"art": "punkte"}),
                         [f'{p}.art: muss einer von "linien", "kasten", "ankreuzen", "satzanfaenge" sein, '
                          'ist "punkte"'])
        self.assertEqual(antwort_fehler({"art": "kasten", "anzahl": 3}),
                         [f"{p}.anzahl: unbekanntes Feld, erlaubt sind: art, hoehe_cm", f"{p}.hoehe_cm: fehlt"])
        self.assertEqual(antwort_fehler({"art": "ankreuzen", "optionen": ["nur eine"]}),
                         [f"{p}.optionen: muss 2 bis 6 Einträge haben, hat 1"])
        self.assertEqual(antwort_fehler({"art": "satzanfaenge", "saetze": [{"anfang": "Ich", "linien": 0}, "x"]}),
                         [f"{p}.saetze[0].linien: muss eine ganze Zahl von 1 bis 10 sein, ist 0",
                          f'{p}.saetze[1]: muss ein Objekt {{...}} sein, ist "x"'])
        self.assertEqual(antwort_fehler({"art": "satzanfang", "saetze": []}),
                         [f'{p}.art: muss einer von "linien", "kasten", "ankreuzen", "satzanfaenge" sein, '
                          'ist "satzanfang" (gemeint: "satzanfaenge"?)'])

    def test_tabelle(self):
        f = self.fehler(blatt_mit(b6={"typ": "tabelle", "kopf": ["a", "b"], "zeilen": [["1", "2"], ["3"]]}))
        self.assertEqual(f, ["bloecke[6].zeilen[1]: hat 1 Zellen, erwartet 2 (wie kopf)"])
        f = self.fehler(blatt_mit(b6={"typ": "tabelle", "zeilen": [["1", "2"], ["3", "4", "5"]]}))
        self.assertEqual(f, ["bloecke[6].zeilen[1]: hat 3 Zellen, erwartet 2 (wie zeilen[0])"])
        f = self.fehler(blatt_mit(b6={"typ": "tabelle", "zeilen": [["1"]], "zeilenhoehe_cm": 20}))
        self.assertEqual(f, ["bloecke[6].zeilenhoehe_cm: muss eine Zahl von 0.5 bis 15 sein, ist 20"])

    def test_laenge_und_steuerzeichen(self):
        f = self.fehler(blatt_mit(titel="x" * 201, b8={"typ": "absatz", "text": "a\x07b"}))
        self.assertIn("titel: zu lang (201 Zeichen, höchstens 200)", f)
        self.assertIn("bloecke[8].text: enthält Steuerzeichen (erlaubt sind nur Zeilenumbruch und Tab)", f)

    def test_folien_fehler(self):
        f = self.fehler({"art": "folien", "titel": "x", "untertitel": 3, "icon": "hand",
                         "folien": [{"titel": "a", "inhalt": []}, {"inhalt": [{"typ": "text", "text": "y"}]}, "b",
                                    {"titel": "c", "icons": ["ziel", "uhr", "stern"], "inhalt": [{"typ": "bild"}]}]})
        self.assertEqual(f[0], "untertitel: muss ein Text sein, ist 3")
        self.assertTrue(f[1].startswith('icon: kein Icon dieses Namens: "hand" (gemeint: "haken"?), erlaubt sind: '
                                        "achtung, aufgabe"))
        self.assertEqual(f[2:], [
            "folien[0].inhalt: muss 1 bis 4 Einträge haben, hat 0",
            "folien[1].titel: fehlt",
            'folien[2]: muss ein Objekt {...} sein, ist "b"',
            "folien[3].icons: muss 1 bis 2 Einträge haben, hat 3",
            'folien[3].inhalt[0].typ: muss einer von "text", "punkte", "kasten", "leitfrage", "zentriert", "zeit", '
            '"spalten", "auswahl", "satzanfang", "feedback", "legende" sein, ist "bild"',
        ])

    def test_folien_elemente(self):
        def fehler(*inhalt):
            return self.fehler({"art": "folien", "titel": "x", "folien": [{"titel": "a", "inhalt": list(inhalt)}]})

        p = "folien[0].inhalt[0]"
        self.assertEqual(fehler({"typ": "zeit", "minuten": 0}),
                         [f"{p}.minuten: muss eine ganze Zahl von 1 bis 180 sein, ist 0"])
        self.assertEqual(fehler({"typ": "auswahl", "optionen": ["nur eine"]}),
                         [f"{p}.optionen: muss 2 bis 4 Einträge haben, hat 1"])
        self.assertEqual(fehler({"typ": "spalten", "spalten": [{"titel": "a", "text": "b"}, {"titel": "c"}]}),
                         [f"{p}.spalten[1].text: fehlt"])
        self.assertEqual(fehler({"typ": "legende", "eintraege": [{"text": "a", "farbe": "lila"},
                                                                 {"text": "b", "farbe": "blau"}]}),
                         [f'{p}.eintraege[0].farbe: muss einer von "blau", "orange", "gruen", "rot", "grau" sein, '
                          'ist "lila"'])
        self.assertEqual(fehler({"typ": "feedback", "gut": ["a"]}), [f"{p}.schlecht: fehlt"])
        self.assertEqual(fehler({"typ": "kasten", "absaetze": ["a"], "farbe": "rot"}),
                         [f"{p}.farbe: unbekanntes Feld, erlaubt sind: typ, absaetze, titel"])

    def test_textteile(self):
        def lese(text):
            d = lesen({"art": "folien", "titel": "x", "folien": [{"titel": "a", "inhalt": [{"typ": "text",
                                                                                           "text": text}]}]})
            return d["folien"][0]["inhalt"][0]["text"]

        self.assertEqual(lese([{"text": "Ich", "farbe": "blau", "unterstrichen": True}, {"text": " "},
                               {"text": "du", "fett": True}]),
                         [{"text": "Ich", "fett": False, "farbe": "blau", "unterstrichen": True},
                          {"text": " ", "fett": False, "farbe": None, "unterstrichen": False},
                          {"text": "du", "fett": True, "farbe": None, "unterstrichen": False}])

        def fehler(text):
            return self.fehler({"art": "folien", "titel": "x", "folien": [{"titel": "a", "inhalt": [
                {"typ": "text", "text": text}]}]})

        p = "folien[0].inhalt[0].text"
        self.assertEqual(fehler([{"text": " "}]),
                         [f'{p}: darf nicht leer sein (einzelne Teile wie " " sind als Trenner erlaubt)'])
        self.assertEqual(fehler(["a"]), [f'{p}[0]: muss ein Objekt {{"text": ...}} sein, ist "a"'])
        self.assertEqual(fehler(5), [f"{p}: muss ein Text oder eine Liste von Textteilen sein, ist 5"])
        self.assertEqual(fehler([{"text": "a" * 1000}, {"text": "b" * 600}]),
                         [f"{p}: zu lang (zusammen höchstens 1500 Zeichen)"])
        self.assertEqual(fehler([{"text": "a", "fett": "ja"}]), [f'{p}[0].fett: muss true oder false sein, ist "ja"'])

    def test_lange_werte_gekuerzt(self):
        f = self.fehler({"art": "x" * 100})
        self.assertIn('ist "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...', f[0])


if __name__ == "__main__":
    unittest.main()
