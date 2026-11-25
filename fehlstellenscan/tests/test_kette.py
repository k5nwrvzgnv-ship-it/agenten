"""Tests der Kette Foto, Label, Datensatz, Training: über den echten Server auf localhost, yolo als Attrappe."""

import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from aufnahme import bilder as bi
from aufnahme import kette as k
from aufnahme import server as s

DREIECK = [[0.1, 0.1], [0.3, 0.1], [0.2, 0.4]]
YOLO = """#!/bin/sh
for a in "$@"; do case $a in project=*) p=${a#project=};; name=*) n=${a#name=};; esac; done
mkdir -p "$p/$n"
printf 'epoch, train/seg_loss, metrics/mAP50(M)\\n1, 1.5, 0.1\\n2, 1.0, 0.4\\n' > "$p/$n/results.csv"
%s
"""


class TestLogik(unittest.TestCase):
    def test_vorschlag_und_probe(self):
        t = k.vorschlag({}, [f"B{i:03d}" for i in range(1, 8)])
        self.assertEqual([x["teil"] for x in t.values()], ["train", "val", "train", "train", "train", "train", "val"])
        self.assertEqual(k.vorschlag(t, ["B001"]), t)
        self.assertTrue(k.zuordnung(t, ["B001"])[1])
        self.assertFalse(k.zuordnung(t, ["B001", "B002"])[1])
        t["B002"]["teil"] = "test"
        benutzt, probe = k.zuordnung(t, ["B001", "B002"])
        self.assertEqual((benutzt, probe), ({"B001": "train"}, True))

    def test_objekte_pruefen(self):
        gut = [{"k": 1, "ok": True, "p": DREIECK}]
        self.assertEqual(k.objekte_pruefen(gut)[0]["p"], DREIECK)
        for o in ({"k": 18, "p": DREIECK}, {"k": 1, "p": DREIECK[:2]}, {"k": 1, "p": [[0, 0], [1, 2], [0, 1]]},
                  {"k": True, "p": DREIECK}, None):
            with self.assertRaises(ValueError):
                k.objekte_pruefen([o])

    def test_raster_lueckenlos(self):
        for n in (500, 1280, 1300, 4032, 8064):
            r = bi.raster(n)
            self.assertEqual(r[0], 0)
            if n > bi.KACHEL:
                self.assertEqual(r[-1] + bi.KACHEL, n)
                self.assertTrue(all(b - a <= bi.KACHEL - bi.UEBERLAPPUNG for a, b in zip(r, r[1:], strict=False)))

    def test_zeilen_trennen_beruehrende(self):
        a = {"k": 1, "p": [[0, 0], [0.5, 0], [0.5, 1], [0, 1]]}
        b = {"k": 1, "p": [[0.5, 0], [1, 0], [1, 1], [0.5, 1]]}
        z = bi.zeilen([a, b], (100, 100), 0, 0, 100, 100)
        self.assertEqual(len(z), 2)
        for zeile in z:
            werte = [float(x) for x in zeile.split()[1:]]
            self.assertTrue(all(0 <= w <= 1 for w in werte))
        self.assertEqual(len(bi.zeilen([a, b], (200, 100), 0, 0, 100, 100)), 1 + 0)

    def test_schneiden_hochkant_wie_oberflaeche(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            a = np.zeros((400, 200, 3), np.uint8)
            a[:200] = (255, 0, 0)             # oben rot: liegt nach der Drehung nach rechts auf der rechten Hälfte
            Image.fromarray(a).save(t / "h.png")
            bi.schneiden(t / "h.png", t / "z.jpg", t / "k.jpg", [0.5, 0.0, 0.5, 1.0])
            with Image.open(t / "z.jpg") as z:
                self.assertEqual(z.size, (200, 200))
                self.assertGreater(z.getpixel((100, 100))[0], 200)


class TestWeg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        self.ordner = self.wurzel / "aufnahmen"
        (self.wurzel / ".venv" / "bin").mkdir(parents=True)
        python = self.wurzel / ".venv" / "bin" / "python"
        python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        python.chmod(0o755)
        self.yolo("exit 0")
        self.server = s.server_bauen(self.ordner, "127.0.0.1", 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.werk = self.server.werk

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def yolo(self, ende):
        y = self.wurzel / ".venv" / "bin" / "yolo"
        y.write_text(YOLO % ende)
        os.chmod(y, 0o755)

    def ruf(self, weg, daten=None, kopf=True):
        c = http.client.HTTPConnection("localhost", self.server.server_address[1], timeout=20)
        c.request("GET" if daten is None else "POST", weg, None if daten is None else json.dumps(daten),
                  {"X-Aufnahme": "1"} if kopf else {})
        a = c.getresponse()
        roh = a.read()
        c.close()
        return a.status, json.loads(roh) if a.headers["Content-Type"].startswith("application/json") else roh

    def balken(self, seiten=("1",)):
        b = self.werk.balken_speichern({"laenge_mm": 295.0, "breite_mm": 200.0, "hoehe_mm": 135.0, "holzart": ""})
        bild = self.wurzel / "f.jpg"
        Image.new("RGB", (1600, 1200), (120, 90, 60)).save(bild)
        for x in seiten:
            self.werk.foto_ablegen(b["id"], x, 0, bild.read_bytes())
        return b["id"], [f["name"] for f in self.werk.kette.alle() if f["balken"] == b["id"]]

    def warte(self):
        for _ in range(200):
            st = self.ruf("/api/training")[1]["lauf"]
            if st["status"] not in ("bauen", "training"):
                return st
            time.sleep(0.05)
        self.fail("Lauf endet nicht")

    def test_seiten_und_fremde(self):
        for weg in ("/", "/labeln", "/training", "/labeln.js", "/training.js", "/labeln-optik.js"):
            self.assertEqual(self.ruf(weg)[0], 200, weg)
        self.assertEqual(self.ruf("/api/label", {"name": "x", "objekte": []}, kopf=False)[0], 403)
        self.assertEqual(self.ruf("/zuschnitt/gibtsnicht.jpg")[0], 404)
        self.assertEqual(self.ruf("/api/training", {})[0], 400)

    def test_durchlauf_vier_seiten_bis_training(self):
        self.werk.einst["zuschnitt"] = [0.0, 0.0, 0.5, 1.0]
        kennung, namen = self.balken(("1", "2", "3", "4"))
        self.assertEqual(len(namen), 4)
        status, roh = self.ruf(f"/zuschnitt/{namen[0]}.jpg")
        self.assertEqual((status, roh[:3]), (200, b"\xff\xd8\xff"))
        with Image.open(self.ordner / kennung / "zuschnitt" / f"{namen[0]}.jpg") as z:
            self.assertEqual(z.size, (800, 1200))
        with Image.open(next((self.ordner / kennung).glob("*_S1_*.jpg"))) as o:
            self.assertEqual(o.size, (1600, 1200))        # Original bleibt ganz
        for n in namen:
            self.assertEqual(self.ruf("/api/label", {"name": n, "objekte": [{"k": 10, "ok": True, "p": DREIECK}]})[0], 200)
        self.assertEqual(self.ruf("/api/bilder")[1][0]["objekte"][0]["k"], 10)
        st = self.ruf("/api/training")[1]
        self.assertEqual((st["probe"], st["balken"][0]["fertig"]), (True, 4))
        self.assertEqual(self.ruf("/api/training", {})[0], 200)
        lauf = self.warte()
        self.assertEqual((lauf["status"], lauf["epoche"], lauf["name"]), ("fertig", 2, "altholz-1"))
        d = self.wurzel / "datensaetze" / "altholz-1"
        self.assertIn("val: images/train", (d / "data.yaml").read_text())
        labels = [z for p in (d / "labels" / "train").glob("*.txt") for z in p.read_text().splitlines()]
        self.assertEqual([z.split()[0] for z in labels], ["10"] * 4)
        self.assertFalse(self.werk.kette.teile()[kennung]["fest"])
        self.ruf("/api/training", {})
        self.assertEqual(self.warte()["name"], "altholz-2")

    def test_trennung_nach_balken_und_sperre(self):
        a, na = self.balken(("1", "2"))
        b, nb = self.balken(("1",))
        c, nc = self.balken(("1",))
        self.ruf("/api/teil", {"balken": c, "teil": "test"})
        for n in na + nb + nc:
            self.ruf("/api/label", {"name": n, "objekte": [{"k": 0, "ok": True, "p": DREIECK}]})
        self.assertFalse(self.ruf("/api/training", {})[1]["probe"])
        self.warte()
        d = self.wurzel / "datensaetze" / "altholz-1" / "images"
        self.assertEqual({p.name[:4] for p in (d / "train").iterdir()}, {a})
        self.assertEqual({p.name[:4] for p in (d / "val").iterdir()}, {b})
        self.assertEqual(self.ruf("/api/teil", {"balken": a, "teil": "val"})[0], 400)

    def test_unfertige_und_fehler(self):
        _, namen = self.balken()
        self.ruf("/api/label", {"name": namen[0], "objekte": [{"k": 1, "ok": False, "p": DREIECK}]})
        self.assertEqual(self.ruf("/api/training", {})[0], 400)
        self.ruf("/api/label", {"name": namen[0], "objekte": [{"k": 1, "ok": True, "p": DREIECK}]})
        self.yolo("echo kaputt; exit 1")
        self.ruf("/api/training", {})
        lauf = self.warte()
        self.assertEqual((lauf["status"], lauf["fehler"]), ("fehler", "kaputt"))

    def test_abbrechen(self):
        _, namen = self.balken()
        self.ruf("/api/label", {"name": namen[0], "objekte": [{"k": 1, "ok": True, "p": DREIECK}]})
        self.yolo("sleep 30")
        self.ruf("/api/training", {})
        for _ in range(200):
            if self.ruf("/api/training")[1]["lauf"]["status"] == "training":
                break
            time.sleep(0.05)
        self.assertEqual(self.ruf("/api/training", {})[0], 400)
        self.assertEqual(self.ruf("/api/abbrechen", {})[1]["lauf"]["status"], "abgebrochen")
        self.werk.kette.prozess.wait(5)


if __name__ == "__main__":
    unittest.main()
