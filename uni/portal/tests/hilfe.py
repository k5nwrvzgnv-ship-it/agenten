"""Aufbau für die Tests: temporärer Agent-Ordner mit Köderdateien, echter Uvicorn auf einem Unix-Socket."""

import http.client
import json
import shutil
import socket
import tempfile
import threading
import time
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

import uvicorn

import app

KOEDER = "KOEDER-GEHEIM-1234"


class UnixVerbindung(http.client.HTTPConnection):
    def __init__(self, pfad):
        super().__init__("localhost")
        self.pfad = pfad

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.pfad)


def agent_ordner(tmp: Path) -> Path:
    """uni/ im Kleinen: ein Modul mit Text- und Bildkarte, dazu Dateien, die das Portal nie zeigen darf."""
    uni = tmp / "uni"
    modul = uni / "data" / "lernen" / "holzschutz"
    (modul / "bilder").mkdir(parents=True)
    bild = "data/lernen/holzschutz/bilder/pilz-1-frage.jpg"
    karten = [
        {"id": "pilze-1", "thema": "pilze", "typ": "bild", "frage": "Welcher <Pilz>?", "antwort": "Hausschwamm",
         "quelle": "Infokarte", "bild": bild},
        {"id": "faeule-1", "thema": "faeule", "typ": "text", "frage": "Was ist Braunfäule?", "antwort": "Würfelbruch",
         "quelle": "SHB", "bild": None},
        {"id": "boese-1", "thema": "faeule", "typ": "bild", "frage": "Böse Karte", "antwort": "x", "quelle": "q",
         "bild": "data/mails/1.jpg"},
        {"id": "boese-2", "thema": "faeule", "typ": "bild", "frage": "Böse Karte 2", "antwort": "x", "quelle": "q",
         "bild": "data/lernen/holzschutz/bilder/../../../../.env"},
    ]
    (modul / "karten.json").write_text(json.dumps(karten), encoding="utf-8")
    (modul / "pruefungsplan.json").write_text(json.dumps({
        "modul": "Holzschutz und Sanierung", "pruefung": {"form": "Vortrag mit mündlicher Prüfung", "termin": "Januar"},
        "themen": [{"id": "faeule", "titel": "Fäuletypen", "teil": "IHS", "score": 3, "begruendung": "b",
                    "lernziele": [{"text": "Ziel A", "aufgabentyp": "erklären"}], "quellen": ["Folie 3"]},
                   {"id": "pilze", "titel": "Pilze bestimmen", "teil": "IHS+SHB", "score": 5, "begruendung": "c",
                    "lernziele": [], "quellen": []},
                   {"id": "leer", "titel": "Ohne Karten", "teil": "SHB", "score": 1, "begruendung": "d",
                    "lernziele": [], "quellen": []}],
        "fehlt": [{"was": "Gedächtnisprotokolle", "warum": "echte Fragen", "woher": "ältere Semester"}]}),
        encoding="utf-8")
    (modul / "bilder" / "pilz-1-frage.jpg").write_bytes(b"JPG-FRAGE")
    (modul / "bilder" / "pilz-1-ganz.jpg").write_bytes(b"JPG-GANZ")
    # Köder
    (uni / ".env").write_text(f"HNEE_KENNWORT={KOEDER}\n")
    for ordner in ("mails", "mailauftraege"):
        (uni / "data" / ordner).mkdir()
        (uni / "data" / ordner / "1.jpg").write_text(KOEDER)
        (uni / "data" / ordner / "1.json").write_text(KOEDER)
    (modul / "elevenlabs").mkdir()
    (modul / "elevenlabs" / "prompt.jpg").write_text(KOEDER)
    (uni / "data" / "lernen" / "anderes").mkdir()
    (uni / "data" / "lernen" / "anderes" / "karten.json").write_text(KOEDER)
    return uni


class Aufbau(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.uni = agent_ordner(self.tmp)
        self.modul = self.uni / "data" / "lernen" / "holzschutz"
        self.daten = self.tmp / "portal-data"
        for name, wert in (("UNI", self.uni), ("DATEN", self.daten)):
            p = mock.patch.object(app, name, wert)
            p.start()
            self.addCleanup(p.stop)
        self.socket = str(self.tmp / "t.sock")
        self.server = uvicorn.Server(uvicorn.Config(app.app, uds=self.socket, log_level="critical"))
        faden = threading.Thread(target=self.server.run, daemon=True)
        faden.start()
        self.addCleanup(faden.join)
        self.addCleanup(setattr, self.server, "should_exit", True)
        ende = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > ende:
                self.fail("Server startet nicht")
            time.sleep(0.01)

    def holen(self, pfad: str, methode="GET", daten=None, kopf=None):
        verbindung = UnixVerbindung(self.socket)
        rumpf = urllib.parse.urlencode(daten) if daten is not None else None
        kopfzeilen = dict(kopf or {})
        if daten is not None:
            kopfzeilen.setdefault("Content-Type", "application/x-www-form-urlencoded")
        verbindung.request(methode, pfad, rumpf, kopfzeilen)
        antwort = verbindung.getresponse()
        inhalt = antwort.read()
        verbindung.close()
        return antwort, inhalt

    def text(self, pfad: str) -> str:
        antwort, inhalt = self.holen(pfad)
        self.assertEqual(antwort.status, 200, pfad)
        return inhalt.decode("utf-8")

    def senden(self, karte: str, nr, bewertung, **aenderung):
        felder = {"token": app.logik.formular_token(app.GEHEIM), "karte": karte, "nr": str(nr),
                  "bewertung": str(bewertung)}
        kopf = {"Origin": "http://localhost", "Host": "localhost"}
        kopf.update(aenderung.pop("kopf", {}))
        felder.update(aenderung)
        return self.holen("/modul/holzschutz/bewerten", "POST", felder, kopf)
