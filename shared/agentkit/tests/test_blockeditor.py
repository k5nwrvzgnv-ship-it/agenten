"""Tests für agentkit.blockeditor (Strukturplan Abschnitt 10: Regeln 16 und 17, Grundlage für 9, 10, 18, 19).

Vorlage: daten/reihen_echt.toml (eingefrorene Kopie der echten reihen.toml im neuen Format).
"""

import tomllib
import unittest
from pathlib import Path

from agentkit import blockeditor as be

DATEN = Path(__file__).parent / "daten"
ECHT = (DATEN / "reihen_echt.toml").read_text(encoding="utf-8")
LG = '# Platzhalter\n\n"ethik-8" = """Platzhalter für die Lerngruppe"""\n\n"darstellendes-spiel-kurs-12" = "Kurs"\n'


def entfernt_und_dazu(alt: str, neu: str) -> tuple[list[str], list[str]]:
    import difflib
    zeilen = list(difflib.unified_diff(alt.splitlines(), neu.splitlines(), n=0, lineterm=""))
    return ([z[1:] for z in zeilen if z.startswith("-") and not z.startswith("---")],
            [z[1:] for z in zeilen if z.startswith("+") and not z.startswith("+++")])


class TestLesen(unittest.TestCase):
    def test_regel17_rundlauf_byte_gleich(self):
        for name in ("reihen_echt.toml", "reihen_neu.toml", "reihen_alt.toml"):
            text = (DATEN / name).read_text(encoding="utf-8")
            with self.subTest(name):
                dok = be.lesen(text)
                self.assertEqual(dok.text(), text)
                self.assertEqual(dok.daten(), tomllib.loads(text))
                self.assertEqual(be.pruefen(dok), text)

    def test_bloecke_und_kommentare(self):
        dok = be.lesen(ECHT)
        self.assertEqual([b.art for b in dok.bloecke[:3]], ["fach", "fach", "klasse"])
        k8 = dok.block("ethik-8")
        self.assertEqual(k8.vor, ["\n", "# Lias Klasse 7 aus 2025/26 ist jetzt ihre Klasse 8.\n"])
        self.assertEqual(dok.block("ethik-8-straftheorien").wert("stand"), "geplant")
        self.assertEqual([k for k, _ in dok.einheiten()][:3], [be.KOPF_EINHEIT, "ethik", "darstellendes-spiel"])
        self.assertEqual("".join(v for _, v in dok.einheiten()), ECHT)

    def test_unterblock_gehoert_zur_gruppe(self):
        text = ECHT + '\n[[reihe.stunde]]\nid = "s-a"\nthema = "A"\n\n[[reihe.stunde]]\nid = "s-b"\n'
        dok = be.lesen(text)
        i = dok.index("darstellendes-spiel-kurs-11-2025-26-proben-und-feedback")
        self.assertEqual(len(dok.gruppe(i)), 3)
        self.assertEqual([b.wert("id") for b in dok.unter("darstellendes-spiel-kurs-11-2025-26-proben-und-feedback")],
                         ["s-a", "s-b"])

    def test_regel16_unbekannte_konstrukte_werden_abgelehnt(self):
        faelle = {
            "Inline-Tabelle": ECHT + 'x = {a = 1}\n',
            "Liste mit Inline-Tabelle": ECHT + 'x = [{a = 1}]\n',
            "gepunkteter Schlüssel": ECHT + 'a.b = 1\n',
            "Schlüssel in Anführungszeichen": ECHT + '"titel2" = "x"\n',
            "unbekannte Tabelle": ECHT + '\n[reihe]\nid = "x"\n',
            "unbekannte Unter-Tabelle": ECHT + '\n[[reihe.material]]\nid = "x"\n',
            "Eintrag vor der ersten Tabelle": 'titel = "x"\n' + ECHT,
            "Stundenplan nicht hinter seiner Klasse": ECHT + '\n[[klasse.zeitplan]]\ntag = "Di"\n',
            "Stunde vor der ersten Reihe": '[[reihe.stunde]]\nid = "s-x"\n' + ECHT,
            "kaputtes TOML": ECHT + 'titel = "offen\n',
        }
        for name, text in faelle.items():
            with self.subTest(name), self.assertRaises(be.EditorFehler):
                be.lesen(text)

    def test_lerngruppen_nur_eintraege(self):
        dok = be.lesen(LG, kopf_eintraege=True)
        self.assertEqual(dok.text(), LG)
        self.assertEqual(dok.daten(), {"ethik-8": "Platzhalter für die Lerngruppe", "darstellendes-spiel-kurs-12": "Kurs"})
        with self.assertRaises(be.EditorFehler):
            be.lesen(LG + "\n[[fach]]\n", kopf_eintraege=True)


class TestSchreiben(unittest.TestCase):
    def test_zeile_ersetzen_einfuegen_entfernen(self):
        dok = be.lesen(ECHT)
        b = dok.block("ethik-7-freundschaft")
        self.assertTrue(b.setzen("titel", "Gute Freunde"))
        self.assertTrue(b.setzen("archiviert", "2026-11-03", ("id", "titel", "archiviert")))
        self.assertTrue(b.entfernen("notizen"))
        weg, dazu = entfernt_und_dazu(ECHT, be.pruefen(dok))
        self.assertEqual(weg, ['titel = "Freundschaft"',
                               'notizen = "Mit Operatorentraining (Ordner „Reihe Freundschaft + Operatoren“)."'])
        self.assertEqual(dazu, ['titel = "Gute Freunde"', 'archiviert = "2026-11-03"'])

    def test_neue_zeile_an_der_stelle_der_ordnung(self):
        dok = be.lesen(ECHT)
        b = dok.block("darstellendes-spiel-kurs-12-der-nackte-wahnsinn")
        b.setzen("stand", "laufend", ("id", "klasse", "titel", "reihenfrage", "stand", "agenten"))
        self.assertEqual([t.schluessel for t in b.teile if isinstance(t, be.Eintrag)],
                         ["id", "klasse", "titel", "stand", "agenten"])

    def test_gleicher_wert_laesst_jans_umbruch_stehen(self):
        dok = be.lesen(ECHT)
        b = dok.block("ethik-8-straftheorien")
        self.assertFalse(b.setzen("notizen", b.wert("notizen")))
        self.assertEqual(be.pruefen(dok), ECHT)

    def test_werte_im_stil_der_datei(self):
        self.assertEqual(be.wert_zeilen("titel", "Würde"), ['titel = "Würde"\n'])
        self.assertEqual(be.wert_zeilen("stunde", 3), ["stunde = 3\n"])
        self.assertEqual(be.wert_zeilen("agenten", ["theater"]), ['agenten = ["theater"]\n'])
        lang = be.wert_zeilen("notizen", "Wort " * 60)
        self.assertGreater(len(lang), 2)
        self.assertTrue(lang[0].startswith('notizen = """Wort '))
        self.assertTrue(all(z.endswith(" \\\n") for z in lang[:-1]))  # Leerzeichen vor dem \ wie bei Jan
        self.assertTrue(all(len(z.rstrip("\n")) <= be.BREITE for z in lang[:-1]))
        liste = be.wert_zeilen("merksaetze", ["Satz " * 20, "kurz"])
        self.assertEqual((liste[0], liste[-1], liste[-2]), ("merksaetze = [\n", "]\n", '    "kurz",\n'))

    def test_schwierige_texte_kommen_unveraendert_zurueck(self):
        texte = ['Zitat "so" und \\ Strich', 'endet auf "', 'drei """ Anführungszeichen', "\nbeginnt mit Umbruch",
                 "zwei\nAbsätze\n\nund Leerzeile", "Tab\tund \x07 Steuerzeichen", "lang " * 50 + '"Ende"',
                 "einwortohneleerzeichen" * 10, "  Leerzeichen  am Rand  ", "Ende mit Umbruch\n"]
        for t in texte:
            for lang in (False, True):
                with self.subTest(t=t, lang=lang):
                    zeilen = be.wert_zeilen("x", t, lang=lang)
                    self.assertEqual(tomllib.loads("".join(zeilen))["x"], t)
                    zeilen = be.wert_zeilen("x", [t, "b"])
                    self.assertEqual(tomllib.loads("".join(zeilen))["x"], [t, "b"])

    def test_block_einfuegen_und_herausnehmen(self):
        dok = be.lesen(ECHT)
        dok.einfuegen(len(dok.bloecke), [be.neuer_block("reihe", [("id", "neu"), ("klasse", "ethik-8"),
                                                                  ("titel", "Neu"), ("notizen", "")])])
        neu = be.pruefen(dok)
        self.assertEqual(neu, ECHT + '\n[[reihe]]\nid = "neu"\nklasse = "ethik-8"\ntitel = "Neu"\n')
        dok.herausnehmen(dok.gruppe(dok.index("neu")))
        self.assertEqual(be.pruefen(dok), ECHT)

    def test_anhaengen_an_datei_ohne_letzten_zeilenumbruch(self):
        dok = be.lesen(ECHT.rstrip("\n"))
        dok.einfuegen(len(dok.bloecke), [be.neuer_block("fach", [("id", "neu"), ("name", "Neu")])])
        self.assertTrue(be.pruefen(dok).endswith('stand = "abgeschlossen"\n\n[[fach]]\nid = "neu"\nname = "Neu"\n'))

    def test_falsches_ergebnis_bricht_ab(self):
        dok = be.lesen(ECHT)
        dok.block("ethik").teile[1].wert = "Anders"  # Wert und Zeilen passen nicht mehr zusammen
        with self.assertRaises(be.EditorFehler):
            be.pruefen(dok)

    def test_lerngruppen_setzen_und_entfernen(self):
        dok = be.lesen(LG, kopf_eintraege=True)
        dok.kopf_setzen("ethik-8", "Neuer Text")
        dok.kopf_setzen("ethik-9", "Andere Gruppe")
        text = be.pruefen(dok)
        self.assertEqual(tomllib.loads(text), {"ethik-8": "Neuer Text", "darstellendes-spiel-kurs-12": "Kurs",
                                               "ethik-9": "Andere Gruppe"})
        self.assertIn('\n\n"ethik-9" = """Andere Gruppe"""\n', text)
        dok.kopf_entfernen("ethik-9")
        dok.kopf_entfernen("darstellendes-spiel-kurs-12")
        self.assertEqual(be.pruefen(dok), '# Platzhalter\n\n"ethik-8" = """Neuer Text"""\n')


class TestGegen(unittest.TestCase):
    def aendern(self, text: str, kennung: str, titel: str) -> str:
        dok = be.lesen(text)
        dok.block(kennung).setzen("titel", titel)
        return be.pruefen(dok)

    def test_zurueck_byte_gleich(self):
        neu = self.aendern(ECHT, "ethik-8-helfen", "Hilfe")
        g = be.gegen(ECHT, neu)
        self.assertEqual(g["betroffen"], ["ethik-8-helfen"])
        self.assertEqual(be.zurueck(g, neu), ECHT)

    def test_verschobener_und_geloeschter_block_kommt_an_seine_stelle(self):
        dok = be.lesen(ECHT)
        bloecke = dok.herausnehmen(dok.gruppe(dok.index("ethik-8-helfen")))
        dok.einfuegen(len(dok.bloecke), bloecke)
        dok.herausnehmen(dok.gruppe(dok.index("darstellendes-spiel-kurs-11")))
        neu = be.pruefen(dok)
        g = be.gegen(ECHT, neu)
        self.assertEqual(sorted(g["betroffen"]), ["darstellendes-spiel-kurs-11", "ethik-8-helfen"])
        self.assertIn("# Jan 30.10.2026: neuer Kurs 11", g["vorher"]["darstellendes-spiel-kurs-11"])  # mit Kommentar
        self.assertEqual(be.zurueck(g, neu), ECHT)

    def test_andere_aenderungen_bleiben(self):
        neu = self.aendern(ECHT, "ethik-8-helfen", "Hilfe")
        g = be.gegen(ECHT, neu)
        jan = self.aendern(neu, "ethik-7-freundschaft", "Freunde")
        self.assertEqual(be.zurueck(g, jan), self.aendern(ECHT, "ethik-7-freundschaft", "Freunde"))

    def test_konflikt_wenn_der_block_geaendert_wurde(self):
        neu = self.aendern(ECHT, "ethik-8-helfen", "Hilfe")
        g = be.gegen(ECHT, neu)
        jan = self.aendern(neu, "ethik-8-helfen", "Helfen!")
        with self.assertRaises(be.EditorKonflikt) as e:
            be.zurueck(g, jan)
        self.assertEqual(e.exception.einheiten, ["ethik-8-helfen"])

    def test_lerngruppen(self):
        dok = be.lesen(LG, kopf_eintraege=True)
        dok.kopf_entfernen("ethik-8")
        neu = be.pruefen(dok)
        g = be.gegen(LG, neu, kopf_eintraege=True)
        self.assertEqual(be.zurueck(g, neu, kopf_eintraege=True), LG)


if __name__ == "__main__":
    unittest.main()
