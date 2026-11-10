"""Alte Oberfläche (vorlagen/ + stil.css): Schalter WEBAPP_OBERFLAECHE, Spalte „Fragen“, und dass
die Routen der neuen Oberfläche hier 404 geben. Die übrigen Tests (test_app.py, test_pflege_app.py) prüfen
oberflaeche/; die alte Testreihe von fd5c5e4 lief am 10.11.2026 einmal vollständig grün gegen diesen Stand."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

import app
from tests import test_app as basis

HIER = Path(__file__).resolve().parent.parent


class AltAufbau(basis.Aufbau):
    oberflaeche = "alt"
    post = basis.TestOrdnung.post

    def setUp(self):  # wie TestOrdnung: Reihen, Testbetrieb für Neu
        super().setUp()
        (self.instanz / "reihen.toml").write_text(basis.REIHEN, encoding="utf-8")
        for name, wert in (("EINGANG", self.tmp / "eingang"), ("NEUER_AUFTRAG", "test")):
            patch = mock.patch.object(app, name, wert)
            patch.start()
            self.addCleanup(patch.stop)
    stunden = basis.TestOrdnung.stunden


class TestSchalter(AltAufbau):

    def test_standard_ist_alt(self):
        """Ohne Angabe (so läuft webapp.service) gilt die alte Oberfläche; nur „neu“ schaltet um."""
        for wert, erwartet in ((None, "alt"), ("neu", "neu"), ("alt", "alt"), ("Neu", "alt")):
            env = {k: v for k, v in os.environ.items() if k != "WEBAPP_OBERFLAECHE"}
            if wert is not None:
                env["WEBAPP_OBERFLAECHE"] = wert
            lauf = subprocess.run([sys.executable, "-c", "import app; print(app.OBERFLAECHE)"], cwd=HIER, env=env,
                                  capture_output=True, text=True, check=True)
            self.assertEqual(lauf.stdout.strip(), erwartet)

    def test_rahmen_alt(self):
        with mock.patch.object(app, "CHAT", True), mock.patch.object(app, "CHAT_ORDNER", self.tmp / "chat"):
            _, html = self.hole("/")
        for text in ('href="/statisch/stil.css"', '<aside class="fragen"', 'action="/fragen"', '<nav class="baum"'):
            self.assertIn(text, html)
        for weg in ("ruhig.css", "Gespräche ohne Ort", "/gespraech"):
            self.assertNotIn(weg, html)
        _, html = self.hole("/reihe/strafe")
        self.assertIn("Kommt bald", html)  # ohne WEBAPP_CHAT nur Platzhalter

    def test_routen_der_anderen_oberflaeche(self):
        ordner = self.tmp / "chat"
        with mock.patch.object(app, "CHAT", True), mock.patch.object(app, "CHAT_ORDNER", ordner):
            gid = app.chat().gespraech_anlegen("", None, ordner)
            for pfad in ("/gespraeche", f"/gespraech/{gid}", f"/teile/gespraech/{gid}",
                         f"/gespraech/{gid}/datei/{gid}/a.pdf", "/ablage/strafe/a.pdf"):
                self.assertEqual(self.hole(pfad)[0].status, 404, pfad)
            for pfad in ("/gespraech/neu", f"/gespraech/{gid}/nachricht", "/ablage/strafe", "/baustein/reihenfrage"):
                self.assertEqual(self.post(pfad, {"text": "x", "ort": "strafe"})[0].status, 404, pfad)
            with mock.patch.object(app, "OBERFLAECHE", "neu"):
                self.assertEqual(self.post("/fragen", {"text": "x"})[0].status, 404)
                self.assertEqual(self.hole(f"/teile/frage/{gid}")[0].status, 404)
                self.assertEqual(self.hole(f"/gespraech/{gid}")[0].status, 200)

    def test_rundgang_ohne_fehler(self):
        """Alle Links ab „Heute“ (zwei Ebenen tief) laden mit der alten Oberfläche ohne Fehler."""
        self.assertEqual(self.post("/reihe/strafe/stunden", {"thema": "Kant"})[0].status, 303)
        gesehen, offen = set(), ["/", "/neu", "/neu?art=arbeitsblatt&reihe=strafe", "/vorlagen", "/ich"]
        for _ in range(2):
            weiter = []
            for pfad in offen:
                if pfad in gesehen:
                    continue
                gesehen.add(pfad)
                r, html = self.hole(pfad, roh=True)
                self.assertIn(r.status, (200, 301, 303), pfad)
                if "text/html" in (r.getheader("Content-Type") or ""):
                    weiter += [p.replace("&amp;", "&") for p in re.findall(r'href="(/[^"#]*)', html.decode())
                               if not p.startswith("/statisch/")]
            offen = weiter
        self.assertGreater(len(gesehen), 15)


class TestFragen(AltAufbau):
    """Spalte „Fragen“ an lia/chat (wie bis 04.11. im Dienst)."""

    def test_fragen_spalte(self):
        self.assertEqual(self.post("/fragen", {"text": "x"})[0].status, 404)  # ohne WEBAPP_CHAT
        ordner = self.tmp / "chat"
        with mock.patch.object(app, "CHAT", True), mock.patch.object(app, "CHAT_ORDNER", ordner):
            _, html = self.hole("/reihe/strafe")
            for text in ("Ich weiß:</span> Ethik › Klasse 8 › Straftheorien", 'name="ohne"', 'action="/fragen"',
                         "htmx-2.0.4.min.js"):
                self.assertIn(text, html)
            r, _ = self.post("/fragen", {"text": "Was heißt Vergeltung?", "reihe": "strafe", "zurueck": "/reihe/strafe"})
            self.assertEqual(r.status, 303)
            fid = r.getheader("location").split("frage=")[1].split("#")[0]
            frage = json.loads((ordner / "fragen" / f"{fid}.json").read_text())
            self.assertEqual((frage["text"], frage["ort"]["reihe"], frage["ort"]["chip"]),
                             ("Was heißt Vergeltung?", "strafe", "Ethik › Klasse 8 › Straftheorien"))
            _, html = self.hole(f"/reihe/strafe?frage={fid}")
            self.assertIn(f'hx-get="/teile/frage/{fid}"', html)
            self.assertIn("Denkt nach", self.hole(f"/teile/frage/{fid}")[1])
            app.chat().antwort_schreiben({"id": fid, "ok": True, "text": "**Vergeltung** heißt <b>x</b>", "fehler": None},
                                         ordner)
            _, teil = self.hole(f"/teile/frage/{fid}")
            self.assertIn("<b>Vergeltung</b> heißt &lt;b&gt;x&lt;/b&gt;", teil)
            self.assertNotIn("hx-get", teil)
            (ordner / "verlauf.jsonl").write_text(json.dumps({"id": fid, "reihe": "strafe", "chip": "Ethik › Klasse 8",
                                                              "frage": "Was heißt Vergeltung?",
                                                              "antwort": "**Vergeltung** heißt Ausgleich."}) + "\n")
            _, html = self.hole("/reihe/strafe")
            self.assertIn(f'href="/neu?reihe=strafe&amp;aus={fid}">Daraus Auftrag machen</a>', html)
            self.assertIn(f"aus={fid}", self.hole(f"/neu?reihe=strafe&aus={fid}")[1])  # Galerie trägt sie weiter
            _, html = self.hole(f"/neu?art=arbeitsblatt&reihe=strafe&aus={fid}")
            self.assertIn("Was heißt Vergeltung?\n\nVergeltung heißt Ausgleich.</textarea>", html)
            r, _ = self.post("/fragen", {"text": " ", "zurueck": "https://boese.example/x"})
            self.assertEqual(r.getheader("location"), "/?fragefehler=leer#fragen")
            self.assertIn("Schreib kurz deine Frage.", self.hole("/?fragefehler=leer")[1])
            self.assertEqual(self.hole("/teile/frage/../../x")[0].status, 404)
