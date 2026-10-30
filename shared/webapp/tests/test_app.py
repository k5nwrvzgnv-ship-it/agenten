import http.client
import json
import shutil
import socket
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import uvicorn

import app


class UnixVerbindung(http.client.HTTPConnection):
    def __init__(self, pfad):
        super().__init__("localhost")
        self.pfad = pfad

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.pfad)


def schreibe(pfad: Path, daten: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")


class TestApp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.instanz = self.tmp / "instanz"
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261030-140944-unterricht-93e29e.json", {
            "id": "20261030-140944-unterricht-93e29e", "agent": "unterricht", "quelle": "portal-material",
            "text": "Arbeitsblatt <Kant> & Strafe", "status": "erledigt",
            "erstellt": "2026-10-30T14:09:44+01:00", "abgeschlossen": "2026-10-30T14:16:49+01:00",
            "ergebnis": "", "ergebnis_dateien": ["data/arbeit/x/Arbeitsblatt.docx"]})
        schreibe(self.instanz / "freigabe" / "offen" / "20261025-003745-examen-0c44bf.json", {
            "id": "20261025-003745-examen-0c44bf", "agent": "examen", "typ": "entwurf",
            "titel": "Umfrage vor der Reihe", "erstellt": "2026-10-25T00:37:45+02:00", "status": "offen"})
        (self.instanz / ".env").write_text("PERSON=Lia\n")
        (self.instanz / ".env").chmod(0o600)
        patch = mock.patch.object(app, "INSTANZ", self.instanz)
        patch.start()
        self.addCleanup(patch.stop)

        self.sock = self.tmp / "data" / "webapp.sock"
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

    def hole(self, pfad, methode="GET"):
        v = UnixVerbindung(str(self.sock))
        v.request(methode, pfad)
        r = v.getresponse()
        inhalt = r.read().decode("utf-8")
        v.close()
        return r, inhalt

    def test_heute_zeigt_echte_eintraege_ohne_ids(self):
        r, html = self.hole("/")
        self.assertEqual(r.status, 200)
        self.assertIn("Hallo Lia.", html)
        self.assertIn("Umfrage vor der Reihe", html)
        self.assertIn("Setzt du selbst ein", html)
        self.assertIn("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", html)  # Jinja maskiert
        self.assertIn("1 Word-Datei", html)
        for verboten in ("0c44bf", "93e29e", "unterricht", "examen"):
            self.assertNotIn(verboten, html)
        self.assertIn('src="/statisch/htmx-2.0.4.min.js"', html)

    def test_teil_und_kopfzeilen(self):
        r, html = self.hole("/teile/heute")
        self.assertEqual(r.status, 200)
        self.assertNotIn("<html", html)
        self.assertIn("Wartet auf dich", html)
        self.assertIn("default-src 'self'", r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("Cache-Control"), "no-store")

    def test_nur_lesen_und_keine_doku(self):
        self.assertEqual(self.hole("/", "POST")[0].status, 405)
        self.assertEqual(self.hole("/docs")[0].status, 404)
        self.assertEqual(self.hole("/openapi.json")[0].status, 404)

    def test_statisch(self):
        r, css = self.hole("/statisch/stil.css")
        self.assertEqual(r.status, 200)
        self.assertIn("--akzent: #d4290f", css)
        self.assertEqual(self.hole("/statisch/../app.py")[0].status, 404)

    def test_socket_ordner_nur_fuer_agent(self):
        self.assertEqual(stat.S_IMODE(self.sock.parent.stat().st_mode), 0o700)


class TestHtmx(unittest.TestCase):
    def test_pruefsumme(self):
        import hashlib
        ordner = Path(app.__file__).parent / "statisch"
        erwartet = (ordner / "htmx-2.0.4.min.js.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256((ordner / "htmx-2.0.4.min.js").read_bytes()).hexdigest(), erwartet)


if __name__ == "__main__":
    unittest.main()
