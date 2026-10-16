import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentkit import config, log


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.shared = self.tmp / "shared"
        self.agent = self.tmp / "agent"
        self.shared.mkdir()
        self.agent.mkdir()
        patcher = mock.patch.object(config, "SHARED_DIR", self.shared)
        patcher.start()
        self.addCleanup(patcher.stop)

    def schreibe(self, pfad, text, modus=0o600):
        pfad.write_text(text, encoding="utf-8")
        os.chmod(pfad, modus)

    def test_agent_ueberschreibt_shared(self):
        self.schreibe(self.shared / ".env", "# Kommentar\nA=1\nB='zwei'\n")
        self.schreibe(self.agent / ".env", "export B=\"drei\"\nC=x=y\n")
        cfg = config.lade_config(self.agent)
        self.assertEqual(cfg, {"A": "1", "B": "drei", "C": "x=y"})

    def test_fehlende_dateien_sind_ok(self):
        self.assertEqual(config.lade_config(self.agent), {})

    def test_falsche_rechte_brechen_ab(self):
        self.schreibe(self.shared / ".env", "A=1\n", modus=0o644)
        with self.assertRaises(config.ConfigFehler):
            config.lade_config(self.agent)

    def test_pflichtwerte(self):
        self.schreibe(self.shared / ".env", "A=\n")
        with self.assertRaises(config.ConfigFehler):
            config.lade_config(self.agent, pflicht=("A",))

    def test_kaputte_zeile(self):
        self.schreibe(self.shared / ".env", "ohne gleichheitszeichen\n")
        with self.assertRaises(config.ConfigFehler):
            config.lade_config(self.agent)


class TestLog(unittest.TestCase):
    def test_schreibt_datei_und_keine_doppelten_handler(self):
        agent = Path(tempfile.mkdtemp())
        logger = log.hole_logger(agent, "testagent")
        self.assertIs(log.hole_logger(agent, "testagent"), logger)
        self.assertEqual(len(logger.handlers), 2)
        with mock.patch("sys.stderr"):
            logger.info("hallo")
        for h in logger.handlers:
            h.flush()
        self.assertIn("hallo", (agent / "logs" / "testagent.log").read_text())


if __name__ == "__main__":
    unittest.main()
