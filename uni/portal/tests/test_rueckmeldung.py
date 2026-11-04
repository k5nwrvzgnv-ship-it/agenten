"""Rückmeldung zum Exposé im Portal: annehmen, Grenzen, Stand, Zurücknehmen. Der Agent-Teil steht in uni/tests/test_rueckmeldungen.py."""

import json
import unittest

import app
import rueckmeldungen

from tests.hilfe import KETTE, Aufbau

ZIEL = "/projekt/fehlstellen/rueckmeldung"
TEXT = "Bitte den Zeitplan <kürzen> und Abschnitt 2 straffen."


class Pruefen(unittest.TestCase):
    def test_nur_text(self):
        self.assertEqual(rueckmeldungen.pruefen(f" a\r\n{TEXT} ", None, b""), (f"a\n{TEXT}", None))

    def test_datei_mit_und_ohne_text(self):
        self.assertEqual(rueckmeldungen.pruefen("", "Mein Exposé.PDF", b"%PDF-1.7"), ("", ".pdf"))
        self.assertEqual(rueckmeldungen.pruefen("x", "a.docx", b"PK\x03\x04rest"), ("x", ".docx"))

    def test_abgelehnt(self):
        for text, name, roh, wort in (("", None, b"", "weder Text"), ("kurz", None, b"", "zu kurz"),
                                      ("x" * (rueckmeldungen.MAX_ZEICHEN + 1), None, b"", "zu lang"), ("a\x00" * 10, None, b"", "ungültige"),
                                      ("", "a.txt", b"%PDF-", "nur PDF"), ("", "a.exe", b"MZ", "nur PDF"), ("", "a", b"%PDF-", "nur PDF"),
                                      ("", "a.pdf", b"PK\x03\x04", "keine echte PDF"), ("", "a.docx", b"%PDF-", "keine echte DOCX"),
                                      ("", "a.pdf", b"", "keine echte PDF"),
                                      ("", "a.pdf", b"%PDF-" + b"x" * rueckmeldungen.MAX_BYTES, "zu groß")):
            with self.assertRaises(rueckmeldungen.UploadFehler, msg=wort) as f:
                rueckmeldungen.pruefen(text, name, roh)
            self.assertIn(wort, str(f.exception))


class Seiten(Aufbau):
    def _schlange(self) -> list[str]:
        ordner = rueckmeldungen.schlange(self.uni)
        return sorted(p.name for p in ordner.iterdir()) if ordner.is_dir() else []

    def _ordner(self, kennung: str):
        return rueckmeldungen.ordner(self.uni, "fehlstellen", kennung)

    def _abschicken(self, text=TEXT, datei=None) -> str:
        antwort, _ = self.hochladen({"text": text}, datei, pfad=ZIEL)
        self.assertEqual(antwort.status, 303)
        return antwort.getheader("location").rsplit("/", 1)[1]

    def test_formular_steht_auf_der_projektseite(self):
        html = self.text("/projekt/fehlstellen")
        for erwartet in (f'action="{ZIEL}"', 'enctype="multipart/form-data"', 'name="datei"', 'name="text"', "1,06", "nur die Kommentare", "20 MB"):
            self.assertIn(erwartet, html)

    def test_text_annehmen(self):
        kennung = self._abschicken()
        wo = self._ordner(kennung)
        self.assertEqual((wo / "text.txt").read_text(encoding="utf-8"), TEXT + "\n")
        self.assertEqual(self._schlange(), [f"{kennung}.json"])
        marke = json.loads((rueckmeldungen.schlange(self.uni) / f"{kennung}.json").read_text())
        self.assertEqual(marke, {"id": kennung, "projekt": "fehlstellen", "kette": KETTE})
        self.assertEqual(sorted(p.name for p in wo.iterdir()), ["stand.json", "text.txt"])  # keine Zwischendatei bleibt
        for pfad, soll in ((wo, 0o700), (wo / "stand.json", 0o600), (wo / "text.txt", 0o600)):
            self.assertEqual(pfad.stat().st_mode & 0o777, soll, pfad.name)

    def test_datei_unter_festem_namen(self):
        for name, roh, ablage in (("../../böse name.PDF", b"%PDF-1.7 Inhalt", "kommentare.pdf"), ("x.docx", b"PK\x03\x04Inhalt", "kommentare.docx")):
            kennung = self._abschicken("", (name, roh))
            wo = self._ordner(kennung)
            self.assertEqual(sorted(p.name for p in wo.iterdir()), [ablage, "stand.json"])
            self.assertEqual((wo / ablage).read_bytes(), roh)
            self.assertEqual((wo / ablage).stat().st_mode & 0o777, 0o600)
            self.assertEqual(rueckmeldungen.stand_lesen(wo)["datei"], ablage)

    def test_text_und_datei_zusammen(self):
        wo = self._ordner(self._abschicken(TEXT, ("k.pdf", b"%PDF-1.7")))
        self.assertEqual(sorted(p.name for p in wo.iterdir()), ["kommentare.pdf", "stand.json", "text.txt"])

    def test_grenzen_auf_dem_weg_durchs_formular(self):
        for datei, felder, status, wort in ((None, {}, 400, "weder Text"), (None, {"text": "kurz"}, 400, "zu kurz"),
                                            (("a.txt", b"x"), {}, 400, "nur PDF"), (("a.pdf", b"kein pdf"), {"text": TEXT}, 400, "keine echte PDF"),
                                            (("a.pdf", b"%PDF-" + b"x" * (21 * 1024 * 1024)), {}, 413, "Zu groß")):
            antwort, inhalt = self.hochladen(felder, datei, pfad=ZIEL)
            self.assertEqual(antwort.status, status, wort)
            self.assertIn(wort, inhalt.decode(), wort)
        self.assertEqual(self._schlange(), [])

    def test_fehler_behaelt_den_text(self):
        antwort, inhalt = self.hochladen({"text": TEXT}, ("a.txt", b"x"), pfad=ZIEL)
        self.assertEqual(antwort.status, 400)
        self.assertIn("Bitte den Zeitplan &lt;kürzen&gt;", inhalt.decode())

    def test_altes_token_und_fremde_herkunft(self):
        antwort, inhalt = self.hochladen({"text": TEXT, "token": "alt"}, pfad=ZIEL)
        self.assertEqual(antwort.status, 400)
        self.assertIn("nicht mehr aktuell", inhalt.decode())
        antwort, _ = self.hochladen({"text": TEXT}, kopf={"Origin": "https://boese.example"}, pfad=ZIEL)
        self.assertEqual(antwort.status, 403)
        self.assertEqual(self._schlange(), [])

    def test_unbekanntes_projekt(self):
        antwort, _ = self.hochladen({"text": TEXT}, pfad="/projekt/anderes/rueckmeldung")
        self.assertEqual(antwort.status, 404)

    def test_stand_wartet(self):
        kennung = self._abschicken()
        html = self.text(f"{ZIEL}/{kennung}")
        for erwartet in ("wartet", 'http-equiv="refresh"', "Zurücknehmen", "Bitte den Zeitplan &lt;kürzen&gt;"):
            self.assertIn(erwartet, html)
        self.assertIn(f'href="{ZIEL}/{kennung}"', self.text("/projekt/fehlstellen"))

    def test_zuruecknehmen(self):
        kennung = self._abschicken()
        antwort, _ = self.senden_an(f"{ZIEL}/{kennung}/zuruecknehmen")
        self.assertEqual(antwort.status, 303)
        self.assertEqual(self._schlange(), [])
        html = self.text(f"{ZIEL}/{kennung}")
        self.assertIn("zurückgenommen", html)
        self.assertNotIn('http-equiv="refresh"', html)
        self.assertNotIn(">Zurücknehmen<", html)

    def test_zuruecknehmen_altes_token(self):
        kennung = self._abschicken()
        antwort, _ = self.holen(f"{ZIEL}/{kennung}/zuruecknehmen", "POST", {"token": "alt"}, {"Origin": "http://localhost", "Host": "localhost"})
        self.assertIn("veraltet=1", antwort.getheader("location"))
        self.assertEqual(self._schlange(), [f"{kennung}.json"])

    def test_zuruecknehmen_zu_spaet_aendert_nichts(self):
        kennung = self._abschicken()
        wo = self._ordner(kennung)
        (rueckmeldungen.schlange(self.uni) / f"{kennung}.json").unlink()  # der Agent hat sie genommen
        rueckmeldungen.stand_aendern(wo, stand="laeuft", grund=rueckmeldungen.GRUND_LAEUFT, auftrag="a")
        self.senden_an(f"{ZIEL}/{kennung}/zuruecknehmen")
        self.assertEqual(rueckmeldungen.stand_lesen(wo)["stand"], "laeuft")
        html = self.text(f"{ZIEL}/{kennung}")
        self.assertIn("läuft", html)
        self.assertNotIn(">Zurücknehmen<", html)

    def test_wartet_ohne_marke_ist_abgebrochen(self):
        kennung = self._abschicken()
        (rueckmeldungen.schlange(self.uni) / f"{kennung}.json").unlink()
        html = self.text(f"{ZIEL}/{kennung}")
        self.assertIn("abgebrochen", html)
        self.assertNotIn('http-equiv="refresh"', html)

    def test_ergebnis_wird_angezeigt(self):
        kennung = self._abschicken()
        (rueckmeldungen.schlange(self.uni) / f"{kennung}.json").unlink()
        rueckmeldungen.stand_aendern(self._ordner(kennung), stand="fertig", grund=None, ergebnis="Neue Fassung <b>da</b>.\nZweite Zeile", hinweis="Datei ohne Kommentare")
        html = self.text(f"{ZIEL}/{kennung}")
        for erwartet in ("fertig", "Neue Fassung &lt;b&gt;da&lt;/b&gt;.", "Zweite Zeile", "Datei ohne Kommentare", "Zur aktuellen Fassung"):
            self.assertIn(erwartet, html)
        self.assertNotIn('http-equiv="refresh"', html)

    def test_kopfzeilen_bleiben_und_kein_stil_inline(self):
        """Die CSP verbietet Inline-Stile: Was die Seite braucht, steht in stil.css."""
        antwort, inhalt = self.holen(f"{ZIEL}/{self._abschicken()}")
        self.assertEqual(antwort.getheader("cache-control"), "no-store")
        self.assertNotIn(b"style=", inhalt)
        self.assertEqual(app.KOPFZEILEN["X-Content-Type-Options"], antwort.getheader("x-content-type-options"))


if __name__ == "__main__":
    unittest.main()
