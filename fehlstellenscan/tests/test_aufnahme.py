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

    def test_kontrolle(self):
        k = l.kontrolle(163 / 600, 600, 160)
        self.assertEqual(k["foto_mm"], 163.0)
        self.assertAlmostEqual(k["abweichung"], 1.88)
        with self.assertRaises(ValueError):
            l.kontrolle(0.0001, 600, 160)
        self.assertIsNone(l.kontrollen_mittel([]))
        m = l.kontrollen_mittel([{"abweichung": 1.0}, {"abweichung": -3.0}])
        self.assertEqual((m["anzahl"], m["mittel"], m["min"], m["max"]), (2, -1.0, -3.0, 1.0))

    def test_neu_skalieren(self):
        p = l.plan(BALKEN, "1", 600, 0.7)
        neu = l.neu_skalieren(p, 0.75)
        frisch = l.plan(BALKEN, "1", 600, 0.75, p["schritt_mm"])
        for feld in ("laengs_mm", "quer_mm", "voll_mm"):
            self.assertAlmostEqual(neu[feld], frisch[feld])
        self.assertEqual((neu["mitten_mm"], neu["faktor"]), (p["mitten_mm"], 0.75))

    def test_zuschnitt(self):
        voll = l.plan(BALKEN, "1", 600, 0.7)
        eng = l.plan(BALKEN, "1", 600, 0.7, None, [0.1, 0.0, 0.8, 0.9])
        self.assertAlmostEqual(eng["laengs_mm"], voll["laengs_mm"] * 0.8)
        self.assertAlmostEqual(eng["voll_mm"], voll["laengs_mm"])
        self.assertGreater(len(eng["mitten_mm"]), len(voll["mitten_mm"]) - 1)
        for schlecht in ([0, 0, 0.05, 1], [0.5, 0, 0.6, 1], [0, 0, 1], "x", [0, 0, float("nan"), 1]):
            with self.assertRaises(ValueError):
                l.zuschnitt_pruefen(schlecht)

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


class TestRasterFuersHandy(unittest.TestCase):
    def test_raster(self):
        self.assertEqual(l.raster_fuers_handy({"r": "0.12500", "w": "50", "g": "1"}),
                         {"anteil": 0.125, "text": "Raster 5 cm"})
        self.assertEqual(l.raster_fuers_handy({"r": "0.25", "w": "15", "g": "0"})["text"], "Raster etwa 1,5 cm")
        for q in ({}, {"r": "x", "w": "50"}, {"r": "0", "w": "50"}, {"r": "0.1", "w": "-5"}, {"r": "nan", "w": "50"}):
            self.assertIsNone(l.raster_fuers_handy(q))


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

    def test_kontrolle_speichern_und_zuruecknehmen(self):
        b = self.balken()
        weg = {"balken": b, "seite": "1", "nr": 0, "anteil": 0.1, "zollstock_mm": 50}
        self.assertEqual(self.ruf("/api/kontrolle", weg)[0], 400)
        self.ruf(f"/api/datei?balken={b}&seite=1&nr=0", JPG)
        faktor = self.server.werk.einst["faktor"]
        status, antwort = self.ruf("/api/kontrolle", weg)
        self.assertEqual(status, 200, antwort)
        voll = antwort["seiten"]["1"]["plan"]["voll_mm"]
        k = antwort["kontrollen"][0]
        self.assertEqual((k["seite"], k["foto_mm"]), ("1", round(0.1 * voll, 1)))
        self.assertEqual(antwort["pruefung"]["anzahl"], 1)
        self.assertEqual(self.server.werk.einst["faktor"], faktor)
        antwort = self.ruf("/api/kontrolle", {"balken": b, "weg": True})[1]
        self.assertEqual((antwort["kontrollen"], antwort["pruefung"]), ([], None))
        self.assertEqual(self.ruf("/api/kontrolle", {"balken": b, "weg": True})[0], 400)

    def test_massstab_gilt_fuer_gemachte_fotos(self):
        b = self.balken()
        self.ruf(f"/api/datei?balken={b}&seite=1&nr=0", JPG)
        vorher = self.ruf("/api/stand")[1]["balken"][0]["seiten"]["1"]["plan"]
        status, antwort = self.ruf("/api/massstab", {"balken": b, "seite": "1", "anteil": 0.5, "strecke_mm": 300})
        self.assertEqual(status, 200, antwort)
        nachher = antwort["balken"][0]["seiten"]["1"]["plan"]
        self.assertAlmostEqual(nachher["faktor"], antwort["einstellungen"]["faktor"])
        self.assertAlmostEqual(nachher["voll_mm"] * 0.5, 300)
        self.assertEqual(nachher["mitten_mm"], vorher["mitten_mm"])

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

    def handyruf(self, was, daten=None, **koepfe):
        v = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        v.request("GET" if daten is None else "POST", f"/h/{self.code}/{was}", body=daten,
                  headers={k.replace("_", "-"): w for k, w in koepfe.items()})
        a = v.getresponse()
        return a.status, a.read()

    def test_app_befehle_und_foto(self):
        self.assertEqual(self.ruf("/api/kamera", {"art": "einmessen"})[0], 409)
        self.handyruf("live", JPG, X_Zustand='{"iso": 50}')
        self.assertEqual(self.ruf("/live.jpg?1&r=0.1&w=100&g=1")[1], JPG)
        def app():
            return json.loads(self.handyruf("live", JPG, X_Zustand='{"iso": 50}')[1])["raster"]
        self.assertEqual(app(), {"anteil": 0.1, "text": "Raster 10 cm"})
        self.ruf("/live.jpg?2")
        self.assertIsNone(app())
        self.assertEqual(self.ruf("/api/stand")[1]["app"], {"iso": 50})
        self.assertEqual(self.ruf("/api/kamera", {"art": "ev", "wert": 9})[0], 400)
        self.assertEqual(self.ruf("/api/kamera", {"art": "ev", "wert": -0.5})[0], 200)
        self.assertEqual(json.loads(self.handyruf("warten", X_App="1")[1]), {"art": "ev", "wert": -0.5})
        b, antwort = self.balken(), []
        f = threading.Thread(target=lambda: antwort.append(
            self.ruf("/api/ausloesen", {"balken": b, "seite": "1", "nr": 0})))
        f.start()
        befehl = json.loads(self.handyruf("warten", X_App="1")[1])
        self.assertEqual((befehl["art"], befehl["fokus"]), ("foto", f"{b}-1"))
        self.handyruf("foto", JPG, X_Auftrag="alt")            # verspätet: darf nicht zugeordnet werden
        self.handyruf("foto", JPG, X_Auftrag=befehl["id"], X_Foto='{"iso": 55}')
        f.join(5)
        self.assertEqual(antwort[0][1]["balken"]["seiten"]["1"]["fotos"]["0"]["kamera"], {"iso": 55})
        self.assertEqual(len(list((Path(self.ordner.name) / "unzugeordnet").iterdir())), 1)

    def test_app_fehler_bricht_ab(self):
        self.handyruf("live", JPG)
        b, antwort = self.balken(), []
        f = threading.Thread(target=lambda: antwort.append(
            self.ruf("/api/ausloesen", {"balken": b, "seite": "1", "nr": 0})))
        f.start()
        befehl = json.loads(self.handyruf("warten", X_App="1")[1])
        self.handyruf("fehler", b"Kamera belegt", X_Auftrag=befehl["id"])
        f.join(5)
        self.assertEqual(antwort[0][0], 400)

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
