import json
import unittest

import luecken


def chat(uuid, prompts):
    nachrichten, vorher = [], "00000000-0000-4000-8000-000000000000"
    for i, p in enumerate(prompts):
        for absender, text in (("lia", p), ("claude", f"Antwort {i}")):
            u = f"{uuid}-{i}-{absender}"
            nachrichten.append({"uuid": u, "vorgaenger": vorher, "absender": absender, "text": text,
                                "anhaenge": [], "dateien": []})
            vorher = u
    return {"uuid": uuid + "0000", "titel": "Straftheorien", "datum": "2026-11-07", "nachrichten": nachrichten}


CHATS = [chat("abcd", ["Mach mir einen Verlaufsplan", "nein, kürzer bitte", "Was sagt Kant zur Strafe?"])]


def aufgabe(von, bis, beleg, **extra):
    a = {"chat": "abcd0000", "von": von, "bis": bis, "aufgabe": "x", "art": "planung", "webapp": "nein",
         "weg": "keiner", "fehlt": ["Hin und Her"], "gespraech": True, "beleg": beleg, "warum": "vermutlich"}
    a.update(extra)
    return a


def gut():
    return {"aufgaben": [aufgabe(1, 2, "nein, kürzer"), aufgabe(3, 3, "Was sagt  KANT", art="fachfrage", webapp="ja",
                                                                     fehlt=[], gespraech=False)],
            "luecken": [{"luecke": "Planen im Gespräch", "beschreibung": "b", "aufgaben": ["abcd0000:1"],
                         "vorschlag": "v"}]}


class Pruefen(unittest.TestCase):
    def test_gut(self):
        self.assertEqual(luecken.pruefen(gut(), CHATS), [])

    def test_erfundenes_zitat(self):
        d = gut()
        d["aufgaben"][0]["beleg"] = "bitte kürzer"
        self.assertTrue(any("wörtlich" in f for f in luecken.pruefen(d, CHATS)))

    def test_zitat_aus_falscher_runde(self):
        d = gut()
        d["aufgaben"][1]["beleg"] = "nein, kürzer"
        self.assertTrue(any("wörtlich" in f for f in luecken.pruefen(d, CHATS)))

    def test_runde_fehlt_und_doppelt(self):
        d = gut()
        d["aufgaben"][1].update(von=2, bis=2, beleg="kürzer")
        fehler = luecken.pruefen(d, CHATS)
        self.assertTrue(any("doppelt" in f for f in fehler))
        self.assertTrue(any("ohne Aufgabe: [3]" in f for f in fehler))

    def test_falsche_werte_und_verweis(self):
        d = gut()
        d["aufgaben"][0]["webapp"] = "vielleicht"
        d["luecken"][0]["aufgaben"] = ["abcd0000:2"]
        fehler = luecken.pruefen(d, CHATS)
        self.assertTrue(any("webapp" in f for f in fehler))
        self.assertTrue(any("Lücke 1" in f for f in fehler))

    def test_unbekannter_chat(self):
        d = gut()
        d["aufgaben"].append(aufgabe(1, 1, "x", chat="zzzz0000"))
        self.assertTrue(any("unbekannter Chat" in f for f in luecken.pruefen(d, CHATS)))


class LesenUndBericht(unittest.TestCase):
    def test_lesen_mit_codeblock(self):
        self.assertEqual(luecken.lesen("```json\n" + json.dumps(gut()) + "\n```")["luecken"][0]["vorschlag"], "v")

    def test_lesen_ohne_listen(self):
        with self.assertRaises(ValueError):
            luecken.lesen('{"aufgaben": []}')

    def test_bericht(self):
        text = luecken.bericht(gut(), CHATS)
        self.assertIn("### Planen im Gespräch (2 Runden, 1 Aufgaben)", text)
        self.assertIn("ja 1, teilweise 0, nein 2", text)
        self.assertIn("Straftheorien R1–2: „nein, kürzer“", text)

    def test_prompt_enthaelt_daten_und_webapp(self):
        p = luecken.prompt(CHATS)
        self.assertIn("R2 LIA: nein, kürzer bitte", p)
        self.assertIn("Spalte „Fragen“", p)


if __name__ == "__main__":
    unittest.main()
