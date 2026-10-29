import copy
import unittest

import fassung
import karte
import stueck
from renderer import pruefen as renderer_pruefen


def einheiten():
    """30 Einheiten: Akt 1 = 1–10, Akt 2 = 11–20, Akt 3 = 21–30; jede Rede 13 Wörter (0,1 Min)."""
    e = []
    for nr in range(1, 31):
        akt = (nr - 1) // 10 + 1
        typ = "regie" if nr % 10 == 1 else "rede"
        e.append(stueck.Einheit(nr, akt, nr // 3 + 4, nr // 3 + 6, typ, "TIM", " ".join([f"w{nr}"] * 13)))
    return e


MUSS = [{"id": "M0-1", "akt": 0, "text": "Einstieg"}, {"id": "M1-1", "akt": 1, "text": "Lloyd von hinten"},
        {"id": "M2-1", "akt": 2, "text": "Blumen"}, {"id": "M3-1", "akt": 3, "text": "Chor"}]
RAHMEN = {"minuten_min": 35, "minuten_max": 40, "spieler": 18, "einheiten": "20 Einheiten",
          "teile": [{"akt": 0, "name": "Eröffnung", "minuten": 3}, {"akt": 1, "name": "Akt 1", "minuten": 10},
                    {"akt": 2, "name": "Akt 2", "minuten": 10}, {"akt": 3, "name": "Akt 3", "minuten": 10}]}


def anlass(i, akt, von, bis, muss=()):
    return {"id": f"A{akt}-{i:02d}", "akt": akt, "von": von, "bis": bis, "titel": "Titel", "figuren": ["TIM"],
            "worum": "Worum", "komik": "Komik", "muss": list(muss), "lustige_stellen": [von]}


def karte_gut():
    return {"anlaesse": [anlass(1, 1, 1, 3, ["M1-1"]), anlass(2, 1, 4, 10), anlass(3, 2, 11, 14, ["M2-1"]),
                         anlass(4, 2, 15, 20), anlass(5, 3, 21, 23), anlass(6, 3, 24, 26), anlass(7, 3, 27, 28),
                         anlass(8, 3, 29, 30)],
            "nicht_gefunden": [{"muss": "M3-1", "grund": "Lias Idee"}], "hinweise": ["Akt 2 hat wenig Text"]}


OPTION = {"titel": "T", "beschreibung": "B", "vorteile": "V", "nachteile": "N"}


def ablauf_gut():
    return {
        "bausteine": [
            {"id": "B01", "teil": 0, "titel": "Choreo", "minuten": 3, "art": "neu", "spielidee": "Musik",
             "neuer_text": "Wir sind die Truppe.", "muss": ["M0-1"]},
            {"id": "B02", "teil": 1, "titel": "Probe", "minuten": 10, "art": "original", "spielidee": "von hinten",
             "stellen": [{"von": 2, "bis": 6, "striche": [4]}], "muss": ["M1-1"]},
            {"id": "B03", "teil": 2, "titel": "Blumen", "minuten": 10, "art": "gemischt", "spielidee": "Publikum",
             "stellen": [{"von": 12, "bis": 13}, {"von": 15, "bis": 15}], "neuer_text": "Durchsage", "muss": ["M2-1"]},
            {"id": "B04", "teil": 3, "titel": "Chor", "minuten": 12, "art": "neu", "spielidee": "Freeze",
             "neuer_text": "Wir haben Angst.", "muss": ["M3-1"]},
        ],
        "varianten": [{"frage": f, "optionen": [OPTION, OPTION], "empfehlung": 0} for f in fassung.FRAGEN],
        "zuspitzung": [{"titel": "Fallhöhe", "vorschlag": "Mehr"}] * 3,
        "annahmen": ["Frederick spielt mit"], "rueckfragen": ["Wie viele Mikrofone?"],
    }


class Szenenkarte(unittest.TestCase):
    def setUp(self):
        self.e = einheiten()

    def test_gut(self):
        self.assertEqual(karte.pruefen(karte_gut(), self.e, MUSS), [])

    def test_bereich_ausserhalb_des_akts(self):
        k = karte_gut()
        k["anlaesse"][1]["bis"] = 12
        self.assertTrue(any("nicht in Akt 1" in f for f in karte.pruefen(k, self.e, MUSS)))

    def test_ueberschneidung(self):
        k = karte_gut()
        k["anlaesse"][1]["von"] = 3
        self.assertTrue(any("überschneiden" in f for f in karte.pruefen(k, self.e, MUSS)))

    def test_muss_fehlt_und_falsche_id(self):
        k = karte_gut()
        k["nicht_gefunden"] = []
        k["anlaesse"][0]["muss"] = ["M9-9"]
        fehler = karte.pruefen(k, self.e, MUSS)
        self.assertTrue(any("M1-1" in f and "fehlen" in f for f in fehler))
        self.assertTrue(any("anlaesse[0].muss" in f for f in fehler))

    def test_einstieg_muss_nicht_im_original_sein(self):
        self.assertFalse(any("M0-1" in f for f in karte.pruefen(karte_gut(), self.e, MUSS)))

    def test_lustige_stelle_ausserhalb_und_figur(self):
        k = karte_gut()
        k["anlaesse"][0]["lustige_stellen"] = [9]
        k["anlaesse"][0]["figuren"] = ["Tim"]
        fehler = karte.pruefen(k, self.e, MUSS)
        self.assertTrue(any("lustige_stellen" in f for f in fehler))
        self.assertTrue(any("figuren" in f for f in fehler))

    def test_beschreibung_ist_gueltig_und_hat_zitat(self):
        b = karte.beschreibung(karte_gut(), self.e, MUSS, "Stück")
        self.assertEqual(renderer_pruefen(b), [])
        self.assertIn("Pointe S. 5: TIM: " + " ".join(["w4"] * 13), str(b))  # wörtlich aus der Einheit
        self.assertIn("(S. 4–5, 0,2 Min)", str(b))
        self.assertIn("Lias Idee", str(b))


class Ablauf(unittest.TestCase):
    def setUp(self):
        self.e = einheiten()

    def pruefen(self, a):
        return fassung.pruefen(a, self.e, MUSS, RAHMEN)

    def test_gut(self):
        self.assertEqual(self.pruefen(ablauf_gut()), [])

    def test_summe_und_teil(self):
        a = ablauf_gut()
        a["bausteine"][3]["minuten"] = 4
        fehler = self.pruefen(a)
        self.assertTrue(any("Summe der Minuten ist 27" in f for f in fehler))
        self.assertTrue(any(f.startswith("Teil 3: 4 Min") for f in fehler))

    def test_stelle_doppelt(self):
        a = ablauf_gut()
        a["bausteine"][2]["stellen"].append({"von": 5, "bis": 5})
        self.assertTrue(any("[5] steht schon in B02" in f for f in self.pruefen(a)))

    def test_sprechzeit_zu_lang(self):
        a = ablauf_gut()
        a["bausteine"][1]["minuten"] = 0.3  # 4 Reden à 0,1 Min
        fehler = self.pruefen(a)
        self.assertTrue(any("etwa 0.4 Min Sprechzeit" in f for f in fehler))

    def test_striche_ausserhalb(self):
        a = ablauf_gut()
        a["bausteine"][1]["stellen"][0]["striche"] = [9]
        self.assertTrue(any("striche" in f for f in self.pruefen(a)))

    def test_muss_genau_einmal(self):
        a = ablauf_gut()
        a["bausteine"][3]["muss"] = ["M1-1"]
        fehler = self.pruefen(a)
        self.assertIn("M1-1 kommt 2-mal vor, genau einmal nötig", fehler)
        self.assertIn("M3-1 kommt 0-mal vor, genau einmal nötig", fehler)

    def test_art_passt_nicht(self):
        a = ablauf_gut()
        a["bausteine"][0]["stellen"] = [{"von": 1, "bis": 1}]
        del a["bausteine"][2]["neuer_text"]
        fehler = self.pruefen(a)
        self.assertTrue(any("art neu hat keine stellen" in f for f in fehler))
        self.assertTrue(any("bausteine[2].neuer_text" in f for f in fehler))

    def test_varianten_und_zuspitzung(self):
        a = ablauf_gut()
        a["varianten"] = a["varianten"][:2]
        a["varianten"][0]["empfehlung"] = 2
        a["zuspitzung"] = []
        fehler = self.pruefen(a)
        self.assertIn("varianten: Frage partitur fehlt", fehler)
        self.assertTrue(any("empfehlung" in f for f in fehler))
        self.assertTrue(any("zuspitzung" in f for f in fehler))

    def test_spielfassung_woertlich_mit_strichen(self):
        b = fassung.spielfassung(ablauf_gut(), self.e, RAHMEN, "Stück")
        self.assertEqual(renderer_pruefen(b), [])
        texte = [x["text"] for x in b["bloecke"] if x["typ"] == "absatz"]
        probe = next(t for t in texte if "w2" in t)
        self.assertIn("TIM: " + " ".join(["w3"] * 13), probe)
        self.assertNotIn("w4", probe)
        self.assertIn("[Strich: 1 Einheit]", probe)
        self.assertIn({"typ": "material", "titel": "Neuer Text", "text": "Wir haben Angst."}, b["bloecke"])

    def test_strichuebersicht(self):
        bloecke = fassung.strichuebersicht(ablauf_gut(), self.e)
        self.assertIn({"typ": "ueberschrift", "text": "Akt 1 im Original: 4 von 10 Einheiten bleiben", "ebene": 2},
                      bloecke)
        self.assertIn({"typ": "ueberschrift", "text": "Akt 3 im Original: 0 von 10 Einheiten bleiben", "ebene": 2},
                      bloecke)

    def test_ablauf_dokument_gueltig(self):
        b = fassung.ablauf(ablauf_gut(), self.e, MUSS, RAHMEN, "Stück")
        self.assertEqual(renderer_pruefen(b), [])
        self.assertIn("(Empfehlung)", str(b))

    def test_lange_stelle_wird_geteilt(self):
        e = [stueck.Einheit(n, 1, 1, 1, "rede", "TIM", "x" * 1000) for n in range(1, 21)]
        a = {"bausteine": [{"id": "B1", "stellen": [{"von": 1, "bis": 20}]}]}
        bloecke = fassung._originalbloecke(a["bausteine"][0], {x.nr: x for x in e})
        self.assertGreater(len(bloecke), 3)
        self.assertTrue(all(len(x["text"]) <= fassung.BLOCK_ZEICHEN for x in bloecke))

    def test_gueltige_vorgabe_unveraendert(self):
        a = ablauf_gut()
        vorher = copy.deepcopy(a)
        self.pruefen(a)
        fassung.spielfassung(a, self.e, RAHMEN, "Stück")
        self.assertEqual(a, vorher)


if __name__ == "__main__":
    unittest.main()
