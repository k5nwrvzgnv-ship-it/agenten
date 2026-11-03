"""Exposé: Prüfung (Fehler mit Pfad für Claude) und Bauen als docx (Deckblatt, Text, Literatur)."""

import copy
import tempfile
import tomllib
import unittest
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image

from renderer import bauen, design, expose, pruefen
from renderer.pruefung import lesen

BEISPIELE = Path(__file__).resolve().parent.parent / "beispiele"

EX = {
    "art": "expose",
    "titel": "Fehlstellen an Lamellen",
    "untertitel": "Ein Prototyp",
    "autoren": ["Anna Muster (Matr.-Nr. 1)", "Ben Beispiel (Matr.-Nr. [OFFEN: Nummer])"],
    "betreuung": ["Prof. Dr. C. Doe"],
    "einrichtung": "Fachbereich Holz",
    "rahmen": "Exposé | Wintersemester 2026/27\nStudiengang Holz (M. Sc.)\nModul Projekt",
    "datum": "02.11.2026",
    "bloecke": [
        {"typ": "ueberschrift", "text": "Ausgangslage"},
        {"typ": "absatz", "text": "Äste mindern die Festigkeit (Muster & Beispiel, 2021). [OFFEN: Zahl] Prozent."},
        {"typ": "ueberschrift", "text": "Ziel", "ebene": 2},
        {"typ": "liste", "punkte": ["Bilder", "Modell"], "nummeriert": True},
        {"typ": "ueberschrift", "text": "Vorgehen"},
        {"typ": "liste", "punkte": ["eins", "zwei"]},
        {"typ": "tabelle", "titel": "Zeitplan", "kopf": ["Zeitraum", "Schritt"],
         "zeilen": [["November", "Aufnahme"], ["Dezember", ""]]},
        {"typ": "tabelle", "zeilen": [["a", "b"]]},
    ],
    "literatur": ["Muster, A., & Beispiel, B. (2021). Titel. Verlag. https://doi.org/10.1000/xyz",
                  "Doe, C. (2020). Ohne Link. Verlag."],
}


def mit(**aenderungen) -> dict:
    """Kopie von EX, z. B. mit(b1={...}) ersetzt bloecke[1], mit(datum=...) ein Feld oben."""
    e = copy.deepcopy(EX)
    for name, wert in aenderungen.items():
        if name[0] == "b" and name[1:].isdigit():
            e["bloecke"][int(name[1:])] = wert
        else:
            e[name] = wert
    return e


class TestPruefung(unittest.TestCase):
    def test_gueltig_mit_standardwerten(self):
        b = lesen({"art": "expose", "titel": "T", "autoren": ["A"], "einrichtung": "E", "datum": "01.02.2026",
                   "bloecke": [{"typ": "tabelle", "zeilen": [["x"]]}]})
        self.assertEqual(b, {"art": "expose", "titel": "T", "untertitel": "", "einrichtung": "E", "rahmen": "",
                             "datum": "01.02.2026", "autoren": ["A"], "betreuung": [],
                             "bloecke": [{"typ": "tabelle", "titel": "", "kopf": None, "zeilen": [["x"]]}],
                             "literatur": []})

    def test_voll_gueltig(self):
        self.assertEqual(pruefen(EX), [])
        b = lesen(EX)
        self.assertEqual(b["bloecke"][3], {"typ": "liste", "nummeriert": True, "punkte": ["Bilder", "Modell"]})
        self.assertEqual(b["bloecke"][2]["ebene"], 2)

    def test_pflichtfelder(self):
        self.assertEqual(pruefen({"art": "expose"}),
                         ["titel: fehlt", "autoren: fehlt", "einrichtung: fehlt", "datum: fehlt", "bloecke: fehlt"])

    def test_kopf_fehler(self):
        f = pruefen(mit(autoren=[], betreuung=["x" * 101], datum="2.11.2026", rahmen="", quellen=[]))
        self.assertIn("quellen: unbekanntes Feld, erlaubt sind: art, titel, autoren, "
                      "einrichtung, datum, bloecke, untertitel, betreuung, rahmen, literatur", f)
        self.assertIn("autoren: muss 1 bis 8 Einträge haben, hat 0", f)
        self.assertIn("betreuung[0]: zu lang (101 Zeichen, höchstens 100)", f)
        self.assertIn('datum: muss ein Datum wie "20.10.2026" sein (TT.MM.JJJJ), ist "2.11.2026"', f)
        self.assertIn("rahmen: darf nicht leer sein", f)
        self.assertEqual(pruefen(mit(betreuung=[], literatur=[])), [])

    def test_bloecke_anderer_arten_nicht_erlaubt(self):
        f = pruefen(mit(b1={"typ": "hinweis", "art": "organisatorisch", "text": "x"}))
        self.assertEqual(f, ['bloecke[1].typ: muss einer von "ueberschrift", "absatz", "liste", "tabelle" sein, '
                             'ist "hinweis"'])

    def test_ueberschriften(self):
        f = pruefen(mit(b0={"typ": "ueberschrift", "text": "1.1 Start", "ebene": 2}))
        self.assertIn("bloecke[0].text: ohne Nummer schreiben, die Nummer setzt der Renderer", f)
        self.assertIn("bloecke[0].ebene: Ebene 2 vor der ersten Überschrift der Ebene 1, erst eine Überschrift "
                      "mit ebene 1 setzen", f)
        self.assertIn("bloecke[2].ebene: muss eine ganze Zahl von 1 bis 2 sein, ist 3",
                      pruefen(mit(b2={"typ": "ueberschrift", "text": "x", "ebene": 3})))

    def test_keine_belege(self):
        f = pruefen(mit(b1={"typ": "absatz", "text": "So gesagt [Transkript S. 4].", "quellen": []}))
        self.assertIn("bloecke[1].quellen: unbekanntes Feld, erlaubt sind: typ, text", f)
        self.assertIn("bloecke[1].text: Beleg aus Transkript oder Folien im Text, der gehört nicht ins Exposé "
                      "(nur ins Protokoll)", f)
        self.assertEqual(pruefen(mit(b3={"typ": "liste", "punkte": [{"text": "a"}]})),
                         ['bloecke[3].punkte[0]: muss ein Text sein, ist {"text": "a"}'])

    def test_tabelle(self):
        f = pruefen(mit(b6={"typ": "tabelle", "kopf": ["a", "b"], "zeilen": [["1"]], "erste_spalte_fett": True}))
        self.assertIn("bloecke[6].erste_spalte_fett: unbekanntes Feld, erlaubt sind: typ, zeilen, titel, kopf", f)
        self.assertIn("bloecke[6].zeilen[0]: hat 1 Zellen, erwartet 2 (wie kopf)", f)
        f = pruefen(mit(b6={"typ": "tabelle", "zeilen": [list("abcdefghi")]}))
        self.assertEqual(f, ["bloecke[6].zeilen[0]: muss 1 bis 8 Einträge haben, hat 9"])

    def test_literatur(self):
        f = pruefen(mit(literatur=["", "x" * 1001] + ["y"] * 49))
        self.assertEqual(f, ["literatur: muss 0 bis 50 Einträge haben, hat 51"])
        f = pruefen(mit(literatur=["", "x" * 1001]))
        self.assertEqual(f, ["literatur[0]: darf nicht leer sein", "literatur[1]: zu lang (1001 Zeichen, höchstens 1000)"])


class TestBauen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.logo = self.tmp / "logo.png"
        Image.new("RGB", (60, 20), "green").save(self.logo)
        self.profil = {"schrift": "Arial", "zeilenabstand": 1.0, "logo": str(self.logo)}

    def bauen(self, beschreibung=EX, profil=None, vorlage=None):
        return bauen(beschreibung, self.tmp / "e.docx", profil or self.profil, vorlage=vorlage, vorschau=False)

    def test_kontrolltext(self):
        self.assertEqual(self.bauen().kontrolltext.split("\n"), [
            "Fachbereich Holz",
            "Anna Muster (Matr.-Nr. 1) | Ben Beispiel (Matr.-Nr. [OFFEN: Nummer])",
            "Fehlstellen an Lamellen",
            "Ein Prototyp",
            "Exposé | Wintersemester 2026/27",
            "Studiengang Holz (M. Sc.)",
            "Modul Projekt",
            "Betreuung: Prof. Dr. C. Doe",
            "02.11.2026",
            "--- neue Seite",
            "# 1\tAusgangslage",
            "Äste mindern die Festigkeit (Muster & Beispiel, 2021). [OFFEN: Zahl] Prozent.",
            "## 1.1\tZiel",
            "1. Bilder",
            "2. Modell",
            "# 2\tVorgehen",
            "• eins",
            "• zwei",
            "Tabelle 1: Zeitplan",
            "| Zeitraum | Schritt |",
            "| November | Aufnahme |",
            "| Dezember | … |",
            "| a | b |",
            "--- neue Seite",
            "# Literaturverzeichnis",
            "Muster, A., & Beispiel, B. (2021). Titel. Verlag. https://doi.org/10.1000/xyz",
            "Doe, C. (2020). Ohne Link. Verlag.",
            "[2 offene Stellen, gelb markiert]",
            "[OFFEN: Nummer]",
            "[OFFEN: Zahl]",
        ])

    def test_offen_fett_und_gelb(self):
        d = docx.Document(self.bauen().pfad)
        absatz = next(p for p in d.paragraphs if p.text.startswith("Äste"))
        runs = [(r.text, r.bold, r.font.highlight_color) for r in absatz.runs]
        self.assertEqual(runs, [("Äste mindern die Festigkeit (Muster & Beispiel, 2021). ", None, None),
                                ("[OFFEN: Zahl]", True, WD_COLOR_INDEX.YELLOW), (" Prozent.", None, None)])

    def test_seite_schrift_und_silbentrennung(self):
        d = docx.Document(self.bauen().pfad)
        s = d.sections[-1]
        self.assertEqual([round(x.cm, 2) for x in (s.top_margin, s.bottom_margin, s.left_margin, s.right_margin)],
                         [3.0, 2.4, 2.5, 2.5])
        self.assertEqual((len(d.sections), str(s.footer.paragraphs[0].text)), (2, ""))
        normal = d.styles["Normal"]
        self.assertEqual((normal.font.name, normal.font.size.pt), ("Arial", 11))
        self.assertEqual(normal.paragraph_format.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertIsNotNone(d.settings.element.find(qn("w:autoHyphenation")))
        h1 = d.styles["Heading 1"]
        self.assertEqual((h1.font.size.pt, h1.font.bold), (11, True))

    def test_deckblatt(self):
        d = docx.Document(self.bauen().pfad)
        bild = d.paragraphs[0]._p.find(".//" + qn("wp:inline"))
        self.assertEqual(round(int(bild.find(qn("wp:extent")).get("cx")) / 360000, 2), 7.0)
        self.assertEqual(bild.get("distL"), "0")
        titel = next(p for p in d.paragraphs if p.text == "Fehlstellen an Lamellen")
        self.assertEqual(titel.runs[0].font.size.pt, 22)
        rahmen = [p for p in d.paragraphs if p._p.pPr is not None and p._p.pPr.find(qn("w:framePr")) is not None]
        self.assertEqual([p.text for p in rahmen][0], "Exposé | Wintersemester 2026/27")
        self.assertEqual(len(rahmen), 5)
        self.assertTrue(rahmen[0].runs[0].bold)
        self.assertEqual(rahmen[0].runs[0].font.size.pt, 9)

    def test_ohne_logo_rahmen_und_betreuung(self):
        e = {"art": "expose", "titel": "T", "autoren": ["A"], "einrichtung": "E", "datum": "01.02.2026",
             "bloecke": [{"typ": "absatz", "text": "x\ny"}]}
        text = self.bauen(e, profil={"rand_links_cm": 2}).kontrolltext
        self.assertEqual(text.split("\n"), ["E", "A", "T", "01.02.2026", "--- neue Seite", "x", "y"])
        d = docx.Document(self.tmp / "e.docx")
        self.assertEqual(d.paragraphs[0]._p.find(".//" + qn("wp:inline")), None)
        self.assertEqual(round(d.sections[0].left_margin.cm, 2), 2.0)
        self.assertFalse(any(r.bold for p in d.paragraphs for r in p.runs))

    def test_logo_fehlt(self):
        with self.assertRaisesRegex(ValueError, "Logo .* gibt es nicht"):
            self.bauen(profil={"logo": str(self.tmp / "fehlt.png")})

    def test_tabelle_mit_drei_linien(self):
        d = docx.Document(self.bauen().pfad)
        t = d.tables[0]
        linien = {el.tag.split("}")[1]: el.get(qn("w:val"))
                  for el in t._tbl.tblPr.find(qn("w:tblBorders"))}
        self.assertEqual(linien, {"top": "single", "left": "nil", "bottom": "single", "right": "nil",
                                  "insideH": "nil", "insideV": "nil"})
        kopf = t.rows[0].cells[0]
        self.assertEqual(kopf._tc.tcPr.find(qn("w:tcBorders")).find(qn("w:bottom")).get(qn("w:sz")), "6")
        self.assertTrue(kopf.paragraphs[0].runs[0].bold)
        self.assertEqual(kopf.paragraphs[0].runs[0].font.size.pt, 10)
        self.assertAlmostEqual(sum(c.width.cm for c in t.rows[0].cells), 16.0, places=1)
        self.assertIsNone(d.tables[1].rows[0].cells[0].paragraphs[0].runs[0].bold)

    def test_literatur_mit_link_und_einzug(self):
        d = docx.Document(self.bauen().pfad)
        titel = next(p for p in d.paragraphs if p.text == "Literaturverzeichnis")
        self.assertTrue(titel.paragraph_format.page_break_before)
        angabe = next(p for p in d.paragraphs if p.text.startswith("Muster"))
        self.assertEqual(angabe.paragraph_format.first_line_indent, Cm(-1.27))
        self.assertEqual([h.address for h in angabe.hyperlinks], ["https://doi.org/10.1000/xyz"])
        self.assertEqual(angabe.text, EX["literatur"][0])

    def test_ohne_literatur_kein_verzeichnis(self):
        self.assertNotIn("Literaturverzeichnis", self.bauen(mit(literatur=[])).kontrolltext)

    def test_link_ohne_satzzeichen(self):
        self.assertEqual(expose.LINK.findall("Siehe https://a.de/x. Und (https://b.org/y), https://c.org/z/"),
                         ["https://a.de/x", "https://b.org/y", "https://c.org/z/"])

    def test_offene_stellen(self):
        self.assertEqual(expose.offene_stellen(lesen(EX)), ["[OFFEN: Nummer]", "[OFFEN: Zahl]"])

    def test_vorlage_gibt_seite_vor(self):
        v = docx.Document()
        v.sections[0].left_margin = Cm(3.5)
        v.save(self.tmp / "vorlage.docx")
        d = docx.Document(self.bauen(vorlage=self.tmp / "vorlage.docx").pfad)
        self.assertEqual(round(d.sections[-1].left_margin.cm, 2), 3.5)


class TestProfil(unittest.TestCase):
    def test_neue_felder(self):
        p = design.profil_lesen({"logo": "/x/logo.png", "logo_breite_cm": 5, "rand_oben_cm": 2})
        self.assertEqual((p["logo"], p["logo_breite_cm"], p["rand_oben_cm"], p["rand_unten_cm"]),
                         ("/x/logo.png", 5, 2, 2.4))
        with self.assertRaisesRegex(design.ProfilUngueltig, "logo: muss ein Pfad"):
            design.profil_lesen({"logo": 3})
        with self.assertRaisesRegex(design.ProfilUngueltig, "rand_links_cm: muss eine Zahl von 1 bis 5"):
            design.profil_lesen({"rand_links_cm": 0})

    def test_beispiel_profil(self):
        with open(BEISPIELE / "profil-jan-expose.toml", "rb") as f:
            p = design.profil_lesen(tomllib.load(f))
        self.assertEqual((p["schrift"], p["schriftgroesse_pt"], p["zeilenabstand"]), ("Arial", 11, 1.0))
        self.assertEqual(p["logo"], "")  # trägt der Agent ein


if __name__ == "__main__":
    unittest.main()
