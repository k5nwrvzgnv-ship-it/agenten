import json
import tempfile
import unittest
from pathlib import Path

import expose

GUELTIG = {
    "art": "expose", "titel": "Fehlstellen: Holzlamellen", "autoren": ["Jan Kleinke", "Felix Frankowiak"],
    "betreuung": ["Prof. Dr. Thomas Böhme"], "einrichtung": "HNEE", "rahmen": "Forschungsprojekt 2",
    "datum": "02.11.2026",
    "bloecke": [
        {"typ": "ueberschrift", "text": "Problemstellung"},
        {"typ": "absatz", "text": "Fehlstellen | Äste"},
        {"typ": "absatz", "text": " ".join(["Wort"] * 700)},  # Umfang: mindestens 650 Wörter
        {"typ": "ueberschrift", "text": "Daten", "ebene": 2},
        {"typ": "liste", "punkte": ["Kamera", "Licht"], "nummeriert": True},
        {"typ": "ueberschrift", "text": "Zeitplan"},
        {"typ": "tabelle", "titel": "Plan", "kopf": ["Wann", "Was"], "zeilen": [["Nov.", "Aufnahmen"]]},
    ],
    "literatur": ["Muster, A. (2020): Titel. Verlag."],
}


class TestAusloeser(unittest.TestCase):
    def test_nur_mit_praefix(self):
        for text in ("Exposé: Lamellen", "  expose:Lamellen", "EXPOSÉ : x"):
            self.assertTrue(expose.ist_exposeauftrag(text), text)
        for text in ("Mach ein Exposé: Lamellen", "Exposee Lamellen", "Dokument: Exposé"):
            self.assertFalse(expose.ist_exposeauftrag(text), text)


class TestPruefen(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(expose.pruefen(json.dumps(GUELTIG)), [])

    def test_alle_fehler_auf_einmal(self):
        d = {**GUELTIG, "art": "zusammenfassung", "datum": "2.11.26", "autoren": [], "quellen": [],
             "bloecke": [{"typ": "ueberschrift", "text": "1. Einleitung", "ebene": 2},
                         {"typ": "absatz", "text": "x", "quellen": []},
                         {"typ": "tabelle", "kopf": ["a", "b"], "zeilen": [["1"]]},
                         {"typ": "bild"}]}
        fehler = "\n".join(expose.pruefen(json.dumps(d)))
        for teil in ("quellen: unbekanntes Feld", "art:", "datum:", "autoren:",
                     "bloecke[0].ebene: vor der ersten Ebene 2", "bloecke[0].text: ohne Nummer",
                     "bloecke[1].quellen: unbekanntes Feld", "bloecke[2].zeilen[0]: 1 Zellen, erwartet 2",
                     "bloecke[3].typ"):
            self.assertIn(teil, fehler)

    def test_umfang_zwei_bis_vier_seiten(self):
        lang = {**GUELTIG, "bloecke": GUELTIG["bloecke"] + [{"typ": "absatz", "text": " ".join(["x"] * 800)}]}
        self.assertIn("sind 1513: kürzen", expose.pruefen(json.dumps(lang))[0])
        kurz = {**GUELTIG, "bloecke": [b for b in GUELTIG["bloecke"] if len(b.get("text", "")) < 100]}
        self.assertIn("sind 13: ausführen", expose.pruefen(json.dumps(kurz))[0])
        viel = {**GUELTIG, "literatur": ["A (2020): T."] * 13,
                "bloecke": GUELTIG["bloecke"] + [{"typ": "ueberschrift", "text": "U", "ebene": 2}] * 6}
        fehler = "\n".join(expose.pruefen(json.dumps(viel)))
        self.assertIn("literatur: höchstens 12 Angaben, sind 13", fehler)
        self.assertIn("höchstens 6 Überschriften der Ebene 2, sind 7", fehler)

    def test_rahmen_mehrzeilig_bis_400_zeichen(self):
        d = {**GUELTIG, "rahmen": "Exposé | Wintersemester 2026/27\nStudiengang Holzingenieurwesen (M. Sc.)\n" + "x" * 300}
        self.assertEqual(expose.pruefen(json.dumps(d)), [])
        self.assertIn("rahmen: höchstens 400 Zeichen", expose.pruefen(json.dumps({**d, "rahmen": "x" * 401}))[0])

    def test_kein_json(self):
        self.assertTrue(expose.pruefen("{kaputt")[0].startswith("kein gültiges JSON"))
        self.assertEqual(expose.pruefen("[]"), ["die Beschreibung muss ein JSON-Objekt sein"])


PROFIL = {"schrift": "Arial"}


def pdf(docx, ziel):  # Attrappe für LibreOffice
    (ziel / f"{docx.stem}.pdf").write_text("pdf")
    return ziel / f"{docx.stem}.pdf"


class TestBauen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        self.aufrufe = []

    def renderer(self, fehler=None):
        def bauen(text, ziel, profil, vorschau):
            self.aufrufe.append((json.loads(text), ziel, profil, vorschau))
            if fehler:
                raise fehler
            ziel.write_text("docx")
        return bauen

    def bauen(self, weitere=None, fehler=None, als_pdf=pdf):
        return expose.bauen(self.ordner, PROFIL, weitere=weitere, bauen=self.renderer(fehler), als_pdf=als_pdf)

    def test_ohne_datei_nichts(self):
        self.assertEqual(self.bauen(), expose.Bericht())

    def test_docx_und_pdf_einmal_und_titelwechsel(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))
        (self.ordner / "fassung").mkdir()
        (self.ordner / "fassung" / "Alt.md").write_text("Fassung vor dem Renderer")
        fassung = self.ordner / "fassung"
        self.assertEqual(self.bauen().dateien, [fassung / "Fehlstellen - Holzlamellen.docx",
                                                fassung / "Fehlstellen - Holzlamellen.pdf"])
        self.assertEqual(self.aufrufe, [(GUELTIG, fassung / "Fehlstellen - Holzlamellen.docx", PROFIL, False)])
        self.assertEqual(self.bauen().dateien, [])  # unverändert: nicht noch einmal
        (self.ordner / "expose.json").write_text(json.dumps({**GUELTIG, "titel": "Neu"}))
        self.assertEqual(len(self.bauen().dateien), 2)
        self.assertEqual(sorted(p.name for p in fassung.iterdir()), ["Neu.docx", "Neu.pdf"])

    def test_ungueltig_nicht_gebaut(self):
        (self.ordner / "expose.json").write_text(json.dumps({**GUELTIG, "datum": "x"}))
        b = self.bauen()
        self.assertEqual((b.dateien, self.aufrufe), ([], []))
        self.assertIn("- datum:", b.ungueltig)
        self.assertFalse((self.ordner / "fassung").exists())

    def test_weitere_pruefung_nur_bei_gueltiger_beschreibung(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))
        b = self.bauen(weitere=lambda d: [f"literatur[0]: {d['literatur'][0]} nicht geprüft"])
        self.assertEqual((b.dateien, b.ungueltig), ([], "- literatur[0]: Muster, A. (2020): Titel. Verlag. nicht geprüft"))
        self.assertEqual(len(self.bauen(weitere=lambda d: []).dateien), 2)

    def test_renderer_lehnt_ab_geht_an_claude(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))
        b = self.bauen(fehler=expose.renderer.BeschreibungUngueltig(["bloecke[1].text: Beleg im Text"]))
        self.assertEqual((b.dateien, b.ungueltig, b.fehler), ([], "- bloecke[1].text: Beleg im Text", []))

    def test_profilfehler_geht_an_jan_und_wird_wiederholt(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))
        b = self.bauen(fehler=ValueError("Logo x.png gibt es nicht (Profil, Feld logo)"))
        self.assertEqual((b.dateien, b.ungueltig), ([], ""))
        self.assertEqual(b.fehler, ["Fehlstellen - Holzlamellen.docx nicht gebaut: Logo x.png gibt es nicht "
                                    "(Profil, Feld logo)"])
        self.assertEqual(len(self.bauen().dateien), 2)  # Stand nicht gesetzt: nächster Lauf baut

    def test_ohne_pdf_geht_die_docx_trotzdem(self):
        (self.ordner / "expose.json").write_text(json.dumps(GUELTIG))

        def kaputt(docx, ziel):
            raise expose.vorschau.VorschauFehler("LibreOffice (soffice) ist nicht installiert")
        b = self.bauen(als_pdf=kaputt)
        self.assertEqual(b.dateien, [self.ordner / "fassung" / "Fehlstellen - Holzlamellen.docx"])
        self.assertIn("PDF nicht gebaut, die docx hängt an: LibreOffice", b.fehler[0])


class TestEchterRenderer(unittest.TestCase):
    """Beschreibung, die expose.pruefen annimmt, nimmt auch der Renderer an; das Profil im Repo ist gültig."""

    def test_baut_docx_mit_profil_aus_dem_repo(self):
        import tomllib
        profil = tomllib.loads((Path(expose.__file__).parent / "profil-expose.toml").read_text())
        self.assertEqual(profil["logo"], "data/vorlagen/hnee_logo.png")
        profil["logo"] = ""  # die PNG liegt nicht im Repo
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "expose.json").write_text(json.dumps(GUELTIG))
            b = expose.bauen(ordner, profil, als_pdf=pdf)
            self.assertEqual((b.ungueltig, b.fehler), ("", []))
            self.assertTrue(b.dateien[0].read_bytes().startswith(b"PK"))  # docx ist ein Zip


if __name__ == "__main__":
    unittest.main()
