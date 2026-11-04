"""Belegt die Positivliste: Das Portal öffnet nichts außerhalb, zeigt keine Köderdatei, lädt uni/.env nicht und hat
keinen Weg nach außen."""

import ast
import builtins
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import ablage
import app

from tests.hilfe import KOEDER, Aufbau

PORTAL = Path(app.__file__).parent
EIGENER_CODE = ("app.py", "logik.py", "ablage.py")
ANGRIFFE = (
    "/.env", "/data/mails/1.json", "/statisch/../.env", "/statisch/%2e%2e/%2e%2e/.env",
    "/statisch/..%2f..%2f.env", "/modul/holzschutz/../../.env", "/modul/..%2f..%2fdata%2fmails",
    "/modul/mails", "/modul/mailauftraege", "/modul/..", "/modul/anderes",
    "/modul/holzschutz/bild/boese-1/frage", "/modul/holzschutz/bild/boese-2/frage",
    "/modul/holzschutz/bild/boese-1/ganz", "/modul/holzschutz/bild/..%2f..%2f.env/frage",
    "/modul/holzschutz/bild/pilze-1/..%2f..%2f..%2f.env",
    "/docs", "/redoc", "/openapi.json",
)


class Positivliste(Aufbau):
    def _geoeffnet(self, ablauf) -> set[Path]:
        """Alles, was während ablauf() unter dem Agent-Ordner geöffnet wird."""
        echt, gesehen = builtins.open, set()

        def merken(datei, *a, **k):
            if isinstance(datei, (str, os.PathLike)):
                pfad = Path(datei).resolve()
                if pfad.is_relative_to(self.uni.resolve()):
                    gesehen.add(pfad)
            return echt(datei, *a, **k)

        with mock.patch.object(builtins, "open", merken), mock.patch.object(io, "open", merken):
            ablauf()
        return gesehen

    def test_nur_dateien_der_liste_werden_geoeffnet(self):
        def ablauf():
            self.text("/modul/holzschutz")
            self.text("/modul/holzschutz/ueben")
            self.holen("/modul/holzschutz/bild/pilze-1/frage")
            self.holen("/modul/holzschutz/bild/pilze-1/ganz")
            self.senden("faeule-1", 0, 3)
            for pfad in ANGRIFFE:
                self.holen(pfad)

        erlaubt = {self.modul.resolve() / n for n in ablage.MODUL_DATEIEN}
        erlaubt |= {self.modul.resolve() / "bilder" / n for n in ("pilz-1-frage.jpg", "pilz-1-ganz.jpg")}
        erlaubt.add(self.modul.resolve() / "zustand.json.tmp")  # lernmodell.schreibe_json schreibt atomar
        geoeffnet = self._geoeffnet(ablauf)
        self.assertTrue(geoeffnet, "Die Messung hat nichts gesehen, der Test belegt so nichts")
        self.assertLessEqual(geoeffnet, erlaubt)

    def test_kein_koeder_in_einer_antwort(self):
        for pfad in ANGRIFFE:
            antwort, inhalt = self.holen(pfad)
            self.assertNotIn(KOEDER.encode(), inhalt, pfad)
            self.assertNotEqual(antwort.status, 500, pfad)
            if pfad != "/modul/..":  # der Client löst das nicht auf, der Server antwortet mit dem Start
                self.assertIn(antwort.status, (404, 405), pfad)

    def test_bild_pfad_lehnt_alles_ausserhalb_ab(self):
        basis = "data/lernen/holzschutz/bilder"
        self.assertIsNotNone(ablage.bild_pfad(self.uni, "holzschutz", f"{basis}/pilz-1-frage.jpg"))
        for falsch in ("data/mails/1.jpg", "data/mailauftraege/1.jpg", ".env", f"{basis}/../elevenlabs/prompt.jpg",
                       f"{basis}/../../../mails/1.jpg", str(self.uni / "data" / "mails" / "1.jpg"),
                       f"{basis}/fehlt.jpg", None, ""):
            self.assertIsNone(ablage.bild_pfad(self.uni, "holzschutz", falsch), falsch)
        self.assertIsNone(ablage.bild_pfad(self.uni, "anderes", f"{basis}/pilz-1-frage.jpg"))

    def test_symlink_nach_draussen_gilt_nicht(self):
        (self.modul / "bilder" / "link.jpg").symlink_to(self.uni / "data" / "mails" / "1.jpg")
        self.assertIsNone(ablage.bild_pfad(self.uni, "holzschutz", "data/lernen/holzschutz/bilder/link.jpg"))

    def test_module_sind_fest(self):
        self.assertEqual(list(ablage.MODULE), ["holzschutz"])
        self.assertIsNone(ablage.modul_ordner(self.uni, "../mails"))
        self.assertIsNone(ablage.modul_laden(self.uni, "mails"))


class KeinWegNachAussen(unittest.TestCase):
    def _importe(self) -> set[str]:
        namen = set()
        for datei in EIGENER_CODE:
            for knoten in ast.walk(ast.parse((PORTAL / datei).read_text(encoding="utf-8"))):
                if isinstance(knoten, ast.Import):
                    namen |= {a.name.split(".")[0] for a in knoten.names}
                elif isinstance(knoten, ast.ImportFrom):
                    namen.add((knoten.module or "").split(".")[0])
        return namen

    def test_nur_diese_importe(self):
        """Kein smtplib, imaplib, urllib, subprocess, agentkit usw. Wer hier etwas ergänzt, begründet es."""
        self.assertEqual(self._importe(), {
            "ablage", "datetime", "fastapi", "hmac", "lernmodell", "logging", "logik", "os", "pathlib", "secrets",
            "sys", "threading", "typing", "urllib", "uvicorn", "zoneinfo"})

    def test_urllib_nur_zum_zerlegen(self):
        self.assertIn("from urllib.parse import urlsplit", (PORTAL / "logik.py").read_text(encoding="utf-8"))
        self.assertNotIn("urllib.request", "".join((PORTAL / d).read_text(encoding="utf-8") for d in EIGENER_CODE))

    def test_routen_sind_genau_diese(self):
        routen = {(r.path, m) for r in app.app.routes if hasattr(r, "methods") for m in r.methods}
        self.assertEqual({(p, m) for p, m in routen if m != "HEAD"}, {
            ("/", "GET"), ("/modul/{modul}", "GET"), ("/modul/{modul}/ueben", "GET"),
            ("/modul/{modul}/bewerten", "POST"), ("/modul/{modul}/bild/{karte_id}/{art}", "GET")})

    def test_dienst_ohne_env_datei(self):
        text = (PORTAL / "systemd" / "uni-portal.service").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?m)^\s*EnvironmentFile")

    def test_start_laedt_keine_zugangsdaten(self):
        """Eigener Prozess mit leerer Umgebung: echtes Import von app, danach steht nichts aus .env in der Umgebung."""
        code = ("import os, sys, app; "
                "print(sorted(k for k in os.environ if 'HNEE' in k or 'TOKEN' in k or 'KENNWORT' in k or 'PASSWORT' in k)); "
                "print([n for n in sys.modules if n == 'agentkit' or n.startswith('agentkit.') or n == 'dotenv'])")
        ergebnis = subprocess.run([sys.executable, "-c", code], cwd=PORTAL, env={"PATH": os.environ["PATH"]},
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stderr)
        self.assertEqual(ergebnis.stdout.split("\n")[:2], ["[]", "[]"])


if __name__ == "__main__":
    unittest.main()
