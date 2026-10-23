import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agent
import material
from agentkit import auftraege, claude_lauf, config, meldungen

JAN_MELDEN = agent.jan_melden  # vor dem Ersetzen in setUp


class AgentTest(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.basis, self.agenten = d / "auftraege", d
        self.hier = d / "unterricht"
        self.gemeldet = []
        for p in (mock.patch.object(auftraege, "BASIS", self.basis),
                  mock.patch.object(auftraege, "AGENTEN_DIR", self.agenten),
                  mock.patch.object(agent, "HIER", self.hier),
                  mock.patch.object(agent, "jan_melden", self.gemeldet.append)):
            p.start()
            self.addCleanup(p.stop)

    def erledigt(self) -> dict:
        return {a["quelle"]: a for a in auftraege.erledigte("unterricht")}

    def test_platzhalter_fuer_woche_und_frage(self):
        self.assertIn("Frage", agent.antwort({"quelle": "portal-frage"}))
        self.assertEqual(agent.antwort({"quelle": "irgendwas"}), agent.STANDARD)
        auftraege.neuer_auftrag("unterricht", "Was ist Ethik?", quelle="portal-frage")
        auftraege.neuer_auftrag("unterricht", "Woche", quelle="portal-woche")
        agent.auftraege_abarbeiten()
        self.assertEqual(auftraege.neue("unterricht"), [])
        self.assertEqual({a["status"] for a in self.erledigt().values()}, {"erledigt"})

    def test_material_mit_datei(self):
        datei = self.hier / "data" / "arbeit" / "x" / "Arbeitsblatt Kant.docx"
        datei.parent.mkdir(parents=True)
        datei.write_bytes(b"docx")
        fertig = material.Fertig(datei, "Hier ist dein Blatt.", "s1", 2, 1.2, 5000, [])
        auftraege.neuer_auftrag("unterricht", "Arbeitsblatt Kant", quelle="portal-material")
        bearbeiten = mock.Mock(return_value=fertig)
        with mock.patch.object(agent.material_auftrag, "__defaults__", (bearbeiten,)):
            agent.auftraege_abarbeiten()
        bearbeiten.assert_called_once()
        a = self.erledigt()["portal-material"]
        self.assertEqual((a["status"], a["ergebnis"], a["sitzung"]), ("erledigt", "Hier ist dein Blatt.", "s1"))
        self.assertEqual(a["ergebnis_dateien"], ["data/arbeit/x/Arbeitsblatt Kant.docx"])
        self.assertEqual(self.gemeldet, [])

    def material_scheitert(self, fehler):
        auftraege.neuer_auftrag("unterricht", "Folien Kant", quelle="portal-material")
        with mock.patch.object(agent.material_auftrag, "__defaults__", (mock.Mock(side_effect=fehler),)):
            agent.auftraege_abarbeiten()
        return self.erledigt()["portal-material"]

    def test_material_fehler_meldet_jan(self):
        a = self.material_scheitert(material.MaterialFehler("Beschreibung ungültig"))
        self.assertEqual((a["status"], a["ergebnis"]), ("fehlgeschlagen", agent.NICHT_GEKLAPPT))
        self.assertEqual(len(self.gemeldet), 1)
        self.assertIn("Beschreibung ungültig", self.gemeldet[0])

    def test_limit(self):
        a = self.material_scheitert(claude_lauf.LimitErreicht(None))
        self.assertEqual(a["status"], "fehlgeschlagen")
        self.assertIn("Kontingent", a["ergebnis"])
        self.assertEqual(len(self.gemeldet), 1)

    def test_unerwarteter_fehler(self):
        a = self.material_scheitert(RuntimeError("Renderer kaputt"))
        self.assertEqual(a["status"], "fehlgeschlagen")
        self.assertIn("Renderer kaputt", self.gemeldet[0])

    def test_jan_melden_in_jans_instanz(self):
        basis = Path(tempfile.mkdtemp())
        JAN_MELDEN("Test", basis=basis)
        self.assertEqual([(m["agent"], m["text"]) for m in meldungen.neue(basis=basis)],
                         [("unterricht", "Lia, Agent unterricht: Test")])
        with mock.patch.object(meldungen, "melden") as melden:
            JAN_MELDEN("Test")
        self.assertEqual(melden.call_args.kwargs["basis"], config.KONTINGENT_DIR / "meldungen")

    def test_reihen_laden(self):
        self.assertEqual(agent.reihen_laden(), [])  # keine Datei
        self.hier.mkdir(parents=True)
        (self.hier / "reihen.toml").write_text("[[reihe]]\nklasse = 8\nreihenfrage = 'Helfen?'\n", encoding="utf-8")
        self.assertEqual(agent.reihen_laden(), [{"klasse": 8, "reihenfrage": "Helfen?"}])
        self.assertEqual(self.gemeldet, [])
        (self.hier / "reihen.toml").write_text("[[reihe]]\nklasse = 8\n", encoding="utf-8")
        self.assertEqual(agent.reihen_laden(), [])
        self.assertEqual(len(self.gemeldet), 1)
        self.assertIn("reihenfrage fehlt", self.gemeldet[0])

    def test_material_bekommt_reihen(self):
        self.hier.mkdir(parents=True)
        (self.hier / "reihen.toml").write_text("[[reihe]]\nklasse = 8\nreihenfrage = 'Helfen?'\n", encoding="utf-8")
        bearbeiten = mock.Mock(side_effect=material.MaterialFehler("egal"))
        auftraege.neuer_auftrag("unterricht", "Blatt", quelle="portal-material")
        with mock.patch.object(agent.material_auftrag, "__defaults__", (bearbeiten,)):
            agent.auftraege_abarbeiten()
        self.assertEqual(bearbeiten.call_args.kwargs["reihen"], [{"klasse": 8, "reihenfrage": "Helfen?"}])

    def test_profil(self):
        profil = agent.profil_laden()
        self.assertEqual((profil["fach"], profil["lehrkraft"]), ("Ethik", "Frau Pohlmann"))


if __name__ == "__main__":
    unittest.main()
