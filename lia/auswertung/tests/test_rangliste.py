import unittest

import rangliste


def a(kat, titel, von, bis, auto="hoch", korr=0, ausgabe=""):
    return {"kategorie": kat, "titel": titel, "ausgabe": ausgabe, "von": von, "bis": bis, "automatisierbar": auto,
            "korrekturen": [{"runde": von, "art": "form"}] * korr}


class Typ(unittest.TestCase):
    def test_stichwoerter_und_vorrang(self):
        self.assertEqual(rangliste.typ(a("material", "Vier Statusspiel-Szenen", 1, 1)), "theater_material")
        self.assertEqual(rangliste.typ(a("material", "Fallbeispiel Jonas K.", 1, 1)), "fallbeispiel")
        self.assertEqual(rangliste.typ(a("material", "Kurzer Text", 1, 1, ausgabe="BBB-Lückentext")),
                         "argumentieren_ueben")
        self.assertEqual(rangliste.typ(a("material", "AB-Text zu Walzer", 1, 1)), "ab_text_position")
        self.assertEqual(rangliste.typ(a("bewertung", "Mitarbeit im Theaterkurs", 1, 1)), "mitarbeit_auswerten")
        self.assertEqual(rangliste.typ(a("planung", "Reihenfrage finden", 1, 1)), "reihe_und_rlp")
        self.assertEqual(rangliste.typ(a("planung", "Tafelbild festlegen", 1, 1)), "stunde_und_ub")

    def test_unbekannte_kategorie(self):
        self.assertEqual(rangliste.typ(a("neu", "x", 1, 1)), "neu")


class Rangliste(unittest.TestCase):
    def test_wert_und_reihenfolge(self):
        r = rangliste.rangliste([a("material", "AB-Text", 1, 10, "mittel", 2), a("material", "AB-Text", 11, 12),
                                 a("planung", "Tafelbild", 1, 20, "gering", 1)])
        self.assertEqual([z["typ"] for z in r], ["ab_text_position", "stunde_und_ub"])
        self.assertEqual(r[0]["wert"], 8.0)  # 10 * 0,6 + 2 * 1
        self.assertEqual((r[0]["aufgaben"], r[0]["runden"], r[0]["korrekturen_je_aufgabe"]), (2, 12, 1.0))
        self.assertEqual(r[0]["automatisierbar_hoch_anteil"], 0.5)
        self.assertEqual(r[1]["wert"], 4.0)
