"""Echter Uvicorn auf einem Unix-Socket im Temp-Ordner, Anfragen mit http.client (kein httpx)."""

import hashlib
import json
import os
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
kennung = "pruefung"
name = "Prüfung"
beschreibung = "Auswertung"
agent = "uni"
aktiv = true
material_oder = "Transkript"
rueckmeldung = false
[[art.feld]]
name = "Transkript"
art = "text"

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

    def post(self, pfad, felder, origin="http://localhost", token=True, dateien=None, feld="dateien"):
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
                teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{feld}"; filename="{name}"\r\n'
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
        self.assertIn("Noch leer. Mit + fängst du an.", html)
        self.assertNotIn("Wartet auf dich", html)
        self.assertIn("default-src 'self'", kopf["content-security-policy"])
        self.assertEqual(kopf["cache-control"], "no-store")
        self.assertEqual(self.get("/ort/gibt-es-nicht")[0], 404)
        self.assertEqual(self.get("/dokument/../../etc")[0], 404)

    def test_statisch_htmx_summe(self):
        js = (app.HIER / "statisch" / "htmx-2.0.4.min.js").read_bytes()
        summe = (app.HIER / "statisch" / "htmx-2.0.4.min.js.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256(js).hexdigest(), summe)
        self.assertEqual(self.get("/statisch/arbeitsplatz.css")[0], 200)

    def test_ruhiges_aussehen(self):
        """umbauplan-ux.md Schritt 1: ruhig.css, rechte Spalte (Läuft gerade, Kosten) nur auf Heute."""
        html = self.get("/")[1]
        self.assertIn('href="/statisch/ruhig.css"', html)
        self.assertNotIn("stil.css", html)
        self.assertIn('<div class="rahmen">', html)
        self.assertIn('<aside class="rechts" aria-label="Läuft gerade">', html)
        self.assertEqual(self.get("/statisch/ruhig.css")[0], 200)
        self.assertEqual(self.get("/statisch/stil.css")[0], 404)
        p = self.ort("Projekt")
        for pfad in (f"/ort/{p}", "/neu", f"/neu/expose?ort={p}", "/archiv", "/seite/neu"):
            html = self.get(pfad)[1]
            self.assertIn('<div class="rahmen ohne-rechts">', html, pfad)
            self.assertNotIn('class="rechts"', html, pfad)

    def test_baum_und_ort_seite(self):
        p = self.ort("Projekt <Fehlstellen>")
        k = self.ort("Kapitel 3", p)
        status, html, _ = self.get(f"/ort/{p}")
        self.assertEqual(status, 200)
        self.assertIn("Projekt &lt;Fehlstellen&gt;", html)  # escaped
        self.assertIn(f'href="/ort/{k}"', html)
        self.assertIn(f'<input type="hidden" name="eltern" value="{p}">', html.split('class="menue-halter plus"')[1])
        self.assertIn(f'href="/neu?ort={p}"', html)
        self.assertIn('aria-current="page"', html)

    def test_plus_je_seite(self):
        """umbauplan-ux.md Schritt 2: je Seite höchstens ein „+“ mit den Einträgen aus dem Plan; Archiv ohne."""
        def eintraege(html):
            if 'class="menue-halter plus"' not in html:
                return None
            menue = html.split('class="menue-halter plus"')[1].split("</details>")[0]
            return re.findall(r'(?:type="submit">|<a class="knopf knopf-leise" href="[^"]*">)([^<]+)<', menue)
        p = self.ort("Projekt")
        heute = self.get("/")[1]
        self.assertEqual(heute.count('class="menue-halter plus"'), 1)
        self.assertEqual(eintraege(heute), ["Seite", "Dokument …"])
        self.assertIn('class="knopf knopf-voll plus-knopf"', heute)
        self.assertEqual(eintraege(self.get(f"/ort/{p}")[1]), ["Seite", "Dokument …", "Datei"])
        for pfad in ("/archiv", "/neu", "/neu/expose", "/seite/neu"):
            self.assertIsNone(eintraege(self.get(pfad)[1]), pfad)
        self.assertNotIn("+ Neu<", self.get(f"/ort/{p}")[1])
        # „Seite“ im „+“ legt sofort „Neue Seite“ unter dem Ort an
        kopf = self.post("/seite/neu", {"eltern": p, "titel": "Neue Seite", "einmal": "p1"})[2]
        self.assertTrue(kopf["location"].startswith("/ort/neue-seite?aktion="))
        self.assertEqual({k["id"]: k for k in orte.laden(self.instanz)}["neue-seite"]["eltern"], p)
        # archivierter Ort: kein „+“, „Wiederherstellen“ am Hinweis, im „···“ kein Archivieren
        self.post(f"/ort/{p}/archivieren", {})
        html = self.get(f"/ort/{p}")[1]
        self.assertIsNone(eintraege(html))
        self.assertIn(f'action="/ort/{p}/wiederherstellen"', html)
        self.assertNotIn(f'action="/ort/{p}/archivieren"', html)

    def test_punkte_am_ort(self):
        """Seltenes steht im „···“: Umbenennen, Verschieben, Unterseiten ordnen (ab zwei), Archivieren."""
        p = self.ort("Projekt")
        a, b, c = self.ort("A", p), self.ort("B", p), self.ort("C", p)
        html = self.get(f"/ort/{p}")[1]
        punkte = html.split('class="menue-halter punkte"')[1].split("</details>")[0]
        for aktion in ("umbenennen", "verschieben", "archivieren"):
            self.assertIn(f'action="/ort/{p}/{aktion}"', punkte)
        self.assertIn("Unterseiten ordnen", punkte)
        self.assertNotIn('aria-label="A nach oben"', punkte)
        self.assertIn('aria-label="A nach unten"', punkte)
        self.assertIn('aria-label="C nach oben"', punkte)
        self.assertNotIn('aria-label="C nach unten"', punkte)
        # außerhalb des „···“ keine Formulare mehr (keine offenen Masken, keine ↑/↓)
        mitte = html.split("</header>")[1].split("</main>")[0]
        mitte = re.sub(r'<section id="ablage" class="ablage-zu".*?</section>', "", mitte, flags=re.S)  # versteckt
        self.assertNotIn("<form", mitte)
        # ↓ an A schiebt A hinter B
        self.post(f"/ort/{a}/verschieben", {"eltern": p, "position": "1", "zurueck": f"/ort/{p}"})
        self.assertEqual([k["id"] for k in orte.kinder(orte.laden(self.instanz), p)], [b, a, c])
        # nur eine Unterseite: nichts zu ordnen
        self.assertNotIn("Unterseiten ordnen", self.get(f"/ort/{a}")[1])

    def test_direkt_am_ding(self):
        """umbauplan-ux.md Schritt 3: Titel des Orts anklicken (Formular an die bestehende Route), Datei ins Formular
        ziehen (data-ablegen); direkt.js ist da."""
        p = self.ort("Projekt")
        html = self.get(f"/ort/{p}")[1]
        self.assertIn('<script src="/statisch/direkt.js" defer></script>', html)
        kopf = html.split('<header class="kopf">')[1].split("</header>")[0]
        self.assertIn('<h1 class="titel-gross" data-direkt-titel>Projekt</h1>', kopf)
        self.assertIn(f'action="/ort/{p}/umbenennen" hidden', kopf)
        self.assertIn('name="titel" type="text" value="Projekt"', kopf)
        self.assertIn('name="token"', kopf)
        self.assertEqual(self.get("/statisch/direkt.js")[0], 200)
        # eine eben über „+“ angelegte „Neue Seite“ steht gleich zum Umbenennen offen, später nicht mehr
        ort_url = self.post("/seite/neu", {"eltern": p, "titel": "Neue Seite", "einmal": "d1"})[2]["location"]
        self.assertIn("data-direkt-offen", self.get(ort_url)[1])
        self.assertNotIn("data-direkt-offen", self.get(ort_url.split("?")[0])[1])
        self.assertNotIn("data-direkt-offen", html)
        # Umbenennen wie aus dem Feld: nur „titel“ und Token
        kopf = self.post(f"/ort/{p}/umbenennen", {"titel": "Projekt Fehlstellen"})[2]
        self.assertTrue(kopf["location"].startswith(f"/ort/{p}?aktion="))
        self.assertIn("Projekt Fehlstellen", self.get(f"/ort/{p}")[1])
        # Formular einer Art: das Feld Material ist das Ziel zum Ziehen
        html = self.get(f"/neu/zusammenfassung?ort={p}")[1]
        self.assertIn('name="dateien" multiple data-ablegen', html)
        self.assertIn("/statisch/direkt.js", html)

    def test_nur_zeigen_was_da_ist(self):
        """Leere Abschnitte fallen weg; ganz leer: eine leise Zeile."""
        p = self.ort("Projekt")
        html = self.get(f"/ort/{p}")[1]
        self.assertNotIn("<h2>Dokumente</h2>", html)
        self.assertNotIn("<h2>Unterseiten</h2>", html)
        self.assertIn("Noch leer. Mit + fängst du an.", html)
        self.ort("Kapitel", p)
        html = self.get(f"/ort/{p}")[1]
        self.assertIn("<h2>Unterseiten</h2>", html)
        self.assertNotIn("Noch leer", html)
        heute = self.get("/")[1]
        self.assertIn("<h2>Orte</h2>", heute)
        self.assertNotIn("<h2>Zuletzt</h2>", heute)
        self.assertNotIn("Noch leer", heute)
        # im Baum kein „+ Seite“ unter dem aktiven Ort mehr, unten bleibt es
        self.assertNotIn(f'/seite/neu?eltern={p}', html)
        self.assertIn('href="/seite/neu"', html)


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

    def test_datei_am_ort(self):
        """umbauplan-ux.md Schritt 4: Datei am Ort ablegen, Galerie „Was soll daraus werden?“ (nur Arten mit
        Material), Formular mit der Datei, Auftrag übernimmt sie, der abgelegte Ordner ist danach weg."""
        html = self.get(f"/ort/{self.k}")[1]
        self.assertIn('href="#ablage">Datei</a>', html)
        self.assertIn('<form class="ablage-form" method="post" action="/neu/datei"', html)
        self.assertIn("data-ablegen", html.split('id="ablage"')[1])
        status, _, kopf = self.post("/neu/datei", {"ort": self.k, "einmal": "g1"},
                                    dateien=[("Folien.pdf", b"%PDF"), ("Notizen.md", b"# N")])
        self.assertEqual(status, 303)
        ziel = kopf["location"]
        m = re.fullmatch(rf"/neu\?ort={self.k}&datei=([a-z0-9_]+)", ziel)
        self.assertTrue(m, ziel)
        kennung = m.group(1)
        gelegt = self.tmp / "webdaten" / "eingang" / f"gelegt-{kennung}"
        self.assertEqual(sorted(p.name for p in gelegt.iterdir()), ["Folien.pdf", "Notizen.md"])
        # Doppelklick legt nichts zweites ab
        self.assertEqual(self.post("/neu/datei", {"ort": self.k, "einmal": "g1"},
                                   dateien=[("Folien.pdf", b"%PDF")])[2]["location"], ziel)
        self.assertEqual(len(list((self.tmp / "webdaten" / "eingang").iterdir())), 1)
        html = self.get(ziel)[1]
        self.assertIn("Was soll daraus werden?", html)
        self.assertIn("Dabei: Folien.pdf, Notizen.md", html)
        self.assertIn(f'href="/neu/zusammenfassung?ort={self.k}&amp;datei={kennung}"', html)
        html = self.get(f"/neu/zusammenfassung?ort={self.k}&datei={kennung}")[1]
        self.assertIn("Schon dabei: Folien.pdf, Notizen.md", html)
        self.assertIn(f'name="datei" value="{kennung}"', html)
        self.assertNotIn("data-ablegen required", html)  # Material ist schon da
        # Auftrag: die abgelegten Dateien plus eine weitere aus dem Formular
        status, _, _ = self.post("/neu/zusammenfassung", {"ort": self.k, "datei": kennung},
                                 dateien=[("Folien.pdf", b"%PDF2")])
        self.assertEqual(status, 303)
        a = auftraege.neue(basis=self.instanz / "auftraege")[0]
        self.assertEqual(sorted(Path(p).name for p in a["dateien"]), ["Folien-2.pdf", "Folien.pdf", "Notizen.md"])
        self.assertFalse(gelegt.exists())
        # danach ist die Kennung verbraucht: Galerie mit Hinweis, Formular mit Fehler
        self.assertIn("nicht mehr da", self.get(f"/neu?ort={self.k}&datei={kennung}")[1])
        status, html, _ = self.post("/neu/zusammenfassung", {"ort": self.k, "datei": kennung})
        self.assertEqual(status, 400)
        self.assertIn("nicht mehr da", html)

    def test_datei_am_ort_grenzen(self):
        self.assertEqual(self.post("/neu/datei", {"ort": self.k}, dateien=[("x.exe", b"MZ")])[0], 400)
        self.assertEqual(self.post("/neu/datei", {"ort": self.k}, dateien=[])[0], 400)
        self.assertEqual(self.post("/neu/datei", {"ort": "gibt-es-nicht"}, dateien=[("a.pdf", b"%PDF")])[0], 404)
        self.assertEqual(self.post("/neu/datei", {"ort": self.k}, dateien=[("a.pdf", b"%PDF")], token=False)[0], 400)
        self.assertEqual(self.post("/neu/datei", {"ort": self.k}, dateien=[("a.pdf", b"%PDF")],
                                   origin="https://b.de")[0], 403)
        zuviel = [(f"{i}.pdf", b"%PDF") for i in range(app.MAX_DATEIEN + 1)]
        self.assertEqual(self.post("/neu/datei", {"ort": self.k}, dateien=zuviel)[0], 400)
        eingang = self.tmp / "webdaten" / "eingang"
        self.assertEqual(list(eingang.iterdir()) if eingang.exists() else [], [])
        # fremde oder böse Kennung: nichts gelegt, Galerie normal
        for k in ("../../etc", "GELEGT", "abc"):
            html = self.get(f"/neu?ort={self.k}&datei={k}")[1]
            self.assertNotIn("Was soll daraus werden?", html)
        # finance-artige Arten ohne Material erscheinen nicht in der Galerie mit Datei
        art = {"kennung": "nur_text", "material": "nein"}
        with mock.patch.object(app.arten, "aktive", lambda _: [art | {"name": "Nur Text", "beschreibung": "",
                                                                     "ausgabe": []}]):
            kennung = re.search(r"datei=([a-z0-9_]+)", self.post("/neu/datei", {"ort": self.k},
                                dateien=[("a.pdf", b"%PDF")])[2]["location"]).group(1)
            self.assertNotIn("/neu/nur_text", self.get(f"/neu?ort={self.k}&datei={kennung}")[1])
            self.assertIn("/neu/nur_text", self.get(f"/neu?ort={self.k}")[1])

    def test_gelegt_aufraeumen(self):
        eingang = self.tmp / "webdaten" / "eingang"
        alt, neu, anders = eingang / "gelegt-alt12345", eingang / "gelegt-neu12345", eingang / "tmpabc"
        for o in (alt, neu, anders):
            o.mkdir(parents=True)
        jetzt = time.time()
        os.utime(alt, (jetzt - app.GELEGT_ALTER - 10,) * 2)
        os.utime(anders, (jetzt - app.GELEGT_ALTER - 10,) * 2)
        app.gelegt_aufraeumen(jetzt)
        self.assertEqual(sorted(p.name for p in eingang.iterdir()), ["gelegt-neu12345", "tmpabc"])

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

    def test_transkript_oder_datei(self):
        status, html, _ = self.post("/neu/pruefung", {"ort": self.k}, dateien=[])
        self.assertIn("Transkript: bitte ausfüllen oder eine Datei anhängen", html)
        self.assertEqual(self.post("/neu/pruefung", {"ort": self.k, "feld-0": "Frage: ..."})[0], 303)
        self.assertEqual(self.post("/neu/pruefung", {"ort": self.k}, dateien=[("pruefung.json", b"{}")])[0], 303)
        self.assertIn("(statt Transkript)", self.get(f"/neu/pruefung?ort={self.k}")[1])

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


class TestDokument(Aufbau):
    U = "20261109-100000-uni-aaaaaa"
    NB = "20261109-110000-uni-bbbbbb"

    def setUp(self):
        super().setUp()
        self.k = self.ort("Kapitel 3")
        (self.units / "feedback.service").write_text("")
        arbeit = self.tmp / "uni" / "data" / "arbeit"
        (arbeit / "Expose-vorschau").mkdir(parents=True)
        (arbeit / "Expose.docx").write_bytes(b"DOCX")
        (arbeit / "Expose-vorschau" / "Expose.pdf").write_bytes(b"%PDF-1.7")
        for n in (1, 2):
            (arbeit / "Expose-vorschau" / f"Expose-seite-0{n}.png").write_bytes(b"PNG" + bytes([n]))
        (self.tmp / "geheim.pdf").write_bytes(b"%PDF geheim")
        (self.tmp / "uni" / ".env").write_text("X=1")
        erledigt = self.instanz / "auftraege" / "erledigt"
        erledigt.mkdir(parents=True)
        for a in ({"id": self.U, "agent": "uni", "quelle": "arbeitsplatz", "ort": self.k, "art": "expose",
                   "felder": {"Thema": "Holz"}, "text": "Art: Exposé\nThema: Holz", "status": "erledigt",
                   "erstellt": "2026-11-09T10:00:00+01:00", "abgeschlossen": "2026-11-09T10:30:00+01:00",
                   "ergebnis": "fertig", "bezug": None,
                   "ergebnis_dateien": ["data/arbeit/Expose.docx", "../geheim.pdf", ".env"],
                   "daten": {"titel": "Exposé Holzschutz", "kern": "Ein Exposé.", "pruefen": "Quellen ansehen"}},
                  {"id": self.NB, "agent": "uni", "quelle": "telegram", "ort": self.k, "art": "pruefung",
                   "text": "Prüfung", "status": "erledigt", "erstellt": "2026-11-09T11:00:00+01:00",
                   "abgeschlossen": "2026-11-09T11:10:00+01:00", "ergebnis": "ok", "ergebnis_dateien": []}):
            (erledigt / f"{a['id']}.json").write_text(json.dumps(a), encoding="utf-8")

    def test_ansicht_mit_seiten_und_dateien(self):
        status, html, _ = self.get(f"/dokument/{self.U}")
        self.assertEqual(status, 200)
        self.assertIn("Exposé Holzschutz", html)
        self.assertIn("Quellen ansehen", html)
        self.assertIn(f"/dokument/{self.U}/datei/{self.U}/0/seite/2", html)
        self.assertIn('id="rueckmeldung"', html)
        self.assertIn("Kapitel 3", html)  # Brotkrume zum Ort
        self.assertEqual(self.get(f"/dokument/{self.U}/datei/{self.U}/0")[1], "DOCX")
        self.assertEqual(self.get(f"/dokument/{self.U}/datei/{self.U}/0/pdf")[1], "%PDF-1.7")
        status, inhalt, kopf = self.get(f"/dokument/{self.U}/datei/{self.U}/0/seite/1")
        self.assertEqual((status, inhalt), (200, "PNG\x01"))
        for pfad in (f"/datei/{self.U}/1", f"/datei/{self.U}/2", f"/datei/{self.U}/3", f"/datei/{self.U}/0/seite/3",
                     f"/datei/{self.NB}/0", "/eigene/1"):
            with self.subTest(pfad=pfad):
                self.assertEqual(self.get(f"/dokument/{self.U}{pfad}")[0], 404)
        self.assertEqual(self.get(f"/dokument/{self.NB}")[0], 200)
        self.assertNotIn('id="rueckmeldung"', self.get(f"/dokument/{self.NB}")[1])  # pruefung: keine Rückmeldung
        self.assertIn("Exposé Holzschutz", self.get("/")[1])  # Heute: wartet auf dich

    def test_dokument_ruhig(self):
        """umbauplan-ux.md Schritt 5: genau ein blauer Knopf („Senden“), Feld nur bei Arten mit rueckmeldung, Final
        und eigene Fassung im „···“, Download-Symbol je Datei, Verlauf als geschlossene Klappe erst ab zwei."""
        html = self.get(f"/dokument/{self.U}")[1]
        self.assertEqual(html.count("knopf-voll"), 1)
        self.assertIn('<button class="knopf knopf-voll" type="submit">Senden</button>', html)
        self.assertIn('placeholder="Was soll anders werden?"', html)
        self.assertIn('id="anhang" name="datei" type="file"', html)
        self.assertIn("data-ablegen", html.split('id="rueckmeldung"')[1])
        punkte = html.split('class="menue-halter punkte"')[1].split("</details>")[0]
        self.assertIn("Als final markieren", punkte)
        self.assertIn(f'action="/dokument/{self.U}/eigene"', punkte)
        self.assertIn("Eigene Fassung hochladen …", punkte)
        self.assertNotIn("Verlauf", html)  # eine Fassung allein steht oben
        self.assertIn('class="menue-halter laden"', html)
        self.assertIn(f'href="/dokument/{self.U}/datei/{self.U}/0" download>Word-Datei</a>', html)
        self.assertIn(f'href="/dokument/{self.U}/datei/{self.U}/0/pdf" target="_blank"', html)
        self.assertIn('class="menue-halter plus"', html)
        self.assertNotIn("knopf-voll plus-knopf", html)
        # ?offen=eigene öffnet das „···“
        self.assertIn('class="menue-halter punkte" open', self.get(f"/dokument/{self.U}?offen=eigene")[1])
        # zweite Station (Rückmeldung): Klappe „Verlauf“, geschlossen, mit Zahlen; final: kein blauer Knopf mehr
        self.post(f"/dokument/{self.U}/rueckmeldung", {"text": "Bitte kürzer", "einmal": "v1"})
        self.post(f"/dokument/{self.U}/final", {"ref": self.U, "an": "1"})
        html = self.get(f"/dokument/{self.U}")[1]
        self.assertIn('<details class="mehr verlauf-klappe">', html)
        self.assertIn("<summary>Verlauf: 1 Fassung, 1 Rückmeldung</summary>", html)
        self.assertNotIn("knopf-voll", html)
        self.assertIn("Nicht mehr final", html.split('class="menue-halter punkte"')[1].split("</details>")[0])
        # Art ohne Rückmeldung: kein Feld, kein Satz dazu
        html = self.get(f"/dokument/{self.NB}")[1]
        self.assertNotIn("Was soll anders werden", html)
        self.assertNotIn("nimmt der Agent keine Rückmeldung", html)

    def test_final_an_und_aus(self):
        status, _, kopf = self.post(f"/dokument/{self.U}/final", {"ref": self.U, "an": "1"})
        self.assertEqual((status, kopf["location"]), (303, f"/dokument/{self.U}?erledigt=final"))
        stand = json.loads((self.instanz / "fassungen" / f"{self.U}.json").read_text())
        self.assertEqual(stand["final"]["fassung"], self.U)
        self.assertIn("Nicht mehr final", self.get(f"/dokument/{self.U}")[1])
        self.post(f"/dokument/{self.U}/final", {"ref": self.U, "an": "0"})
        self.assertIsNone(json.loads((self.instanz / "fassungen" / f"{self.U}.json").read_text())["final"])
        self.assertEqual(self.post(f"/dokument/{self.U}/final", {"ref": self.NB, "an": "1"})[0], 404)
        self.assertEqual(self.post(f"/dokument/{self.U}/final", {"ref": self.U}, origin="https://b.de")[0], 403)

    def test_eigene_fassung(self):
        status, _, kopf = self.post(f"/dokument/{self.U}/eigene", {"einmal": "e1"},
                                    dateien=[("Mein Exposé.docx", b"MEINS")], feld="datei")
        self.assertEqual(status, 303)
        self.post(f"/dokument/{self.U}/eigene", {"einmal": "e1"}, dateien=[("Mein Exposé.docx", b"MEINS")],
                  feld="datei")  # Doppelklick
        stand = json.loads((self.instanz / "fassungen" / f"{self.U}.json").read_text())
        self.assertEqual([e["name"] for e in stand["eigene"]], ["Mein Exposé.docx"])
        self.assertEqual(self.get(f"/dokument/{self.U}/eigene/1")[1], "MEINS")
        html = self.get(f"/dokument/{self.U}")[1]
        self.assertIn("Deine Fassung 1", html)
        self.assertEqual(self.post(f"/dokument/{self.U}/eigene", {}, dateien=[("x.exe", b"MZ")], feld="datei")[0],
                         400)

    def test_rueckmeldung(self):
        with mock.patch.object(app, "AUFTRAEGE", "aus"):
            status, html, _ = self.post(f"/dokument/{self.U}/rueckmeldung", {"text": "kürzer"})
        self.assertEqual(status, 400)
        self.assertIn("ausgeschaltet", html)
        self.assertEqual(self.post(f"/dokument/{self.U}/rueckmeldung", {"text": ""})[0], 400)
        status, _, kopf = self.post(f"/dokument/{self.U}/rueckmeldung", {"text": "Bitte kürzer", "einmal": "r1"})
        self.assertEqual((status, kopf["location"]), (303, f"/dokument/{self.U}?erledigt=rueckmeldung"))
        self.post(f"/dokument/{self.U}/rueckmeldung", {"text": "Bitte kürzer", "einmal": "r1"})  # Doppelklick
        fb = auftraege.neue("feedback", basis=self.instanz / "auftraege")
        self.assertEqual([(a["bezug"], a["text"]) for a in fb], [(self.U, "Bitte kürzer")])
        self.assertEqual(self.gestartet, [["systemctl", "--user", "start", "--no-block", "feedback.service"]])
        self.assertIn("Bitte kürzer", self.get(f"/dokument/{self.U}")[1])
        self.assertEqual(self.post(f"/dokument/{self.NB}/rueckmeldung", {"text": "x"})[0], 404)


class TestEigeneAnsichten(Aufbau):
    R = "20261109-120000-uni-cccccc"
    P = "20261109-130000-uni-dddddd"
    UE = "20261109-130000-abcdef"

    def setUp(self):
        super().setUp()
        (self.tmp / "arten.toml").write_text(ARTEN + """
[[art]]
kennung = "recherche"
name = "Research-Bericht"
beschreibung = "x"
agent = "uni"
aktiv = true
ansicht = "recherche"
rueckmeldung = false

[[art]]
kennung = "pruefung2"
name = "Prüfung"
beschreibung = "x"
agent = "uni"
aktiv = true
ansicht = "pruefung"
rueckmeldung = false
""", encoding="utf-8")
        uni = self.tmp / "uni"
        r = uni / "data" / "recherchen" / self.R / "recherche"
        r.mkdir(parents=True)
        (r / "geprueft.json").write_text(json.dumps({"fragen": [{"id": "F1", "frage": "Wirkt <Borsalz>?"}],
                                                     "aussagen": [{"id": "A1", "frage": "F1", "text": "Ja",
                                                                   "status": "gesichert"}]}), encoding="utf-8")
        (r.parent / "Recherchebericht.md").write_text("# Bericht\n\nBorsalz **wirkt**.\n", encoding="utf-8")
        m = uni / "data" / "lernen" / "holzschutz"
        (m / "uebungen" / self.UE).mkdir(parents=True)
        (m / "uebungen" / self.UE / "auswertung.json").write_text(json.dumps(
            {"gesamt": "Solide", "punkte": [{"titel": "Fachwissen", "stufe": "teilweise", "stufe_text": "teilweise",
                                             "begruendung": "fehlt etwas"}],
             "karten_neu": [{"thema": "t1", "frage": "Was ist Borsalz?", "antwort": "Salz"}]}), encoding="utf-8")
        (m / "pruefungsplan.json").write_text(json.dumps({"themen": [{"id": "t1", "titel": "Salze"}]}))
        (m / "karten.json").write_text("[]")
        erledigt = self.instanz / "auftraege" / "erledigt"
        erledigt.mkdir(parents=True)
        for a in ({"id": self.R, "art": "recherche", "ergebnis_dateien": [f"data/recherchen/{self.R}/Recherchebericht.md"],
                   "daten": {"titel": "Borsalz", "ansicht": {"recherche": f"data/recherchen/{self.R}/recherche"}}},
                  {"id": self.P, "art": "pruefung2", "ergebnis_dateien": [],
                   "daten": {"titel": "Übung", "ansicht": {"modul": "holzschutz", "uebung": self.UE}}}):
            a.update({"agent": "uni", "status": "erledigt", "text": "x", "erstellt": "2026-11-09T12:00:00+01:00",
                      "abgeschlossen": "2026-11-09T12:30:00+01:00", "ergebnis": "fertig"})
            (erledigt / f"{a['id']}.json").write_text(json.dumps(a), encoding="utf-8")

    def test_recherche(self):
        status, html, _ = self.get(f"/dokument/{self.R}")
        self.assertEqual(status, 200)
        self.assertIn("Wirkt &lt;Borsalz&gt;?", html)
        self.assertIn("<strong>wirkt</strong>", html)  # Recherchebericht.md
        self.assertIn("gesichert (1)", html)
        self.assertNotIn('id="rueckmeldung"', html)
        self.assertIn("Literatursuche", self.get(f"/dokument/{self.R}?ansicht=suche")[1])
        self.assertEqual(self.get(f"/dokument/{self.R}/datei/{self.R}/0")[1], "# Bericht\n\nBorsalz **wirkt**.\n")

    def test_pruefung(self):
        html = self.get(f"/dokument/{self.P}")[1]
        self.assertIn("Solide", html)
        self.assertIn("Was ist Borsalz?", html)
        self.assertIn(f"https://uni.meldro.de/modul/holzschutz/uebung/{self.UE}", html)
        self.assertIn("1 Karten im Portal übernehmen", html)

    def test_boese_ansicht_zeigt_nichts(self):
        pfad = self.instanz / "auftraege" / "erledigt" / f"{self.R}.json"
        a = json.loads(pfad.read_text())
        a["daten"]["ansicht"] = {"recherche": "data/recherchen/../../../shared"}
        pfad.write_text(json.dumps(a))
        status, html, _ = self.get(f"/dokument/{self.R}")
        self.assertEqual(status, 200)
        self.assertNotIn("Wirkt", html)


class TestZuordnungApp(TestDokument):
    def test_altes_ergebnis_am_ort(self):
        pfad = self.instanz / "auftraege" / "erledigt" / f"{self.U}.json"
        a = json.loads(pfad.read_text())
        del a["ort"]
        pfad.write_text(json.dumps(a))
        self.assertNotIn("Exposé Holzschutz", self.get(f"/ort/{self.k}")[1])
        (self.instanz / "orte-zuordnung.json").write_text(json.dumps({"zuordnung": {self.U: self.k}}))
        self.assertIn("Exposé Holzschutz", self.get(f"/ort/{self.k}")[1])
        self.assertIn(f'href="/ort/{self.k}"', self.get(f"/dokument/{self.U}")[1].split('aria-label="Brotkrumen"')[1][:600])
        (self.instanz / "orte-zuordnung.json").write_text("kaputt")
        self.assertEqual(self.get(f"/ort/{self.k}")[0], 200)
