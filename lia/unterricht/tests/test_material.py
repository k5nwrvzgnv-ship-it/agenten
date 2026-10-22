import functools
import json
import tempfile
import tomllib
import unittest
from pathlib import Path

import material
import renderer
from agentkit.claude_lauf import Ergebnis

PROFIL = tomllib.loads((Path(__file__).resolve().parent.parent / "profil.toml").read_text(encoding="utf-8"))
BAUEN = functools.partial(renderer.bauen, vorschau=False)  # Vorschau prüft der Renderer selbst (dauert 5 s)

BLATT = {"art": "arbeitsblatt", "titel": "Der kategorische Imperativ", "nummer": "1", "bloecke": [
    {"typ": "merksatz", "text": "Handle nur nach derjenigen Maxime, durch die du zugleich wollen kannst, "
                                "dass sie ein allgemeines Gesetz werde."},
    {"typ": "aufgaben", "aufgaben": [{"text": "Erkläre den Merksatz.", "antwort": {"art": "linien", "anzahl": 3}}]},
]}
FOLIEN = {"art": "folien", "titel": "Kant für Einsteiger", "untertitel": "Ethik · Klasse 10", "folien": [
    {"titel": "Ziel für heute", "inhalt": [{"typ": "zentriert", "absaetze": ["Wir lernen Kants Pflichtethik."]}]},
]}


class FalscherClaude:
    """Spielt Claude: jeder Schritt schreibt (oder nicht) die Beschreibung und antwortet mit einem Text."""

    def __init__(self, ordner: Path, schritte: list):
        self.pfad = ordner / "beschreibung.json"
        self.schritte = list(schritte)
        self.prompts, self.sitzungen = [], []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append(prompt)
        self.sitzungen.append(sitzung)
        inhalt, text = self.schritte.pop(0)
        if inhalt is not None:
            self.pfad.write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt), encoding="utf-8")
        return Ergebnis(text=text, sitzung="s1", ok=True, usd=0.5, tokens=1000)


class MaterialTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.auftrag = {"id": "20261022-120000-unterricht-abcdef", "text": "Arbeitsblatt kategorischer Imperativ, Kl. 10"}
        self.ordner = self.hier / "data" / "arbeit" / self.auftrag["id"]

    def bearbeiten(self, schritte):
        claude = FalscherClaude(self.ordner, schritte)
        return material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN), claude

    def test_format_nur_passende_abschnitte(self):
        text = material.format_abschnitte(material.FORMAT_DATEI.read_text(encoding="utf-8"))
        self.assertIn("## Arbeitsblatt", text)
        self.assertIn("## Folien", text)
        self.assertIn("## Allgemein", text)
        self.assertNotIn("## Zusammenfassung", text)
        with self.assertRaises(ValueError):
            material.format_abschnitte("# Format\n## Allgemein\nx")

    def test_dateiname(self):
        self.assertEqual(material.dateiname({"art": "arbeitsblatt", "titel": "Muss ich helfen? Ja/Nein!"}),
                         "Arbeitsblatt Muss ich helfen JaNein.docx")
        self.assertEqual(material.dateiname(FOLIEN), "Folien Kant für Einsteiger.pptx")
        self.assertTrue(material.dateiname({"art": "folien", "titel": "x" * 300}).endswith("x.pptx"))
        lang = "Kann ich wollen, dass alle so handeln wie ich? – Kants kategorischer Imperativ"
        self.assertEqual(material.dateiname({"art": "arbeitsblatt", "titel": lang}),
                         "Arbeitsblatt Kann ich wollen dass alle so handeln wie ich Kants.docx")

    def test_gelingt_beim_ersten_mal(self):
        f, claude = self.bearbeiten([(BLATT, "Entwurf"), (None, "Ein Blatt mit Merksatz und einer Aufgabe.")])
        self.assertEqual(f.datei, self.ordner / "Arbeitsblatt Der kategorische Imperativ.docx")
        self.assertTrue(f.datei.is_file())
        self.assertEqual(f.begleittext, "Ein Blatt mit Merksatz und einer Aufgabe.")
        self.assertEqual((f.laeufe, f.usd, f.tokens, f.sitzung), (2, 1.0, 2000, "s1"))
        self.assertIn("kategorischer Imperativ, Kl. 10", claude.prompts[0])
        self.assertIn("Ethik", claude.prompts[0])
        self.assertIn("data/arbeit/20261022-120000-unterricht-abcdef/beschreibung.json", claude.prompts[0])
        self.assertIn("Skill einzelmaterial", claude.prompts[0])
        self.assertIn("Kontrolltext", claude.prompts[1])
        self.assertIn("Handle nur nach derjenigen Maxime", claude.prompts[1])
        self.assertEqual(claude.sitzungen, [None, "s1"])

    def test_fehler_gehen_an_claude_zurueck(self):
        falsch = dict(BLATT, farbe="rot")
        f, claude = self.bearbeiten([(falsch, "a"), (BLATT, "b"), (None, "fertig")])
        self.assertIn("farbe", claude.prompts[1])
        self.assertIn("Korrigiere", claude.prompts[1])
        self.assertEqual(f.laeufe, 3)
        self.assertEqual(f.begleittext, "fertig")

    def test_fehlende_datei_kaputtes_json_falsche_art(self):
        f, claude = self.bearbeiten([(None, "a"), ("{kaputt", "b"), ({"art": "zusammenfassung"}, "c"),
                                     (FOLIEN, "d"), (None, "Folien fertig")])
        self.assertIn("fehlt", claude.prompts[1])
        self.assertIn("kein gültiges JSON", claude.prompts[2])
        self.assertIn("art", claude.prompts[3])
        self.assertEqual(f.datei.suffix, ".pptx")

    def test_gibt_nach_max_korrekturen_auf(self):
        with self.assertRaises(material.MaterialFehler):
            self.bearbeiten([("{", "x")] * (material.MAX_KORREKTUREN + 1))

    def test_kontrolle_ueberarbeitet(self):
        besser = dict(BLATT, titel="Kants kategorischer Imperativ")
        f, claude = self.bearbeiten([(BLATT, "a"), (besser, "Überarbeitet.")])
        self.assertEqual(f.datei.name, "Arbeitsblatt Kants kategorischer Imperativ.docx")
        self.assertEqual(f.begleittext, "Überarbeitet.")
        self.assertEqual(f.laeufe, 2)

    def test_lauf_fehlgeschlagen(self):
        def laufen(prompt, sitzung=None):
            return Ergebnis(text="kaputt", sitzung=None, ok=False)
        with self.assertRaises(material.MaterialFehler):
            material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=laufen, bauen=BAUEN)

    def test_zeitbudget(self):
        uhr = iter([0, material.ZEIT_BUDGET_S + 1])
        claude = FalscherClaude(self.ordner, [("{", "a"), (BLATT, "b")])
        with self.assertRaises(material.MaterialFehler):
            material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN, uhr=lambda: next(uhr))
        self.assertEqual(len(claude.prompts), 1)

    def test_kontrolle_ohne_vorschau(self):
        text = material.prompt_kontrolle("b.json", "Inhalt", [], ["Keine Vorschau: soffice fehlt"])
        self.assertIn("soffice fehlt", text)
        self.assertNotIn("Öffne jedes", text)
        text = material.prompt_kontrolle("b.json", "Inhalt", ["data/x-vorschau/seite-1.png"], [])
        self.assertIn("- data/x-vorschau/seite-1.png", text)


if __name__ == "__main__":
    unittest.main()
