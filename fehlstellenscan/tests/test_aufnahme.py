"""Tests für die Fotobox-Aufnahme: Rechnung, Ablage, Auslösen über den echten Server auf localhost."""

import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from aufnahme import logik as l
from aufnahme import server as s

JPG = b"\xff\xd8\xff" + b"x" * 200
BALKEN = {"laenge_mm": 2000.0, "breite_mm": 120.0, "hoehe_mm": 200.0}


class TestLogik(unittest.TestCase):
    def test_abstand_haengt_von_der_seite_ab(self):
        self.assertEqual(l.plan(BALKEN, "1", 600, 0.7)["abstand_mm"], 480)
        self.assertEqual(l.plan(BALKEN, "2", 600, 0.7)["abstand_mm"], 400)
        self.assertEqual(l.plan(BALKEN, "1", 600, 0.7)["flaeche_mm"], 200)
        self.assertEqual(l.seite_info(120, 120, "2")["art"], "Seite")

    def test_abschnitte_decken_alles_ab(self):
        for laenge in (300, 577, 700, 2000, 5130):
            for abstand in (150, 300, 480, 560):
                feld = l.bildfeld(abstand, l.FAKTOR_START)[0]
                mitten = l.mitten(laenge, feld, l.schritt_vorschlag(feld))
                self.assertLessEqual(mitten[0] - feld / 2, 0)
                self.assertGreaterEqual(mitten[-1] + feld / 2, laenge)
                for a, b in zip(mitten, mitten[1:], strict=False):
                    self.assertLessEqual(b - a, feld * 0.75 + 0.01)

    def test_luecke_und_zu_hoch(self):
        self.assertTrue(l.plan(BALKEN, "2", 500, 0.7, 500)["luecke"])
        with self.assertRaises(ValueError):
            l.plan(BALKEN, "2", 220, 0.7)

    def test_messung_gibt_faktor_zurueck(self):
        feld = l.bildfeld(400, 0.72)[0]
        self.assertAlmostEqual(l.faktor_aus_messung(200 / feld, 200, 400), 0.72)
        with self.assertRaises(ValueError):
            l.faktor_aus_messung(0.001, 200, 400)

    def test_id_kommt_nie_wieder(self):
        self.assertEqual(l.neue_id(7, ["B002"]), ("B008", 8))
        self.assertEqual(l.neue_id(0, ["B011"]), ("B012", 12))

    def test_eingaben(self):
        for wert in (None, "12", True, -1, float("nan")):
            with self.assertRaises(ValueError):
                l.masse_pruefen({**BALKEN, "breite_mm": wert})

    def test_endung(self):
        self.assertEqual(l.endung_von(JPG), ".jpg")
        self.assertEqual(l.endung_von(b"\0\0\0\x18ftypheic0000"), ".heic")
        with self.assertRaises(ValueError):
            l.endung_von(b"<html>")


class TestServer(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.server = s.server_bauen(Path(self.ordner.name), "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        self.server.werk.port = self.port
        self.faden = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.faden.start()
        self.code = self.server.werk.einst["code"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.ordner.cleanup()

    def ruf(self, weg, daten=None, kopf=True, host=None):
        v = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        koepfe = {"X-Aufnahme": "1"} if kopf else {}
        if host:
            koepfe["Host"] = host
        body = daten if isinstance(daten, bytes) else None if daten is None else json.dumps(daten).encode()
        v.request("GET" if daten is None else "POST", weg, body=body, headers=koepfe)
        a = v.getresponse()
        inhalt = a.read()
        v.close()
        return a.status, json.loads(inhalt) if inhalt[:1] in (b"{", b"[") else inhalt

    def balken(self):
        return self.ruf("/api/balken", BALKEN)[1]["id"]

    def handy(self, antwort=JPG):
        """Wie der Kurzbefehl: warten, Foto machen, hochladen."""
        def lauf():
            self.ruf(f"/h/{self.code}/warten")
            self.ruf(f"/h/{self.code}/foto", antwort)
        f = threading.Thread(target=lauf, daemon=True)
        f.start()
        for _ in range(100):
            if self.server.werk.handy_da():
                return f
            time.sleep(0.02)
        self.fail("Handy nicht verbunden")

    def test_ausloesen_und_wiederholen(self):
        b = self.balken()
        for mal in (1, 2):
            f = self.handy()
            status, antwort = self.ruf("/api/ausloesen", {"balken": b, "seite": "2", "nr": 0})
            f.join(5)
            self.assertEqual(status, 200, antwort)
            foto = antwort["balken"]["seiten"]["2"]["fotos"]["0"]
            self.assertTrue((Path(self.ordner.name) / b / foto["datei"]).is_file())
            self.assertEqual(len(list((Path(self.ordner.name) / b / "verworfen").glob("*.jpg"))), mal - 1)
            time.sleep(1.1)

    def test_ohne_handy(self):
        self.assertEqual(self.ruf("/api/ausloesen", {"balken": self.balken(), "seite": "1", "nr": 0})[0], 409)

    def test_kein_foto_bricht_ab(self):
        b = self.balken()
        self.handy(b"<html>")
        status, antwort = self.ruf("/api/ausloesen", {"balken": b, "seite": "1", "nr": 0})
        self.assertEqual(status, 400)
        self.assertIn("kein Foto", antwort["fehler"])

    def test_foto_ohne_auftrag_geht_nicht_verloren(self):
        self.ruf(f"/h/{self.code}/foto", JPG)
        self.assertEqual(len(list((Path(self.ordner.name) / "unzugeordnet").iterdir())), 1)

    def test_plan_bleibt_nach_erstem_foto(self):
        b = self.balken()
        self.ruf(f"/api/datei?balken={b}&seite=1&nr=0", JPG)
        self.ruf("/api/einstellungen", {"kamera_rolle_mm": 700})
        stand = self.ruf("/api/stand")[1]["balken"][0]
        self.assertEqual(stand["seiten"]["1"]["plan"]["abstand_mm"], 480)
        self.assertEqual(stand["seiten"]["2"]["plan"]["abstand_mm"], 500)
        self.assertEqual(self.ruf("/api/balken", {**BALKEN, "id": b})[0], 400)
        self.assertEqual(self.ruf("/api/vorschub", {"balken": b, "seite": "1", "mm": 300})[0], 400)

    def test_loeschen_und_zurueck(self):
        b = self.balken()
        ziel = {"balken": b, "seite": "1", "nr": 0}
        self.ruf(f"/api/datei?balken={b}&seite=1&nr=0", JPG)
        ordner = Path(self.ordner.name) / b
        self.assertEqual(self.ruf("/api/loeschen", ziel)[1]["balken"]["seiten"]["1"]["fotos"], {})
        self.assertEqual(len(list(ordner.glob("*.jpg"))), 0)
        self.assertEqual(self.ruf("/api/loeschen", ziel)[0], 400)
        self.assertEqual(self.ruf("/api/zurueck", ziel)[0], 200)
        self.assertEqual(len(list(ordner.glob("*.jpg"))), 1)
        self.ruf("/api/loeschen", ziel)
        self.ruf(f"/api/datei?balken={b}&seite=1&nr=0", JPG)
        self.assertEqual(self.ruf("/api/zurueck", ziel)[0], 400)

    def test_zugang(self):
        self.assertEqual(self.ruf("/h/falsch/warten")[0], 403)
        self.assertEqual(self.ruf("/api/balken", BALKEN, kopf=False)[0], 403)
        self.assertEqual(self.ruf("/api/stand", host="boese.example")[0], 403)
        self.assertEqual(self.ruf("/foto/../einstellungen.json")[0], 404)
        self.assertEqual(self.ruf("/api/datei?balken=../x&seite=1&nr=0", JPG)[0], 400)

    def test_neustart_behaelt_alles(self):
        b = self.balken()
        neu = s.Werk(Path(self.ordner.name))
        self.assertEqual(neu.stand()["balken"][0]["id"], b)
        self.assertEqual(neu.einst["code"], self.code)


if __name__ == "__main__":
    unittest.main()
