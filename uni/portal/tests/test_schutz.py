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
EIGENER_CODE = ("app.py", "logik.py", "ablage.py", "uebungen.py")
ANGRIFFE = (
    "/.env", "/data/mails/1.json", "/statisch/../.env", "/statisch/%2e%2e/%2e%2e/.env",
    "/statisch/..%2f..%2f.env", "/modul/holzschutz/../../.env", "/modul/..%2f..%2fdata%2fmails",
    "/modul/mails", "/modul/mailauftraege", "/modul/..", "/modul/anderes",
    "/modul/holzschutz/bild/boese-1/frage", "/modul/holzschutz/bild/boese-2/frage",
    "/modul/holzschutz/bild/boese-1/ganz", "/modul/holzschutz/bild/..%2f..%2f.env/frage",
    "/modul/holzschutz/bild/pilze-1/..%2f..%2f..%2f.env",
    "/modul/mails/uebung/20261104-100000-abcdef", "/modul/holzschutz/uebung/1", "/modul/holzschutz/uebung/mails",
    "/modul/holzschutz/uebung/..%2f..%2f..%2fmails", "/modul/holzschutz/uebung/20261104-100000-abcdef",
    "/modul/holzschutz/uebung/..%2f..%2felevenlabs", "/modul/mailauftraege/rubrik", "/modul/anderes/rubrik",
    "/modul/holzschutz/uebungen", "/modul/holzschutz/uebung",
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
        uebung_id = self.uebung_mit_auswertung()

        def ablauf():
            self.text("/modul/holzschutz")
            self.text("/modul/holzschutz/ueben")
            self.holen("/modul/holzschutz/bild/pilze-1/frage")
            self.holen("/modul/holzschutz/bild/pilze-1/ganz")
            self.senden("faeule-1", 0, 3)
            self.text(f"/modul/holzschutz/uebung/{uebung_id}")
            self.text("/modul/holzschutz/rubrik")
            for pfad in ANGRIFFE:
                self.holen(pfad)

        erlaubt = {self.modul.resolve() / n for n in ablage.MODUL_DATEIEN}
        erlaubt |= {self.modul.resolve() / "bilder" / n for n in ("pilz-1-frage.jpg", "pilz-1-ganz.jpg")}
        erlaubt.add(self.modul.resolve() / "zustand.json.tmp")  # lernmodell.schreibe_json schreibt atomar
        erlaubt |= {self.modul.resolve() / "uebungen" / uebung_id / n for n in ablage.UEBUNG_DATEIEN}
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
        self.assertNotIn("mails", ablage.MODUL_DATEIEN)
        self.assertIsNone(ablage.modul_ordner(self.uni, "../mails"))
        self.assertIsNone(ablage.modul_laden(self.uni, "mails"))


class UebungsablagePositivliste(Aufbau):
    def test_nur_feste_dateien_einer_uebung(self):
        uebung_id = self.uebung_mit_auswertung()
        ordner = self.modul / "uebungen" / uebung_id
        (ordner / "geheim.json").write_text(KOEDER)
        self.assertIsNotNone(ablage.uebung_datei(self.uni, "holzschutz", uebung_id, ablage.TRANSKRIPT))
        self.assertIsNone(ablage.uebung_datei(self.uni, "holzschutz", uebung_id, "geheim.json"))
        self.assertIsNone(ablage.uebung_datei(self.uni, "holzschutz", uebung_id, "../../../mails/1.json"))
        self.assertNotIn(KOEDER, self.text(f"/modul/holzschutz/uebung/{uebung_id}"))

    def test_ids_nur_im_festen_format(self):
        (self.modul / "uebungen").mkdir()
        for falsch in ("..", "../../mails", "mails", "", None, "20261104-100000-ABCDEF", "20261104-100000-abcdef/.."):
            self.assertIsNone(ablage.uebung_ordner(self.uni, "holzschutz", falsch), falsch)
        self.assertIsNone(ablage.uebung_ordner(self.uni, "mails", "20261104-100000-abcdef"))

    def test_symlink_auf_mails_gilt_nicht(self):
        (self.modul / "uebungen").mkdir()
        kennung = "20261104-100000-abcdef"
        (self.modul / "uebungen" / kennung).symlink_to(self.uni / "data" / "mails")
        self.assertIsNone(ablage.uebung_ordner(self.uni, "holzschutz", kennung))
        self.assertEqual(ablage.uebungen_ids(self.uni, "holzschutz"), [])
        self.assertEqual(self.holen(f"/modul/holzschutz/uebung/{kennung}")[0].status, 404)

    def test_transkript_als_symlink_gilt_nicht(self):
        uebung_id = self.uebung_mit_auswertung()
        pfad = self.modul / "uebungen" / uebung_id / ablage.TRANSKRIPT
        pfad.unlink()
        ziel = self.uni / "data" / "mails" / "1.txt"
        ziel.write_text(KOEDER)
        pfad.symlink_to(ziel)
        self.assertIsNone(ablage.uebung_datei(self.uni, "holzschutz", uebung_id, ablage.TRANSKRIPT))
        self.assertNotIn(KOEDER, self.text(f"/modul/holzschutz/uebung/{uebung_id}"))

    def test_env_nur_die_eine_zeile(self):
        self.env.write_text(f"UNI_PASSWORT={KOEDER}\nELEVENLABS_AGENT_URL=https://elevenlabs.io/app/talk-to?agent_id=abc\n")
        self.assertEqual(ablage.elevenlabs_adresse(self.env), "https://elevenlabs.io/app/talk-to?agent_id=abc")
        html = self.text("/modul/holzschutz")
        self.assertIn('href="https://elevenlabs.io/app/talk-to?agent_id=abc"', html)
        self.assertNotIn(KOEDER, html)


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
            "ablage", "datetime", "fastapi", "hashlib", "hmac", "json", "lernmodell", "logging", "logik", "os", "pathlib",
            "re", "secrets", "sys", "threading", "typing", "uebungen", "urllib", "uvicorn", "zoneinfo"})

    def test_urllib_nur_zum_zerlegen(self):
        for datei in ("logik.py", "ablage.py"):
            self.assertIn("from urllib.parse import urlsplit", (PORTAL / datei).read_text(encoding="utf-8"))
        self.assertNotIn("urllib.request", "".join((PORTAL / d).read_text(encoding="utf-8") for d in EIGENER_CODE))

    def test_routen_sind_genau_diese(self):
        routen = {(r.path, m) for r in app.app.routes if hasattr(r, "methods") for m in r.methods}
        self.assertEqual({(p, m) for p, m in routen if m != "HEAD"}, {
            ("/", "GET"), ("/modul/{modul}", "GET"), ("/modul/{modul}/ueben", "GET"),
            ("/modul/{modul}/bewerten", "POST"), ("/modul/{modul}/bild/{karte_id}/{art}", "GET"),
            ("/modul/{modul}/uebung", "POST"), ("/modul/{modul}/uebung/{uebung_id}", "GET"),
            ("/modul/{modul}/uebung/{uebung_id}/neu", "POST"), ("/modul/{modul}/uebung/{uebung_id}/karten", "POST"),
            ("/modul/{modul}/rubrik", "GET"), ("/modul/{modul}/rubrik/bestaetigen", "POST")})

    def test_dienst_ohne_env_datei(self):
        for dienst in ("uni-portal.service", "uni-portal-frage.service"):
            text = (PORTAL / "systemd" / dienst).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^\s*EnvironmentFile")

    def test_web_ruft_den_agenten_nicht_auf(self):
        code = "".join((PORTAL / d).read_text(encoding="utf-8") for d in EIGENER_CODE)
        for wort in ("import auswertung_agent", "claude_lauf", "import bewertung", "subprocess"):
            self.assertNotIn(wort, code)

    def test_auswertung_ohne_werkzeuge_und_eigene_sperre(self):
        code = (PORTAL / "auswertung_agent.py").read_text(encoding="utf-8")
        self.assertIn('cfg["werkzeuge"][AGENT] = [""]', code)
        self.assertIn("claude_lauf.laufen(AGENT, HIER,", code)
        self.assertNotIn("subprocess", code)

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
