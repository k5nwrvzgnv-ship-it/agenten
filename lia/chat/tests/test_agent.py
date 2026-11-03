import json
import tempfile
import unittest
from pathlib import Path

import agent
import chatverlauf
import schnittstelle
from agentkit import claude_lauf

REIHEN = '[[reihe]]\nfach = "Ethik"\nklasse = "8"\ntitel = "Strafe"\nreihenfrage = "Warum strafen wir?"\n'
ORT = {"reihe": "ethik-8-strafe", "chip": "Ethik › 8 › Strafe"}
NEU = ('[[fach]]\nid = "ethik"\nname = "Ethik"\n\n[[klasse]]\nid = "ethik-8"\nfach = "ethik"\nname = "8"\n\n'
       '[[reihe]]\nid = "ethik-8-strafe"\nklasse = "ethik-8"\ntitel = "Strafe"\n\n'
       '[[reihe.stunde]]\nid = "s-1"\nthema = "Einstieg"\n')


class Fake:
    """Ersatz für claude_fragen: merkt sich Prompts, liefert ein Ergebnis oder wirft."""

    def __init__(self, text="Kurze Antwort.", fehler=None, ok=True):
        self.text, self.fehler, self.ok, self.prompts = text, fehler, ok, []

    def __call__(self, prompt, gruendlich, frage_id, netz=False):
        self.prompts.append((prompt, gruendlich))
        self.netz = netz
        if self.fehler:
            raise self.fehler
        return claude_lauf.Ergebnis(text=self.text, sitzung="sitzung-1", ok=self.ok)


class Agent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        wurzel = Path(self.tmp.name)
        self.instanz = wurzel / "instanz"
        self.instanz.mkdir()
        (self.instanz / "reihen.toml").write_text(REIHEN, encoding="utf-8")
        self.ordner = wurzel / "data"
        self.meldungen, self.geloescht = [], []

    def tearDown(self):
        self.tmp.cleanup()

    def abarbeiten(self, fake):
        return agent.fragen_abarbeiten(self.instanz, self.ordner, fragen=fake, melden=self.meldungen.append,
                                       loeschen=self.geloescht.append)

    def test_frage_mit_ort_und_verlauf(self):
        fid = schnittstelle.frage_stellen("Was ist Vergeltung?", ORT, ordner=self.ordner)
        fake = Fake()
        self.assertEqual(self.abarbeiten(fake), 1)
        a = schnittstelle.antwort_holen(fid, self.ordner)
        self.assertEqual((a["ok"], a["text"], a["fehler"], a["chip"]), (True, "Kurze Antwort.", None, ORT["chip"]))
        self.assertFalse(schnittstelle.wartet(fid, self.ordner))
        self.assertIn("Reihenfrage: Warum strafen wir?", fake.prompts[0][0])
        self.assertFalse(fake.prompts[0][1])
        self.assertEqual(self.geloescht, ["sitzung-1"])
        # zweite Frage am selben Ort bekommt den Verlauf mit, eine ohne Ort nicht
        schnittstelle.frage_stellen("Und Prävention?", ORT, gruendlich=True, ordner=self.ordner)
        self.abarbeiten(fake)
        self.assertIn("Lia: Was ist Vergeltung?", fake.prompts[1][0])
        self.assertTrue(fake.prompts[1][1])
        schnittstelle.frage_stellen("Teilzeitantrag?", None, ordner=self.ordner)
        self.abarbeiten(fake)
        self.assertNotIn("Bisheriger Verlauf", fake.prompts[2][0])
        self.assertEqual(len(chatverlauf.lesen(self.ordner)), 3)
        self.assertEqual(self.meldungen, [])

    def test_unbekannte_reihe_ohne_angaben(self):
        schnittstelle.frage_stellen("x", {"reihe": "weg"}, ordner=self.ordner)
        fake = Fake()
        self.abarbeiten(fake)
        self.assertIn("keine weiteren Angaben", fake.prompts[0][0])

    def test_fehler_geben_satz_fuer_lia(self):
        faelle = [(claude_lauf.LimitErreicht(None), "limit", 0), (claude_lauf.KeinPlatz("voll"), "belegt", 0),
                  (claude_lauf.Zeitueberschreitung("lang"), "zeit", 0), (RuntimeError("kaputt"), "technik", 1)]
        for fehler, art, meldungen in faelle:
            with self.subTest(art=art):
                self.meldungen.clear()
                fid = schnittstelle.frage_stellen("x", None, ordner=self.ordner)
                self.abarbeiten(Fake(fehler=fehler))
                a = schnittstelle.antwort_holen(fid, self.ordner)
                self.assertEqual((a["ok"], a["fehler"]), (False, art))
                self.assertEqual(a["text"].split()[0], agent.TEXTE[art].split()[0])
                self.assertEqual(len(self.meldungen), meldungen)
        self.assertEqual(chatverlauf.lesen(self.ordner), [])

    def test_leere_antwort_ist_technikfehler(self):
        fid = schnittstelle.frage_stellen("x", None, ordner=self.ordner)
        self.abarbeiten(Fake(text="", ok=True))
        self.assertEqual(schnittstelle.antwort_holen(fid, self.ordner)["fehler"], "technik")
        self.assertEqual(len(self.meldungen), 1)

    def test_kaputte_frage_und_kaputte_reihen(self):
        (self.ordner / "fragen").mkdir(parents=True)
        (self.ordner / "fragen" / "0123456789ab.json").write_text(json.dumps({"id": "0123456789ab", "text": ""}))
        (self.ordner / "fragen" / "quatsch.json").write_text("nicht json")
        self.abarbeiten(Fake())
        self.assertEqual(schnittstelle.antwort_holen("0123456789ab", self.ordner)["fehler"], "ungueltig")
        self.assertEqual(list((self.ordner / "fragen").iterdir()), [])
        (self.instanz / "reihen.toml").write_text("[[reihe]\n", encoding="utf-8")
        fid = schnittstelle.frage_stellen("x", ORT, ordner=self.ordner)
        self.abarbeiten(Fake())
        self.assertTrue(schnittstelle.antwort_holen(fid, self.ordner)["ok"])
        self.assertEqual(len(self.meldungen), 1)

    def test_neues_format_lerngruppe_und_stunde(self):
        (self.instanz / "reihen.toml").write_text(NEU, encoding="utf-8")
        gruppen = self.instanz / "lerngruppen.toml"
        gruppen.write_text('"ethik-8" = "Geheime Gruppe"\n', encoding="utf-8")
        gruppen.chmod(0o600)
        fake = Fake()
        schnittstelle.frage_stellen("x", dict(ORT, reihe="ethik-8-strafe", stunde_id="s-1"), ordner=self.ordner)
        self.abarbeiten(fake)
        for teil in ("Fach: Ethik, Klasse 8", "Lerngruppe: Geheime Gruppe", "Gerade offen: Stunde 1: Einstieg"):
            self.assertIn(teil, fake.prompts[0][0])
        # Lerngruppen-Datei mit falschen Rechten: ohne Reihe antworten, Jan melden, ohne den Text der Gruppe
        gruppen.chmod(0o644)
        fid = schnittstelle.frage_stellen("y", dict(ORT, reihe="ethik-8-strafe"), ordner=self.ordner)
        self.abarbeiten(fake)
        self.assertTrue(schnittstelle.antwort_holen(fid, self.ordner)["ok"])
        self.assertIn("keine weiteren Angaben", fake.prompts[1][0])
        self.assertEqual(len(self.meldungen), 1)
        self.assertIn("chmod 600", self.meldungen[0])
        self.assertNotIn("Geheime Gruppe", self.meldungen[0])

    def test_lauf_einstellungen_ohne_werkzeuge(self):
        cfg = {"werkzeuge": {"standard": ["Read"]}, "lauf": {"max_schritte": 30, "max_minuten": 15,
                                                             "warten_minuten": 30}}
        neu = agent.lauf_einstellungen(False, cfg)
        self.assertEqual(neu["werkzeuge"]["chat"], [""])
        self.assertEqual(neu["lauf"], {"max_schritte": 3, "max_minuten": 2, "warten_minuten": 1})
        self.assertEqual(agent.lauf_einstellungen(True, cfg)["lauf"]["max_minuten"], 5)
        self.assertEqual(cfg["lauf"]["max_minuten"], 15)
        cmd = claude_lauf.befehl("chat", Path(self.tmp.name), "p", "sonnet",
                                 dict(neu, modelle={}, lauf=neu["lauf"]))
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")

    def test_netz_nur_auf_wunsch(self):
        fid = schnittstelle.frage_stellen("Ferien Bayern 2027?", None, ordner=self.ordner, netz=True)
        fake = Fake()
        self.abarbeiten(fake)
        self.assertTrue(fake.netz)
        self.assertIn("WebSearch", fake.prompts[0][0])
        self.assertTrue(schnittstelle.antwort_holen(fid, self.ordner)["netz"])
        self.assertTrue(chatverlauf.lesen(self.ordner)[-1]["netz"])
        schnittstelle.frage_stellen("Und 2028?", None, ordner=self.ordner)
        self.abarbeiten(fake)
        self.assertFalse(fake.netz)
        self.assertIn("keine Werkzeuge", fake.prompts[1][0])

    def test_lauf_einstellungen_netz(self):
        cfg = {"werkzeuge": {"standard": ["Read"]}, "lauf": {"max_schritte": 30, "max_minuten": 15,
                                                             "warten_minuten": 30},
               "webfetch": {"recherche": ["bpb.de"]}}
        neu = agent.lauf_einstellungen(False, cfg, netz=True)
        self.assertEqual(neu["werkzeuge"]["chat"], ["WebSearch", "WebFetch"])
        self.assertEqual(neu["webfetch"]["chat"], ["bpb.de"])
        self.assertEqual(neu["lauf"], {"max_schritte": agent.NETZ_SCHRITTE, "max_minuten": 4, "warten_minuten": 1})
        self.assertEqual(agent.lauf_einstellungen(True, cfg, netz=True)["lauf"]["max_minuten"], 6)
        self.assertNotIn("chat", cfg["webfetch"])
        cmd = claude_lauf.befehl("chat", Path(self.tmp.name), "p", "sonnet", dict(neu, modelle={}))
        rechte = json.loads(cmd[cmd.index("--settings") + 1])["permissions"]["allow"]
        self.assertEqual(sorted(rechte), ["WebFetch(domain:*.bpb.de)", "WebFetch(domain:bpb.de)", "WebSearch"])
        # ohne Liste kein WebFetch (sonst dürfte es überall hin)
        ohne = agent.lauf_einstellungen(False, {k: v for k, v in cfg.items() if k != "webfetch"}, netz=True)
        self.assertEqual(ohne["werkzeuge"]["chat"], ["WebSearch"])

    def datei(self, name, inhalt=None):
        """Datei zum Hochladen: docx mit Text, leeres PDF (wie ein Scan) oder Bytes."""
        pfad = Path(self.tmp.name) / "upload" / name
        pfad.parent.mkdir(exist_ok=True)
        if isinstance(inhalt, bytes):
            pfad.write_bytes(inhalt)
        elif name.endswith(".docx"):
            import docx
            d = docx.Document()
            d.add_paragraph(inhalt or "Aufgabe 1: Erkläre Vergeltung.")
            d.save(pfad)
        else:
            import pypdf
            w = pypdf.PdfWriter()
            w.add_blank_page(100, 100)
            w.write(pfad)
        return (name, pfad)

    def test_datei_im_prompt_und_folgefrage(self):
        fid = schnittstelle.frage_stellen("Passt das?", ORT, ordner=self.ordner, dateien=[self.datei("AB.docx")])
        fake = Fake()
        self.abarbeiten(fake)
        self.assertIn("mit dieser Frage geschickt", fake.prompts[0][0])
        self.assertIn("--- Datei: AB.docx\nAufgabe 1: Erkläre Vergeltung.", fake.prompts[0][0])
        self.assertFalse(schnittstelle.dateien_ordner(fid, self.ordner).exists())
        e = chatverlauf.lesen(self.ordner)[-1]
        self.assertEqual(e["dateien"], ["AB.docx"])
        self.assertIn("Erkläre Vergeltung", e["dateitext"])
        # Folgefrage am selben Ort bekommt den Text mit, eine ohne Ort nicht
        schnittstelle.frage_stellen("Und Aufgabe 2?", ORT, ordner=self.ordner)
        self.abarbeiten(fake)
        self.assertIn("früheren Frage an diesem Ort", fake.prompts[1][0])
        self.assertIn("Erkläre Vergeltung", fake.prompts[1][0])
        self.assertEqual(chatverlauf.lesen(self.ordner)[-1]["dateitext"], "")
        schnittstelle.frage_stellen("Anderes", None, ordner=self.ordner)
        self.abarbeiten(fake)
        self.assertNotIn("Erkläre Vergeltung", fake.prompts[2][0])

    def test_scan_kaputte_datei_und_kuerzen(self):
        lang = "x" * agent.DATEI_ZEICHEN
        schnittstelle.frage_stellen("?", None, ordner=self.ordner, dateien=[
            self.datei("scan.pdf"), self.datei("kaputt.docx", b"kein zip"), self.datei("lang.docx", lang)])
        fake = Fake()
        self.abarbeiten(fake)
        p = fake.prompts[0][0]
        self.assertIn("--- Datei: scan.pdf\n(Kein Text gefunden, vermutlich ein Scan. Lesen kann ich ihn nicht.)", p)
        self.assertNotIn("Read", p.split("Dateien, die Lia")[1])
        self.assertIn("--- Datei: kaputt.docx\n(Die Datei ließ sich nicht lesen.)", p)
        self.assertIn("x" * (agent.DATEI_ZEICHEN // 3) + "\n[… gekürzt]", p)
        self.assertNotIn("x" * (agent.DATEI_ZEICHEN // 3 + 1), p)
        self.assertEqual(self.meldungen, [])

    def test_dateien_weg_auch_nach_fehler(self):
        fid = schnittstelle.frage_stellen("?", None, ordner=self.ordner, dateien=[self.datei("AB.docx")])
        self.abarbeiten(Fake(fehler=claude_lauf.KeinPlatz("voll")))
        self.assertEqual(schnittstelle.antwort_holen(fid, self.ordner)["fehler"], "belegt")
        self.assertFalse(schnittstelle.dateien_ordner(fid, self.ordner).exists())

    def test_sitzungen_loeschen(self):
        sitzungen = Path(self.tmp.name) / "projekte"
        sitzungen.mkdir()
        (sitzungen / "s1.jsonl").write_text("x")
        (sitzungen / "s2.jsonl").write_text("x")
        agent.sitzung_loeschen("s1", sitzungen)
        agent.sitzung_loeschen(None, sitzungen)
        self.assertEqual([p.name for p in sitzungen.iterdir()], ["s2.jsonl"])
        agent.aufraeumen(self.ordner, sitzungen)
        self.assertEqual(list(sitzungen.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
