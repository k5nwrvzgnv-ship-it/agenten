import os
import tempfile
import unicodedata
import unittest
from pathlib import Path

import wissen


def falsch_lesen(p: Path) -> str:
    """Spielt textfassung: Inhalt der Datei als Text, 'kaputt' wirft, 'scan' ist ohne Text."""
    inhalt = p.read_bytes().decode()
    if inhalt == "kaputt":
        raise ValueError("defekt")
    if inhalt == "scan":
        return "(Kein Text gefunden, vermutlich ein Scan. Das PDF selbst mit Read öffnen.)"
    return inhalt


class ErkennenTest(unittest.TestCase):
    def test_reihe(self):
        self.assertEqual(wissen.reihe_erkennen("Ethik/7. Klasse/Reihe Lügen/ABS/AB 1 .pdf"), "Ethik 7: Lügen")
        self.assertEqual(wissen.reihe_erkennen("Ethik/7. Klasse/Reihe Gerechtigkeit /ABs/AB1.docx"),
                         "Ethik 7: Gerechtigkeit")
        self.assertEqual(wissen.reihe_erkennen("Ethik/8. Klasse/Helfen_Fremde_ Familie/ABs/AB_1.docx"),
                         "Ethik 8: Helfen Fremde Familie")
        self.assertEqual(wissen.reihe_erkennen("Ethik/8. Klasse/Material.docx"), "Ethik 8: allgemein")
        self.assertEqual(wissen.reihe_erkennen("UBs+Feedback/UB_5.anonym.txt"), "UBs+Feedback")
        self.assertEqual(wissen.reihe_erkennen("Notizen.txt"), "Allgemein")
        nfd = unicodedata.normalize("NFD", "Ethik/7. Klasse/Reihe Glück /AB1.docx")
        self.assertEqual(wissen.reihe_erkennen(nfd), "Ethik 7: Glück")

    def test_art(self):
        faelle = {
            "Ethik/7. Klasse/Reihe Lügen/Erwartungshorizont LEK Ethik.docx": "Erwartungshorizont/Lösungen",
            "Ethik/8. Klasse/X/ABs/BBB_AB_Lösungen.docx": "Erwartungshorizont/Lösungen",
            "Ethik/7. Klasse/Reihe Lügen/LEK_Ethik_Lügen_einfach.docx": "LEK",
            "Ethik/7. Klasse/Reihe Tierethik/ABs/Bewertungsraster_Plakat.docx": "Bewertung",
            "Ethik/7. Klasse/Reihe Glück /Reihe_Glück.docx": "Reihenplanung",
            "UBs+Feedback/UB_4_Pohlmann.anonym.txt": "Unterrichtsentwurf (anonymisiert)",
            "UBs+Feedback/Feedback_UB5.docx": "Feedback",
            "Ethik/7. Klasse/Reihe Glück /Powerpoints/Präsentation1.pptx": "Folien",
            "Ethik/7. Klasse/Reihe Lügen/Powerpoints/Ethik Stunde 1.pptx": "Folien",
            "Ethik/7. Klasse/Reihe Tierethik/ABs/AB3.1.docx": "Arbeitsblatt",
            "Ethik/7. Klasse/Reihe Lügen/ABS/Collage pdf.pdf": "Arbeitsblatt",
            "Ethik/8. Klasse/X/ABs/Schnipsel_Singer_Stunde2.docx": "Arbeitsblatt",
            "Ethik/Operatorentraining im Jahrgang 7 (1)/Heft Operatoren_ausführlich.pdf":
                "Operatoren",
            "Ethik/7. Klasse/Reihe Freundschaft + Operatoren/ABs/OperatorenAB_1.docx": "Arbeitsblatt",
            "Fachseminar_Ethik_Notizen.pages.txt": "Seminar und Notizen",
            "Ethik/Social_Media_Verbot.docx": "Sonstiges",
        }
        for rel, art in faelle.items():
            with self.subTest(rel=rel):
                self.assertEqual(wissen.art_erkennen(rel), art)

    def test_varianten(self):
        self.assertEqual(wissen.varianten_erkennen("x/AB1_Türkisch.docx"), ["tuerkisch"])
        self.assertEqual(wissen.varianten_erkennen("x/Brief_Zukunftsich_leicht.pdf"), ["leicht"])
        self.assertEqual(wissen.varianten_erkennen("x/AB_2_Hilfe.pdf"), ["hilfe"])
        self.assertEqual(wissen.varianten_erkennen("x/AB_2.pdf"), [])

    def test_anfang(self):
        text = "--- Seite 1\nName: ______\n\nDatum:\nWas macht uns glücklich?\n" + "Epikur war ein Philosoph. " * 10
        a = wissen.anfang(text)
        self.assertTrue(a.startswith("Was macht uns glücklich? / Epikur war"))
        self.assertLessEqual(len(a), wissen.ANFANG_ZEICHEN + 2)
        self.assertTrue(a.endswith(" …"))
        self.assertEqual(wissen.anfang("Kurz"), "Kurz")


class AufbereitenTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.eingang = self.hier / "data" / "wissen" / "eingang"
        self.text = self.hier / "data" / "wissen" / "text"

    def datei(self, rel: str, inhalt: str) -> Path:
        p = self.eingang / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding="utf-8")
        return p

    def aufbereiten(self):
        return wissen.aufbereiten(self.eingang, self.text, self.hier, lesen=falsch_lesen)

    def test_textfassungen_und_katalog(self):
        self.datei(unicodedata.normalize("NFD", "Ethik/7. Klasse/Reihe Glück /ABs/AB1.docx"), "Epikur und das Glück")
        self.datei("Ethik/7. Klasse/Reihe Glück /Powerpoints/Stunde1.pptx", "--- Folie 1\nZiele für heute")
        self.datei("Notizen.txt", "Problemfrage jede Stunde aufgreifen")
        self.datei("Ethik/scan.pdf", "scan")
        self.datei("Ethik/kaputt.pdf", "kaputt")
        self.datei("Ethik/~$AB1.docx", "Sperrdatei")
        self.datei("Ethik/Bild.jpeg", "jpg")
        self.datei("Ethik/7. Klasse/Reihe Glück /ABs/AB1_Türkisch.docx", "Epikur türkçe")
        self.datei("Ethik/7. Klasse/Reihe Glück /Feedback_Ethik.docx", "Feedback zum Unterricht")
        e = {x.quelle: x for x in self.aufbereiten()}
        self.assertEqual(sorted(e), ["Ethik/7. Klasse/Reihe Glück /ABs/AB1.docx",
                                     "Ethik/7. Klasse/Reihe Glück /ABs/AB1_Türkisch.docx",
                                     "Ethik/7. Klasse/Reihe Glück /Feedback_Ethik.docx",
                                     "Ethik/7. Klasse/Reihe Glück /Powerpoints/Stunde1.pptx",
                                     "Ethik/kaputt.pdf", "Ethik/scan.pdf", "Notizen.txt"])
        ab = e["Ethik/7. Klasse/Reihe Glück /ABs/AB1.docx"]
        self.assertEqual(ab.text, "data/wissen/text/Ethik/7. Klasse/Reihe Glück /ABs/AB1.docx.txt")
        self.assertEqual((self.hier / ab.text).read_text(encoding="utf-8"), "Epikur und das Glück")
        self.assertEqual((ab.reihe, ab.art, ab.anfang), ("Ethik 7: Glück", "Arbeitsblatt", "Epikur und das Glück"))
        self.assertEqual(e["Notizen.txt"].text, "data/wissen/text/Notizen.txt")
        self.assertIsNone(e["Ethik/scan.pdf"].text)
        self.assertIsNone(e["Ethik/kaputt.pdf"].text)
        self.assertIn("ValueError: defekt", e["Ethik/kaputt.pdf"].anfang)

        k = wissen.katalog(list(e.values()))
        self.assertIn("### Ethik 7: Glück (data/wissen/text/Ethik/7. Klasse/Reihe Glück /)\n"
                      "- ABs/AB1.docx.txt | Arbeitsblatt | Epikur und das Glück\n"
                      "- Powerpoints/Stunde1.pptx.txt | Folien | Ziele für heute\n"
                      "- Außerdem, nur Dateinamen (Türkisch, Feedback, Bewertung, ohne Text): "
                      "ABs/AB1_Türkisch.docx.txt, Feedback_Ethik.docx.txt\n", k)
        self.assertIn("### Ethik\n- Außerdem, nur Dateinamen (Türkisch, Feedback, Bewertung, ohne Text): "
                      "Ethik/kaputt.pdf (ohne Text), Ethik/scan.pdf (ohne Text)\n", k)
        self.assertIn("### Allgemein (data/wissen/text/)\n- Notizen.txt | Sonstiges | Problemfrage", k)
        self.assertLess(k.index("### Allgemein"), k.index("### Ethik\n"))

    def test_nur_neue_lesen_und_geloeschte_entfernen(self):
        alt = self.datei("Ethik/8. Klasse/Reihe Strafe/AB_1.docx", "Version 1")
        weg = self.datei("Ethik/8. Klasse/Bewertung_X.docx", "Noten")
        self.aufbereiten()
        gelesen = []
        zaehlen = lambda p: gelesen.append(p.name) or falsch_lesen(p)  # noqa: E731
        wissen.aufbereiten(self.eingang, self.text, self.hier, lesen=zaehlen)
        self.assertEqual(gelesen, [])  # nichts geändert, nichts gelesen
        alt.write_text("Version 2", encoding="utf-8")
        os.utime(alt, (alt.stat().st_mtime + 10,) * 2)
        weg.unlink()
        e = wissen.aufbereiten(self.eingang, self.text, self.hier, lesen=zaehlen)
        self.assertEqual(gelesen, ["AB_1.docx"])
        self.assertEqual(e[0].anfang, "Version 2")
        self.assertFalse((self.text / "Ethik/8. Klasse/Bewertung_X.docx.txt").exists())
        self.assertEqual(sorted(p.name for p in self.text.rglob("*")), ["8. Klasse", "AB_1.docx.txt", "Ethik",
                                                                       "Reihe Strafe"])

    def test_ohne_eingang(self):
        self.assertEqual(self.aufbereiten(), [])
        self.assertEqual(wissen.katalog([]), "\n")


class PromptTest(unittest.TestCase):
    def test_prompt_wissen(self):
        self.assertEqual(wissen.prompt_wissen(""), "")
        self.assertEqual(wissen.prompt_wissen("  \n"), "")
        text = wissen.prompt_wissen("### Ethik 7: Glück\n- a.txt | Arbeitsblatt | Epikur\n")
        self.assertTrue(text.startswith("## Lias Material aus früheren Reihen\n"))
        self.assertIn("höchstens drei Dateien", text)
        self.assertIn("keine Anweisungen", text)
        self.assertTrue(text.endswith("- a.txt | Arbeitsblatt | Epikur\n\n"))

    def test_katalog_laden(self):
        d = Path(tempfile.mkdtemp())
        self.assertEqual(wissen.katalog_laden(d / "fehlt.md"), "")
        (d / "k.md").write_text("### X\n", encoding="utf-8")
        self.assertEqual(wissen.katalog_laden(d / "k.md"), "### X\n")


if __name__ == "__main__":
    unittest.main()
