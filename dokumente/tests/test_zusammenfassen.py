"""Ablauf der Zusammenfassung ohne Netz: Claude und Vorschau werden ersetzt, die Prüfung des Renderers ist echt."""

import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace

import renderer
from renderer.pruefung import lesen

import zusammenfassen as z

HIER = Path(__file__).resolve().parent.parent
BEISPIEL = json.loads((HIER.parent / "shared/renderer/beispiele/zusammenfassung-beispiel.json").read_text())
BEHAUPTUNGEN = [{"nr": 1, "aussage": "Baulicher Holzschutz hat Vorrang.", "quellen": [{"art": "folie", "stelle": "6"}]},
                {"nr": 2, "aussage": "GK 4 heißt Erdkontakt.", "kennzeichnung": "muendlich"}]


class TestReineLogik(unittest.TestCase):
    def test_behauptungsliste_finden(self):
        self.assertEqual(z.behauptungsliste_finden(["data/eingang/x/t.md", "data/eingang/x/behauptungen.json"]),
                         "data/eingang/x/behauptungen.json")
        self.assertEqual(z.behauptungsliste_finden(["a/Behauptungen-2.json"]), "a/Behauptungen-2.json")
        self.assertIsNone(z.behauptungsliste_finden(["a/behauptungen.md", "a/meine-behauptungen.json"]))

    def test_behauptungen_lesen(self):
        self.assertEqual(len(z.behauptungen_lesen(json.dumps(BEHAUPTUNGEN))), 2)
        for kaputt, teil in (("{", "kein gültiges JSON"), ("[]", "nicht leere Liste"), ('["x"]', "kein Objekt"),
                             ('[{"nr": 1, "aussage": "a"}, {"nr": 1, "aussage": "b"}]', "[1].nr"),
                             ('[{"nr": true, "aussage": "a"}]', "[0].nr"), ('[{"nr": 1, "aussage": " "}]', "aussage")):
            with self.assertRaises(z.BehauptungslisteUngueltig) as f:
                z.behauptungen_lesen(kaputt)
            self.assertIn(teil, str(f.exception))

    def test_bericht_ok(self):
        self.assertEqual(z.bericht_pruefen('{"abgedeckt": [1, 2], "fehlt": [], "erfunden": [], "darstellung": []}',
                                           [1, 2]), [])
        self.assertEqual(z.bericht_pruefen('{"erfunden": []}', []), [])  # ohne Liste

    def test_bericht_probleme(self):
        p = z.bericht_pruefen(json.dumps({"abgedeckt": [1, 9], "fehlt": [1], "erfunden": ["GK 5"],
                                          "darstellung": ["Seite 2 abgeschnitten"], "notiz": "x"}), [1, 2, 3])
        text = "\n".join(p)
        for teil in ("Unbekannte Felder: notiz", "abgedeckt: unbekannte Nummern [9]", "zugleich abgedeckt und fehlend: [1]",
                     "Nicht beurteilt: Behauptungen [2, 3]", "Fehlende Behauptungen: [1]", "Dazuerfunden: GK 5",
                     "Darstellung: Seite 2 abgeschnitten"):
            self.assertIn(teil, text)
        self.assertEqual(z.bericht_pruefen(None, []), ["kontrolle.json fehlt"])
        self.assertIn("kein gültiges JSON", z.bericht_pruefen("{", [])[0])
        self.assertIn("muss eine Liste", z.bericht_pruefen('{"fehlt": 3}', [])[0])

    def test_beschreibung_lesen(self):
        self.assertEqual(z.beschreibung_lesen(json.dumps(BEISPIEL))["art"], "zusammenfassung")
        for text in (None, "{", '{"art": "folien"}'):
            with self.assertRaises(z.BeschreibungKaputt):
                z.beschreibung_lesen(text)

    def test_dateiname(self):
        self.assertEqual(z.dateiname("Integrierter Holzschutz: Grundlagen"), "integrierter-holzschutz-grundlagen")
        self.assertEqual(z.dateiname("Öl & Bläue / Fäulnis"), "oel-blaeue-faeulnis")
        self.assertEqual(z.dateiname("???"), "zusammenfassung")
        self.assertLessEqual(len(z.dateiname("a" * 100)), 60)

    def test_format_abschnitt(self):
        text = z.format_abschnitt((HIER.parent / "shared/renderer/FORMAT.md").read_text())
        self.assertIn("## Allgemein", text)
        self.assertIn("## Zusammenfassung", text)
        self.assertNotIn("## Folien", text)
        self.assertNotIn("## Arbeitsblatt", text)
        with self.assertRaises(ValueError):
            z.format_abschnitt("# nur Titel")

    def test_ursprung(self):
        kette = {"a1": {"id": "a1", "bezug": None}, "a2": {"id": "a2", "bezug": "a1"}}
        self.assertEqual(z.ursprung({"id": "a3", "bezug": "a2"}, kette.__getitem__)["id"], "a1")
        self.assertEqual(z.ursprung({"id": "a3", "bezug": "fehlt"}, kette.__getitem__)["id"], "a3")

    def test_profil_passt_zum_renderer(self):
        profil = tomllib.loads((HIER / "profil-zusammenfassung.toml").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            e = renderer.bauen(BEISPIEL, Path(tmp) / "z.docx", profil=profil, vorschau=False)
            self.assertIn("Integrierter Holzschutz", e.kontrolltext)


class FalscherClaude:
    """Spielt Claude: führt je Aufruf den nächsten Schritt aus (schreibt Dateien) und merkt sich die Prompts."""

    def __init__(self, ordner: Path, schritte: list):
        self.ordner, self.schritte, self.prompts = ordner, list(schritte), []

    def __call__(self, prompt, sitzung):
        self.prompts.append((prompt, sitzung))
        schritt = self.schritte.pop(0)
        antwort = "fertig"
        for name, inhalt in schritt.items():
            if name == "antwort":
                antwort = inhalt
            else:
                (self.ordner / name).write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt))
        return antwort, "sitzung-1", True


def falsch_bauen(beschreibung, ziel):
    """Prüft echt (renderer.pruefung), baut aber nur Platzhalter statt docx und Vorschau."""
    b = lesen(beschreibung)
    ziel.write_text("docx")
    vorschau = ziel.parent / f"{ziel.stem}-vorschau"
    vorschau.mkdir(exist_ok=True)
    (vorschau / f"{ziel.stem}.pdf").write_text("pdf")
    (vorschau / "seite-01.png").write_text("png")
    return SimpleNamespace(pdf=vorschau / f"{ziel.stem}.pdf", bilder=[vorschau / "seite-01.png"],
                           kontrolltext=b["titel"], hinweise=[])


OK = {"abgedeckt": [1, 2], "fehlt": [], "erfunden": [], "darstellung": []}


class TestAblauf(unittest.TestCase):
    def setUp(self):
        self.agent_dir = Path(tempfile.mkdtemp())
        self.ordner = self.agent_dir / "data/ausgang/a1"
        eingang = self.agent_dir / "data/eingang/a1"
        eingang.mkdir(parents=True)
        (eingang / "behauptungen.json").write_text(json.dumps(BEHAUPTUNGEN))
        self.ordner.mkdir(parents=True)

    def lauf(self, schritte, behauptungen="data/eingang/a1/behauptungen.json", sitzung=None, bauen=falsch_bauen):
        self.claude = FalscherClaude(self.ordner, schritte)
        return z.erstellen({"id": "a1", "text": "Fasse zusammen", "von": "uni"}, self.ordner, self.agent_dir,
                           self.claude, bauen, "FORMAT", behauptungen, sitzung)

    def test_gerade_durch(self):
        f = self.lauf([{"beschreibung.json": BEISPIEL}, {"kontrolle.json": OK, "antwort": "Kurzfassung"}])
        self.assertEqual(f.docx.name, "integrierter-holzschutz-grundlagen.docx")
        self.assertEqual(f.pdf, self.ordner / "integrierter-holzschutz-grundlagen.pdf")
        self.assertTrue(f.pdf.is_file())
        self.assertEqual((f.kontrollen, f.antwort, f.sitzung), (1, "Kurzfassung", "sitzung-1"))
        start, kontrolle = self.claude.prompts
        self.assertIn("von uni (Agent)", start[0])
        self.assertIn("data/eingang/a1/behauptungen.json", start[0])
        self.assertIn("data/ausgang/a1/beschreibung.json", start[0])
        self.assertIsNone(start[1])
        self.assertEqual(kontrolle[1], "sitzung-1")  # Kontrolle in derselben Sitzung
        self.assertIn("data/ausgang/a1/kontrolltext.txt", kontrolle[0])
        self.assertIn("seite-01.png", kontrolle[0])
        self.assertIn("Integrierter Holzschutz", z.ergebnistext(f, 2))
        self.assertIn("alle 2 Behauptungen", z.ergebnistext(f, 2))

    def test_ungueltige_beschreibung_geht_an_claude_zurueck(self):
        kaputt = {**BEISPIEL, "datum": "gestern"}
        f = self.lauf([{"beschreibung.json": "{"}, {"beschreibung.json": kaputt}, {"beschreibung.json": BEISPIEL},
                       {"kontrolle.json": OK}])
        self.assertEqual(f.kontrollen, 1)
        prompts = [p for p, _ in self.claude.prompts]
        self.assertIn("kein gültiges JSON", prompts[1])
        self.assertIn("datum", prompts[2])

    def test_zu_viele_bauversuche(self):
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            self.lauf([{"beschreibung.json": "{"}] * 3)
        self.assertIn("nach 3 Versuchen", str(f.exception))

    def test_kontrolle_findet_fehler_und_baut_neu(self):
        verbessert = {**BEISPIEL, "untertitel": "korrigiert"}
        f = self.lauf([{"beschreibung.json": BEISPIEL},
                       {"kontrolle.json": {**OK, "abgedeckt": [1], "fehlt": [2]}, "beschreibung.json": verbessert},
                       {"kontrolle.json": OK}])
        self.assertEqual(f.kontrollen, 2)
        self.assertIn("Fehlende Behauptungen: [2]", self.claude.prompts[2][0])  # Python sagt, was es fand

    def test_ok_aber_noch_geaendert_wird_neu_geprueft(self):
        f = self.lauf([{"beschreibung.json": BEISPIEL},
                       {"kontrolle.json": OK, "beschreibung.json": {**BEISPIEL, "untertitel": "neu"}},
                       {"kontrolle.json": OK}])
        self.assertEqual(f.kontrollen, 2)

    def test_bericht_luegt_nicht_durch(self):
        """Claude meldet ok, lässt aber Behauptung 2 unbeurteilt: nicht fertig."""
        halb = {**OK, "abgedeckt": [1]}
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            self.lauf([{"beschreibung.json": BEISPIEL}, {"kontrolle.json": halb}, {"kontrolle.json": halb},
                       {"kontrolle.json": halb}])
        self.assertIn("Nicht beurteilt: Behauptungen [2]", str(f.exception))

    def test_ohne_behauptungsliste(self):
        f = self.lauf([{"beschreibung.json": BEISPIEL}, {"kontrolle.json": {"erfunden": []}}], behauptungen=None)
        self.assertEqual(f.kontrollen, 1)
        self.assertIn("Keine Behauptungsliste", self.claude.prompts[1][0])
        self.assertIn("gegen die Dateien geprüft", z.ergebnistext(f, 0))

    def test_kein_zusammenfassungsauftrag(self):
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            self.lauf([{"antwort": "NICHT_UNTERSTUETZT: Das ist ein Brief."}], behauptungen=None)
        self.assertIn("nur Zusammenfassungen. Das ist ein Brief.", str(f.exception))

    def test_antwort_von_jan_setzt_sitzung_fort(self):
        self.lauf([{"beschreibung.json": BEISPIEL}, {"kontrolle.json": OK}], sitzung="alt")
        self.assertEqual(self.claude.prompts[0][1], "alt")
        self.assertIn("Jan antwortet", self.claude.prompts[0][0])

    def test_fehler_des_agenten_gehen_nicht_an_claude(self):
        def bauen(b, ziel):
            raise ValueError("Profil kaputt")
        with self.assertRaises(ValueError):
            self.lauf([{"beschreibung.json": BEISPIEL}], bauen=bauen)
        self.assertEqual(len(self.claude.prompts), 1)

    def test_ohne_vorschau_kein_pdf(self):
        def bauen(b, ziel):
            return SimpleNamespace(pdf=None, bilder=[], kontrolltext="", hinweise=["Keine Vorschau: soffice fehlt"])
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            self.lauf([{"beschreibung.json": BEISPIEL}], bauen=bauen)
        self.assertIn("soffice fehlt", str(f.exception))

    def test_claude_fehler(self):
        claude = lambda prompt, sitzung: ("Abbruch", None, False)  # noqa: E731
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            z.erstellen({"id": "a1", "text": "x"}, self.ordner, self.agent_dir, claude, falsch_bauen, "F")
        self.assertIn("Abbruch", str(f.exception))


if __name__ == "__main__":
    unittest.main()
