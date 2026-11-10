import hashlib
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
from datetime import datetime

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


class FesteZeit(datetime):
    """Web-App und Ablage sehen immer den Abend des 30.10.2026, damit „heute 14:16“ nicht vom Testtag abhängt."""

    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 30, 18, 0, tzinfo=tz)


class Aufbau(unittest.TestCase):
    """Echter Uvicorn auf einem Socket im Temp-Ordner, Instanz mit Beispielaufträgen."""

    oberflaeche = "neu"  # die Tests hier prüfen oberflaeche/; die alte (vorlagen/) prüft test_alt.py

    def setUp(self):
        for zeit in (mock.patch.object(app, "datetime", FesteZeit), mock.patch.dict(app._EINMAL, clear=True),
                     mock.patch("agentkit._ablage.jetzt", lambda: "2026-10-30T17:59:00+01:00")):
            zeit.start()
            self.addCleanup(zeit.stop)
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
        self.meldungen = []  # Meldungen an Jan (agentkit.strukturpflege) gehen in Tests nur hierher
        for name, wert in (("INSTANZ", self.instanz), ("DATEN", self.tmp / "webdaten"),
                           ("MELDEN", self.meldungen.append), ("OBERFLAECHE", self.oberflaeche)):
            patch = mock.patch.object(app, name, wert)
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

    def hole(self, pfad, methode="GET", roh=False, body=None, kopf=None):
        v = UnixVerbindung(str(self.sock))
        v.request(methode, pfad, body=body, headers=kopf or {})
        r = v.getresponse()
        inhalt = r.read()
        v.close()
        return r, inhalt if roh else inhalt.decode("utf-8")

    def sichtbar(self, html):
        """HTML ohne Links und versteckte Formularwerte: IDs dürfen nur dort stehen."""
        return re.sub(r'(href|src|action|value)="[^"]*"', "", html)


class TestApp(Aufbau):

    def test_heute_zeigt_echte_eintraege_ohne_ids(self):
        r, html = self.hole("/")
        self.assertEqual(r.status, 200)
        self.assertIn("Hallo Lia.", html)
        self.assertIn("Umfrage vor der Reihe", html)
        self.assertIn("Du entscheidest, ob du ihn einsetzt", html)
        self.assertIn("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", html)  # Jinja maskiert
        self.assertIn("1 Word-Datei", html)
        for verboten in ("0c44bf", "93e29e", "unterricht", "examen"):
            self.assertNotIn(verboten, self.sichtbar(html))
        self.assertIn('href="/entwurf/20261025-003745-examen-0c44bf"', html)
        self.assertIn('href="/ergebnis/20261030-140944-unterricht-93e29e"', html)
        self.assertIn('href="/ergebnis/20261022-232618-unterricht-67ba47"', html)
        self.assertIn('src="/statisch/htmx-2.0.4.min.js"', html)

    def test_rahmen(self):
        _, html = self.hole("/")
        for text in ('<nav class="baum"', '<nav class="krumen"',
                     '<li aria-current="page">Heute</li>', 'aria-current="page"><span>Heute</span>'
                     '<span class="baum-zahl">2</span>', 'hx-get="/teile/heute"'):
            self.assertIn(text, html)
        for weg in ("ordnung=", "/unterricht", "Unterricht"):
            self.assertNotIn(weg, html)
        r, _ = self.hole("/unterricht")
        self.assertEqual((r.status, r.getheader("Location")), (301, "/"))
        _, html = self.hole("/entwurf/20261025-003745-examen-0c44bf")  # Einzelansicht im selben Rahmen
        self.assertIn('<span class="baum-zahl">2</span>', html)
        self.assertIn('<li aria-current="page">Umfrage vor der Reihe</li>', html)
        r, html = self.hole("/reihe/gibt-es-nicht")
        self.assertEqual(r.status, 404)
        self.assertIn('<nav class="baum"', html)

    def test_teil_und_kopfzeilen(self):
        r, html = self.hole("/teile/heute")
        self.assertEqual(r.status, 200)
        self.assertNotIn("<html", html)
        self.assertIn("Wartet auf dich", html)
        self.assertIn("default-src 'self'", r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("Referrer-Policy"), "same-origin")  # no-referrer machte Origin zu null: 403
        self.assertEqual(r.getheader("Cache-Control"), "no-store")

    def test_nur_lesen_und_keine_doku(self):
        self.assertEqual(self.hole("/", "POST")[0].status, 405)
        self.assertEqual(self.hole("/docs")[0].status, 404)
        self.assertEqual(self.hole("/openapi.json")[0].status, 404)

    def test_statisch(self):
        r, css = self.hole("/statisch/ruhig.css")
        self.assertEqual(r.status, 200)
        self.assertIn("--akzent: #d44c47", css)
        self.assertEqual(self.hole("/statisch/../app.py")[0].status, 404)
        # Befund 03.11. Punkt 5: Der Hinweis mit Rückgängig bleibt nach dem Sprung im Bild. Gemessen wird im Browser.
        self.assertRegex(css, r"\.aktion-hinweis \{ position: sticky; top: 0;")

    def test_schriftgroessen(self):
        """Ruhige Oberfläche (ui-plan-notion.md): 12/14/16/20/32, schmal 26. Neue Größen müssen hier begründet werden."""
        _, css = self.hole("/statisch/ruhig.css")
        self.assertEqual({int(n) for n in re.findall(r"font-size: (\d+)px", css)}, {12, 14, 16, 20, 26, 32})

    def test_rot_nur_fuer_wartendes_und_fehler(self):
        """Befund 03.11., Kapitel 4: Rot sagt nur noch „schau hier hin“. Neue rote Stellen müssen hier begründet werden."""
        _, css = self.hole("/statisch/ruhig.css")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        rot = {w.strip() for sel, inhalt in re.findall(r"([^{}]+)\{([^{}]*)\}", css) if "var(--akzent)" in inhalt
               for w in sel.split(",")}
        self.assertEqual(rot, {".baum-zahl", ".akzent", ".punkt-rot", ".marke-rot", ".hinweis-fehler", ".fehler"})

    def test_ergebnis(self):
        r, html = self.hole("/ergebnis/20261030-140944-unterricht-93e29e")
        self.assertEqual(r.status, 200)
        # Material-Ansicht wie Board "Desktop": Kopf, zwei Seiten, Knopf-Spalte, Das Wichtigste, Fassungen
        for text in ("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", "Material · Word", "Neu · wartet",
                     "Ein Arbeitsblatt zu Kant.", "Bitte prüfen:</b> Passt der Fall?", "Das Wichtigste",
                     '<a href="/">Heute</a>', "Etwa zwei Seiten, passt in eine Stunde.", "aus Fassung 1",
                     "Fassungen", "Deine Rückmeldung", "„Ist das &lt;zu&gt; lang?“", "steht oben", "<details>",
                     ">In Word öffnen<", ">PDF zum Drucken<", ">Als final markieren<", ">Rückmeldung geben<",
                     ">Eigene Fassung hochladen<", "von mir, heute 14:16", "2 Seiten · ansehen"):
            self.assertIn(text, html)
        basis = "/ergebnis/20261030-140944-unterricht-93e29e/datei/0"
        self.assertIn(f'href="{basis}/pdf" download>PDF zum Drucken', html)
        self.assertIn(f'href="{basis}" download>In Word öffnen', html)
        # oben die ersten zwei Seiten zum Durchblättern, an der früheren Fassung die Karte
        for m in (1, 2):
            self.assertIn(f'href="{basis}/ansehen?seite={m}"', html)
            self.assertIn(f'src="{basis}/seite/{m}"', html)
        self.assertEqual(html.count(f'<a class="dateiname" href="{basis}/ansehen">Arbeitsblatt</a>'), 1)
        self.assertLess(html.index("von mir, heute 14:40"), html.index("von mir, heute 14:16"))
        # „Als final markieren“ abgesetzt nach den anderen Knöpfen (Chrome-Test Nr. 11)
        self.assertLess(html.index("Eigene Fassung hochladen<"), html.index('<div class="knopf-abgesetzt">'))
        self.assertLess(html.index('<div class="knopf-abgesetzt">'), html.index("Als final markieren"))
        self.assertNotIn("<script", html)
        self.assertNotIn('id="rueck-text"', html)  # Rückmeldung erst nach Klick
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

    def test_seiten_betrachter(self):
        basis = "/ergebnis/20261030-140944-unterricht-93e29e/datei/0"
        r, html = self.hole(basis + "/ansehen")
        self.assertEqual(r.status, 200)
        for text in (f'src="{basis}/seite/1"', f'href="{basis}/ansehen?seite=2" rel="next"', "1 / 2",
                     f'href="{basis}/pdf"', f'href="{basis}" download', "Zurück zum Ergebnis",
                     'href="/ergebnis/20261030-140944-unterricht-93e29e">Arbeitsblatt &lt;Kant&gt; &amp; Strafe</a>',
                     '<li aria-current="page">Arbeitsblatt</li>', "Seite 1 von 2"):
            self.assertIn(text, html)
        self.assertNotIn('rel="prev"', html)
        self.assertNotIn("<script", html)
        _, html = self.hole(basis + "/ansehen?seite=2")
        self.assertIn(f'src="{basis}/seite/2"', html)
        self.assertIn(f'href="{basis}/ansehen?seite=1" rel="prev"', html)
        self.assertNotIn('rel="next"', html)
        for verboten in ("93e29e", "unterricht", "data/arbeit"):
            self.assertNotIn(verboten, self.sichtbar(html))
        for falsch in ("?seite=0", "?seite=3", "?seite=x", "?seite=", "?seite=-1"):
            self.assertEqual(self.hole(basis + "/ansehen" + falsch)[0].status, 404, falsch)
        for falsch in (basis[:-1] + "1/ansehen", "/ergebnis/20261030-150000-unterricht-aaaaaa/datei/0/ansehen",
                       "/ergebnis/20261022-232618-unterricht-67ba47/datei/0/ansehen",
                       "/ergebnis/20261030-999999-unterricht-ffffff/datei/0/ansehen"):
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
        self.assertIn("Die Rechenzeit war aufgebraucht.", html)
        self.assertNotIn("Kontingent", html)

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
        self.assertIn("Du entscheidest, ob du ihn einsetzt.", html)
        self.assertNotIn("Setzt du selbst ein", html)  # nicht doppelt mit dem Knopf (Chrome-Test Nr. 12)
        self.assertIn('href="/" aria-current="location"', html)  # Entwurf ohne Reihe: Heute als Ort
        for verboten in ("impuls.md", "0c44bf", "examen"):
            self.assertNotIn(verboten, self.sichtbar(html))
        self.assertIn("Setze ich selbst ein</button>", html)

    def test_entwurf_entscheiden(self):
        url = "/entwurf/20261025-003745-examen-0c44bf"

        def post(stand, token=None):
            body, art = multipart({"token": token or app.logik.formular_token(app.GEHEIM), "stand": stand}, [])
            return self.hole(url, "POST", body=body,
                             kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})
        self.assertIn("Umfrage vor der Reihe", self.hole("/")[1])
        self.assertEqual(post("selbst", "falsch")[0].status, 400)
        self.assertEqual(post("quatsch")[0].status, 400)
        r, _ = post("selbst")
        self.assertEqual((r.status, r.getheader("location")), (303, url + "?erledigt=entwurf-selbst"))
        _, html = self.hole(url + "?erledigt=entwurf-selbst")
        self.assertIn("Erledigt: Du setzt den Entwurf selbst ein.", html)
        self.assertIn("Rückgängig</button>", html)
        self.assertNotIn("Umfrage vor der Reihe", self.hole("/")[1].split("Läuft gerade")[0])  # wartet nicht mehr
        self.assertTrue((self.instanz / "freigabe" / "offen" / "20261025-003745-examen-0c44bf.json").exists())
        self.assertEqual(post("")[0].status, 303)
        self.assertIn("Umfrage vor der Reihe", self.hole("/")[1])
        # Entwürfe nach außen entscheidet Jan
        schreibe(self.instanz / "freigabe" / "offen" / "20261025-003745-examen-aaaaaa.json", {
            "id": "20261025-003745-examen-aaaaaa", "agent": "examen", "typ": "mail", "titel": "Mail",
            "erstellt": "2026-10-25T00:37:45+02:00", "status": "offen", "inhalt": "x"})
        self.assertNotIn("<button", self.hole("/entwurf/20261025-003745-examen-aaaaaa")[1])
        body, art = multipart({"token": app.logik.formular_token(app.GEHEIM), "stand": "selbst"}, [])
        r, _ = self.hole("/entwurf/20261025-003745-examen-aaaaaa", "POST", body=body,
                         kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})
        self.assertEqual(r.status, 404)

    def test_socket_ordner_nur_fuer_agent(self):
        self.assertEqual(stat.S_IMODE(self.sock.parent.stat().st_mode), 0o700)


def multipart(felder: dict, dateien: list[tuple[str, bytes]]) -> tuple[bytes, str]:
    grenze = "----grenze7MA4YWxk"
    teile = [f'--{grenze}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{w}\r\n'.encode()
             for n, werte in felder.items() for w in (werte if isinstance(werte, list) else [werte])]
    for name, inhalt in dateien:
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="dateien"; filename="{name}"\r\n'
                     "Content-Type: application/octet-stream\r\n\r\n".encode() + inhalt + b"\r\n")
    return b"".join(teile) + f"--{grenze}--\r\n".encode(), f"multipart/form-data; boundary={grenze}"


class TestNeuerAuftrag(Aufbau):
    """Neuer Auftrag über den echten Server."""

    def setUp(self):
        super().setUp()
        for name, wert in (("EINGANG", self.tmp / "eingang"), ("NEUER_AUFTRAG", "test")):
            patch = mock.patch.object(app, name, wert)
            patch.start()
            self.addCleanup(patch.stop)

    def schicke(self, text="Arbeitsblatt Kant, 45 Minuten", dateien=(), token=None, origin="http://localhost"):
        body, art = multipart({"token": token or app.logik.formular_token(app.GEHEIM), "text": text}, list(dateien))
        kopf = {"Content-Type": art, "Content-Length": str(len(body))}
        if origin:
            kopf["Origin"] = origin
        return self.hole("/neu", "POST", body=body, kopf=kopf)

    def neue(self):
        return app.auftraege.neue(basis=self.instanz / "auftraege")

    def test_doppelklick_ein_auftrag(self):
        """Doppelklick auf „Abschicken“: zwei gleiche POST, nur ein Auftrag, beide Antworten gleich."""
        (self.tmp / "unterricht").mkdir(exist_ok=True)
        with mock.patch("agentkit._ablage.jetzt", lambda: "2026-10-30T18:00:00+01:00"), \
                mock.patch.object(app, "NEUER_AUFTRAG", "echt"), mock.patch.object(app, "agent_starten") as start:
            antworten = [self.schicke(dateien=[("Text.pdf", b"PDF")])[0] for _ in range(2)]
            self.assertEqual([(r.status, r.getheader("Location")) for r in antworten], [(303, "/?abgeschickt=1")] * 2)
            start.assert_called_once_with("unterricht")
            self.assertEqual(len(self.neue()), 1)
            # Anderer Text oder andere Datei ist ein neuer Auftrag
            self.assertEqual(self.schicke("Anderes Blatt", [("Text.pdf", b"PDF")])[0].status, 303)
            self.assertEqual(self.schicke(dateien=[("Anders.pdf", b"PDF")])[0].status, 303)
        self.assertEqual(len(self.neue()), 3)

    def test_knopf_sperrt_sich(self):
        _, html = self.hole("/neu?art=arbeitsblatt")
        self.assertIn('<script src="/statisch/einmal.js" defer></script>', html)
        self.assertRegex(html, r'<form [^>]*action="/neu"[^>]* data-einmal[ >]')

    def test_aus_ohne_einstellung_und_nie_test_auf_lias_instanz(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):
            self.assertEqual(self.hole("/neu")[0].status, 404)
            self.assertEqual(self.schicke()[0].status, 404)
            self.assertNotIn('href="/neu"', self.hole("/")[1])
        with mock.patch.object(app, "INSTANZ", app.ECHTE_INSTANZ):
            self.assertEqual(app.neu_modus(), "")  # nur prüfen, nichts abschicken
        self.assertEqual(self.neue(), [])

    def test_formular_und_einstieg_in_heute(self):
        r, html = self.hole("/neu")  # ohne Art: Galerie
        self.assertEqual(r.status, 200)
        for text in ('href="/neu?art=arbeitsblatt"', 'href="/neu?art=praesentation"', 'href="/neu?art=tabelle"'):
            self.assertIn(text, html)
        self.assertNotIn('type="file"', html)
        # Reihenentwurf und LEK baut unterricht seit 30.10.: verlinkt und nicht mehr „kommen bald“ (Nr. 8)
        self.assertIn('href="/neu?art=lek"', html)
        self.assertNotIn("Lernerfolgskontrolle) kommen", html)
        r, html = self.hole("/neu?art=arbeitsblatt")
        self.assertEqual(r.status, 200)
        self.assertIn("Was soll drauf?", html)
        self.assertIn('<input type="hidden" name="art" value="arbeitsblatt">', html)
        self.assertNotIn('name="art"', self.hole("/neu?art=quatsch")[1])  # unbekannt: Galerie
        for text in ("Testbetrieb", 'enctype="multipart/form-data"', 'name="token"',
                     "Bitte keine Namen", 'type="file"', "Abschicken"):
            self.assertIn(text, html)
        self.assertIn('href="/neu"', self.hole("/")[1])
        self.assertIn('href="/neu"', self.hole("/teile/heute")[1])

    def test_fremde_herkunft_und_falsches_token_legen_nichts_an(self):
        self.assertEqual(self.schicke(origin=None)[0].status, 403)
        self.assertEqual(self.schicke(origin="https://boese.example")[0].status, 403)
        r, html = self.schicke(token="falsch")
        self.assertEqual(r.status, 400)
        self.assertIn("Die Seite war veraltet", html)
        self.assertIn("Arbeitsblatt Kant, 45 Minuten", html)  # Text bleibt stehen
        self.assertEqual(self.neue(), [])

    def test_auftrag_mit_datei(self):
        r, _ = self.schicke("Arbeitsblatt nach dieser Vorlage", [("../Vorlage.docx", b"DOCX"), ("Foto.JPG", b"JPG")])
        self.assertEqual((r.status, r.getheader("Location")), (303, "/?abgeschickt=1"))
        (a,) = self.neue()
        self.assertEqual((a["agent"], a["quelle"], a["modus"], a["bezug"], a["dienst"]),
                         ("unterricht", "portal-material", "erledigen", None, None))
        self.assertEqual(a["dateien"], [f"data/eingang/{a['id']}/Vorlage.docx", f"data/eingang/{a['id']}/Foto.jpg"])
        self.assertTrue(a["text"].startswith("Arbeitsblatt nach dieser Vorlage\n\nAngehängte Dateien von Lia"))
        self.assertEqual((self.tmp / "unterricht" / a["dateien"][0]).read_bytes(), b"DOCX")
        self.assertEqual(list((self.tmp / "eingang").iterdir()), [])  # Zwischenablage aufgeräumt
        _, html = self.hole("/?abgeschickt=1")
        self.assertIn("Dein Auftrag ist unterwegs", html)
        self.assertIn("Arbeitsblatt nach dieser Vorlage", html.split("Läuft gerade</h2>")[1])

    def test_falsche_eingaben(self):
        r, html = self.schicke("Vorlage", [("tool.exe", b"MZ")])
        self.assertEqual(r.status, 400)
        self.assertIn("„tool.exe“: Diese Art Datei kann ich nicht lesen", html)
        r, html = self.schicke("   ")
        self.assertEqual(r.status, 400)
        self.assertIn("Schreib bitte kurz, was du brauchst.", html)
        self.assertEqual(self.neue(), [])

    def test_echt_startet_den_agenten(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", "echt"), mock.patch.object(app, "agent_starten") as start:
            self.assertEqual(self.schicke()[0].status, 303)
        start.assert_called_once_with("unterricht")
        self.assertEqual(len(self.neue()), 1)
        with mock.patch.object(app, "agent_starten") as start:  # im Testbetrieb nicht
            self.schicke()
        start.assert_not_called()


REIHEN = """
[[fach]]
id = "ethik"
name = "Ethik"

[[fach]]
id = "darstellendes-spiel"
name = "Darstellendes Spiel"

[[klasse]]
id = "ethik-8"
fach = "ethik"
name = "8"

[[klasse]]
id = "darstellendes-spiel-kurs-12"
fach = "darstellendes-spiel"
name = "Kurs 12"

[[reihe]]
id = "strafe"
klasse = "ethik-8"
titel = "Straftheorien"
reihenfrage = "Wozu <strafen> wir?"
behandelt = ["Kant", "Bentham"]
agenten = ["examen"]

[[reihe]]
id = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"
klasse = "darstellendes-spiel-kurs-12"
titel = "Der nackte Wahnsinn"
agenten = ["theater"]
"""


class TestOrdnung(Aufbau):
    """Fach, Klasse und Reihe über den echten Server (reihen.toml in der Instanz)."""

    def setUp(self):
        super().setUp()
        (self.instanz / "reihen.toml").write_text(REIHEN, encoding="utf-8")
        for name, wert in (("EINGANG", self.tmp / "eingang"), ("NEUER_AUFTRAG", "test")):
            patch = mock.patch.object(app, name, wert)
            patch.start()
            self.addCleanup(patch.stop)

    def test_baum_und_ort_in_heute(self):
        _, html = self.hole("/")
        for text in ('<a class="baum-fach" href="/fach/ethik">Ethik</a>',
                     '<a class="baum-eintrag baum-gruppe" href="/klasse/ethik-8"><span>Klasse 8</span></a>',
                     '<a class="baum-eintrag tiefe-1" href="/reihe/strafe"><span>Straftheorien</span></a>',
                     '<a class="baum-fach" href="/fach/darstellendes-spiel">Darstellendes Spiel</a>', '<span>Kurs 12</span>',
                     "Ethik › Klasse 8 › Straftheorien"):
            self.assertIn(text, html)
        self.assertNotIn("Theater</", html)

    def test_reihe(self):
        r, html = self.hole("/reihe/strafe")
        self.assertEqual(r.status, 200)
        for text in ("Straftheorien", "Ethik · Klasse 8", "Wozu &lt;strafen&gt; wir?", "Kant; Bentham",
                     "Zur ganzen Reihe", "Umfrage vor der Reihe", 'aria-current="page"><span>Straftheorien</span>',
                     '<li><a href="/fach/ethik">Ethik</a>', '<a href="/klasse/ethik-8">Klasse 8</a>',
                     '<li aria-current="page">Straftheorien</li>'):
            self.assertIn(text, html)
        self.assertNotIn("Arbeitsblatt &lt;Kant&gt;", html)  # Material ohne Reihe steht nur in Heute
        self.assertNotIn("20261030", self.sichtbar(html))
        r, html = self.hole("/reihe/darstellendes-spiel-kurs-12-der-nackte-wahnsinn")
        self.assertEqual(r.status, 200)
        self.assertIn("Noch nichts zur ganzen Reihe.", html)
        self.assertIn("+ Probe", html)  # Reihe des Theater-Agenten: Proben statt Stunden
        self.assertIn("Reihenfrage noch offen", html)  # Chrome-Test Nr. 5
        self.assertNotIn("Reihenfrage noch offen", self.hole("/reihe/strafe")[1])
        _, html = self.hole("/entwurf/20261025-003745-examen-0c44bf")  # Ort als Brotkrume mit Link zur Reihe
        self.assertIn('<a href="/reihe/strafe">Straftheorien</a>', html)

    def test_klasse(self):
        r, html = self.hole("/klasse/ethik-8")
        self.assertEqual(r.status, 200)
        for text in ('<li aria-current="page">Klasse 8</li>', '<li><a href="/fach/ethik">Ethik</a>',
                     'aria-current="page"><span>Klasse 8</span>', '<a class="zeile" href="/reihe/strafe">',
                     "Wozu &lt;strafen&gt; wir?", "1 Sache", "Deine Dateien"):
            self.assertIn(text, html)
        self.assertEqual(self.hole("/klasse/ethik-9")[0].status, 404)
        self.assertEqual(self.hole("/klasse/darstellendes-spiel-kurs-12")[0].status, 200)

    def test_ablage(self):
        def hoch(ort, dateien_, origin="http://localhost"):
            body, art = multipart({"token": app.logik.formular_token(app.GEHEIM)}, dateien_)
            return self.hole(f"/ablage/{ort}", "POST", body=body,
                             kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": origin})[0]
        r = hoch("darstellendes-spiel-kurs-12", [("../Kriterien Theater.pdf", b"%PDF-1"), ("Probe.JPG", b"jpg")])
        self.assertEqual((r.status, r.getheader("location")),
                         (303, "/klasse/darstellendes-spiel-kurs-12?erledigt=abgelegt#ablage"))
        ordner = self.instanz / "ablage" / "darstellendes-spiel-kurs-12"
        self.assertEqual(sorted(x.name for x in ordner.iterdir()), ["Kriterien Theater.pdf", "Probe.jpg"])
        _, html = self.hole("/klasse/darstellendes-spiel-kurs-12?erledigt=abgelegt")
        for text in ("Kriterien Theater.pdf", 'href="/ablage/darstellendes-spiel-kurs-12/Kriterien%20Theater.pdf"',
                     "Gespräche hier und darunter kennen deine Dateien", "PDF · deine Datei", "Foto · deine Datei"):
            self.assertIn(text, html)
        r, inhalt = self.hole("/ablage/darstellendes-spiel-kurs-12/Probe.jpg", roh=True)
        self.assertEqual((r.status, r.getheader("Content-Type"), inhalt), (200, "image/jpeg", b"jpg"))
        for falsch in ("/ablage/darstellendes-spiel-kurs-12/..%2F..%2F.env", "/ablage/x/Probe.jpg",
                       "/ablage/darstellendes-spiel-kurs-12/fehlt.pdf"):
            self.assertEqual(self.hole(falsch)[0].status, 404, falsch)
        self.assertEqual(hoch("strafe", [("IMG_1.heic", b"x")]).getheader("location"),
                         "/reihe/strafe?ablagefehler=heic#ablage")
        self.assertIn("HEIC", self.hole("/reihe/strafe?ablagefehler=heic")[1])
        self.assertEqual(hoch("strafe", [("a.pdf", b"x")], origin="https://boese.example").status, 403)
        self.assertEqual(hoch("gibt-es-nicht", [("a.pdf", b"x")]).status, 404)
        self.assertFalse((self.instanz / "ablage" / "strafe").exists())
        r, _ = self.post("/ablage/darstellendes-spiel-kurs-12/entfernen", {"name": "Probe.jpg"})
        self.assertEqual(r.getheader("location"), "/klasse/darstellendes-spiel-kurs-12?erledigt=entfernt#ablage")
        self.assertEqual([x.name for x in ordner.iterdir()], ["Kriterien Theater.pdf"])

    def test_gespraech(self):
        """Gespräch in der Mitte über die echte Schnittstelle von lia/chat (Ordner im Temp, kein Claude-Lauf)."""
        ordner = self.tmp / "chat"
        self.assertEqual(self.post("/gespraech/neu", {"ort": "strafe"})[0].status, 404)  # Chat aus
        with mock.patch.object(app, "CHAT", True), mock.patch.object(app, "CHAT_ORDNER", ordner):
            modul = app.chat()
            _, html = self.hole("/reihe/strafe")
            self.assertIn("Noch kein Gespräch hier.", html)
            self.assertIn('href="/gespraeche"><span>Gespräche ohne Ort</span>', html)
            r, _ = self.post("/gespraech/neu", {"ort": "strafe"})
            self.assertEqual(r.status, 303)
            gid = r.getheader("location").rsplit("/", 1)[1]
            self.assertEqual(modul.gespraech(gid, ordner)["ort"], {"ebene": "reihe", "id": "strafe"})
            r, html = self.hole(f"/gespraech/{gid}")
            self.assertEqual(r.status, 200)
            for text in ("Frag einfach los", 'action="/gespraech/' + gid + '/nachricht"', "Daraus Auftrag machen",
                         "Was haben wir bisher?", "Reihenfrage", "Wozu &lt;strafen&gt; wir?", 'class="rahmen"',
                         '<a href="/reihe/strafe">Straftheorien</a>', "gespraech.js"):
                self.assertIn(text, html)
            body, art = multipart({"token": app.logik.formular_token(app.GEHEIM), "text": "Such mir eine Reihenfrage",
                                   "gruendlich": "1"}, [("Planung.JPG", b"jpg"), ("Text.pdf", b"%PDF")])
            r, _ = self.hole(f"/gespraech/{gid}/nachricht", "POST", body=body, kopf={
                "Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})
            self.assertEqual((r.status, r.getheader("location")), (303, f"/gespraech/{gid}#ende"))
            g = modul.gespraech(gid, ordner)
            (e,) = g["eintraege"]
            self.assertEqual((e["text"], e["fotos"], e["dateien"], e["gruendlich"], g["laeuft"]),
                             ("Such mir eine Reihenfrage", ["Planung.jpg"], ["Text.pdf"], True, True))
            _, html = self.hole(f"/gespraech/{gid}")
            self.assertIn("Claude denkt nach", html)
            self.assertIn(f'hx-get="/teile/gespraech/{gid}"', html)
            _, html = self.hole("/")
            self.assertIn("Weiter im Gespräch", html)
            self.assertIn("Claude antwortet …", html)
            r, foto = self.hole(f"/gespraech/{gid}/datei/{e['id']}/Planung.jpg", roh=True)
            self.assertEqual((r.status, r.getheader("Content-Type"), foto), (200, "image/jpeg", b"jpg"))
            self.assertEqual(self.hole(f"/gespraech/{gid}/datei/{e['id']}/..%2F{gid}.json")[0].status, 404)
            # zweite Nachricht, solange Claude antwortet: Satz von lia/chat, kein fremder Text in der URL
            r, _ = self.post(f"/gespraech/{gid}/nachricht", {"text": "Und?"})
            self.assertRegex(r.getheader("location"), rf"^/gespraech/{gid}\?fehler=[0-9a-f]{{8}}#eingabe$")
            self.assertIn("Claude antwortet noch", self.hole(r.getheader("location").split("#")[0])[1])
            self.assertEqual(list((self.tmp / "eingang").iterdir()), [])  # Uploads immer weggeräumt
            # Fehlschlag (wie der Agent ihn schreibt): Satz aus antwort_holen unter Lias Nachricht
            import gespraechablage
            with gespraechablage.sperre(ordner):
                roh = gespraechablage.lesen(gid, ordner)
                roh["eintraege"][0].update(stand="fehler", fehler="limit")
                gespraechablage.schreiben(roh, ordner)
            modul.antwort_schreiben({"id": e["id"], "ok": False, "fehler": "limit",
                                     "text": "Gerade ist das Kontingent aufgebraucht, wieder frei ab 14:30."}, ordner)
            teil = self.hole(f"/teile/gespraech/{gid}")[1]
            self.assertIn("wieder frei ab 14:30.", teil)
            self.assertNotIn("hx-get", teil)
            # Antwort von Claude mit Baustein (wie der Agent sie schreibt)
            with gespraechablage.sperre(ordner):
                roh = gespraechablage.lesen(gid, ordner)
                roh["eintraege"][0].update(stand="fertig", fehler=None)
                roh["eintraege"].append({"id": "a" * 12, "rolle": "claude", "zeit": roh["eintraege"][0]["zeit"],
                                         "text": "| A | B |\n|---|---|\n| 1 | 2 |\n\n```baustein reihenfrage\n"
                                                 "Ist Strafe **gerecht**?\n```", "ok": True})
                gespraechablage.schreiben(roh, ordner)
            _, teil = self.hole(f"/teile/gespraech/{gid}")
            self.assertNotIn("hx-get", teil)
            for text in ("<th>A</th>", "<td>2</td>", 'data-kopie="Ist Strafe gerecht?"', "Als Reihenfrage übernehmen",
                         'name="text" value="Ist Strafe gerecht?"'):
                self.assertIn(text, teil)
            r, _ = self.post("/baustein/reihenfrage", {"reihe": "strafe", "gespraech": gid, "text": "Ist Strafe gerecht?"})
            self.assertEqual(r.status, 303)
            self.assertRegex(r.getheader("location"), rf"^/gespraech/{gid}\?aktion=")
            self.assertEqual(app.struktur.laden(self.instanz).reihe("strafe")["reihenfrage"], "Ist Strafe gerecht?")
            # Listen: an der Reihe, darunter an der Klasse
            self.assertIn("Such mir eine Reihenfrage", self.hole("/reihe/strafe")[1])
            self.assertIn("1 darunter", self.hole("/klasse/ethik-8")[1])
            # Daraus Auftrag machen: Sonderlauf, Ergebnis in Neu
            r, _ = self.post(f"/gespraech/{gid}/sonder", {"art": "auftrag"})
            nid = r.getheader("location").split("sonder=")[1].split("&")[0]
            self.assertIn("ordnet das Gespräch", self.hole(f"/teile/sonder/{gid}/{nid}?art=auftrag")[1])
            modul.antwort_schreiben({"id": nid, "ok": True, "text": "Reihenentwurf: Strafe, entschieden: Kant."}, ordner)
            teil = self.hole(f"/teile/sonder/{gid}/{nid}?art=auftrag")[1]
            self.assertIn(f'href="/neu?aus_gespraech={gid}&amp;ergebnis={nid}&amp;reihe=strafe"', teil)
            _, html = self.hole(f"/neu?art=arbeitsblatt&aus_gespraech={gid}&ergebnis={nid}&reihe=strafe")
            self.assertIn("Reihenentwurf: Strafe, entschieden: Kant.</textarea>", html)
            # Umhängen, ohne Ort, Löschen
            self.assertEqual(self.post(f"/gespraech/{gid}/umhaengen", {"ort": ""})[0].status, 303)
            self.assertIn("Such mir eine Reihenfrage", self.hole("/gespraeche")[1])
            r, _ = self.post(f"/gespraech/{gid}/loeschen", {})
            self.assertEqual(r.getheader("location"), "/gespraeche?erledigt=gespraech-geloescht")
            self.assertIsNone(modul.gespraech(gid, ordner))
            self.assertEqual(self.hole(f"/gespraech/{gid}")[0].status, 404)
            self.assertEqual(self.hole("/gespraech/zzz")[0].status, 404)

    def post(self, pfad, felder, token=True):
        body, art = multipart({**({"token": app.logik.formular_token(app.GEHEIM)} if token else {}), **felder}, [])
        return self.hole(pfad, "POST", body=body,
                         kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})

    def stunden(self, reihe_id="strafe"):
        """Stunden der Reihe aus reihen.toml (dort stehen sie seit Bauschritt 5 nur noch)."""
        return app.struktur.laden(self.instanz).reihe(reihe_id)["stunden"]

    def test_stunden(self):
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261030-160000-unterricht-cccccc.json", {
            "id": "20261030-160000-unterricht-cccccc", "agent": "unterricht", "text": "Arbeitsblatt Vergeltung",
            "status": "erledigt", "reihe": "strafe", "erstellt": "2026-10-30T15:00:00+01:00",
            "abgeschlossen": "2026-10-30T15:10:00+01:00", "ergebnis": "x", "ergebnis_dateien": []})
        _, html = self.hole("/reihe/strafe")
        self.assertIn("Noch keine Stunden.", html)
        self.assertNotIn("Gehört zu", self.hole("/ergebnis/20261030-160000-unterricht-cccccc")[1])
        r, _ = self.post("/reihe/strafe/stunden", {"thema": "  Einstieg  "})
        self.assertEqual(r.status, 303)
        self.assertRegex(r.getheader("location"), r"^/reihe/strafe\?aktion=\d{8}-\d{6}-\d{6}#stunden$")
        self.assertEqual(self.post("/reihe/strafe/stunden", {"thema": "Kant <Vergeltung>"})[0].status, 303)
        r, html = self.hole("/reihe/strafe/stunde/2")
        self.assertEqual(r.status, 200)
        for text in ("Kant &lt;Vergeltung&gt;", "Stunde 2", '<a href="/reihe/strafe">Straftheorien</a>',
                     "Noch kein Material für diese Stunde."):
            self.assertIn(text, html)
        for falsch in ("/reihe/strafe/stunde/3", "/reihe/strafe/stunde/0", "/reihe/strafe/stunde/x",
                       "/reihe/gibts-nicht/stunde/1"):
            self.assertEqual(self.hole(falsch)[0].status, 404, falsch)
        self.assertEqual(self.post("/reihe/strafe/stunden", {"thema": " "})[0].status, 303)  # Thema darf offen bleiben
        self.assertEqual([s["thema"] for s in self.stunden()], ["Einstieg", "Kant <Vergeltung>", ""])
        self.assertIn("Thema offen", self.hole("/reihe/strafe")[1])
        self.assertEqual(self.post("/reihe/strafe/stunden", {"thema": "x"}, token=False)[0].status, 400)
        self.assertEqual(len(self.stunden()), 3)
        einstieg = self.stunden()[0]["id"]
        self.assertEqual(self.post(f"/stunde/{einstieg}/aendern", {"thema": "Einstieg: Gefängnis",
                                                                   "alt_thema": "Einstieg"})[0].status, 303)
        # Material einordnen
        r, html = self.hole("/ergebnis/20261030-160000-unterricht-cccccc")
        self.assertIn('<option value="2">Stunde 2: Kant &lt;Vergeltung&gt;</option>', html)
        r, _ = self.post("/ergebnis/20261030-160000-unterricht-cccccc/stunde", {"nr": "2"})
        self.assertEqual(r.status, 303)
        _, html = self.hole("/ergebnis/20261030-160000-unterricht-cccccc")
        self.assertIn('<option value="2" selected>', html)
        self.assertIn('<a href="/reihe/strafe/stunde/2">Stunde 2</a>', html)
        _, html = self.hole("/reihe/strafe/stunde/2")
        self.assertIn("Arbeitsblatt Vergeltung", html)
        _, html = self.hole("/reihe/strafe")
        self.assertIn("Einstieg: Gefängnis", html)
        self.assertNotIn("Arbeitsblatt Vergeltung", html.split("Zur ganzen Reihe")[1].split("Stunden</h2>")[0])
        self.assertEqual(self.post("/ergebnis/20261030-160000-unterricht-cccccc/stunde", {"nr": "9"})[0].status, 404)
        self.assertEqual(self.post("/ergebnis/20261030-160000-unterricht-cccccc/stunde", {"nr": "0"})[0].status, 303)
        _, html = self.hole("/reihe/strafe")
        self.assertIn("Arbeitsblatt Vergeltung", html.split("Zur ganzen Reihe")[1].split("Stunden</h2>")[0])
        # Material ohne Reihe hat nichts zum Einordnen
        self.assertEqual(self.post("/ergebnis/20261030-140944-unterricht-93e29e/stunde", {"nr": "1"})[0].status, 404)

    def test_reihe_zuordnen(self):
        aid = "20261030-140944-unterricht-93e29e"  # Material ohne Reihe (Chrome-Test Nr. 4)
        _, html = self.hole(f"/ergebnis/{aid}")
        self.assertIn('<option value="" selected>keine Reihe</option>', html)
        self.assertIn('<option value="strafe">Straftheorien (Ethik, Klasse 8)</option>', html)
        self.assertNotIn("Arbeitsblatt &lt;Kant&gt;", self.hole("/reihe/strafe")[1])
        self.assertEqual(self.post(f"/ergebnis/{aid}/reihe", {"reihe": "gibts-nicht"})[0].status, 404)
        self.assertEqual(self.post(f"/ergebnis/{aid}/reihe", {"reihe": "strafe"}, token=False)[0].status, 400)
        r, _ = self.post(f"/ergebnis/{aid}/reihe", {"reihe": "strafe"})
        self.assertEqual((r.status, r.getheader("location")), (303, f"/ergebnis/{aid}?erledigt=zugeordnet"))
        _, html = self.hole(f"/ergebnis/{aid}")
        for text in ('<option value="strafe" selected>', '<a href="/reihe/strafe">Straftheorien</a>',
                     'href="/neu?reihe=strafe">+ Neu hier'):
            self.assertIn(text, html)
        self.assertIn("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", self.hole("/reihe/strafe")[1])
        self.assertIn("Ethik › Klasse 8 › Straftheorien", self.hole("/")[1].split("Arbeitsblatt &lt;Kant&gt;")[1][:400])
        # zurücknehmen
        self.assertEqual(self.post(f"/ergebnis/{aid}/reihe", {"reihe": ""})[0].status, 303)
        self.assertNotIn("Arbeitsblatt &lt;Kant&gt;", self.hole("/reihe/strafe")[1])
        # Aufträge mit eigener Reihe haben keine Auswahl (logik: TestReiheZuordnen)
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261030-160000-unterricht-cccccc.json", {
            "id": "20261030-160000-unterricht-cccccc", "agent": "unterricht", "text": "Arbeitsblatt Vergeltung",
            "reihe": "strafe", "status": "erledigt", "erstellt": "2026-10-30T16:00:00+01:00",
            "abgeschlossen": "2026-10-30T16:05:00+01:00", "ergebnis": "x", "ergebnis_dateien": []})
        self.assertEqual(self.hole("/ergebnis/20261030-160000-unterricht-cccccc")[0].status, 200)
        self.assertNotIn('name="reihe"', self.hole("/ergebnis/20261030-160000-unterricht-cccccc")[1])
        self.assertEqual(self.post("/ergebnis/20261030-160000-unterricht-cccccc/reihe", {"reihe": ""})[0].status, 404)

    def test_vorlagen_und_ich(self):
        (self.tmp / "unterricht" / "profil.toml").write_text('schrift = "Calibri"\nschriftgroesse_pt = 11\n')
        (self.instanz / "regeln.md").write_text("## Regeln\n- 30.10.2026: Immer <Du> (Feedback 20261030-110916-feedback-1c1e7e)\n")
        r, html = self.hole("/vorlagen")
        self.assertEqual(r.status, 200)
        for text in ("Calibri 11 pt", "Arbeitsblatt", "Präsentation", "Tabelle", "Muster", 'href="/vorlagen" aria-current="page"'):
            self.assertIn(text, html)
        r, html = self.hole("/ich")
        self.assertEqual(r.status, 200)
        self.assertIn("Immer &lt;Du&gt;", html)
        self.assertIn("Für alles", html)
        self.assertNotIn("feedback", self.sichtbar(html))
        (self.tmp / "unterricht" / "profil.toml").write_text("kaputt = [")
        with self.assertLogs("webapp", "ERROR"):
            self.assertEqual(self.hole("/vorlagen")[0].status, 200)

    def test_fach_und_stunden_im_baum(self):
        r, html = self.hole("/fach/ethik")
        self.assertEqual(r.status, 200)
        for text in ('<a class="baum-fach" href="/fach/ethik" aria-current="page">Ethik</a>', "Klasse 8",
                     "Läuft: Straftheorien", "1 Reihe · 1 Sache", "Zum ganzen Fach"):
            self.assertIn(text, html)
        self.assertEqual(self.hole("/fach/mathe")[0].status, 404)
        self.post("/reihe/strafe/stunden", {"thema": "Einstieg"})
        self.assertNotIn("Einstieg", self.hole("/")[1])  # Stunden nur unter der gezeigten Reihe
        _, html = self.hole("/reihe/strafe")
        self.assertIn('<a class="baum-eintrag tiefe-2" href="/reihe/strafe/stunde/1"><span>1  Einstieg</span></a>', html)
        _, html = self.hole("/reihe/strafe/stunde/1")
        self.assertIn('href="/reihe/strafe/stunde/1" aria-current="page"><span>1  Einstieg</span>', html)
        self.assertIn('<a class="baum-eintrag tiefe-1" href="/reihe/strafe"><span>', html)  # Reihe nicht markiert

    def test_formatvorlagen(self):
        ordner = self.tmp / "unterricht" / "data" / "vorlagen"

        def hoch(name, inhalt=b"PK-VORLAGE", geltung=""):
            body, art = multipart({"token": app.logik.formular_token(app.GEHEIM), "geltung": geltung}, [(name, inhalt)])
            body = body.replace(b'name="dateien"', b'name="datei"')
            return self.hole("/vorlagen/formatvorlage", "POST", body=body,
                             kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})
        self.assertIn("Noch keine. Ich nehme dann die Gestaltung oben.", self.hole("/vorlagen")[1])
        r, _ = hoch("../Schule Kopf.dotx")
        self.assertEqual((r.status, r.getheader("location")), (303, "/vorlagen?erledigt=formatvorlage#formatvorlagen"))
        self.assertEqual((ordner / "Schule Kopf.dotx").read_bytes(), b"PK-VORLAGE")
        self.assertEqual(hoch("LEK.docx", geltung="lernerfolgskontrolle")[0].status, 303)
        self.assertTrue((ordner / "lernerfolgskontrolle" / "LEK.docx").exists())
        self.assertEqual(hoch("bild.png")[0].status, 400)
        self.assertEqual(hoch("a.docx", geltung="../x")[0].status, 400)
        self.assertEqual(hoch("leer.docx", b"")[0].status, 400)
        _, html = self.hole("/vorlagen?erledigt=formatvorlage")
        for text in ("Schule Kopf.dotx", "Word-Vorlage für Arbeitsblatt und Präsentation", "LEK.docx",
                     "Lernerfolgskontrolle (auch Erwartungshorizont)", ">gilt<", "Gespeichert."):
            self.assertIn(text, html)
        body, art = multipart({"token": app.logik.formular_token(app.GEHEIM), "geltung": "", "name": "../geheim.pdf"}, [])
        r, _ = self.hole("/vorlagen/formatvorlage/entfernen", "POST", body=body,
                         kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})
        self.assertEqual(r.status, 404)
        self.assertTrue((self.tmp / "geheim.pdf").exists())
        self.assertEqual(self.post("/vorlagen/formatvorlage/entfernen", {"geltung": "", "name": "Schule Kopf.dotx"})[0].status, 303)
        self.assertFalse((ordner / "Schule Kopf.dotx").exists())

    def test_ohne_reihen_und_kaputte_datei(self):
        (self.instanz / "reihen.toml").write_text("[[reihe]\n")
        with self.assertLogs("webapp", "ERROR"):
            r, html = self.hole("/")
        self.assertEqual(r.status, 200)
        self.assertNotIn('>Ethik</a>', html)
        self.assertIn('<span class="baum-zahl">', html)
        self.assertEqual(self.hole("/reihe/strafe")[0].status, 404)

    def schicke(self, text="Arbeitsblatt Kant", reihe=""):
        body, art = multipart({"token": app.logik.formular_token(app.GEHEIM), "text": text, "reihe": reihe}, [])
        return self.hole("/neu", "POST", body=body,
                         kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})

    def test_neuer_auftrag_mit_reihe(self):
        _, html = self.hole("/neu?art=arbeitsblatt")
        self.assertIn('<option value="strafe">Straftheorien (Ethik, Klasse 8)</option>', html)
        self.assertEqual(self.schicke(reihe="strafe")[0].status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual((a["reihe"], a["text"]), ("strafe", "Arbeitsblatt Kant\n\nReihe: Straftheorien (Ethik, Klasse 8)"))
        self.assertEqual(a["ort"], "strafe")  # Feld ort (agentkit.struktur): die Reihe
        _, html = self.hole("/reihe/strafe")
        self.assertIn("Arbeitsblatt Kant", html.split("Zur ganzen Reihe</h2>")[1])

    def test_neu_hier_mit_art_und_stunde(self):
        self.assertEqual(self.post("/reihe/strafe/stunden", {"thema": "Kant"})[0].status, 303)
        _, html = self.hole("/reihe/strafe/stunde/1")
        self.assertIn('<a class="knopf knopf-voll" href="/neu?reihe=strafe&amp;stunde=1">+ Neu hier</a>', html)
        self.assertIn('href="/neu?reihe=strafe"', self.hole("/reihe/strafe")[1])
        _, html = self.hole("/neu?reihe=strafe&stunde=1")
        self.assertIn('href="/neu?art=tabelle&amp;reihe=strafe&amp;stunde=1"', html)
        _, html = self.hole("/neu?art=praesentation&reihe=strafe&stunde=1")
        for text in ("für Ethik › Klasse 8 › Straftheorien › Stunde 1", '<input type="hidden" name="reihe" value="strafe">',
                     '<input type="hidden" name="stunde" value="1">', "Beachtet: Ethik › Klasse 8 › Straftheorien › Stunde 1"):
            self.assertIn(text, html)
        self.assertNotIn('<select id="reihe"', html)
        r, _ = self.post("/neu", {"text": "Folien Kant", "art": "praesentation", "reihe": "strafe", "stunde": "1"})
        self.assertEqual((r.status, r.getheader("location")), (303, "/reihe/strafe/stunde/1?erledigt=auftrag-test"))
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual(a["text"], "Präsentation: Folien Kant\n\nReihe: Straftheorien (Ethik, Klasse 8)\nStunde 1: Kant")
        z = app.zustand_().lesen()
        (stunde,) = self.stunden()
        self.assertRegex(stunde["id"], r"^s-[a-z0-9]{6}$")  # Stunde aus reihen.toml mit fester id (agentkit)
        self.assertEqual((a["reihe"], a["ort"], z["stunde_von"]), ("strafe", stunde["id"], {a["id"]: {"stunde": stunde["id"]}}))
        _, html = self.hole("/reihe/strafe/stunde/1?erledigt=auftrag-test")
        self.assertIn("Präsentation: Folien Kant", html)
        self.assertIn("Auftrag angelegt (Testbetrieb", html)
        # unbekannte Stunde fällt weg, unbekannte Art auch
        self.assertEqual(self.post("/neu", {"text": "x", "art": "quatsch", "reihe": "strafe", "stunde": "7"})[0].status, 303)
        b = next(x for x in app.auftraege.neue(basis=self.instanz / "auftraege") if x["id"] != a["id"])
        self.assertEqual((b["text"], b["ort"]), ("x\n\nReihe: Straftheorien (Ethik, Klasse 8)", "strafe"))
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):
            self.assertNotIn("+ Neu hier", self.hole("/reihe/strafe")[1])

    def test_neu_stunde_waehlen(self):  # Chrome-Test Nr. 2
        _, html = self.hole("/neu?art=arbeitsblatt&reihe=strafe")  # Reihe ohne Stunden
        self.assertIn("Gilt für die ganze Reihe. Für eine bestimmte Stunde leg sie zuerst in der", html)
        self.assertNotIn('<select id="stunde"', html)
        _, html = self.hole("/neu?art=arbeitsblatt&reihe=strafe&stunde=1")  # gibt es nicht: sagen, nicht schlucken
        self.assertIn("Stunde 1 gibt es in dieser Reihe noch nicht. Der Auftrag gilt für die ganze Reihe.", html)
        self.assertEqual(self.post("/reihe/strafe/stunden", {"thema": "Kant"})[0].status, 303)
        _, html = self.hole("/neu?art=arbeitsblatt&reihe=strafe")
        for text in ('<select id="stunde" name="stunde">', '<option value="0">zur ganzen Reihe</option>',
                     '<option value="1">Stunde 1: Kant</option>'):
            self.assertIn(text, html)
        r, _ = self.post("/neu", {"text": "Blatt Kant", "art": "arbeitsblatt", "reihe": "strafe", "stunde": "1"})
        self.assertEqual(r.getheader("location"), "/reihe/strafe/stunde/1?erledigt=auftrag-test")
        _, html = self.hole("/neu?art=arbeitsblatt")  # Reihe aus der Auswahl: gilt für die ganze Reihe
        self.assertIn("für eine Stunde nimm „+ Neu hier“ in der Stunde", html)

    def test_stunden_aus_der_datei_regel_23(self):
        """Stunden in reihen.toml (neues Format): Auftrag aus einer Stunde trägt ihre id als ort, das Material folgt
        der Stunde, wenn sie verschoben wird. Testregel 23: Auftrags-JSONs und Fassungen bleiben dabei byte-gleich."""
        kopf = '[[fach]]\nid = "ethik"\nname = "Ethik"\n\n[[klasse]]\nid = "ethik-8"\nfach = "ethik"\nname = "8"\n\n' \
               '[[reihe]]\nid = "strafe"\nklasse = "ethik-8"\ntitel = "Straftheorien"\nstand = "geplant"\n\n'
        einstieg = '[[reihe.stunde]]\nid = "s-einstieg"\nthema = "Einstieg"\n\n'
        kant = '[[reihe.stunde]]\nid = "s-kant"\nthema = "Kant"\n\n'
        (self.instanz / "reihen.toml").write_text(kopf + einstieg + kant, encoding="utf-8")
        schreibe(self.instanz / "fassungen" / "x.json", {"ursprung": "x"})
        _, html = self.hole("/reihe/strafe")
        self.assertIn("Ethik · Klasse 8 · in Planung", html)
        self.assertIn('<span>Straftheorien (in Planung)</span>', html)
        r, _ = self.post("/neu", {"text": "Blatt Kant", "art": "arbeitsblatt", "reihe": "strafe", "stunde": "2"})
        self.assertEqual(r.getheader("location"), "/reihe/strafe/stunde/2?erledigt=auftrag-test")
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual((a["reihe"], a["ort"], a["text"].rsplit("\n", 1)[1]), ("strafe", "s-kant", "Stunde 2: Kant"))
        self.assertEqual(app.zustand_().lesen()["stunde_von"], {a["id"]: {"stunde": "s-kant"}})

        def pruefsummen():
            return {p: hashlib.sha256(p.read_bytes()).hexdigest()
                    for ordner in ("auftraege", "fassungen") for p in sorted((self.instanz / ordner).rglob("*.json"))}
        vorher = pruefsummen()
        (self.instanz / "reihen.toml").write_text(kopf + kant + einstieg, encoding="utf-8")  # Kant nach vorn
        for pfad in ("/", "/reihe/strafe", "/reihe/strafe/stunde/1", "/reihe/strafe/stunde/2", "/klasse/ethik-8",
                     "/fach/ethik"):
            self.assertEqual(self.hole(pfad)[0].status, 200, pfad)
        _, html = self.hole("/reihe/strafe/stunde/1")
        self.assertIn("Blatt Kant", html)
        self.assertNotIn("Blatt Kant", self.hole("/reihe/strafe/stunde/2")[1])
        self.assertEqual(pruefsummen(), vorher)
        self.assertTrue({f"{a['id']}.json", "x.json"} <= {p.name for p in vorher})

    def test_varianten(self):
        original = "20261030-140944-unterricht-93e29e"
        _, html = self.hole(f"/ergebnis/{original}")
        self.assertIn('<span class="variante variante-hier" aria-current="page">normal</span>', html)
        self.assertIn(f'href="/ergebnis/{original}?offen=variante#variante">+ Variante</a>', html)
        _, html = self.hole(f"/ergebnis/{original}?offen=variante")
        self.assertIn('<input type="radio" name="art" value="hilfekarten">', html)
        self.assertEqual(self.post(f"/ergebnis/{original}/variante", {"art": "quatsch"})[0].status, 400)
        r, _ = self.post(f"/ergebnis/{original}/variante", {"art": "hilfekarten", "extra": "Merksatz zweisprachig"})
        self.assertEqual((r.status, r.getheader("location")), (303, f"/ergebnis/{original}?erledigt=variante-test"))
        (v,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertTrue(v["text"].startswith("Variante „mit Hilfekarten“ von „Arbeitsblatt <Kant> & Strafe“: Bau das angehängte"))
        self.assertIn("Dazu: Merksatz zweisprachig", v["text"])
        self.assertTrue((self.tmp / "unterricht" / "data" / "arbeit" / "x" / "Arbeitsblatt.docx").exists())  # Kopie
        _, html = self.hole(f"/ergebnis/{original}")
        self.assertIn('<span class="variante">mit Hilfekarten <span class="unter">Läuft</span></span>', html)
        self.assertNotIn(v["id"], self.hole("/")[1].split("Läuft gerade")[0])  # läuft, steht unter Läuft gerade
        app.auftraege.abschliessen(v["id"], "Fertig.", basis=self.instanz / "auftraege")
        _, html = self.hole(f"/ergebnis/{original}")
        self.assertIn(f'<a class="variante" href="/ergebnis/{v["id"]}">mit Hilfekarten', html)
        _, html = self.hole(f"/ergebnis/{v['id']}")
        for text in (f'<a class="variante" href="/ergebnis/{original}">normal</a>',
                     '<span class="variante variante-hier" aria-current="page">mit Hilfekarten</span>',
                     f'<a href="/ergebnis/{original}">Original</a>'):
            self.assertIn(text, html)
        self.assertNotIn("+ Variante", html)
        self.assertEqual(self.post(f"/ergebnis/{v['id']}/variante", {"art": "einfach"})[0].status, 404)
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):
            self.assertNotIn("+ Variante", self.hole(f"/ergebnis/{original}")[1])
            self.assertEqual(self.post(f"/ergebnis/{original}/variante", {"art": "einfach"})[0].status, 404)

    def test_nochmal(self):
        alt = "20261022-232618-unterricht-67ba47"
        _, html = self.hole(f"/ergebnis/{alt}")
        self.assertIn("Nochmal</button>", html)
        self.assertIn("formatvorlage anwenden", self.hole("/")[1].split("Hat nicht geklappt")[1].lower())
        r, _ = self.post(f"/ergebnis/{alt}/nochmal", {})
        self.assertEqual((r.status, r.getheader("location")), (303, f"/ergebnis/{alt}?erledigt=nochmal-test"))
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual((a["text"], a.get("bezug")), ("formatvorlage anwenden", None))
        self.assertEqual(app.zustand_().lesen()["ersetzt"], {alt: a["id"]})
        _, html = self.hole("/")
        self.assertNotIn("Hat nicht geklappt", html)
        self.assertIn("Formatvorlage anwenden", html.split("Läuft gerade")[1])
        self.assertEqual(self.post(f"/ergebnis/{alt}/nochmal", {})[0].status, 404)  # nicht doppelt
        self.assertEqual(self.post("/ergebnis/20261030-140944-unterricht-93e29e/nochmal", {})[0].status, 404)

    def test_nochmal_doppelklick(self):
        alt = "20261022-232618-unterricht-67ba47"
        _, html = self.hole(f"/ergebnis/{alt}")
        form = re.search(r'<form [^>]*/nochmal"[^>]*>.*?</form>', html, re.S).group(0)
        self.assertIn("data-einmal", form)
        self.assertRegex(form, r'name="einmal" value="[0-9a-f]{16}"')
        self.assertIn("einmal.js", html)
        erste, zweite = (self.post(f"/ergebnis/{alt}/nochmal", {"einmal": "kennung-1"})[0] for _ in range(2))
        self.assertEqual((erste.status, zweite.status), (303, 303))
        self.assertEqual(zweite.getheader("location"), erste.getheader("location"))
        self.assertEqual(len(app.auftraege.neue(basis=self.instanz / "auftraege")), 1)
        # Eine alte Seite ohne diese Kennung bleibt abgewiesen
        self.assertEqual(self.post(f"/ergebnis/{alt}/nochmal", {"einmal": "kennung-2"})[0].status, 404)

    def test_nochmal_mit_datei_zeigt_weg(self):
        alt = "20261022-232618-unterricht-67ba47"
        pfad = self.instanz / "auftraege" / "erledigt" / f"{alt}.json"
        d = json.loads(pfad.read_text())
        pfad.write_text(json.dumps({**d, "dateien": ["data/eingang/x/AB4_einfach.pdf"]}))
        _, html = self.hole(f"/ergebnis/{alt}")
        self.assertNotIn("Nochmal</button>", html)
        self.assertIn("mit der Datei bitte über „Neu“ noch einmal. <a href=\"/neu\">Zu „Neu“</a>", html)
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):
            self.assertNotIn("Zu „Neu“", self.hole(f"/ergebnis/{alt}")[1])

    def test_theater_vorlagen(self):
        wahnsinn = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"
        _, html = self.hole(f"/neu?reihe={wahnsinn}")
        self.assertIn("Spielfassung (Kürzung)", html)
        self.assertNotIn("Spielfassung", self.hole("/neu?reihe=strafe")[1])  # nur Darstellendes Spiel
        _, html = self.hole(f"/neu?art=spielfassung&reihe={wahnsinn}")
        for text in ('name="laenge"', 'name="bleiben"', "Dauert bis zu drei Stunden"):
            self.assertIn(text, html)
        r, _ = self.post("/neu", {"art": "spielfassung", "reihe": wahnsinn, "text": "Der nackte Wahnsinn",
                                  "laenge": "35–40 Minuten", "spieler": "18", "bleiben": "Akt 1\r\nTreppe"})
        self.assertEqual(r.status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual((a["agent"], a["quelle"], a["reihe"]), ("theater", "portal-theater", wahnsinn))
        self.assertEqual(a["text"], "Spielfassung: Der nackte Wahnsinn\nLänge: 35–40 Minuten\nSpieler*innen: 18\n"
                                    "Was bleiben muss: Akt 1\nTreppe\n\nReihe: Der nackte Wahnsinn (Darstellendes Spiel, Kurs 12)")

    def test_zurueckziehen(self):
        self.assertEqual(self.post("/neu", {"text": "Blatt", "art": "arbeitsblatt"})[0].status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        _, html = self.hole("/")
        self.assertIn(f'action="/auftrag/{a["id"]}/zurueckziehen"', html)
        self.assertNotIn(a["id"], self.sichtbar(html))
        # Befund 03.11. Punkt 7: Der erste Klick öffnet nur die Rückfrage, abschicken kann erst „Ja, zurückziehen“
        self.assertRegex(html, r'(?s)<details class="nachfrage">\s*<summary[^>]*>Zurückziehen</summary>\s*<form [^>]*/zurueckziehen"')
        self.assertIn("Wirklich zurückziehen?", html)
        self.assertIn(">Ja, zurückziehen</button>", html)
        self.assertNotIn(">Zurückziehen</button>", html)
        self.assertIn('<script src="/statisch/einmal.js" defer></script>', html)
        r, _ = self.post(f"/auftrag/{a['id']}/zurueckziehen", {})
        self.assertEqual((r.status, r.getheader("location")), (303, "/?erledigt=zurueckgezogen"))
        self.assertEqual(app.auftraege.neue(basis=self.instanz / "auftraege"), [])
        _, html = self.hole("/?erledigt=zurueckgezogen")
        self.assertIn("Zurückgezogen.", html)
        self.assertNotIn("Blatt", html)
        self.assertEqual(self.post(f"/auftrag/{a['id']}/zurueckziehen", {})[0].status, 404)  # nicht mehr offen
        self.assertEqual(self.post("/auftrag/../x/zurueckziehen", {})[0].status, 404)

    def test_auch_als_im_formular(self):
        self.assertIn('name="varianten" value="hilfekarten"', self.hole("/neu?art=arbeitsblatt")[1])
        self.assertNotIn('name="varianten"', self.hole("/neu?art=tabelle")[1])
        r, _ = self.post("/neu", {"text": "Blatt", "art": "arbeitsblatt", "varianten": ["hilfekarten", "tuerkisch", "einfach"]})
        self.assertEqual(r.status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual(a["text"], "Arbeitsblatt: Blatt\nAuch als: einfach, mit Hilfekarten")  # baut der Agent mit

    def test_neuer_auftrag_ohne_und_mit_falscher_reihe(self):
        self.assertEqual(self.schicke()[0].status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertNotIn("reihe", a)
        r, html = self.schicke(reihe="gibt-es-nicht")
        self.assertEqual(r.status, 400)
        self.assertIn("Diese Reihe gibt es nicht (mehr).", html)
        self.assertEqual(len(app.auftraege.neue(basis=self.instanz / "auftraege")), 1)


class TestSchrift(Aufbau):
    def test_pruefsummen(self):
        ordner = Path(app.__file__).parent / "statisch" / "schrift"
        for zeile in (ordner / "schrift.sha256").read_text().splitlines():
            summe, name = zeile.split()
            self.assertEqual(hashlib.sha256((ordner / name).read_bytes()).hexdigest(), summe, name)
        self.assertIn("Open Font License", (ordner / "LIZENZ-OFL.txt").read_text())

    def test_auslieferung(self):
        _, css = self.hole("/statisch/ruhig.css")
        self.assertIn('url("schrift/inter.woff2")', css)
        self.assertNotIn("http", css)  # nur dieser Server
        for name in ("inter.woff2", "inter-tight.woff2"):
            r, _ = self.hole("/statisch/schrift/" + name, roh=True)
            self.assertEqual((r.status, r.getheader("Content-Type")), (200, "font/woff2"))
            # Sonst lädt sie bei jedem Seitenwechsel neu und der Text springt
            self.assertIn("max-age", r.getheader("Cache-Control"))


class TestHtmx(unittest.TestCase):
    def test_pruefsumme(self):
        import hashlib
        ordner = Path(app.__file__).parent / "statisch"
        erwartet = (ordner / "htmx-2.0.4.min.js.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256((ordner / "htmx-2.0.4.min.js").read_bytes()).hexdigest(), erwartet)


if __name__ == "__main__":
    unittest.main()


class TestMaterial(Aufbau):
    """Aktionen der Material-Ansicht: final, eigene Fassung, Rückmeldung."""

    URL = "/ergebnis/20261030-140944-unterricht-93e29e"
    F1 = "20261030-140944-unterricht-93e29e"

    def sende(self, pfad, felder, dateien=(), feld="datei", token=None, origin="http://localhost"):
        felder = {"token": token or app.logik.formular_token(app.GEHEIM), **felder}
        body, art = multipart(felder, list(dateien))
        body = body.replace(b'name="dateien"', f'name="{feld}"'.encode())
        kopf = {"Content-Type": art, "Content-Length": str(len(body))}
        if origin:
            kopf |= {"Origin": origin, "Host": "localhost", "Sec-Fetch-Site": "same-origin"}
        return self.hole(self.URL + pfad, "POST", body=body, kopf=kopf)

    def neue(self):
        ordner = self.instanz / "auftraege" / "neu"
        return [json.loads(p.read_text()) for p in sorted(ordner.glob("*.json"))] if ordner.exists() else []

    def test_final_an_und_aus(self):
        r, _ = self.sende("/final", {"ref": self.F1, "an": "1"})
        self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=final"))
        _, html = self.hole(self.URL + "?erledigt=final")
        for text in ("Final. Fassung 1 ist jetzt die, die du nimmst.", ">Final · rückgängig<",
                     '<span class="material-marke marke-final">Final</span>'):
            self.assertIn(text, html)
        _, heute = self.hole("/")
        self.assertIn('<span class="baum-zahl">1</span>', heute)  # final wartet nicht mehr, nur der Entwurf
        self.assertIn(">Final<", heute)
        self.assertEqual(self.sende("/final", {"ref": self.F1, "an": "0"})[0].status, 303)
        self.assertNotIn("Final · rückgängig", self.hole(self.URL)[1])
        self.assertEqual(self.neue(), [])  # nichts in Lias Instanz

    def test_final_nur_gueltig_und_geschuetzt(self):
        self.assertEqual(self.sende("/final", {"ref": NB, "an": "1"})[0].status, 404)  # Antwort ohne Dateien
        self.assertEqual(self.sende("/final", {"ref": "../x", "an": "1"})[0].status, 404)
        self.assertEqual(self.sende("/final", {"ref": self.F1, "an": "1"}, origin=None)[0].status, 403)
        r, html = self.sende("/final", {"ref": self.F1, "an": "1"}, token="falsch")
        self.assertEqual(r.status, 400)
        self.assertIn("Die Seite war veraltet", html)
        self.assertNotIn("Final · rückgängig", self.hole(self.URL)[1])
        # Aktionen nur an der Ansicht selbst, nicht über die ID einer Nachbesserung
        self.URL = f"/ergebnis/{NB}"
        self.assertEqual(self.sende("/final", {"ref": self.F1, "an": "1"})[0].status, 404)

    def test_eigene_fassung(self):
        _, html = self.hole(self.URL + "?offen=eigene")
        self.assertIn("Als neue Fassung hochladen", html)
        r, _ = self.sende("/eigene", {}, [("../Mein Blatt.docx", b"MEINS")])
        self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=eigene"))
        _, html = self.hole(self.URL + "?erledigt=eigene")
        for text in ("Deine Datei ist jetzt die neueste Fassung.", "Fassung 2", "von dir, heute",
                     f'href="{self.URL}/eigene/1" download>Word<'):
            self.assertIn(text, html)
        self.assertLess(html.index("von dir, heute"), html.index("von mir, heute 14:40"))
        r, inhalt = self.hole(self.URL + "/eigene/1", roh=True)
        self.assertEqual((r.status, inhalt), (200, b"MEINS"))
        self.assertIn("Mein%20Blatt.docx", r.getheader("Content-Disposition"))
        for falsch in ("/eigene/0", "/eigene/2"):
            self.assertEqual(self.hole(self.URL + falsch)[0].status, 404)
        # eigene Fassung kann final werden
        self.assertEqual(self.sende("/final", {"ref": "eigene-1", "an": "1"})[0].status, 303)
        self.assertIn("marke-final", self.hole(self.URL)[1])
        self.assertEqual(self.neue(), [])
        self.assertFalse((self.instanz / "eigene").exists())

    def erstes_final_formular(self, html):
        """(ref, Knopftext) des ersten Final-Formulars der Seite, das ist der große Knopf oben."""
        return re.search(r'action="[^"]*/final">.*?name="ref" value="([^"]+)".*?<button[^>]*>([^<]+)<', html, re.S).groups()

    def test_oberer_final_knopf_gilt_der_neuesten_fassung(self):
        """Befund 03.11. Punkt 3: Nach einer eigenen Fassung markierte der große Knopf weiter die alte als final."""
        self.assertEqual(self.erstes_final_formular(self.hole(self.URL)[1]), (self.F1, "Als final markieren"))
        datei = self.tmp / "Mein Blatt.docx"
        datei.write_bytes(b"MEINS")
        app.fassungen.eigene_dazu(self.F1, datei, basis=self.instanz / "auftraege", agenten_dir=self.tmp)
        _, html = self.hole(self.URL)
        self.assertEqual(self.erstes_final_formular(html), ("eigene-1", "Fassung 2 als final markieren"))
        self.assertIn("Oben steht noch: Fassung 1. Deine Datei ist Fassung 2", html)
        # Fassung 1 behält ihren kleinen Knopf, Fassung 2 hat den großen
        self.assertEqual(html.count('name="ref" value="eigene-1"'), 1)
        self.assertEqual(html.count(f'name="ref" value="{self.F1}"'), 1)
        self.assertEqual(self.sende("/final", {"ref": "eigene-1", "an": "1"})[0].status, 303)
        _, html = self.hole(self.URL + "?erledigt=final")
        self.assertIn("Final. Fassung 2 ist jetzt die, die du nimmst.", html)
        self.assertEqual(self.erstes_final_formular(html), ("eigene-1", "Final · rückgängig"))

    def test_eigene_fassung_doppelklick_eine_fassung(self):
        def eigene():
            return app.fassungen.lesen(self.F1, basis=self.instanz / "auftraege")["eigene"]
        with mock.patch("agentkit._ablage.jetzt", lambda: "2026-10-30T18:00:00+01:00"):
            for _ in range(2):
                r, _ = self.sende("/eigene", {}, [("Blatt.docx", b"MEINS")])
                self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=eigene"))
            self.assertEqual([e["n"] for e in eigene()], [1])
            # Gleicher Name, anderer Inhalt: Lia hat die Datei geändert, das ist eine neue Fassung
            self.assertEqual(self.sende("/eigene", {}, [("Blatt.docx", b"GEAENDERT")])[0].status, 303)
            self.assertEqual([e["n"] for e in eigene()], [1, 2])
            self.assertEqual(self.sende("/eigene", {}, [("Anders.docx", b"GEAENDERT")])[0].status, 303)
            self.assertEqual([e["n"] for e in eigene()], [1, 2, 3])
        _, html = self.hole(self.URL + "?offen=eigene")
        self.assertIn("einmal.js", html)
        self.assertRegex(html, r'<form [^>]*/eigene"[^>]* data-einmal[ >]')

    def test_eigene_fassung_falsche_datei(self):
        r, html = self.sende("/eigene", {}, [("bild.exe", b"x")])
        self.assertEqual(r.status, 400)
        self.assertIn("Diese Datei geht nicht", html)
        r, html = self.sende("/eigene", {})
        self.assertEqual(r.status, 400)
        self.assertIn("Wähle eine Datei aus.", html)

    # Die Rückmeldungs-Tests hier prüfen den gründlichen Weg über den Feedback-Dienst (mit Datei, andere Agenten);
    # ohne Datei ginge es an lia/schnell, darum dort app.schnell -> None. Den schnellen Weg prüft test_schnell.py.
    def test_rueckmeldung_je_datei(self):
        ursprung = "20261030-140944-unterricht-93e29e"
        with mock.patch.object(app, "NEUER_AUFTRAG", "test"), mock.patch.object(app, "agent_starten"), \
                mock.patch.object(app, "schnell", lambda: None):
            _, html = self.hole(self.URL)
            link = f"{self.URL}?offen=rueckmeldung&amp;fassung={ursprung}&amp;datei=0#rueckmeldung"
            self.assertIn(f'<a class="knopf" href="{link}">Rückmeldung</a>', html)
            _, html = self.hole(f"/ergebnis/{ursprung}/datei/0/ansehen?seite=2")
            self.assertIn(f"{self.URL}?offen=rueckmeldung&amp;fassung={ursprung}&amp;datei=0&amp;seite=2#rueckmeldung", html)
            _, html = self.hole(f"{self.URL}?offen=rueckmeldung&fassung={ursprung}&datei=0&seite=2")
            for text in ("Zu „Arbeitsblatt.docx“, Seite 2", '<input type="hidden" name="dnr" value="0">',
                         "Stattdessen zum Ganzen"):
                self.assertIn(text, html)
            _, html = self.hole(f"{self.URL}?offen=rueckmeldung&fassung={ursprung}&datei=7")  # unbekannt: das Ganze
            self.assertNotIn('name="dnr"', html)
            r, _ = self.sende("/rueckmeldung", {"text": "Aufgabe 2 kürzer", "fassung": ursprung, "dnr": "0", "seite": "2"})
            self.assertEqual(r.status, 303)
        (a,) = self.neue()
        # gilt der Fassung, aus der die Datei stammt (nicht der neuesten Antwort)
        self.assertEqual((a["bezug"], a["text"]), (ursprung, "Zur Datei „Arbeitsblatt.docx“, Seite 2: Aufgabe 2 kürzer"))
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):
            self.assertNotIn(">Rückmeldung</a>", self.hole(self.URL)[1])
            self.assertNotIn("Rückmeldung zu dieser Seite", self.hole(f"/ergebnis/{ursprung}/datei/0/ansehen")[1])

    def test_rueckmeldung_aus_ohne_einstellung(self):
        _, html = self.hole(self.URL + "?offen=rueckmeldung")
        self.assertIn("Rückmeldungen gehen im Moment noch über Telegram", html)
        self.assertNotIn('id="rueck-text"', html)
        self.assertEqual(self.sende("/rueckmeldung", {"text": "kürzer"})[0].status, 404)
        self.assertEqual(self.neue(), [])

    def test_rueckmeldung_doppelklick_ein_auftrag(self):
        """Befund 03.11. Punkt 1: Ein Doppelklick schickt denselben POST zweimal, die zweite Antwort sieht Lia."""
        with mock.patch.object(app, "NEUER_AUFTRAG", "echt"), mock.patch.object(app, "agent_starten") as start, \
                mock.patch("agentkit._ablage.jetzt", lambda: "2026-10-30T18:00:00+01:00"), \
                mock.patch.object(app, "schnell", lambda: None):
            for _ in range(2):
                r, _ = self.sende("/rueckmeldung", {"text": "Bitte kürzer"}, [("Kommentare.docx", b"KOMM")])
                self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=rueckmeldung"))
            start.assert_called_once_with("feedback")
            self.assertEqual(len(self.neue()), 1)
            stand = app.fassungen.lesen(self.F1, basis=self.instanz / "auftraege")
            self.assertEqual(len(stand["eigene"]), 1)  # auch die Datei nur einmal
            # Anderer Text ist eine neue Rückmeldung
            self.assertEqual(self.sende("/rueckmeldung", {"text": "Und größer"})[0].status, 303)
            self.assertEqual(len(self.neue()), 2)

    def test_rueckmeldung_gleichzeitig_ein_auftrag(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", "test"), mock.patch.object(app, "schnell", lambda: None), \
                mock.patch("agentkit._ablage.jetzt", lambda: "2026-10-30T18:00:00+01:00"):
            antworten = []
            faeden = [threading.Thread(target=lambda: antworten.append(self.sende("/rueckmeldung", {"text": "Kürzer"})[0]))
                      for _ in range(2)]
            for f in faeden:
                f.start()
            for f in faeden:
                f.join()
        self.assertEqual([r.status for r in antworten], [303, 303])
        self.assertEqual(len(self.neue()), 1)

    def test_variante_doppelklick_ein_auftrag(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", "echt"), mock.patch.object(app, "agent_starten") as start, \
                mock.patch("agentkit._ablage.jetzt", lambda: "2026-10-30T18:00:00+01:00"):
            for _ in range(2):
                r, _ = self.sende("/variante", {"art": "einfach"})
                self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=variante"))
            start.assert_called_once_with("unterricht")
            self.assertEqual(len(self.neue()), 1)
            self.assertEqual(len(app.zustand_().lesen()["varianten"][self.F1]), 1)
            # Andere Art ist eine neue Variante
            self.assertEqual(self.sende("/variante", {"art": "hilfekarten"})[0].status, 303)
            self.assertEqual(len(self.neue()), 2)
            _, html = self.hole(self.URL + "?offen=variante")
            self.assertIn("einmal.js", html)
            self.assertRegex(html, r'<form [^>]*/variante"[^>]* data-einmal[ >]')

    def test_rueckmeldung_knopf_sperrt_sich(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", "test"):
            _, html = self.hole(self.URL + "?offen=rueckmeldung")
            self.assertIn('<script src="/statisch/einmal.js" defer></script>', html)
            self.assertRegex(html, r'<form [^>]*/rueckmeldung"[^>]* data-einmal[ >]')
        r, js = self.hole("/statisch/einmal.js")
        self.assertEqual(r.status, 200)
        self.assertIn("data-einmal", js)

    def test_eine_stimme(self):
        """Sprachregel: Lia liest „ich“, nie Agent oder Assistent. „Deine Assistenz“ bleibt nur als Name oben links."""
        with mock.patch.object(app, "NEUER_AUFTRAG", "test"):
            for pfad in (self.URL, self.URL + "?offen=rueckmeldung", self.URL + "?offen=eigene", "/", "/neu",
                         "/neu?art=arbeitsblatt", "/neu?art=spielfassung", "/vorlagen", "/ich"):
                _, html = self.hole(pfad)
                for wort in ("Agent", "Assistent", "Test-Instanz"):
                    self.assertNotIn(wort, self.sichtbar(html), pfad)
                self.assertEqual(self.sichtbar(html).count("Assistenz"), 1, pfad)

    def test_rote_marken(self):
        _, html = self.hole("/")
        self.assertRegex(html, r'<span class="punkt punkt-rot"[^>]*></span>')
        self.assertIn('<span class="marke marke-rot">Neu</span>', html)

    def test_ein_hauptknopf(self):
        """Befund 03.11., Teil D: Auf der Material-Ansicht ist „Rückmeldung geben“ der eine schwarze Knopf."""
        _, html = self.hole(self.URL)
        self.assertEqual(re.findall(r'<a class="[^"]*knopf-voll[^"]*"[^>]*>([^<]+)<', html), ["Rückmeldung geben"])

    def test_rueckmeldung_nur_mit_datei(self):
        """Befund 03.11. Punkt 2: Eine Datei allein reicht, der Browser verlangt keinen Text mehr."""
        with mock.patch.object(app, "NEUER_AUFTRAG", "test"):
            _, html = self.hole(self.URL + "?offen=rueckmeldung")
            self.assertNotRegex(html, r'<textarea id="rueck-text"[^>]* required')
            r, _ = self.sende("/rueckmeldung", {"text": ""}, [("Korrigiert.docx", b"KOMM")])
            self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=rueckmeldung-test"))
        (a,) = self.neue()
        self.assertEqual(a["text"], f"{app.logik.RUECK_NUR_DATEI}\n\nDazu eine Datei: Korrigiert.docx.")

    def test_datei_wege_erklaert(self):
        """Befund 03.11. Punkt 2: Unter den zwei Knöpfen steht je ein Satz, was danach passiert."""
        _, html = self.hole(self.URL)
        for satz in ("Ich ändere es für dich.", "Deine Datei gilt, ich ändere nichts."):
            self.assertIn(satz, html)

    def test_rueckmeldung_im_testbetrieb(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", "test"), mock.patch.object(app, "agent_starten") as start:
            _, html = self.hole(self.URL + "?offen=rueckmeldung")
            for text in ("Was soll anders werden?", "Datei anhängen", "Neue Fassung anfordern",
                         "Testbetrieb", "Bitte keine Namen"):
                self.assertIn(text, html)
            r, html = self.sende("/rueckmeldung", {"text": " "})
            self.assertEqual(r.status, 400)
            self.assertIn("Schreib kurz, was anders werden soll, oder häng eine Datei an.", html)
            r, _ = self.sende("/rueckmeldung", {"text": "Bitte kürzer"}, [("Kommentare.docx", b"KOMM")])
            self.assertEqual((r.status, r.getheader("Location")), (303, self.URL + "?erledigt=rueckmeldung-test"))
            start.assert_not_called()
        (a,) = self.neue()
        # gilt der neuesten fertigen Fassung (wie in Telegram), die Datei ist nicht lesbar, also „unklar“
        self.assertEqual((a["agent"], a["quelle"], a["bezug"]), ("feedback", "feedback", NB))
        self.assertEqual(a["text"], "Bitte kürzer\n\nDazu eine Datei: Kommentare.docx.")
        # agentkit.fassungen: Eintrag in der Instanz, Datei im Agent-Ordner (die Agenten sehen sie)
        stand = app.fassungen.lesen("20261030-140944-unterricht-93e29e", basis=self.instanz / "auftraege")
        self.assertEqual([e["name"] for e in stand["eigene"]], ["Kommentare.docx"])
        self.assertTrue((self.tmp / "unterricht" / stand["eigene"][0]["datei"]).is_file())
        r, inhalt = self.hole(self.URL + "/eigene/1", roh=True)
        self.assertEqual(inhalt, b"KOMM")
        _, html = self.hole(self.URL)
        self.assertIn("Deine Datei", html)
        self.assertNotIn("mit deinen Kommentaren", html)
        self.assertEqual(stand["eigene"][0]["art"], "unklar")
