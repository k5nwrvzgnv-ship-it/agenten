import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from agentkit import freigabe, regeln

ALLGEMEIN = """# Allgemeine Regeln

Text davor.

## Regeln
- (noch keine)
"""

STATUS = """# Status: Agent uni

## Gelernte Regeln
- (noch keine)

## Danach
- bleibt unberührt
"""


class TestRegeln(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.allgemein = self.tmp / "regeln.md"
        self.allgemein.write_text(ALLGEMEIN, encoding="utf-8")
        self.agent = self.tmp / "uni"
        self.agent.mkdir()
        (self.agent / "STATUS.md").write_text(STATUS, encoding="utf-8")
        self.basis = self.tmp / "freigabe"
        p = mock.patch.object(regeln, "ALLGEMEIN_DATEI", self.allgemein)
        p.start()
        self.addCleanup(p.stop)

    def freigeben(self, regel, allgemein):
        eid = regeln.regel_vorschlagen("uni", regel, "Jan hat korrigiert", allgemein, basis=self.basis)
        abdruck = freigabe.offene(basis=self.basis)[-1]["fingerabdruck"]
        return freigabe.entscheide(eid, "freigegeben", gesehen=abdruck, basis=self.basis)

    def test_leer(self):
        self.assertEqual(regeln.allgemeine_regeln(), [])
        self.assertEqual(regeln.agent_regeln(self.agent), [])
        self.assertIn("- (keine)", regeln.regeln_als_text(self.agent))

    def test_vorschlag_landet_in_freigabe_nicht_in_datei(self):
        regeln.regel_vorschlagen("uni", "Immer duzen", "Anlass", basis=self.basis)
        self.assertEqual(freigabe.offene("uni", basis=self.basis)[0]["typ"], "regel")
        self.assertEqual(regeln.agent_regeln(self.agent), [])

    def test_nicht_freigegeben_wird_nicht_eingetragen(self):
        eid = regeln.regel_vorschlagen("uni", "Immer duzen", "Anlass", basis=self.basis)
        entwurf = freigabe.entscheide(eid, "abgelehnt", basis=self.basis)
        with self.assertRaises(regeln.RegelFehler):
            regeln.regel_eintragen(entwurf, self.agent)

    def test_agent_regel_eintragen(self):
        self.assertTrue(regeln.regel_eintragen(self.freigeben("Quellen immer mit Seite", False), self.agent))
        self.assertTrue(regeln.regel_eintragen(self.freigeben("Kurz antworten", False), self.agent))
        r = regeln.agent_regeln(self.agent)
        self.assertEqual(len(r), 2)
        self.assertIn("Quellen immer mit Seite (Anlass: Jan hat korrigiert)", r[0])
        text = (self.agent / "STATUS.md").read_text(encoding="utf-8")
        self.assertNotIn("(noch keine)", text)
        self.assertIn("## Danach\n- bleibt unberührt", text)
        self.assertEqual(regeln.allgemeine_regeln(), [])

    def test_allgemeine_regel_und_kein_doppelter_eintrag(self):
        entwurf = self.freigeben("Keine Emojis", True)
        self.assertTrue(regeln.regel_eintragen(entwurf))
        self.assertFalse(regeln.regel_eintragen(entwurf))
        self.assertEqual(len(regeln.allgemeine_regeln()), 1)
        self.assertTrue(self.allgemein.read_text(encoding="utf-8").startswith("# Allgemeine Regeln\n\nText davor."))
        self.assertIn("Keine Emojis", regeln.regeln_als_text(self.agent))

    def test_regel_muss_eine_zeile_sein(self):
        with self.assertRaises(regeln.RegelFehler):
            regeln.regel_vorschlagen("uni", "zwei\nzeilen", "x", basis=self.basis)


if __name__ == "__main__":
    unittest.main()


class TestAusFeedback(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.status = self.tmp / "STATUS.md"
        self.status.write_text(STATUS, encoding="utf-8")
        self.fid = "20261027-120000-feedback-abc123"

    def test_eintragen_mit_herkunft(self):
        zeile = regeln.zeile_eintragen(self.status, "## Gelernte Regeln", "Kurz halten", self.fid,
                                       heute=date(2026, 10, 27))
        self.assertEqual(zeile, f"- 27.10.2026: Kurz halten (Feedback {self.fid})")
        text = self.status.read_text(encoding="utf-8")
        self.assertIn(zeile + "\n\n## Danach", text)
        self.assertNotIn("(noch keine)", text)

    def test_fehlender_abschnitt_wird_angelegt(self):
        regeln.zeile_eintragen(self.status, "## Offene Punkte", "Knopf fehlt", self.fid)
        self.assertTrue(self.status.read_text(encoding="utf-8").rstrip().endswith(f"Knopf fehlt (Feedback {self.fid})"))
        self.assertIn("## Offene Punkte", self.status.read_text(encoding="utf-8"))

    def test_mehrzeilig_abgelehnt(self):
        with self.assertRaises(regeln.RegelFehler):
            regeln.zeile_eintragen(self.status, "## Gelernte Regeln", "a\nb", self.fid)

    def test_entfernen_nur_eigene_zeilen(self):
        regeln.zeile_eintragen(self.status, "## Gelernte Regeln", "Eins", self.fid)
        regeln.zeile_eintragen(self.status, "## Gelernte Regeln", "Zwei", "20261027-120001-feedback-def456")
        self.assertEqual(regeln.zeilen_entfernen(self.status, self.fid), 1)
        text = self.status.read_text(encoding="utf-8")
        self.assertNotIn("Eins", text)
        self.assertIn("Zwei", text)
        self.assertIn("- bleibt unberührt", text)
        self.assertEqual(regeln.zeilen_entfernen(self.status, self.fid), 0)
        self.assertEqual(regeln.agent_regeln(self.tmp)[0].split(": ", 1)[1], "Zwei (Feedback 20261027-120001-feedback-def456)")
