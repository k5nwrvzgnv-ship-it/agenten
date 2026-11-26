"""Tests der Kette Foto, Label, Datensatz, Training: über den echten Server auf localhost, yolo als Attrappe."""

import http.client
import json
import os
import shutil
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
from aufnahme import saetze as sa
from aufnahme import server as s

DREIECK = [[0.1, 0.1], [0.3, 0.1], [0.2, 0.4]]
YOLO = """#!/bin/sh
echo "$*" >> "AUFRUFE"
for a in "$@"; do case $a in project=*) p=${a#project=};; name=*) n=${a#name=};; esac; done
mkdir -p "$p/$n"
printf 'epoch, time, train/seg_loss, metrics/mAP50(B), metrics/mAP50-95(B), metrics/mAP50(M), metrics/mAP50-95(M)\\n\
1, 60.5, 1.5, 0.2, 0.1, 0.1, 0.05\\n2, 121, 1.0, 0.5, 0.3, 0.4, 0.2\\n' > "$p/$n/results.csv"
printf 'task: segment\\nmodel: yolo11n-seg.pt\\nepochs: 60\\nbatch: 2\\nimgsz: 1280\\n' > "$p/$n/args.yaml"
cat "TABELLE"
ENDE
"""
TABELLE = """\
\x1b[K                 Class     Images  Instances      Box(P          R      mAP50  mAP50-95)     Mask(P          R      \
mAP50  mAP50-95): 50% ━━━━━━── 1/2 4.3it/s 0.2s<0.2s\r\x1b[K                 Class     Images  Instances      Box(P          \
R      mAP50  mAP50-95)     Mask(P          R      mAP50  mAP50-95): 100% ━━━━━━━━━━━━ 2/2 4.3it/s 0.5s
                   all       2026       4465      0.753      0.672      0.748      0.457      0.753      0.669      0.746      0.413
             live_knot       1277       2205       0.85      0.786      0.867      0.442      0.851      0.783      0.868       0.42
            blue_stain          5         12      0.359      0.333      0.293      0.195       0.36      0.333      0.293      0.151
Speed: 0.2ms preprocess, 0.5ms inference, 0.0ms loss, 6.5ms postprocess per image
Results saved to /x/runs/segment/altholz-1"""


class TestLogik(unittest.TestCase):
    def test_vorschlag(self):
        t = k.vorschlag({}, [f"B{i:03d}" for i in range(1, 8)])
        self.assertEqual([x["teil"] for x in t.values()], ["train", "val", "train", "train", "train", "train", "val"])
        self.assertEqual(k.vorschlag(t, ["B001"]), t)

    def test_pruefung_nie_auf_trainingsbildern(self):
        def f(b, seite, nr, objekte=1):
            return {"balken": b, "seite": seite, "nr": nr, "name": f"{b}_S{seite}_{nr}", "objekte": objekte}
        t = k.vorschlag({}, ["B001", "B002", "B003"])
        t["B003"]["teil"] = "test"
        teil, art = k.pruefung(t, [f("B001", "1", 0), f("B002", "1", 0), f("B003", "1", 0)])
        self.assertEqual((teil, art), ({("B001", "B001_S1_0"): "train", ("B002", "B002_S1_0"): "val"}, "balken"))
        # nur Trainingsbalken: eine Seite mit Objekten zurück, Fotozahl nahe einem Fünftel
        fotos = [f("B001", s, n) for s in "1234" for n in range(3)] + [f("B001", "2", 3)]
        fotos[0]["objekte"] = 0
        teil, art = k.pruefung(t, fotos)
        val = sorted(n for (_, n), x in teil.items() if x == "val")
        self.assertEqual((art, val), ("seite", ["B001_S4_0", "B001_S4_1", "B001_S4_2"]))
        self.assertEqual(len(teil), 13)
        # Seite ohne Objekte prüft nichts, die mit allen Objekten ließe das Training leer
        teil, _ = k.pruefung(t, [f("B001", "1", 0, 0), f("B001", "2", 0, 3), f("B001", "3", 0, 0), f("B001", "4", 0, 2)])
        self.assertEqual({n for (_, n), x in teil.items() if x == "val"}, {"B001_S4_0"})
        # nur eine Seite: die letzten Fotos
        teil, art = k.pruefung(t, [f("B001", "1", n) for n in (3, 0, 9, 1, 2, 4, 5, 6, 7, 8)])
        self.assertEqual((art, sorted(n for (_, n), x in teil.items() if x == "val")), ("fotos", ["B001_S1_8", "B001_S1_9"]))
        self.assertEqual(k.pruefung(t, [f("B001", "1", 0), f("B001", "1", 1)])[0][("B001", "B001_S1_1")], "val")
        self.assertEqual(k.pruefung(t, [f("B001", "1", 0)]), ({}, None))
        self.assertEqual(k.pruefung(t, [f("B001", "1", 0), f("B003", "1", 0)]), ({}, None))

    def test_ergebnis_aus_log_csv_und_args(self):
        tabelle = k.tabelle_gelesen("Epoche 1\n" + TABELLE)
        self.assertEqual([t["klasse"] for t in tabelle], ["all", "live_knot", "blue_stain"])
        self.assertEqual((tabelle[0]["bilder"], tabelle[0]["box"]["map"], tabelle[2]["maske"]["p"]), (2026, 0.457, 0.36))
        self.assertEqual(k.tabelle_gelesen("kein Abschluss"), [])
        with tempfile.TemporaryDirectory() as t:
            lauf, log = Path(t), Path(t) / "lauf.log"
            log.write_text("        all  3  4  0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1\n")
            self.assertIsNone(k.ergebnis_gelesen(lauf, log, lauf / "bericht.json"))
            log.write_text(TABELLE)
            (lauf / "results.csv").write_text(
                "epoch,time,metrics/mAP50(B),metrics/mAP50-95(B),metrics/mAP50(M),metrics/mAP50-95(M)\n"
                "1,10,0.9,0.1,0.9,0.1\n2,20,0.5,0.3,0.4,0.2\n3,30,0.5,0.25,0.4,0.2\n")
            (lauf / "args.yaml").write_text("model: /m/runs/segment/kodytek-seg1-n1280/weights/best.pt\nepochs: 60\n"
                                             "imgsz: 1280\nbatch: 2\nname: null\n")
            (lauf / "bericht.json").write_text('{"probe": false, "kacheln": {"train": 30, "val": 8}}')
            e = k.ergebnis_gelesen(lauf, log, lauf / "bericht.json")
        self.assertEqual((e["beste"], e["gelaufen"], e["sekunden"], e["modell"], e["train"], e["val"]),
                         (2, 3, 30.0, "kodytek-seg1-n1280", 30, 8))

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
        (self.wurzel / "tabelle.txt").write_text(TABELLE + "\n")
        y.write_text(YOLO.replace("TABELLE", str(self.wurzel / "tabelle.txt")).replace("ENDE", ende)
                     .replace("AUFRUFE", str(self.wurzel / "aufrufe.txt")))
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
            if st["status"] not in k.LAUFEND:
                return st
            time.sleep(0.05)
        self.fail("Lauf endet nicht")

    def test_seiten_und_fremde(self):
        for weg in ("/", "/labeln", "/training", "/koerper", "/labeln.js", "/training.js", "/labeln-optik.js",
                    "/koerper.js", "/koerper.css"):
            self.assertEqual(self.ruf(weg)[0], 200, weg)
        self.assertEqual(self.ruf("/api/label", {"name": "x", "objekte": []}, kopf=False)[0], 403)
        self.assertEqual(self.ruf("/zuschnitt/gibtsnicht.jpg")[0], 404)
        self.assertEqual(self.ruf("/api/training", {})[0], 400)

    def test_koerper(self):
        b = self.werk.balken_speichern({"laenge_mm": 295.0, "breite_mm": 200.0, "hoehe_mm": 135.0, "holzart": ""})
        bild = Image.new("RGB", (1600, 1200), (18, 20, 30))
        bild.paste((190, 140, 80), (300, 400, 1300, 800))
        pfad = self.wurzel / "k.jpg"
        bild.save(pfad)
        self.werk.foto_ablegen(b["id"], "1", 0, pfad.read_bytes())
        status, k1 = self.ruf(f"/api/koerper?id={b['id']}")
        self.assertEqual(status, 200, k1)
        self.assertEqual(list(k1["seiten"]), ["1"])
        self.assertEqual(self.ruf(f"/koerper/{b['id']}/S1_k.jpg")[0], 200)
        status, roh = self.ruf(f"/koerper/{b['id']}/S1.jpg")
        self.assertEqual((status, roh[:3]), (200, b"\xff\xd8\xff"))
        self.assertEqual(self.ruf(f"/api/koerper?id={b['id']}")[1]["stand"], k1["stand"])   # nicht neu gerechnet
        self.assertEqual(self.ruf("/api/koerper?id=B999")[0], 400)
        self.assertEqual(self.ruf(f"/koerper/{b['id']}/S2.jpg")[0], 404)

    def test_alter_plan_ohne_zuschnitt(self):
        """Wie B001 Seite 3: Plan aus einer älteren Fassung ohne "zuschnitt" -> ganzes Bild, kein Absturz."""
        b = self.werk.balken_speichern({"laenge_mm": 295.0, "breite_mm": 200.0, "hoehe_mm": 135.0, "holzart": ""})
        bild = Image.new("RGB", (1600, 1200), (18, 20, 30))
        bild.paste((190, 140, 80), (300, 400, 1300, 800))
        pfad = self.wurzel / "alt.jpg"
        bild.save(pfad)
        self.werk.foto_ablegen(b["id"], "3", 0, pfad.read_bytes())
        datei = self.ordner / b["id"] / "balken.json"
        roh = json.loads(datei.read_text())
        del roh["seiten"]["3"]["plan"]["zuschnitt"]
        datei.write_text(json.dumps(roh))
        name = next(f["name"] for f in self.werk.kette.alle() if f["balken"] == b["id"])
        status, z = self.ruf(f"/zuschnitt/{name}.jpg")
        self.assertEqual((status, z[:3]), (200, b"\xff\xd8\xff"))
        self.assertEqual(self.ruf(f"/api/koerper?id={b['id']}")[0], 200)
        self.assertEqual(self.ruf("/api/label", {"name": name, "objekte": []})[0], 200)

    def test_galerie_und_zuordnen(self):
        alt, _ = self.balken(("1", "2"))
        neu = self.werk.balken_speichern({"laenge_mm": 4000.0, "breite_mm": 100.0, "hoehe_mm": 120.0, "holzart": "Eiche"})["id"]
        for weg in ("/galerie", "/galerie.js", "/galerie.css"):
            self.assertEqual(self.ruf(weg)[0], 200, weg)
        g = self.ruf("/api/galerie")[1]
        self.assertEqual([b["id"] for b in g], [neu, alt])                     # neueste zuerst
        self.assertEqual((g[1]["seiten"], g[1]["fotos"], g[1]["koerper"]), ({"1": 1, "2": 1, "3": 0, "4": 0}, 2, None))
        self.assertEqual((g[0]["bild"], g[0]["holzart"], g[0]["teil"]), (None, "Eiche", "val"))      # zweiter Balken: Prüfung (vorschlag)
        self.assertEqual(self.ruf("/api/teil", {"balken": alt, "teil": "test"})[0], 200)
        self.assertEqual(self.ruf("/api/galerie")[1][1]["teil"], "test")
        self.assertEqual(self.ruf("/api/teil", {"balken": alt, "teil": "irgendwo"})[0], 400)

    def test_koerper_veraltet(self):
        with tempfile.TemporaryDirectory() as t:
            o = Path(t)
            (o / "zuschnitt").mkdir()
            (o / "balken.json").write_text("{}")
            (o / "zuschnitt" / "a.jpg").write_text("")
            self.assertTrue(k.koerper_veraltet(o, ["a"]))                     # noch kein Körper
            (o / "koerper").mkdir()
            (o / "koerper" / "koerper.json").write_text("{}")
            self.assertTrue(k.koerper_veraltet(o, ["a"]))                     # keine kleinen Bilder
            (o / "koerper" / "S1_k.jpg").write_text("")
            jetzt = time.time()
            os.utime(o / "koerper" / "koerper.json", (jetzt, jetzt))
            for q in (o / "balken.json", o / "zuschnitt" / "a.jpg"):
                os.utime(q, (jetzt - 10, jetzt - 10))
            self.assertFalse(k.koerper_veraltet(o, ["a"]))
            self.assertTrue(k.koerper_veraltet(o, ["a", "b"]))                # neues Foto, Zuschnitt fehlt noch
            os.utime(o / "balken.json", (jetzt + 10, jetzt + 10))
            self.assertTrue(k.koerper_veraltet(o, ["a"]))                     # Maße geändert

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
        self.assertEqual((st["altholz"], st["balken"][0]["fertig"]), ({"art": "seite", "fertig": 4, "train": 3, "val": 1}, 4))
        self.assertEqual(self.ruf("/api/training", {})[0], 200)
        lauf = self.warte()
        self.assertEqual((lauf["status"], lauf["epoche"], lauf["name"]), ("fertig", 2, "altholz-1"))
        d = self.wurzel / "datensaetze" / "altholz-1"
        self.assertIn("val: images/val", (d / "data.yaml").read_text())
        labels = {t: [z for p in (d / "labels" / t).glob("*.txt") for z in p.read_text().splitlines()] for t in ("train", "val")}
        self.assertEqual(([z.split()[0] for z in labels["train"]], [z.split()[0] for z in labels["val"]]), (["10"] * 3, ["10"]))
        val = {p.name.split("_x")[0] for p in (d / "images" / "val").iterdir()}
        self.assertFalse(val & {p.name.split("_x")[0] for p in (d / "images" / "train").iterdir()})
        self.assertEqual([n for n in namen if "_S4_" in n], sorted(val))
        self.assertFalse(self.werk.kette.teile()[kennung]["fest"])
        e = self.ruf("/api/training")[1]["ergebnis"]
        bericht = json.loads((d / "bericht.json").read_text())
        self.assertEqual((e["name"], e["probe"], e["pruefung"], e["beste"], e["gelaufen"], e["epochen"], e["sekunden"]),
                         ("altholz-1", None, "seite", 2, 2, 60, 121.0))
        self.assertEqual((e["train"], e["val"]), (bericht["kacheln"]["train"], bericht["kacheln"]["val"]))
        self.assertEqual((e["train"], e["val"]), (3, 1))
        self.assertEqual((e["modell"], e["imgsz"], e["batch"], e["saetze"]), ("yolo11n-seg", "1280", "2", ["altholz"]))
        self.assertIsNone(e["altholz"])          # nur Altholz: die Prüfung von ultralytics ist schon reines Altholz
        self.assertFalse((d / "altholz.yaml").exists())
        self.assertNotIn("segment val", (self.wurzel / "aufrufe.txt").read_text())
        self.assertEqual((e["gesamt"]["maske"]["map50"], [x["k"] for x in e["klassen"]]), (0.746, [0, 8]))
        self.ruf("/api/training", {})
        self.assertEqual(self.warte()["name"], "altholz-2")
        self.yolo("exit 1")
        self.ruf("/api/training", {})
        self.assertEqual(self.warte()["status"], "fehler")
        self.assertIsNone(self.ruf("/api/training")[1]["ergebnis"])
        self.werk.kette.lauf = None             # wie nach einem Neustart: letzter Lauf auf der Platte
        (self.ordner / "altholz-3.log").write_text("Epoche 1\nkaputt\n")
        self.assertIsNone(self.ruf("/api/training")[1]["ergebnis"])    # altholz-3 ohne Abschluss im Log
        (self.ordner / "altholz-3.log").unlink()
        shutil.rmtree(self.wurzel / "runs" / "segment" / "altholz-3")
        self.assertEqual(self.ruf("/api/training")[1]["ergebnis"]["name"], "altholz-2")

    def test_trennung_nach_balken_und_sperre(self):
        a, na = self.balken(("1", "2"))
        b, nb = self.balken(("1",))
        c, nc = self.balken(("1",))
        self.ruf("/api/teil", {"balken": c, "teil": "test"})
        for n in na + nb + nc:
            self.ruf("/api/label", {"name": n, "objekte": [{"k": 0, "ok": True, "p": DREIECK}]})
        self.assertEqual(self.ruf("/api/training", {})[1]["lauf"]["pruefung"], "balken")
        self.warte()
        d = self.wurzel / "datensaetze" / "altholz-1" / "images"
        self.assertEqual({p.name[:4] for p in (d / "train").iterdir()}, {a})
        self.assertEqual({p.name[:4] for p in (d / "val").iterdir()}, {b})
        self.assertEqual(self.ruf("/api/teil", {"balken": a, "teil": "val"})[0], 400)

    def test_unfertige_und_fehler(self):
        _, namen = self.balken(("1", "2"))
        self.ruf("/api/label", {"name": namen[0], "objekte": [{"k": 1, "ok": False, "p": DREIECK}]})
        self.assertEqual(self.ruf("/api/training", {})[0], 400)
        self.ruf("/api/label", {"name": namen[0], "objekte": [{"k": 1, "ok": True, "p": DREIECK}]})
        status, antwort = self.ruf("/api/training", {})      # ein Foto: keine Prüfung möglich, kein Lauf
        self.assertEqual((status, antwort["fehler"]), (400, "Für die Prüfung fehlt ein zweites fertig gelabeltes Foto."))
        self.assertEqual(self.ruf("/api/training")[1]["altholz"], {"art": None, "fertig": 1, "train": 0, "val": 0})
        self.ruf("/api/label", {"name": namen[1], "objekte": [{"k": 1, "ok": True, "p": DREIECK}]})
        self.yolo("echo kaputt; exit 1")
        self.ruf("/api/training", {})
        lauf = self.warte()
        self.assertEqual((lauf["status"], lauf["fehler"]), ("fehler", "kaputt"))

    def test_abbrechen(self):
        _, namen = self.balken(("1", "2"))
        for n in namen:
            self.ruf("/api/label", {"name": n, "objekte": [{"k": 1, "ok": True, "p": DREIECK}]})
        self.yolo("sleep 30")
        self.ruf("/api/training", {})
        for _ in range(200):
            if self.ruf("/api/training")[1]["lauf"]["status"] == "training":
                break
            time.sleep(0.05)
        self.assertEqual(self.ruf("/api/training", {})[0], 400)
        self.assertEqual(self.ruf("/api/abbrechen", {})[1]["lauf"]["status"], "abgebrochen")
        self.werk.kette.prozess.wait(5)

    def kodytek(self, name="kodytek-seg-1", zahl=(6, 3)):
        d = self.wurzel / "datensaetze" / name
        for teil, n in zip(("train", "val", "test"), (*zahl, 2), strict=True):
            (d / "images" / teil).mkdir(parents=True)
            (d / "labels" / teil).mkdir(parents=True)
            for i in range(n):
                stamm = f"{teil}{i}"
                Image.new("RGB", (280, 102), (150, 120, 80)).save(d / "images" / teil / f"{stamm}.bmp")
                (d / "labels" / teil / f"{stamm}.txt").write_text("" if i == 1 else "1 0.1 0.1 0.3 0.1 0.2 0.4\n")
        (d / "data.yaml").write_text("path: x\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n" + "".join(
            f"  {i}: {n}\n" for i, n in enumerate(k.KLASSEN[:10])))
        return d

    def test_kodytek_ansehen_korrigieren_trainieren(self):
        d = self.kodytek()
        bilder = self.ruf("/api/bilder?satz=kodytek")[1]
        self.assertEqual(len(bilder), 9)
        self.assertFalse([b for b in bilder if "test" in b["name"]])
        eins = next(b for b in bilder if b["name"] == "kodytek_train0")
        self.assertEqual((eins["objekte"][0]["k"], eins["objekte"][0]["ok"]), (1, False))
        self.assertEqual(self.ruf("/zuschnitt/kodytek_train0.jpg")[1][:3], b"\xff\xd8\xff")
        self.assertEqual(self.ruf("/api/label", {"name": "kodytek_train0", "objekte": [{"k": 4, "ok": True, "p": DREIECK}]})[0], 200)
        st = self.ruf("/api/training")[1]["saetze"]
        self.assertEqual([(x["id"], x["train"], x["val"], x["fertig"]) for x in st],
                         [("kodytek", 6, 3, 1), ("kodytek-seg-1", 6, 3, None)])
        self.assertEqual(self.ruf("/api/training", {"saetze": ["kodytek"]})[0], 200)
        self.assertEqual(self.warte()["status"], "fertig")
        z = self.wurzel / "datensaetze" / "altholz-1"
        self.assertEqual((z / "labels/train/kodytek_train0.txt").read_text().split()[0], "4")
        self.assertEqual((z / "labels/train/kodytek_train2.txt").read_text(), (d / "labels/train/train2.txt").read_text())
        self.assertEqual((d / "labels/train/train0.txt").read_text().split()[0], "1")     # Original bleibt
        self.assertEqual(len(list((z / "images/val").iterdir())), 3)

    def test_datensaetze_verbinden(self):
        self.kodytek()
        zweiter = self.kodytek("extra", (2, 1))
        kaputt = self.kodytek("boxen", (1, 1))
        for p in (kaputt / "labels/train").iterdir():
            p.write_text("1 0.5 0.5 0.1 0.1\n")
        for p in (zweiter / "images").rglob("*.bmp"):
            p.rename(p.with_name("e_" + p.name))
        a, na = self.balken(("1", "2"))
        for n in na:
            self.ruf("/api/label", {"name": n, "objekte": [{"k": 10, "ok": True, "p": DREIECK}]})
        self.assertEqual([x["id"] for x in self.ruf("/api/training")[1]["saetze"]], ["kodytek", "extra", "kodytek-seg-1"])
        self.assertEqual(self.ruf("/api/training", {"saetze": ["boxen"]})[0], 400)
        self.assertEqual(self.ruf("/api/training", {"saetze": []})[0], 400)
        self.assertEqual(self.ruf("/api/training", {"saetze": ["altholz", "kodytek", "extra", "kodytek-seg-1"]})[1]["lauf"]["pruefung"], "seite")
        self.assertEqual(self.warte()["status"], "fertig")
        z = self.wurzel / "datensaetze" / "altholz-1"
        self.assertIn("train: train.txt\nval: val.txt", (z / "data.yaml").read_text())
        # zweite Prüfung von best.pt nur auf den Altholz-Kacheln (Seite 2), nicht auf Kodytek
        self.assertIn("val: val_altholz.txt", (z / "altholz.yaml").read_text())
        nur = [Path(x) for x in (z / "val_altholz.txt").read_text().splitlines()]
        self.assertEqual(sorted(p.name.split("_x")[0] for p in nur), [na[1]] * 2)
        self.assertTrue(all(p.exists() for p in nur))
        val = [x for x in (self.wurzel / "aufrufe.txt").read_text().splitlines() if x.startswith("segment val")]
        self.assertEqual(len(val), 1)
        self.assertIn(f"data={z / 'altholz.yaml'}", val[0])
        self.assertIn("altholz-1/weights/best.pt", val[0])
        e = self.ruf("/api/training")[1]["ergebnis"]
        self.assertEqual((e["altholz"]["gesamt"]["maske"]["map50"], [x["k"] for x in e["altholz"]["klassen"]]), (0.746, [0, 8]))
        self.assertEqual(json.loads((z / "bericht.json").read_text())["altholz_val"], 2)
        train = [Path(x) for x in (z / "train.txt").read_text().splitlines()]
        # Kodytek-Auswahl 6 + Altholz 2 Kacheln + extra 2, kodytek-seg-1 steckt schon ganz in der Auswahl
        self.assertEqual(len(train), 6 + 2 + 2)
        self.assertTrue(all(p.exists() for p in train))
        self.assertFalse([p for p in train if "/test/" in str(p) or "/val/" in str(p)])

    def test_fehlerfreies_altholz_mit_kodytek(self):
        self.kodytek()
        _, na = self.balken(("1", "2"))
        self.assertEqual(self.ruf("/api/training", {"saetze": ["altholz", "kodytek"]})[0], 400)
        self.ruf("/api/label", {"name": na[0], "objekte": []})
        self.assertEqual(self.ruf("/api/training", {"saetze": ["altholz", "kodytek"]})[0], 400)     # Altholz ohne Prüfung
        self.ruf("/api/label", {"name": na[1], "objekte": []})
        self.assertEqual(self.ruf("/api/training", {"saetze": ["altholz", "kodytek"]})[0], 200)
        self.assertEqual(self.warte()["status"], "fertig")
        val = self.wurzel / "datensaetze" / "altholz-1" / "images" / "val"
        self.assertEqual(sum(p.name.startswith(na[1]) for p in val.iterdir()), 2)     # Altholz wird mitgeprüft
        self.yolo('[ "$2" = val ] && { echo kaputt; exit 1; }; exit 0')     # Training gut, Altholz-Prüfung nicht
        self.ruf("/api/training", {"saetze": ["altholz", "kodytek"]})
        lauf = self.warte()
        self.assertEqual((lauf["status"], lauf["fehler"]), ("fertig", "Altholz-Prüfung ging nicht: kaputt"))
        self.assertEqual(self.ruf("/api/training")[1]["ergebnis"]["name"], "altholz-2")


class TestAuswahl(unittest.TestCase):
    def test_seltene_zuerst_und_wiederholbar(self):
        je = {f"b{i}": {0} for i in range(100)} | {"s1": {7}, "s2": {7, 0}}
        w = sa.ziehen(je, 10, 5)
        self.assertTrue({"s1", "s2"} <= set(w))
        self.assertEqual((len(w), len(set(w))), (10, 10))
        self.assertEqual(w, sa.ziehen(je, 10, 5))

    def test_umriss_hin_und_zurueck(self):
        o = sa.objekte_aus("3 0.1 0.2 0.3 0.4 0.5 0.6\n")
        self.assertEqual(sa.objekte_aus(sa.zeilen_aus(o)), o)


if __name__ == "__main__":
    unittest.main()
