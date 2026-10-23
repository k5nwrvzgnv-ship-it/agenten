import unittest

import pruefsatz


def n(uuid, vor, absender, text):
    return {"uuid": uuid, "vorgaenger": vor, "absender": absender, "text": text, "zeit": uuid,
            "anhaenge": [], "dateien": []}


AUFTRAG = "Schreib mir einen AB-Text zu Singer für eine lernschwache 8. Klasse, kurz und einfach."
CHAT = {"uuid": "aaaaaaaa-1", "titel": "T", "datum": "d", "nachrichten": [
    n("1", "0", "lia", AUFTRAG), n("2", "1", "claude", "Text v1"),
    n("3", "2", "lia", "einfacher bitte"), n("4", "3", "claude", "Text v2"),
    n("5", "4", "lia", "ok"), n("6", "5", "claude", "gern")]}


def aufgabe(**extra):
    a = {"chat": "aaaaaaaa", "von": 1, "bis": 3, "kategorie": "material", "titel": "AB-Text zu Singer",
         "ausgabe": "AB-Text", "fach": "ethik", "klasse": 8, "ergebnis": "erreicht", "runde_ergebnis": 2,
         "korrekturen": [{"runde": 2, "art": "niveau", "zitat": "einfacher bitte"}]}
    a.update(extra)
    return a


class Eintrag(unittest.TestCase):
    def test_auftrag_kriterien_altes_ergebnis(self):
        e = pruefsatz.eintrag(CHAT, aufgabe())
        self.assertEqual(e["auftrag"], AUFTRAG)
        self.assertEqual(e["kriterien"], ["niveau: einfacher bitte"])
        self.assertEqual(e["altes_ergebnis"], "Text v2")
        self.assertEqual((e["typ"], e["runden"]), ("ab_text_position", "1-3"))
        self.assertEqual(e["kontext"], [])

    def test_mitten_im_chat_braucht_langen_auftrag_und_bringt_kontext(self):
        lang = "x" * 150
        chat = dict(CHAT, nachrichten=CHAT["nachrichten"] + [n("7", "6", "lia", lang), n("8", "7", "claude", "neu")])
        e = pruefsatz.eintrag(chat, aufgabe(von=4, bis=4, runde_ergebnis=4))
        self.assertEqual(e["auftrag"], lang)
        self.assertEqual(e["kontext"], [AUFTRAG, "einfacher bitte", "ok"])
        chat["nachrichten"][6]["text"] = "x" * 149
        self.assertIsNone(pruefsatz.eintrag(chat, aufgabe(von=4, bis=4, runde_ergebnis=4)))

    def test_ohne_ergebnis_oder_zu_kurz(self):
        self.assertIsNone(pruefsatz.eintrag(CHAT, aufgabe(ergebnis="teilweise")))
        self.assertIsNone(pruefsatz.eintrag(CHAT, aufgabe(runde_ergebnis=None)))
        self.assertIsNone(pruefsatz.eintrag(CHAT, aufgabe(von=2, bis=3)))  # "einfacher bitte" ist kein Auftrag


class Auswaehlen(unittest.TestCase):
    def test_je_typ_und_ids(self):
        a = [aufgabe(), aufgabe(korrekturen=[]), aufgabe(kategorie="verwaltung")]
        p = pruefsatz.auswaehlen({"aaaaaaaa": CHAT}, a, {"ab_text_position": 1, "verwaltung": 2})
        self.assertEqual([(e["id"], e["typ"], len(e["kriterien"])) for e in p],
                         [("P01", "ab_text_position", 1), ("P02", "verwaltung", 1)])
