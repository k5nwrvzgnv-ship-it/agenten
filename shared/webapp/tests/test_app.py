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


class Aufbau(unittest.TestCase):
    """Echter Uvicorn auf einem Socket im Temp-Ordner, Instanz mit Beispielaufträgen."""

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

    def hole(self, pfad, methode="GET", roh=False, body=None, kopf=None):
        v = UnixVerbindung(str(self.sock))
        v.request(methode, pfad, body=body, headers=kopf or {})
        r = v.getresponse()
        inhalt = r.read()
        v.close()
        return r, inhalt if roh else inhalt.decode("utf-8")

    def sichtbar(self, html):
        """HTML ohne Links: IDs dürfen nur in href stehen."""
        return re.sub(r'(href|src)="[^"]*"', "", html)


class TestApp(Aufbau):

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


def multipart(felder: dict, dateien: list[tuple[str, bytes]]) -> tuple[bytes, str]:
    grenze = "----grenze7MA4YWxk"
    teile = [f'--{grenze}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{w}\r\n'.encode()
             for n, w in felder.items()]
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

    def test_aus_ohne_einstellung_und_nie_test_auf_lias_instanz(self):
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):
            self.assertEqual(self.hole("/neu")[0].status, 404)
            self.assertEqual(self.schicke()[0].status, 404)
            self.assertNotIn('href="/neu"', self.hole("/")[1])
        with mock.patch.object(app, "INSTANZ", app.ECHTE_INSTANZ):
            self.assertEqual(app.neu_modus(), "")  # nur prüfen, nichts abschicken
        self.assertEqual(self.neue(), [])

    def test_formular_und_einstieg_in_heute(self):
        r, html = self.hole("/neu")
        self.assertEqual(r.status, 200)
        for text in ("Neuer Auftrag", "Testbetrieb", 'enctype="multipart/form-data"', 'name="token"',
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
[[reihe]]
id = "strafe"
fach = "Ethik"
klasse = "8"
titel = "Straftheorien"
reihenfrage = "Wozu <strafen> wir?"
behandelt = ["Kant", "Bentham"]
agenten = ["examen"]

[[reihe]]
fach = "Theater"
klasse = "Kurs 11"
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

    def test_heute_mit_chips_und_filter(self):
        _, html = self.hole("/")
        for text in ('href="/?ordnung=fach%3Aethik"', ">Theater</a>", ">Ohne Reihe</a>", 'href="/unterricht"',
                     "Ethik · Klasse 8 · Straftheorien"):
            self.assertIn(text, html)
        self.assertIn('aria-current="true">Alle</a>', html)
        _, html = self.hole("/?ordnung=fach%3Atheater")
        self.assertIn('aria-current="true">Theater</a>', html)
        self.assertNotIn("Umfrage vor der Reihe", html)  # Entwurf aus examen gehört zu Ethik
        self.assertIn('hx-get="/teile/heute?ordnung=fach%3Atheater"', html)
        self.assertNotIn("Gerade wartet nichts", html)  # Begrüßung zählt trotzdem alles
        _, html = self.hole("/teile/heute?ordnung=fach%3Aethik")
        self.assertIn("Umfrage vor der Reihe", html)
        self.assertNotIn("Arbeitsblatt &lt;Kant&gt;", html)  # Material ohne Reihe
        _, html = self.hole("/?ordnung=ohne")
        self.assertIn("Arbeitsblatt &lt;Kant&gt;", html)
        self.assertNotIn("Umfrage vor der Reihe", html)
        _, html = self.hole("/?ordnung=%3Cboese%3E")  # unbekannter Filter: alles
        self.assertIn("Umfrage vor der Reihe", html)
        self.assertNotIn("boese", html)

    def test_unterricht(self):
        r, html = self.hole("/unterricht")
        self.assertEqual(r.status, 200)
        for text in ("Ethik", "Straftheorien", "Klasse 8", "Wozu &lt;strafen&gt; wir?", "Kant; Bentham", "Theater",
                     "Kurs 11", "Noch keine Aufträge zu dieser Reihe.", "Ohne Reihe",
                     'href="/ergebnis/20261030-140944-unterricht-93e29e"', "Umfrage vor der Reihe"):
            self.assertIn(text, html)
        self.assertNotIn("20261030", self.sichtbar(html))

    def test_unterricht_ohne_reihen_und_kaputte_datei(self):
        (self.instanz / "reihen.toml").write_text("[[reihe]\n")
        with self.assertLogs("webapp", "ERROR"):
            _, html = self.hole("/unterricht")
        self.assertIn("Noch keine Reihen eingetragen.", html)
        _, html = self.hole("/")
        self.assertNotIn("Ohne Reihe", html)  # ohne Reihen keine Chips

    def schicke(self, text="Arbeitsblatt Kant", reihe=""):
        body, art = multipart({"token": app.logik.formular_token(app.GEHEIM), "text": text, "reihe": reihe}, [])
        return self.hole("/neu", "POST", body=body,
                         kopf={"Content-Type": art, "Content-Length": str(len(body)), "Origin": "http://localhost"})

    def test_neuer_auftrag_mit_reihe(self):
        _, html = self.hole("/neu")
        self.assertIn('<option value="strafe">Straftheorien (Ethik, Klasse 8)</option>', html)
        self.assertEqual(self.schicke(reihe="strafe")[0].status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertEqual((a["reihe"], a["text"]), ("strafe", "Arbeitsblatt Kant\n\nReihe: Straftheorien (Ethik, Klasse 8)"))
        _, html = self.hole("/?ordnung=reihe%3Astrafe")
        self.assertIn("Arbeitsblatt Kant", html.split("Läuft gerade</h2>")[1])

    def test_neuer_auftrag_ohne_und_mit_falscher_reihe(self):
        self.assertEqual(self.schicke()[0].status, 303)
        (a,) = app.auftraege.neue(basis=self.instanz / "auftraege")
        self.assertNotIn("reihe", a)
        r, html = self.schicke(reihe="gibt-es-nicht")
        self.assertEqual(r.status, 400)
        self.assertIn("Diese Reihe gibt es nicht (mehr).", html)
        self.assertEqual(len(app.auftraege.neue(basis=self.instanz / "auftraege")), 1)


class TestHtmx(unittest.TestCase):
    def test_pruefsumme(self):
        import hashlib
        ordner = Path(app.__file__).parent / "statisch"
        erwartet = (ordner / "htmx-2.0.4.min.js.sha256").read_text().split()[0]
        self.assertEqual(hashlib.sha256((ordner / "htmx-2.0.4.min.js").read_bytes()).hexdigest(), erwartet)


if __name__ == "__main__":
    unittest.main()
