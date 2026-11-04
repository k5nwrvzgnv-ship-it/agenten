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

from tests.hilfe import KETTE, KOEDER, Aufbau

PORTAL = Path(app.__file__).parent
EIGENER_CODE = ("app.py", "logik.py", "ablage.py", "uebungen.py", "projekt.py", "../rueckmeldungen.py")
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
    "/projekt/anderes", "/projekt/mails/recherche", "/projekt/..%2f..%2fmails", "/projekt/fehlstellen/fassung/json",
    "/projekt/fehlstellen/fassung/..%2f..%2f..%2f.env", "/projekt/fehlstellen/fassung/env", "/projekt/fehlstellen/mails",
    "/projekt/anderes/schriftverkehr", "/projekt/fehlstellen/kontakte.json", "/projekt/fehlstellen/schriftverkehr.json",
    "/projekt/fehlstellen/rueckmeldung", "/projekt/fehlstellen/rueckmeldung/1", "/projekt/fehlstellen/rueckmeldung/..%2f..%2f..%2fmails",
    "/projekt/fehlstellen/rueckmeldung/20261104-100000-abcdef", "/projekt/anderes/rueckmeldung/20261104-100000-abcdef",
    "/projekt/fehlstellen/rueckmeldung/20261104-100000-abcdef/zuruecknehmen",
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
        antwort, _ = self.hochladen({"text": "Bitte den Zeitplan kürzen."}, ("k.pdf", b"%PDF-KOMMENTARE"), pfad="/projekt/fehlstellen/rueckmeldung")
        kennung = antwort.getheader("location").rsplit("/", 1)[1]

        def ablauf():
            self.text(f"/projekt/fehlstellen/rueckmeldung/{kennung}")
            self.text("/modul/holzschutz")
            self.text("/modul/holzschutz/ueben")
            self.holen("/modul/holzschutz/bild/pilze-1/frage")
            self.holen("/modul/holzschutz/bild/pilze-1/ganz")
            self.senden("faeule-1", 0, 3)
            self.text(f"/modul/holzschutz/uebung/{uebung_id}")
            self.text("/modul/holzschutz/rubrik")
            for pfad in ("", "/recherche", "/recherche?ansicht=quellen", "/protokoll", "/schriftverkehr"):
                self.text(f"/projekt/fehlstellen{pfad}")
            for pfad in ANGRIFFE:
                self.holen(pfad)

        erlaubt = {self.modul.resolve() / n for n in ablage.MODUL_DATEIEN}
        erlaubt |= {self.modul.resolve() / "bilder" / n for n in ("pilz-1-frage.jpg", "pilz-1-ganz.jpg")}
        erlaubt.add(self.modul.resolve() / "zustand.json.tmp")  # lernmodell.schreibe_json schreibt atomar
        erlaubt |= {self.modul.resolve() / "uebungen" / uebung_id / n for n in ablage.UEBUNG_DATEIEN}
        kette = self.uni.resolve() / "data" / "expose" / KETTE
        erlaubt |= {kette / "expose.json", kette / "recherche" / "geprueft.json",
                    self.uni.resolve() / "protokolle" / f"{KETTE}.md",
                    self.uni.resolve() / "data" / "projekte" / "fehlstellen" / "schriftverkehr.json"}
        rueck = self.uni.resolve() / "data" / "projekte" / "fehlstellen" / "rueckmeldungen" / kennung
        erlaubt |= {rueck / "stand.json", rueck / "text.txt"}  # kommentare.pdf nicht: Das Portal gibt sie nie wieder aus
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


class ProjektPositivliste(Aufbau):
    def test_fassung_als_symlink_gilt_nicht(self):
        ordner = self.uni / "data" / "expose" / KETTE / "fassung"
        for datei in ordner.iterdir():
            datei.unlink()
        (ordner / "boese.pdf").symlink_to(self.uni / ".env")
        self.assertIsNone(ablage.fassung_pfad(self.uni, "fehlstellen", "pdf"))
        self.assertEqual(self.holen("/projekt/fehlstellen/fassung/pdf")[0].status, 404)

    def test_nur_docx_und_pdf(self):
        ordner = self.uni / "data" / "expose" / KETTE / "fassung"
        (ordner / "geheim.env").write_text(KOEDER)
        for art in ("env", "json", "txt", "../../../.env"):
            self.assertIsNone(ablage.fassung_pfad(self.uni, "fehlstellen", art), art)

    def test_auszug_als_symlink_gilt_nicht(self):
        ziel = self.uni / "data" / "projekte" / "fehlstellen" / "schriftverkehr.json"
        ziel.unlink()
        ziel.symlink_to(self.uni / "data" / "mails" / "1.json")
        self.assertIsNone(ablage.schriftverkehr_lesen(self.uni, "fehlstellen"))
        self.assertNotIn(KOEDER, self.text("/projekt/fehlstellen/schriftverkehr"))

    def test_kein_koeder_auf_den_seiten(self):
        for pfad in ("", "/recherche", "/protokoll", "/schriftverkehr"):
            self.assertNotIn(KOEDER, self.text(f"/projekt/fehlstellen{pfad}"), pfad)

    def test_portal_liest_kontakte_nicht(self):
        """Die Kontaktliste steuert nur den Agenten; das Portal braucht sie nicht."""
        self.assertNotIn("kontakte.json", (PORTAL / "ablage.py").read_text(encoding="utf-8"))


class RueckmeldungPositivliste(Aufbau):
    def _anlegen(self) -> str:
        antwort, _ = self.hochladen({"text": "Bitte den Zeitplan kürzen."}, ("k.pdf", b"%PDF-" + KOEDER.encode()), pfad="/projekt/fehlstellen/rueckmeldung")
        self.assertEqual(antwort.status, 303)
        return antwort.getheader("location").rsplit("/", 1)[1]

    def test_ids_nur_im_festen_format(self):
        for falsch in ("..", "../../mails", "mails", "", None, "20261104-100000-ABCDEF", "20261104-100000-abcdef/.."):
            self.assertIsNone(ablage.rueckmeldung_ordner(self.uni, "fehlstellen", falsch), falsch)
        self.assertIsNone(ablage.rueckmeldung_ordner(self.uni, "mails", self._anlegen()))

    def test_datei_und_sicherung_kommen_nie_zurueck(self):
        kennung = self._anlegen()
        vorher = self.uni / "data" / "projekte" / "fehlstellen" / "rueckmeldungen" / kennung / "vorher"
        vorher.mkdir()
        (vorher / "expose.json").write_text(KOEDER)
        self.assertNotIn(KOEDER, self.text(f"/projekt/fehlstellen/rueckmeldung/{kennung}"))
        self.assertNotIn(KOEDER, self.text("/projekt/fehlstellen"))
        for rest in ("/kommentare.pdf", "/vorher/expose.json", "/stand.json", "/text.txt"):
            self.assertEqual(self.holen(f"/projekt/fehlstellen/rueckmeldung/{kennung}{rest}")[0].status, 404, rest)

    def test_symlink_gilt_nicht(self):
        wurzel = self.uni / "data" / "projekte" / "fehlstellen" / "rueckmeldungen"
        wurzel.mkdir()
        kennung = "20261104-100000-abcdef"
        (wurzel / kennung).symlink_to(self.uni / "data" / "mails")
        self.assertIsNone(ablage.rueckmeldung_ordner(self.uni, "fehlstellen", kennung))
        self.assertEqual(ablage.rueckmeldungen_ids(self.uni, "fehlstellen"), [])
        self.assertEqual(self.holen(f"/projekt/fehlstellen/rueckmeldung/{kennung}")[0].status, 404)

    def test_text_als_symlink_gilt_nicht(self):
        kennung = self._anlegen()
        pfad = self.uni / "data" / "projekte" / "fehlstellen" / "rueckmeldungen" / kennung / "text.txt"
        pfad.unlink()
        ziel = self.uni / "data" / "mails" / "1.txt"
        ziel.write_text(KOEDER)
        pfad.symlink_to(ziel)
        self.assertNotIn(KOEDER, self.text(f"/projekt/fehlstellen/rueckmeldung/{kennung}"))


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
            "projekt", "re", "rueckmeldungen", "secrets", "shutil", "sys", "threading", "typing", "uebungen", "urllib", "uvicorn",
            "zoneinfo"})

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
            ("/modul/{modul}/rubrik", "GET"), ("/modul/{modul}/rubrik/bestaetigen", "POST"),
            ("/projekt/{projekt}", "GET"), ("/projekt/{projekt}/fassung/{art}", "GET"), ("/projekt/{projekt}/recherche", "GET"),
            ("/projekt/{projekt}/protokoll", "GET"), ("/projekt/{projekt}/schriftverkehr", "GET"),
            ("/projekt/{projekt}/rueckmeldung", "POST"), ("/projekt/{projekt}/rueckmeldung/{kennung}", "GET"),
            ("/projekt/{projekt}/rueckmeldung/{kennung}/zuruecknehmen", "POST")})

    def test_dienst_ohne_env_datei(self):
        for dienst in ("uni-portal.service", "uni-portal-frage.service"):
            text = (PORTAL / "systemd" / dienst).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?m)^\s*EnvironmentFile")

    def test_web_ruft_den_agenten_nicht_auf(self):
        code = "".join((PORTAL / d).read_text(encoding="utf-8") for d in EIGENER_CODE)
        for wort in ("import auswertung_agent", "claude_lauf", "import bewertung", "subprocess"):
            self.assertNotIn(wort, code)

    def test_web_nutzt_vom_gemeinsamen_modul_nur_den_web_teil(self):
        """Marken nehmen, Sichern und Auftrag anlegen gehören dem Agenten: Das Portal ruft nichts davon auf."""
        erlaubt = {"ID", "MAX_BYTES", "MAX_ZEICHEN", "PROJEKTE_ORDNER", "RUECKMELDUNGEN", "STAND", "TEXT", "UploadFehler", "anlegen", "ordner",
                   "pruefen", "stand_ansicht", "zuruecknehmen"}
        benutzt = set()
        for datei in ("app.py", "ablage.py"):
            for knoten in ast.walk(ast.parse((PORTAL / datei).read_text(encoding="utf-8"))):
                if isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name) and knoten.value.id == "rueckmeldungen":
                    benutzt.add(knoten.attr)
        self.assertEqual(benutzt, erlaubt)
        self.assertNotIn("agentkit", (PORTAL.parent / "rueckmeldungen.py").read_text(encoding="utf-8").split('"""', 2)[2])

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
