import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agent
from agentkit import auftraege


class PlatzhalterTest(unittest.TestCase):
    def test_antwort_je_art(self):
        self.assertIn("Material", agent.antwort({"quelle": "portal-material"}))
        self.assertIn("Frage", agent.antwort({"quelle": "portal-frage"}))
        self.assertEqual(agent.antwort({"quelle": "irgendwas"}), agent.STANDARD)

    def test_schliesst_alle_auftraege_ab(self):
        with tempfile.TemporaryDirectory() as d:
            basis, agenten = Path(d) / "auftraege", Path(d)
            with mock.patch.object(auftraege, "BASIS", basis), mock.patch.object(auftraege, "AGENTEN_DIR", agenten):
                auftraege.neuer_auftrag("unterricht", "Arbeitsblatt Kant", quelle="portal-material")
                auftraege.neuer_auftrag("unterricht", "Was ist Ethik?", quelle="portal-frage")
                agent.auftraege_abarbeiten()
                self.assertEqual(auftraege.neue("unterricht"), [])
                erledigt = auftraege.erledigte("unterricht")
                self.assertEqual({a["status"] for a in erledigt}, {"erledigt"})
                self.assertTrue(all(a["ergebnis"] for a in erledigt))


if __name__ == "__main__":
    unittest.main()
