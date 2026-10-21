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


class InstanzTest(unittest.TestCase):
    def test_ohne_variable_bleibt_shared(self):
        erwartet = Path(config.__file__).resolve().parent.parent
        self.assertEqual(config.instanz_dir({}), erwartet)
        self.assertEqual(config.instanz_dir({"AGENTKIT_INSTANZ": "  "}), erwartet)

    def test_mit_variable(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(config.instanz_dir({"AGENTKIT_INSTANZ": d}), Path(d).resolve())

    def test_relativ_oder_fehlend_bricht_ab(self):
        for wert in ("lia/instanz", "/gibt/es/nicht"):
            with self.assertRaises(config.ConfigFehler):
                config.instanz_dir({"AGENTKIT_INSTANZ": wert})


class PersonTest(unittest.TestCase):
    def test_person_aus_env_sonst_jan(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(config.person(Path(d)), "Jan")
            env = Path(d) / ".env"
            env.write_text("PERSON=Lia\n")
            env.chmod(0o600)
            self.assertEqual(config.person(Path(d)), "Lia")

    def test_jans_instanz_teilt_kontingent_mit_sich(self):
        self.assertEqual(config.KONTINGENT_DIR, config.instanz_dir({}))

if __name__ == "__main__":
    unittest.main()
