import hashlib
import re
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import app
import lernmodell

from tests.hilfe import Aufbau

STATISCH = Path(app.__file__).parent / "statisch"


def karte_auf_seite(html: str) -> tuple[str, str]:
    return re.search(r'name="karte" value="([^"]+)"', html).group(1), re.search(r'name="nr" value="(\d+)"', html).group(1)


class Seiten(Aufbau):
    def test_start_fuehrt_zum_modul(self):
        antwort, _ = self.holen("/")
        self.assertEqual((antwort.status, antwort.getheader("location")), (303, "/modul/holzschutz"))

    def test_pruefungsseite(self):
        html = self.text("/modul/holzschutz")
        for erwartet in ("Vortrag mit mündlicher Prüfung", "Pilze bestimmen", "Score 5", "nicht gesehen", "keine Karten",
                         "Gedächtnisprotokolle", "ältere Semester", "Ziel A", "Folie 3"):
            self.assertIn(erwartet, html)
        self.assertLess(html.index("Pilze bestimmen"), html.index("Fäuletypen"))

    def test_pruefungsseite_ohne_termin(self):
        """Gelernte Regel in uni/STATUS.md: Kein Drängen wegen Datum oder Zeitplan."""
        self.assertNotIn("Januar", self.text("/modul/holzschutz"))

    def test_nur_freigegebene_module(self):
        for pfad in ("/modul/anderes", "/modul/anderes/ueben", "/modul/anderes/bild/x/frage"):
            self.assertEqual(self.holen(pfad)[0].status, 404, pfad)

    def test_kopfzeilen(self):
        antwort, _ = self.holen("/modul/holzschutz")
        self.assertEqual(antwort.getheader("content-security-policy"),
                         "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.assertEqual(antwort.getheader("x-content-type-options"), "nosniff")
        self.assertEqual(antwort.getheader("cache-control"), "no-store")
        self.assertEqual(self.holen("/statisch/schrift/inter.woff2")[0].getheader("cache-control"),
                         "public, max-age=2592000")

    def test_keine_fremden_quellen_und_kein_inline(self):
        for pfad in ("/modul/holzschutz", "/modul/holzschutz/ueben", "/modul/holzschutz/rubrik",
                     f"/modul/holzschutz/uebung/{self.uebung_mit_auswertung()}"):
            html = self.text(pfad)
            self.assertNotRegex(html, r'(src|href)="https?:')
            self.assertNotIn("style=", html)
            self.assertNotIn("<script", html)


class Ueben(Aufbau):
    def test_karte_zeigen_ohne_speichern(self):
        html = self.text("/modul/holzschutz/ueben")
        self.assertIn("Antwort zeigen", html)
        for wort in lernmodell.BEWERTUNGEN:
            self.assertIn(f">{wort}</button>", html)
        self.assertFalse((self.modul / "zustand.json").exists())
        self.assertFalse((self.modul / "verlauf.jsonl").exists())

    def test_inhalte_werden_maskiert(self):
        ids = []
        for _ in range(4):
            html = self.text("/modul/holzschutz/ueben")
            if "Pilz" in html and "Welcher" in html:
                self.assertIn("Welcher &lt;Pilz&gt;?", html)
                self.assertNotIn("<Pilz>", html)
                return
            karte, nr = karte_auf_seite(html)
            ids.append(karte)
            self.senden(karte, nr, 3)
        self.fail(f"Karte nicht gesehen: {ids}")

    def test_bewerten_speichert_wie_lernmodell(self):
        karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
        antwort, _ = self.senden(karte, nr, 3)
        self.assertEqual((antwort.status, antwort.getheader("location")), (303, "/modul/holzschutz/ueben"))
        m = lernmodell.Modul(self.modul)
        self.assertIn(karte, m.zustand)
        self.assertEqual([(e["karte"], e["bewertung"]) for e in m.verlauf], [(karte, 3)])
        self.assertEqual(set(m.verlauf[0]), {"zeit", "karte", "thema", "bewertung"})

    def test_doppelt_gesendet_zaehlt_einmal(self):
        karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
        self.senden(karte, nr, 3)
        self.senden(karte, nr, 3)
        self.assertEqual(len(lernmodell.Modul(self.modul).verlauf), 1)

    def test_ende_der_runde(self):
        for _ in range(4):
            karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
            self.senden(karte, nr, 3)
        html = self.text("/modul/holzschutz/ueben")
        self.assertIn("Gerade nichts dran", html)
        self.assertIn("Heute bewertet: 4", html)

    def test_fremde_herkunft_abgelehnt(self):
        karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
        antwort, _ = self.senden(karte, nr, 3, kopf={"Origin": "https://boese.example"})
        self.assertEqual(antwort.status, 403)
        self.assertFalse((self.modul / "verlauf.jsonl").exists())

    def test_ohne_gueltiges_token_nichts_gespeichert(self):
        karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
        antwort, _ = self.senden(karte, nr, 3, token="alt")
        self.assertEqual(antwort.getheader("location"), "/modul/holzschutz/ueben?veraltet=1")
        self.assertFalse((self.modul / "verlauf.jsonl").exists())
        self.assertIn("nicht mehr aktuell", self.text("/modul/holzschutz/ueben?veraltet=1"))

    def test_unbekannte_bewertung(self):
        karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
        self.assertEqual(self.senden(karte, nr, 9)[0].status, 400)
        self.assertFalse((self.modul / "verlauf.jsonl").exists())

    def test_bilder(self):
        antwort, inhalt = self.holen("/modul/holzschutz/bild/pilze-1/frage")
        self.assertEqual((antwort.status, inhalt), (200, b"JPG-FRAGE"))
        self.assertEqual(self.holen("/modul/holzschutz/bild/pilze-1/ganz")[1], b"JPG-GANZ")
        self.assertEqual(self.holen("/modul/holzschutz/bild/faeule-1/frage")[0].status, 404)
        self.assertEqual(self.holen("/modul/holzschutz/bild/pilze-1/anders")[0].status, 404)


class VertraegtSichMitLernenPy(Aufbau):
    def test_lernen_py_setzt_auf_dem_stand_des_portals_auf(self):
        import lernen  # erst hier: lädt agentkit, das Portal selbst tut das nie (test_schutz)
        karte, nr = karte_auf_seite(self.text("/modul/holzschutz/ueben"))
        self.senden(karte, nr, 3)
        m = lernmodell.Modul(self.modul)
        abend = datetime.now(ZoneInfo("Europe/Berlin")).replace(hour=18, minute=0)
        s, nachricht = lernen.zeitschritt(None, m, abend, lambda: False)
        self.assertNotIn(karte, s["warteschlange"])
        self.assertTrue(s["warteschlange"])
        self.assertIsNotNone(nachricht)

    def test_portal_liest_bewertung_aus_telegram(self):
        """Der Lernstand kommt bei jedem Aufruf von der Platte, kein Zwischenspeicher im Dienst."""
        self.text("/modul/holzschutz/ueben")
        m = lernmodell.Modul(self.modul)
        m.bewerten("faeule-1", 3, datetime.now(ZoneInfo("Europe/Berlin")) - timedelta(minutes=1))
        html = self.text("/modul/holzschutz")
        self.assertIn("1 von 4 gesehen", html)


class Pruefsummen(unittest.TestCase):
    def _pruefen(self, ordner: Path, datei: str):
        for zeile in (ordner / datei).read_text().splitlines():
            summe, name = zeile.split()
            self.assertEqual(hashlib.sha256((ordner / name).read_bytes()).hexdigest(), summe, name)

    def test_schrift(self):
        self._pruefen(STATISCH / "schrift", "schrift.sha256")

    def test_htmx(self):
        self._pruefen(STATISCH, "htmx-2.0.4.min.js.sha256")


class Dienstvorlage(unittest.TestCase):
    def test_grenzen(self):
        text = (Path(app.__file__).parent / "systemd" / "uni-portal.service").read_text(encoding="utf-8")
        for zeile in ("MemoryMax=200M", "OnFailure=ausfall@%n.service", "StartLimitIntervalSec=300", "StartLimitBurst=5",
                      "Environment=PORTAL_PORT=8793"):
            self.assertIn(zeile, text)

    def test_auswertung(self):
        ordner = Path(app.__file__).parent / "systemd"
        text = (ordner / "uni-portal-frage.service").read_text(encoding="utf-8")
        for zeile in ("Type=oneshot", "MemoryMax=500M", "OnFailure=ausfall@%n.service", "auswertung_agent.py"):
            self.assertIn(zeile, text)
        text = (ordner / "uni-portal-frage.path").read_text(encoding="utf-8")
        self.assertIn("DirectoryNotEmpty=/home/agent/agenten/uni/portal/data/warteschlange", text)
        self.assertIn("Unit=uni-portal-frage.service", text)


if __name__ == "__main__":
    unittest.main()
