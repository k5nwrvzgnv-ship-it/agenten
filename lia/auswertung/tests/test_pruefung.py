import unittest

import pruefung


def aufgabe(chat, von, bis, kat="material", korr=(), ergebnis="erreicht", auto="hoch"):
    return {"chat": chat, "von": von, "bis": bis, "kategorie": kat, "titel": f"{kat}{von}", "ergebnis": ergebnis,
            "automatisierbar": auto, "korrekturen": [{"runde": von, "art": x} for x in korr]}


def n(uuid, vor, absender, text):
    return {"uuid": uuid, "vorgaenger": vor, "absender": absender, "text": text, "zeit": uuid,
            "anhaenge": [], "dateien": []}


CHAT = {"uuid": "aaaaaaaa-1", "titel": "T", "datum": "d", "nachrichten": [
    n("1", "0", "lia", "Mach mir <b>einen</b> Text"), n("2", "1", "claude", "y" * 800)]}


class Stichprobe(unittest.TestCase):
    def test_jede_kategorie_und_anzahl(self):
        aufgaben = [aufgabe("c", i, i, "material") for i in range(1, 30)] + [aufgabe("c", 40, 40, "verwaltung"),
                                                                           aufgabe("c", 50, 80, "bewertung")]
        s = pruefung.stichprobe(aufgaben, anzahl=5)
        self.assertEqual(len(s), 5)
        self.assertIn("verwaltung", {a["kategorie"] for a in s})
        self.assertNotIn("bewertung", {a["kategorie"] for a in s})  # 31 Runden, zu lang
        self.assertEqual(s, pruefung.stichprobe(aufgaben, anzahl=5))  # fester Seed


class Formular(unittest.TestCase):
    def test_ausschnitt_kuerzt_und_bogen_escaped(self):
        e = pruefung.kodier_eintraege({"aaaaaaaa": CHAT}, [aufgabe("aaaaaaaa", 1, 1)])
        text = e[0]["abschnitte"][0][1]
        self.assertIn("Runde 1 – du: Mach mir <b>einen</b> Text", text)
        self.assertTrue(text.endswith(" […]"))
        h = pruefung.formular_html("Bogen", "Bitte ausfüllen", e, "lia.csv")
        self.assertIn("&lt;b&gt;einen&lt;/b&gt;", h)
        self.assertIn("name='K01|kategorie' value='material'", h)
        self.assertIn("type='checkbox' name='K01|korrekturarten'", h)
        self.assertIn('"lia.csv"', h)
        self.assertNotIn("material1", h)  # Claudes Titel steht nicht im Bogen

    def test_csv_lesen(self):
        a = pruefung.lies_antworten("id;feld;wert\nK01;kategorie;material\nK01;korrekturarten;form\n"
                                    "K01;korrekturarten;stil\n")
        self.assertEqual(a, {"K01": {"kategorie": ["material"], "korrekturarten": ["form", "stil"]}})


class Uebereinstimmung(unittest.TestCase):
    def test_kappa(self):
        self.assertEqual(pruefung.kappa([("a", "a"), ("b", "b")]), 1.0)
        self.assertEqual(pruefung.kappa([("a", "b"), ("b", "a")]), -1.0)
        self.assertIsNone(pruefung.kappa([("a", "a")]))
        self.assertIsNone(pruefung.kappa([]))

    def test_felder(self):
        auswahl = [aufgabe("c", 1, 2, "material", ["form", "stil"]), aufgabe("c", 3, 4, "planung", ["niveau"] * 7)]
        antworten = {"K01": {"kategorie": ["material"], "korrekturen": ["3"], "korrekturarten": ["form"]},
                     "K02": {"kategorie": ["auswahl"], "korrekturen": ["6+"], "korrekturarten": ["niveau"]}}
        u = pruefung.uebereinstimmung(auswahl, antworten)
        self.assertEqual(u["kategorie"]["gleich"], 0.5)
        self.assertEqual(u["korrekturen"]["gleich"], 0.5)  # 2 vs 3 ungleich, 6+ gleich
        self.assertEqual(u["korrekturen"]["hoechstens_1_daneben"], 1.0)
        self.assertEqual(u["korrekturarten_jaccard"], 0.75)  # 1/2 und 1/1
        self.assertEqual(u["ergebnis"]["n"], 0)
        self.assertEqual(u["unterschiede_kategorie"], ["K02: Claude planung, Lia auswahl"])


class Blindvergleich(unittest.TestCase):
    SATZ = [{"id": "P01", "titel": "AB", "auftrag": "Auftrag", "kontext": ["vorher"], "kriterien": ["niveau: einfacher"],
             "altes_ergebnis": "ALT"},
            {"id": "P02", "titel": "X", "auftrag": "A2", "kontext": [], "kriterien": [], "altes_ergebnis": "ALT2"}]

    def test_paare_und_auswertung(self):
        eintraege, schluessel = pruefung.paare(self.SATZ, {"P01": "NEU"})
        self.assertEqual(len(eintraege), 1)  # P02 hat kein neues Ergebnis
        texte = dict(eintraege[0]["abschnitte"])
        self.assertEqual({texte["Fassung A"], texte["Fassung B"]}, {"ALT", "NEU"})
        self.assertEqual(schluessel["P01"], "alt" if texte["Fassung A"] == "ALT" else "neu")
        self.assertIn("Vorher im Chat: vorher", texte["Dein Auftrag"])
        neu_seite = "A" if schluessel["P01"] == "neu" else "B"
        alt_seite = "B" if neu_seite == "A" else "A"
        antworten = {"P01": {"besser": [neu_seite], f"nutzbar_{neu_seite}": ["ja"], f"nutzbar_{alt_seite}": ["nein"],
                             f"kriterien_{neu_seite}": ["k1"]}}
        schluessel["P09"] = "alt"  # nicht bewertet, darf nicht mitzählen
        self.SATZ = self.SATZ + [{"id": "P09", "kriterien": ["a", "b"]}]
        v = pruefung.vergleich_auswerten(antworten, schluessel, self.SATZ)
        self.assertEqual(v["besser"], {"neu": 1})
        self.assertEqual(v["nutzbar"], {"neu": {"ja": 1}, "alt": {"nein": 1}})
        self.assertEqual(v["kriterien_erfuellt"], {"neu": 1.0, "alt": 0.0})


class Normalisieren(unittest.TestCase):
    def test_markdown_und_reste(self):
        alt = "``` This block is not supported on your current device yet. ``` **Titel**\n## Teil\n* Punkt\n*kursiv* 2*3"
        self.assertEqual(pruefung.normalisieren(alt), "Titel\nTeil\n- Punkt\nkursiv 2*3")
