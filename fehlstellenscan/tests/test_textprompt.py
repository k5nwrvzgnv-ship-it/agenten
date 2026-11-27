"""Test mit Text-Prompt-Modellen (aufnahme/textprompt.py): reine Teile, Fotowahl und Bilder, ohne ultralytics."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from aufnahme import server as s
from aufnahme import textprompt as tp
from aufnahme import vorlabeln as vl


def ergebnis(umrisse, klassen, konf, namen):
    return SimpleNamespace(masks=SimpleNamespace(xyn=umrisse), boxes=SimpleNamespace(cls=klassen, conf=konf),
                           names=namen)


DREIECK = [[0.1, 0.1], [0.3, 0.1], [0.2, 0.4]]


class TestTextprompt(unittest.TestCase):
    def test_laedt_kein_ultralytics(self):
        self.assertNotIn("ultralytics", sys.modules)
        self.assertNotIn("torch", sys.modules)

    def test_begriffe(self):
        self.assertEqual(tp.begriffe_lesen(None), tp.BEGRIFFE)
        self.assertEqual(tp.begriffe_lesen(["nail hole=Nagelloch", " dent "]), [("nail hole", "Nagelloch"),
                                                                              ("dent", "dent")])
        with self.assertRaises(ValueError):
            tp.begriffe_lesen(["=leer"])
        self.assertEqual(len({b[0] for b in tp.BEGRIFFE}), len(tp.BEGRIFFE))
        self.assertGreaterEqual(len(tp.FARBEN), len(tp.BEGRIFFE))

    def test_verteilt(self):
        namen = [f"f{i}" for i in range(10)]
        self.assertEqual(tp.verteilt(namen, 3), ["f0", "f4", "f9"])   # 4,5 gerundet: immer gleich
        self.assertEqual(tp.verteilt(namen, 1), ["f5"])
        self.assertEqual(tp.verteilt(namen, 20), namen)
        self.assertEqual(tp.verteilt(namen, 0), [])

    def test_zeilen_aus_ergebnis_ueber_namen(self):
        begriffe = ["wood knot", "nail hole"]
        # names in anderer Reihenfolge als die Begriffe: Name zählt; unbekannter Name nach Nummer, zu kurz fällt weg
        r = ergebnis([DREIECK, DREIECK, DREIECK[:2]], [0, 1, 0], [0.9, 0.5, 0.7], {0: "nail hole", 1: "wood knot"})
        zeilen = vl.zeilen_lesen(tp.zeilen_aus_ergebnis(r, begriffe))
        self.assertEqual([(n, c) for n, _, c in zeilen], [(1, 0.9), (0, 0.5)])
        self.assertEqual(zeilen[0][1], [tuple(p) for p in DREIECK])
        r = ergebnis([DREIECK, DREIECK], [1, 7], [0.4, 0.4], None)          # ohne names (SAM 3?): Nummer
        self.assertEqual([n for n, _, _ in vl.zeilen_lesen(tp.zeilen_aus_ergebnis(r, begriffe))], [1])
        self.assertEqual(tp.zeilen_aus_ergebnis(SimpleNamespace(masks=None, boxes=None), begriffe), "")

    def test_kacheln_zurueck_aufs_foto(self):
        begriffe = ["wood knot", "crack"]
        kacheln = vl.kacheln("B001_S1_0", 2000, 1280)
        self.assertEqual(len(kacheln), 2)
        # Objekt in der Mitte der zweiten Kachel
        r = ergebnis([[[0.4, 0.4], [0.6, 0.4], [0.5, 0.6]]], [1], [0.8], {0: "wood knot", 1: "crack"})
        texte = {kacheln[1]["name"]: tp.zeilen_aus_ergebnis(r, begriffe)}
        objekte = vl.foto_objekte("B001_S1_0", 2000, 1280, texte, {0: 0, 1: 1}, "yoloe")
        self.assertEqual([(o["k"], o["c"], o["q"], o["ok"]) for o in objekte], [(1, 0.8, "yoloe", False)])
        x0 = kacheln[1]["x0"]
        self.assertAlmostEqual(objekte[0]["p"][0][0], (x0 + 0.4 * 1280) / 2000, places=5)
        self.assertEqual(tp.zaehlen({"B001_S1_0": objekte}, begriffe), {"wood knot": 0, "crack": 1})

    def test_zeichnen(self):
        with tempfile.TemporaryDirectory() as t:
            foto, ziel = Path(t) / "f.jpg", Path(t) / "aus" / "f.jpg"
            Image.new("RGB", (2000, 1000), (120, 90, 60)).save(foto)
            o = {"k": 3, "p": DREIECK, "c": 0.5}
            tp.zeichnen(foto, {"yoloe": [o], "sam3": []}, [b[1] for b in tp.BEGRIFFE], ziel, breite=800)
            with Image.open(ziel) as z:
                self.assertEqual(z.width, 800)
                self.assertGreater(z.height, 2 * 400)                     # zwei Streifen mit Kopfzeile

    def test_fotos_waehlen_wie_im_labeln(self):
        with tempfile.TemporaryDirectory() as t:
            wurzel = Path(t)
            ordner = wurzel / "aufnahmen"
            (wurzel / ".venv" / "bin").mkdir(parents=True)
            python = wurzel / ".venv" / "bin" / "python"
            python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
            python.chmod(0o755)
            server = s.server_bauen(ordner, "127.0.0.1", 0)
            try:
                werk = server.werk
                b = werk.balken_speichern({"laenge_mm": 295.0, "breite_mm": 200.0, "hoehe_mm": 135.0, "holzart": ""})
                bild = wurzel / "f.jpg"
                Image.new("RGB", (1600, 1200), (120, 90, 60)).save(bild)
                for seite in "1234":
                    werk.foto_ablegen(b["id"], seite, 0, bild.read_bytes())
                fotos = tp.fotos_waehlen(ordner, [b["id"]], 2)
            finally:
                server.server_close()
            self.assertEqual(len(fotos), 2)
            for name, pfad in fotos:
                self.assertTrue(name.startswith(b["id"]))
                self.assertTrue(pfad.exists() and pfad.parent.name == "zuschnitt")


if __name__ == "__main__":
    unittest.main()
