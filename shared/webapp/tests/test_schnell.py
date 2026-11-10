"""Schneller Weg über lia/schnell in beiden Oberflächen: Rückmeldung ohne Datei geht von selbst an lia/schnell
(kein Schalter, Jan 10.11.2026), „Anderes Dokument“ unter Neu, Anzeige „Wird geändert …“ und die schnell geänderte
Fassung oben. TestSchnell prüft vorlagen/, TestSchnellNeu dieselben Abläufe in oberflaeche/."""

import json
import shutil
import unittest
from pathlib import Path
from unittest import mock

import app
from tests import test_app as basis
from tests.test_alt import AltAufbau

HIER = Path(__file__).resolve().parent.parent


SCHNITTSTELLE = HIER.parent.parent / "lia" / "schnell" / "schnittstelle.py"
KOPF = "20261030-140944-unterricht-93e29e"


@unittest.skipUnless(SCHNITTSTELLE.exists(), "lia/schnell noch nicht da")
class TestSchnell(AltAufbau):
    """Schneller Weg über lia/schnell (Testbetrieb: Wünsche in DATEN/schnell-test, kein Agent antwortet; die
    Antworten schreibt der Test über die Schnittstelle selbst)."""

    def setUp(self):
        super().setUp()
        patch = mock.patch.dict(app._SCHNELL_LETZTE, clear=True)  # Doppelklick-Erinnerung je Test leer
        patch.start()
        self.addCleanup(patch.stop)
        self.modul = app.schnell()
        self.ordner = self.tmp / "webdaten" / "schnell-test"
        patch = mock.patch.object(app, "SCHNELL_FASSUNGEN", self.tmp / "schnell" / "data" / "fassungen")
        patch.start()
        self.addCleanup(patch.stop)

    def wunsch(self, location):
        wid = location.split("schnell=")[1].split("#")[0] if "schnell=" in location else location.rsplit("/", 1)[1]
        return wid, json.loads((self.ordner / "wuensche" / f"{wid}.json").read_text())

    def feedback(self):
        return [a for a in app.auftraege.neue(basis=self.instanz / "auftraege") if a["agent"] == "feedback"]

    def post_dateien(self, pfad, felder, dateien_, feld="dateien"):
        body, art = basis.multipart({"token": app.logik.formular_token(app.GEHEIM), **felder}, dateien_)
        body = body.replace(b'name="dateien"; filename=', f'name="{feld}"; filename='.encode())
        return self.hole(pfad, "POST", body=body, kopf={"Content-Type": art, "Content-Length": str(len(body)),
                                                         "Origin": "http://localhost"})

    def test_kennzeichen_wie_in_lia_schnell(self):
        """Die Web-App erkennt schnell geänderte Fassungen am Notiz-Anfang, den lia/schnell zusichert."""
        self.assertEqual(app.logik.SCHNELL_NOTIZ, self.modul.NOTIZ_PRAEFIX)

    def test_rueckmeldung_geht_an_schnell(self):
        r, _ = self.post(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "Aufgabe 2 einfacher"})
        self.assertEqual(r.status, 303)
        self.assertRegex(r.getheader("location"), rf"^/ergebnis/{KOPF}\?schnell=[0-9a-f]{{12}}#schnell$")
        wid, w = self.wunsch(r.getheader("location"))
        self.assertEqual((w["art"], w["bezug"], w["nr"], w["eigene"], w["text"]),
                         ("aenderung", KOPF, 0, None, "Aufgabe 2 einfacher"))
        self.assertEqual(self.feedback(), [])  # kein Auftrag an den Feedback-Dienst
        # Doppelklick: derselbe Wunsch
        self.assertEqual(self.post(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "Aufgabe 2 einfacher"})[0]
                         .getheader("location"), r.getheader("location"))
        _, html = self.hole(f"/ergebnis/{KOPF}?schnell={wid}")
        for text in ("Wird geändert …", f'hx-get="/teile/schnell/{wid}?zurueck=/ergebnis/{KOPF}&amp;n=1"',
                     'hx-trigger="load delay:2s"', "htmx-2.0.4.min.js"):
            self.assertIn(text, html)
        _, teil = self.hole(f"/teile/schnell/{wid}?zurueck=/ergebnis/{KOPF}&n=95")
        self.assertIn("länger als sonst", teil)
        self.assertIn("delay:10s", teil)
        # lia/schnell legt die neue Fassung mit Seitenbildern ab und antwortet
        quelle = self.tmp / "neu" / "Arbeitsblatt.docx"
        quelle.parent.mkdir()
        quelle.write_bytes(b"DOCX-NEU")
        e = app.fassungen.eigene_dazu(KOPF, quelle, "Schnell geändert: Aufgabe 2 einfacher",
                                      basis=self.instanz / "auftraege", agenten_dir=self.tmp)
        vorschau = (self.tmp / "unterricht" / e["datei"]).parent / "Arbeitsblatt-vorschau"
        vorschau.mkdir()
        (vorschau / "Arbeitsblatt-seite-01.png").write_bytes(b"PNG-NEU")
        (vorschau / "Arbeitsblatt.pdf").write_bytes(b"%PDF neu")
        self.modul.antwort_schreiben({"id": wid, "art": "aenderung", "ok": True, "stand": "fertig",
                                      "text": "Aufgabe 2 ist jetzt einfacher.", "fassung": {"eigene": e["n"]}},
                                     self.ordner)
        r, teil = self.hole(f"/teile/schnell/{wid}?zurueck=/ergebnis/{KOPF}&n=3")
        self.assertEqual((r.status, teil, r.getheader("HX-Redirect")), (200, "", f"/ergebnis/{KOPF}?schnell={wid}#schnell"))
        _, html = self.hole(f"/ergebnis/{KOPF}?schnell={wid}")
        self.assertIn('id="schnell" role="status">Aufgabe 2 ist jetzt einfacher.</p>', html)
        self.assertNotIn("hx-get=\"/teile/schnell", html)
        self.assertIn(f'<img src="/ergebnis/{KOPF}/eigene/1/seite/1"', html)
        self.assertIn("Fassung 2, schnell geändert: „Aufgabe 2 einfacher“", html)
        self.assertEqual(self.hole(f"/ergebnis/{KOPF}/eigene/1/seite/1", roh=True)[1], b"PNG-NEU")
        self.assertEqual(self.hole(f"/ergebnis/{KOPF}/eigene/1/pdf", roh=True)[1], b"%PDF neu")
        self.assertEqual(self.hole(f"/ergebnis/{KOPF}/eigene/1/seite/2")[0].status, 404)
        # Seitenbilder in der Ablage von lia/schnell statt neben der Datei
        ablage = self.tmp / "schnell" / "data" / "fassungen" / KOPF / "eigene-1"
        (ablage / "Arbeitsblatt-vorschau").mkdir(parents=True)
        (ablage / "Arbeitsblatt.docx").write_bytes(b"DOCX-NEU")
        (ablage / "Arbeitsblatt-vorschau" / "Arbeitsblatt-seite-01.png").write_bytes(b"PNG-ABLAGE")
        shutil.rmtree(vorschau)
        self.assertEqual(self.hole(f"/ergebnis/{KOPF}/eigene/1/seite/1", roh=True)[1], b"PNG-ABLAGE")
        self.assertIn(f'<img src="/ergebnis/{KOPF}/eigene/1/seite/1"', self.hole(f"/ergebnis/{KOPF}")[1])
        self.assertEqual(self.hole(f"/ergebnis/{KOPF}/eigene/1/pdf")[0].status, 404)  # dort ohne PDF
        # die nächste Änderung baut auf der schnellen Fassung auf
        r, _ = self.post(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "Merksatz kürzer"})
        self.assertEqual(self.wunsch(r.getheader("location"))[1]["eigene"], 1)
        # an einer bestimmten Datei und Seite
        r, _ = self.post(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "Bild weg", "fassung": KOPF, "dnr": "0", "seite": "2"})
        self.assertEqual({k: self.wunsch(r.getheader("location"))[1][k] for k in ("nr", "eigene", "seite")},
                         {"nr": 0, "eigene": None, "seite": 2})

    def test_fehler_und_andere_wege(self):
        r, html = self.post(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "x" * 4500})  # lia/schnell: höchstens 4000
        self.assertEqual(r.status, 400)
        self.assertIn("Der Text ist zu lang (höchstens 4000 Zeichen).", html)
        # mit Datei: wie bisher an den Feedback-Dienst
        r, _ = self.post_dateien(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "So"}, [("Notiz.pdf", b"%PDF-1")], "datei")
        self.assertEqual(r.status, 303)
        self.assertEqual(len(self.feedback()), 1)
        # Fehler von lia/schnell: der Satz steht oben, rot
        r, _ = self.post(f"/ergebnis/{KOPF}/rueckmeldung", {"text": "Folie 4 weg"})
        wid, _ = self.wunsch(r.getheader("location"))
        self.modul.antwort_schreiben({"id": wid, "art": "aenderung", "ok": False, "stand": "fehler",
                                      "text": "Gerade ist die Rechenzeit aufgebraucht."}, self.ordner)
        _, html = self.hole(f"/ergebnis/{KOPF}?schnell={wid}")
        self.assertIn('hinweis-fehler" id="schnell" role="status">Gerade ist die Rechenzeit aufgebraucht.', html)
        self.assertEqual(self.hole("/teile/schnell/zzz?zurueck=/")[0].status, 404)
        self.assertNotIn("Wird geändert", self.hole(f"/ergebnis/{KOPF}?schnell=0123456789ab")[1])  # unbekannt
        with mock.patch.object(app, "NEUER_AUFTRAG", ""):  # ohne Neu und Rückmeldung auch kein schneller Weg
            self.assertIsNone(app.schnell())
            self.assertEqual(self.hole(f"/teile/schnell/{wid}?zurueck=/")[0].status, 404)
            self.assertNotIn("Anderes Dokument", self.hole("/neu")[1])

    def test_anderes_dokument(self):
        _, html = self.hole("/neu?reihe=strafe")
        self.assertIn('href="/neu?art=dokument&amp;reihe=strafe"', html)
        self.assertIn("Anderes Dokument", html)
        _, html = self.hole("/neu?art=dokument&reihe=strafe")
        self.assertIn("ohne Recherche und ohne Quellenprüfung", html)
        self.assertIn('name="art" value="dokument"', html)
        r, _ = self.post_dateien("/neu", {"art": "dokument", "reihe": "strafe", "text": "Checkliste Wandertag"},
                                 [("../Plan.pdf", b"%PDF-1")])
        self.assertEqual(r.status, 303)
        wid, w = self.wunsch(r.getheader("location"))
        self.assertEqual(r.getheader("location"), f"/neu/schnell/{wid}")
        self.assertEqual((w["art"], w["ort"], w["dateien"], w["text"]),
                         ("dokument", "strafe", ["Plan.pdf"], "Checkliste Wandertag"))
        self.assertEqual((self.ordner / "dateien" / wid / "Plan.pdf").read_bytes(), b"%PDF-1")
        self.assertEqual(list((self.tmp / "eingang").iterdir()), [])
        self.assertEqual(app.auftraege.neue(basis=self.instanz / "auftraege"), [])  # kein Auftrag an unterricht
        _, html = self.hole(f"/neu/schnell/{wid}")
        self.assertIn("Wird erstellt …", html)
        self.assertIn(f'hx-get="/teile/schnell/{wid}?zurueck=/neu/schnell/{wid}&amp;n=1"', html)
        r, _ = self.post_dateien("/neu", {"art": "dokument", "text": "Viel"}, [(f"{n}.pdf", b"%PDF") for n in range(6)])
        self.assertEqual(r.status, 400)
        # fertig: ein erledigter Auftrag von schnell, die Seite leitet zu ihm
        aid = "20261030-170000-schnell-cccccc"
        basis.schreibe(self.instanz / "auftraege" / "erledigt" / f"{aid}.json", {
            "id": aid, "agent": "schnell", "quelle": "schnell-dokument", "ort": "strafe", "text": "Checkliste Wandertag",
            "status": "erledigt", "erstellt": "2026-10-30T17:00:00+01:00", "abgeschlossen": "2026-10-30T17:00:40+01:00",
            "ergebnis": "Hier ist sie.", "ergebnis_dateien": [], "daten": {"kern": "Hier ist sie."}})
        self.modul.antwort_schreiben({"id": wid, "art": "dokument", "ok": True, "stand": "fertig", "auftrag": aid,
                                      "text": "Hier ist sie. Schnell erstellt, ohne Quellenprüfung."}, self.ordner)
        r, _ = self.hole(f"/teile/schnell/{wid}?zurueck=/neu/schnell/{wid}")
        self.assertEqual(r.getheader("HX-Redirect"), f"/ergebnis/{aid}?schnell={wid}#schnell")
        r, _ = self.hole(f"/neu/schnell/{wid}")
        self.assertEqual((r.status, r.getheader("location")), (303, f"/ergebnis/{aid}?schnell={wid}#schnell"))
        _, html = self.hole(f"/ergebnis/{aid}?schnell={wid}")
        self.assertIn("Schnell erstellt, ohne Quellenprüfung.</p>", html)
        self.assertIn('href="/reihe/strafe"', html)  # Ort aus dem Feld ort
        # hat nicht geklappt: Satz und zurück zu Neu
        r, _ = self.post("/neu", {"art": "dokument", "text": "Handout"})
        wid2, _ = self.wunsch(r.getheader("location"))
        self.modul.antwort_schreiben({"id": wid2, "art": "dokument", "ok": False, "stand": "fehler",
                                      "text": "Das hat leider nicht geklappt."}, self.ordner)
        _, html = self.hole(f"/neu/schnell/{wid2}")
        self.assertIn("Das hat leider nicht geklappt.", html)
        self.assertIn('href="/neu?art=dokument"', html)


@unittest.skipUnless(SCHNITTSTELLE.exists(), "lia/schnell noch nicht da")
class TestSchnellNeu(TestSchnell):
    """Dieselben Abläufe in der neuen Oberfläche (oberflaeche/ + ruhig.css), die Lia ab 10.11.2026 sieht."""

    oberflaeche = "neu"

    def test_beide_oberflaechen(self):
        """Kein Schalter: der schnelle Weg hängt an keiner Oberfläche."""
        for wert in ("alt", "neu"):
            with mock.patch.object(app, "OBERFLAECHE", wert):
                self.assertIsNotNone(app.schnell())
        _, html = self.hole(f"/ergebnis/{KOPF}")
        self.assertIn('href="/statisch/ruhig.css"', html)
        self.assertNotIn("htmx-2.0.4.min.js", html)  # htmx nur, solange ein Wunsch wartet
