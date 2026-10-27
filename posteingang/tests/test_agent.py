import json
import tempfile
import unittest
from pathlib import Path

from agentkit import claude_lauf
from agentkit.claude_lauf import Ergebnis

import agent


def mail(uid, **kopf):
    return {"uid": uid, "von": f"x{uid}@example.de", "datum": "", "betreff": f"B{uid}", "text": "t",
            "anhaenge": [], "kopf": kopf}


class TestPostPruefen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.offen = Path(self.tmp.name) / "mails_offen.json"
        self.gemeldet, self.prompts = [], []

    def tearDown(self):
        self.tmp.cleanup()

    def pruefen(self, neue, antwort="KEINE", ok=True, fehler=None, gesperrt=()):
        def laufen(name, hier, prompt, **kw):
            self.prompts.append((prompt, kw))
            if fehler:
                raise fehler
            return Ergebnis(antwort, None, ok)
        agent.post_pruefen(holen=lambda: neue, laufen=laufen, melden=self.gemeldet.append,
                           gesperrt=lambda: list(gesperrt), offen_datei=self.offen)

    def test_keine_mails_nichts_tun(self):
        self.pruefen([])
        self.assertEqual(self.prompts, [])
        self.assertFalse(self.offen.exists())

    def test_wichtige_mail_gemeldet(self):
        self.pruefen([mail(1), mail(2, **{"list-unsubscribe": "<x>"})], antwort="- Persönlich | x1: B1. Antworten")
        self.assertEqual(len(self.prompts), 1)
        prompt, kw = self.prompts[0]
        self.assertIn("uid 1", prompt)
        self.assertNotIn("uid 2", prompt)
        self.assertEqual(kw, {"art": "routine", "zeitgesteuert": True})
        self.assertEqual(self.gemeldet, ["[post] Wichtige Mails (1 geprüft, 1 vorgefiltert):\n- Persönlich | x1: B1. Antworten"])
        self.assertFalse(self.offen.exists())

    def test_keine_nichts_melden(self):
        self.pruefen([mail(1)])
        self.assertEqual(self.gemeldet, [])
        self.assertFalse(self.offen.exists())

    def test_alle_vorgefiltert_ohne_claude(self):
        self.pruefen([mail(1, precedence="bulk"), mail(2)], gesperrt=["x2@example.de"])
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.gemeldet, [])
        self.assertFalse(self.offen.exists())

    def test_warten_mails_bleiben_offen(self):
        self.pruefen([mail(1)], fehler=claude_lauf.LimitErreicht(None))
        self.assertEqual([m["uid"] for m in json.loads(self.offen.read_text())], [1])
        # nächster Lauf nimmt die offenen und die neuen
        self.prompts.clear()
        self.pruefen([mail(2)], antwort="- Termin | x2: B2")
        self.assertIn("uid 1", self.prompts[0][0])
        self.assertIn("uid 2", self.prompts[0][0])
        self.assertIn("2 geprüft", self.gemeldet[0])
        self.assertFalse(self.offen.exists())

    def test_fehlgeschlagener_lauf_wirft_und_behaelt(self):
        with self.assertRaises(claude_lauf.LaufFehler):
            self.pruefen([mail(1)], antwort="kaputt", ok=False)
        self.assertTrue(self.offen.exists())
        self.assertEqual(self.gemeldet, [])


class TestSchrittFehler(unittest.TestCase):
    def test_einmal_am_tag(self):
        with tempfile.TemporaryDirectory() as d:
            datei, gemeldet = Path(d) / "f.json", []
            f = RuntimeError("weg")
            self.assertTrue(agent.schritt_fehler_melden("post_pruefen", f, "2026-10-27", datei, gemeldet.append))
            self.assertFalse(agent.schritt_fehler_melden("post_pruefen", f, "2026-10-27", datei, gemeldet.append))
            self.assertTrue(agent.schritt_fehler_melden("post_pruefen", f, "2026-10-28", datei, gemeldet.append))
            self.assertEqual(len(gemeldet), 2)
            self.assertIn("RuntimeError: weg", gemeldet[0])


if __name__ == "__main__":
    unittest.main()
