"""Tests für quellen.py und pruefung.py (ohne Netz, ohne agentkit)."""

import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pruefung
import quellen

ZEIT = datetime(2026, 11, 9, 12, 0).astimezone()
ROH = json.dumps({"data": [{"primaryValue": 9487189.307}, {"primaryValue": 69487.488}],
                  "text": "Umsatz 1.234,5 Mio EUR"}).encode()


class TestQuellen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_speichern_und_lesen(self):
        qid = quellen.speichern(self.ordner, "comtrade", "https://comtradeapi.un.org/x", ROH, "DE Export HS 8479",
                                zeit=ZEIT)
        self.assertTrue(quellen.ist_id(qid))
        self.assertTrue(qid.startswith("Q-20261109-comtrade-"))
        self.assertEqual(quellen.rohinhalt(self.ordner, qid), ROH)
        self.assertEqual(quellen.meta(self.ordner, qid)["url"], "https://comtradeapi.un.org/x")
        self.assertEqual([m["id"] for m in quellen.alle(self.ordner)], [qid])

    def test_gleicher_inhalt_gleiche_id_neuer_inhalt_neue_id(self):
        a = quellen.speichern(self.ordner, "ted", "https://api.ted.europa.eu/x", b"1", "t", zeit=ZEIT)
        b = quellen.speichern(self.ordner, "ted", "https://api.ted.europa.eu/x", b"1", "t", zeit=ZEIT)
        c = quellen.speichern(self.ordner, "ted", "https://api.ted.europa.eu/x", b"2", "t", zeit=ZEIT)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(quellen.alle(self.ordner)), 2)

    def test_ungueltig(self):
        with self.assertRaises(quellen.QuellenFehler):
            quellen.speichern(self.ordner, "unbekannt", "https://x", b"", "t")
        with self.assertRaises(quellen.QuellenFehler):
            quellen.speichern(self.ordner, "web", "http://x", b"", "t")
        with self.assertRaises(quellen.QuellenFehler):
            quellen.speichern(self.ordner, "web", "https://x", b"", " ")
        with self.assertRaises(quellen.QuellenFehler):
            quellen.meta(self.ordner, "Q-20261109-web-000000")

    def test_veraenderte_rohdaten(self):
        qid = quellen.speichern(self.ordner, "web", "https://x.de/a.pdf", b"abc", "GB", endung="pdf", zeit=ZEIT)
        (self.ordner / f"{qid}.roh.pdf").write_bytes(b"abd")
        with self.assertRaisesRegex(quellen.QuellenFehler, "verändert"):
            quellen.rohinhalt(self.ordner, qid)

    def test_umdeklarieren_faellt_auf(self):
        qid = quellen.speichern(self.ordner, "genesis", "https://genesis.destatis.de/x", b"1", "t", zeit=ZEIT)
        pfad = self.ordner / f"{qid}.json"
        m = json.loads(pfad.read_text())
        pfad.write_text(json.dumps({**m, "art": "web"}))
        with self.assertRaisesRegex(quellen.QuellenFehler, "Beschreibung .* verändert"):
            quellen.meta(self.ordner, qid)

    def test_ohne_indexeintrag_keine_quelle(self):
        qid = quellen.speichern(self.ordner, "ted", "https://api.ted.europa.eu/x", b"1", "t", zeit=ZEIT)
        (self.ordner / quellen.INDEX).write_text("")
        with self.assertRaisesRegex(quellen.QuellenFehler, "gibt es nicht"):
            quellen.meta(self.ordner, qid)

    def test_zahlen_im_rohinhalt(self):
        werte = quellen.zahlen_im_rohinhalt(ROH)
        self.assertIn(9487189.307, werte)
        self.assertIn(1234.5, werte)  # deutsche Schreibweise


class TestPruefung(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)
        self.q = quellen.speichern(self.ordner, "comtrade", "https://comtradeapi.un.org/x", ROH, "DE Export",
                                   zeit=ZEIT)
        self.web = quellen.speichern(self.ordner, "web", "https://firma.de/gb.pdf", b"%PDF", "GB 2025",
                                     endung="pdf", zeit=ZEIT)

    def tearDown(self):
        self.tmp.cleanup()

    def zahl(self, wert, **beleg):
        return {"wert": wert, "einheit": "EUR", **beleg}

    def test_zahl_mit_quelle_aus_rohdaten(self):
        p = pruefung.pruefen({"export": self.zahl(9487189.307, quelle=self.q)}, self.ordner)
        self.assertEqual(p.fehler, [])
        self.assertEqual(p.benutzte_quellen, {self.q})

    def test_andere_groessenordnung_und_rundung(self):
        p = pruefung.pruefen({"a": self.zahl(9.49, quelle=self.q), "b": self.zahl(1.23, quelle=self.q)}, self.ordner)
        self.assertEqual(p.fehler, [])  # 9,49 Mio und 1,23 Tsd (aus 1.234,5) auf 0,5 % genau

    def test_zahl_nicht_in_rohdaten(self):
        p = pruefung.pruefen({"a": self.zahl(5555, quelle=self.q)}, self.ordner)
        self.assertEqual(len(p.fehler), 1)
        self.assertIn("steht nicht in den Rohdaten", p.fehler[0])

    def test_webquelle_nur_hinweis(self):
        p = pruefung.pruefen({"a": self.zahl(42, quelle=self.web)}, self.ordner)
        self.assertEqual(p.fehler, [])
        self.assertEqual(len(p.hinweise), 1)

    def test_ohne_beleg_und_unbekannte_quelle(self):
        p = pruefung.pruefen({"a": self.zahl(1), "b": self.zahl(2, quelle="Q-20261109-ted-abcdef"),
                              "c": self.zahl(3, quelle="irgendwas")}, self.ordner)
        self.assertEqual(len(p.fehler), 3)
        self.assertIn("braucht genau eins", p.fehler[0])

    def test_annahme(self):
        p = pruefung.pruefen({"a": self.zahl(0.3, annahme="Branchenüblicher Wert, nicht belegt"),
                              "b": self.zahl(0.3, annahme="kurz")}, self.ordner)
        self.assertEqual(len(p.fehler), 1)
        self.assertEqual(p.annahmen, [("a", "Branchenüblicher Wert, nicht belegt")])

    def test_nackte_zahl_und_zaehlfelder(self):
        p = pruefung.pruefen({"jahr": 2025, "luecken": [{"nr": 1, "umsatz": 12.5, "text": "x"}]}, self.ordner)
        self.assertEqual(p.fehler, ["luecken[0].umsatz: nackte Zahl 12.5, gehört in ein Zahl-Objekt mit quelle "
                                    "oder annahme"])

    def test_marktgroesse_von_unten(self):
        faktoren = [self.zahl(1200, annahme="Zahl der Sägewerke laut Annahme, belegt später"),
                    self.zahl(0.25, annahme="Anteil mit Bedarf, angenommen"),
                    self.zahl(80000, annahme="Preis je Anlage, angenommen")]
        richtig = {"wert": 24e6, "einheit": "EUR", "berechnet": {"art": "produkt", "aus": faktoren}}
        falsch = {"wert": 30e6, "einheit": "EUR", "berechnet": {"art": "produkt", "aus": faktoren}}
        self.assertEqual(pruefung.pruefen({"markt": richtig}, self.ordner).fehler, [])
        f = pruefung.pruefen({"markt": falsch}, self.ordner).fehler
        self.assertEqual(len(f), 1)
        self.assertIn("produkt ergibt 2.4e+07", f[0])

    def test_quotient_und_division_durch_null(self):
        q = {"wert": 0.5, "einheit": "Anteil", "berechnet": {"art": "quotient", "aus": [
            self.zahl(1, annahme="Annahme eins, Test"), self.zahl(0, annahme="Annahme null, Test")]}}
        self.assertIn("Division durch 0", pruefung.pruefen({"m": q}, self.ordner).fehler[0])
        q["berechnet"]["aus"] = [self.zahl(1, annahme="Annahme eins, Test")]
        self.assertIn("braucht 2", pruefung.pruefen({"m": q}, self.ordner).fehler[0])


def hypothese(**aenderung):
    h = {"titel": "Nachrüstung", "these": "x", "begruendung": "y", "sicherheit": "mittel",
         "szenarien": {"pessimistisch": "a", "basis": "b", "optimistisch": "c"},
         "abbruchkriterien": [{"text": "Weniger als 5 Anfragen", "pruefen_bis": "2027-06-30"}]}
    h.update(aenderung)
    return h


class TestHypothesen(unittest.TestCase):
    HEUTE = date(2026, 11, 9)

    def test_gueltig(self):
        self.assertEqual(pruefung.hypothesen_pruefen([hypothese()] * 3, self.HEUTE), [])

    def test_hoechstens_drei(self):
        self.assertIn("1 bis 3", pruefung.hypothesen_pruefen([hypothese()] * 4, self.HEUTE)[0])
        self.assertIn("1 bis 3", pruefung.hypothesen_pruefen([], self.HEUTE)[0])

    def test_abbruchkriterien_pflicht_und_zukunft(self):
        f = pruefung.hypothesen_pruefen([hypothese(abbruchkriterien=[])], self.HEUTE)
        self.assertIn("mindestens ein Kriterium", f[0])
        f = pruefung.hypothesen_pruefen([hypothese(abbruchkriterien=[{"text": "x", "pruefen_bis": "2026-01-01"}])],
                                        self.HEUTE)
        self.assertIn("Zukunft", f[0])

    def test_sicherheit_und_szenarien(self):
        f = pruefung.hypothesen_pruefen([hypothese(sicherheit="sicher", szenarien={"basis": "b"})], self.HEUTE)
        self.assertEqual(len(f), 2)


if __name__ == "__main__":
    unittest.main()
