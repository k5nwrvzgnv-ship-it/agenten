"""Prüft das Gerüst von finance, solange es noch keine .venv gibt (läuft mit System-python3, ohne agentkit)."""

import ast
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent


class TestGeruest(unittest.TestCase):
    def test_agent_name(self):
        baum = ast.parse((HIER / "agent.py").read_text(encoding="utf-8"))
        namen = {z.targets[0].id: z.value.value for z in baum.body
                 if isinstance(z, ast.Assign) and isinstance(z.targets[0], ast.Name)
                 and isinstance(z.value, ast.Constant)}
        self.assertEqual(namen.get("AGENT"), "finance")

    def test_dienstvorlage(self):
        unit = (HIER / "systemd" / "finance.service").read_text(encoding="utf-8")
        self.assertIn("WorkingDirectory=/home/agent/agenten/finance\n", unit)
        self.assertIn("OnFailure=ausfall@%n.service", unit)
        self.assertNotIn("<name>", unit)


if __name__ == "__main__":
    unittest.main()
