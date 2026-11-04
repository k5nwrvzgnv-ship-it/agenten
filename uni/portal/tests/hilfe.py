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
KETTE = "20261102-165741-uni-ac9dcc"
EXPOSE = {"art": "expose", "titel": "Fehlstellen <erkennen>", "untertitel": "Prototyp", "autoren": ["Jan K."], "betreuung": ["Prof. B."],
          "datum": "03.11.2026", "literatur": ["Achatz (2025). Titel. [OFFEN: Seitenzahl]"], "bloecke": [
              {"typ": "ueberschrift", "text": "Ausgangslage"},
              {"typ": "absatz", "text": "Text davor [OFFEN: Branchenzahlen] und <b>danach</b>."},
              {"typ": "ueberschrift", "ebene": 2, "text": "Daten"},
              {"typ": "liste", "punkte": ["Punkt eins"]},
              {"typ": "tabelle", "titel": "Zeitplan", "kopf": ["Wann", "Was"], "zeilen": [["Dez.", "Versuch [OFFEN]"]]},
              {"typ": "neuartig", "text": "gibt es noch nicht"}]}
GEPRUEFT = {"thema": "t", "fragen": [{"id": "F1", "fenster": "markt", "frage": "Was kostet es?"}, {"id": "F2", "frage": "Wie gut?"}],
            "aussagen": [{"id": "markt-1", "frage": "F1", "text": "Kamera kostet wenig", "status": "gesichert", "fehlt": "", "belege": [
                             {"url": "https://example.org/a", "zitat": "wenig Geld", "pruefung": {"status": "bestanden", "vermerk": "gefunden"}}]},
                         {"id": "markt-2", "frage": "F2", "text": "Gut genug", "status": "unbelegt", "fehlt": "Beleg fehlt", "belege": [
                             {"url": "javascript:alert(1)", "zitat": "boese", "pruefung": {"status": "abgelehnt"}},
                             {"datei": "data/normen/DIN 4074-1.pdf.txt", "seite": 8, "zitat": "Norm", "pruefung": {"status": "bestanden"}}]}],
            "quellen": [{"url": "https://example.org/a", "titel": "Quelle A", "autoren": ["Lin"], "jahr": 2025, "doi": "10.1/ab", "zitierfaehig": True,
                         "pruefung": {"status": "bestanden", "vermerk": "DOI ok"}},
                        {"url": "javascript:alert(2)", "titel": "Quelle B", "jahr": None, "doi": "keine doi", "zitierfaehig": False, "pruefung": {}}],
            "luecken": [{"fenster": "markt", "text": "Preise fehlen"}], "widersprueche": [{"ids": ["markt-1", "markt-2"], "worum": "passt nicht"}],
            "offen": [{"frage": "F2", "warum": "Keine Studie"}],
            "literatursuche": {"datenbank": "Scopus", "datum": "02.11.2026", "arbeiten_ohne_doppelte": 12,
                               "suchen": [{"nr": "S1", "titel": "Holz", "suchstring": "TITLE-ABS-KEY(wood)"}]}}
PROTOKOLL = "# Kopf\n\n## Beschlossen\n- Umfang **kurz**: Henri 10:01\n\nAbsatz <i>eins</i>\nweiter\n"
AUSZUG = {"stand": "2026-11-04T13:00", "seit": "2026-10-01", "gekappt": False,
          "kontakte": [{"name": "Prof. Böhme", "adresse": "b@hnee.de"}, {"name": "Werk", "adresse": "w@x.de"}],
          "mails": [{"kontakt": "b@hnee.de", "richtung": "von", "von": "Böhme <b@hnee.de>", "an": ["jan@hnee.de"], "betreff": "AW: Anfrage",
                     "datum": "2026-10-26T09:44", "text": "Guten Tag <b>Herr</b> Kleinke", "anhaenge": ["plan.pdf"]},
                    {"kontakt": "b@hnee.de", "richtung": "an", "von": "Jan", "an": ["b@hnee.de"], "betreff": "Anfrage",
                     "datum": "2026-10-21T10:00", "text": "Sehr geehrter Herr Böhme", "anhaenge": []}]}
RUBRIK = {"modul": "holzschutz", "quellen": ["Modulhandbuch"], "hinweis": "Entwurf", "bestaetigt": None, "punkte": [
    {"id": "r1", "titel": "Fäule erklären", "teil": "IHS", "themen": ["faeule"], "quelle": "S. 42", "erwartung": "Erklärt Fäule."},
    {"id": "r2", "titel": "Vortrag", "teil": "IHS+SHB", "themen": [], "quelle": "S. 41", "erwartung": "Hält einen Vortrag."}]}
TRANSKRIPT = ("TEST, künstlich.\nPrüferin: Was ist Braunfäule und woran erkennen Sie sie?\n"
              "Prüfling: Bei der Braunfäule bauen die Pilze vor allem die Zellulose ab, das Holz\nzerfällt dann in Würfel.\n"
              "Prüferin: Und bei der Weißfäule?\nPrüfling: Das weiß ich gerade nicht mehr, da bin ich leider unsicher.\n"
              "Prüferin: Danke, damit sind wir am Ende der kleinen Probe angekommen.\n")


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
    (modul / "rubrik.json").write_text(json.dumps(RUBRIK), encoding="utf-8")
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
    # Projekt, dazu Köder neben den erlaubten Dateien
    kette = uni / "data" / "expose" / KETTE
    (kette / "recherche").mkdir(parents=True)
    (kette / "fassung").mkdir()
    (kette / "expose.json").write_text(json.dumps(EXPOSE), encoding="utf-8")
    (kette / "recherche" / "geprueft.json").write_text(json.dumps(GEPRUEFT), encoding="utf-8")
    (kette / "recherche" / "literatur.json").write_text(KOEDER)
    (kette / "fassung" / "Fassung.pdf").write_bytes(b"%PDF-TEST")
    (kette / "fassung" / "Fassung.docx").write_bytes(b"DOCX-TEST")
    (uni / "protokolle").mkdir()
    (uni / "protokolle" / f"{KETTE}.md").write_text(PROTOKOLL, encoding="utf-8")
    (uni / "protokolle" / "anderes.md").write_text(KOEDER)
    projekt = uni / "data" / "projekte" / "fehlstellen"
    projekt.mkdir(parents=True)
    (projekt / "schriftverkehr.json").write_text(json.dumps(AUSZUG), encoding="utf-8")
    (projekt / "kontakte.json").write_text(KOEDER)
    return uni


class Aufbau(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.uni = agent_ordner(self.tmp)
        self.modul = self.uni / "data" / "lernen" / "holzschutz"
        self.daten = self.tmp / "portal-data"
        self.env = self.tmp / "portal.env"
        self.env.write_text(f"UNI_PASSWORT={KOEDER}\n")
        for name, wert in (("UNI", self.uni), ("DATEN", self.daten), ("ENV_DATEI", self.env)):
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

    def hochladen(self, felder: dict | None = None, datei: tuple[str, bytes] | None = None, kopf=None, modul="holzschutz"):
        """Formular multipart/form-data wie aus dem Browser. Ohne Angabe: gültiges Token."""
        grenze = "----testgrenze"
        felder = {"token": app.logik.formular_token(app.GEHEIM), **(felder or {})}
        teile = []
        for name, wert in felder.items():
            teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{wert}\r\n'.encode())
        if datei is not None:
            teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="datei"; filename="{datei[0]}"\r\n'
                         f'Content-Type: application/octet-stream\r\n\r\n'.encode() + datei[1] + b"\r\n")
        rumpf = b"".join(teile) + f"--{grenze}--\r\n".encode()
        kopfzeilen = {"Origin": "http://localhost", "Host": "localhost",
                      "Content-Type": f"multipart/form-data; boundary={grenze}", **(kopf or {})}
        verbindung = UnixVerbindung(self.socket)
        verbindung.request("POST", f"/modul/{modul}/uebung", rumpf, kopfzeilen)
        antwort = verbindung.getresponse()
        inhalt = antwort.read()
        verbindung.close()
        return antwort, inhalt

    def senden_an(self, pfad: str, **felder):
        """POST mit gültigem Token und passender Herkunft."""
        kopf = {"Origin": "http://localhost", "Host": "localhost", **felder.pop("kopf", {})}
        return self.holen(pfad, "POST", {"token": app.logik.formular_token(app.GEHEIM), **felder}, kopf)

    def uebung_mit_auswertung(self) -> str:
        """Fertige Übung im Modulordner, wie sie der Agent hinterlässt."""
        import uebungen
        uebung_id = uebungen.anlegen(self.modul, self.daten, "holzschutz", TRANSKRIPT, "Probe", app._jetzt())
        ordner = self.modul / "uebungen" / uebung_id
        (self.daten / uebungen.WARTESCHLANGE / f"{uebung_id}.json").unlink()
        uebungen.stand_aendern(ordner, stand="fertig", grund=None, laeufe=1, usd=0.25, dauer_s=40.0)
        (ordner / "auswertung.json").write_text(json.dumps({
            "id": uebung_id, "gesamt": "Gesamteinschätzung <b>hier</b>", "rubrik_summe": uebungen.rubrik_summe(RUBRIK),
            "punkte": [{"id": "r1", "titel": "Fäule erklären", "teil": "IHS", "stufe": "teilweise", "stufe_text": "teilweise",
                        "stufe_genannt": "teilweise", "begruendung": "Braunfäule ja, Weißfäule nein.",
                        "zitate": [{"text": "bauen die Pilze vor allem die Zellulose ab", "belegt": True}]},
                       {"id": "r2", "titel": "Vortrag", "teil": "IHS+SHB", "stufe": "unbelegt", "stufe_text": "unbelegt",
                        "stufe_genannt": "erfuellt", "begruendung": "Gut.", "zitate": [{"text": "erfundenes Zitat aus dem Nichts", "belegt": False}]}],
            "luecken": [{"thema": "faeule", "was": "Weißfäule nicht erklärt", "zitat": "Das weiß ich gerade nicht mehr"}],
            "karten_neu": [{"thema": "faeule", "frage": "Was baut Weißfäule ab?", "antwort": "Auch Lignin", "quelle": "SHB", "warum": "Lücke"},
                           {"thema": "pilze", "frage": "Zweite neue Karte?", "antwort": "Ja", "quelle": "Infokarte", "warum": ""}],
            "karten_faellig": [{"karte": "faeule-1", "warum": "Lücke"}], "verworfen": ["Zitat stimmte nicht"]}), encoding="utf-8")
        return uebung_id
