"""Prüfstand: Codefassung, Reihen, Speicher, Status, Ablage, Vorlauf und Vergleich."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pruefstand as ps

BEISPIELE = Path(__file__).parent / "beispiele"
MEMINFO = "MemTotal:        8131584 kB\nMemFree:  1000 kB\nMemAvailable:    2097152 kB\n"


def schritt(status="ok", exit_code=0):
    return {"status": status, "exit": exit_code, "dauer_s": 12.0, "spitze_mb": 900}


def ergebnis(nahtversatz=0.09, punkte=("a",), status="ok"):
    return {"status": status, "schritte": {"zusammenbau": schritt(status)},
            "vorpruefung": {"masstreue": "GRUEN", "maengel": []},
            "zusammenbau": {"nahtversatz_median_mm": nahtversatz, "pruefbericht": list(punkte),
                            "ohne_verbindung": [], "rechenzeit_s": 100}}


class TestCodeUndReihen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_codefassung_aendert_sich_mit_dem_inhalt(self):
        (self.tmp / "a.py").write_text("x = 1\n")
        (self.tmp / "b.md").write_text("Text\n")
        alt = ps.codefassung(self.tmp)
        (self.tmp / "b.md").write_text("anderer Text\n")
        self.assertEqual(ps.codefassung(self.tmp), alt)  # Unterlagen zählen nicht
        (self.tmp / "a.py").write_text("x = 2\n")
        self.assertNotEqual(ps.codefassung(self.tmp), alt)
        self.assertEqual(len(alt), 12)

    def test_reihen_brauchen_bauteil_json_und_zwei_fotos(self):
        gut = self.tmp / "ISO 800"
        gut.mkdir()
        (gut / "bauteil.json").write_text("{}")
        for n in ("a.jpg", "b.JPG"):
            (gut / n).write_bytes(b"")
        halb = self.tmp / "halb"
        halb.mkdir()
        (halb / "a.jpg").write_bytes(b"")
        (halb / "bauteil.json").write_text("{}")
        self.assertEqual(ps.reihen_finden(self.tmp), ["ISO 800"])
        self.assertEqual(ps.reihen_finden(self.tmp / "fehlt"), [])

    def test_unvollstaendige_fotos(self):
        (self.tmp / "gut.jpg").write_bytes(b"\xff\xd8daten\xff\xd9")
        (self.tmp / "halb.jpg").write_bytes(b"\xff\xd8dat")
        (self.tmp / "bauteil.json").write_text("{}")
        self.assertEqual(ps.unvollstaendige_fotos(self.tmp), ["halb.jpg"])
        text = "\n".join(ps.reihe_kurz("R", {"status": "fehler", "unvollstaendig": ["halb.jpg"]}))
        self.assertIn("unvollständige Fotos (Datei endet mitten im Bild): halb.jpg", text)

    def test_auswahl(self):
        reihen = ["261022_Test", "ISO 800"]
        self.assertEqual(ps.auswahl("bitte iso 800 rechnen", reihen), ["ISO 800"])
        self.assertEqual(ps.auswahl("Prüfstand laufen lassen", reihen), reihen)

    def test_lauf_id(self):
        self.assertEqual(ps.lauf_id(datetime(2026, 11, 7, 9, 5, 3)), "20261107-090503")


class TestSpeicher(unittest.TestCase):
    def test_groessen(self):
        self.assertEqual(ps.in_mb("3G"), 3072)
        self.assertEqual(ps.in_mb("1500M"), 1500)
        with self.assertRaises(ValueError):
            ps.in_mb("viel")

    def test_aus_auftrag(self):
        self.assertEqual(ps.speicher_aus_text("ISO 800, speicher 4G", "3G"), "4G")
        self.assertEqual(ps.speicher_aus_text("speicher=2500m", "3G"), "2500M")
        self.assertEqual(ps.speicher_aus_text("ISO 800", "3G"), "3G")

    def test_genug_speicher(self):
        self.assertEqual(ps.verfuegbar_mb(MEMINFO), 2048)
        self.assertTrue(ps.genug_speicher(MEMINFO, "1G")[0])
        ok, grund = ps.genug_speicher(MEMINFO, "2G")
        self.assertFalse(ok)
        self.assertIn("2048 MB frei", grund)
        self.assertFalse(ps.genug_speicher("", "1G")[0])

    def test_befehl_mit_scope_und_grenze(self):
        b = ps.befehl("/py", Path("/v/zusammensetzen2.py"), ["/r/ISO 800", "--ziel", "/z.jpg"], "3G",
                      ps.scope_name("20261107-090503", "ISO 800", "zusammenbau"))
        self.assertEqual(b[:4], ["systemd-run", "--user", "--scope", "--quiet"])
        self.assertIn("--unit=holzbalkenscan-20261107-090503-iso-800-zusammenbau", b)
        self.assertIn("MemoryMax=3G", b)
        self.assertEqual(b[-5:], ["/py", "/v/zusammensetzen2.py", "/r/ISO 800", "--ziel", "/z.jpg"])


class TestStatus(unittest.TestCase):
    def test_zusammenbau(self):
        self.assertEqual(ps.schritt_status("zusammenbau", 1, False, True), "ok")
        self.assertEqual(ps.schritt_status("zusammenbau", 3, False, True), "fehler")
        self.assertEqual(ps.schritt_status("zusammenbau", 0, False, False), "fehler")

    def test_vorpruefung_rot_ist_kein_fehler(self):
        self.assertEqual(ps.schritt_status("vorpruefung", 2, False, True), "ok")

    def test_grenzen(self):
        self.assertEqual(ps.schritt_status("zusammenbau", -9, False, False), "speichergrenze")
        self.assertEqual(ps.schritt_status("zusammenbau", -9, True, False), "zeitgrenze")

    def test_reihe(self):
        self.assertEqual(ps.reihe_status({"a": schritt(), "b": schritt()}), "ok")
        self.assertEqual(ps.reihe_status({"a": schritt(), "b": schritt("speichergrenze")}), "speichergrenze")


class TestAblageUndVergleich(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.laeufe = self.tmp / "laeufe"
        self.ref = self.tmp / "referenz"
        self.ref.mkdir()

    def lauf(self, lid, reihen):
        lauf = {"id": lid, "zeit": "", "code": "c" + lid[-1], "auftrag": None, "speicher": "3G", "reihen": reihen}
        ps.speichern(self.laeufe / lid, lauf)
        return lauf

    def test_vorlauf_ist_der_letzte_fruehere_mit_der_reihe(self):
        self.lauf("20261101-000001", {"A": ergebnis(0.10)})
        self.lauf("20261102-000002", {"B": ergebnis()})
        self.lauf("20261109-000003", {"A": ergebnis()})  # später, zählt nicht
        self.lauf("20261104-000004", {"A": ergebnis(status="fehler")})  # gescheitert, zählt nicht
        (self.laeufe / "kaputt").mkdir()
        self.assertEqual(ps.vorlauf(self.laeufe, "20261105-000000", "A")["id"], "20261101-000001")
        self.assertIsNone(ps.vorlauf(self.laeufe, "20261105-000000", "C"))

    def test_vorlauf_und_basis_je_fassung(self):
        def mit_fassung(lid, fassung, status="ok"):
            lauf = {"id": lid, "zeit": "", "code": "c", "auftrag": None, "speicher": "3G", "fassung": fassung,
                    "reihen": {"A": ergebnis(status=status)}}
            ps.speichern(self.laeufe / lid, lauf)
        self.lauf("20261101-000001", {"A": ergebnis()})               # ohne Angabe: alte Fassung
        mit_fassung("20261102-000002", "alt", status="speichergrenze")
        mit_fassung("20261103-000003", "neu")
        self.assertEqual(ps.vorlauf(self.laeufe, "20261105-000000", "A")["id"], "20261101-000001")
        self.assertEqual(ps.vorlauf(self.laeufe, "20261105-000000", "A", "neu")["id"], "20261103-000003")
        self.assertEqual(ps.vorlauf(self.laeufe, "20261105-000000", "A", nur_gelungen=False)["id"],
                         "20261102-000002")
        name, _ = ps.basis(self.laeufe, self.ref, "20261105-000000", "A", "neu")
        self.assertTrue(name.startswith("Grundlinie alte Fassung 20261102-000002"))
        self.assertIn("speichergrenze", name)
        name, _ = ps.basis(self.laeufe, self.ref, "20261105-000000", "A")
        self.assertTrue(name.startswith("Vorlauf 20261101-000001"))

    def test_fassung_aus_text(self):
        self.assertEqual(ps.fassung_aus_text("pf-flau fassung neu speicher 2G"), "neu")
        self.assertEqual(ps.fassung_aus_text("Fassung=Neu"), "neu")
        self.assertEqual(ps.fassung_aus_text("ISO 800"), "alt")
        self.assertEqual(ps.fassung_aus_text("fassung neuer"), "alt")
        self.assertEqual(ps.fassung_aus_text("pf-flau Fassung achse"), "achse")

    def test_basis_faellt_auf_referenz_zurueck(self):
        (self.ref / "ISO 800.txt").write_text((BEISPIELE / "zusammenbau_iso800.txt").read_text(encoding="utf-8"),
                                              encoding="utf-8")
        name, alt = ps.basis(self.laeufe, self.ref, "20261107-000000", "ISO 800")
        self.assertEqual(name, "Referenzbericht")
        self.assertEqual(alt["zusammenbau"]["nahtversatz_median_mm"], 0.09)
        self.assertIsNone(ps.basis(self.laeufe, self.ref, "20261107-000000", "andere"))

    def test_vergleichen_zahlen_listen_und_schwellen(self):
        alt = {"nahtversatz_median_mm": 0.09, "kante_langwellig_mm": 4.2, "pruefbericht": ["a", "b"],
               "rechenzeit_s": 100, "masstreue": "GRUEN", "aufmass_mm": 6485}
        neu = {"nahtversatz_median_mm": 0.15, "kante_langwellig_mm": 4.3, "pruefbericht": ["b", "c"],
               "rechenzeit_s": 110, "masstreue": "GELB", "aufmass_mm": 7000}
        z = ps.vergleichen(alt, neu)
        self.assertIn("Nahtversatz Median mm: 0.09 -> 0.15 (+0.06)", z)
        self.assertIn("Prüfbericht neu: c", z)
        self.assertIn("Prüfbericht weg: a", z)
        self.assertIn("Maßtreue: GRUEN -> GELB", z)
        self.assertFalse(any("langwellig" in x or "Rechenzeit" in x or "6485" in x for x in z))
        self.assertEqual(ps.vergleichen(alt, alt), [])

    def test_fehlender_wert_ist_eine_aenderung(self):
        self.assertEqual(ps.vergleichen({"nahtkanten": 59}, {"nahtkanten": None}), ["sichtbare Nahtkanten: 59 -> –"])

    def test_meldetext(self):
        lauf = self.lauf("20261107-000001", {"ISO 800": ergebnis(0.15, ("a", "neu")), "X": ergebnis()})
        text = ps.meldetext(lauf, {"ISO 800": ("Vorlauf 1 (Code c1)", ergebnis()), "X": None})
        self.assertIn("Lauf 20261107-000001, Fassung alt, Code c1", text)
        self.assertIn("ISO 800: ok", text)
        self.assertIn("Nahtversatz Median 0.15 / max – mm", text)
        self.assertIn("gegen Vorlauf 1 (Code c1):", text)
        self.assertIn("zusammenbau: Nahtversatz Median mm: 0.09 -> 0.15 (+0.06)", text)
        self.assertIn("zusammenbau: Prüfbericht neu: neu", text)
        self.assertIn("kein Vorlauf und kein Referenzbericht", text)

    def test_meldetext_ohne_kennzahlen_behauptet_keine_gleichheit(self):
        leer = {"status": "fehler", "schritte": {"zusammenbau": schritt("fehler", 3)}, "vorpruefung": {},
                "zusammenbau": {}}
        lauf = self.lauf("20261107-000001", {"A": leer})
        text = ps.meldetext(lauf, {"A": ("Referenzbericht", ergebnis())})
        self.assertIn("nichts zu vergleichen", text)
        self.assertNotIn("keine Änderung", text)

    def test_meldetext_ohne_aenderung(self):
        lauf = self.lauf("20261107-000001", {"A": ergebnis()})
        self.assertIn("keine Änderung über den Schwellen", ps.meldetext(lauf, {"A": ("V", ergebnis())}))


if __name__ == "__main__":
    unittest.main()
