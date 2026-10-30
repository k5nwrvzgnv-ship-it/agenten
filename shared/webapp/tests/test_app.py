import http.client
import json
import re
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


NB = "20261030-143100-unterricht-bbbbbb"


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
            "ergebnis": "", "ergebnis_dateien": ["data/arbeit/x/Arbeitsblatt.docx"],
            "daten": {"kern": "Ein Arbeitsblatt zu Kant.", "punkte": ["Fall", "Aufgabe"], "pruefen": "Passt der Fall?"}})
        schreibe(self.instanz / "freigabe" / "offen" / "20261025-003745-examen-0c44bf.json", {
            "id": "20261025-003745-examen-0c44bf", "agent": "examen", "typ": "entwurf",
            "titel": "Umfrage vor der Reihe", "erstellt": "2026-10-25T00:37:45+02:00", "status": "offen",
            "inhalt": "Kurze Umfrage\n\n1. Frage\n   [ ] ja   [ ] nein\n" + "Ende " * 100,
            "daten": {"einsatz": "Lia selbst, auf Papier", "datei": "lia/examen/impuls.md"}})
        # Agent-Ordner neben der Instanz: Ergebnisdatei mit Vorschau des Renderers
        arbeit = self.tmp / "unterricht" / "data" / "arbeit" / "x"
        (arbeit / "Arbeitsblatt-vorschau").mkdir(parents=True)
        (arbeit / "Arbeitsblatt.docx").write_bytes(b"DOCX-INHALT")
        (arbeit / "Arbeitsblatt-vorschau" / "Arbeitsblatt.pdf").write_bytes(b"%PDF-1.7 vorschau")
        for n in (1, 2):
            (arbeit / "Arbeitsblatt-vorschau" / f"Arbeitsblatt-seite-0{n}.png").write_bytes(b"PNG" + bytes([n]))
        (self.tmp / "geheim.pdf").write_bytes(b"%PDF geheim")  # außerhalb jedes Agent-Ordners
        (self.tmp / "unterricht" / ".env").write_text("TOKEN=x\n")
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261030-150000-unterricht-aaaaaa.json", {
            "id": "20261030-150000-unterricht-aaaaaa", "agent": "unterricht", "text": "Böse Pfade",
            "status": "erledigt", "abgeschlossen": "2026-10-01T10:00:00+02:00", "ergebnis": "x",
            "ergebnis_dateien": ["../geheim.pdf", str(self.tmp / "geheim.pdf"), ".env",
                                 "data/arbeit/x/../../../../geheim.pdf"]})
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261030-110916-feedback-1c1e7e.json", {
            "id": "20261030-110916-feedback-1c1e7e", "agent": "feedback", "text": "Ist das <zu> lang?", "status": "erledigt",
            "bezug": "20261030-140944-unterricht-93e29e", "erstellt": "2026-10-30T14:30:00+01:00",
            "abgeschlossen": "2026-10-30T14:30:09+01:00", "daten": {"nachbesserung": NB}})
        # Nachbesserung zur Rückmeldung: Antwort ohne Dateien, gehört zum selben Auftrag
        schreibe(self.instanz / "auftraege" / "erledigt" / f"{NB}.json", {
            "id": NB, "agent": "unterricht", "bezug": "20261030-140944-unterricht-93e29e",
            "text": "Nachbesserung zu deinem Ergebnis (Auftrag 20261030-140944-unterricht-93e29e)", "status": "erledigt",
            "erstellt": "2026-10-30T14:31:00+01:00", "abgeschlossen": "2026-10-30T14:40:00+01:00", "ergebnis": "x",
            "ergebnis_dateien": [], "daten": {"kern": "Etwa zwei Seiten, passt in eine Stunde."}})
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261022-232618-unterricht-67ba47.json", {
            "id": "20261022-232618-unterricht-67ba47", "agent": "unterricht", "text": "formatvorlage anwenden",
            "status": "fehlgeschlagen", "abgeschlossen": "2026-10-22T23:27:02+02:00",
            "ergebnis": "Gerade ist das gemeinsame Kontingent aufgebraucht.", "ergebnis_dateien": []})
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

    def hole(self, pfad, methode="GET", roh=False):
        v = UnixVerbindung(str(self.sock))
        v.request(methode, pfad)
        r = v.getresponse()
        inhalt = r.read()
        v.close()
        return r, inhalt if roh else inhalt.decode("utf-8")

    def sichtbar(self, html):
        """HTML ohne Links: IDs dürfen nur in href stehen."""
        return re.sub(r'(href|src)="[^"]*"', "", html)

    def test_heute_zeigt_echte_eintraege_ohne_ids(self):
        r, html = self.hole("/")
        self.assertEqual(r.status, 200)
        self.assertIn("Hallo Lia.", html)
        self.assertIn("Umfrage vor der Reihe", html)
        self.assertIn("Setzt du selbst ein", html)
        self.assertIn("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", html)  # Jinja maskiert
        self.assertIn("1 Word-Datei", html)
        for verboten in ("0c44bf", "93e29e", "unterricht", "examen"):
            self.assertNotIn(verboten, self.sichtbar(html))
        self.assertIn('href="/entwurf/20261025-003745-examen-0c44bf"', html)
        self.assertIn('href="/ergebnis/20261030-140944-unterricht-93e29e"', html)
        self.assertIn('href="/ergebnis/20261022-232618-unterricht-67ba47"', html)
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

    def test_ergebnis(self):
        r, html = self.hole("/ergebnis/20261030-140944-unterricht-93e29e")
        self.assertEqual(r.status, 200)
        for text in ("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", "Material · heute 14:40", "Ein Arbeitsblatt zu Kant.",
                     "Bitte prüfen:</b> Passt der Fall?", "Das Wichtigste", "Seiten", "Dateien", "Zurück",
                     "Etwa zwei Seiten, passt in eine Stunde.", "Aus Fassung 1", "Verlauf", "Deine Rückmeldung",
                     "„Ist das &lt;zu&gt; lang?“", "steht oben", "<details>"):
            self.assertIn(text, html)
        basis = "/ergebnis/20261030-140944-unterricht-93e29e/datei/0"
        self.assertIn(f'href="{basis}/pdf"', html)
        self.assertIn(f'href="{basis}"', html)
        self.assertIn(f'src="{basis}/seite/2"', html)
        self.assertNotIn(f"{basis}/seite/3", html)
        for verboten in ("93e29e", "unterricht", "data/arbeit", "Wie ist es", "Anmerk"):
            self.assertNotIn(verboten, self.sichtbar(html))

    def test_downloads_und_seiten(self):
        basis = "/ergebnis/20261030-140944-unterricht-93e29e/datei/0"
        r, inhalt = self.hole(basis, roh=True)
        self.assertEqual((r.status, inhalt), (200, b"DOCX-INHALT"))
        self.assertIn("attachment", r.getheader("Content-Disposition"))
        self.assertIn("Arbeitsblatt.docx", r.getheader("Content-Disposition"))
        r, inhalt = self.hole(basis + "/pdf", roh=True)
        self.assertEqual((r.status, r.getheader("Content-Type"), inhalt),
                         (200, "application/pdf", b"%PDF-1.7 vorschau"))
        r, inhalt = self.hole(basis + "/seite/2", roh=True)
        self.assertEqual((r.status, r.getheader("Content-Type"), inhalt), (200, "image/png", b"PNG\x02"))
        for falsch in (basis + "/seite/0", basis + "/seite/3", basis[:-1] + "1", basis[:-1] + "x",
                       basis + "/../../../../.env"):
            self.assertEqual(self.hole(falsch)[0].status, 404, falsch)

    def test_pfad_ausserhalb_des_agent_ordners_404(self):
        r, html = self.hole("/ergebnis/20261030-150000-unterricht-aaaaaa")
        self.assertEqual(r.status, 200)
        self.assertNotIn("/datei/", html)  # keine Knöpfe für unerlaubte Dateien
        for nr in range(4):  # ../, absolut, versteckt, .. mitten im Pfad
            r, inhalt = self.hole(f"/ergebnis/20261030-150000-unterricht-aaaaaa/datei/{nr}", roh=True)
            self.assertEqual(r.status, 404, nr)
            self.assertNotIn(b"geheim", inhalt)
            self.assertEqual(self.hole(f"/ergebnis/20261030-150000-unterricht-aaaaaa/datei/{nr}/pdf")[0].status, 404)

    def test_fehlgeschlagen_zeigt_grund(self):
        r, html = self.hole("/ergebnis/20261022-232618-unterricht-67ba47")
        self.assertEqual(r.status, 200)
        self.assertIn("Hat nicht geklappt", html)
        self.assertIn("Gerade ist das gemeinsame Kontingent aufgebraucht.", html)

    def test_unbekannt_und_ungueltig_404(self):
        for pfad in ("/ergebnis/20261030-999999-unterricht-ffffff", "/ergebnis/..%2F..%2Fapp",
                     "/ergebnis/nicht-gueltig", "/entwurf/20261030-140944-unterricht-93e29e",
                     "/entwurf/20261025-003745-examen-0c44bf.json"):
            r, html = self.hole(pfad)
            self.assertEqual(r.status, 404, pfad)
            self.assertIn("Nicht gefunden", html)

    def test_kette_ein_auftrag_und_umleitung(self):
        _, html = self.hole("/")
        self.assertEqual(html.count('href="/ergebnis/20261030-140944-unterricht-93e29e"'), 1)
        self.assertNotIn(NB, html)  # keine eigene Zeile für die Nachbesserung
        self.assertNotIn("Antwort auf deine Rückmeldung", html)
        self.assertIn("1 Word-Datei · nach deiner Rückmeldung", html)
        for aid in (NB, "20261030-110916-feedback-1c1e7e"):  # Nachbesserung und Rückmeldung führen zum Ursprung
            r, _ = self.hole(f"/ergebnis/{aid}")
            self.assertEqual((r.status, r.getheader("Location")), (303, "/ergebnis/20261030-140944-unterricht-93e29e"))

    def test_entwurf(self):
        r, html = self.hole("/entwurf/20261025-003745-examen-0c44bf")
        self.assertEqual(r.status, 200)
        self.assertIn("Kurze Umfrage\n\n1. Frage\n   [ ] ja   [ ] nein\n" + "Ende " * 99, html)  # ganz
        self.assertIn("<dt>Einsatz</dt><dd>Lia selbst, auf Papier</dd>", html)
        self.assertIn("Setzt du selbst ein", html)
        for verboten in ("impuls.md", "0c44bf", "examen", "<button", "<form"):
            self.assertNotIn(verboten, self.sichtbar(html))
        self.assertEqual(self.hole("/entwurf/20261025-003745-examen-0c44bf", "POST")[0].status, 405)

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
