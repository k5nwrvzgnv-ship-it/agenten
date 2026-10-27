"""Feedback-Dienst mit nachgebauter Umgebung: Instanz in einem Temp-Ordner, Claude als Attrappe, kein Git."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentkit import auftraege, claude_lauf, meldungen, verbrauch
import lauf

LIA_STATUS = "# Status: Agent recherche\n\n## Gelernte Regeln\n- (noch keine)\n"


def zuordnung(**felder):
    z = {"art": "regel", "ziel": "alle", "auftrag": "", "regel": "Ergebnisse beginnen mit einer Empfehlung.",
         "notiz": "", "heikel": False, "heikel_grund": "", "widerspricht": "", "zusammenfassung": "Lia will den Kern zuerst."}
    z.update(felder)
    return claude_lauf.Ergebnis(text=json.dumps(z), sitzung="s", ok=True)


class TestLauf(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.jan = tmp / "shared"
        self.instanz = tmp / "lia" / "instanz"
        for ordner in (self.jan, self.instanz, tmp / "lia" / "recherche"):
            ordner.mkdir(parents=True)
        env = self.instanz / ".env"
        env.write_text("PERSON=Lia\n")
        os.chmod(env, 0o600)
        (self.instanz / "regeln.md").write_text("# Regeln\n\n## Regeln\n- (noch keine)\n", encoding="utf-8")
        (tmp / "lia" / "recherche" / "STATUS.md").write_text(LIA_STATUS, encoding="utf-8")
        self.units = tmp / "units"
        self.units.mkdir()
        self.commits, self.starts = [], []
        for name, wert in (("JAN", self.jan), ("INDEX", lauf.fb.Index(tmp / "index.json")), ("REPO", tmp),
                           ("UNIT_DIR", self.units), ("commit", lambda p, n: self.commits.append((Path(p).name, n))),
                           ("starten", self.starts.append)):
            p = mock.patch.object(lauf, name, wert)
            p.start()
            self.addCleanup(p.stop)
        self.ort = lauf.Ort(self.instanz)
        self.basis = self.ort.auftraege
        aid = auftraege.neuer_auftrag("recherche", "Reihe Strafe", quelle="portal-frage", basis=self.basis)
        self.ergebnis = auftraege.abschliessen(aid, "31 von 49 Aussagen belegt", sitzung="s0", basis=self.basis)

    def feedback(self, text, antwort):
        fid = auftraege.neuer_auftrag("feedback", text, quelle="feedback", bezug=self.ergebnis["id"], basis=self.basis)
        lauf.feedback_bearbeiten(self.ort, auftraege.neue("feedback", basis=self.basis)[0], laufen=lambda *a, **k: antwort)
        return auftraege.erledigter(fid, basis=self.basis)

    def jan_meldung(self, f=None):
        """Meldung zum Fall f (IDs derselben Sekunde sind nicht sortiert), ohne f die einzige."""
        alle = meldungen.neue(basis=self.jan / "meldungen")
        return next(m for m in alle if m["id"] == f["daten"]["meldung"]) if f else alle[0]

    def klick(self, meldung, text):
        with mock.patch.object(auftraege, "BASIS", self.jan / "auftraege"):
            kid = auftraege.neuer_auftrag("feedback", text, quelle="knopf", meldung=meldung["id"], dienst="feedback")
            lauf.knopf_bearbeiten(auftraege.neue("feedback")[0])
            return auftraege.erledigter(kid)

    def test_regel_uebernommen_und_gestoppt(self):
        f = self.feedback("Bitte immer erst die Empfehlung", zuordnung())
        self.assertEqual(f["ergebnis"], "Danke, übernommen. Ab jetzt gilt: Ergebnisse beginnen mit einer Empfehlung.")
        self.assertEqual((f["daten"]["stand"], f["daten"]["bezug"]), ("uebernommen", self.ergebnis["id"]))
        regeln_md = (self.instanz / "regeln.md").read_text(encoding="utf-8")
        self.assertIn(f"Ergebnisse beginnen mit einer Empfehlung. (Feedback {f['id']})", regeln_md)
        self.assertEqual(self.commits[0][0], "regeln.md")
        m = self.jan_meldung(f)
        self.assertEqual((m["agent"], m["knoepfe"], m["dienst"]), ("feedback", [["Stopp"]], "feedback"))
        self.assertIn("Passiert: „Ergebnisse beginnen mit einer Empfehlung.“", m["text"])

        k = self.klick(m, "Stopp")
        self.assertEqual(k["ergebnis"], "Gestoppt. Regel entfernt (1 Zeile). Lia weiß Bescheid.")
        self.assertNotIn("Empfehlung", (self.instanz / "regeln.md").read_text(encoding="utf-8"))
        self.assertEqual(auftraege.erledigter(f["id"], basis=self.basis)["daten"]["stand"], "gestoppt")
        an_lia = meldungen.neue(basis=self.instanz / "meldungen")[-1]["text"]
        self.assertIn("Jan hat dein Feedback „Bitte immer erst die Empfehlung“ zurückgenommen", an_lia)
        self.assertEqual(len(self.commits), 2)
        self.assertIn("Schon entschieden", self.klick(m, "Stopp")["ergebnis"])

    def test_nachbesserung_und_stopp_zieht_zurueck(self):
        (self.units / "lia-recherche.service").write_text("")
        with mock.patch.object(verbrauch, "kosten", return_value=0.4):
            f = self.feedback("zu lang", zuordnung(art="nachbesserung", auftrag="Kürze auf eine Seite."))
        nb = auftraege.neue("recherche", basis=self.basis)[0]
        self.assertEqual((nb["id"], nb["bezug"], nb["sitzung"], nb["quelle"]),
                         (f["daten"]["nachbesserung"], self.ergebnis["id"], "s0", "portal-frage"))
        self.assertIn("Kürze auf eine Seite.", nb["text"])
        self.assertEqual(self.starts, ["lia-recherche"])
        self.assertIn("Nachbesserung läuft", f["ergebnis"])
        self.assertEqual(self.klick(self.jan_meldung(f), "Stopp")["ergebnis"],
                         "Gestoppt. Nachbesserung zurückgezogen. Lia weiß Bescheid.")
        self.assertEqual(auftraege.erledigter(nb["id"], basis=self.basis)["status"], "zurueckgezogen")

    def test_zweite_nachbesserung_wird_vorschlag_und_jan_uebernimmt(self):
        (self.units / "lia-recherche.service").write_text("")
        with mock.patch.object(verbrauch, "kosten", return_value=0.4):
            self.feedback("zu lang", zuordnung(art="nachbesserung", auftrag="Kürzer."))
            auftraege.abschliessen(auftraege.neue("recherche", basis=self.basis)[0]["id"], "kürzer", basis=self.basis)
            f = self.feedback("noch kürzer", zuordnung(art="nachbesserung", auftrag="Noch kürzer."))
        self.assertEqual(f["daten"]["stand"], "vorschlag")
        self.assertIn("Jan zur Entscheidung", f["ergebnis"])
        self.assertEqual(auftraege.neue("recherche", basis=self.basis), [])
        m = self.jan_meldung(f)
        self.assertEqual(m["knoepfe"], [["Übernehmen", "Verwerfen"]])
        self.assertIn("schon eine Nachbesserung", m["text"])
        self.assertEqual(self.klick(m, "Übernehmen")["ergebnis"], "Übernommen. Lia weiß Bescheid.")
        self.assertIn("Noch kürzer.", auftraege.neue("recherche", basis=self.basis)[0]["text"])
        self.assertIn("übernommen", meldungen.neue(basis=self.instanz / "meldungen")[-1]["text"])

    def test_heikel_verwerfen(self):
        f = self.feedback("Schick das gleich an die Schulleitung", zuordnung(heikel=True, heikel_grund="Handeln nach außen"))
        self.assertEqual(f["daten"]["stand"], "vorschlag")
        self.assertIn("(noch keine)", (self.instanz / "regeln.md").read_text(encoding="utf-8"))
        self.assertEqual(self.klick(self.jan_meldung(f), "Verwerfen")["ergebnis"], "Verworfen. Lia weiß Bescheid.")
        self.assertIn("nicht zu übernehmen", meldungen.neue(basis=self.instanz / "meldungen")[-1]["text"])

    def test_notiz_fuer_agent_und_lob(self):
        f = self.feedback("Kann recherche auch Videos prüfen?", zuordnung(art="notiz", ziel="recherche", notiz="Videos prüfen"))
        status = (self.instanz.parent / "recherche" / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("## Wünsche aus Feedback\n- ", status)
        self.assertIn(f"Lia zu recherche: Videos prüfen (Feedback {f['id']})", status)
        f = self.feedback("super!", zuordnung(art="keine"))
        self.assertEqual(f["ergebnis"], "Danke, ist angekommen.")
        self.assertEqual(self.jan_meldung(f)["knoepfe"], [])

    def test_unzuordenbar_geht_an_jan(self):
        f = self.feedback("hm", claude_lauf.Ergebnis(text="weiß nicht", sitzung=None, ok=True))
        self.assertEqual(f["status"], "erledigt")
        self.assertIn("Jan schaut es sich an", f["ergebnis"])
        self.assertIn("Konnte ich nicht zuordnen", self.jan_meldung()["text"])

    def test_ergebnis_fehlt(self):
        auftraege.neuer_auftrag("feedback", "x", quelle="feedback", bezug="20260101-000000-uni-abcdef", basis=self.basis)
        lauf.feedback_bearbeiten(self.ort, auftraege.neue("feedback", basis=self.basis)[0], laufen=None)
        self.assertEqual(auftraege.erledigte("feedback", basis=self.basis)[0]["status"], "fehlgeschlagen")


if __name__ == "__main__":
    unittest.main()
