import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agent
from agentkit.claude_lauf import Ergebnis

ID = "20261022-120000-uni-abc123"
BESCHREIBUNG = {"art": "zusammenfassung", "titel": "IHS", "kurs": "Integrierter Holzschutz", "datum": "20.10.2026",
                "bloecke": [{"typ": "absatz", "text": "Holz kann abgebaut werden."}]}
BEHAUPTUNGEN = [{"nr": 1, "aussage": "Holz kann abgebaut werden.", "quellen": [{"art": "folie", "stelle": "4"}]}]


def uebergabe_schreiben(hier: Path, gueltig: bool = True) -> None:
    ordner = hier / "data" / "weitergabe" / ID
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "behauptungen.json").write_text(json.dumps(BEHAUPTUNGEN))
    (ordner / "zusammenfassung.json").write_text(json.dumps(BESCHREIBUNG if gueltig else {**BESCHREIBUNG, "datum": "x"}))
    (hier / "data" / "weitergabe" / f"{ID}.json").write_text(json.dumps(
        {"text": "Bitte als PDF bauen.", "dateien": [f"data/weitergabe/{ID}/behauptungen.json",
                                                     f"data/weitergabe/{ID}/zusammenfassung.json"]}))


class FalschesClaude:
    """Spielt Claude: schreibt je Lauf eine gültige oder ungültige Übergabe, merkt sich die Aufrufe."""

    def __init__(self, hier: Path, gueltig: list[bool], ok: bool = True):
        self.hier, self.gueltig, self.ok, self.aufrufe = hier, list(gueltig), ok, []

    def __call__(self, agent_name, hier, prompt, **kw):
        self.aufrufe.append((prompt, kw))
        if self.gueltig:
            uebergabe_schreiben(self.hier, self.gueltig.pop(0))
        return Ergebnis(text="Kurzfassung", sitzung="s1", ok=self.ok)


class TestAuftraege(unittest.TestCase):
    def test_nur_auftraege_ohne_dienst(self):
        with mock.patch.object(agent.auftraege, "neue", return_value=[]) as neue:
            agent.auftraege_abarbeiten()
        neue.assert_called_once_with(agent.AGENT, dienst=None)


class TestDokumentAuftrag(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self._tmp.name)
        self.a = {"id": ID, "text": "Dokument: Zusammenfassung IHS 20.10.", "modus": "erledigen"}
        patcher = [mock.patch.object(agent, "HIER", self.hier),
                   mock.patch.object(agent.auftraege, "abschliessen")]
        self.abschliessen = [p.start() for p in patcher][1]
        for p in patcher:
            self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)
        self.weitergeben = mock.Mock(return_value="20261022-120100-dokumente-def456")

    def ausfuehren(self, claude):
        agent.dokument_auftrag(self.a, laufen=claude, weitergeben=self.weitergeben)
        return self.abschliessen.call_args

    def test_gueltig_wird_weitergegeben(self):
        claude = FalschesClaude(self.hier, [True])
        aufruf = self.ausfuehren(claude)
        self.assertEqual(len(claude.aufrufe), 1)
        prompt, kw = claude.aufrufe[0]
        self.assertIn('"art": "zusammenfassung"', prompt)  # Format aus FORMAT.md eingesetzt
        self.assertIn(f"data/weitergabe/{ID}/behauptungen.json", prompt)
        self.assertEqual(kw["auftrag_id"], ID)
        args, kw = self.weitergeben.call_args
        self.assertEqual(args[:3], ("uni", "dokumente", "Bitte als PDF bauen."))
        self.assertEqual(kw["aus_auftrag"], ID)  # nie None, sonst greift der Kettenschutz nicht
        self.assertEqual([p.name for p in kw["dateien"]], ["behauptungen.json", "zusammenfassung.json"])
        self.assertIn("An dokumente weitergegeben (Auftrag 20261022-120100-dokumente-def456)", aufruf.args[1])
        self.assertEqual(aufruf.kwargs, {"sitzung": "s1"})
        self.assertEqual((self.hier / "data" / "weitergabe" / f"{ID}.erledigt").read_text(),
                         "20261022-120100-dokumente-def456")

    def test_eine_nachbesserung(self):
        claude = FalschesClaude(self.hier, [False, True])
        self.ausfuehren(claude)
        self.assertEqual(len(claude.aufrufe), 2)
        self.assertIn("datum", claude.aufrufe[1][0])  # Prüffehler gehen an Claude zurück
        self.assertEqual(claude.aufrufe[1][1]["sitzung_fortsetzen"], "s1")
        self.weitergeben.assert_called_once()

    def test_zweimal_ungueltig_keine_weitergabe(self):
        claude = FalschesClaude(self.hier, [False, False])
        aufruf = self.ausfuehren(claude)
        self.assertEqual(len(claude.aufrufe), 2)
        self.weitergeben.assert_not_called()
        self.assertEqual(aufruf.kwargs["status"], "fehlgeschlagen")
        self.assertIn("Nicht an dokumente weitergegeben", aufruf.args[1])
        self.assertIn("datum", aufruf.args[1])

    def test_claude_fehlgeschlagen(self):
        aufruf = self.ausfuehren(FalschesClaude(self.hier, [], ok=False))
        self.weitergeben.assert_not_called()
        self.assertEqual(aufruf.kwargs["status"], "fehlgeschlagen")

    def test_weitergabe_abgelehnt(self):
        self.weitergeben.side_effect = agent.auftraege.AuftragFehler("nicht erlaubt")
        aufruf = self.ausfuehren(FalschesClaude(self.hier, [True]))
        self.assertEqual(aufruf.kwargs["status"], "fehlgeschlagen")
        self.assertIn("nicht erlaubt", aufruf.args[1])
        self.assertFalse((self.hier / "data" / "weitergabe" / f"{ID}.erledigt").exists())

    def test_vorhandene_uebergabe_ohne_neuen_lauf(self):
        uebergabe_schreiben(self.hier)
        claude = FalschesClaude(self.hier, [])
        self.ausfuehren(claude)
        self.assertEqual(claude.aufrufe, [])
        self.weitergeben.assert_called_once()

    def test_nie_doppelt_weitergeben(self):
        claude = FalschesClaude(self.hier, [True])
        self.ausfuehren(claude)
        self.ausfuehren(claude)
        self.weitergeben.assert_called_once()
        self.assertIn("Schon an dokumente weitergegeben", self.abschliessen.call_args.args[1])

    def test_nur_erster_lauf_und_nur_mit_ausloeser(self):
        auftraege_liste = [{**self.a, "id": "a1"}, {**self.a, "id": "a2", "sitzung": "s", "bezug": None},
                           {**self.a, "id": "a3", "text": "Fass das Transkript zusammen"}]
        with mock.patch.object(agent.auftraege, "neue", return_value=auftraege_liste), \
             mock.patch.object(agent, "dokument_auftrag") as dok, \
             mock.patch.object(agent.claude_lauf, "laufen", return_value=Ergebnis("x", "s", True)):
            agent.auftraege_abarbeiten()
        self.assertEqual([c.args[0]["id"] for c in dok.call_args_list], ["a1"])


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


class TestAuftraegeNachholen(unittest.TestCase):
    def test_auftrag_waehrend_des_laufs(self):
        runden = [[{"id": "a1"}], [{"id": "a1"}, {"id": "a2"}], [{"id": "a1"}, {"id": "a2"}]]
        bearbeitet = []
        agent.auftraege_abarbeiten(neue=lambda: runden.pop(0), bearbeiten=lambda a: bearbeitet.append(a["id"]) or True)
        self.assertEqual(bearbeitet, ["a1", "a2"])

    def test_warten_bricht_ab(self):
        bearbeitet = []
        agent.auftraege_abarbeiten(neue=lambda: [{"id": "a1"}, {"id": "a2"}],
                                   bearbeiten=lambda a: bearbeitet.append(a["id"]) and False)
        self.assertEqual(bearbeitet, ["a1"])


class TestLinksAuswerten(unittest.TestCase):
    SEITE = ('<script type="application/ld+json">{"@type":"Event","name":"Webinar","startDate":'
             '"2026-11-17T10:00:00+01:00","duration":"PT1H"}</script><p>Anmeldung bestätigt</p>')

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = mock.patch.object(agent, "DATA", Path(self._tmp.name))
        self.data.start()

    def tearDown(self):
        self.data.stop()
        self._tmp.cleanup()

    def test_termin_wird_ics(self):
        zusatz, dateien = agent.links_auswerten({"id": "x1", "text": "https://a.de/w?k=1"}, holen=lambda u: self.SEITE)
        self.assertIn("Webinar: Di 17.11.2026 10:00-11:00 Uhr", zusatz)
        self.assertIn("Anmeldung bestätigt", zusatz)
        (pfad,) = dateien
        self.assertIn("DTSTART:20261117T090000Z", pfad.read_text())

    def test_fehler_und_ohne_link(self):
        def kaputt(url):
            raise TimeoutError("weg")
        zusatz, dateien = agent.links_auswerten({"id": "x2", "text": "siehe https://a.de"}, holen=kaputt)
        self.assertIn("Konnte die Seite nicht laden (TimeoutError)", zusatz)
        self.assertEqual(dateien, [])
        self.assertEqual(agent.links_auswerten({"id": "x3", "text": "ohne Link"}), ("", []))


class TestMaterialMeldung(unittest.TestCase):
    def test_einordnung_und_liste(self):
        aufrufe = []

        def claude(agent_name, hier, prompt, **kw):
            aufrufe.append((prompt, kw))
            return Ergebnis("Einstufung: NUR ABLEGEN, Übung nur für Biel", "s", True)

        text = agent.material_meldung("Kurs A", ["06/a.pdf", "06/b.zip"], laufen=claude)
        self.assertEqual(text, "Neues Material in Kurs A:\nEinstufung: NUR ABLEGEN, Übung nur für Biel"
                               "\n\nDateien:\n- 06/a.pdf\n- 06/b.zip")
        prompt, kw = aufrufe[0]
        self.assertIn("- 06/a.pdf", prompt)
        self.assertIn("data/kurse/Kurs A/aufgaben.md", prompt)
        self.assertEqual(kw, {"art": "routine", "zeitgesteuert": True})

    def test_ohne_claude_trotzdem_liste(self):
        def pausiert(*a, **kw):
            raise agent.claude_lauf.Pausiert("Stufe nur_auftraege")

        for laufen in (pausiert, lambda *a, **kw: Ergebnis("kaputt", None, False)):
            text = agent.material_meldung("Kurs A", ["a.pdf"], laufen=laufen)
            self.assertIn("Keine Einordnung", text)
            self.assertTrue(text.endswith("Dateien:\n- a.pdf"))
