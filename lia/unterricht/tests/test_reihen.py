"""Tests für reihen.py. Seit 03.11.2026 liest agentkit.struktur die Datei (Strukturplan, Bauschritt 2); die Prüfung
selbst testet shared/agentkit/tests/test_struktur.py, hier nur, dass Fehler ankommen.

Regel 22 des Strukturplans: prompt_reihen ist für die echte Datei (altes Format, eingefrorene Kopie
shared/agentkit/tests/daten/reihen_alt.toml) und dieselben Reihen im neuen Format (tests/daten/reihen_neu.toml)
gleich, auch mit gewählter Reihe; ein Auftrag mit ort = Stunden-id wählt Reihe und Stunde.
"""

import tempfile
import unittest
from pathlib import Path

import reihen
from agentkit import struktur

HIER = Path(__file__).resolve().parent.parent
ALT = (HIER.parents[1] / "shared" / "agentkit" / "tests" / "daten" / "reihen_alt.toml").read_text(encoding="utf-8")
NEU = (HIER / "tests" / "daten" / "reihen_neu.toml").read_text(encoding="utf-8")
GRUPPE = "Platzhalter: Lias Text steht nicht in den Testdaten (F6)."  # Lerngruppe von Ethik 8 in ALT

GUT = """
[[reihe]]
id = "ethik-8-helfen"
fach = "Ethik"
klasse = "8"
titel = "Helfen"
reihenfrage = "Muss ich Fremden genauso helfen wie meiner Familie?"
lerngruppe = "lernschwach, mehrsprachig"
behandelt = ["Singer", "Aristoteles"]
merksaetze = ["Merksatz eins.", "Merksatz zwei."]
notizen = "Nächste Stunde Fallbeispiel"

[[reihe]]
fach = "Darstellendes Spiel"
klasse = "Kurs 11"
reihenfrage = "Wie entsteht eine Figur?"

[[reihe]]
fach = "Ethik"
klasse = "8"
titel = "Strafe (in Planung)"
bisherige_reihen = ["Klasse 7: Lüge", "Klasse 8: Helfen"]

[[reihe]]
fach = "Ethik"
klasse = "7"
titel = "Glück"
reihenfrage = "Wie führe ich ein glückliches Leben?"
schuljahr = "2025/26"
stand = "abgeschlossen"
lerngruppe = "steht nicht im Prompt"
"""

STUNDEN_NEU = """
[[reihe.stunde]]
id = "s-einstieg"
thema = "Einstieg: Warum strafen wir?"

[[reihe.stunde]]
id = "s-alt"
thema = "Ausgeblendet"
archiviert = "2026-11-02"

[[reihe.stunde]]
id = "s-kant"
thema = "Kant: Vergeltung"
marke = "Prüfung"
"""


def instanz(text: str, lerngruppen: str = "") -> Path:
    """Ordner wie lia/instanz mit reihen.toml (und lerngruppen.toml, chmod 600)."""
    ordner = Path(tempfile.mkdtemp())
    (ordner / "reihen.toml").write_text(text, encoding="utf-8")
    if lerngruppen:
        (ordner / "lerngruppen.toml").write_text(lerngruppen, encoding="utf-8")
        (ordner / "lerngruppen.toml").chmod(0o600)
    return ordner


def mit_stunden_neu(text: str) -> str:
    """Stunden an Straftheorien im neuen Format (vor dem nächsten Reihen-Block)."""
    teile = text.split('[[reihe]]\nid = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"')
    return teile[0] + STUNDEN_NEU.lstrip() + '\n[[reihe]]\nid = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"' + teile[1]


class ReihenTest(unittest.TestCase):
    def test_mitgelieferte_datei_ist_gueltig(self):
        s = reihen.laden(HIER.parent / "instanz")
        text = reihen.prompt_reihen(s.reihen, "Ethik")
        self.assertIn("### Ethik, Klasse 8: Straftheorien", text)
        self.assertIn("### Darstellendes Spiel, Kurs 12: Der nackte Wahnsinn", text)

    def test_ohne_datei_und_leer(self):
        self.assertEqual(reihen.laden(Path(tempfile.mkdtemp())).reihen, [])
        self.assertEqual(reihen.laden(instanz("# nur Kommentare\n")).reihen, [])
        self.assertEqual(reihen.prompt_reihen([], "Ethik"), "")
        self.assertEqual(reihen.prompt_auftrag(None, "Ethik", {"reihe": "x"}), "")

    def test_laden_und_prompt(self):
        r = reihen.laden(instanz(GUT)).reihen
        self.assertEqual(len(r), 4)
        text = reihen.prompt_reihen(r, "Ethik")
        self.assertTrue(text.startswith("## Lias laufende Reihen\n"))
        self.assertIn("### Ethik, Klasse 8: Helfen\n- Reihenfrage: Muss ich Fremden", text)
        self.assertIn("- Lerngruppe: lernschwach, mehrsprachig", text)
        self.assertIn("- Schon behandelt: Singer; Aristoteles", text)
        self.assertIn("- Merksätze der Reihe:\n  - Merksatz eins.\n  - Merksatz zwei.", text)
        self.assertIn("- Notizen: Nächste Stunde Fallbeispiel", text)
        self.assertIn("### Darstellendes Spiel, Kurs 11\n- Reihenfrage: Wie entsteht eine Figur?\n\n", text)
        self.assertNotIn("Lerngruppe", text.split("### Darstellendes Spiel")[1])
        self.assertIn("### Ethik, Klasse 8: Strafe (in Planung)\n"
                      "- Frühere Reihen der Klasse:\n  - Klasse 7: Lüge\n  - Klasse 8: Helfen\n\n", text)
        self.assertTrue(text.endswith("### Abgeschlossene Reihen (nur zur Orientierung, was die Klassen schon kennen)\n"
                                      "- Ethik, Klasse 7 (2025/26): Glück – Wie führe ich ein glückliches Leben?\n\n"))
        self.assertNotIn("steht nicht im Prompt", text)

    def test_stunden(self):
        text = GUT + """
[[reihe]]
id = "ds-kurs-12-stueck"
fach = "Darstellendes Spiel"
klasse = "Kurs 12"
titel = "Stück"
agenten = ["theater"]

[[reihe.stunde]]
nr = 2
thema = "Szene 2"
marke = "Prüfung"

[[reihe.stunde]]
nr = 1
thema = "Leseprobe"
"""
        r = reihen.laden(instanz(text)).reihen
        self.assertEqual([s["nr"] for s in r[-1]["stunden"]], [1, 2])
        self.assertNotIn("stunde", r[-1])
        prompt = reihen.prompt_reihen(r, "Ethik")
        self.assertIn("- Proben der Reihe:\n  - Probe 1: Leseprobe\n  - Probe 2: Szene 2 (Prüfung)", prompt)
        self.assertNotIn("zugeordnet)", prompt)
        # gewählte Reihe steht zuerst und ist markiert
        prompt = reihen.prompt_reihen(r, "Ethik", gewaehlt="ds-kurs-12-stueck")
        self.assertIn("## Lias laufende Reihen\n", prompt)
        erster = prompt.split("### ")[1]
        self.assertTrue(erster.startswith("Darstellendes Spiel, Kurs 12: Stück (Lia hat den Auftrag dieser Reihe zugeordnet)"))
        self.assertEqual(prompt.count("Kurs 12: Stück"), 1)
        # auch eine abgeschlossene Reihe kann gewählt sein (Archiv), dann voll und nicht in der Liste
        prompt = reihen.prompt_reihen(r, "Ethik", gewaehlt=None)
        self.assertIn("Klasse 7 (2025/26): Glück", prompt)
        self.assertEqual(r[3]["id"], "ethik-7-glueck")  # abgeleitet wie in der Web-App
        prompt = reihen.prompt_reihen(r, "Ethik", gewaehlt="ethik-7-glueck")
        self.assertIn("### Ethik, Klasse 7: Glück (Lia hat", prompt)
        self.assertNotIn("Abgeschlossene Reihen", prompt)
        self.assertEqual(reihen.stunden_wort(r[0]), "Stunde")

    def test_geplant_laufend_archiviert(self):
        neu = """
[[fach]]
id = "ethik"
name = "Ethik"

[[klasse]]
id = "ethik-8"
fach = "ethik"
name = "8"

[[klasse]]
id = "ethik-7"
fach = "ethik"
name = "7"
schuljahr = "2025/26"
archiviert = "2026-08-01"

[[reihe]]
id = "a"
klasse = "ethik-8"
titel = "Geplant"
stand = "geplant"

[[reihe]]
id = "b"
klasse = "ethik-8"
titel = "Archiviert"
archiviert = "2026-11-03"

[[reihe]]
id = "c"
klasse = "ethik-7"
titel = "Laufend in archivierter Klasse"
"""
        s = reihen.laden(instanz(neu))
        self.assertEqual([reihen.laufend(r) for r in s.reihen], [True, False, False])
        text = reihen.prompt_reihen(s.reihen, "Ethik")
        self.assertIn("### Ethik, Klasse 8: Geplant\n", text)
        self.assertTrue(text.endswith("### Abgeschlossene Reihen (nur zur Orientierung, was die Klassen schon kennen)\n"
                                      "- Ethik, Klasse 8: Archiviert\n"
                                      "- Ethik, Klasse 7 (2025/26): Laufend in archivierter Klasse\n\n"))

    def test_fehler_kommen_als_strukturfehler(self):
        for text, erwartet in {"[[reihe]\nklasse = '8'": "kein gültiges TOML",
                               "[[reihe]]\nfach = 'Ethik'\nreihenfrage = 'x'": "klasse fehlt",
                               "[[reihe]]\nfach = 'Ethik'\nklasse = '8'\nstand = 'fertig'": "stand 'fertig'"}.items():
            with self.subTest(text=text), self.assertRaises(struktur.StrukturFehler) as f:
                reihen.laden(instanz(text))
            self.assertIn(erwartet, str(f.exception))


class WahlTest(unittest.TestCase):
    def setUp(self):
        self.s = reihen.laden(instanz(mit_stunden_neu(NEU), f'"ethik-8" = "{GRUPPE}"\n'))

    def test_ort_vor_reihe(self):
        self.assertEqual(reihen.wahl(self.s, {}), (None, None))
        self.assertEqual(reihen.wahl(None, {"reihe": "a", "ort": "s-kant"}), ("a", None))
        self.assertEqual(reihen.wahl(self.s, {"reihe": "ethik-7-freundschaft"}), ("ethik-7-freundschaft", None))
        gewaehlt, stunde = reihen.wahl(self.s, {"reihe": "ethik-7-freundschaft", "ort": "s-kant"})
        self.assertEqual((gewaehlt, stunde["id"], stunde["nr"]), ("ethik-8-straftheorien", "s-kant", 2))
        self.assertEqual(reihen.wahl(self.s, {"ort": "ethik-8-straftheorien"}), ("ethik-8-straftheorien", None))

    def test_ort_ohne_reihe_oder_unbekannt_nimmt_feld_reihe(self):
        for ort in ("ethik-8", "ethik", "gibt-es-nicht"):
            with self.subTest(ort=ort):
                self.assertEqual(reihen.wahl(self.s, {"ort": ort, "reihe": "ethik-7-freundschaft"}),
                                 ("ethik-7-freundschaft", None))

    def test_auftrag_mit_stunden_id(self):
        text = reihen.prompt_auftrag(self.s, "Ethik", {"ort": "s-kant"})
        erster = text.split("### ")[1]
        self.assertTrue(erster.startswith(
            "Ethik, Klasse 8: Straftheorien (in Planung) (Lia hat den Auftrag dieser Reihe zugeordnet)\n"
            "- Lia hat den Auftrag zugeordnet: Stunde 2: Kant: Vergeltung (Prüfung)\n"
            f"- Lerngruppe: {GRUPPE}\n"))
        self.assertIn("- Stunden der Reihe:\n  - Stunde 1: Einstieg: Warum strafen wir?\n"
                      "  - Stunde 2: Kant: Vergeltung (Prüfung)\n\n", text)
        self.assertNotIn("Ausgeblendet", text)
        # Stunde ohne Nummer (ausgeblendet) wird ohne Nummer genannt
        text = reihen.prompt_auftrag(self.s, "Ethik", {"ort": "s-alt"})
        self.assertIn("- Lia hat den Auftrag zugeordnet: Stunde: Ausgeblendet\n", text)
        # Probe statt Stunde für die Reihe des Theater-Agenten
        r = self.s.reihe("darstellendes-spiel-kurs-12-der-nackte-wahnsinn")
        self.assertEqual(reihen.stunde_zeile(r, {"nr": 3, "thema": "Szene 1", "marke": ""}), "Probe 3: Szene 1")


class Regel22AltUndNeuTest(unittest.TestCase):
    """Strukturplan Regel 22 für unterricht: prompt_reihen liefert die Reihe in beiden Formaten gleich."""

    def setUp(self):
        self.alt = reihen.laden(instanz(ALT))
        self.neu = reihen.laden(instanz(NEU, f'"ethik-8" = "{GRUPPE}"\n'))
        self.assertEqual((self.alt.format, self.neu.format), ("alt", "neu"))

    def test_gleicher_prompt_ohne_und_mit_gewaehlter_reihe(self):
        self.assertEqual([r["id"] for r in self.alt.reihen], [r["id"] for r in self.neu.reihen])
        for gewaehlt in [None] + [r["id"] for r in self.alt.reihen]:
            with self.subTest(gewaehlt=gewaehlt):
                auftrag = {"reihe": gewaehlt} if gewaehlt else {}
                alt = reihen.prompt_auftrag(self.alt, "Ethik", auftrag)
                self.assertEqual(alt, reihen.prompt_auftrag(self.neu, "Ethik", auftrag))
                self.assertEqual(alt, reihen.prompt_auftrag(self.neu, "Ethik", {"ort": gewaehlt} if gewaehlt else {}))

    def test_inhalt_der_echten_datei(self):
        text = reihen.prompt_auftrag(self.neu, "Ethik", {"reihe": "ethik-8-straftheorien"})
        self.assertIn("### Ethik, Klasse 8: Straftheorien (in Planung) (Lia hat den Auftrag dieser Reihe zugeordnet)\n"
                      f"- Lerngruppe: {GRUPPE}\n- Frühere Reihen der Klasse:\n  - Klasse 7, Lüge und Wahrheit:", text)
        self.assertIn("### Darstellendes Spiel, Kurs 12: Der nackte Wahnsinn\n\n", text)
        self.assertIn("### Darstellendes Spiel, Kurs 11\n\n", text)  # Platzhalter-Reihe bis zur Migration
        kurz = text.split("### Abgeschlossene Reihen")[1]
        self.assertIn("- Ethik, Klasse 7 (2025/26): Lüge und Wahrheit – Sollte ich lügen", kurz)
        self.assertIn("- Darstellendes Spiel, Kurs 11 (2025/26): Proben + Feedbackphase\n\n", kurz)
        self.assertEqual(kurz.count("\n- "), 11)

    def test_stunden_id_in_beiden_formaten(self):
        alt_mit = ALT.replace('# Jan 30.10.2026: das Stück', '[[reihe.stunde]]\nnr = 1\nthema = "Einstieg: Warum '
                              'strafen wir?"\n\n[[reihe.stunde]]\nnr = 2\nthema = "Kant: Vergeltung"\nmarke = '
                              '"Prüfung"\n\n# Jan 30.10.2026: das Stück')
        alt = reihen.laden(instanz(alt_mit))
        neu = reihen.laden(instanz(mit_stunden_neu(NEU), f'"ethik-8" = "{GRUPPE}"\n'))
        self.assertEqual(reihen.prompt_auftrag(alt, "Ethik", {"ort": "ethik-8-straftheorien-stunde-2"}),
                         reihen.prompt_auftrag(neu, "Ethik", {"ort": "s-kant"}))


if __name__ == "__main__":
    unittest.main()
