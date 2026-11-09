import unittest

import checkliste
import formulare
from angaben import Angaben
from tests.hilfe import beispiel


def liste(a):
    auswahl = formulare.auswahl(a)
    seiten, s = {}, 1
    for f, gilt, _ in auswahl:
        if gilt is not False:
            seiten[f.schluessel] = (s, s + len(f.seiten) - 1)
            s += len(f.seiten)
    for f, gilt, _ in auswahl:  # Felder lesen, damit fehlend gefüllt ist (wie im Agenten)
        if gilt is not False:
            f.felder(a, formulare.date(2026, 11, 10))
    return checkliste.erstellen(a, auswahl, seiten, "druck.pdf")


class TestCheckliste(unittest.TestCase):
    def test_ledig(self):
        text = liste(beispiel())
        self.assertIn("NICHT doppelseitig", text)
        self.assertIn(" 1. Personalfragebogen (Fin 770): liegt bei (S. 1-4)", text)
        self.assertIn("entfällt (nur mit Kindern)", text)
        self.assertNotIn("Eheurkunde", text)
        self.assertNotIn("FEHLENDE ANGABEN", text)
        self.assertIn("Dienstag, 10.11.2026, 14:00", text)

    def test_verheiratet_und_fehlendes(self):
        a = beispiel(familie={"stand": "verheiratet"}, geld={"iban": ""})
        text = liste(a)
        self.assertIn("26. Eheurkunde", text)
        self.assertIn("- IBAN", text)
        self.assertIn("Erklärung zum Familienzuschlag (Fin 708): liegt bei", text)

    def test_ohne_angaben(self):
        text = liste(Angaben({}))
        self.assertIn("bitte prüfen, ob nötig", text)
        self.assertIn("26.-30. nur falls zutreffend", text)
        self.assertIn("- Nachname", text)


if __name__ == "__main__":
    unittest.main()
