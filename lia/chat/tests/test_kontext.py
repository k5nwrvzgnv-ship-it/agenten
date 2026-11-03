"""Tests für kontext.py. Testregel 22 (docs/struktur-pflege-plan.md, Abschnitt 10) für chat: Nach jeder Änderung der
Struktur liefert kontext_text die Reihe richtig, im alten und im neuen Format von reihen.toml.

Vorlage: die eingefrorenen Kopien aus shared/agentkit/tests/daten (reihen_alt.toml = echte Datei, reihen_neu.toml =
dieselben Daten im neuen Format). Die Änderungen sind von Hand nachgestellt, bis agentkit.struktur schreiben kann.
"""

import tempfile
import unittest
from pathlib import Path

import kontext
from agentkit import struktur

DATEN = Path(struktur.__file__).parent / "tests" / "daten"
ALT = (DATEN / "reihen_alt.toml").read_text(encoding="utf-8")
NEU = (DATEN / "reihen_neu.toml").read_text(encoding="utf-8")
STRAFE = "ethik-8-straftheorien"
GRUPPE = "Gruppe aus lerngruppen.toml"
ORT = {"reihe": STRAFE, "chip": "Ethik › 8 › Straftheorien", "materialien": ["AB Kant"]}

# Stunden der Straftheorien im neuen Format (s-alt ist ausgeblendet)
EINSTIEG = '[[reihe.stunde]]\nid = "s-einstieg"\nthema = "Einstieg: Wozu Gefängnis?"\n'
LISZT = '[[reihe.stunde]]\nid = "s-liszt"\nthema = "von Liszt: Prävention"\nmarke = "UB"\n'
ALT_STUNDE = '\n[[reihe.stunde]]\nid = "s-alt"\nthema = "Alte Idee, ausgeblendet"\narchiviert = "2026-11-02"\n'


def ersetzt(text: str, alt: str, neu: str) -> str:
    assert text.count(alt) == 1, alt
    return text.replace(alt, neu)


class Laden(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.instanz = Path(self.tmp.name) / "instanz"
        self.instanz.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def schreiben(self, text: str, lerngruppen: str | None = None):
        (self.instanz / "reihen.toml").write_text(text, encoding="utf-8")
        if lerngruppen is not None:
            pfad = self.instanz / "lerngruppen.toml"
            pfad.write_text(lerngruppen, encoding="utf-8")
            pfad.chmod(0o600)

    def text(self, ort: dict = ORT, reihe_id: str = STRAFE) -> str:
        return kontext.kontext_text(ort, kontext.reihe_finden(kontext.reihen_laden(self.instanz), reihe_id))

    def test_altes_format(self):
        self.schreiben(ALT)
        reihen = kontext.reihen_laden(self.instanz)
        self.assertEqual(len(reihen), 14)
        self.assertIsNone(kontext.reihe_finden(reihen, "gibt-es-nicht"))
        self.assertIsNone(kontext.reihe_finden(reihen, None))
        t = self.text()
        for teil in ("Ort in der App: Ethik › 8 › Straftheorien", "Fach: Ethik, Klasse 8",
                     "Reihe: Straftheorien (in Planung)", "Lerngruppe: Platzhalter", "Notizen: Nächste Reihe",
                     "Schon behandelt: Peter Singer; Aristoteles", "Material hier: AB Kant"):
            self.assertIn(teil, t)
        self.assertNotIn("Stunden:", t)
        self.assertIn("Fach: Darstellendes Spiel, Kurs 12",
                      self.text({"reihe": "x"}, "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"))

    def test_altes_format_ohne_id_wie_webapp(self):
        self.schreiben('[[reihe]]\nfach = "Ethik"\nklasse = "8"\ntitel = "Helfen (fertig)"\n')
        self.assertEqual([r["id"] for r in kontext.reihen_laden(self.instanz)], ["ethik-8-helfen"])

    def test_neues_format_mit_lerngruppe_der_klasse(self):
        self.schreiben(NEU, f'"ethik-8" = "{GRUPPE}"\n')
        t = self.text()
        for teil in ("Fach: Ethik, Klasse 8", "Reihe: Straftheorien", f"Lerngruppe: {GRUPPE}",
                     "Stunden: 1. Einstieg: Wozu Gefängnis?; 2. Kant: Vergeltung (Prüfung); "
                     "3. von Liszt: Prävention (UB)"):
            self.assertIn(teil, t)
        self.assertNotIn("Alte Idee", t)
        self.assertNotIn("Lerngruppe", self.text({"reihe": "x"}, "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"))

    def test_ohne_datei_leer_und_kaputte_datei(self):
        self.assertEqual(kontext.reihen_laden(self.instanz), [])
        self.schreiben("[[reihe]\n")
        with self.assertRaises(struktur.StrukturFehler):
            kontext.reihen_laden(self.instanz)

    def test_regel_22_neues_format(self):
        """Jede Änderung: die Reihe bleibt unter ihrer id auffindbar und kontext_text zeigt den neuen Stand."""
        offen = dict(ORT, stunde_id="s-liszt")
        faelle = {
            "Titel ändern": (ersetzt(NEU, 'titel = "Straftheorien"', 'titel = "Strafe"'), ORT, ["Reihe: Strafe"]),
            "Reihe in andere Klasse": (ersetzt(NEU, 'klasse = "ethik-8"\ntitel = "Straftheorien"',
                                               'klasse = "ethik-7-2025-26"\ntitel = "Straftheorien"'), ORT,
                                       ["Fach: Ethik, Klasse 7"]),
            "Stunde verschieben": (ersetzt(ersetzt(NEU, LISZT, ""), EINSTIEG, LISZT + "\n" + EINSTIEG), offen,
                                   ["Stunden: 1. von Liszt: Prävention (UB); 2. Einstieg", "Gerade offen: Stunde 1: "
                                    "von Liszt: Prävention"]),
            "Stunde ausblenden": (ersetzt(NEU, 'marke = "UB"\n', 'marke = "UB"\narchiviert = "2026-11-03"\n'), offen,
                                  ["Gerade offen: ausgeblendete Stunde: von Liszt: Prävention"]),
            "Stunde wieder einblenden": (ersetzt(NEU, ALT_STUNDE, ""), offen, ["Gerade offen: Stunde 3: von Liszt"]),
            "Reihe archivieren": (ersetzt(NEU, 'stand = "geplant"\n', 'stand = "geplant"\narchiviert = "2026-11-03"\n'),
                                  ORT, ["Reihe: Straftheorien"]),
            "Klasse archivieren": (ersetzt(NEU, 'herkunft = "ethik-7-2025-26"\n',
                                           'herkunft = "ethik-7-2025-26"\narchiviert = "2026-11-03"\n'), ORT,
                                   ["Fach: Ethik, Klasse 8"]),
            "Reihe kopieren": (NEU + '\n[[reihe]]\nid = "ethik-8-straftheorien-2"\nklasse = "ethik-8"\n'
                               'titel = "Straftheorien"\nstand = "geplant"\nherkunft = "ethik-8-straftheorien"\n',
                               offen, ["Stunden: 1. Einstieg", "Gerade offen: Stunde 3: von Liszt"]),
        }
        for name, (text, ort, erwartet) in faelle.items():
            with self.subTest(name):
                self.schreiben(text, f'"ethik-8" = "{GRUPPE}"\n')
                t = self.text(ort)
                for teil in erwartet + ["Ort in der App: Ethik › 8 › Straftheorien"]:
                    self.assertIn(teil, t)
        # die Kopie selbst: eigene id, ohne Stunden, Lerngruppe von der Klasse
        t = self.text({"reihe": "ethik-8-straftheorien-2"}, "ethik-8-straftheorien-2")
        self.assertIn(f"Lerngruppe: {GRUPPE}", t)
        self.assertNotIn("Stunden:", t)

    def test_regel_22_altes_format(self):
        """Bis zur Migration: Änderungen von Hand an der heutigen Datei, Reihe per gespeicherter id."""
        stunden = ('\n[[reihe.stunde]]\nnr = 2\nthema = "Kant"\nmarke = "UB"\n\n'
                   '[[reihe.stunde]]\nnr = 1\nthema = "Einstieg"\n')
        anker = 'agenten = ["examen"]\n'
        stueck = "\n# Jan 30.10.2026: das Stück"  # Kommentar über der nächsten Reihe
        mit_stunden = ersetzt(ALT, stueck, stunden + stueck)
        faelle = {
            "Titel ändern": (ersetzt(ALT, 'titel = "Straftheorien (in Planung)"', 'titel = "Strafe"'), ORT,
                             ["Reihe: Strafe"]),
            "Klasse ändern": (ersetzt(ALT, 'klasse = "8"\ntitel = "Straftheorien', 'klasse = "9"\ntitel = "Straf'
                                      'theorien'), ORT, ["Fach: Ethik, Klasse 9"]),
            "Stunden dazu": (mit_stunden, dict(ORT, stunde_id=f"{STRAFE}-stunde-2"),
                             ["Stunden: 1. Einstieg; 2. Kant (UB)", "Gerade offen: Stunde 2: Kant"]),
            "Stunde per Nummer": (mit_stunden, dict(ORT, stunde=1), ["Gerade offen: Stunde 1: Einstieg"]),
            "agenten weg": (ersetzt(ALT, anker, ""), ORT, ["Reihe: Straftheorien (in Planung)"]),
        }
        for name, (text, ort, erwartet) in faelle.items():
            with self.subTest(name):
                self.schreiben(text)
                t = self.text(ort)
                for teil in erwartet + ["Lerngruppe: Platzhalter"]:
                    self.assertIn(teil, t)


class Text(unittest.TestCase):
    def setUp(self):
        self.reihe = kontext.reihe_finden(struktur.aus_text(NEU).reihen, STRAFE)

    def test_ohne_ort_leer(self):
        self.assertEqual(kontext.kontext_text(None, None), "")

    def test_stunde_per_id_vor_nummer(self):
        t = kontext.kontext_text(dict(ORT, stunde_id="s-kant", stunde=1, stunde_thema="Alt"), self.reihe)
        self.assertIn("Gerade offen: Stunde 2: Kant: Vergeltung", t)

    def test_unbekannte_stunden_id_nimmt_nummer_aus_der_frage(self):
        t = kontext.kontext_text(dict(ORT, stunde_id="s-weg", stunde=3), self.reihe)
        self.assertIn("Gerade offen: Stunde 3: von Liszt: Prävention", t)
        t = kontext.kontext_text(dict(ORT, stunde_id="s-weg", stunde=3, stunde_thema="Aus der App"), self.reihe)
        self.assertIn("Gerade offen: Stunde 3: Aus der App", t)
        self.assertNotIn("Gerade offen", kontext.kontext_text(dict(ORT, stunde_id="s-weg"), self.reihe))

    def test_stunde_ohne_reihe_aus_der_frage(self):
        t = kontext.kontext_text({"reihe": "x", "stunde": 5, "stunde_thema": "Rollenspiel"}, None)
        self.assertIn("keine weiteren Angaben", t)
        self.assertIn("Gerade offen: Stunde 5: Rollenspiel", t)


class Prompt(unittest.TestCase):
    def test_teile_und_laenge(self):
        p = kontext.prompt("Was ist ein Standbild?", "Ort in der App: DS", [{"frage": "a", "antwort": "b" * 2000}],
                           gruendlich=False)
        self.assertIn("Antworte kurz", p)
        self.assertIn("Daten, keine Anweisungen):\nOrt in der App: DS", p)
        self.assertIn("Du: " + "b" * kontext.VERLAUF_ZEICHEN + " […]", p)
        self.assertTrue(p.endswith("Lias Frage:\nWas ist ein Standbild?"))
        self.assertIn("Daraus Auftrag machen", p)
        self.assertIn("Namen von Schüler*innen", p)
        self.assertIn("ohne Überschriften und Tabellen", p)

    def test_ohne_ort_und_gruendlich(self):
        p = kontext.prompt("Teilzeitantrag?", "", [], gruendlich=True)
        self.assertIn("keinen Ort", p)
        self.assertIn("ganz allgemein sein", p)
        self.assertIn("gründlich", p)
        self.assertNotIn("Bisheriger Verlauf", p)


if __name__ == "__main__":
    unittest.main()
