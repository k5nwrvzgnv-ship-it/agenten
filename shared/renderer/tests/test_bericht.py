"""Bericht: Prüfung (Belege als Quellen-ID, Annahme, Quellenverzeichnis, Zellbelege) und Bauen als docx."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from renderer import bauen, pruefen, zusammenfassung
from renderer.pruefung import lesen

Q1, Q2 = "Q-20261109-genesis-3fa2c1", "Q-20261109-ted-9b1c22"
BERICHT = {
    "art": "bericht",
    "rubrik": "Wirtschaftlichkeit",
    "titel": "Robotik",
    "bloecke": [
        {"typ": "ueberschrift", "text": "Markt"},
        {"typ": "absatz", "text": "Umsatz 7,9 Mrd. EUR.", "quellen": [{"art": "quelle", "stelle": Q1}]},
        {"typ": "absatz", "text": "Marge etwa 4 %.", "kennzeichnung": "annahme"},
        {"typ": "tabelle", "kopf": ["Größe", "Wert"], "zeilen": [
            ["Betriebe", {"text": "1.850", "quellen": [{"art": "quelle", "stelle": Q1}]}],
            ["Anteil", {"text": "30 %", "kennzeichnung": "annahme"}],
            ["Ort", "Brandenburg"]]},
        {"typ": "hinweis", "art": "wichtig", "titel": "Hypothese 1", "text": "Abbruch bei < 3 Zusagen."},
        {"typ": "hinweis", "art": "einschraenkung", "text": "Daten aufgeteilt.", "kennzeichnung": "unsicher"},
    ],
    "offene_fragen": ["Wer kauft?"],
    "quellenverzeichnis": [{"id": Q1, "text": "GENESIS, https://genesis.destatis.de/x"},
                           {"id": Q2, "text": "TED"}],
}
PROFIL = {"erstellt_von": "finance", "farben": {"pruefungsrelevant": "DDEEDD"}}


def mit(**aenderungen) -> dict:
    """Kopie von BERICHT, mit(b1={...}) ersetzt bloecke[1], mit(titel=...) ein Feld oben."""
    z = copy.deepcopy(BERICHT)
    for name, wert in aenderungen.items():
        if name[0] == "b" and name[1:].isdigit():
            z["bloecke"][int(name[1:])] = wert
        else:
            z[name] = wert
    return z


class TestPruefung(unittest.TestCase):
    def test_gueltig_mit_standardwerten(self):
        b = lesen({"art": "bericht", "titel": "T", "bloecke": [{"typ": "absatz", "text": "x"}]})
        self.assertEqual(b, {"art": "bericht", "titel": "T", "untertitel": "", "rubrik": "", "datum": "",
                             "offene_fragen": [], "quellenverzeichnis": [], "bloecke": [
                                 {"typ": "absatz", "text": "x", "quellen": [], "kennzeichnung": None}]})
        self.assertEqual(pruefen(BERICHT), [])

    def test_zellbelege_gelesen(self):
        t = lesen(BERICHT)["bloecke"][3]
        self.assertEqual(t["zeilen"], [["Betriebe", "1.850"], ["Anteil", "30 %"], ["Ort", "Brandenburg"]])
        self.assertEqual(t["belege"], [[None, {"quellen": [{"art": "quelle", "stelle": Q1}], "kennzeichnung": None}],
                                       [None, {"quellen": [], "kennzeichnung": "annahme"}], [None, None]])

    def test_kein_vorlesungskopf(self):
        self.assertEqual(pruefen(mit(kurs="K")), ["kurs: unbekanntes Feld, erlaubt sind: art, titel, bloecke, "
                                                  "untertitel, rubrik, datum, offene_fragen, quellenverzeichnis"])
        self.assertEqual(pruefen(mit(selbsttest=[])), [
            "selbsttest: unbekanntes Feld, erlaubt sind: art, titel, bloecke, untertitel, rubrik, datum, "
            "offene_fragen, quellenverzeichnis"])

    def test_belege_des_berichts(self):
        f = pruefen(mit(b1={"typ": "absatz", "text": "x", "quellen": [{"art": "transkript", "stelle": "4"}],
                            "kennzeichnung": "muendlich"}))
        self.assertEqual(f, ['bloecke[1].kennzeichnung: muss "annahme" oder "unsicher" sein, ist "muendlich"',
                             'bloecke[1].quellen[0].art: muss einer von "quelle", "norm" sein, ist "transkript"'])
        f = pruefen(mit(b1={"typ": "absatz", "text": "x", "quellen": [{"art": "quelle", "stelle": "Q 1"}]}))
        self.assertEqual(len(f), 1)
        self.assertTrue(f[0].startswith('bloecke[1].quellen[0].stelle: nur eine Quellen-ID wie'), f)

    def test_zusammenfassung_behaelt_ihre_regeln(self):
        z = {"art": "zusammenfassung", "titel": "T", "kurs": "K", "datum": "01.02.2026",
             "bloecke": [{"typ": "absatz", "text": "x", "kennzeichnung": "annahme",
                          "quellen": [{"art": "quelle", "stelle": Q1}]}]}
        self.assertEqual(pruefen(z), [
            'bloecke[0].kennzeichnung: muss "unsicher" oder "muendlich" sein, ist "annahme"',
            'bloecke[0].quellen[0].art: muss einer von "transkript", "folie", "norm" sein, ist "quelle"'])
        z["bloecke"] = [{"typ": "tabelle", "zeilen": [[{"text": "1"}]]}]
        self.assertEqual(pruefen(z), ['bloecke[0].zeilen[0][0]: muss ein Text sein, ist {"text": "1"}'])

    def test_hinweisarten(self):
        f = pruefen(mit(b4={"typ": "hinweis", "art": "pruefungsrelevant", "text": "x"}))
        self.assertEqual(f, ['bloecke[4].art: muss "wichtig" oder "einschraenkung" sein, ist "pruefungsrelevant"'])

    def test_quellenverzeichnis(self):
        f = pruefen(mit(quellenverzeichnis=[{"id": Q2, "text": "TED"}]))
        self.assertEqual(f, [f'bloecke[1].quellen[0].stelle: "{Q1}" fehlt im quellenverzeichnis, dort ergänzen '
                             'oder die ID korrigieren',
                             f'bloecke[3].zeilen[0][1].quellen[0].stelle: "{Q1}" fehlt im quellenverzeichnis, '
                             'dort ergänzen oder die ID korrigieren'])
        f = pruefen(mit(quellenverzeichnis=[{"id": Q1, "text": "a"}, {"id": Q1, "text": "b"}, {"id": "a b", "text": "c"},
                                            {"text": "d"}]))
        self.assertEqual(f, [f'quellenverzeichnis[1].id: "{Q1}" steht schon im Quellenverzeichnis',
                             'quellenverzeichnis[2].id: nur Buchstaben, Ziffern und . _ : -, ist "a b"',
                             "quellenverzeichnis[3].id: fehlt"])
        # Ohne Verzeichnis wird nicht abgeglichen
        self.assertEqual(pruefen({k: v for k, v in BERICHT.items() if k != "quellenverzeichnis"}), [])

    def test_quellen_id_nicht_im_text(self):
        f = pruefen(mit(b2={"typ": "absatz", "text": f"Laut {Q2} sind es 5."}))
        self.assertEqual(f, [f'bloecke[2].text: Quellen-ID "{Q2}" im Text, bitte ins Feld quellen verschieben '
                             f'(z. B. [{{"art": "quelle", "stelle": "{Q2}"}}])'])
        # In Tabellenzellen darf die ID stehen (z. B. eine Spalte "Beleg")
        self.assertEqual(pruefen(mit(b3={"typ": "tabelle", "zeilen": [["Wert", Q2]]})), [])

    def test_zellbelege_fehler(self):
        f = pruefen(mit(b3={"typ": "tabelle", "zeilen": [[{"text": "1", "quelle": Q1}, {"wert": 2}], ["a"]]}))
        self.assertEqual(f, [
            'bloecke[3].zeilen[0][0].quelle: unbekanntes Feld (gemeint: "quellen"?), erlaubt sind: text, quellen, '
            'kennzeichnung',
            "bloecke[3].zeilen[0][1].wert: unbekanntes Feld, erlaubt sind: text, quellen, kennzeichnung",
            "bloecke[3].zeilen[0][1].text: fehlt",
            "bloecke[3].zeilen[1]: hat 1 Zellen, erwartet 2 (wie zeilen[0])"])

    def test_datum_und_ebenen(self):
        f = pruefen(mit(datum="2026-11-09", b0={"typ": "ueberschrift", "text": "x", "ebene": 2}))
        self.assertEqual(f, ['datum: muss ein Datum wie "20.10.2026" sein (TT.MM.JJJJ), ist "2026-11-09"',
                             "bloecke[0].ebene: Ebene 2 vor der ersten Überschrift der Ebene 1, erst eine Überschrift "
                             "mit ebene 1 setzen"])


class TestBauen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        heute = mock.patch.object(zusammenfassung, "heute", return_value="09.11.2026")
        heute.start()
        self.addCleanup(heute.stop)

    def bauen(self, beschreibung=BERICHT, profil=PROFIL):
        return bauen(beschreibung, self.tmp / "b.docx", profil, vorschau=False)

    def test_kontrolltext(self):
        self.assertEqual(self.bauen().kontrolltext.split("\n"), [
            "Wirtschaftlichkeit",
            "Robotik",
            "Stand 09.11.2026 · erstellt von finance",
            "[Annahme] nicht durch eine Quelle belegt, angenommen   [unsicher] Quelle nicht eindeutig, bitte prüfen",
            "# 1  Markt",
            f"Umsatz 7,9 Mrd. EUR. [{Q1}]",
            "Marge etwa 4 %. [Annahme]",
            "| Größe | Wert |",
            f"| Betriebe | 1.850 [{Q1}] |",
            "| Anteil | 30 % [Annahme] |",
            "| Ort | Brandenburg |",
            "[Kasten] Hypothese 1",
            "[Kasten] Abbruch bei < 3 Zusagen.",
            "[Kasten] Einschränkung",
            "[Kasten] Daten aufgeteilt. [unsicher]",
            "# Offene Fragen",
            "• Wer kauft?",
            "# Quellen",
            Q1,
            "GENESIS, https://genesis.destatis.de/x",
            Q2,
            "TED",
        ])

    def test_schlicht_ohne_rubrik_datum_kennzeichen(self):
        b = {"art": "bericht", "titel": "T", "datum": "01.11.2026", "bloecke": [{"typ": "absatz", "text": "x"}]}
        self.assertEqual(self.bauen(b, profil=None).kontrolltext.split("\n"), ["T", "Stand 01.11.2026", "x"])

    def test_zahlen_rechts_link_farben_fusszeile(self):
        d = docx.Document(self.bauen().pfad)
        zellen = d.tables[0].rows[1].cells
        self.assertEqual(zellen[1].paragraphs[0].alignment, WD_ALIGN_PARAGRAPH.RIGHT)  # 1.850
        self.assertIsNone(zellen[0].paragraphs[0].alignment)
        self.assertIsNone(d.tables[0].rows[3].cells[1].paragraphs[0].alignment)  # Brandenburg
        self.assertEqual(len(d.element.body.findall(".//" + qn("w:hyperlink"))), 1)
        flaechen = {el.get(qn("w:fill")) for el in d.element.body.iter(qn("w:shd"))}
        self.assertIn("DDEEDD", flaechen)  # Hinweis "wichtig" in der Farbe pruefungsrelevant
        fuss = d.sections[0].footer.paragraphs[0].text
        self.assertTrue(fuss.startswith("Wirtschaftlichkeit · Robotik\tSeite "), fuss)


if __name__ == "__main__":
    unittest.main()
