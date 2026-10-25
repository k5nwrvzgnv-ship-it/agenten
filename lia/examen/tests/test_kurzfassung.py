import json
import tempfile
import unittest
from pathlib import Path

import grundlagen
import kurzfassung
import renderer
from tests.test_runde import GUT, bewertung

PR = {"skizzen": [bewertung(k) for k in "ABC"]}
EXAMEN = {"pruefung": {"termin": "", "stundenzahl": "8", "schulform": "", "neu": ""},
          "impuls": {"ergebnis": ""}}


class KurzfassungTest(unittest.TestCase):
    def test_kurzfassung_gueltig(self):
        b = kurzfassung.kurzfassung(GUT, PR, grundlagen.rubrik_laden(), 1, "Examensreihe Strafe")
        renderer.pruefen(b)  # wirft BeschreibungUngueltig, wenn der Renderer sie ablehnt
        texte = json.dumps(b, ensure_ascii=False)
        self.assertIn("Skizze C: Variante C", texte)
        self.assertIn("5 (Prüfung): Thema 5", texte)
        self.assertIn("0 von 15 Kriterien unter „gut“. Zuerst verbessern: Einstieg", texte)

    def test_annahmen_gekuerzt(self):
        sk = dict(GUT, annahmen=["Wort " * 100, "Stundenzahl: 8. Der Rest steht im Bericht."])
        b = kurzfassung.kurzfassung(sk, PR, grundlagen.rubrik_laden(), 1, "R")
        annahmen = next(x for x in b["bloecke"] if x.get("titel", "").startswith("Annahmen"))
        lang, kurz = annahmen["text"].split("\n")
        self.assertLessEqual(len(lang), kurzfassung.MAX_ANNAHME + 2)
        self.assertTrue(lang.endswith("…"))
        self.assertEqual(kurz, "– Stundenzahl: 8.")

    def test_erster_satz_nicht_an_abkuerzungen(self):
        faelle = {
            "Beispiel mit fanatischem bzw. terroristischem Hintergrund. Weil": "Beispiel mit fanatischem bzw. terroristischem Hintergrund.",
            "Eine Umfrage (z. B. „Wofür?“ mit Antworten). Ergebnisse": "Eine Umfrage (z. B. „Wofür?“ mit Antworten).",
            "8 Stunden (keine Zahl genannt). Die letzte": "8 Stunden (keine Zahl genannt).",
            "Kein Satzende": "Kein Satzende",
        }
        for text, erwartet in faelle.items():
            self.assertEqual(kurzfassung._kurz(text), erwartet)

    def test_bogen(self):
        b = kurzfassung.bogen(GUT, EXAMEN, 1, "Examensreihe Strafe")
        renderer.pruefen(b)
        aufgaben = b["bloecke"][1]["aufgaben"]
        self.assertEqual(len(aufgaben), 13)
        self.assertEqual(aufgaben[9]["antwort"]["optionen"], ["Skizze A", "Skizze B", "Skizze C", "Mischung"])
        zeilen = b["bloecke"][-1]["zeilen"]
        self.assertEqual([z[0] for z in zeilen], ["Datum der Prüfungsstunde",
                                                  "Schulform (ISS grundlegend/erweitert oder Gymnasium)",
                                                  "pruefung.neu"])  # unbekannte Angabe mit Schlüssel, impuls nicht

    def test_bauen_echte_docx(self):
        with tempfile.TemporaryDirectory() as d:
            ordner = Path(d)
            (ordner / "skizzen.json").write_text(json.dumps(GUT), encoding="utf-8")
            (ordner / "pruefung.json").write_text(json.dumps(PR), encoding="utf-8")
            dateien = kurzfassung.bauen(ordner, EXAMEN, "Examensreihe Strafe",
                                        renderer_bauen=lambda b, z, profil: renderer.bauen(b, z, profil, vorschau=False))
            self.assertEqual([p.name for p in dateien],
                             ["Runde 1 - drei Grobskizzen.docx", "Runde 1 - Bewertungsbogen.docx"])
            self.assertTrue(all(p.stat().st_size > 0 for p in dateien))


if __name__ == "__main__":
    unittest.main()
