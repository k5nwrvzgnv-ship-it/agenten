"""Vorlabeln per Modell: reine Logik (vorlabeln.py), Lauf auf dem Mac mit yolo-Attrappe, Weg Server -> Tunnel -> Mac
-> zurück in die Labels des Servers (docs/plan-vorlabeln.md)."""

import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from PIL import Image

from aufnahme import bilder as bi
from aufnahme import klassen as kls
from aufnahme import server as s
from aufnahme import tunnel as t
from aufnahme import vorlabeln as vl
from aufnahme import zugang as z

QUADRAT = [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]
# yolo-Attrappe: schreibt je Kachel zwei Objekte (Kodytek-Nummer 4 = crack, 9 = overgrown) und eins mit Nummer 99,
# die das Modell nicht kennt. Gibt "image i/n" aus wie ultralytics.
YOLO = """#!/bin/sh
echo "$*" >> "AUFRUFE"
for a in "$@"; do case $a in project=*) p=${a#project=};; name=*) n=${a#name=};; source=*) q=${a#source=};; esac; done
mkdir -p "$p/$n/labels"
i=0; m=$(ls "$q"/*.jpg | wc -l)
for f in "$q"/*.jpg; do i=$((i+1)); b=$(basename "$f" .jpg); echo "image $i/$m $f: 1280x1280"
printf '4 0.40 0.40 0.60 0.40 0.60 0.60 0.40 0.60 0.81\\n9 0.05 0.05 0.10 0.05 0.10 0.10 0.30\\n99 0.2 0.2 0.3 0.2 0.3 0.3 0.5\\n' > "$p/$n/labels/$b.txt"
done
ENDE
"""


def objekt(p, ok=False, q=None, k=4, c=None):
    o = {"k": k, "ok": ok, "p": p}
    if q:
        o["q"] = q
    if c is not None:
        o["c"] = c
    return o


class Logik(unittest.TestCase):
    def test_raster_wie_beim_training(self):
        for n in (500, 1280, 1281, 2000, 4032, 6048, 8064):
            self.assertEqual(vl.raster(n), bi.raster(n), n)

    def test_kerne_lueckenlos(self):
        for n in (900, 3000, 6048):
            a = vl.raster(n)
            k = vl.kerne(a, n)
            self.assertEqual((k[0][0], k[-1][1]), (0.0, float(n)))
            for (_, hi), (lo, _) in zip(k, k[1:], strict=False):
                self.assertEqual(hi, lo)
            for (lo, hi), x0 in zip(k, a, strict=True):         # Kern liegt in der Kachel
                self.assertTrue(x0 <= lo < hi <= x0 + min(vl.KACHEL, n))

    def test_zeilen_lesen(self):
        z_ = vl.zeilen_lesen("4 0.1 0.1 0.2 0.1 0.2 0.2 0.9\n5 0.1 0.1 0.2 0.1 0.2 0.2\nkaputt\n3 1 2\n")
        self.assertEqual(z_[0], (4, [(0.1, 0.1), (0.2, 0.1), (0.2, 0.2)], 0.9))
        self.assertEqual((z_[1][0], z_[1][2]), (5, None))
        self.assertEqual(len(z_), 2)

    def test_objekt_in_der_ueberlappung_nur_einmal(self):
        # Foto 2000 px breit: zwei Kacheln (0 und 720), Überlappung 720-1280, Kerngrenze 1000
        kach = vl.kacheln("F", 2000, 1000)
        self.assertEqual([k_["x0"] for k_ in kach], [0, 720])
        # Objekt bei x 1100-1200 px: in Kachel 0 bei 1100/1280, in Kachel 1 bei 380/1280
        zeile = "{} {a} 0.4 {b} 0.4 {b} 0.6 {a} 0.6 0.7\n"
        texte = {kach[0]["name"]: zeile.format(4, a=1100 / 1280, b=1200 / 1280),
                 kach[1]["name"]: zeile.format(4, a=380 / 1280, b=480 / 1280)}
        o = vl.foto_objekte("F", 2000, 1000, texte, {4: 4}, "m")
        self.assertEqual(len(o), 1)
        self.assertAlmostEqual(o[0]["p"][0][0], 0.55, 4)
        self.assertEqual((o[0]["k"], o[0]["ok"], o[0]["c"], o[0]["q"]), (4, False, 0.7, "m"))
        self.assertEqual(vl.foto_objekte("F", 2000, 1000, texte, {}, "m"), [])     # Klasse unbekannt

    def test_ueberdeckt(self):
        gross = [[0, 0], [1, 0], [1, 1], [0, 1]]
        self.assertTrue(vl.ueberdeckt(QUADRAT, gross))
        self.assertTrue(vl.ueberdeckt(gross, QUADRAT))            # gemessen am kleineren
        self.assertFalse(vl.ueberdeckt(QUADRAT, [[0.25, 0.25], [0.5, 0.25], [0.5, 0.5], [0.25, 0.5]]))
        self.assertFalse(vl.ueberdeckt(QUADRAT, [[0.5, 0.5], [0.6, 0.5], [0.6, 0.6]]))

    def test_einfuegen_regeln(self):
        ok = objekt(QUADRAT, ok=True, q="alt", k=17)
        hand = objekt([[0.6, 0.6], [0.7, 0.6], [0.7, 0.7], [0.6, 0.7]])
        alt_vor = objekt([[0.8, 0.1], [0.9, 0.1], [0.9, 0.2]], q="kodytek-seg1-n1280")
        neu_auf_ok = objekt([[0.12, 0.12], [0.28, 0.12], [0.28, 0.28]], q="m", c=0.9)
        neu_frei = objekt([[0.4, 0.8], [0.5, 0.8], [0.5, 0.9]], q="m", c=0.5)
        objekte, zahl = vl.einfuegen([ok, hand, alt_vor], [neu_auf_ok, neu_frei])
        self.assertEqual(objekte, [ok, hand, neu_frei])
        self.assertEqual(zahl, {"neu": 1, "verdeckt": 1, "ersetzt": 1})

    def test_namen_und_zuordnung(self):
        self.assertEqual(vl.namen_aus_yaml("path: x\nnames:\n  0: live_knot\n  4: 'crack'\nnc: 2\n"),
                         {0: "live_knot", 4: "crack"})
        self.assertEqual(vl.namen_aus_yaml("names:\n- live_knot\n- dead_knot\n"), {0: "live_knot", 1: "dead_knot"})
        self.assertEqual(vl.namen_aus_yaml("names: ['a', 'b']\n"), {0: "a", 1: "b"})
        self.assertEqual(vl.namen_aus_yaml("names: {0: a, 2: c}\n"), {0: "a", 2: "c"})
        d = kls.standard()
        kls.weg(d, 9, 0, 0)                                     # overgrown gelöscht
        self.assertEqual(vl.zuordnung({0: "live_knot", 4: "crack", 9: "overgrown", 5: "unbekannt"}, d),
                         {0: 0, 4: 4})
        # altholz-Modell: Nummer = ID, auch wenn eine Klasse umbenannt ist (Schlüssel bleibt)
        kls.aendern(d, 17, "Klebefuge", None, ...)
        self.assertEqual(vl.zuordnung(dict(enumerate(kls.schluessel_liste(d))), d)[17], 17)

    def test_modell_wahl(self):
        k = {"name": vl.STANDARD_MODELL, "zahl": None, "zeit": 1}
        self.assertEqual(vl.modell_wahl([k]), vl.STANDARD_MODELL)
        self.assertIsNone(vl.modell_wahl([]))
        a1 = {"name": "altholz-1", "zahl": 0.30, "zeit": 2}
        a2 = {"name": "altholz-2", "zahl": 0.25, "zeit": 3}
        a3 = {"name": "altholz-3", "zahl": 0.30, "zeit": 4}
        ohne = {"name": "altholz-4", "zahl": None, "zeit": 5}
        self.assertEqual(vl.modell_wahl([k, a1, a2, ohne]), "altholz-1")
        self.assertEqual(vl.modell_wahl([k, a1, a2, a3, ohne]), "altholz-3")   # Gleichstand: neuer
        self.assertEqual(vl.modell_wahl([k, ohne]), vl.STANDARD_MODELL)

    def test_fortschritt(self):
        self.assertEqual(vl.fortschritt("x\nimage 3/40 /a.jpg\nimage 4/40 /b.jpg: 1280x1280"), (4, 40))
        self.assertIsNone(vl.fortschritt(""))


class Mac(unittest.TestCase):
    """Neurolign auf dem Mac: Lauf mit yolo-Attrappe, Ergebnis direkt in die Labels (Mac-Modus)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name) / "mac"
        self.server = self.mac_bauen(self.wurzel)
        self.werk = self.server.werk
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    @staticmethod
    def mac_bauen(wurzel: Path, port=0):
        (wurzel / ".venv" / "bin").mkdir(parents=True)
        python = wurzel / ".venv" / "bin" / "python"
        python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        python.chmod(0o755)
        y = wurzel / ".venv" / "bin" / "yolo"
        y.write_text(YOLO.replace("AUFRUFE", str(wurzel / "aufrufe.txt")).replace("ENDE", "exit 0"))
        os.chmod(y, 0o755)
        lauf = wurzel / "runs" / "segment" / vl.STANDARD_MODELL
        (lauf / "weights").mkdir(parents=True)
        (lauf / "weights" / "best.pt").write_bytes(b"x")
        (lauf / "args.yaml").write_text("task: segment\ndata: datensaetze/kodytek-seg-1/data.yaml\nimgsz: 1280\n")
        (wurzel / "datensaetze" / "kodytek-seg-1").mkdir(parents=True)
        (wurzel / "datensaetze" / "kodytek-seg-1" / "data.yaml").write_text(
            "path: x\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(
                ["live_knot", "dead_knot", "knot_missing", "knot_with_crack", "crack", "quartzity", "resin", "marrow",
                 "blue_stain", "overgrown"])))
        return s.server_bauen(wurzel / "aufnahmen", "127.0.0.1", port)

    @staticmethod
    def balken(werk, breite=2000):
        b = werk.balken_speichern({"laenge_mm": 1000.0, "breite_mm": 200.0, "hoehe_mm": 135.0, "holzart": ""})
        bild = werk.ordner.parent / "f.jpg"
        Image.new("RGB", (breite, 1000), (120, 90, 60)).save(bild)
        for x in ("1", "2"):
            werk.foto_ablegen(b["id"], x, 0, bild.read_bytes())
        return b["id"], [f["name"] for f in werk.kette.alle() if f["balken"] == b["id"]]

    def ruf(self, weg, daten=None):
        c = http.client.HTTPConnection("localhost", self.server.server_address[1], timeout=20)
        c.request("GET" if daten is None else "POST", weg, None if daten is None else json.dumps(daten),
                  {"X-Aufnahme": "1"})
        a = c.getresponse()
        roh = a.read()
        c.close()
        return a.status, json.loads(roh)

    def warte(self):
        for _ in range(400):
            st = self.ruf("/api/vorlabeln")[1]
            if st["lauf"] and st["lauf"]["status"] not in ("holen", "rechnen"):
                return st
            time.sleep(0.05)
        self.fail("Vorlabeln endet nicht")

    def test_stand_und_modell(self):
        st, stand = self.ruf("/api/vorlabeln")
        self.assertEqual(st, 200)
        self.assertEqual((stand["mac"], stand["modell"], stand["modelle"], stand["lauf"]),
                         (True, vl.STANDARD_MODELL, [vl.STANDARD_MODELL], None))

    def test_balken_vorlabeln_mit_regeln(self):
        b, namen = self.balken(self.werk)
        # Foto 1: ein bestätigtes Objekt genau dort, wo die Attrappe ein Riss-Objekt meldet (Kachel 0, 40-60 %)
        x0, x1 = 0.4 * 1280 / 2000, 0.6 * 1280 / 2000
        bestaetigt = {"k": 17, "ok": True, "p": [[x0, 0.4 * 1000 / 1000], [x1, 0.4], [x1, 0.6], [x0, 0.6]]}
        self.werk.kette.speichern({"name": namen[0], "objekte": [bestaetigt]})
        st, stand = self.ruf("/api/vorlabeln", {"balken": [b]})
        self.assertEqual(st, 200, stand)
        stand = self.warte()
        self.assertEqual(stand["lauf"]["status"], "fertig", stand)
        e = stand["lauf"]["balken"][b]
        self.assertEqual(e["status"], "fertig")
        self.assertNotIn("ergebnis", e)                         # Mac-Modus: gleich eingefügt
        aufruf = (self.wurzel / "aufrufe.txt").read_text()
        self.assertIn("segment predict", aufruf)
        self.assertIn("save_conf=True", aufruf)
        l0 = self.werk.kette.label(self.werk.kette.foto(namen[0]))
        l1 = self.werk.kette.label(self.werk.kette.foto(namen[1]))
        self.assertEqual(l0["objekte"][0], bestaetigt | {"p": l0["objekte"][0]["p"]})
        # zwei Kacheln (0 und 720 px) je zwei bekannte Objekte (99 kennt das Modell nicht); das kleine bei 5-10 %
        # der zweiten Kachel liegt in der Überlappung außerhalb ihres Kerns (gehört der ersten), also drei je Foto.
        # Das Riss-Objekt der ersten Kachel auf Foto 1 liegt unter dem bestätigten.
        self.assertEqual(len(l1["objekte"]), 3)
        self.assertEqual(len(l0["objekte"]), 1 + 2)
        o = l1["objekte"][0]
        self.assertEqual((o["ok"], o["q"], o["c"]), (False, vl.STANDARD_MODELL, 0.81))
        self.assertEqual({x["k"] for x in l1["objekte"]}, {4, 9})
        self.assertEqual(l1["von"], "vorlabel")
        self.assertFalse((self.wurzel / "vorlabeln").exists() and any((self.wurzel / "vorlabeln").iterdir()))
        # zweiter Lauf ersetzt die offenen, Zahl bleibt gleich
        self.ruf("/api/vorlabeln", {"balken": [b], "fotos": [namen[1]]})
        self.warte()
        self.assertEqual(len(self.werk.kette.label(self.werk.kette.foto(namen[1]))["objekte"]), 3)

    def test_pruefbalken_gesperrt_ausser_bewusst(self):
        b, namen = self.balken(self.werk)
        self.werk.kette.teil_setzen({"balken": b, "teil": "val"})
        self.ruf("/api/vorlabeln", {"balken": [b]})
        self.assertEqual(self.warte()["lauf"]["balken"][b]["status"], "gesperrt")
        self.assertIsNone(self.werk.kette.label(self.werk.kette.foto(namen[0])))
        self.ruf("/api/vorlabeln", {"balken": [b], "pruefung": True})
        self.assertEqual(self.warte()["lauf"]["balken"][b]["status"], "fertig")

    def test_eingaben_und_sperren(self):
        self.assertEqual(self.ruf("/api/vorlabeln", {"balken": "B001"})[0], 400)
        self.assertEqual(self.ruf("/api/vorlabeln", {"balken": ["../x"]})[0], 400)
        self.assertEqual(self.ruf("/api/vorlabeln", {"balken": ["B001"], "modell": "gibtsnicht"})[0], 400)
        st, stand = self.ruf("/api/vorlabeln", {"balken": ["B777"]})
        self.assertEqual(st, 200)
        self.assertEqual(self.warte()["lauf"]["balken"]["B777"]["status"], "fehler")
        self.werk.kette.lauf = {"status": "training"}
        self.assertIn("Training", self.ruf("/api/vorlabeln", {"balken": ["B001"]})[1]["fehler"])

    def test_yolo_scheitert(self):
        b, _ = self.balken(self.werk)
        (self.wurzel / ".venv" / "bin" / "yolo").write_text("#!/bin/sh\necho 'CUDA kaputt'\nexit 1\n")
        self.ruf("/api/vorlabeln", {"balken": [b]})
        e = self.warte()["lauf"]["balken"][b]
        self.assertEqual(e["status"], "fehler")
        self.assertIn("kaputt", e["fehler"])


SCHLUESSEL = "v" * 32


class UeberTunnel(unittest.TestCase):
    """Server -> Tunnel -> Mac und zurück, alles in einem Prozess wie in test_neurolign_server.Tunnel."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.mac = Mac.mac_bauen(d / "mac")
        self.eingang = s.tunnel_eingang_bauen(self.mac.werk, 0, SCHLUESSEL)
        self.server = s.server_bauen(d / "server" / "aufnahmen", "127.0.0.1", 0, True, Path(sys.executable),
                                     schluessel=SCHLUESSEL, mac_port=self.eingang.server_address[1])
        for x in (self.mac, self.eingang, self.server):
            threading.Thread(target=x.serve_forever, daemon=True).start()
        # Der Abgleich holt den Balken vom Server: hier ein Python-Kopierer statt rsync
        self.b, self.namen = Mac.balken(self.server.werk)
        skript = d / "abgleich.sh"
        skript.write_text(f'[ "$1" = runter ] && cp -r "{d}/server/aufnahmen/{self.b}" "{d}/mac/aufnahmen/"\n')
        self.mac.werk.abgleich = skript
        self.hand = {"k": 12, "ok": True, "p": [[0.9, 0.9], [0.95, 0.9], [0.95, 0.95]]}
        self.server.werk.kette.speichern({"name": self.namen[0], "objekte": [self.hand]}, "felix")

    def tearDown(self):
        for x in (self.mac, self.eingang, self.server):
            x.shutdown()
            x.server_close()
        self.tmp.cleanup()

    def vom_server(self, methode, weg, daten=None, wer="henri"):
        kopf = {"Host": z.HOST, "X-Nutzer": wer}
        if methode == "POST":
            kopf |= {"X-Aufnahme": "1", "Origin": f"https://{z.HOST}"}
        v = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=20)
        v.request(methode, weg, body=None if daten is None else json.dumps(daten), headers=kopf)
        a = v.getresponse()
        inhalt = json.loads(a.read())
        v.close()
        return a.status, inhalt

    def test_ergebnis_landet_auf_dem_server(self):
        st, stand = self.vom_server("POST", "/api/vorlabeln", {"balken": [self.b]})
        self.assertEqual(st, 200, stand)
        for _ in range(400):                    # der Abholer des Servers arbeitet auch ohne offene Seite
            l1 = self.server.werk.kette.label(self.server.werk.kette.foto(self.namen[1]))
            if l1:
                break
            time.sleep(0.05)
        else:
            self.fail("Vorlabel kamen nicht auf dem Server an")
        self.assertEqual(len(l1["objekte"]), 3)
        self.assertEqual(l1["objekte"][0]["q"], vl.STANDARD_MODELL)
        l0 = self.server.werk.kette.label(self.server.werk.kette.foto(self.namen[0]))
        self.assertEqual(l0["objekte"][0], self.hand)               # bestätigt bleibt
        for _ in range(100):
            st, stand = self.vom_server("GET", "/api/vorlabeln")
            if stand["lauf"]["status"] == "fertig" and "ergebnis" not in json.dumps(stand):
                break
            time.sleep(0.05)
        self.assertEqual(stand["lauf"]["balken"][self.b]["status"], "fertig")
        self.assertEqual(stand["lauf"]["balken"][self.b]["neu"], 6)            # Handobjekt liegt abseits, je Foto 3
        self.assertNotIn("ergebnis", self.mac.werk.kette.vlauf["balken"][self.b])   # Mac hat vergessen
        # Labels auf dem Mac bleiben unberührt (der Server ist die Ablage)
        self.assertIsNone(self.mac.werk.kette.label(self.mac.werk.kette.foto(self.namen[1])))

    def test_mac_aus_und_eingang(self):
        port = self.eingang.server_address[1]
        v = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        v.request("POST", "/api/vorlabeln-ab", body="{}", headers={})
        self.assertEqual(v.getresponse().status, 403)                # ohne Schlüssel nicht
        v.close()
        self.assertIn(("POST", "/api/vorlabeln"), t.WEGE)
        self.assertEqual(z.post_erlaubt("felix", "/api/vorlabeln-ab"), (404, "Gibt es hier nicht."))
        self.eingang.shutdown()
        self.eingang.server_close()
        st, f = self.vom_server("GET", "/api/vorlabeln")
        self.assertEqual((st, f["mac"]), (503, False))
        st, f = self.vom_server("POST", "/api/vorlabeln", {"balken": [self.b]})
        self.assertEqual((st, f["mac"]), (503, False))
        self.eingang = s.tunnel_eingang_bauen(self.mac.werk, 0, SCHLUESSEL)     # für tearDown
        threading.Thread(target=self.eingang.serve_forever, daemon=True).start()


if __name__ == "__main__":
    unittest.main()
