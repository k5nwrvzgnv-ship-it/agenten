import json
import shutil
import tempfile
import unittest
from pathlib import Path

import faelle
import renderer
from tests.test_webpruefung import DOMAINS, seitentext

HIER = Path(__file__).resolve().parent.parent


def kandidat(titel="Fahrraddieb", url="https://taz.de/fall", zitat="stahl drei Fahrräder", **mehr):
    k = {"titel": titel, "fall": "Ein Mann stahl drei Fahrräder.", "quelle_art": "reportage",
         "belege": [{"url": url, "zitat": zitat}], "lebenswelt": "Fahrräder kennt jeder.",
         "strafzweck": "Vergeltung oder Besserung", "gewalt": False}
    k.update(mehr)
    return k


def auswahl(fid="F01", **mehr):
    a = {"id": fid, "kurztitel": "Fahrraddieb", "warum": "stark", "achten": "nichts"}
    a.update(mehr)
    return a


def bewertung(stufe="stark", regeln=("L1",)):
    return {"stufe": stufe, "begruendung": "konkret", "regeln": list(regeln)}


def abgleich_eintrag(fid, gesamt="stark", **kr):
    return {"id": fid, "kriterien": {k: kr.get(k, bewertung()) for k in faelle.KRITERIEN}, "gefaehrdet": [],
            "gesamt": gesamt}


def leitfrage(**mehr):
    q = {"frage": "Muss jeder Dieb ins Gefängnis?", "pole": ["Ja, weil", "Nein, damit"], "faelle": ["F01"],
         "einstieg": "Der Fahrraddieb zeigt es.", "kant": "Ja.", "liszt": "Kommt auf den Täter an.",
         "belege_register": ["liszt:41"], "rlp": ["strafe"], "regeln": ["P3"]}
    q.update(mehr)
    return q


class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def datei(self, name, daten):
        p = self.tmp / name
        p.write_text(json.dumps(daten) if not isinstance(daten, str) else daten, encoding="utf-8")
        return p


class KontextTest(unittest.TestCase):
    def test_regeln_mit_folgezeilen(self):
        text = "## L\n\n- L1 Erste Regel,\n  geht weiter.\n- L2 Zweite.\nkein Punkt\n  - eingerückt\n- x klein\n"
        self.assertEqual(faelle.regeln_aus_regelwerk(text), {"L1": "Erste Regel, geht weiter.", "L2": "Zweite."})

    def test_echtes_regelwerk_lesbar(self):
        regeln = faelle.regeln_aus_regelwerk((HIER / "regelwerk_reihe.md").read_text(encoding="utf-8"))
        for k in ("L1", "L7", "P1", "P7", "F1", "F8", "R1", "R6", "K1", "K11", "G1", "G2"):
            self.assertIn(k, regeln)
        self.assertIn("Containern", regeln["L3"])
        self.assertNotIn("##", " ".join(regeln.values()))

    def test_gelernte_regeln_nummeriert(self):
        text = "# S\n## Gelernte Regeln\n- 23.10.: Eins\n- 24.10.: Zwei\n## Danach\n- nicht\n"
        self.assertEqual(faelle.gelernte_regeln(text), {"GR1": "23.10.: Eins", "GR2": "24.10.: Zwei"})
        self.assertEqual(faelle.gelernte_regeln("## Gelernte Regeln\n- (noch keine)\n"), {})

    def test_rlp_stellen(self):
        toml = '[[stelle]]\nid = "a"\nseite = 1\nabschnitt = "3.3"\ntext = "Strafe"\n'
        self.assertEqual(faelle.rlp_stellen(toml), {"a": "3.3: Strafe"})

    def test_sammel_prompt_enthaelt_fenster_regeln_domains(self):
        k = {"reihe": "Klasse 8", "regelwerk": "- L3 Containern meiden", "gelernte": {"GR1": "keine Tötung"}}
        p = faelle.sammel_prompt("popkultur", k, ["taz.de"], "data/x.json")
        for teil in ("Deutschrap", "L3 Containern", "GR1: keine Tötung", "taz.de", "NUR in die Datei data/x.json",
                     "Es müssen keine Philosophen sein"):
            self.assertIn(teil, p)


class SammelnTest(Temp):
    def test_gueltige_und_ungueltige_kandidaten(self):
        p = self.datei("s.json", {"kandidaten": [kandidat(), kandidat(titel="", quelle_art="tiktok"),
                                                 kandidat(fall="x" * 801, belege=[])],
                                  "verworfen": [{"titel": "Containern", "grund": "L3", "regeln": ["L3"]}, "kaputt"],
                                  "luecken": ["kein Video", ""]})
        daten, fehler = faelle.sammeln_lesen(p)
        self.assertEqual(len(daten["kandidaten"]), 1)
        self.assertEqual(len(daten["verworfen"]), 1)
        self.assertEqual(daten["luecken"], ["kein Video"])
        self.assertEqual(len(fehler), 2)
        self.assertIn("titel fehlt", fehler[0])
        self.assertIn("quelle_art", fehler[0])
        self.assertIn("länger als 800", fehler[1])
        self.assertIn("mindestens ein Beleg", fehler[1])

    def test_ohne_datei_oder_ohne_kandidaten(self):
        with self.assertRaises(faelle.FallFehler):
            faelle.sammeln_lesen(self.tmp / "fehlt.json")
        with self.assertRaises(faelle.FallFehler):
            faelle.sammeln_lesen(self.datei("s.json", {"luecken": []}))

    def test_belege_status(self):
        daten = {"kandidaten": [kandidat(), kandidat(url="https://instagram.com/p/1"),
                                kandidat(zitat="stahl vier Räder")]}
        faelle.belege_pruefen(daten, DOMAINS, seitentext)
        self.assertEqual([k["status"] for k in daten["kandidaten"]], ["belegt", "ungeprueft", "nicht_belegt"])
        liste = faelle.durchgefallene(daten)
        self.assertEqual(len(liste), 1)
        self.assertIn("stahl vier Räder", liste[0])

    def test_unlesbare_adresse_faellt_durch_statt_abzustuerzen(self):
        def kaputt(url):
            raise UnicodeEncodeError("ascii", "ü", 0, 1, "ordinal not in range")
        daten = faelle.belege_pruefen({"kandidaten": [kandidat()]}, DOMAINS, kaputt)
        self.assertEqual(daten["kandidaten"][0]["status"], "nicht_belegt")
        self.assertIn("Seite nicht ladbar", daten["kandidaten"][0]["belege"][0]["pruefung"]["vermerk"])

    def test_zusammenfuehren_vereint_doppelte(self):
        a = {"kandidaten": [dict(kandidat(), status="ungeprueft"), dict(kandidat(titel="Weg"), status="nicht_belegt")],
             "verworfen": [{"titel": "Containern", "grund": "L3"}], "luecken": ["nichts"]}
        b = {"kandidaten": [dict(kandidat(titel="Anderer Titel", url="https://www.taz.de/fall/"), status="belegt"),
                            dict(kandidat(titel="Zweiter", url="https://taz.de/zwei"), status="belegt")],
             "verworfen": [], "luecken": []}
        ges = faelle.zusammenfuehren({"nachrichten": a, "urteile": b})
        self.assertEqual([f["id"] for f in ges["faelle"]], ["F01", "F02"])
        self.assertEqual(ges["faelle"][0]["fenster"], ["nachrichten", "urteile"])
        self.assertEqual(ges["faelle"][0]["status"], "belegt")
        self.assertEqual(len(ges["faelle"][0]["belege"]), 1)  # gleiche URL nicht doppelt
        self.assertEqual(ges["nicht_belegt"][0]["titel"], "Weg")
        self.assertEqual(ges["verworfen"][0]["fenster"], "nachrichten")
        self.assertTrue(ges["luecken"][0].startswith("Reportagen"))
        self.assertNotIn("_urls", ges["faelle"][0])


class AbgleichTest(Temp):
    def test_gueltig_fehlend_doppelt_unbekannt(self):
        p = self.datei("a.json", {"faelle": [
            abgleich_eintrag("F01"),
            abgleich_eintrag("F01"),
            abgleich_eintrag("F02", lebenswelt=bewertung(regeln=["X9"])),
            abgleich_eintrag("F09"),
            {"id": "F03", "kriterien": {"lebenswelt": bewertung("super")}, "gesamt": "gut"}]})
        gut, fehler = faelle.abgleich_lesen(p, ["F01", "F02", "F03", "F04"], {"L1", "GR1"})
        self.assertEqual(list(gut), ["F01"])
        text = " | ".join(fehler)
        for teil in ("F01 doppelt", "unbekannte Kennungen ['X9']", "unbekannte id 'F09'", "lebenswelt.stufe",
                     "passung fehlt", "gesamt muss", "F04: fehlt"):
            self.assertIn(teil, text)

    def test_begruendung_zu_lang(self):
        p = self.datei("a.json", {"faelle": [abgleich_eintrag("F01", passung={"stufe": "stark",
                                                                             "begruendung": "x" * 601,
                                                                             "regeln": ["L1"]})]})
        gut, fehler = faelle.abgleich_lesen(p, ["F01"], {"L1"})
        self.assertEqual(gut, {})
        self.assertIn("passung.begruendung", fehler[0])


class DossierTest(Temp):
    ABGLEICH = {"F01": abgleich_eintrag("F01"), "F02": abgleich_eintrag("F02", gesamt="mittel")}

    def lesen(self, daten, fallbezug=frozenset({"Pollux", "Neukölln"})):
        return faelle.dossier_lesen(self.datei("d.json", daten), self.ABGLEICH, {"P3", "L1"}, {"strafe"},
                                    {"liszt:41"}, verworfen={"V01": {"titel": "Containern"}}, fallbezug=fallbezug)

    def test_gueltig(self):
        d, fehler = self.lesen({"auswahl": [auswahl()], "leitfragen": [leitfrage()],
                                "auch_interessant": [{"ref": "F02", "warum": "nah"}, {"ref": "V01", "warum": "x"}],
                                "rueckfragen": ["Schulform?", "Mit (L3)?"]})
        self.assertEqual(fehler, [])
        self.assertEqual(len(d["leitfragen"]), 1)
        self.assertEqual([x["ref"] for x in d["auch_interessant"]], ["F02", "V01"])
        self.assertEqual(d["rueckfragen"], ["Schulform?"])  # Kennungen fliegen raus

    def test_reihenfrage_muss_allgemein_sein(self):
        d, fehler = self.lesen({"auswahl": [auswahl()], "leitfragen": [
            leitfrage(frage="Pollux saß 13 Jahre: War die Strafe richtig?"),
            leitfrage(frage="Muss der Raketenschütze aus Neukölln bestraft werden?"),
            leitfrage(frage="Soll eine Strafe den Täter bessern oder vergelten, was er getan hat?" + "x" * 40),
            leitfrage(frage="Muss eine Strafe sein, wenn das Opfer verzeiht?")]})
        self.assertEqual([q["frage"] for q in d["leitfragen"]], ["Muss eine Strafe sein, wenn das Opfer verzeiht?"])
        text = " | ".join(fehler)
        for teil in ("ohne Pollux", "keine Zahlen", "ohne Neukölln", "länger als 100"):
            self.assertIn(teil, text)

    def test_keine_kennungen_fuer_lia(self):
        d, fehler = self.lesen({"auswahl": [auswahl(warum="erfüllt L2 und GR3")],
                                "leitfragen": [leitfrage(kant="Kant (K1) sagt ja.")]})
        self.assertIn("keine Regel-Kennungen", " ".join(fehler))
        self.assertEqual(d["auswahl"], [])

    def test_fehler_je_leitfrage(self):
        d, fehler = self.lesen({"auswahl": [auswahl(), {"id": "F07", "warum": "x"}],
                                "leitfragen": [leitfrage(), leitfrage(pole=["nur einer"]),
                                               leitfrage(faelle=["F02"]), leitfrage(belege_register=["kant:999"]),
                                               leitfrage(rlp=[]), leitfrage(einstieg="")],
                                "auch_interessant": [{"ref": "F01", "warum": "schon gewählt"}, {"ref": "V09"}]})
        self.assertEqual(len(d["leitfragen"]), 1)
        text = " | ".join(fehler)
        for teil in ("auswahl:", "pole: genau zwei", "faelle: nur ids aus der auswahl", "unbekannt ['kant:999']",
                     "rlp: mindestens", "einstieg fehlt", "'F01' ist kein übriger", "'V09' ist kein übriger"):
            self.assertIn(teil, text)

    def test_leer(self):
        d, fehler = self.lesen({})
        self.assertIn("auswahl ist leer", fehler)
        self.assertIn("keine gültige Leitfrage", fehler)


class FallbezugTest(unittest.TestCase):
    def test_fallwoerter(self):
        fs = [{"titel": "Pollux: 13 Jahre Haft", "fall": "Pollux war Täter in Bayern."},
              {"titel": "Böller in Neukölln", "fall": "Ein Opfer wurde verletzt. Täter war 15."},
              {"titel": "Rakete in Neukölln", "fall": "Das Opfer verzieh. Täter war Influencer."},
              {"titel": "Heide", "fall": "Das Opfer war 13. Täter waren Mädchen."}]
        w = faelle.fallwoerter(fs, "Strafe für Täter, Haft, Gefängnis")
        self.assertTrue({"Pollux", "Bayern", "Neukölln", "Heide", "Influencer"} <= w)
        self.assertNotIn("Opfer", w)  # in drei Fällen: allgemeines Wort
        self.assertNotIn("Haft", w)  # steht im allgemeinen Kontext
        self.assertNotIn("Täter", w)

    def test_reihenfragen_lias(self):
        toml = """[[reihe]]
klasse = "8"
bisherige_reihen = ["Klasse 7, Lüge und Wahrheit: Sollte ich lügen, um einen Freund zu schützen?",
  "Klasse 8, Helfen: Muss ich Fremden genauso helfen? Merksätze (Lia, 24.10.2026): Singer: x", "ohne Frage"]
"""
        self.assertEqual(faelle.reihenfragen_lias(toml), ["Sollte ich lügen, um einen Freund zu schützen?",
                                                          "Muss ich Fremden genauso helfen?"])

    def test_echte_reihenfragen(self):
        fragen = faelle.reihenfragen_lias((HIER.parent / "unterricht/reihen.toml").read_text(encoding="utf-8"))
        self.assertIn("Muss ich fremden Menschen in Not genauso helfen wie Nahestehenden?", fragen)


class BeschreibungTest(Temp):
    def test_renderer_baut_schlankes_dossier(self):
        ges = {"faelle": [dict(kandidat(), id="F01", status="belegt", fenster=["nachrichten"], gewalt=True,
                               belege=[{"url": "https://x.de", "zitat": "z", "pruefung": {"status": "ungeprueft"}},
                                       {"url": "https://taz.de/fall", "zitat": "z",
                                        "pruefung": {"status": "bestanden", "vermerk": ""}}]),
                          dict(kandidat(titel="Zweiter"), id="F02", status="ungeprueft", fenster=["urteile"],
                               belege=[{"url": "https://x.de", "zitat": "z", "pruefung": {"status": "ungeprueft"}}])],
               "verworfen": [{"titel": "Containern", "grund": "interessiert nicht", "regeln": ["L3"]},
                             {"titel": "Abwegig", "grund": "weit weg"}],
               "nicht_belegt": [], "luecken": ["kein Video"]}
        dossier = {"auswahl": [auswahl()], "leitfragen": [leitfrage()],
                   "auch_interessant": [{"ref": "V01", "warum": "Gegenbeispiel"}], "rueckfragen": ["Schulform?"]}
        zahlen = {"fenster": 2, "faelle": 2, "belegt": 1, "ungeprueft": 1, "verworfen": 2, "nicht_belegt": 0}
        b = faelle.beschreibung("Fallsuche", ges, dossier, zahlen)
        text = json.dumps(b, ensure_ascii=False)
        for teil in ("4 reale Fälle", "Reihenfrage 1", "Muss jeder Dieb ins Gefängnis?", "Einstieg (Fahrraddieb)",
                     "Fahrraddieb (mit Gewalt)", "Quelle: https://taz.de/fall", "Containern (beim Suchen aussortiert)",
                     "Offene Fragen an dich"):
            self.assertIn(teil, text)
        for nicht in ("Abwegig", "Zweiter", "kein Video", "L3", "P3", "Bewertungsbogen"):
            self.assertNotIn(nicht, text)
        renderer.bauen(b, self.tmp / "d.docx", vorschau=False)
        self.assertTrue((self.tmp / "d.docx").exists())

if __name__ == "__main__":
    unittest.main()
