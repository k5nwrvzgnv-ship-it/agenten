"""protokoll.py: Prüfung von protokoll.json gegen das Transkript, Umbau in einen Bericht, Bau (ohne LibreOffice)."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

import renderer

import protokoll

TRANSKRIPT = """Felix Neumann   0:01
Also, ich würde sagen, wir nehmen die Zeilenkamera und nicht die Flächenkamera.
Henri Bauer   0:45
Ja, einverstanden. Ich frage bei Schneider nach, ob wir im Dezember ins Werk dürfen.
Jan Kleinke   1:30
Ob wir die Lamellen sortiert oder unsortiert bekommen, wissen wir noch nicht.
Felix Neumann   2:10
Dann treffen wir uns nächsten Donnerstag um 10 Uhr wieder."""

PROTOKOLL = {
    "titel": "Kamera und Werksbesuch",
    "datum": "18.11.2026",
    "teilnehmende": ["Felix Neumann", "Henri Bauer", "Jan Kleinke"],
    "kurzfassung": "Die Gruppe hat sich für die Zeilenkamera entschieden. Henri klärt den Werksbesuch.",
    "themen": [{"titel": "Kamera", "text": "Zeilen- gegen Flächenkamera."}],
    "beschluesse": [{"text": "Zeilenkamera statt Flächenkamera", "von": "Felix",
                     "beleg": "wir nehmen die Zeilenkamera und nicht die Flächenkamera"}],
    "aufgaben": [{"was": "Werksbesuch im Dezember bei Schneider anfragen", "wer": "Henri", "bis": "",
                  "beleg": "Ich frage bei Schneider nach"}],
    "offen": [{"text": "Lamellen sortiert oder unsortiert?", "beleg": "sortiert oder unsortiert bekommen"}],
    "naechster_termin": "Donnerstag, 10 Uhr",
    "naechste_besprechung": {
        "ziel": "Termin im Werk steht fest.",
        "vorab_klaeren": ["Antwort von Schneider da?"],
        "tagesordnung": [{"punkt": "Werksbesuch", "ziel": "entscheiden", "vorbereitung": "Henri: Antwort von Schneider",
                          "minuten": 15, "bezug": ["A1"]},
                         {"punkt": "Lamellen", "ziel": "klaeren", "vorbereitung": "", "minuten": 10, "bezug": ["o1"]},
                         {"punkt": "Arbeitsteilung, kam zu kurz", "ziel": "entscheiden", "minuten": 10,
                          "bezug": ["neu"]}],
        "hinweise": ["Aufgaben wurden nicht ausdrücklich verteilt: am Ende kurz zusammenfassen, wer was macht."]},
}


def fehler(d: dict, transkript: str = TRANSKRIPT) -> list[str]:
    return protokoll.pruefen(json.dumps(d), transkript)


class Pruefen(unittest.TestCase):
    def test_gueltig(self):
        self.assertEqual(fehler(PROTOKOLL), [])

    def test_kein_json_und_unbekannte_felder(self):
        self.assertIn("kein gültiges JSON", protokoll.pruefen("{", TRANSKRIPT)[0])
        d = {**PROTOKOLL, "zeitmarken": []}
        self.assertIn("zeitmarken: unbekanntes Feld", fehler(d))

    def test_beleg_muss_woertlich_im_transkript_stehen(self):
        d = copy.deepcopy(PROTOKOLL)
        d["beschluesse"][0]["beleg"] = "WIR NEHMEN die Zeilenkamera, und nicht"  # Schreibung und Satzzeichen egal
        self.assertEqual(fehler(d), [])
        d["beschluesse"][0]["beleg"] = "wir nehmen die Flächenkamera"
        self.assertTrue(any("steht so nicht im Transkript" in f for f in fehler(d)))
        d["beschluesse"][0]["beleg"] = "Zeilenkamera"
        self.assertTrue(any("3 bis 40 Wörter" in f for f in fehler(d)))

    def test_namen_aus_teilnehmenden(self):
        d = copy.deepcopy(PROTOKOLL)
        d["aufgaben"][0]["wer"] = "offen"
        d["beschluesse"][0]["von"] = "alle"
        self.assertEqual(fehler(d), [])
        d["aufgaben"][0]["wer"] = "Prof. Böhme"
        self.assertTrue(any("aufgaben[0].wer" in f for f in fehler(d)))
        d = copy.deepcopy(PROTOKOLL)
        d["teilnehmende"].append("Maria")
        self.assertTrue(any("'Maria' kommt im Transkript nicht vor" in f for f in fehler(d)))

    def test_tagesordnung_nur_mit_bezug(self):
        d = copy.deepcopy(PROTOKOLL)
        d["naechste_besprechung"]["tagesordnung"][0]["bezug"] = ["A7"]
        self.assertTrue(any("'A7' gibt es nicht" in f for f in fehler(d)))
        d["naechste_besprechung"]["tagesordnung"][0]["bezug"] = []
        self.assertTrue(any("bezug: Liste" in f for f in fehler(d)))
        d["naechste_besprechung"]["tagesordnung"] = []
        self.assertTrue(any("tagesordnung: muss eine Liste sein (nicht leer)" in f for f in fehler(d)))

    def test_ziel_minuten_und_grenzen(self):
        d = copy.deepcopy(PROTOKOLL)
        p = d["naechste_besprechung"]["tagesordnung"][0]
        p["ziel"], p["minuten"] = "diskutieren", True
        f = fehler(d)
        self.assertTrue(any(".ziel: muss einer von" in x for x in f))
        self.assertTrue(any(".minuten: ganze Zahl" in x for x in f))
        d = copy.deepcopy(PROTOKOLL)
        for p in d["naechste_besprechung"]["tagesordnung"]:
            p["minuten"] = 100
        self.assertTrue(any("höchstens 240 Minuten" in x for x in fehler(d)))
        d = copy.deepcopy(PROTOKOLL)
        d["naechste_besprechung"]["hinweise"] *= 4
        self.assertTrue(any("hinweise: höchstens 3" in x for x in fehler(d)))

    def test_leere_listen_erlaubt_pflichtfelder_nicht(self):
        d = {**copy.deepcopy(PROTOKOLL), "themen": [], "beschluesse": [], "aufgaben": [], "offen": []}
        d["naechste_besprechung"]["tagesordnung"] = [{"punkt": "Start", "ziel": "klaeren", "minuten": 5,
                                                      "bezug": ["neu"]}]
        self.assertEqual(fehler(d), [])
        d = {k: v for k, v in PROTOKOLL.items() if k not in ("kurzfassung", "datum")}
        f = fehler(d)
        self.assertTrue(any(x.startswith("kurzfassung:") for x in f))
        self.assertTrue(any(x.startswith("datum:") for x in f))


class Umbau(unittest.TestCase):
    def test_bericht_ohne_belege_und_gueltig_fuer_den_renderer(self):
        b = protokoll.als_bericht(PROTOKOLL)
        self.assertEqual((b["art"], b["rubrik"], b["datum"]), ("bericht", "Besprechungsprotokoll", "18.11.2026"))
        text = json.dumps(b, ensure_ascii=False)
        self.assertNotIn("beleg", text)
        self.assertNotIn("wir nehmen die Zeilenkamera und nicht", text)
        tabellen = {t.get("titel") or t["kopf"][1]: t for t in b["bloecke"] if t["typ"] == "tabelle"}
        self.assertEqual(tabellen["Aufgabe"]["zeilen"][0], ["A1", PROTOKOLL["aufgaben"][0]["was"], "Henri", "offen"])
        ordnung = tabellen["Tagesordnung"]["zeilen"]
        self.assertEqual((ordnung[1][2], ordnung[1][5], ordnung[2][5]), ("klären", "O1", "neu"))
        self.assertEqual(ordnung[-1][4], "35 min")
        with tempfile.TemporaryDirectory() as tmp:
            renderer.bauen(b, Path(tmp) / "p.docx", vorschau=False)  # wirft BeschreibungUngueltig, wenn nicht

    def test_daten(self):
        d = protokoll.daten(PROTOKOLL)
        self.assertEqual(d["titel"], "Protokoll 18.11.2026: Kamera und Werksbesuch")
        self.assertEqual(d["punkte"], ["B1: Zeilenkamera statt Flächenkamera"])
        self.assertIn("0 Aufgaben ohne Zuständige, 1 ohne Frist", d["pruefen"])
        self.assertIn("kein gültiges", protokoll.daten(None)["kern"])

    def test_dateiname(self):
        self.assertEqual(protokoll.dateiname({**PROTOKOLL, "titel": "Kamera: Auswahl"}),
                         "2026-11-18 Protokoll Kamera - Auswahl")


class Bauen(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ordner = Path(self._tmp.name)
        self.pdfs = []

    def als_pdf(self, docx: Path, ziel: Path) -> Path:
        pdf = ziel / (docx.stem + ".pdf")
        pdf.write_bytes(b"%PDF")
        self.pdfs.append(pdf)
        return pdf

    def test_baut_einmal_je_fassung(self):
        (self.ordner / protokoll.DATEI).write_text(json.dumps(PROTOKOLL))
        b = protokoll.bauen(self.ordner, TRANSKRIPT, {}, als_pdf=self.als_pdf)
        self.assertEqual(([p.name for p in b.dateien], b.ungueltig, b.fehler),
                         (["2026-11-18 Protokoll Kamera und Werksbesuch.docx",
                           "2026-11-18 Protokoll Kamera und Werksbesuch.pdf"], "", []))
        self.assertEqual(protokoll.bauen(self.ordner, TRANSKRIPT, {}, als_pdf=self.als_pdf).dateien, [])

    def test_ungueltig_geht_an_claude(self):
        d = copy.deepcopy(PROTOKOLL)
        d["offen"][0]["beleg"] = "das hat niemand gesagt"
        (self.ordner / protokoll.DATEI).write_text(json.dumps(d))
        b = protokoll.bauen(self.ordner, TRANSKRIPT, {}, als_pdf=self.als_pdf)
        self.assertIn("offen[0].beleg", b.ungueltig)
        self.assertEqual(b.dateien, [])

    def test_pdf_fehler_docx_trotzdem_stand_offen(self):
        (self.ordner / protokoll.DATEI).write_text(json.dumps(PROTOKOLL))

        def kaputt(docx, ziel):
            raise OSError("LibreOffice fehlt")
        b = protokoll.bauen(self.ordner, TRANSKRIPT, {}, als_pdf=kaputt)
        self.assertEqual(len(b.dateien), 1)
        self.assertIn("LibreOffice fehlt", b.fehler[0])
        self.assertFalse((self.ordner / protokoll.STAND).exists())

    def test_transkript_dateien(self):
        vtt = self.ordner / "a.vtt"
        vtt.write_text("WEBVTT")
        docx = self.ordner / "b.docx"
        docx.write_bytes(b"")
        (self.ordner / "b.docx.txt").write_text("Text")
        ohne = self.ordner / "c.pdf"
        ohne.write_bytes(b"")
        self.assertEqual(protokoll.transkript_dateien([vtt, docx, ohne]), [vtt, self.ordner / "b.docx.txt"])
        self.assertEqual(protokoll.transkript_lesen([vtt, docx]), "WEBVTT\n\nText")


if __name__ == "__main__":
    unittest.main()
