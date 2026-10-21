import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agent


class TestAuftraege(unittest.TestCase):
    def test_nur_auftraege_ohne_dienst(self):
        with mock.patch.object(agent.auftraege, "neue", return_value=[]) as neue:
            agent.auftraege_abarbeiten()
        neue.assert_called_once_with(agent.AGENT, dienst=None)


class TestUrsprung(unittest.TestCase):
    def test_kette(self):
        ablage = {"a1": {"id": "a1", "bezug": None, "modus": "lernen"},
                  "a2": {"id": "a2", "bezug": "a1", "modus": "erledigen"}}
        neu = {"id": "a3", "bezug": "a2", "modus": "erledigen", "sitzung": "s"}
        self.assertEqual(agent.ursprung(neu, ablage.__getitem__)["id"], "a1")

    def test_ohne_bezug(self):
        a = {"id": "a1", "bezug": None}
        self.assertIs(agent.ursprung(a, lambda i: 1 / 0), a)

    def test_fehlendes_glied(self):
        def holen(i):
            raise KeyError(i)
        neu = {"id": "a3", "bezug": "weg", "sitzung": "s"}
        self.assertEqual(agent.ursprung(neu, holen)["id"], "a3")

    def test_schleife(self):
        ablage = {"a1": {"id": "a1", "bezug": "a2"}, "a2": {"id": "a2", "bezug": "a1"}}
        self.assertIn(agent.ursprung({"id": "a3", "bezug": "a1"}, ablage.__getitem__)["id"], ("a1", "a2"))


class TestSchrittFehler(unittest.TestCase):
    def test_einmal_am_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "f.json"
            with mock.patch.object(agent, "melden") as melden:
                self.assertTrue(agent.schritt_fehler_melden("post_pruefen", OSError("IMAP weg"), "2026-10-21", datei))
                self.assertFalse(agent.schritt_fehler_melden("post_pruefen", OSError("IMAP weg"), "2026-10-21", datei))
                self.assertTrue(agent.schritt_fehler_melden("kurse_spiegeln", ValueError("x"), "2026-10-21", datei))
                self.assertTrue(agent.schritt_fehler_melden("post_pruefen", OSError("IMAP weg"), "2026-10-22", datei))
            self.assertEqual(melden.call_count, 3)
            self.assertIn("post_pruefen fehlgeschlagen: OSError: IMAP weg", melden.call_args_list[0].args[0])
