"""Prüfung der Beschreibung: gültige Beschreibungen mit Standardwerten, klare Fehler mit Pfad."""

import copy
import json
import unittest

from renderer import BeschreibungUngueltig, pruefen
from renderer.pruefung import lesen

BLATT = {
    "art": "arbeitsblatt",
    "titel": "Der kategorische Imperativ",
    "kopfzeile": ["Name", "Klasse", "Datum"],
    "bloecke": [
        {"typ": "ueberschrift", "text": "Einstieg"},
        {"typ": "absatz", "text": "Kant formuliert ...\nzweite Zeile"},
        {"typ": "liste", "punkte": ["Maxime", "Gesetz"]},
        {"typ": "tabelle", "kopf": ["Begriff", "Erklärung"], "zeilen": [["Maxime", ""]]},
        {"typ": "aufgabe", "text": "Erkläre ...", "antwort": {"art": "linien", "anzahl": 5}},
        {"typ": "aufgabe", "text": "Skizziere ...", "antwort": {"art": "kasten", "hoehe_cm": 6.5}},
        {"typ": "aufgabe", "text": "Lies den Text."},
    ],
}

FOLIEN = {
    "art": "folien",
    "titel": "Der kategorische Imperativ",
    "folien": [{"titel": "Was ist eine Maxime?", "punkte": ["Regel", "subjektiv"]}, {"titel": "Fragen?"}],
}


def blatt_mit(**aenderungen):
    """Kopie von BLATT, Blöcke per Index ersetzbar: blatt_mit(b2={...})."""
    d = copy.deepcopy(BLATT)
    for name, wert in aenderungen.items():
        if name.startswith("b"):
            d["bloecke"][int(name[1:])] = wert
        else:
            d[name] = wert
    return d


class TestGueltig(unittest.TestCase):
    def test_arbeitsblatt_mit_standardwerten(self):
        e = lesen(BLATT)
        self.assertEqual(e["kopfzeile"], ["Name", "Klasse", "Datum"])
        b = e["bloecke"]
        self.assertEqual(b[0], {"typ": "ueberschrift", "text": "Einstieg", "ebene": 1})
        self.assertEqual(b[2]["nummeriert"], False)
        self.assertEqual(b[4]["antwort"], {"art": "linien", "anzahl": 5})
        self.assertEqual(b[5]["antwort"], {"art": "kasten", "hoehe_cm": 6.5})
        self.assertIsNone(b[6]["antwort"])

    def test_ohne_kopfzeile_und_tabelle_ohne_kopf(self):
        d = blatt_mit(b3={"typ": "tabelle", "zeilen": [["a", "b"], ["c", "d"]]})
        del d["kopfzeile"]
        e = lesen(d)
        self.assertEqual(e["kopfzeile"], [])
        self.assertIsNone(e["bloecke"][3]["kopf"])

    def test_folien_mit_standardwerten(self):
        e = lesen(FOLIEN)
        self.assertEqual(e["untertitel"], "")
        self.assertEqual(e["folien"][1], {"titel": "Fragen?", "punkte": []})

    def test_json_text_und_dict_gleich(self):
        self.assertEqual(lesen(json.dumps(BLATT)), lesen(BLATT))
        self.assertEqual(pruefen(json.dumps(FOLIEN)), [])

    def test_eingabe_bleibt_unveraendert(self):
        d = copy.deepcopy(FOLIEN)
        lesen(d)
        self.assertEqual(d, FOLIEN)


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
        self.assertEqual(self.fehler({"titel": "x"}), ['art: fehlt, erlaubt sind "arbeitsblatt" oder "folien"'])
        self.assertEqual(self.fehler({"art": "brief"}),
                         ['art: muss "arbeitsblatt" oder "folien" sein, ist "brief"'])

    def test_unbekanntes_feld_mit_tippfehler_hinweis(self):
        f = self.fehler(blatt_mit(b2={"typ": "liste", "punkt": ["a"]}))
        self.assertIn('bloecke[2].punkt: unbekanntes Feld (gemeint: "punkte"?), erlaubt sind: typ, punkte, nummeriert',
                      f)
        self.assertIn("bloecke[2].punkte: fehlt", f)

    def test_unbekannter_blocktyp(self):
        self.assertEqual(self.fehler(blatt_mit(b0={"typ": "Ueberschrift", "text": "x"})),
                         ['bloecke[0].typ: muss einer von "ueberschrift", "absatz", "liste", "tabelle", "aufgabe" '
                          'sein, ist "Ueberschrift" (gemeint: "ueberschrift"?)'])

    def test_alle_fehler_auf_einmal(self):
        d = blatt_mit(titel="", b0={"typ": "ueberschrift", "text": "x", "ebene": 4},
                      b4={"typ": "aufgabe", "text": "x", "antwort": {"art": "linien", "anzahl": "fünf"}})
        self.assertEqual(self.fehler(d), [
            "titel: darf nicht leer sein",
            "bloecke[0].ebene: muss eine ganze Zahl von 1 bis 3 sein, ist 4",
            'bloecke[4].antwort.anzahl: muss eine ganze Zahl von 1 bis 30 sein, ist "fünf"',
        ])

    def test_exception_nennt_alle_fehler(self):
        with self.assertRaises(BeschreibungUngueltig) as ctx:
            lesen({"art": "folien", "folien": []})
        self.assertEqual(ctx.exception.fehler, ["titel: fehlt", "folien: muss 1 bis 50 Einträge haben, hat 0"])
        self.assertEqual(str(ctx.exception),
                         "Beschreibung ungültig, bitte korrigieren:\n- titel: fehlt\n"
                         "- folien: muss 1 bis 50 Einträge haben, hat 0")

    def test_falsche_typen(self):
        f = self.fehler(blatt_mit(kopfzeile="Name", b1={"typ": "absatz", "text": 5},
                                  b2={"typ": "liste", "punkte": ["a"], "nummeriert": "ja"}, b3="Tabelle"))
        self.assertIn('kopfzeile: muss eine Liste [...] sein, ist "Name"', f)
        self.assertIn("bloecke[1].text: muss ein Text sein, ist 5", f)
        self.assertIn('bloecke[2].nummeriert: muss true oder false sein, ist "ja"', f)
        self.assertIn('bloecke[3]: muss ein Objekt {...} sein, ist "Tabelle"', f)

    def test_wahrheitswert_ist_keine_zahl(self):
        self.assertEqual(self.fehler(blatt_mit(b4={"typ": "aufgabe", "text": "x",
                                                   "antwort": {"art": "kasten", "hoehe_cm": True}})),
                         ["bloecke[4].antwort.hoehe_cm: muss eine Zahl von 1 bis 25 sein, ist true"])

    def test_nan_ist_keine_zahl(self):
        text = json.dumps(BLATT).replace('"hoehe_cm": 6.5', '"hoehe_cm": NaN')
        self.assertEqual(self.fehler(text), ["bloecke[5].antwort.hoehe_cm: muss eine Zahl von 1 bis 25 sein, ist NaN"])

    def test_antwortart(self):
        self.assertEqual(self.fehler(blatt_mit(b4={"typ": "aufgabe", "text": "x", "antwort": {"art": "punkte"}})),
                         ['bloecke[4].antwort.art: muss "linien" oder "kasten" sein, ist "punkte"'])
        self.assertEqual(self.fehler(blatt_mit(b4={"typ": "aufgabe", "text": "x",
                                                   "antwort": {"art": "kasten", "anzahl": 3}})),
                         ["bloecke[4].antwort.anzahl: unbekanntes Feld, erlaubt sind: art, hoehe_cm",
                          "bloecke[4].antwort.hoehe_cm: fehlt"])

    def test_tabelle_spaltenzahl(self):
        f = self.fehler(blatt_mit(b3={"typ": "tabelle", "kopf": ["a", "b"], "zeilen": [["1", "2"], ["3"]]}))
        self.assertEqual(f, ["bloecke[3].zeilen[1]: hat 1 Zellen, erwartet 2 (wie kopf)"])
        f = self.fehler(blatt_mit(b3={"typ": "tabelle", "zeilen": [["1", "2"], ["3", "4", "5"]]}))
        self.assertEqual(f, ["bloecke[3].zeilen[1]: hat 3 Zellen, erwartet 2 (wie zeilen[0])"])

    def test_laenge_und_steuerzeichen(self):
        f = self.fehler(blatt_mit(titel="x" * 201, b1={"typ": "absatz", "text": "a\x07b"}))
        self.assertIn("titel: zu lang (201 Zeichen, höchstens 200)", f)
        self.assertIn("bloecke[1].text: enthält Steuerzeichen (erlaubt sind nur Zeilenumbruch und Tab)", f)

    def test_folien_fehler(self):
        f = self.fehler({"art": "folien", "titel": "x", "untertitel": 3,
                         "folien": [{"titel": "a", "punkte": ["p"] * 11}, {"punkte": []}, "b"]})
        self.assertEqual(f, [
            "untertitel: muss ein Text sein, ist 3",
            "folien[0].punkte: muss 0 bis 10 Einträge haben, hat 11",
            "folien[1].titel: fehlt",
            'folien[2]: muss ein Objekt {...} sein, ist "b"',
        ])

    def test_lange_werte_gekuerzt(self):
        f = self.fehler({"art": "x" * 100})
        self.assertIn('ist "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...', f[0])


if __name__ == "__main__":
    unittest.main()
