import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import app  # noqa: F401  (setzt den Pfad zu uni/lernmodell.py)
import lernmodell
import uebungen

from tests.hilfe import KOEDER, RUBRIK, TRANSKRIPT, Aufbau

JETZT = datetime(2026, 11, 4, 18, 0, tzinfo=ZoneInfo("Europe/Berlin"))


class Upload(unittest.TestCase):
    def test_erlaubte_endungen(self):
        for name in ("a.txt", "A.TXT", "b.md"):
            self.assertIn("Prüferin:", uebungen.datei_lesen(name, TRANSKRIPT.encode()))

    def test_andere_endungen_abgelehnt(self):
        for name in ("a.pdf", "a.exe", "a.html", "a.txt.sh", "a", "", None, "a.docx", ".env"):
            with self.assertRaises(uebungen.UploadFehler, msg=name):
                uebungen.datei_lesen(name, TRANSKRIPT.encode())

    def test_groesse(self):
        with self.assertRaisesRegex(uebungen.UploadFehler, "zu groß"):
            uebungen.datei_lesen("a.txt", b"x" * (uebungen.MAX_BYTES + 1))

    def test_zeichengrenzen(self):
        with self.assertRaisesRegex(uebungen.UploadFehler, "zu lang"):
            uebungen.text_pruefen("x" * (uebungen.MAX_ZEICHEN + 1))
        with self.assertRaisesRegex(uebungen.UploadFehler, "zu kurz"):
            uebungen.text_pruefen("kurz")
        self.assertEqual(len(uebungen.text_pruefen("x" * uebungen.MAX_ZEICHEN)), uebungen.MAX_ZEICHEN)

    def test_kein_text(self):
        with self.assertRaisesRegex(uebungen.UploadFehler, "UTF-8"):
            uebungen.datei_lesen("a.txt", b"\xff\xfe\x00\x01" * 100)
        with self.assertRaisesRegex(uebungen.UploadFehler, "reinen Text"):
            uebungen.datei_lesen("a.txt", b"x" * 300 + b"\x00")

    def test_bom_und_zeilenenden(self):
        text = uebungen.datei_lesen("a.txt", b"\xef\xbb\xbf" + ("Zeile\r\n" * 50).encode())
        self.assertTrue(text.startswith("Zeile\nZeile"))

    def test_json_von_elevenlabs(self):
        roh = {"transcript": [{"role": "agent", "message": "Was ist Braunfäule?", "time_in_call_secs": 1},
                              {"role": "user", "message": "x" * 200, "time_in_call_secs": 5},
                              {"role": "agent", "message": None}]}
        text = uebungen.datei_lesen("a.json", json.dumps(roh).encode())
        self.assertTrue(text.startswith("Prüferin: Was ist Braunfäule?\nPrüfling: xxx"))

    def test_fremdes_json(self):
        for roh in (b'{"a": 1}', b"[1, 2]", b"{kaputt"):
            with self.assertRaises(uebungen.UploadFehler):
                uebungen.datei_lesen("a.json", roh)

    def test_titel(self):
        self.assertEqual(uebungen.titel_pruefen("  ein\n Titel "), "ein Titel")
        self.assertEqual(len(uebungen.titel_pruefen("x" * 500)), uebungen.MAX_TITEL)
        self.assertEqual(uebungen.titel_pruefen(None), "")


class Warteschlange(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.tmp = Path(t.name)
        self.modul, self.daten = self.tmp / "m", self.tmp / "d"
        self.modul.mkdir()
        self.id = uebungen.anlegen(self.modul, self.daten, "holzschutz", TRANSKRIPT, "T", JETZT)
        self.ordner = self.modul / "uebungen" / self.id

    def test_anlegen(self):
        self.assertEqual((self.ordner / "transkript.txt").read_text(encoding="utf-8").strip(), TRANSKRIPT.strip())
        self.assertEqual(self.ordner.stat().st_mode & 0o777, 0o700)
        self.assertEqual(json.loads((self.daten / "warteschlange" / f"{self.id}.json").read_text()),
                         {"id": self.id, "modul": "holzschutz", "erzwingen": False})
        self.assertEqual(uebungen.stand_ansicht(uebungen.stand_lesen(self.ordner), self.daten)["text"], "wartet")

    def test_abgebrochen_wenn_auftrag_weg(self):
        (self.daten / "warteschlange" / f"{self.id}.json").unlink()
        uebungen.stand_aendern(self.ordner, stand="laeuft")
        ansicht = uebungen.stand_ansicht(uebungen.stand_lesen(self.ordner), self.daten)
        self.assertEqual((ansicht["wert"], ansicht["neu_startbar"]), ("fehlgeschlagen", True))

    def test_parken_und_neu_starten(self):
        auftrag = {"id": self.id, "modul": "holzschutz"}
        uebungen.stand_aendern(self.ordner, stand="wartet", grund="knapp", versuche=2)
        uebungen.parken(self.daten, auftrag)
        self.assertFalse(uebungen.in_schlange(self.daten, self.id))
        ansicht = uebungen.stand_ansicht(uebungen.stand_lesen(self.ordner), self.daten)
        self.assertEqual((ansicht["wert"], ansicht["geparkt"], ansicht["laeuft_noch"]), ("wartet", True, False))
        self.assertTrue(uebungen.neu_einreihen(self.ordner, self.daten, "holzschutz", self.id, JETZT))
        self.assertFalse(uebungen.ist_geparkt(self.daten, self.id))
        roh = json.loads((self.daten / "warteschlange" / f"{self.id}.json").read_text())
        self.assertTrue(roh["erzwingen"])
        self.assertEqual(uebungen.stand_lesen(self.ordner)["versuche"], 0)

    def test_fertige_startet_nicht_neu(self):
        (self.daten / "warteschlange" / f"{self.id}.json").unlink()
        uebungen.stand_aendern(self.ordner, stand="fertig")
        self.assertFalse(uebungen.neu_einreihen(self.ordner, self.daten, "holzschutz", self.id, JETZT))
        self.assertFalse(uebungen.in_schlange(self.daten, self.id))


class Rubrik(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.ordner = Path(t.name)
        (self.ordner / "rubrik.json").write_text(json.dumps(RUBRIK), encoding="utf-8")

    def test_entwurf_und_bestaetigung(self):
        rubrik = uebungen.rubrik_lesen(self.ordner)
        self.assertFalse(uebungen.rubrik_bestaetigt(rubrik))
        self.assertEqual(uebungen.rubrik_hinweis({"rubrik_summe": uebungen.rubrik_summe(rubrik)}, rubrik), "Rubrik noch nicht bestätigt")
        self.assertTrue(uebungen.rubrik_bestaetigen(self.ordner, JETZT))
        rubrik = uebungen.rubrik_lesen(self.ordner)
        self.assertTrue(uebungen.rubrik_bestaetigt(rubrik))
        self.assertIsNone(uebungen.rubrik_hinweis({"rubrik_summe": uebungen.rubrik_summe(rubrik)}, rubrik))

    def test_geaenderte_rubrik_gilt_wieder_als_unbestaetigt(self):
        uebungen.rubrik_bestaetigen(self.ordner, JETZT)
        rubrik = uebungen.rubrik_lesen(self.ordner)
        alte_summe = uebungen.rubrik_summe(rubrik)
        rubrik["punkte"][0]["erwartung"] = "Anders"
        self.assertFalse(uebungen.rubrik_bestaetigt(rubrik))
        self.assertIn("früheren", uebungen.rubrik_hinweis({"rubrik_summe": alte_summe}, rubrik))

    def test_ohne_rubrik(self):
        (self.ordner / "rubrik.json").unlink()
        self.assertIsNone(uebungen.rubrik_lesen(self.ordner))
        self.assertFalse(uebungen.rubrik_bestaetigen(self.ordner, JETZT))


class KartenUebernehmen(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.modul = Path(t.name)
        self.ordner = self.modul / "uebung"
        self.ordner.mkdir()
        self.karten = [{"id": "alt-1", "thema": "alt", "typ": "text", "frage": "Alt?", "antwort": "Ja", "quelle": "q", "bild": None}]
        (self.modul / "karten.json").write_text(json.dumps(self.karten), encoding="utf-8")
        (self.modul / "zustand.json").write_text('{"nicht": "anfassen"}', encoding="utf-8")
        (self.modul / "verlauf.jsonl").write_text('{"nicht": "anfassen"}\n', encoding="utf-8")
        self.auswertung = {"id": "u1", "karten_neu": [
            {"thema": "t", "frage": "Neu 1?", "antwort": "A", "quelle": "Q"}, {"thema": "t", "frage": "Neu 2?", "antwort": "B", "quelle": "Q"},
            {"thema": "alt", "frage": "Neu 3?", "antwort": "C", "quelle": "Q"}], "karten_faellig": [{"karte": "alt-1"}, {"karte": "alt-2"}]}

    def _karten(self):
        return json.loads((self.modul / "karten.json").read_text(encoding="utf-8"))

    def _unveraendert(self):
        self.assertEqual((self.modul / "zustand.json").read_text(), '{"nicht": "anfassen"}')
        self.assertEqual((self.modul / "verlauf.jsonl").read_text(), '{"nicht": "anfassen"}\n')
        self.assertEqual(self._karten()[0], self.karten[0])

    def test_einzeln(self):
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", [1], JETZT), 1)
        self.assertEqual([k["frage"] for k in self._karten()], ["Alt?", "Neu 2?"])
        self.assertEqual(self._karten()[1]["herkunft"], "uebung u1")
        self.assertEqual(self._karten()[1]["id"], uebungen.karte_id("t", "Neu 2?"))
        self._unveraendert()

    def test_gesammelt_und_kein_zweites_mal(self):
        uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", [1], JETZT)
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", None, JETZT), 2)
        self.assertEqual(len(self._karten()), 4)
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", None, JETZT), 0)
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", [1], JETZT), 0)
        self.assertEqual(len(self._karten()), 4)
        self._unveraendert()

    def test_gleiche_karte_aus_zwei_uebungen_nur_einmal(self):
        anderer = self.modul / "andere"
        anderer.mkdir()
        uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", [0], JETZT)
        uebungen.uebernehmen(self.modul, anderer, self.auswertung, "neu", [0], JETZT)
        self.assertEqual(len(self._karten()), 2)

    def test_unbekannte_nummer_oder_art(self):
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "neu", [99], JETZT), 0)
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "boese", None, JETZT), 0)
        self.assertEqual(len(self._karten()), 1)

    def test_vormerken_aendert_keinen_lernstand(self):
        self.assertEqual(uebungen.uebernehmen(self.modul, self.ordner, self.auswertung, "faellig", [0], JETZT), 1)
        self.assertEqual(uebungen.vorgemerkt_lesen(self.modul), ["alt-1"])
        self._unveraendert()
        uebungen.vormerkung_entfernen(self.modul, "alt-1")
        self.assertEqual(uebungen.vorgemerkt_lesen(self.modul), [])

    def test_karten_id_wie_karten_py(self):
        import hashlib
        schluessel = "Frage?|".encode()
        self.assertEqual(uebungen.karte_id("t", " Frage? "), f"t-{hashlib.sha1(schluessel).hexdigest()[:8]}")


class Seiten(Aufbau):
    def _rubrik_datei(self):
        return lernmodell.lies_json(self.modul / "rubrik.json", None)

    def test_ohne_adresse_ein_hinweis_statt_link(self):
        html = self.text("/modul/holzschutz")
        self.assertIn("Mündlich üben", html)
        self.assertIn("Adresse des ElevenLabs-Agenten fehlt", html)
        self.assertNotIn('href="https', html)

    def test_nur_https_als_adresse(self):
        for falsch in ("http://elevenlabs.io/a", "javascript:alert(1)", 'https://a.de/"onclick="x', "https://"):
            self.env.write_text(f"ELEVENLABS_AGENT_URL={falsch}\n")
            html = self.text("/modul/holzschutz")
            self.assertIn("Adresse des ElevenLabs-Agenten fehlt", html, falsch)

    def test_csp_bleibt(self):
        self.env.write_text("ELEVENLABS_AGENT_URL=https://elevenlabs.io/a\n")
        antwort, inhalt = self.holen("/modul/holzschutz")
        self.assertEqual(antwort.getheader("content-security-policy"),
                         "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.assertNotIn(b"<iframe", inhalt)
        self.assertNotIn(b"<script", inhalt)

    def test_datei_hochladen_legt_auftrag_an(self):
        antwort, _ = self.hochladen({"titel": "Erste"}, ("t.txt", TRANSKRIPT.encode()))
        self.assertEqual(antwort.status, 303)
        kennung = antwort.getheader("location").rsplit("/", 1)[1]
        self.assertTrue((self.modul / "uebungen" / kennung / "transkript.txt").is_file())
        self.assertTrue(uebungen.in_schlange(self.daten, kennung))
        self.assertIn("Erste", self.text("/modul/holzschutz"))
        html = self.text(antwort.getheader("location"))
        self.assertIn("wartet", html)
        self.assertIn('http-equiv="refresh"', html)
        self.assertIn("Rubrik noch nicht bestätigt", html)

    def test_text_einfuegen(self):
        antwort, _ = self.hochladen({"text": TRANSKRIPT})
        self.assertEqual(antwort.status, 303)

    def test_grenzen_auf_dem_weg_durchs_formular(self):
        for datei, felder, status, wort in (
                (("t.pdf", b"%PDF"), {}, 400, "Erlaubt sind nur"),
                (("t.txt", b"x" * (uebungen.MAX_BYTES + 1)), {}, 400, "zu groß"),
                (("t.txt", b"x" * (2 * 1024 * 1024)), {}, 413, "Zu groß"),
                (None, {"text": "kurz"}, 400, "zu kurz"),
                (None, {}, 400, "weder eine Datei"),
                (("t.txt", TRANSKRIPT.encode()), {"text": TRANSKRIPT}, 400, "nicht beides")):
            antwort, inhalt = self.hochladen(felder, datei)
            self.assertEqual(antwort.status, status, wort)
            self.assertIn(wort, inhalt.decode(), wort)
        self.assertEqual(list((self.modul).glob("uebungen/*")), [])
        self.assertEqual(list(self.daten.glob("warteschlange/*")), [])

    def test_dateiname_kann_keinen_pfad_setzen(self):
        antwort, _ = self.hochladen({}, ("../../../.env.txt", TRANSKRIPT.encode()))
        self.assertEqual(antwort.status, 303)
        kennung = antwort.getheader("location").rsplit("/", 1)[1]
        self.assertEqual(sorted(p.name for p in (self.modul / "uebungen" / kennung).iterdir()), ["stand.json", "transkript.txt"])
        self.assertEqual((self.uni / ".env").read_text(), f"HNEE_KENNWORT={KOEDER}\n")

    def test_formularschutz_beim_upload(self):
        antwort, _ = self.hochladen({"text": TRANSKRIPT}, kopf={"Origin": "http://boese.example"})
        self.assertEqual(antwort.status, 403)
        antwort, inhalt = self.hochladen({"text": TRANSKRIPT, "token": "falsch"})
        self.assertEqual(antwort.status, 400)
        self.assertIn("nicht mehr aktuell", inhalt.decode())
        self.assertIn("Prüfling", inhalt.decode())  # der eingefügte Text ist nicht verloren
        self.assertEqual(list(self.daten.glob("warteschlange/*")), [])

    def test_ergebnisseite(self):
        kennung = self.uebung_mit_auswertung()
        html = self.text(f"/modul/holzschutz/uebung/{kennung}")
        for teil in ("fertig", "Fäule erklären", "teilweise", "bauen die Pilze vor allem die Zellulose ab", "nicht im Transkript gefunden",
                     "Weißfäule nicht erklärt", "Was baut Weißfäule ab?", "Alle 2 übernehmen", "Vormerken", "Rubrik noch nicht bestätigt",
                     "0.25 USD", "Zitat stimmte nicht", "Fäuletypen"):
            self.assertIn(teil, html, teil)
        self.assertIn("&lt;b&gt;hier", html)  # Text von Claude wird maskiert
        self.assertNotIn('http-equiv="refresh"', html)

    def test_rubrik_bestaetigen_per_knopf(self):
        kennung = self.uebung_mit_auswertung()
        self.assertIn("Rubrik bestätigen", self.text("/modul/holzschutz/rubrik"))
        antwort, _ = self.senden_an("/modul/holzschutz/rubrik/bestaetigen")
        self.assertEqual(antwort.status, 303)
        self.assertNotIn("noch nicht bestätigt", self.text("/modul/holzschutz/rubrik"))
        self.assertNotIn("noch nicht bestätigt", self.text(f"/modul/holzschutz/uebung/{kennung}"))
        self.assertTrue(uebungen.rubrik_bestaetigt(self._rubrik_datei()))

    def test_rubrik_formularschutz(self):
        self.assertEqual(self.senden_an("/modul/holzschutz/rubrik/bestaetigen", kopf={"Origin": "http://boese.example"})[0].status, 403)
        self.senden_an("/modul/holzschutz/rubrik/bestaetigen", token="falsch")
        self.assertFalse(uebungen.rubrik_bestaetigt(self._rubrik_datei()))

    def test_karten_erst_auf_klick(self):
        kennung = self.uebung_mit_auswertung()
        vorher = (self.modul / "karten.json").read_text(encoding="utf-8")
        self.text(f"/modul/holzschutz/uebung/{kennung}")
        self.assertEqual((self.modul / "karten.json").read_text(encoding="utf-8"), vorher)
        self.senden_an(f"/modul/holzschutz/uebung/{kennung}/karten", art="neu", nr="0")
        karten = json.loads((self.modul / "karten.json").read_text(encoding="utf-8"))
        self.assertEqual(karten[:4], json.loads(vorher))
        self.assertEqual(karten[4]["frage"], "Was baut Weißfäule ab?")
        self.senden_an(f"/modul/holzschutz/uebung/{kennung}/karten", art="neu", nr="alle")
        self.assertEqual(len(json.loads((self.modul / "karten.json").read_text(encoding="utf-8"))), 6)
        self.assertFalse((self.modul / "zustand.json").exists())
        self.assertFalse((self.modul / "verlauf.jsonl").exists())
        self.assertEqual(self.senden_an(f"/modul/holzschutz/uebung/{kennung}/karten", art="neu", nr="abc")[0].status, 400)

    def test_vorgemerkte_karte_kommt_zuerst_und_verschwindet_nach_bewertung(self):
        kennung = self.uebung_mit_auswertung()
        self.senden_an(f"/modul/holzschutz/uebung/{kennung}/karten", art="faellig", nr="0")
        self.assertFalse((self.modul / "zustand.json").exists())
        self.assertIn("1 aus Übungen vorgemerkt", self.text("/modul/holzschutz"))
        self.assertIn('name="karte" value="faeule-1"', self.text("/modul/holzschutz/ueben"))
        self.senden("faeule-1", 0, 3)
        self.assertEqual(uebungen.vorgemerkt_lesen(self.modul), [])
        self.assertTrue((self.modul / "zustand.json").exists())

    def test_neu_starten(self):
        kennung = self.uebung_mit_auswertung()
        ordner = self.modul / "uebungen" / kennung
        self.senden_an(f"/modul/holzschutz/uebung/{kennung}/neu")
        self.assertFalse(uebungen.in_schlange(self.daten, kennung))  # fertig: nichts passiert
        uebungen.stand_aendern(ordner, stand="fehlgeschlagen", grund="Grund X")
        html = self.text(f"/modul/holzschutz/uebung/{kennung}")
        self.assertIn("Grund X", html)
        self.assertIn("Noch einmal auswerten", html)
        self.senden_an(f"/modul/holzschutz/uebung/{kennung}/neu")
        self.assertTrue(uebungen.in_schlange(self.daten, kennung))

    def test_knappes_kontingent_sagt_wartet(self):
        kennung = self.uebung_mit_auswertung()
        ordner = self.modul / "uebungen" / kennung
        uebungen.stand_aendern(ordner, stand="wartet", grund="Kontingent ist knapp.")
        uebungen.parken(self.daten, {"id": kennung, "modul": "holzschutz"})
        html = self.text(f"/modul/holzschutz/uebung/{kennung}")
        self.assertIn("wartet", html)
        self.assertIn("Kontingent ist knapp.", html)
        self.assertIn("Jetzt starten", html)
        self.assertNotIn('http-equiv="refresh"', html)


if __name__ == "__main__":
    unittest.main()
