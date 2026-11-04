import unittest

import app  # noqa: F401  (setzt den Pfad zu uni/lernmodell.py)
import bewertung

from tests.hilfe import RUBRIK, TRANSKRIPT

PLAN = {"modul": "HSS", "pruefung": {"form": "Vortrag"}, "themen": [
    {"id": "faeule", "titel": "Fäule", "teil": "IHS", "score": 5, "lernziele": [{"text": "Ziel"}], "quellen": ["SHB 01 S. 3"]},
    {"id": "pilze", "titel": "Pilze", "teil": "IHS", "score": 4, "lernziele": [], "quellen": []}]}
KARTEN = [{"id": "faeule-1", "thema": "faeule", "typ": "text", "frage": "Was ist Braunfäule?", "antwort": "Würfelbruch", "quelle": "SHB 02 S. 9"},
          {"id": "pilze-1", "thema": "pilze", "typ": "bild", "frage": "Was ist das?", "antwort": "Hausschwamm\nStränge", "quelle": "Infokarte S. 1"}]
GUT = "bauen die Pilze vor allem die Zellulose ab"


def antwort(**aendern):
    return {"gesamt": "Geht so.", "punkte": [
        {"id": "r1", "stufe": "teilweise", "begruendung": "Teils.", "zitate": [GUT]},
        {"id": "r2", "stufe": "nicht_geprueft", "begruendung": "Kein Vortrag.", "zitate": []}],
        "luecken": [{"thema": "faeule", "was": "Weißfäule fehlt", "zitat": "Das weiß ich gerade nicht mehr"}],
        "karten_neu": [{"thema": "faeule", "frage": "Was baut Weißfäule ab?", "antwort": "Auch Lignin", "quelle": "SHB 01 S. 3", "warum": "Lücke"}],
        "karten_faellig": [{"karte": "faeule-1", "warum": "Lücke"}], **aendern}


def pruefen(roh):
    return bewertung.pruefen(roh, RUBRIK, PLAN, KARTEN, TRANSKRIPT)


class Zitate(unittest.TestCase):
    def test_woertlich_gefunden(self):
        self.assertTrue(bewertung.zitat_belegt(GUT, TRANSKRIPT))

    def test_ueber_zeilenumbruch_und_mehrfachen_leerraum(self):
        self.assertTrue(bewertung.zitat_belegt("das Holz zerfällt  dann in Würfel", TRANSKRIPT))

    def test_typografische_zeichen_zaehlen_gleich(self):
        self.assertTrue(bewertung.zitat_belegt("sagte „hier“ – und ging", 'sagte "hier" - und ging weiter'))
        self.assertTrue(bewertung.zitat_belegt("Zelle mit Wand und Lumen", "Zelle mit Wand und Lumen"))

    def test_umformuliert_nicht_gefunden(self):
        for falsch in ("bauen die Pilze hauptsächlich die Zellulose ab", "bauen die Pilze ... die Zellulose ab",
                       "BAUEN DIE PILZE VOR ALLEM DIE ZELLULOSE AB", "erfunden und nie gesagt worden"):
            self.assertFalse(bewertung.zitat_belegt(falsch, TRANSKRIPT), falsch)

    def test_zu_kurz_oder_leer_belegt_nichts(self):
        for falsch in ("Prüfling", "Und", "", "   ", None):
            self.assertFalse(bewertung.zitat_belegt(falsch, TRANSKRIPT), falsch)


class AntwortLesen(unittest.TestCase):
    def test_mit_codeblock(self):
        self.assertEqual(bewertung.antwort_lesen('Hier:\n```json\n{"a": 1}\n```'), {"a": 1})

    def test_kein_json(self):
        for text in ("kein json", "", None, "{kaputt}", "[1, 2]"):
            self.assertIsNone(bewertung.antwort_lesen(text), text)


class Pruefen(unittest.TestCase):
    def test_gute_antwort(self):
        ergebnis, harte, weiche = pruefen(antwort())
        self.assertEqual((harte, weiche), ([], []))
        self.assertEqual([p["stufe"] for p in ergebnis["punkte"]], ["teilweise", "nicht_geprueft"])
        self.assertEqual(ergebnis["punkte"][0]["titel"], "Fäule erklären")  # aus der Rubrik, nicht von Claude
        self.assertTrue(ergebnis["punkte"][0]["zitate"][0]["belegt"])
        self.assertEqual(len(ergebnis["karten_neu"]), 1)

    def test_kein_json_ist_hart(self):
        self.assertEqual(pruefen(None)[:2], (None, ["Die Antwort ist kein lesbares JSON-Objekt"]))

    def test_erfundenes_zitat_macht_den_punkt_unbelegt(self):
        roh = antwort()
        roh["punkte"][0] = {"id": "r1", "stufe": "erfuellt", "begruendung": "Super.", "zitate": ["Das hat Jan nie so gesagt, wirklich nicht"]}
        ergebnis, harte, weiche = pruefen(roh)
        self.assertEqual(harte, [])
        punkt = ergebnis["punkte"][0]
        self.assertEqual((punkt["stufe"], punkt["stufe_genannt"]), ("unbelegt", "erfuellt"))
        self.assertFalse(punkt["zitate"][0]["belegt"])
        self.assertTrue(any("nicht wörtlich" in f for f in weiche))

    def test_ein_echtes_zitat_reicht_das_falsche_bleibt_markiert(self):
        roh = antwort()
        roh["punkte"][0]["zitate"] = [GUT, "Das hat Jan nie so gesagt, wirklich nicht"]
        ergebnis, _, weiche = pruefen(roh)
        self.assertEqual(ergebnis["punkte"][0]["stufe"], "teilweise")
        self.assertEqual([z["belegt"] for z in ergebnis["punkte"][0]["zitate"]], [True, False])
        self.assertEqual(len(weiche), 1)

    def test_stufe_ohne_zitat_ist_unbelegt(self):
        roh = antwort()
        roh["punkte"][0]["zitate"] = []
        ergebnis, _, weiche = pruefen(roh)
        self.assertEqual(ergebnis["punkte"][0]["stufe"], "unbelegt")
        self.assertIn("braucht ein Zitat", weiche[0])

    def test_claude_kann_unbelegt_nicht_selbst_setzen(self):
        roh = antwort()
        roh["punkte"][0]["stufe"] = "unbelegt"
        self.assertIsNone(pruefen(roh)[0])

    def test_fehlender_doppelter_fremder_punkt(self):
        roh = antwort()
        roh["punkte"].pop()
        self.assertIn("Punkt r2 fehlt", pruefen(roh)[1])
        roh = antwort()
        roh["punkte"].append({"id": "x9", "stufe": "erfuellt", "begruendung": "b", "zitate": []})
        self.assertIn("Punkt x9 steht nicht in der Rubrik", pruefen(roh)[1])
        roh = antwort()
        roh["punkte"].append(dict(roh["punkte"][0]))
        self.assertIn("Punkt r1 steht doppelt da", pruefen(roh)[1])

    def test_luecke_mit_falschem_thema_oder_zitat(self):
        roh = antwort(luecken=[{"thema": "erfunden", "was": "x", "zitat": ""},
                               {"thema": "faeule", "was": "y", "zitat": "gar nicht gesagt, kein Wort davon"}])
        ergebnis, _, weiche = pruefen(roh)
        self.assertEqual(ergebnis["luecken"], [{"thema": "faeule", "was": "y", "zitat": ""}])
        self.assertEqual(len(weiche), 2)

    def test_karte_nur_mit_fundstelle_aus_der_wissensbasis(self):
        erfunden = {"thema": "faeule", "frage": "Neu?", "antwort": "Ja", "quelle": "DIN 99999 Abschnitt 7"}
        gut = {"thema": "faeule", "frage": "Neu2?", "antwort": "Ja", "quelle": "SHB 02 S. 9"}
        ergebnis, _, weiche = pruefen(antwort(karten_neu=[erfunden, gut]))
        self.assertEqual([k["frage"] for k in ergebnis["karten_neu"]], ["Neu2?"])
        self.assertIn("Fundstelle", weiche[0])

    def test_einzelne_stelle_einer_angabe_zaehlt(self):
        karten = KARTEN + [{"id": "x", "thema": "pilze", "frage": "Y?", "antwort": "a", "quelle": "Infokarten S. 1; SHB_01 S. 19, 22"}]
        stellen = bewertung.fundstellen_sammeln(karten, PLAN)
        for gut in ("SHB_01 S. 19", "SHB_01 S. 22", "SHB_01 S. 19, 22", "Infokarten S. 1", "Infokarten S. 1; SHB_01 S. 22",
                    "Infokarten S. 1; SHB_01 S. 19, 22", "SHB 01 S. 3"):
            self.assertTrue(bewertung.fundstelle_belegt(gut, stellen), gut)
        for falsch in ("SHB_01 S. 20", "SHB_01 S. 19; DIN 99999", "SHB_01", "", ";", "Infokarten S. 2"):
            self.assertFalse(bewertung.fundstelle_belegt(falsch, stellen), falsch)

    def test_karte_die_es_schon_gibt_wird_verworfen(self):
        doppelt = {"thema": "faeule", "frage": "was ist braunfäule?", "antwort": "x", "quelle": "SHB 02 S. 9"}
        self.assertEqual(pruefen(antwort(karten_neu=[doppelt]))[0]["karten_neu"], [])

    def test_faellige_karte_muss_es_geben(self):
        ergebnis, _, weiche = pruefen(antwort(karten_faellig=[{"karte": "gibt-es-nicht"}, {"karte": "pilze-1"}, {"karte": "pilze-1"}]))
        self.assertEqual([k["karte"] for k in ergebnis["karten_faellig"]], ["pilze-1"])
        self.assertEqual(len(weiche), 1)

    def test_id_mit_klammern_wie_in_der_wissensbasis(self):
        ergebnis, _, weiche = pruefen(antwort(karten_faellig=[{"karte": "[pilze-1]"}]))
        self.assertEqual((ergebnis["karten_faellig"][0]["karte"], weiche), ("pilze-1", []))

    def test_mengengrenzen(self):
        viele = [{"thema": "faeule", "frage": f"F{i}?", "antwort": "a", "quelle": "SHB 02 S. 9"} for i in range(50)]
        self.assertEqual(len(pruefen(antwort(karten_neu=viele))[0]["karten_neu"]), bewertung.MAX_NEUE_KARTEN)


class Prompt(unittest.TestCase):
    def test_enthaelt_alles_noetige(self):
        p = bewertung.prompt_bauen(RUBRIK, PLAN, KARTEN, TRANSKRIPT, "- Keine Hinweise zu Terminen")
        for teil in (GUT.split()[0], "r1", "Erklärt Fäule.", "[faeule-1]", "Thema-ID pilze", "SHB 02 S. 9", "Keine Hinweise zu Terminen", "<transkript>"):
            self.assertIn(teil, p)
        self.assertIn("Merkmale: Hausschwamm", p)  # Bildkarte ohne Foto
        self.assertLess(p.index("Thema-ID faeule"), p.index("Thema-ID pilze"))  # wichtigste zuerst

    def test_grenze_fuer_das_programmargument(self):
        self.assertLess(bewertung.MAX_PROMPT_BYTES, 128 * 1024)
        with self.assertRaises(bewertung.PromptZuGross):
            bewertung.prompt_bauen(RUBRIK, PLAN, KARTEN, "ä" * 70_000)

    def test_umlaute_zaehlen_als_bytes(self):
        erlaubt = bewertung.prompt_bauen(RUBRIK, PLAN, KARTEN, "a" * 60_000)
        self.assertLess(len(erlaubt.encode()), bewertung.MAX_PROMPT_BYTES)


if __name__ == "__main__":
    unittest.main()
