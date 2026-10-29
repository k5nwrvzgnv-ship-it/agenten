"""Rechensprache: zerlegen, ablehnen, nach Excel übersetzen und in Python nachrechnen."""

import unittest

from renderer import rechnung
from renderer.rechnung import FEHLER, LEER, FormelFehler, ausrechnen, deutsch, excel, zerlegen

# Spalten wie in Lias Notentabelle: A nr, B name, C-G n1-n5, H schnitt, I lek, J endnote
SPALTEN = [("nr", "nummer"), ("name", "text"), ("n1", "zahl"), ("n2", "zahl"), ("n3", "zahl"), ("n4", "zahl"),
           ("n5", "zahl"), ("schnitt", "rechnung"), ("lek", "zahl"), ("endnote", "rechnung")]
REIHE = [i for i, _ in SPALTEN]
ZELLE = {sid: f"{chr(65 + i)}5" for i, sid in enumerate(REIHE)}.__getitem__
SCHNITT = "mittelwert(n1:n5)"
ENDNOTE = "wenn_leer(2/3 * schnitt + 1/3 * lek, schnitt)"


def formeln(**texte) -> dict:
    return {sid: zerlegen(t) for sid, t in texte.items()}


class TestZerlegen(unittest.TestCase):
    def test_rangfolge_und_klammern(self):
        self.assertEqual(excel(zerlegen("1 + 2 * 3"), ZELLE), "=1+2*3")
        self.assertEqual(excel(zerlegen("(1 + 2) * 3"), ZELLE), "=(1+2)*3")
        self.assertEqual(excel(zerlegen("8 - (2 - 1)"), ZELLE), "=8-(2-1)")
        self.assertEqual(excel(zerlegen("8 / (4 / 2)"), ZELLE), "=8/(4/2)")
        self.assertEqual(excel(zerlegen("8 - 2 - 1"), ZELLE), "=8-2-1")
        self.assertEqual(excel(zerlegen("-(1 + 2)"), ZELLE), "=-(1+2)")
        self.assertEqual(excel(zerlegen("007.50 * 1"), ZELLE), "=7.50*1")

    def test_ablehnen(self):
        faelle = {
            "=mittelwert(n1:n5)": "Zeichen 1: kein = schreiben",
            "AVERAGE(n1:n5)": "Zeichen 1: Großbuchstaben",
            "indirekt(n1)": "unbekannte Funktion 'indirekt'",
            "hyperlink(n1)": "unbekannte Funktion 'hyperlink'",
            "mittelwrt(n1:n5)": "(gemeint: 'mittelwert'?)",
            "n1 & n2": "Zeichen 4: Zeichen '&' ist nicht erlaubt",
            'n1 + "a"': "Zeichen 6: Zeichen '\"' ist nicht erlaubt",
            "Noten!n1": "Großbuchstaben",
            "n1 ! n2": "Zeichen '!' ist nicht erlaubt",
            "$c$5": "Zeichen '$' ist nicht erlaubt",
            "runden(n1; 2)": "Argumente mit Komma trennen",
            "2,5 * n1": "Kommazahlen mit Punkt schreiben",
            "n1 / 0": "Zeichen 6: Teilen durch 0",
            "n1 / 0.0": "Teilen durch 0",
            "n1 +": "endet zu früh",
            "(n1 + n2": "')' fehlt am Ende",
            "n1 n2": "Zeichen 4: unerwartet: 'n2'",
            "n1:n5": "Bereich n1:n5 nur in summe",
            "n1:n5 + 1": "Bereich n1:n5 nur in summe",
            "summe(n1 + n2)": "summe: nur Spalten oder Bereiche",
            "runden(n1)": "runden braucht genau 2 Argumente",
            "runden(n1, 5)": "Stellen als ganze Zahl von 0 bis 4",
            "runden(n1, 1.5)": "Stellen als ganze Zahl",
            "runden(n1, lek)": "Stellen als ganze Zahl",
            "wenn_leer(n1)": "wenn_leer braucht genau 2 Argumente",
            "1234567890": "Zahl zu lang",
            "": "leer",
            "n1 + " * 61: "zu lang",
            "ä": "Zeichen 'ä' ist nicht erlaubt",
        }
        for text, erwartet in faelle.items():
            with self.subTest(text=text), self.assertRaises(FormelFehler) as f:
                zerlegen(text)
            self.assertIn(erwartet, str(f.exception), text)

    def test_tiefe(self):
        zerlegen("(" * 10 + "1" + ")" * 10)
        with self.assertRaisesRegex(FormelFehler, "zu tief verschachtelt"):
            zerlegen("(" * 11 + "1" + ")" * 11)

    def test_pruefen_gegen_spalten(self):
        def meldungen(text):
            return [str(f) for f in rechnung.pruefen_gegen(zerlegen(text), SPALTEN)]

        self.assertEqual(meldungen(ENDNOTE), [])
        self.assertIn("unbekannte Spalte 'lek2' (gemeint: 'lek'?)", meldungen("lek2 * 2")[0])
        self.assertIn("Spalte 'name' hat die Art 'text'", meldungen("name + 1")[0])
        self.assertIn("Spalte 'nr' hat die Art 'nummer'", meldungen("summe(nr)")[0])
        self.assertIn("muss von links nach rechts gehen", meldungen("summe(n5:n1)")[0])
        self.assertIn("muss von links nach rechts gehen", meldungen("summe(n1:n1)")[0])
        self.assertEqual(meldungen("summe(n1:lek)"), [])  # schnitt dazwischen ist eine Rechnung, erlaubt
        self.assertIn("unbekannte Spalte", meldungen("summe(n1:xx)")[0])

    def test_bereich_ueber_textspalte(self):
        spalten = [("a", "zahl"), ("t", "text"), ("b", "zahl")]
        meldung = [str(f) for f in rechnung.pruefen_gegen(zerlegen("summe(a:b)"), spalten)]
        self.assertEqual(len(meldung), 1)
        self.assertIn("Bereich a:b enthält 't' mit Art 'text'", meldung[0])

    def test_zyklus_und_reihenfolge(self):
        self.assertIsNone(rechnung.zyklus(formeln(schnitt=SCHNITT, endnote=ENDNOTE), REIHE))
        self.assertEqual(rechnung.zyklus(formeln(schnitt="endnote + 1", endnote="schnitt * 2"), REIHE),
                         ["schnitt", "endnote", "schnitt"])
        self.assertEqual(rechnung.zyklus(formeln(schnitt="schnitt + 1"), REIHE), ["schnitt", "schnitt"])
        # Ein Bereich, der die eigene Spalte umfasst, ist ein Selbstbezug
        self.assertEqual(rechnung.zyklus(formeln(schnitt="summe(n1:endnote)", endnote="n1"), REIHE),
                         ["schnitt", "schnitt"])
        self.assertEqual(rechnung.zyklus(formeln(schnitt="summe(n1:endnote)", endnote="schnitt"), REIHE),
                         ["schnitt", "endnote", "schnitt"])
        # endnote steht vorn in den Formeln, braucht aber schnitt
        self.assertEqual(rechnung.reihenfolge(formeln(endnote=ENDNOTE, schnitt=SCHNITT), REIHE),
                         ["schnitt", "endnote"])


class TestExcel(unittest.TestCase):
    def test_lias_notentabelle(self):
        self.assertEqual(excel(zerlegen(SCHNITT), ZELLE), '=IF(COUNT(C5:G5)=0,"",AVERAGE(C5:G5))')
        self.assertEqual(excel(zerlegen(ENDNOTE), ZELLE),
                         '=IF(AND(OR(COUNT(H5)=0,COUNT(I5)=0),COUNT(H5)=0),"",'
                         'IF(OR(COUNT(H5)=0,COUNT(I5)=0),H5,2/3*H5+1/3*I5))')

    def test_ohne_leer_bedingung(self):
        self.assertEqual(excel(zerlegen("anzahl(n1:n5)"), ZELLE), "=COUNT(C5:G5)")
        self.assertEqual(excel(zerlegen("2 * 3"), ZELLE), "=2*3")
        self.assertEqual(excel(zerlegen("wenn_leer(n1, 0)"), ZELLE), '=IF(COUNT(C5)=0,0,C5)')

    def test_doppelte_bedingung_nur_einmal(self):
        self.assertEqual(excel(zerlegen("n1 * n1 + runden(n2, 1)"), ZELLE),
                         '=IF(OR(COUNT(C5)=0,COUNT(D5)=0),"",C5*C5+ROUND(D5,1))')

    def test_mehrere_argumente(self):
        self.assertEqual(excel(zerlegen("max(n1, n3:n5, lek)"), ZELLE),
                         '=IF(COUNT(C5,E5:G5,I5)=0,"",MAX(C5,E5:G5,I5))')

    def test_deutsch(self):
        self.assertEqual(deutsch('=IF(COUNT(C5:G5)=0,"",ROUND(AVERAGE(C5:G5)*0.5,2))'),
                         '=WENN(ANZAHL(C5:G5)=0;"";RUNDEN(MITTELWERT(C5:G5)*0,5;2))')

    def test_laenge_bleibt_im_rahmen(self):
        verschachtelt = "wenn_leer(" * 5 + "n1" + ", n2)" * 5
        self.assertLess(len(excel(zerlegen(verschachtelt), ZELLE)), rechnung.MAX_EXCEL)


class TestAusrechnen(unittest.TestCase):
    def zeile(self, noten, lek):
        eingaben = {f"n{i + 1}": n for i, n in enumerate(noten)} | {"lek": lek}
        werte = rechnung.zeile_ausrechnen(formeln(endnote=ENDNOTE, schnitt=SCHNITT), REIHE, eingaben)
        return werte["schnitt"], werte["endnote"]

    def test_lias_notentabelle(self):
        schnitt, endnote = self.zeile([15, 10, LEER, LEER, LEER], 9)
        self.assertEqual(schnitt, 12.5)
        self.assertAlmostEqual(endnote, 11.3333333333, places=8)

    def test_ohne_lek_zaehlen_die_noten(self):
        self.assertEqual(self.zeile([8, LEER, 8, LEER, 8], LEER), (8.0, 8.0))

    def test_ohne_noten_leer(self):
        self.assertEqual(self.zeile([LEER] * 5, 9), (LEER, LEER))
        self.assertEqual(self.zeile([LEER] * 5, LEER), (LEER, LEER))

    def test_grenzen(self):
        self.assertEqual(self.zeile([0] * 5, 0), (0.0, 0.0))
        schnitt, endnote = self.zeile([15] * 5, 15)
        self.assertEqual(schnitt, 15.0)
        self.assertAlmostEqual(endnote, 15.0)

    def test_funktionen(self):
        werte = {"n1": 1.0, "n2": LEER, "n3": 4.0, "n4": 2.5, "n5": LEER}

        def r(text):
            return ausrechnen(zerlegen(text), werte, REIHE)

        self.assertEqual(r("summe(n1:n5)"), 7.5)
        self.assertEqual(r("min(n1:n5)"), 1.0)
        self.assertEqual(r("max(n1, n4)"), 2.5)
        self.assertEqual(r("anzahl(n1:n5)"), 3.0)
        self.assertEqual(r("anzahl(n2, n5)"), 0.0)
        self.assertIs(r("summe(n2, n5)"), LEER)
        self.assertIs(r("n1 + n2"), LEER)
        self.assertEqual(r("-n1 * 2"), -2.0)
        self.assertEqual(r("runden(n4 / 2, 0)"), 1.0)  # 1,25 -> 1
        self.assertEqual(r("runden(2.5, 0)"), 3.0)  # wie Excel nach oben, nicht 2
        self.assertEqual(r("runden(0.125, 2)"), 0.13)
        self.assertEqual(r("wenn_leer(n2, n1)"), 1.0)
        self.assertEqual(r("wenn_leer(n1, n3)"), 1.0)

    def test_teilen_durch_null(self):
        werte = {"n1": 3.0, "n2": 0.0, "n3": LEER}

        def r(text):
            return ausrechnen(zerlegen(text), werte, REIHE)

        self.assertEqual(r("n1 / n2"), FEHLER)
        self.assertEqual(r("n1 / n2 + 1"), FEHLER)
        self.assertIs(r("n3 / n2"), LEER)  # leer geht vor, wie die Bedingung in Excel
        # Eine Spalte mit Fehler zählt wie in Excel (COUNT) als leer
        self.assertIs(ausrechnen(zerlegen("schnitt + 1"), {"schnitt": FEHLER}, REIHE), LEER)
        self.assertEqual(ausrechnen(zerlegen("summe(n1, schnitt)"), {"n1": 1.0, "schnitt": FEHLER}, REIHE), FEHLER)


if __name__ == "__main__":
    unittest.main()
