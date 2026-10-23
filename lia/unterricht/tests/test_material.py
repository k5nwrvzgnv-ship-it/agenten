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
        self.assertNotIn("laufende Reihen", claude.prompts[0])
        self.assertNotIn("früheren Reihen", claude.prompts[0])
        self.assertIn("Handle nur nach derjenigen Maxime", claude.prompts[1])
        self.assertEqual(claude.sitzungen, [None, "s1"])

    def test_reihen_im_startprompt(self):
        claude = FalscherClaude(self.ordner, [(BLATT, "Entwurf"), (None, "Fertig.")])
        reihe = {"klasse": 10, "reihenfrage": "Was soll ich tun?", "behandelt": ["Kant"]}
        material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN, reihen=[reihe])
        start = claude.prompts[0]
        self.assertIn("## Lias laufende Reihen", start)
        self.assertIn("### Ethik, Klasse 10\n- Reihenfrage: Was soll ich tun?\n- Schon behandelt: Kant", start)
        self.assertLess(start.index("kategorischer Imperativ, Kl. 10"), start.index("## Lias laufende Reihen"))
        self.assertLess(start.index("## Lias laufende Reihen"), start.index("Skill einzelmaterial"))
        self.assertNotIn("laufende Reihen", claude.prompts[1])

    def test_katalog_im_startprompt(self):
        claude = FalscherClaude(self.ordner, [(BLATT, "Entwurf"), (None, "Fertig.")])
        material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN,
                            reihen=[{"klasse": 10, "reihenfrage": "Was soll ich tun?"}],
                            katalog="### Ethik 7: Lügen\n- data/wissen/text/AB_6_Kant.docx.txt | Arbeitsblatt | Kant\n")
        start = claude.prompts[0]
        self.assertIn("## Lias Material aus früheren Reihen", start)
        self.assertIn("- data/wissen/text/AB_6_Kant.docx.txt | Arbeitsblatt | Kant", start)
        self.assertLess(start.index("## Lias laufende Reihen"), start.index("## Lias Material aus früheren Reihen"))
        self.assertLess(start.index("## Lias Material aus früheren Reihen"), start.index("Skill einzelmaterial"))

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


class AnhaengeTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.eingang = self.hier / "data" / "eingang" / "a1"
        self.eingang.mkdir(parents=True)
        self.vorschau_aufrufe = []

    def vorschau(self, quelle, ordner, anzahl=2):
        self.vorschau_aufrufe.append(quelle.name)
        ordner.mkdir(parents=True, exist_ok=True)
        return [ordner / f"seite-{i:02d}.png" for i in range(1, anzahl + 1)]

    def datei(self, name, inhalt=b"x") -> str:
        (self.eingang / name).write_bytes(inhalt)
        return f"data/eingang/a1/{name}"

    def test_bild_und_unbekanntes(self):
        zeilen = material.anhaenge_vorbereiten(self.hier, [self.datei("foto.jpg"), self.datei("alt.odt")],
                                               self.vorschau)
        self.assertEqual(zeilen, ["- data/eingang/a1/foto.jpg: Bild, mit Read öffnen",
                                  "- data/eingang/a1/alt.odt: Format ohne Aufbereitung, versuche Read"])
        self.assertEqual(self.vorschau_aufrufe, [])

    def test_docx_mit_textfassung_und_hoechstens_8_bildern(self):
        import docx
        d = docx.Document()
        d.add_paragraph("Der Ring des Gyges")
        d.save(self.eingang / "text.docx")
        zeilen = material.anhaenge_vorbereiten(self.hier, ["data/eingang/a1/text.docx"],
                                               lambda q, o: self.vorschau(q, o, anzahl=10))
        txt = self.eingang / "text.docx.txt"
        self.assertIn("Ring des Gyges", txt.read_text(encoding="utf-8"))
        self.assertIn("  Textfassung: data/eingang/a1/text.docx.txt", zeilen)
        bilder = [z for z in zeilen if "Seitenbilder" in z][0]
        self.assertIn("nur die ersten 8 von 10", bilder)
        self.assertIn("data/eingang/a1/text.docx-seiten/seite-08.png", bilder)
        self.assertNotIn("seite-09", bilder)

    def test_scan_ohne_text(self):
        import io

        import pypdf
        w = pypdf.PdfWriter()
        w.add_blank_page(595, 842)
        puffer = io.BytesIO()
        w.write(puffer)
        rel = self.datei("scan.pdf", puffer.getvalue())
        zeilen = material.anhaenge_vorbereiten(self.hier, [rel], self.vorschau)
        self.assertTrue(any("vermutlich ein Scan" in z for z in zeilen))
        self.assertTrue(any("Seitenbilder: data/eingang/a1/scan.pdf-seiten/seite-01.png" in z for z in zeilen))
        self.assertFalse((self.eingang / "scan.pdf.txt").exists())

    def test_kaputte_pdf_und_vorschau_fehler(self):
        def kaputt(quelle, ordner):
            raise renderer.vorschau.VorschauFehler("PDF lässt sich nicht öffnen")
        zeilen = material.anhaenge_vorbereiten(self.hier, [self.datei("kaputt.pdf", b"kein pdf")], kaputt)
        self.assertTrue(any("Text nicht lesbar" in z for z in zeilen))
        self.assertTrue(any("Keine Seitenbilder (PDF lässt sich nicht öffnen)" in z for z in zeilen))

    def test_prompt(self):
        self.assertEqual(material.prompt_anhaenge([]), "")
        self.assertIn("Angehängte Dateien von Lia", material.prompt_anhaenge(["- a.jpg: Bild"]))

    def test_bearbeiten_mit_anhang(self):
        auftrag = {"id": "20261022-120000-unterricht-abcdef", "text": "Mach daraus ein Arbeitsblatt",
                   "dateien": [self.datei("foto.jpg")]}
        claude = FalscherClaude(self.hier / "data" / "arbeit" / auftrag["id"], [(BLATT, "a"), (None, "b")])
        material.bearbeiten(auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN, vorschau=self.vorschau)
        self.assertIn("- data/eingang/a1/foto.jpg: Bild, mit Read öffnen", claude.prompts[0])
        self.assertIn("Angehängte Dateien von Lia", claude.prompts[0])


if __name__ == "__main__":
    unittest.main()
