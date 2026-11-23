"""Tests für auswertung.py: IoU der Masken, Zuordnung, Kennzahlen, Messungen am Holz, Befehle."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import auswertung as a
import masken as m

LIVE, DEAD, CRACK = 0, 1, 4


def quadrat(x, y, seite):
    return np.array([[x, y], [x + seite, y], [x + seite, y + seite], [x, y + seite]], dtype=np.float64)


def kreis(x, y, r, punkte=40):
    t = np.linspace(0, 2 * np.pi, punkte, endpoint=False)
    return np.stack([x + r * np.cos(t), y + r * np.sin(t)], axis=1)


class TestIou(unittest.TestCase):
    def test_gleich_ist_eins(self):
        self.assertAlmostEqual(a.iou(quadrat(10, 10, 50), quadrat(10, 10, 50)), 1.0)

    def test_getrennt_ist_null(self):
        self.assertEqual(a.iou(quadrat(0, 0, 10), quadrat(100, 100, 10)), 0.0)

    def test_halb_ueberlappt_etwa_ein_drittel(self):
        # zwei 100er-Quadrate, um 50 verschoben: Schnitt 5000, Vereinigung 15000
        self.assertAlmostEqual(a.iou(quadrat(0, 0, 100), quadrat(50, 0, 100)), 1 / 3, delta=0.02)

    def test_symmetrisch(self):
        p, q = kreis(50, 50, 30), quadrat(40, 40, 50)
        self.assertAlmostEqual(a.iou(p, q), a.iou(q, p))


class TestGroesse(unittest.TestCase):
    def test_kreis_in_mm_mit_nicht_quadratischen_pixeln(self):
        # Kreis mit 10 mm Durchmesser im Kodytek-Maßstab: in Pixeln eine Ellipse
        t = np.linspace(0, 2 * np.pi, 60, endpoint=False)
        punkte = np.stack([5 * np.cos(t) * 16.66 + 500, 5 * np.sin(t) * 6.67 + 300], axis=1)
        kurz, lang = a.groesse_mm(punkte)
        self.assertAlmostEqual(kurz, 10, delta=0.3)
        self.assertAlmostEqual(lang, 10, delta=0.3)

    def test_wenige_punkte_rechteck(self):
        kurz, lang = a.groesse_mm(np.array([[0, 0], [166.6, 0], [0, 33.35]]))
        self.assertAlmostEqual(kurz, 5, places=2)
        self.assertAlmostEqual(lang, 10, places=2)

    def test_klassen(self):
        self.assertEqual(a.groessenklasse(3), "<5")
        self.assertEqual(a.groessenklasse(5), "5-10")
        self.assertEqual(a.groessenklasse(39.9), "20-40")
        self.assertEqual(a.groessenklasse(40), ">=40")
        self.assertEqual(a.groessenklassen(), ["<5", "5-10", "10-20", "20-40", ">=40"])


class TestVergleichen(unittest.TestCase):
    def arten(self, eintraege):
        return sorted((e["art"], e["klasse"], e["klasse_vorhersage"]) for e in eintraege)

    def test_treffer_uebersehen_fehlalarm(self):
        markiert = [(LIVE, quadrat(0, 0, 100), None), (DEAD, quadrat(500, 0, 100), None)]
        vor = [(LIVE, quadrat(5, 5, 100), 0.9), (CRACK, quadrat(1000, 0, 50), 0.6)]
        self.assertEqual(self.arten(a.vergleichen(markiert, vor)), [
            ("fehlalarm", "crack", "crack"), ("treffer", "live_knot", "live_knot"),
            ("uebersehen", "dead_knot", None)])

    def test_vertauscht(self):
        e = a.vergleichen([(LIVE, quadrat(0, 0, 100), None)], [(DEAD, quadrat(0, 0, 100), 0.8)])
        self.assertEqual(self.arten(e), [("vertauscht", "live_knot", "dead_knot")])

    def test_richtige_klasse_geht_vor_vertauscht(self):
        # dead mit höherer Konfidenz darf den live-Ast nicht wegnehmen, wenn live ihn trifft
        markiert = [(LIVE, quadrat(0, 0, 100), None)]
        vor = [(DEAD, quadrat(0, 0, 100), 0.9), (LIVE, quadrat(2, 2, 100), 0.5)]
        self.assertEqual(self.arten(a.vergleichen(markiert, vor)), [
            ("fehlalarm", "dead_knot", "dead_knot"), ("treffer", "live_knot", "live_knot")])

    def test_doppelte_vorhersage_ein_treffer(self):
        markiert = [(LIVE, quadrat(0, 0, 100), None)]
        vor = [(LIVE, quadrat(0, 0, 100), 0.5), (LIVE, quadrat(3, 0, 100), 0.9)]
        e = a.vergleichen(markiert, vor)
        self.assertEqual(self.arten(e), [("fehlalarm", "live_knot", "live_knot"),
                                          ("treffer", "live_knot", "live_knot")])
        self.assertEqual(next(x for x in e if x["art"] == "treffer")["konfidenz"], 0.9)

    def test_konfidenzschwelle(self):
        e = a.vergleichen([(LIVE, quadrat(0, 0, 100), None)], [(LIVE, quadrat(0, 0, 100), 0.1)])
        self.assertEqual(self.arten(e), [("uebersehen", "live_knot", None)])

    def test_iou_schwelle(self):
        markiert = [(LIVE, quadrat(0, 0, 100), None)]
        vor = [(LIVE, quadrat(50, 0, 100), 0.9)]     # IoU etwa 1/3
        self.assertEqual(self.arten(a.vergleichen(markiert, vor))[0][0], "fehlalarm")
        self.assertEqual(self.arten(a.vergleichen(markiert, vor, iou_schwelle=0.3)),
                         [("treffer", "live_knot", "live_knot")])

    def test_ohne_konfidenz_zaehlt_alles(self):
        # Person gegen Person: zweite Markierung ohne Konfidenz
        e = a.vergleichen([(LIVE, quadrat(0, 0, 100), None)], [(LIVE, quadrat(0, 0, 100), None)])
        self.assertEqual(e[0]["art"], "treffer")

    def test_mm_bei_treffer(self):
        e = a.vergleichen([(LIVE, kreis(500, 500, 100), None)], [(LIVE, kreis(500, 500, 110), 0.9)])[0]
        self.assertGreater(e["kurz_vorhersage_mm"], e["kurz_mm"])


class TestZusammenfassen(unittest.TestCase):
    def test_zaehlen_und_quoten(self):
        bilder = {
            "b1": a.vergleichen([(LIVE, quadrat(0, 0, 100), None), (LIVE, quadrat(300, 0, 100), None)],
                                [(LIVE, quadrat(0, 0, 100), 0.9), (DEAD, quadrat(300, 0, 100), 0.7)]),
            "b2": a.vergleichen([(LIVE, quadrat(0, 0, 100), None)], [(CRACK, quadrat(600, 0, 20), 0.5)]),
        }
        b = a.zusammenfassen(bilder)
        live = b["je_klasse"]["live_knot"]
        self.assertEqual((live["markiert"], live["treffer"], live["uebersehen"], live["vertauscht"]), (3, 1, 1, 1))
        self.assertAlmostEqual(live["trefferquote"], 1 / 3, places=3)
        self.assertEqual(live["praezision"], 1.0)
        self.assertEqual(b["je_klasse"]["dead_knot"]["vorhergesagt"], 1)
        self.assertEqual(b["je_klasse"]["dead_knot"]["praezision"], 0.0)
        self.assertEqual(b["je_klasse"]["crack"]["fehlalarm"], 1)
        self.assertEqual(b["verwechslung"], {"live_knot -> dead_knot": 1})
        self.assertEqual(b["gesamt"]["markiert"], 3)
        lo, hi = live["trefferquote_95"]
        self.assertLessEqual(lo, 1 / 3)
        self.assertGreaterEqual(hi, 1 / 3)
        self.assertEqual(b["aeste_mm_vorhersage_minus_markierung"]["n"], 1)

    def test_groessenklassen(self):
        # 100 px Quadrat: quer 6 mm, längs 15 mm -> kurz 6 mm
        bilder = {"b": a.vergleichen([(LIVE, quadrat(0, 0, 100), None)], [])}
        self.assertEqual(a.zusammenfassen(bilder)["je_groesse"]["live_knot"],
                         {"5-10": {"markiert": 1, "treffer": 0, "quote": 0.0}})


class TestStatistik(unittest.TestCase):
    def test_bland_altman(self):
        r = a.bland_altman([11, 12, 13], [10, 10, 10])
        self.assertEqual(r["n"], 3)
        self.assertEqual(r["mittel"], 2.0)
        self.assertEqual(r["sd"], 1.0)
        self.assertEqual(r["grenzen"], [0.04, 3.96])
        self.assertEqual(r["betrag"], 2.0)

    def test_bland_altman_leer_und_einer(self):
        self.assertIsNone(a.bland_altman([], [])["mittel"])
        self.assertIsNone(a.bland_altman([1], [0])["sd"])

    def test_bootstrap(self):
        self.assertEqual(a.bootstrap_quote([(2, 2), (3, 3)]), [1.0, 1.0])
        self.assertIsNone(a.bootstrap_quote([(0, 0)]))
        self.assertIsNone(a.bootstrap_quote([]))
        erste = a.bootstrap_quote([(1, 2), (0, 3), (4, 4)])
        self.assertEqual(erste, a.bootstrap_quote([(1, 2), (0, 3), (4, 4)]))   # fester Seed
        self.assertLess(erste[0], erste[1])


CSV = """balken;seite;ast;l_mm;q_mm;d_min_mm;d_max_mm;messer;bemerkung
B07;A;1;412;63;14,5;22;F;
B07;A;1;;;15,5;21;J;zweite Messung
B07;A;1;;;18;26;F;mit Ring
B07;A;2;1000;100;8;9;F;

B08;A;1;50;50;10;10;F;
"""


class TestMessung(unittest.TestCase):
    def test_lesen(self):
        z = a.messungen_lesen(CSV)
        self.assertEqual(len(z), 5)
        self.assertEqual(z[0]["d_min_mm"], 14.5)
        self.assertIsNone(z[1]["l_mm"])

    def test_lesen_fehlende_spalte(self):
        with self.assertRaises(ValueError):
            a.messungen_lesen("balken;seite;ast\nB1;A;1\n")

    def test_lesen_kaputte_zahl(self):
        with self.assertRaisesRegex(ValueError, "Zeile 2"):
            a.messungen_lesen(CSV.splitlines()[0] + "\nB1;A;1;x;1;1;1;F;\n")

    def test_aeste_mitteln_ohne_ring(self):
        liste = {x["ast"]: x for x in a.aeste([z for z in a.messungen_lesen(CSV) if z["balken"] == "B07"])}
        self.assertEqual(liste["1"]["d_min_mm"], 15.0)
        self.assertEqual(liste["1"]["l_mm"], 412)
        self.assertEqual(liste["1"]["d_min_einzeln"], [14.5, 15.5])

    def test_wiederholbarkeit(self):
        w = a.wiederholbarkeit(a.messungen_lesen(CSV))
        self.assertEqual(w["d_min_mm"]["n"], 1)
        self.assertEqual(w["d_min_mm"]["mittel"], -1.0)
        self.assertEqual(w["d_max_mm"]["mittel"], 1.0)

    def funde(self):
        return [{"klasse": "dead_knot", "konfidenz": 0.6, "l_von": 405, "l_bis": 421, "q_von": 55, "q_bis": 70,
                 "ellipse_kurz": 13.0, "ellipse_lang": 20.0},
                {"klasse": "crack", "konfidenz": 0.9, "l_von": 990, "l_bis": 1010, "q_von": 95, "q_bis": 105,
                 "ellipse_kurz": None, "ellipse_lang": None}]

    def test_zuordnen(self):
        liste = a.aeste([z for z in a.messungen_lesen(CSV) if z["balken"] == "B07"])
        paare, ohne = a.zuordnen(liste, self.funde())
        self.assertEqual([p["ast"] for p in paare], ["1"])
        self.assertEqual([x["ast"] for x in ohne], ["2"])    # beim Riss-Fund, aber Riss ist kein Ast

    def test_zuordnen_spiegeln(self):
        liste = [{"balken": "B", "seite": "A", "ast": "1", "l_mm": 100.0, "q_mm": 20.0, "d_min_mm": 5.0,
                  "d_max_mm": 6.0}]
        fund = [{"klasse": "live_knot", "konfidenz": 0.5, "l_von": 895, "l_bis": 905, "q_von": 175, "q_bis": 185,
                 "ellipse_kurz": 5.0, "ellipse_lang": 6.0}]
        self.assertEqual(a.zuordnen(liste, fund)[0], [])
        self.assertEqual(len(a.zuordnen(liste, fund, laenge_mm=1000, hoehe_mm=200)[0]), 1)

    def test_auswerten(self):
        r = a.messung_auswerten(a.messungen_lesen(CSV), self.funde(), "B07", "A")
        self.assertEqual((r["aeste"], r["zugeordnet"], r["ohne_fund"]), (2, 1, ["2"]))
        self.assertEqual(r["modell_minus_messung_d_min"]["mittel"], -2.0)
        with self.assertRaises(ValueError):
            a.messung_auswerten(a.messungen_lesen(CSV), self.funde(), "B99", "A")


class TestBefehle(unittest.TestCase):
    def test_fehler_ende_zu_ende(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            mark, vor, bilder, aus = tmp / "m", tmp / "v", tmp / "b", tmp / "aus"
            for ordner in (mark, vor, bilder):
                ordner.mkdir()
            breite, hoehe = 400, 200
            mark.joinpath("x1.txt").write_text(m.zu_yolo_seg(LIVE, quadrat(10, 10, 80), breite, hoehe) + "\n")
            mark.joinpath("x2.txt").write_text("")                       # Bild ohne Fehler
            vor.joinpath("x1.txt").write_text(m.zu_yolo_seg(LIVE, quadrat(12, 10, 80), breite, hoehe) + " 0.8\n")
            vor.joinpath("x2.txt").write_text(m.zu_yolo_seg(CRACK, quadrat(200, 50, 40), breite, hoehe) + " 0.4\n")
            vor.joinpath("x3.txt").write_text(m.zu_yolo_seg(CRACK, quadrat(200, 50, 40), breite, hoehe) + " 0.4\n")
            for n in ("x1", "x2"):
                Image.new("RGB", (breite, hoehe)).save(bilder / f"{n}.bmp")
            self.assertEqual(a.main(["fehler", "--markierung", str(mark), "--vorhersage", str(vor),
                                     "--bilder", str(bilder), "--ausgabe", str(aus)]), 0)
            bericht = json.loads((aus / "bericht.json").read_text())
            self.assertEqual(bericht["bilder"], 2)                        # x3 hat keine Markierung
            self.assertEqual(bericht["je_klasse"]["live_knot"]["treffer"], 1)
            self.assertEqual(bericht["je_klasse"]["crack"]["fehlalarm"], 1)
            zeilen = (aus / "fehler.csv").read_text().splitlines()
            self.assertEqual(len(zeilen), 3)
            self.assertTrue(zeilen[0].startswith("bild;art;klasse"))

    def test_fehler_ohne_bild_bricht_ab(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "m").mkdir()
            (tmp / "b").mkdir()
            (tmp / "m" / "x.txt").write_text("")
            self.assertEqual(a.main(["fehler", "--markierung", str(tmp / "m"), "--vorhersage", str(tmp / "v"),
                                     "--bilder", str(tmp / "b"), "--ausgabe", str(tmp / "aus")]), 1)

    def test_messung_ende_zu_ende(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "messung.csv").write_text(CSV)
            (tmp / "funde.json").write_text(json.dumps(TestMessung.funde(None)))
            self.assertEqual(a.main(["messung", "--messungen", str(tmp / "messung.csv"), "--funde",
                                     str(tmp / "funde.json"), "--balken", "B07", "--seite", "A",
                                     "--ausgabe", str(tmp / "aus")]), 0)
            r = json.loads((tmp / "aus" / "messung.json").read_text())
            self.assertEqual(r["zugeordnet"], 1)


if __name__ == "__main__":
    unittest.main()
