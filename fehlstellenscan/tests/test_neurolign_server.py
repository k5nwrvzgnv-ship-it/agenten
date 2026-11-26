"""Neurolign im Servermodus (neurolign.meldro.de): Zugang, Rechte, Hochladen, Labeln mit Namen."""

import http.client
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from aufnahme import server as s
from aufnahme import zugang as z

HOST = "neurolign.meldro.de"


def jpeg(farbe=(120, 90, 60), groesse=(64, 48)) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", groesse, farbe).save(puffer, "JPEG")
    return puffer.getvalue()


class Zugang(unittest.TestCase):
    def test_nutzer_nur_von_caddy_mit_host(self):
        self.assertEqual(z.nutzer_aus("127.0.0.1", HOST, "henri"), "henri")
        self.assertEqual(z.nutzer_aus("127.0.0.1", HOST + ":443", "Felix "), "felix")
        self.assertIsNone(z.nutzer_aus("192.168.1.5", HOST, "jan"))
        self.assertIsNone(z.nutzer_aus("127.0.0.1", "localhost", "jan"))
        self.assertIsNone(z.nutzer_aus("127.0.0.1", HOST, "mallory"))
        self.assertIsNone(z.nutzer_aus("127.0.0.1", HOST, None))
        self.assertIsNone(z.nutzer_aus("127.0.0.1", f"[::1]:{HOST}", "jan"))

    def test_rechte(self):
        self.assertTrue(z.darf("jan", z.VERWALTEN))
        for wer in ("henri", "felix"):
            self.assertTrue(z.darf(wer, z.HOCHLADEN) and z.darf(wer, z.LABELN))
            self.assertFalse(z.darf(wer, z.VERWALTEN))
            self.assertEqual(z.post_erlaubt(wer, "/api/foto-weg")[0], 403)
        self.assertFalse(z.darf(None, z.ANSEHEN))
        for weg in ("/api/training", "/api/loeschen", "/api/ausloesen", "/api/einstellungen", "/api/teil"):
            self.assertEqual(z.post_erlaubt("jan", weg)[0], 404)
        self.assertIsNone(z.post_erlaubt("henri", "/api/hochladen"))

    def test_herkunft(self):
        self.assertTrue(z.herkunft_ok("https://neurolign.meldro.de", None))
        self.assertTrue(z.herkunft_ok(None, "https://neurolign.meldro.de/labeln"))
        self.assertFalse(z.herkunft_ok("https://boese.example", "https://neurolign.meldro.de/"))
        self.assertFalse(z.herkunft_ok("http://neurolign.meldro.de", None))
        self.assertFalse(z.herkunft_ok(None, None))


class Servermodus(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.ablage = Path(self.ordner.name) / "aufnahmen"
        self.server = s.server_bauen(self.ablage, "127.0.0.1", 0, True, Path(sys.executable))
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.ordner.cleanup()

    def ruf(self, weg, daten=None, wer="henri", herkunft=f"https://{HOST}", host=HOST, roh=None):
        v = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        kopf = {"Host": host}
        if wer:
            kopf["X-Nutzer"] = wer
        if daten is None and roh is None:
            v.request("GET", weg, headers=kopf)
        else:
            kopf |= {"X-Aufnahme": "1"} | ({"Origin": herkunft} if herkunft else {})
            v.request("POST", weg, body=roh if roh is not None else json.dumps(daten), headers=kopf)
        a = v.getresponse()
        inhalt = a.read()
        v.close()
        try:
            return a.status, json.loads(inhalt)
        except ValueError:
            return a.status, inhalt

    def balken(self, wer="henri"):
        st, b = self.ruf("/api/balken", {"laenge_mm": 1200, "breite_mm": 120, "hoehe_mm": 100, "holzart": "Fichte"}, wer)
        self.assertEqual(st, 200, b)
        return b["id"]

    def test_ohne_anmeldung_nichts(self):
        self.assertEqual(self.ruf("/", wer=None)[0], 403)
        self.assertEqual(self.ruf("/api/stand", host="localhost")[0], 403)
        self.assertEqual(self.ruf("/api/balken", {"laenge_mm": 1}, wer=None)[0], 403)

    def test_seiten_ohne_fotobox_und_training(self):
        st, html = self.ruf("/")
        self.assertEqual(st, 200)
        self.assertIn(b"hochladen.js", html)
        st, html = self.ruf("/labeln")
        self.assertNotIn(b"/training", html)
        self.assertIn(b'<a href="/">Hochladen</a>', html)
        for weg in ("/training", "/api/training", "/live.jpg", "/h/abc/warten"):
            self.assertEqual(self.ruf(weg)[0], 404, weg)
        self.assertEqual(self.ruf("/api/saetze")[1], {"kodytek": 0})

    def test_fremde_herkunft_abgelehnt(self):
        self.assertEqual(self.ruf("/api/balken", {"laenge_mm": 1200}, herkunft="https://boese.example")[0], 403)
        self.assertEqual(self.ruf("/api/balken", {"laenge_mm": 1200}, herkunft=None)[0], 403)

    def test_hochladen_labeln_mit_namen(self):
        kennung = self.balken("felix")
        st, stand = self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg(), wer="felix")
        self.assertEqual(st, 200, stand)
        self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg((10, 10, 10)), wer="henri")
        b = next(x for x in self.ruf("/api/stand")[1]["balken"] if x["id"] == kennung)
        self.assertEqual(b["von"], "felix")
        self.assertEqual([f["von"] for f in b["seiten"]["1"]["fotos"]], ["felix", "henri"])
        self.assertTrue((self.ablage / kennung / b["seiten"]["1"]["fotos"][0]["datei"]).exists())

        bilder = self.ruf("/api/bilder")[1]
        self.assertEqual(len(bilder), 2)
        name = bilder[0]["name"]
        st, inhalt = self.ruf(f"/zuschnitt/{name}_k.jpg")
        self.assertEqual(st, 200, inhalt)
        umriss = {"k": 0, "ok": True, "p": [[0.1, 0.1], [0.3, 0.1], [0.2, 0.3]]}
        st, a = self.ruf("/api/label", {"name": name, "stand": None, "objekte": [umriss]}, wer="henri")
        self.assertEqual(st, 200, a)
        label = json.loads((self.ablage / kennung / "labels" / f"{name}.json").read_text())
        self.assertEqual(label["von"], "henri")
        # Felix hatte das Foto vor Henris Speichern geladen: sein Stand ist alt, kein stilles Überschreiben
        st, f = self.ruf("/api/label", {"name": name, "stand": None, "objekte": []}, wer="felix")
        self.assertEqual(st, 400)
        self.assertIn("henri", f["fehler"])
        st, _ = self.ruf("/api/label", {"name": name, "stand": a["zeit"], "objekte": []}, wer="felix")
        self.assertEqual(st, 200)

    def test_henri_darf_nicht_verwalten(self):
        kennung = self.balken()
        self.ruf(f"/api/hochladen?balken={kennung}&seite=2", roh=jpeg())
        self.assertEqual(self.ruf("/api/foto-weg", {"balken": kennung, "seite": "2", "nr": 0})[0], 403)
        self.assertEqual(self.ruf("/api/balken", {"id": kennung, "laenge_mm": 900, "breite_mm": 100,
                                                  "hoehe_mm": 100})[0], 400)
        self.assertEqual(self.ruf("/api/training", {})[0], 404)
        self.assertEqual(self.ruf("/api/loeschen", {})[0], 404)
        st, stand = self.ruf("/api/foto-weg", {"balken": kennung, "seite": "2", "nr": 0}, wer="jan")
        self.assertEqual(st, 200, stand)
        self.assertEqual(stand["balken"][0]["seiten"]["2"]["fotos"], [])
        self.assertTrue(stand["verwalten"])

    def test_hochladen_prueft_eingaben(self):
        kennung = self.balken()
        self.assertEqual(self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=b"kein bild")[0], 400)
        heic = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20
        st, f = self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=heic)
        self.assertEqual(st, 400)
        self.assertIn("HEIC", f["fehler"])
        for q in ("balken=../x&seite=1", f"balken={kennung}&seite=5", "balken=B999&seite=1"):
            self.assertEqual(self.ruf(f"/api/hochladen?{q}", roh=jpeg())[0], 400, q)
        self.assertEqual(self.ruf("/foto/B001/..%2F..%2Feinstellungen.json")[0], 404)

    def test_fotobox_seite_bleibt(self):
        kennung = self.balken()
        b = json.loads((self.ablage / kennung / "balken.json").read_text())
        b["seiten"]["3"] = {"schritt_mm": None, "plan": {"zuschnitt": None, "faktor": 1, "laengs_mm": 300,
                                                         "mitten_mm": [150]}, "fotos": {"0": {"datei": "x.jpg"}}}
        (self.ablage / kennung / "balken.json").write_text(json.dumps(b))
        st, f = self.ruf(f"/api/hochladen?balken={kennung}&seite=3", roh=jpeg())
        self.assertEqual(st, 400)
        self.assertIn("Fotobox", f["fehler"])


class MacModusUnveraendert(unittest.TestCase):
    def test_hochgeladene_seite_stoert_die_fotobox_nicht(self):
        with tempfile.TemporaryDirectory() as d:
            w = s.Werk(Path(d))
            b = w.balken_speichern({"laenge_mm": 1200, "breite_mm": 120, "hoehe_mm": 100})
            w.hochladen(b["id"], "1", jpeg(), "henri")
            st = w.stand()
            seite = st["balken"][0]["seiten"]["1"]
            self.assertIsNone(seite["plan"])
            self.assertEqual(len(seite["fotos"]), 1)
            self.assertIsNotNone(st["balken"][0]["seiten"]["2"]["plan"])
            with self.assertRaises(ValueError):
                w.foto_ablegen(b["id"], "1", 0, jpeg())


if __name__ == "__main__":
    unittest.main()
