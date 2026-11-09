"""Echter Uvicorn auf einem Unix-Socket im Temp-Ordner, Anfragen mit http.client (kein httpx)."""

import hashlib
import http.client
import re
import shutil
import socket
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock
from urllib.parse import urlencode

import uvicorn

from agentkit import auftraege, orte

import app

ARTEN = """
[[art]]
kennung = "expose"
name = "Exposé"
beschreibung = "Exposé für eine Arbeit"
agent = "uni"
aktiv = true
ausgabe = ["pdf", "docx"]
[[art.feld]]
name = "Thema"
art = "zeile"
pflicht = true
[[art.feld]]
name = "Umfang"
art = "auswahl"
werte = ["kurz", "lang"]

[[art]]
kennung = "zusammenfassung"
name = "Zusammenfassung"
beschreibung = "Aus Folien"
agent = "uni"
aktiv = true
material = "pflicht"

[[art]]
kennung = "bericht"
name = "Bericht"
beschreibung = "Noch nicht fertig"
agent = "uni"
aktiv = false
"""


class UnixVerbindung(http.client.HTTPConnection):
    def __init__(self, pfad):
        super().__init__("localhost")
        self.pfad = pfad

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.pfad)


class Aufbau(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.instanz = self.tmp / "shared"
        self.instanz.mkdir()
        (self.tmp / "uni").mkdir()
        (self.tmp / "uni" / "agent.py").write_text("")
        (self.tmp / "arten.toml").write_text(ARTEN, encoding="utf-8")
        self.units = self.tmp / "units"
        self.units.mkdir()
        self.gestartet = []
        for name, wert in (("INSTANZ", self.instanz), ("ARTEN_DATEI", self.tmp / "arten.toml"),
                           ("DATEN", self.tmp / "webdaten"), ("UNIT_DIR", self.units), ("AUFTRAEGE", "echt")):
            p = mock.patch.object(app, name, wert)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(app.subprocess, "run", lambda befehl, **k: self.gestartet.append(befehl))
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.dict(app._EINMAL, clear=True)
        p.start()
        self.addCleanup(p.stop)
        self.sock = self.tmp / "data" / "arbeitsplatz.sock"
        app.socket_vorbereiten(self.sock)
        self.server = uvicorn.Server(uvicorn.Config(app.app, uds=str(self.sock), log_level="warning"))
        faden = threading.Thread(target=self.server.run, daemon=True)
        faden.start()
        for _ in range(100):
            if self.server.started:
                break
            time.sleep(0.05)
        self.assertTrue(self.server.started)

        def stoppen():
            self.server.should_exit = True
            faden.join(5)
        self.addCleanup(stoppen)

    def get(self, pfad):
        v = UnixVerbindung(str(self.sock))
        v.request("GET", pfad)
        r = v.getresponse()
        try:
            return r.status, r.read().decode("utf-8"), dict(r.getheaders())
        finally:
            v.close()

    def post(self, pfad, felder, origin="http://localhost", token=True, dateien=None):
        felder = dict(felder)
        if token:
            felder.setdefault("token", app.logik.formular_token(app.GEHEIM))
        kopf = {"Host": "localhost"}
        if origin:
            kopf["Origin"] = origin
        if dateien is None:
            body = urlencode(felder).encode()
            kopf["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            grenze = uuid.uuid4().hex
            teile = []
            for k, w in felder.items():
                teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{w}\r\n'.encode())
            for name, inhalt in dateien:
                teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="dateien"; filename="{name}"\r\n'
                             f'Content-Type: application/octet-stream\r\n\r\n'.encode() + inhalt + b"\r\n")
            body = b"".join(teile) + f"--{grenze}--\r\n".encode()
            kopf["Content-Type"] = f"multipart/form-data; boundary={grenze}"
        v = UnixVerbindung(str(self.sock))
        v.request("POST", pfad, body=body, headers=kopf)
        r = v.getresponse()
        try:
            return r.status, r.read().decode("utf-8"), dict(r.getheaders())
        finally:
            v.close()

    def ort(self, titel, eltern=None):
        return orte.anlegen(titel, eltern, instanz=self.instanz).id


class TestSeiten(Aufbau):
    def test_heute_leer_und_kopfzeilen(self):
        status, html, kopf = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("Noch keine Orte", html)
        self.assertIn("default-src 'self'", kopf["content-security-policy"])
        self.assertEqual(kopf["cache-control"], "no-store")
        self.assertEqual(self.get("/ort/gibt-es-nicht")[0], 404)
        self.assertEqual(self.get("/dokument/../../etc")[0], 404)

    def test_statisch_htmx_summe(self):
        js = (app.HIER / "statisch" / "htmx-2.0.4.min.js").read_bytes()
        summe = (app.HIER / "statisch" / "htmx-2.0.4.min.js.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256(js).hexdigest(), summe)
        self.assertEqual(self.get("/statisch/arbeitsplatz.css")[0], 200)

    def test_baum_und_ort_seite(self):
        p = self.ort("Projekt <Fehlstellen>")
        k = self.ort("Kapitel 3", p)
        status, html, _ = self.get(f"/ort/{p}")
        self.assertEqual(status, 200)
        self.assertIn("Projekt &lt;Fehlstellen&gt;", html)  # escaped
        self.assertIn(f'href="/ort/{k}"', html)
        self.assertIn(f'href="/seite/neu?eltern={p}"', html)
        self.assertIn(f'href="/neu?ort={p}"', html)
        self.assertIn('aria-current="page"', html)


class TestPflege(Aufbau):
    def test_seite_anlegen_umbenennen_rueckgaengig(self):
        status, _, kopf = self.post("/seite/neu", {"titel": "Modul Holzschutz", "einmal": "a1"})
        self.assertEqual(status, 303)
        self.assertTrue(kopf["location"].startswith("/ort/modul-holzschutz?aktion="))
        # Doppelklick: dieselbe Kennung legt nichts zweites an
        self.assertEqual(self.post("/seite/neu", {"titel": "Modul Holzschutz", "einmal": "a1"})[2]["location"],
                         kopf["location"])
        self.assertEqual(len(orte.laden(self.instanz)), 1)
        html = self.get(kopf["location"])[1]
        self.assertIn("Seite „Modul Holzschutz“ angelegt", html)
        self.assertIn('action="/rueckgaengig"', html)
        status, _, kopf = self.post("/ort/modul-holzschutz/umbenennen", {"titel": "Holzschutz"})
        self.assertEqual(status, 303)
        self.assertEqual(orte.laden(self.instanz)[0]["titel"], "Holzschutz")
        aktion = kopf["location"].split("aktion=")[1]
        self.assertEqual(self.post("/rueckgaengig", {"aktion": aktion, "zurueck": "/ort/modul-holzschutz"})[0], 303)
        self.assertEqual(orte.laden(self.instanz)[0]["titel"], "Modul Holzschutz")

    def test_rueckgaengig_von_anlegen_fuehrt_nach_heute(self):
        kopf = self.post("/seite/neu", {"titel": "Weg"})[2]
        aktion = kopf["location"].split("aktion=")[1]
        status, _, kopf = self.post("/rueckgaengig", {"aktion": aktion, "zurueck": "/ort/weg"})
        self.assertEqual((status, kopf["location"].split("?")[0]), (303, "/"))
        self.assertEqual(orte.laden(self.instanz), [])

    def test_verschieben_archivieren_wiederherstellen(self):
        a, b = self.ort("A"), self.ort("B")
        a1 = self.ort("A1", a)
        status, html, _ = self.post(f"/ort/{a}/verschieben", {"eltern": a1})
        self.assertEqual(status, 400)
        self.assertIn("kann nicht in sich selbst liegen", html)
        self.assertEqual(self.post(f"/ort/{a1}/verschieben", {"eltern": b})[0], 303)
        self.assertEqual(orte.pfad(orte.laden(self.instanz), a1)[0]["id"], b)
        self.assertEqual(self.post(f"/ort/{b}/archivieren", {})[0], 303)
        self.assertIn(">B<", self.get("/archiv")[1])
        self.assertNotIn(f'href="/ort/{b}"', self.get("/")[1].split('aria-label="Orte"')[1])
        self.assertEqual(self.post(f"/ort/{b}/wiederherstellen", {"zurueck": "/archiv"})[0], 303)
        self.assertIn("Das Archiv ist leer", self.get("/archiv")[1])

    def test_schutz(self):
        self.assertEqual(self.post("/seite/neu", {"titel": "X"}, origin="https://boese.de")[0], 403)
        self.assertEqual(self.post("/seite/neu", {"titel": "X"}, origin=None)[0], 403)
        status, html, _ = self.post("/seite/neu", {"titel": "X"}, token=False)
        self.assertEqual(status, 400)
        self.assertIn("zu alt", html)
        self.assertEqual(orte.laden(self.instanz), [])
        self.assertEqual(self.post("/seite/neu", {"titel": "X", "eltern": "gibt-es-nicht"})[0], 404)


class TestNeu(Aufbau):
    def setUp(self):
        super().setUp()
        self.k = self.ort("Kapitel 3")
        (self.units / "uni.service").write_text("")

    def test_galerie_nur_aktive_arten(self):
        html = self.get(f"/neu?ort={self.k}")[1]
        self.assertIn(f'href="/neu/expose?ort={self.k}"', html)
        self.assertNotIn("/neu/bericht", html)
        self.assertEqual(self.get("/neu/bericht")[0], 404)
        html = self.get(f"/neu/expose?ort={self.k}")[1]
        self.assertIn('name="feld-0"', html)
        self.assertIn("<option>kurz</option>", html)
        self.assertIn("Kapitel 3", html)

    def test_auftrag_anlegen_und_dienst_starten(self):
        status, _, kopf = self.post("/neu/expose", {"ort": self.k, "feld-0": " Holz ", "feld-1": "kurz",
                                                    "einmal": "x"})
        self.assertEqual((status, kopf["location"]), (303, f"/ort/{self.k}?erledigt=auftrag"))
        self.post("/neu/expose", {"ort": self.k, "feld-0": "Holz", "feld-1": "kurz", "einmal": "x"})  # Doppelklick
        neu = auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual(len(neu), 1)
        a = neu[0]
        self.assertEqual((a["agent"], a["quelle"], a["ort"], a["art"], a["felder"]),
                         ("uni", "arbeitsplatz", self.k, "expose", {"Thema": "Holz", "Umfang": "kurz"}))
        self.assertEqual(a["text"], "Art: Exposé\nThema: Holz\nUmfang: kurz")
        self.assertEqual(self.gestartet, [["systemctl", "--user", "start", "--no-block", "uni.service"]])
        html = self.get(f"/ort/{self.k}?erledigt=auftrag")[1]
        self.assertIn("Exposé: Holz", html)
        self.assertIn("Läuft", html)
        self.assertIn("Auftrag angelegt", html)
        status, html, _ = self.get(f"/dokument/{a['id']}")
        self.assertEqual(status, 200)
        self.assertIn("Kapitel 3", html)

    def test_formularfehler_und_aus(self):
        status, html, _ = self.post("/neu/expose", {"ort": self.k, "feld-1": "riesig"})
        self.assertEqual(status, 400)
        self.assertIn("Thema: bitte ausfüllen", html)
        self.assertIn("Umfang: bitte aus der Liste wählen", html)
        status, html, _ = self.post("/neu/expose", {"feld-0": "Holz"})
        self.assertIn("Ort: bitte wählen", html)
        with mock.patch.object(app, "AUFTRAEGE", "aus"):
            status, html, _ = self.post("/neu/expose", {"ort": self.k, "feld-0": "Holz"})
        self.assertEqual(status, 400)
        self.assertIn("ausgeschaltet", html)
        self.assertEqual(auftraege.neue(basis=self.instanz / "auftraege"), [])
        self.assertEqual(self.gestartet, [])

    def test_material(self):
        status, html, _ = self.post("/neu/zusammenfassung", {"ort": self.k}, dateien=[])
        self.assertIn("mindestens eine Datei", html)
        status, html, _ = self.post("/neu/zusammenfassung", {"ort": self.k}, dateien=[("x.exe", b"MZ")])
        self.assertEqual(status, 400)
        status, _, _ = self.post("/neu/zusammenfassung", {"ort": self.k},
                                 dateien=[("../Folien.pdf", b"%PDF"), ("Folien.pdf", b"%PDF2")])
        self.assertEqual(status, 303)
        a = auftraege.neue(basis=self.instanz / "auftraege")[0]
        self.assertEqual([Path(p).name for p in a["dateien"]], ["Folien.pdf", "Folien-2.pdf"])
        self.assertTrue((self.tmp / "uni" / a["dateien"][0]).exists())
        self.assertEqual(list((self.tmp / "webdaten" / "eingang").iterdir()), [])  # nichts liegen geblieben

    def test_ohne_unit_wartet(self):
        (self.units / "uni.service").unlink()
        kopf = self.post("/neu/expose", {"ort": self.k, "feld-0": "Holz"})[2]
        self.assertTrue(kopf["location"].endswith("erledigt=auftrag-wartet"))
        self.assertEqual(self.gestartet, [])

    def test_laeuft_gerade_rechts(self):
        self.post("/neu/expose", {"ort": self.k, "feld-0": "Holz"})
        rechts = self.get("/")[1].split('aria-label="Läuft gerade"')[1]
        self.assertIn("Exposé: Holz", rechts)
        self.assertTrue(re.search(r"uni · seit heute \d\d:\d\d|uni · seit \d\d\.\d\d\.", rechts))


if __name__ == "__main__":
    unittest.main()
