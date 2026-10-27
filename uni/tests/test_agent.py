import json
import tempfile
import unittest
from datetime import datetime
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


class OhneTelegram(unittest.TestCase):
    """Meldungen landen in self.gemeldet statt in shared/meldungen/ (sonst schickt die Zentrale sie echt)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hier = Path(self._tmp.name)
        self.gemeldet, self.angelegt, self.reihenfolge = [], [], []
        for p in (mock.patch.object(agent, "HIER", self.hier),
                  mock.patch.object(agent.meldungen, "melden", self.melden),
                  mock.patch.object(agent.meldungen, "neue", lambda *a, **kw: [])):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)

    def melden(self, agent_name, text, dateien=None, **kw):
        self.gemeldet.append((text, dateien))
        self.reihenfolge.append("meldung")
        return f"m{len(self.gemeldet)}"

    def neuer_entwurf(self, agent_name, **kw):
        self.angelegt.append(kw)
        self.reihenfolge.append("entwurf")
        return f"e{len(self.angelegt)}"


class TestMailEntwuerfe(OhneTelegram):

    def schreiben(self, schluessel, name, inhalt):
        ordner = agent.entwurf_ordner(schluessel)
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / name).write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt))
        return ordner

    def test_einreichen_einmal_und_ungueltige(self):
        ordner = self.schreiben("a1", "mail_1.json", {"an": ["a@hnee.de"], "betreff": "B", "text": "T"})
        self.schreiben("a1", "mail_2.json", {"an": ["kaputt"], "betreff": "B", "text": "T"})
        self.schreiben("a1", "mail_3.json", "{kein json")
        zeilen = agent.entwuerfe_einreichen("a1", neuer_entwurf=self.neuer_entwurf)
        self.assertEqual(len(self.angelegt), 1)
        self.assertEqual(self.angelegt[0]["typ"], "mail")
        self.assertIn("An: a@hnee.de", self.angelegt[0]["inhalt"])
        self.assertEqual(zeilen[0], "Mail-Entwurf an a@hnee.de liegt zur Freigabe: B")
        self.assertEqual(sum("nicht vorgelegt" in z for z in zeilen), 2)
        self.assertEqual(agent.entwuerfe_einreichen("a1", neuer_entwurf=self.neuer_entwurf), [])
        self.assertTrue((ordner / "mail_1.eingereicht").exists())
        self.assertEqual(self.gemeldet, [("T", None)])  # Entwurfstext allein, keine Originalmail

    def test_wortlaut_und_entwurf_einzeln_vor_dem_entwurf(self):
        mails = self.hier / "data" / "mails"
        agent.mail.mail_merken({"uid": 7, "von": "Böhme <b@hnee.de>", "message_id": "<m@hnee.de>",
                                "betreff": "Betreuung", "datum": "2026-10-27T10:05:00+01:00",
                                "text": "Hallo Herr Kleinke, gern. Grüße", "wortlaut": "Hallo Herr Kleinke,\n\ngern.\n\nGrüße",
                                "anhaenge": []}, mails)
        self.schreiben("p1", "mail_1.json", {"an": ["b@hnee.de"], "betreff": "AW: Betreuung", "text": "Vielen Dank",
                                             "antwort_auf_uid": 7})
        echt = agent.mail.mail_holen
        with mock.patch.object(agent.mail, "mail_holen", lambda uid, ordner=None: echt(uid, mails)):
            zeilen = agent.entwuerfe_einreichen("p1", neuer_entwurf=self.neuer_entwurf, nur_fehler=True)
        self.assertEqual(zeilen, [])
        self.assertEqual(self.reihenfolge, ["meldung", "meldung", "entwurf"])
        wortlaut, entwurf = self.gemeldet[0][0], self.gemeldet[1][0]
        self.assertTrue(wortlaut.startswith("Von: Böhme <b@hnee.de>\nDatum: 27.10.2026 10:05\nBetreff: Betreuung"))
        self.assertTrue(wortlaut.endswith("Hallo Herr Kleinke,\n\ngern.\n\nGrüße"))
        self.assertEqual(entwurf, "Vielen Dank")
        self.assertEqual(self.angelegt[0]["daten"]["in_reply_to"], "<m@hnee.de>")

    def test_bis_gesendet(self):
        offen = [[{"id": "m1"}], [{"id": "m1"}], []]
        with mock.patch.object(agent.meldungen, "neue", lambda *a, **kw: offen.pop(0)):
            schlaefe = []
            self.assertTrue(agent.bis_gesendet(["m1"], schlafen=schlaefe.append))
        self.assertEqual(schlaefe, [5, 5])
        with mock.patch.object(agent.meldungen, "neue", lambda *a, **kw: [{"id": "m1"}]):
            self.assertFalse(agent.bis_gesendet(["m1"], max_sekunden=10, schlafen=lambda s: None))

    def test_hinweis_nennt_ordner(self):
        self.assertIn("data/entwuerfe/post-1/mail_1.json", agent.entwurf_hinweis("post-1"))

    def test_aendern_mit_regel(self):
        alt = {"id": "20261024-000000-uni-aaaaaa", "typ": "mail",
               "daten": {"an": ["a@hnee.de"], "cc": [], "betreff": "B", "text": "Hi", "in_reply_to": "<x@y>",
                         "references": "<x@y>", "antwort_auf": "A: B"}}
        auftrag = {"id": "20261024-000100-uni-bbbbbb", "text": "förmlicher, mit Sie", "bezug": alt["id"],
                   "quelle": "telegram-aendern"}
        prompts = []

        def claude(agent_name, hier, prompt, **kw):
            prompts.append(prompt)
            self.schreiben(auftrag["id"], "mail_1.json", {"an": ["a@hnee.de"], "betreff": "B", "text": "Guten Tag"})
            self.schreiben(auftrag["id"], "regel.json", {"regel": "Lehrende siezen", "anlass": "Kommentar"})
            return Ergebnis("Förmlicher formuliert.", "s", True)

        with mock.patch.object(agent.freigabe, "neuer_entwurf", self.neuer_entwurf), \
             mock.patch.object(agent.regeln, "regel_vorschlagen") as regel, \
             mock.patch.object(agent.auftraege, "abschliessen") as abschliessen:
            agent.aenderung_bearbeiten(auftrag, laufen=claude, holen={alt["id"]: alt}.get)
        self.assertIn("förmlicher, mit Sie", prompts[0])
        self.assertIn('"text": "Hi"', prompts[0])
        self.assertEqual(self.angelegt[0]["vorgaenger"], alt["id"])
        self.assertEqual(self.angelegt[0]["daten"]["in_reply_to"], "<x@y>")
        self.assertEqual(self.gemeldet, [("Guten Tag", None)])  # bei Überarbeitung kein Wortlaut
        regel.assert_called_once_with(agent.AGENT, "Lehrende siezen", "Kommentar")
        self.assertIn("Regelvorschlag zur Freigabe", abschliessen.call_args.args[1])

    def test_aendern_nur_bei_mail(self):
        with mock.patch.object(agent.auftraege, "abschliessen") as abschliessen:
            agent.aenderung_bearbeiten({"id": "x", "text": "k", "bezug": "e"}, holen=lambda e: None)
        self.assertEqual(abschliessen.call_args.kwargs["status"], "fehlgeschlagen")

    def test_ausfuehren_sendet_freigegebene_daten(self):
        with mock.patch.object(agent.mail, "senden", return_value="gesendet") as senden:
            self.assertEqual(agent.ausfuehren({"typ": "mail", "daten": {"an": ["a@hnee.de"]}}), "gesendet")
        senden.assert_called_once_with(agent.cfg, {"an": ["a@hnee.de"]})


class TestTermine(OhneTelegram):
    JETZT = datetime(2026, 10, 27, 11, 0, tzinfo=agent.termine.ZONE)

    def schreiben(self, schluessel, name, inhalt):
        ordner = agent.entwurf_ordner(schluessel)
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / name).write_text(json.dumps(inhalt))
        return ordner

    def test_vorschlag_abgleich_und_nur_einmal(self):
        ordner = self.schreiben("post-1", "termin_1.json", {"titel": "Exkursion Holzschutz", "beginn": "2026-10-27T14:00",
                                                            "ort": "Rio-Reiser-Platz, Berlin"})
        self.schreiben("post-1", "termin_2.json", {"titel": "Alt", "beginn": "2026-10-20T14:00"})
        self.schreiben("post-1", "termin_3.json", {"titel": "CAM Exkursion Homag", "beginn": "2026-11-05T08:45",
                                                   "ende": "2026-11-05T14:00"})
        im_kalender = [agent.kalender.Termin(datetime(2026, 11, 5, 8, 45, tzinfo=agent.termine.ZONE),
                                             datetime(2026, 11, 5, 14, tzinfo=agent.termine.ZONE),
                                             "Exkursion Homag", "", False, "x")]
        zeilen, dateien = agent.termine_einreichen("post-1", jetzt=self.JETZT, vorhandene=im_kalender)
        self.assertEqual(zeilen[0], "Termin-Vorschlag termin_2.json verworfen: Termin liegt in der Vergangenheit")
        self.assertIn("Termin zum Antippen: Exkursion Holzschutz: Di 27.10.2026 14:00-15:00 Uhr, Rio-Reiser-Platz, "
                      "Berlin. Erinnerung 1 Tag und 2 Std. vorher.", zeilen)
        self.assertIn("Steht schon in deinem Kalender: CAM Exkursion Homag: Do 05.11.2026 08:45-14:00 Uhr", zeilen)
        (ics,) = dateien
        self.assertIn("TRIGGER:-PT120M", ics.read_text())
        self.assertTrue((ordner / "termin_1.eingereicht").exists())
        self.schreiben("post-2", "termin_1.json", {"titel": "Exkursion Holzschutz", "beginn": "2026-10-27T14:00"})
        self.assertEqual(agent.termine_einreichen("post-2", jetzt=self.JETZT, vorhandene=[]), ([], []))

    def test_kalender_nicht_lesbar(self):
        self.schreiben("a1", "termin_1.json", {"titel": "Gespräch Böhme", "beginn": "2026-11-02T10:00"})
        with mock.patch.object(agent.kalender, "termine", side_effect=agent.kalender.KalenderFehler("Kalender 1")):
            zeilen, dateien = agent.termine_einreichen("a1", jetzt=self.JETZT)
        self.assertEqual(len(dateien), 1)
        self.assertTrue(zeilen[0].startswith("Termin zum Antippen: Gespräch Böhme"))

    def test_ohne_entwuerfe(self):
        self.assertEqual(agent.termine_einreichen("leer"), ([], []))

    def test_hinweis_nennt_termine(self):
        self.assertIn("data/entwuerfe/post-1/termin_1.json", agent.entwurf_hinweis("post-1"))


class TestLernblaetter(OhneTelegram):
    """Claude schreibt blatt_<n>.json, Python baut das PDF (LibreOffice hier durch eine Attrappe ersetzt)."""

    def setUp(self):
        super().setUp()
        self.ordner = self.hier / "data" / "lernblaetter" / ID
        self.aufrufe = []

    @staticmethod
    def bauen(ordner, profil):
        def pdf(docx, ziel):
            (ziel / f"{docx.stem}.pdf").write_text("pdf")
            return ziel / f"{docx.stem}.pdf"
        return agent.lernblatt.bauen_neue(ordner, profil, als_pdf=pdf)

    def blatt(self, inhalt):
        self.ordner.mkdir(parents=True, exist_ok=True)
        (self.ordner / "blatt_1.json").write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt))

    def claude(self, korrigiert=None, fehler=None):
        def laufen(agent_name, hier, prompt, **kw):
            self.aufrufe.append((prompt, kw))
            if fehler:
                raise fehler
            if korrigiert:
                self.blatt(korrigiert)
            return Ergebnis(text="Korrigiert.", sitzung="s2", ok=True)
        return laufen

    def test_ohne_blatt_nichts(self):
        self.assertEqual(agent.lernblaetter_bauen(ID, "a2", "s1", laufen=self.claude()), ([], [], "s1"))
        self.assertEqual(self.aufrufe, [])

    def test_gueltiges_blatt_wird_pdf_ohne_claude(self):
        self.blatt(BESCHREIBUNG)
        zeilen, pdfs, sitzung = agent.lernblaetter_bauen(ID, "a2", "s1", laufen=self.claude(), bauen=self.bauen)
        self.assertEqual((zeilen, sitzung, self.aufrufe), ([], "s1", []))
        self.assertEqual(pdfs, [self.ordner / "blatt_1" / "IHS.pdf"])
        self.assertEqual(agent.lernblaetter_bauen(ID, "a2", "s1", bauen=self.bauen)[1], [])  # schon geschickt

    def test_ungueltig_eine_nachbesserung_in_derselben_sitzung(self):
        self.blatt({**BESCHREIBUNG, "datum": "x"})
        zeilen, pdfs, sitzung = agent.lernblaetter_bauen(ID, "a2", "s1", laufen=self.claude(BESCHREIBUNG),
                                                          bauen=self.bauen)
        self.assertEqual((zeilen, sitzung, len(pdfs)), ([], "s2", 1))
        prompt, kw = self.aufrufe[0]
        self.assertIn("blatt_1.json:\n- datum", prompt)
        self.assertIn(f"data/lernblaetter/{ID}/", prompt)
        self.assertEqual((kw["sitzung_fortsetzen"], kw["auftrag_id"]), ("s1", "a2"))

    def test_bleibt_ungueltig_steht_im_ergebnis(self):
        self.blatt("{kein json")
        zeilen, pdfs, _ = agent.lernblaetter_bauen(ID, "a2", "s1", laufen=self.claude(), bauen=self.bauen)
        self.assertEqual((pdfs, len(self.aufrufe)), ([], 1))
        self.assertEqual(len(zeilen), 1)
        self.assertTrue(zeilen[0].startswith("Lernblatt blatt_1.json nicht gebaut, Beschreibung ungültig:"))

    def test_claude_nicht_verfuegbar_wirft_nicht(self):
        self.blatt({**BESCHREIBUNG, "datum": "x"})
        zeilen, pdfs, sitzung = agent.lernblaetter_bauen(
            ID, "a2", "s1", laufen=self.claude(fehler=agent.claude_lauf.Pausiert("Stufe")), bauen=self.bauen)
        self.assertEqual((pdfs, sitzung), ([], "s1"))
        self.assertIn("Nachbesserung des Lernblatts nicht möglich: Stufe", zeilen[0])
        self.assertIn("nicht gebaut", zeilen[1])

    def test_hinweis_legt_format_ab(self):
        text = agent.lernblatt_hinweis(ID)
        self.assertIn(f"data/lernblaetter/{ID}/blatt_1.json", text)
        self.assertIn("data/lernblaetter/FORMAT.md", text)
        self.assertIn("## Zusammenfassung", (self.hier / "data" / "lernblaetter" / "FORMAT.md").read_text())
