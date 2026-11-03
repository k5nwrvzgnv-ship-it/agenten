"""Tests für reihenkontext.py: Reihe nur über agentkit.struktur und ihre id (Strukturplan Bauschritt 2, Regel 22).

Vorlagen: daten/reihen_alt.toml (eingefrorene Kopie der echten reihen.toml, Lerngruppe als Platzhalter) und
daten/reihen_neu.toml (dieselben Daten im neuen Format, mit Stunden). Dazu die echte Datei in lia/instanz, in
welchem Format sie gerade ist. Die Operationen des Plans (Abschnitt 4) gibt es noch nicht (Bauschritt 4); hier
stehen sie als Textänderung so, wie die App sie schreiben wird.
"""

import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

import reihenkontext
from agentkit import struktur

DATEN = Path(__file__).parent / "daten"
ALT = (DATEN / "reihen_alt.toml").read_text(encoding="utf-8")
NEU = (DATEN / "reihen_neu.toml").read_text(encoding="utf-8")
STRAF = "ethik-8-straftheorien"
HELFEN = "Muss ich fremden Menschen in Not genauso helfen wie Nahestehenden?"
FREUND = "Wie erkenne ich einen guten Freund?"


def waehlen(text: str, ort: str | None = None) -> tuple[dict | None, str]:
    return reihenkontext.waehlen(struktur.aus_text(text), ort)


def alt_reihe_text(reihen: list[dict]) -> str:
    """Bisheriges kernstellen.reihe_text (bis 03.11.2026): erste Reihe mit „Straftheorien“ im Titel."""
    for r in reihen:
        if "Straftheorien" in r.get("titel", ""):
            teile = [f"Ethik Klasse {r.get('klasse', '?')}, Reihe {r['titel']}."]
            for feld, name in (("lerngruppe", "Lerngruppe"), ("notizen", "Planung")):
                if r.get(feld):
                    teile.append(f"{name}: {r[feld]}")
            return "\n".join(teile)
    return ""


def alt_reihenfragen(text: str) -> list[str]:
    """Bisheriges faelle.reihenfragen_lias: Regex über bisherige_reihen."""
    fragen = []
    for r in tomllib.loads(text).get("reihe", []):
        for eintrag in r.get("bisherige_reihen", []):
            m = re.search(r":\s*([^:?]+\?)", eintrag)
            if m:
                fragen.append(m.group(1).strip())
    return fragen


class AltesFormat(unittest.TestCase):
    """Die heutige Datei (bis zur Migration): keine Stunden, also keine Prüfungsreihe."""

    def test_ohne_ort_keine_reihe_und_grund(self):
        reihe, grund = waehlen(ALT)
        self.assertIsNone(reihe)
        self.assertIn("keine Reihe mit einer Stunde mit Marke „Prüfung“", grund)
        self.assertIn("--reihe", grund)

    def test_mit_id_prompt_wie_bisher(self):
        reihe, grund = waehlen(ALT, STRAF)
        self.assertEqual(grund, "")
        self.assertEqual(reihenkontext.text(reihe), alt_reihe_text(tomllib.loads(ALT)["reihe"]))
        self.assertTrue(reihenkontext.text(reihe).startswith("Ethik Klasse 8, Reihe Straftheorien (in Planung).\n"))
        self.assertIn("Lerngruppe: Platzhalter", reihenkontext.text(reihe))

    def test_pruefungsstunde_im_alten_format(self):
        text = ALT + '\n[[reihe.stunde]]\nnr = 1\nthema = "Kant"\nmarke = "Prüfung"\n'  # an die letzte Reihe
        letzte = struktur.aus_text(ALT).reihen[-1]["id"]
        self.assertEqual(waehlen(text)[0]["id"], letzte)

    def test_fruehere_reihenfragen(self):
        """Aus Reihenfragen abgeschlossener Reihen und, im alten Format, aus bisherige_reihen; nichts geht
        verloren gegenüber dem bisherigen Regex."""
        s = struktur.aus_text(ALT)
        fragen = reihenkontext.fruehere_reihenfragen(s, s.reihe(STRAF))
        self.assertLessEqual(set(alt_reihenfragen(ALT)), set(fragen))
        self.assertIn(HELFEN, fragen)  # steht nur in bisherige_reihen
        self.assertIn(FREUND, fragen)
        self.assertEqual(len(fragen), len(set(fragen)))
        self.assertEqual(fragen, reihenkontext.fruehere_reihenfragen(s))  # Darstellendes Spiel hat keine

    def test_bisherige_reihen_regex(self):
        text = ('[[reihe]]\nfach = "Ethik"\nklasse = "8"\nbisherige_reihen = ["Klasse 7, Lüge und Wahrheit: '
                'Sollte ich lügen, um einen Freund zu schützen?", "Klasse 8, Helfen: Muss ich Fremden genauso '
                'helfen? Merksätze (Lia, 24.10.2026): Singer: x", "ohne Frage"]\n')
        self.assertEqual(reihenkontext.fruehere_reihenfragen(struktur.aus_text(text)),
                         ["Sollte ich lügen, um einen Freund zu schützen?", "Muss ich Fremden genauso helfen?"])


class NeuesFormat(unittest.TestCase):
    """Nach der Migration: Prüfungsreihe über die Marke, Regel 22 für recherche nach jeder Operation."""

    def assertReihe(self, text: str, kennung: str, ort: str | None = None):
        reihe, grund = waehlen(text, ort)
        self.assertEqual(grund, "")
        self.assertEqual(reihe["id"], kennung)
        return reihe

    def test_pruefungsreihe(self):
        reihe = self.assertReihe(NEU, STRAF)
        self.assertEqual(reihenkontext.text(reihe), "Ethik Klasse 8, Reihe Straftheorien.\n"
                                                    "Planung: Erst Kant (Vergeltung), dann von Liszt als Gegenposition.")

    def test_titel_aendern(self):
        text = NEU.replace('titel = "Straftheorien"', 'titel = "Wozu strafen wir?"')
        reihe = self.assertReihe(text, STRAF)
        self.assertIn("Reihe Wozu strafen wir?.", reihenkontext.text(reihe))

    def test_kopie_mit_gleichem_titel_davor(self):
        """Eine Kopie (neue ids, herkunft, geplant, ohne Marken) vor dem Original: der Titel entscheidet nicht
        mehr (früher nahm kernstellen die erste Reihe mit „Straftheorien“)."""
        kopie = ('[[reihe]]\nid = "ethik-8-straftheorien-2"\nklasse = "ethik-8"\ntitel = "Straftheorien"\n'
                 'stand = "geplant"\nherkunft = "ethik-8-straftheorien"\n\n'
                 '[[reihe.stunde]]\nid = "s-k1"\nthema = "Kant: Vergeltung"\n\n')
        text = NEU.replace('[[reihe]]\nid = "ethik-8-straftheorien"', kopie + '[[reihe]]\nid = "ethik-8-straftheorien"')
        self.assertEqual(struktur.aus_text(text).reihen[0]["id"], "ethik-8-straftheorien-2")
        self.assertReihe(text, STRAF)
        self.assertReihe(text, "ethik-8-straftheorien-2", "ethik-8-straftheorien-2")
        self.assertReihe(text, "ethik-8-straftheorien-2", "s-k1")

    def test_stunde_verschieben(self):
        block = '[[reihe.stunde]]\nid = "s-kant"\nthema = "Kant: Vergeltung"\nmarke = "Prüfung"\n\n'
        text = NEU.replace(block, "").replace('[[reihe.stunde]]\nid = "s-einstieg"', block + '[[reihe.stunde]]\nid = "s-einstieg"')
        self.assertEqual(struktur.aus_text(text).pruefungsstunde(STRAF)["nr"], 1)
        self.assertReihe(text, STRAF)
        self.assertReihe(text, STRAF, "s-kant")

    def test_reihe_in_andere_klasse_verschieben(self):
        text = NEU.replace('[[reihe]]\nid = "ethik-8-straftheorien"\nklasse = "ethik-8"',
                           '[[klasse]]\nid = "ethik-9"\nfach = "ethik"\nname = "9"\n\n'
                           '[[reihe]]\nid = "ethik-8-straftheorien"\nklasse = "ethik-9"')
        reihe = self.assertReihe(text, STRAF)
        self.assertTrue(reihenkontext.text(reihe).startswith("Ethik Klasse 9, Reihe Straftheorien."))

    def test_archivieren_und_wiederherstellen(self):
        zeile = 'stand = "geplant"\n'
        archiviert = NEU.replace(zeile, zeile + 'archiviert = "2026-11-03"\n')
        reihe, grund = waehlen(archiviert)
        self.assertIsNone(reihe)
        self.assertIn("keine Reihe", grund)
        self.assertReihe(archiviert, STRAF, STRAF)  # ausdrücklich angegeben: auch archiviert
        self.assertReihe(NEU, STRAF)  # wiederhergestellt = Zeile weg

    def test_pruefungsstunde_ausblenden(self):
        text = NEU.replace('marke = "Prüfung"\n', 'marke = "Prüfung"\narchiviert = "2026-11-03"\n')
        self.assertIsNone(waehlen(text)[0])

    def test_zwei_pruefungsreihen(self):
        text = NEU + '\n[[reihe.stunde]]\nid = "s-f"\nthema = "Freund"\nmarke = "Prüfung"\n'
        text = text.replace('archiviert = "2026-08-01"\n', "")  # Klasse 7 nicht archiviert
        reihe, grund = waehlen(text)
        self.assertIsNone(reihe)
        self.assertIn("2 Reihen mit Prüfungsstunde (ethik-8-straftheorien, ethik-7-freundschaft)", grund)

    def test_ort_keine_reihe(self):
        self.assertIn("ist ein(e) klasse", waehlen(NEU, "ethik-8")[1])
        self.assertIn("ist ein(e) fach", waehlen(NEU, "ethik")[1])
        self.assertIn("gibt es nicht", waehlen(NEU, "gibt-es-nicht")[1])

    def test_kurs(self):
        reihe = self.assertReihe(NEU, "darstellendes-spiel-kurs-12-der-nackte-wahnsinn",
                                 "darstellendes-spiel-kurs-12-der-nackte-wahnsinn")
        self.assertEqual(reihenkontext.text(reihe), "Darstellendes Spiel Kurs 12, Reihe Der nackte Wahnsinn.")

    def test_fruehere_reihenfragen(self):
        """Abgeschlossene und archivierte Reihen desselben Fachs; bisherige_reihen zählt im neuen Format nicht."""
        text = NEU.replace('titel = "Straftheorien"', 'titel = "Straftheorien"\nbisherige_reihen = ["K7, X: Alt?"]')
        s = struktur.aus_text(text)
        self.assertEqual(reihenkontext.fruehere_reihenfragen(s, s.reihe(STRAF)), [HELFEN, FREUND])
        ds = s.reihe("darstellendes-spiel-kurs-12-der-nackte-wahnsinn")
        self.assertEqual(reihenkontext.fruehere_reihenfragen(s, ds), [])
        self.assertEqual(reihenkontext.fruehere_reihenfragen(None), [])

    def test_woerter(self):
        w = reihenkontext.woerter(struktur.aus_text(NEU))
        for teil in ("Straftheorien", "Kant: Vergeltung", "Alte Idee, ausgeblendet", "Peter Singer", HELFEN):
            self.assertIn(teil, w)


class Laden(unittest.TestCase):
    def setUp(self):
        self.instanz = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.instanz)

    def test_lerngruppe_aus_lerngruppen_toml(self):
        (self.instanz / "reihen.toml").write_text(NEU, encoding="utf-8")
        pfad = self.instanz / "lerngruppen.toml"
        pfad.write_text('"ethik-8" = "unruhig, mag Videos"\n', encoding="utf-8")
        pfad.chmod(0o600)
        s, reihe, grund = reihenkontext.laden(self.instanz)
        self.assertEqual((reihe["id"], grund), (STRAF, ""))
        self.assertIn("\nLerngruppe: unruhig, mag Videos\n", reihenkontext.text(reihe))

    def test_kaputte_datei(self):
        (self.instanz / "reihen.toml").write_text(ALT.replace('fach = "Ethik"', 'fach = ""', 1), encoding="utf-8")
        s, reihe, grund = reihenkontext.laden(self.instanz, STRAF)
        self.assertEqual((s, reihe), (None, None))
        self.assertIn("reihen.toml nicht lesbar", grund)
        self.assertNotIn("Platzhalter", grund)  # nie die Lerngruppe
        self.assertEqual(reihenkontext.text(reihe), "")

    def test_ohne_datei(self):
        s, reihe, grund = reihenkontext.laden(self.instanz)
        self.assertIsNone(reihe)
        self.assertIn("keine Reihe", grund)


class EchteDatei(unittest.TestCase):
    """lia/instanz/reihen.toml, wie sie gerade ist (vor und nach der Migration)."""

    def setUp(self):
        self.s = struktur.laden()

    def test_straftheorien_ueber_id(self):
        reihe, grund = reihenkontext.waehlen(self.s, STRAF)
        self.assertEqual(grund, "")
        self.assertTrue(reihenkontext.text(reihe).startswith("Ethik Klasse 8, Reihe Straftheorien"))

    def test_ohne_ort_eine_pruefungsreihe_oder_grund(self):
        reihe, grund = reihenkontext.waehlen(self.s)
        if reihe is None:
            self.assertTrue(grund)
        else:
            self.assertEqual(len(self.s.pruefungsreihen()), 1)

    def test_fruehere_reihenfragen(self):
        fragen = reihenkontext.fruehere_reihenfragen(self.s, self.s.reihe(STRAF))
        self.assertIn(HELFEN, fragen)
        self.assertIn(FREUND, fragen)


if __name__ == "__main__":
    unittest.main()
