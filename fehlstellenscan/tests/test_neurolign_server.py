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
from aufnahme import tunnel as t
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
        # Henri und Felix sind vollwertige Kollegen (Jan 26.11.2026)
        for wer in ("jan", "henri", "felix"):
            for recht in (z.ANSEHEN, z.HOCHLADEN, z.LABELN, z.VERWALTEN):
                self.assertTrue(z.darf(wer, recht), (wer, recht))
            self.assertIsNone(z.post_erlaubt(wer, "/api/foto-weg"))
        self.assertFalse(z.darf(None, z.ANSEHEN))
        self.assertFalse(z.darf("mallory", z.ANSEHEN))
        for weg in ("/api/loeschen", "/api/ausloesen", "/api/einstellungen", "/api/zuschnitt", "/api/balken-weg"):
            self.assertIsNone(z.post_erlaubt("henri", weg))       # dieselbe Oberfläche wie am Mac
        self.assertEqual(z.post_erlaubt("jan", "/h/abc/foto")[0], 404)
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

    def test_dieselben_seiten_wie_am_mac(self):
        # Jan 26.11.2026: die Domain ist ein Klon der Mac-Oberfläche
        for weg, datei in (("/", "index.html"), ("/galerie", "galerie.html"), ("/koerper", "koerper.html"),
                           ("/labeln", "labeln.html"), ("/training", "training.html")):
            st, html = self.ruf(weg)
            self.assertEqual(st, 200, weg)
            self.assertEqual(html, (s.SEITE / datei).read_bytes(), weg)
        for weg in ("/live.jpg", "/h/abc/warten"):
            self.assertEqual(self.ruf(weg)[0], 404, weg)
        self.assertEqual(self.ruf("/api/saetze")[1], {"kodytek": 0})
        st, stand = self.ruf("/api/stand")
        self.assertEqual((st, stand["adressen"], stand["app"], stand["ich"]), (200, [], None, "henri"))

    def test_kodytek_auswahl_aus_dem_abgleich(self):
        # neurolign_abgleich.sh hoch legt die Bilder unter kodytek/quelle/ ab, auswahl.json nennt noch die Mac-Pfade
        quelle = self.ablage / "kodytek" / "quelle"
        for teil, n in (("train", "a"), ("val", "v")):
            (quelle / "images" / teil).mkdir(parents=True)
            (quelle / "labels" / teil).mkdir(parents=True)
            Image.new("RGB", (64, 48), (90, 70, 50)).save(quelle / "images" / teil / f"{n}.bmp")
            (quelle / "labels" / teil / f"{n}.txt").write_text("0 0.1 0.1 0.3 0.1 0.2 0.3\n")
        mac = "/Users/jan/fehlstellenscan/datensaetze/kodytek-seg-1/images"
        auswahl = [{"name": "kodytek_a", "teil": "train", "bild": f"{mac}/train/a.bmp"},
                   {"name": "kodytek_v", "teil": "val", "bild": f"{mac}/val/v.bmp"},
                   {"name": "kodytek_x", "teil": "train", "bild": f"{mac}/train/x.bmp"}]   # nicht angekommen
        (self.ablage / "kodytek" / "auswahl.json").write_text(json.dumps(auswahl))
        self.assertEqual(self.ruf("/api/saetze")[1], {"kodytek": 2})
        bilder = self.ruf("/api/bilder?satz=kodytek")[1]
        self.assertEqual([b["name"] for b in bilder], ["kodytek_a", "kodytek_v"])
        self.assertEqual(len(bilder[0]["objekte"]), 1)
        self.assertEqual(self.ruf("/zuschnitt/kodytek_a_k.jpg")[0], 200)
        umriss = {"k": 0, "ok": True, "p": [[0.1, 0.1], [0.3, 0.1], [0.2, 0.3]]}
        self.assertEqual(self.ruf("/api/label", {"name": "kodytek_a", "stand": None, "objekte": [umriss]})[0], 200)
        self.assertTrue((self.ablage / "kodytek" / "labels" / "kodytek_a.json").exists())

    def test_aufnahme_wege_wie_am_mac(self):
        kennung = self.balken()
        st, b = self.ruf(f"/api/datei?balken={kennung}&seite=1&nr=0", roh=jpeg())
        self.assertEqual(st, 200, b)
        self.assertEqual(list(b["balken"]["seiten"]["1"]["fotos"]), ["0"])
        self.assertEqual(self.ruf("/api/ausloesen", {"balken": kennung, "seite": "1", "nr": 1})[0], 409)
        self.assertEqual(self.ruf("/api/loeschen", {"balken": kennung, "seite": "1", "nr": 0})[0], 200)
        self.assertEqual(self.ruf("/api/zurueck", {"balken": kennung, "seite": "1", "nr": 0})[0], 200)
        self.assertEqual([x["id"] for x in self.ruf("/api/galerie")[1]], [kennung])
        self.assertEqual(self.ruf("/api/balken-weg", {"balken": kennung})[0], 200)
        self.assertEqual(self.ruf("/api/galerie")[1], [])
        self.assertEqual(self.ruf("/api/balken-zurueck", {"balken": kennung})[0], 200)

    def test_fremde_herkunft_abgelehnt(self):
        self.assertEqual(self.ruf("/api/balken", {"laenge_mm": 1200}, herkunft="https://boese.example")[0], 403)
        self.assertEqual(self.ruf("/api/balken", {"laenge_mm": 1200}, herkunft=None)[0], 403)

    def test_hochladen_labeln_mit_namen(self):
        kennung = self.balken("felix")
        st, stand = self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg(), wer="felix")
        self.assertEqual(st, 200, stand)
        self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg((10, 10, 10)), wer="henri")
        self.assertEqual(kennung, "B501")
        b = next(x for x in self.ruf("/api/stand")[1]["balken"] if x["id"] == kennung)
        self.assertEqual(b["von"], "felix")
        self.assertEqual([f["von"] for f in b["seiten"]["1"]["fotos"].values()], ["felix", "henri"])
        self.assertTrue((self.ablage / kennung / b["seiten"]["1"]["fotos"]["0"]["datei"]).exists())

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

    def test_labels_zeigen_wer_angelegt_und_geaendert_hat(self):
        kennung = self.balken()
        self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg(), wer="henri")
        name = self.ruf("/api/bilder")[1][0]["name"]
        ast = {"k": 0, "ok": False, "p": [[0.1, 0.1], [0.3, 0.1], [0.2, 0.3]]}
        riss = {"k": 0, "ok": True, "p": [[0.5, 0.5], [0.7, 0.5], [0.6, 0.7]]}
        st, a = self.ruf("/api/label", {"name": name, "stand": None, "objekte": [ast, riss]}, wer="henri")
        self.assertEqual(st, 200, a)
        geladen = self.ruf("/api/bilder")[1][0]["objekte"]
        self.assertEqual([(o["a"], o.get("g")) for o in geladen], [("henri", None), ("henri", None)])
        # Felix bestätigt den Ast (wie der Browser: Objekt mit a zurück), lässt den Riss, legt einen neuen an
        neu = {"k": 0, "ok": True, "p": [[0.8, 0.1], [0.9, 0.1], [0.85, 0.2]]}
        st, b = self.ruf("/api/label", {"name": name, "stand": a["zeit"],
                                        "objekte": [{**geladen[0], "ok": True}, geladen[1], neu]}, wer="felix")
        self.assertEqual(st, 200, b)
        objekte = json.loads((self.ablage / kennung / "labels" / f"{name}.json").read_text())["objekte"]
        self.assertEqual([(o["a"], o.get("g")) for o in objekte],
                         [("henri", "felix"), ("henri", None), ("felix", None)])
        verlauf = (self.ablage / kennung / "labels" / f"{name}.verlauf.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(z)["von"] for z in verlauf], ["henri", "felix"])
        self.assertEqual(len(json.loads(verlauf[0])["objekte"]), 2)

    def test_foto_massstab_einmessen(self):
        kennung = self.balken()
        self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg(), wer="henri")
        name = self.ruf("/api/bilder")[1][0]["name"]
        self.assertIsNone(self.ruf("/api/bilder")[1][0]["mm_je_px"])
        st, a = self.ruf("/api/foto-massstab", {"name": name, "mm_je_px": 0.25}, wer="felix")
        self.assertEqual(st, 200, a)
        self.assertEqual(a, {"mm_je_px": 0.25, "vorher": None})
        self.assertEqual(self.ruf("/api/bilder")[1][0]["mm_je_px"], 0.25)
        e = json.loads((self.ablage / kennung / "einmessung.json").read_text())
        self.assertEqual(e[name]["von"], "felix")
        # Rückgängig: vorigen Wert (hier keinen) zurückschreiben
        st, a = self.ruf("/api/foto-massstab", {"name": name, "mm_je_px": None})
        self.assertEqual(a["vorher"], 0.25)
        self.assertIsNone(self.ruf("/api/bilder")[1][0]["mm_je_px"])
        for falsch in (0, -1, "0.3", True, 1000):
            self.assertEqual(self.ruf("/api/foto-massstab", {"name": name, "mm_je_px": falsch})[0], 400, falsch)
        self.assertEqual(self.ruf("/api/foto-massstab", {"name": "gibtsnicht", "mm_je_px": 0.2})[0], 400)
        self.assertEqual(self.ruf("/api/foto-massstab", {"name": name, "mm_je_px": 0.2}, herkunft=None)[0], 403)
        self.assertEqual(self.ruf("/api/foto-massstab", {"name": name, "mm_je_px": 0.2}, wer=None)[0], 403)

    def test_henri_verwaltet_wie_jan(self):
        kennung = self.balken("jan")
        st, b = self.ruf("/api/balken", {"id": kennung, "laenge_mm": 900, "breite_mm": 100, "hoehe_mm": 100})
        self.assertEqual(st, 200, b)
        self.ruf(f"/api/hochladen?balken={kennung}&seite=2", roh=jpeg())
        st, stand = self.ruf("/api/foto-weg", {"balken": kennung, "seite": "2", "nr": 0}, wer="felix")
        self.assertEqual(st, 200, stand)
        self.assertEqual(stand["balken"][0]["seiten"]["2"]["fotos"], [])
        self.assertTrue(stand["verwalten"])

    def test_foto_weg_und_zurueck_mit_labels(self):
        kennung = self.balken()
        for farbe in ((10, 10, 10), (20, 20, 20), (30, 30, 30)):
            self.ruf(f"/api/hochladen?balken={kennung}&seite=1", roh=jpeg(farbe))
        bilder = self.ruf("/api/bilder")[1]
        self.assertTrue(all(b["frei"] for b in bilder))
        name = bilder[1]["name"]
        umriss = {"k": 0, "ok": True, "p": [[0.1, 0.1], [0.3, 0.1], [0.2, 0.3]]}
        self.assertEqual(self.ruf("/api/label", {"name": name, "stand": None, "objekte": [umriss]})[0], 200)
        st, stand = self.ruf("/api/foto-weg", {"balken": kennung, "seite": "1", "nr": 1}, wer="felix")
        self.assertEqual(st, 200, stand)
        self.assertEqual([f["nr"] for f in stand["balken"][0]["seiten"]["1"]["fotos"]], [0, 2])
        self.assertNotIn(name, [b["name"] for b in self.ruf("/api/bilder")[1]])
        self.assertTrue(any((self.ablage / kennung / "verworfen").iterdir()))
        st, stand = self.ruf("/api/foto-zurueck", {"balken": kennung, "seite": "1", "nr": 1}, wer="jan")
        self.assertEqual(st, 200, stand)
        self.assertEqual([f["nr"] for f in stand["balken"][0]["seiten"]["1"]["fotos"]], [0, 1, 2])
        bild = next(b for b in self.ruf("/api/bilder")[1] if b["name"] == name)
        self.assertEqual(len(bild["objekte"]), 1)
        self.assertFalse(any((self.ablage / kennung / "verworfen").iterdir()))
        # zweimal zurück geht nicht, auch nicht über den Mac-Weg /api/zurueck
        self.assertEqual(self.ruf("/api/foto-zurueck", {"balken": kennung, "seite": "1", "nr": 1})[0], 400)
        self.assertEqual(self.ruf("/api/zurueck", {"balken": kennung, "seite": "1", "nr": 1})[0], 400)
        self.assertEqual(self.ruf("/api/foto-zurueck", {"balken": kennung, "seite": "1", "nr": 1}, wer=None)[0], 403)

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


SCHLUESSEL = "k" * 32


class Tunnel(unittest.TestCase):
    """Training über neurolign.meldro.de, gerechnet auf dem Mac: Server reicht durch, Mac-Eingang prüft den Schlüssel."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        d = Path(self.ordner.name)
        self.mac = s.server_bauen(d / "mac", "127.0.0.1", 0)
        self.eingang = s.tunnel_eingang_bauen(self.mac.werk, 0, SCHLUESSEL)
        self.server = s.server_bauen(d / "server", "127.0.0.1", 0, True, Path(sys.executable), schluessel=SCHLUESSEL,
                                     mac_port=self.eingang.server_address[1])
        for x in (self.mac, self.eingang, self.server):
            threading.Thread(target=x.serve_forever, daemon=True).start()

    def tearDown(self):
        for x in (self.mac, self.eingang, self.server):
            x.shutdown()
            x.server_close()
        self.ordner.cleanup()

    def ruf(self, port, methode, weg, daten=None, kopf=None):
        v = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        v.request(methode, weg, body=None if daten is None else json.dumps(daten), headers=kopf or {})
        a = v.getresponse()
        inhalt = json.loads(a.read())
        v.close()
        return a.status, inhalt

    def vom_server(self, methode, weg, daten=None, wer="felix"):
        kopf = {"Host": HOST, "X-Nutzer": wer}
        if methode == "POST":
            kopf |= {"X-Aufnahme": "1", "Origin": f"https://{HOST}"}
        return self.ruf(self.server.server_address[1], methode, weg, daten, kopf)

    def test_stand_kommt_vom_mac(self):
        b = self.mac.werk.balken_speichern({"laenge_mm": 1200, "breite_mm": 120, "hoehe_mm": 100})
        st, stand = self.vom_server("GET", "/api/training")
        self.assertEqual(st, 200, stand)
        self.assertEqual([x["id"] for x in stand["balken"]], [b["id"]])
        st, f = self.vom_server("POST", "/api/training", {"saetze": ["altholz"]})
        self.assertEqual(st, 400)
        self.assertIn("gelabelt", f["fehler"])         # Fehler des Macs kommt durch

    def test_ohne_anmeldung_kein_weiterreichen(self):
        self.assertEqual(self.ruf(self.server.server_address[1], "GET", "/api/training", None, {"Host": HOST})[0], 403)

    def test_eingang_nur_mit_schluessel_und_nur_training(self):
        port = self.eingang.server_address[1]
        self.assertEqual(self.ruf(port, "GET", "/api/training")[0], 403)
        self.assertEqual(self.ruf(port, "GET", "/api/training", kopf={t.KOPF: "falsch" * 8})[0], 403)
        self.assertEqual(self.ruf(port, "GET", "/api/training", kopf={t.KOPF: SCHLUESSEL})[0], 200)
        for methode, weg in (("GET", "/api/stand"), ("POST", "/api/loeschen"), ("POST", "/api/ausloesen")):
            self.assertEqual(self.ruf(port, methode, weg, {}, {t.KOPF: SCHLUESSEL})[0], 403, weg)

    def test_mac_aus(self):
        self.eingang.shutdown()
        self.eingang.server_close()
        st, f = self.vom_server("GET", "/api/training")
        self.assertEqual(st, 503)
        self.assertIs(f["mac"], False)
        self.eingang = s.tunnel_eingang_bauen(self.mac.werk, 0, SCHLUESSEL)   # für tearDown
        threading.Thread(target=self.eingang.serve_forever, daemon=True).start()

    def test_abgleich_scheitert_dann_kein_start(self):
        skript = Path(self.ordner.name) / "abgleich.sh"
        skript.write_text("echo 'ssh: keine Verbindung' >&2; exit 255\n")
        self.mac.werk.abgleich = skript
        st, f = self.vom_server("POST", "/api/training", {"saetze": ["altholz"]})
        self.assertEqual(st, 400)
        self.assertIn("keine Verbindung", f["fehler"])
        self.assertIsNone(self.mac.werk.kette.lauf)

    def test_schluessel_aus_env(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            self.assertIsNone(t.schluessel_aus(env))
            env.write_text(f"ANDERES=1\n{t.SCHLUESSEL_NAME}={SCHLUESSEL}\n")
            self.assertEqual(t.schluessel_aus(env), SCHLUESSEL)
            env.write_text(f"{t.SCHLUESSEL_NAME}=kurz\n")
            self.assertIsNone(t.schluessel_aus(env))
        self.assertEqual(t.weiterreichen("GET", "/api/training", None, None, "jan")[0], 503)


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

    def test_mac_misst_foto_ein(self):
        with tempfile.TemporaryDirectory() as d:
            w = s.Werk(Path(d))
            b = w.balken_speichern({"laenge_mm": 1200, "breite_mm": 120, "hoehe_mm": 100})
            w.hochladen(b["id"], "1", jpeg(), "felix")
            name = w.kette.bilder()[0]["name"]
            self.assertEqual(w.kette.foto_massstab({"name": name, "mm_je_px": 0.5})["vorher"], None)
            self.assertEqual(w.kette.foto_massstab({"name": name, "mm_je_px": 0.4})["vorher"], 0.5)
            self.assertEqual(w.kette.bilder()[0]["mm_je_px"], 0.4)
            self.assertEqual(w.kette.einmessungen(b["id"])[name]["von"], "mac")

    def test_mac_loescht_hochgeladene_fotos_und_holt_sie_zurueck(self):
        with tempfile.TemporaryDirectory() as d:
            w = s.Werk(Path(d))
            b = w.balken_speichern({"laenge_mm": 1200, "breite_mm": 120, "hoehe_mm": 100})
            w.hochladen(b["id"], "1", jpeg(), "felix")
            w.hochladen(b["id"], "1", jpeg((5, 5, 5)), "felix")
            w.loeschen({"balken": b["id"], "seite": "1", "nr": 0})
            self.assertEqual(list(w.lesen(b["id"])["seiten"]["1"]["fotos"]), ["1"])
            self.assertEqual(w.lesen(b["id"])["seiten"]["1"]["geloescht"]["0"]["von"], "mac")
            w.zurueckholen({"balken": b["id"], "seite": "1", "nr": 0})
            self.assertEqual(sorted(w.lesen(b["id"])["seiten"]["1"]["fotos"]), ["0", "1"])
            with self.assertRaises(ValueError):
                w.zurueckholen({"balken": b["id"], "seite": "1", "nr": 0})


if __name__ == "__main__":
    unittest.main()
