import unittest

import verlauf

WURZEL = "00000000"


def n(uuid, vor, absender, text, zeit):
    return {"uuid": uuid, "vorgaenger": vor, "absender": absender, "text": text, "zeit": zeit,
            "anhaenge": [], "dateien": []}


# Lia fragt, Claude antwortet, Lia schreibt die zweite Frage einmal neu (m3 verworfen, m5 gilt)
NACHRICHTEN = [
    n("m1", WURZEL, "lia", "Frage 1", "1"), n("m2", "m1", "claude", "Antwort 1", "2"),
    n("m3", "m2", "lia", "Frage 2 alt", "3"), n("m4", "m3", "claude", "Antwort alt", "4"),
    n("m5", "m2", "lia", "Frage 2 neu", "5"), n("m6", "m5", "claude", "Antwort neu", "6"),
]
CHAT = {"uuid": "abcdefgh-1", "titel": "Kant", "datum": "2026-09-01", "nachrichten": NACHRICHTEN}


class Hauptpfad(unittest.TestCase):
    def test_juengster_ast_und_bearbeitung(self):
        pfad, verworfen = verlauf.hauptpfad(NACHRICHTEN)
        self.assertEqual([x["uuid"] for x in pfad], ["m1", "m2", "m5", "m6"])
        self.assertEqual(verworfen, {"m5": 1})

    def test_leer(self):
        self.assertEqual(verlauf.hauptpfad([]), ([], {}))


class Runden(unittest.TestCase):
    def test_runden(self):
        r = verlauf.runden(CHAT)
        self.assertEqual([(x["nr"], x["prompt"], x["antwort"], x["bearbeitet"]) for x in r],
                         [(1, "Frage 1", "Antwort 1", 0), (2, "Frage 2 neu", "Antwort neu", 1)])

    def test_kompakt_kuerzt_antworten(self):
        chat = dict(CHAT, nachrichten=[n("a", WURZEL, "lia", "Hallo", "1"), n("b", "a", "claude", "x" * 50, "2")])
        chat["nachrichten"][0]["anhaenge"] = [{"name": "ab.pdf", "text": "123"}]
        t = verlauf.kompakt(chat, antwort_zeichen=10)
        self.assertIn("R1 LIA: Hallo [Anhang ab.pdf (3 Zeichen)]", t)
        self.assertIn("R1 CLAUDE: xxxxxxxxxx […40 Zeichen gekürzt]", t)
        self.assertTrue(t.startswith("### Chat abcdefgh: Kant (2026-09-01)"))

    def test_kompakt_ausschnitt(self):
        t = verlauf.kompakt(CHAT, von=2, bis=2)
        self.assertNotIn("R1 ", t)
        self.assertIn("R2 LIA: Frage 2 neu [Prompt 1x neu geschrieben]", t)

    def test_tokens(self):
        self.assertEqual(verlauf.tokens_geschaetzt("x" * 35), 10)
