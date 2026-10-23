import json
import unittest

import einordnen


def chat(uuid, runden, laenge=10):
    nachrichten, vor = [], "0"
    for i in range(1, runden + 1):
        nachrichten += [{"uuid": f"{uuid}l{i}", "vorgaenger": vor, "absender": "lia", "text": "x" * laenge,
                         "zeit": f"{i:04d}a", "anhaenge": [], "dateien": []},
                        {"uuid": f"{uuid}c{i}", "vorgaenger": f"{uuid}l{i}", "absender": "claude", "text": "y",
                         "zeit": f"{i:04d}b", "anhaenge": [], "dateien": []}]
        vor = f"{uuid}c{i}"
    return {"uuid": uuid + "-rest", "titel": "T", "datum": "2026-09-01", "nachrichten": nachrichten}


def aufgabe(chat, von, bis, **extra):
    a = {"chat": chat, "von": von, "bis": bis, "kategorie": "material", "titel": "t", "fach": "ethik", "klasse": 8,
         "eingaben": ["freitext"], "ausgabe": "AB", "ergebnis": "erreicht", "runde_ergebnis": bis,
         "korrekturen": [], "belastung": False, "automatisierbar": "mittel", "begruendung": "b"}
    a.update(extra)
    return a


class Pakete(unittest.TestCase):
    def test_langer_chat_wird_geteilt(self):
        teile = einordnen.ausschnitte(chat("aaaaaaaa", 30, laenge=350), budget=1000)
        self.assertGreater(len(teile), 1)
        self.assertEqual(teile[0]["von"], 1)
        self.assertEqual(teile[-1]["bis"], 30)
        for a, b in zip(teile, teile[1:], strict=False):
            self.assertEqual(a["bis"] + 1, b["von"])
        self.assertTrue(all(t["tokens"] <= 1000 for t in teile))

    def test_kurze_chats_teilen_paket(self):
        p = einordnen.pakete([chat("aaaaaaaa", 2), chat("bbbbbbbb", 2), chat("cccccccc", 0)], budget=1000)
        self.assertEqual(len(p), 1)
        self.assertEqual([t["chat"] for t in p[0]], ["aaaaaaaa", "bbbbbbbb"])

    def test_prompt_nennt_ausschnitt(self):
        teile = einordnen.ausschnitte(chat("aaaaaaaa", 30, laenge=350), budget=1000)
        p = einordnen.prompt([teile[1]], "SCHEMA-TEXT")
        self.assertIn("SCHEMA-TEXT", p)
        self.assertIn(f"Ausschnitt Runden {teile[1]['von']} bis {teile[1]['bis']} von 30", p)


class Lesen(unittest.TestCase):
    def test_mit_codeblock(self):
        self.assertEqual(einordnen.lesen('Hier:\n```json\n[{"a": 1}]\n```'), [{"a": 1}])

    def test_kaputt(self):
        with self.assertRaises(ValueError):
            einordnen.lesen("keine Ahnung")
        with self.assertRaises(json.JSONDecodeError):
            einordnen.lesen("[{kaputt]")


class Pruefen(unittest.TestCase):
    PAKET = [{"chat": "aaaaaaaa", "von": 1, "bis": 5, "runden": 5}]

    def test_in_ordnung(self):
        a = [aufgabe("aaaaaaaa", 1, 2), aufgabe("aaaaaaaa", 3, 5,
                                                korrekturen=[{"runde": 4, "art": "niveau", "zitat": "zu schwer"}])]
        self.assertEqual(einordnen.pruefen(a, self.PAKET), [])

    def test_luecke_und_werte(self):
        a = [aufgabe("aaaaaaaa", 1, 2, kategorie="quatsch"), aufgabe("aaaaaaaa", 4, 5, eingaben=["fax"],
                                                                   korrekturen=[{"runde": 4, "art": "laut"}])]
        f = einordnen.pruefen(a, self.PAKET)
        self.assertTrue(any("kategorie='quatsch'" in x for x in f))
        self.assertTrue(any("eingaben" in x for x in f))
        self.assertTrue(any("Korrektur ungültig" in x for x in f))
        self.assertTrue(any("nicht lückenlos ab R3" in x for x in f))

    def test_ende_fehlt_und_feld_fehlt(self):
        a = [aufgabe("aaaaaaaa", 1, 3)]
        del a[0]["begruendung"]
        f = einordnen.pruefen(a, self.PAKET)
        self.assertTrue(any("Felder fehlen: begruendung" in x for x in f))
        self.assertTrue(any("R1-R5 keiner Aufgabe" in x or "R4-R5" in x for x in f))


class Zusammenfuehren(unittest.TestCase):
    def test_ueber_grenze(self):
        a = [aufgabe("aaaaaaaa", 1, 10, korrekturen=[{"runde": 3, "art": "form"}]),
             aufgabe("aaaaaaaa", 11, 15, korrekturen=[{"runde": 12, "art": "stil"}], ergebnis="teilweise"),
             aufgabe("aaaaaaaa", 16, 20, kategorie="planung")]
        z = einordnen.zusammenfuehren(a, {"aaaaaaaa": {10}})
        self.assertEqual([(x["von"], x["bis"]) for x in z], [(1, 15), (16, 20)])
        self.assertEqual(len(z[0]["korrekturen"]), 2)
        self.assertEqual(z[0]["ergebnis"], "teilweise")

    def test_ohne_grenze_nicht(self):
        a = [aufgabe("aaaaaaaa", 1, 10), aufgabe("aaaaaaaa", 11, 15)]
        self.assertEqual(len(einordnen.zusammenfuehren(a, {})), 2)
