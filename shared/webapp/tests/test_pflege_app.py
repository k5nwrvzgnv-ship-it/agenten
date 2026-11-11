"""Struktur pflegen über den echten Server (Strukturplan docs/struktur-pflege-plan.md, Bauschritt 5): jede Maske, die
Testregeln 24, 25 und 32 bis 35 aus Sicht der App, Rückgängig und „Letzte Änderungen“, die Lerngruppe (Abschnitt 6).
Grundlage ist eine eingefrorene Kopie der echten reihen.toml (tests/daten/reihen_echt.toml) in einer Instanz im
Temp-Ordner; die liegt in keinem Git-Repo, also gibt es keinen Commit (agentkit.strukturpflege)."""

import asyncio
import hashlib
import logging
import re
import stat
import threading
from pathlib import Path
from unittest import mock

from agentkit import struktur, termine
from agentkit import strukturpflege as sp

import app
import pflege
from tests.test_app import Aufbau, multipart, schreibe

ECHT = (Path(__file__).parent / "daten" / "reihen_echt.toml").read_text(encoding="utf-8")
STRAFE = "ethik-8-straftheorien"
WAHNSINN = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"
AKTION = re.compile(r"\?aktion=(\d{8}-\d{6}-\d{6})")


class Pflege(Aufbau):
    def setUp(self):
        super().setUp()
        self.datei = self.instanz / "reihen.toml"
        self.datei.write_text(ECHT, encoding="utf-8")

    def post(self, pfad, felder, token=True, origin="http://localhost"):
        body, art = multipart({**({"token": app.logik.formular_token(app.GEHEIM)} if token else {}), **felder}, [])
        kopf = {"Content-Type": art, "Content-Length": str(len(body))}
        if origin:
            kopf["Origin"] = origin
        return self.hole(pfad, "POST", body=body, kopf=kopf)

    def ok(self, pfad, felder) -> str:
        """POST, der eine Aktion auslöst: 303 mit ?aktion=…; gibt die Weiterleitung zurück."""
        r, html = self.post(pfad, felder)
        self.assertEqual(r.status, 303, html[-2000:])
        ziel = r.getheader("location")
        self.assertRegex(ziel, AKTION)
        return ziel

    def seite(self, ziel: str) -> str:
        """Seite nach einer Weiterleitung, ohne Anker (den schickt ein Browser nicht mit)."""
        return self.hole(ziel.split("#")[0])[1]

    def material_an(self, stunde_id: str, reihe_id: str, aid="20261030-140944-unterricht-93e29e") -> None:
        schreibe(self.instanz / "auftraege" / "erledigt" / f"{aid}.json", {
            **app.auftraege.erledigter(aid, basis=self.instanz / "auftraege"), "reihe": reihe_id})
        z = app.zustand_()
        z.schreiben(app.logik.stunde_zuordnen(z.lesen(), aid, stunde_id))

    def s(self):
        return struktur.laden(self.instanz)

    def text(self) -> str:
        return self.datei.read_text(encoding="utf-8")

    def mit_berlin(self) -> None:
        self.datei.write_text('[schule]\nbundesland = "BE"\n\n' + ECHT, encoding="utf-8")

    def termine_von(self, klasse_id: str) -> list[str]:
        return [t.kennung for t in self.s().plan(klasse_id).termine]

    def letzte(self):
        return sp.letzte(50, app.umgebung())

    def mit_plan(self, klasse_id="ethik-8", tag="Di", stunde="3") -> list[str]:
        """Bundesland und Stundenplan über die Masken; gibt die Termine der Klasse ab heute (30.10.2026) zurück."""
        if not self.s().schule:
            self.ok("/schule", {"bundesland": "BE"})
        self.ok(f"/klasse/{klasse_id}/stundenplan", {"wie": "ganz", "zeilen": "2", "tag-0": tag, "stunde-0": stunde})
        return [k for k in self.termine_von(klasse_id) if k >= "2026-10-30"]

    def reihe(self, titel, anzahl=0, klasse_id="ethik-8", ab="2026-10-30") -> dict:
        ziel = self.ok(f"/klasse/{klasse_id}/reihe/neu", {"titel": titel, **({"anzahl": str(anzahl)} if anzahl else {}),
                                                         **({"ab": ab} if ab else {})})
        return self.s().reihe(ziel.split("/reihe/")[1].split("?")[0])


class TestLesen(Pflege):
    def test_regel_35_laden_und_lesen_aendern_nichts(self):
        """Testregel 35: Keine Seite und keine Maske ändert beim Öffnen etwas (Datei byte-gleich, keine Aktion,
        keine Lerngruppen-Datei)."""
        self.mit_berlin()
        vorher = self.text()
        for pfad in ("/", "/fach/ethik", "/fach/neu", "/fach/ethik/bearbeiten", "/fach/ethik/klasse/neu",
                     "/klasse/ethik-8", "/klasse/ethik-8/bearbeiten", "/klasse/ethik-8/stundenplan",
                     "/klasse/ethik-8/uebernehmen", "/klasse/ethik-8/reihe/neu", f"/reihe/{STRAFE}",
                     f"/reihe/{STRAFE}/bearbeiten", f"/reihe/{STRAFE}/termine", f"/reihe/{STRAFE}/kopieren",
                     f"/reihe/{STRAFE}/kopieren?klasse=darstellendes-spiel-kurs-11", "/klasse/ethik-7-2025-26",
                     "/reihe/ethik-7-freundschaft", "/ich"):
            with self.subTest(pfad=pfad):
                r, html = self.hole(pfad)
                self.assertEqual(r.status, 200, pfad)
                self.assertNotIn("20261", self.sichtbar(html))  # keine Aktions-ids im sichtbaren Text
        self.assertEqual(self.text(), vorher)
        self.assertEqual(self.letzte(), [])
        self.assertFalse((self.instanz / "lerngruppen.toml").exists())
        self.assertFalse((self.tmp / "webdaten" / "aktionen").exists())

    def test_baum_mit_neu_und_altes_format_ohne_masken(self):
        _, html = self.hole(f"/reihe/{STRAFE}")
        for text in ('href="/fach/neu"><span>+ Fach</span>', 'href="/fach/ethik/klasse/neu"><span>+ Klasse oder Kurs',
                     'href="/klasse/ethik-8/reihe/neu"><span>+ Reihe</span>', f'href="/reihe/{STRAFE}/bearbeiten"',
                     "Archivieren", "In eine andere Klasse übernehmen", f'action="/reihe/{STRAFE}/stunden"'):
            self.assertIn(text, html)
        self.assertNotIn('href="/klasse/ethik-7-2025-26/reihe/neu"', html)  # Archiv: keine „+ Neu“-Knöpfe
        _, html = self.hole("/reihe/ethik-7-freundschaft")
        self.assertIn("Im Archiv (mit der ganzen Klasse", html)
        self.assertNotIn('action="/reihe/ethik-7-freundschaft/stunden"', html)
        self.assertNotIn('class="menue-halter plus"', html)  # Archiv: kein „+“
        self.datei.write_text('[[reihe]]\nid = "r"\nfach = "Ethik"\nklasse = "8"\ntitel = "Alt"\n', encoding="utf-8")
        self.assertNotIn("+ Fach", self.hole("/")[1])
        for pfad in ("/fach/neu", "/fach/ethik/klasse/neu", "/reihe/r/bearbeiten"):
            self.assertEqual(self.hole(pfad)[0].status, 404, pfad)


class TestDoppelklick(Pflege):
    """Ein Doppelklick schickt dieselbe Formular-Kennung zweimal; eine neu geladene Seite hat eine neue."""

    def zweimal(self, pfad, felder):
        """Zwei gleiche POST: beide 303 auf dieselbe Seite."""
        erste, zweite = (self.post(pfad, {**felder, "einmal": "kennung-1"})[0] for _ in range(2))
        self.assertEqual((erste.status, zweite.status), (303, 303))
        self.assertRegex(erste.getheader("location"), AKTION)
        self.assertEqual(zweite.getheader("location"), erste.getheader("location"))

    def stunden(self):
        return len(self.s().reihe(STRAFE)["stunden"])

    def test_stunde(self):
        vorher = self.stunden()
        self.zweimal(f"/reihe/{STRAFE}/stunden", {"thema": ""})
        self.assertEqual(self.stunden(), vorher + 1)
        # Mehrere leere Stunden nacheinander sind Absicht: neue Seite, neue Kennung
        self.ok(f"/reihe/{STRAFE}/stunden", {"thema": "", "einmal": "kennung-2"})
        self.assertEqual(self.stunden(), vorher + 2)

    def test_stunde_gleichzeitig(self):
        vorher = self.stunden()
        antworten = []
        felder = {"thema": "Kant", "einmal": "kennung-1"}
        faeden = [threading.Thread(target=lambda: antworten.append(self.post(f"/reihe/{STRAFE}/stunden", felder)[0]))
                  for _ in range(2)]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join()
        self.assertEqual([r.status for r in antworten], [303, 303])
        self.assertEqual(antworten[0].getheader("location"), antworten[1].getheader("location"))
        self.assertEqual(self.stunden(), vorher + 1)

    def test_fehler_zaehlt_nicht(self):
        """Hat die erste Anfrage nicht geklappt, darf derselbe Knopf es noch einmal versuchen."""
        vorher = self.stunden()
        r, _ = self.post(f"/reihe/{STRAFE}/stunden", {"thema": "x" * 5000, "einmal": "kennung-1"})
        self.assertEqual(r.status, 400)
        self.ok(f"/reihe/{STRAFE}/stunden", {"thema": "Kant", "einmal": "kennung-1"})
        self.assertEqual(self.stunden(), vorher + 1)

    def test_reihe(self):
        vorher = self.text().count("[[reihe]]")
        self.zweimal("/klasse/ethik-8/reihe/neu", {"titel": "Neue Reihe"})
        self.assertEqual(self.text().count("[[reihe]]"), vorher + 1)

    def test_fach(self):
        vorher = self.text().count("[[fach]]")
        self.zweimal("/fach/neu", {"name": "Kunst"})
        self.assertEqual(self.text().count("[[fach]]"), vorher + 1)

    def test_formulare_tragen_kennung_und_sperre(self):
        for seite, ziel in ((f"/reihe/{STRAFE}", "/stunden"), ("/klasse/ethik-8/reihe/neu", "/reihe/neu"),
                            ("/fach/neu", "/fach/neu")):
            _, html = self.hole(seite)
            form = re.search(rf'<form [^>]*{ziel}"[^>]*>.*?</form>', html, re.S).group(0)
            self.assertIn("data-einmal", form, seite)
            self.assertRegex(form, r'name="einmal" value="[0-9a-f]{16}"')
            self.assertIn('<script src="/statisch/einmal.js" defer></script>', html)
        # Neu geladen: neue Kennung
        kennung = re.compile(r'name="einmal" value="([0-9a-f]+)"')
        self.assertNotEqual(kennung.search(self.hole("/fach/neu")[1])[1], kennung.search(self.hole("/fach/neu")[1])[1])
        self.assertNotIn("einmal.js", self.hole("/fach/ethik/bearbeiten")[1])


class TestFach(Pflege):
    def test_anlegen_aendern_archivieren_loeschen(self):
        r, html = self.post("/fach/neu", {"name": " "})
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.PFLICHT["fach"], html)
        r, html = self.post("/fach/neu", {"name": "ethik"})  # Testregel 24: gibt es schon
        self.assertEqual(r.status, 400)
        self.assertIn("Fach ethik gibt es schon.", html)
        ziel = self.ok("/fach/neu", {"name": "Philosophie"})
        self.assertTrue(ziel.startswith("/fach/philosophie?aktion="))
        r, html = self.hole(ziel)
        for text in ("Fach „Philosophie“ angelegt", ">Rückgängig</button>", "Noch keine Klasse und kein Kurs.",
                     '<a class="baum-fach" href="/fach/philosophie" aria-current="page">Philosophie</a>',
                     'href="/fach/philosophie/klasse/neu"'):
            self.assertIn(text, html)
        self.ok("/fach/philosophie/bearbeiten", {"name": "Philosophie", "alt_name": "Philosophie", "kurzform": "PH",
                                                 "alt_kurzform": ""})
        self.assertEqual(self.s().objekt("philosophie")["kurzform"], "PH")
        r, _ = self.post("/fach/philosophie/bearbeiten", {"name": "Philosophie", "alt_name": "Philosophie",
                                                          "kurzform": "PH", "alt_kurzform": "PH"})
        self.assertEqual(r.getheader("location"), "/fach/philosophie?erledigt=nichts")
        # Archivieren und Löschen eines Fachs: einmal fragen (Plan Abschnitt 5)
        r, html = self.post("/objekt/philosophie/archivieren", {})
        self.assertEqual(r.status, 200)
        self.assertIn("Fach Philosophie archivieren?", html)
        self.assertIn("Dazu gehören 0 Klassen mit 0 Reihen.", html)
        self.assertIsNone(self.s().objekt("philosophie")["archiviert"] or None)
        self.ok("/objekt/philosophie/archivieren", {"bestaetigt": "1"})
        self.assertTrue(self.s().objekt("philosophie")["archiviert"])
        self.assertIn("Archiviert. Alles darin bleibt erhalten.", self.hole("/fach/philosophie")[1])
        self.ok("/objekt/philosophie/wiederherstellen", {})
        self.assertIn("Löschen", self.hole("/fach/philosophie/bearbeiten")[1])
        self.assertIn("Fach Philosophie löschen?", self.post("/objekt/philosophie/loeschen", {})[1])
        ziel = self.ok("/objekt/philosophie/loeschen", {"bestaetigt": "1"})
        self.assertTrue(ziel.startswith("/?aktion="))
        self.assertIsNone(self.s().objekt("philosophie"))
        # Ethik hat Klassen: kein Löschen, Archivieren geht
        _, html = self.hole("/fach/ethik/bearbeiten")
        self.assertIn("Löschen geht nicht, daran hängt: 2 Klassen.", html)
        r, html = self.post("/objekt/ethik/loeschen", {"bestaetigt": "1"})
        self.assertEqual(r.status, 400)
        self.assertIn("Archivieren geht immer", html)


class TestKlasse(Pflege):
    def test_anlegen_mit_stundenplan_und_bundesland(self):
        """Lia-Test Aufgabe 1: neue 9 in Ethik ab Februar, dienstags 3. Stunde; das Bundesland fragt die Maske
        einmal."""
        _, html = self.hole("/fach/ethik/klasse/neu")
        for text in ('value="2026/27"', 'name="bundesland"', 'name="tag-1"', "+ weiterer Termin"):
            self.assertIn(text, html)
        felder = {"name": "9", "schuljahr": "2026/27", "zeilen": "2", "tag-0": "Di", "stunde-0": "3",
                  "ab": "2027-02-01"}
        r, html = self.post("/fach/ethik/klasse/neu", {**felder, "mehr": "1"})  # eine Zeile mehr, nichts gespeichert
        self.assertEqual(r.status, 200)
        self.assertIn('name="tag-2"', html)
        self.assertIn('<option value="Di" selected>Dienstag</option>', html)
        r, html = self.post("/fach/ethik/klasse/neu", felder)
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.BUNDESLAND_FEHLT, html)
        vorher = self.text()
        ziel = self.ok("/fach/ethik/klasse/neu", {**felder, "bundesland": "BE"})
        self.assertTrue(ziel.startswith("/klasse/ethik-9?aktion="))
        s = self.s()
        self.assertEqual(s.schule, {"bundesland": "BE"})
        k = s.objekt("ethik-9")
        self.assertEqual([(e["tag"], e["stunde"], e["ab"]) for e in k["zeitplan"]], [("Di", 3, "2027-02-01")])
        self.assertEqual(k["zeitplan"][0]["bis"], termine.kalender("BE").schuljahr("2026/27")[1].isoformat())
        erwartet = self.termine_von("ethik-9")
        self.assertTrue(erwartet and all(termine.kennung_lesen(t)[0].weekday() == 1 for t in erwartet))
        _, html = self.hole(ziel)
        self.assertIn("Klasse Ethik 9 (2026/27) angelegt", html)
        self.assertIn("Stundenplan: Di 3. Std.", html)
        self.assertEqual(html.count('class="termin-zeile'), len(erwartet))
        self.assertIn(termine.anzeige(erwartet[0]), html)
        self.assertIn('href="/klasse/ethik-9/reihe/neu"', html)
        # Testregel 24: doppelte Klasse, zu langer Name, kaputtes Schuljahr: nichts geschrieben, Text für Lia
        jetzt = self.text()
        for falsch, text in (({"name": "9", "schuljahr": "2026/27"}, "Klasse 9 (2026/27) in Ethik gibt es schon."),
                             ({"name": "x" * 41, "schuljahr": "2026/27"}, "Der Name ist zu lang"),
                             ({"name": "10", "schuljahr": "26/27"}, "Schreib das Schuljahr bitte so: 2026/27."),
                             ({"name": "", "schuljahr": "2026/27"}, "Wie heißt die Klasse oder der Kurs?")):
            with self.subTest(falsch=falsch):
                r, html = self.post("/fach/ethik/klasse/neu", falsch)
                self.assertEqual(r.status, 400)
                self.assertIn(text, html)
        self.assertEqual(self.text(), jetzt)
        # Rückgängig: die Klasse ist weg, das Bundesland bleibt (eigene Aktion)
        aktion = AKTION.search(ziel)[1]
        r, _ = self.post("/rueckgaengig", {"aktion": aktion, "zurueck": "/klasse/ethik-9"})
        self.assertEqual(r.status, 303)
        self.assertTrue(r.getheader("location").startswith("/ich?aktion="))  # die Klasse gibt es nicht mehr
        self.assertIsNone(self.s().objekt("ethik-9"))
        self.assertEqual(self.text().replace('[schule]\nbundesland = "BE"\n\n', ""), vorher)

    def test_bearbeiten_lerngruppe_verschieben(self):
        self.ok("/klasse/ethik-8/bearbeiten", {"name": "8a", "alt_name": "8", "schuljahr": "2026/27",
                                               "alt_schuljahr": "2026/27"})
        self.assertEqual(self.s().objekt("ethik-8")["name"], "8a")
        _, html = self.hole("/klasse/ethik-8/bearbeiten")
        self.assertIn(pflege.LERNGRUPPE_HINWEIS, html)
        geheim = "Sehr heterogene Gruppe, viel Sprachförderung"
        with self.assertLogs(level="DEBUG") as logs:
            ziel = self.ok("/klasse/ethik-8/lerngruppe", {"lerngruppe": geheim, "alt_lerngruppe": ""})
            _, html = self.hole(ziel)
        self.assertIn("Lerngruppe von Ethik 8a (2026/27) geändert", html)
        lg = self.instanz / "lerngruppen.toml"
        self.assertEqual(stat.S_IMODE(lg.stat().st_mode), 0o600)
        self.assertIn(geheim, lg.read_text(encoding="utf-8"))
        self.assertNotIn(geheim, self.text())
        # Testregel 21: nie in Log, Hinweis oder Aktionsliste
        self.assertFalse([z for z in logs.output if "Sprachförderung" in z])
        self.assertNotIn("Sprachförderung", html.split('id="lg"')[0])
        self.assertFalse([a for a in self.letzte() if "Sprachförderung" in (a["text"] or "")])
        self.assertIn(geheim, self.hole("/klasse/ethik-8/bearbeiten")[1])
        # Konflikt: Jan hat die Lerngruppe inzwischen geändert
        r, html = self.post("/klasse/ethik-8/lerngruppe", {"lerngruppe": "neu", "alt_lerngruppe": "etwas anderes"})
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.NEU_LADEN, html)
        # in ein anderes Fach (Korrektur), Reihen gehen mit; Rückgängig
        vorher = self.text()
        ziel = self.ok("/klasse/ethik-8/verschieben", {"fach": "darstellendes-spiel"})
        self.assertEqual(self.s().reihe(STRAFE)["fach"], "Darstellendes Spiel")
        self.post("/rueckgaengig", {"aktion": AKTION.search(ziel)[1], "zurueck": "/klasse/ethik-8"})
        self.assertEqual(self.text(), vorher)

    def test_stundenplan_und_ab_stichtag(self):
        """Halbjahr (Plan 2a.3): neuer Wochentag ab dem Stichtag, die Stunden danach behalten die Reihenfolge und
        bekommen neue Daten, bei gleicher Anzahl keine Stunde ohne Termin (Testregel 30 aus Sicht der App)."""
        r, html = self.post("/klasse/ethik-8/stundenplan", {"wie": "ganz", "zeilen": "2", "tag-0": "Di",
                                                            "stunde-0": "3"})
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.BUNDESLAND_FEHLT, html)
        frei = self.mit_plan()
        stichtag = termine.kalender("BE").halbjahr_stichtag("2026/27")
        _, html = self.hole("/klasse/ethik-8/stundenplan")
        self.assertIn(f'value="{stichtag.isoformat()}"', html)  # Vorbelegung: Beginn der Winterferien
        nach_stichtag = [k for k in frei if k >= stichtag.isoformat()]
        r = self.reihe("Würde", anzahl=3, ab=nach_stichtag[0][:10])
        ids = [s["id"] for s in r["stunden"]]
        self.assertEqual([s["termin"] for s in r["stunden"]], nach_stichtag[:3])
        ziel = self.ok("/klasse/ethik-8/stundenplan", {"wie": "ab", "stichtag": stichtag.isoformat(), "zeilen": "2",
                                                       "tag-0": "Do", "stunde-0": "2"})
        self.assertTrue(ziel.startswith("/klasse/ethik-8?aktion=") and ziel.endswith("#termine"))
        neu = self.s().reihe(r["id"])
        self.assertEqual([s["id"] for s in neu["stunden"]], ids)
        self.assertTrue(all(termine.kennung_lesen(s["termin"])[0].weekday() == 3 for s in neu["stunden"]))
        self.assertTrue(all(s["termin"].endswith("/2") for s in neu["stunden"]))
        self.assertIn("Stundenplan: Di 3. Std., Do 2. Std.", self.hole("/klasse/ethik-8")[1])
        r2, html = self.post("/klasse/ethik-8/stundenplan", {"wie": "ab", "stichtag": "", "zeilen": "2",
                                                             "tag-0": "Do", "stunde-0": "2"})
        self.assertEqual(r2.status, 400)
        self.assertIn("Ab wann gilt der neue Stundenplan?", html)

    def test_uebernehmen_ins_naechste_schuljahr(self):
        _, html = self.hole("/klasse/ethik-8/uebernehmen")
        self.assertIn('value="2027/28"', html)
        self.ok("/klasse/ethik-8/lerngruppe", {"lerngruppe": "Gruppe", "alt_lerngruppe": ""})
        ziel = self.ok("/klasse/ethik-8/uebernehmen", {"name": "9", "schuljahr": "2027/28", "lerngruppe": "1"})
        neu = self.s().objekt("ethik-9")
        self.assertTrue(ziel.startswith("/klasse/ethik-9?aktion="))
        self.assertEqual((neu["herkunft"], neu["schuljahr"], neu["reihen"], neu["lerngruppe"]),
                         ("ethik-8", "2027/28", [], "Gruppe"))
        r, html = self.post("/klasse/ethik-8/uebernehmen", {"name": "9", "schuljahr": "2027/28"})
        self.assertEqual(r.status, 400)
        self.assertIn("gibt es schon", html)

    def test_ausfall_doppelklick(self):
        """Die zweite Anfrage ändert nichts und zeigt dieselbe Seite wie die erste, nicht „Nicht gefunden“."""
        frei = self.mit_plan()
        self.reihe("A", anzahl=2)
        felder = {"termin": frei[0], "folge": "nachruecken"}
        _, html = self.hole(f"/klasse/ethik-8/ausfall?termin={frei[0]}")
        self.assertIn('<script src="/statisch/einmal.js" defer></script>', html)
        self.assertRegex(html, r'<form [^>]*/ausfall"[^>]* data-einmal[ >]')
        ziel = self.ok("/klasse/ethik-8/ausfall", felder)
        danach = self.text()
        self.assertEqual(self.ok("/klasse/ethik-8/ausfall", felder), ziel)
        self.assertEqual(self.text(), danach)

    def test_ausfall_alt_nichts_geaendert(self):
        frei = self.mit_plan()
        self.reihe("A", anzahl=2)
        felder = {"termin": frei[0], "folge": "nachruecken"}
        self.ok("/klasse/ethik-8/ausfall", felder)
        with mock.patch.object(app.sp, "letzte", lambda *a: []):
            r, _ = self.post("/klasse/ethik-8/ausfall", felder)
        self.assertEqual((r.status, r.getheader("location")), (303, "/klasse/ethik-8?erledigt=nichts#termine"))

    def test_ausfall_gleichzeitig(self):
        frei = self.mit_plan()
        self.reihe("A", anzahl=2)
        felder = {"termin": frei[0], "folge": "nachruecken"}
        antworten = []
        faeden = [threading.Thread(target=lambda: antworten.append(self.post("/klasse/ethik-8/ausfall", felder)[0]))
                  for _ in range(2)]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join()
        self.assertEqual([r.status for r in antworten], [303, 303])
        self.assertEqual(self.text().count(frei[0]), 1)

    def test_ausfall_zusatztermin(self):
        """Lia-Test Aufgabe 4 und Plan 2a.3: „Alles rückt nach“ (alle späteren Stunden der Klasse einen Termin weiter,
        über Reihengrenzen) bzw. „Diese Stunde fällt weg“; Rückgängig stellt alle Daten her."""
        frei = self.mit_plan()
        a = self.reihe("A", anzahl=2)
        b = self.reihe("B", anzahl=2)
        vorher = self.text()
        _, html = self.hole("/klasse/ethik-8")
        self.assertIn(f'href="/klasse/ethik-8/ausfall?termin={frei[0]}">fällt aus</a>', html)
        _, html = self.hole(f"/klasse/ethik-8/ausfall?termin={frei[0]}")
        self.assertIn("Alles rückt nach", html)
        self.assertIn("Diese Stunde fällt weg", html)
        self.assertEqual(self.hole("/klasse/ethik-8/ausfall?termin=2026-10-31/3")[0].status, 404)
        r, html = self.post("/klasse/ethik-8/ausfall", {"termin": frei[0]})
        self.assertEqual(r.status, 400)
        self.assertIn("Bitte wählen", html)
        ziel = self.ok("/klasse/ethik-8/ausfall", {"termin": frei[0], "folge": "nachruecken"})
        s = self.s()
        self.assertEqual([x["termin"] for x in s.reihe(a["id"])["stunden"] + s.reihe(b["id"])["stunden"]], frei[1:5])
        self.assertEqual([x["id"] for x in s.reihe(a["id"])["stunden"]], [x["id"] for x in a["stunden"]])
        self.assertIn("fällt aus, alles rückt nach", self.seite(ziel))
        self.post("/rueckgaengig", {"aktion": AKTION.search(ziel)[1], "zurueck": "/klasse/ethik-8"})
        self.assertEqual(self.text(), vorher)
        self.ok("/klasse/ethik-8/ausfall", {"termin": frei[1], "folge": "faellt_weg"})
        s = self.s()
        self.assertEqual(len(s.reihe(a["id"])["stunden"]), 1)
        self.assertEqual(s.reihe(b["id"])["stunden"][0]["termin"], frei[2])
        _, html = self.hole(f"/reihe/{a['id']}")
        self.assertIn("Ausgeblendete Stunden", html)
        self.assertIn(f'action="/objekt/{a["stunden"][1]["id"]}/wiederherstellen"', html)
        _, html = self.hole("/klasse/ethik-8")
        self.assertIn("findet doch statt", html)
        self.ok("/klasse/ethik-8/ausfall-aufheben", {"termin": frei[1]})
        self.assertNotIn(frei[1], self.s().objekt("ethik-8")["ausfall"])
        # freier Termin: nur streichen; Zusatztermin dazu und weg
        self.assertIn("Termin streichen", self.hole(f"/klasse/ethik-8/ausfall?termin={frei[6]}")[1])
        self.ok("/klasse/ethik-8/ausfall", {"termin": frei[6]})
        self.assertIn(frei[6], self.s().objekt("ethik-8")["ausfall"])
        self.ok("/klasse/ethik-8/zusatztermin", {"datum": "2026-12-02", "stunde": "5"})
        self.assertEqual(self.s().objekt("ethik-8")["zusatz"], ["2026-12-02/5"])
        self.assertIn("Zusatztermin", self.hole("/klasse/ethik-8")[1])
        self.ok("/klasse/ethik-8/zusatztermin-entfernen", {"termin": "2026-12-02/5"})
        self.assertEqual(self.s().objekt("ethik-8")["zusatz"], [])
        r, html = self.post("/klasse/ethik-8/zusatztermin", {"datum": "", "stunde": "5"})
        self.assertEqual(r.status, 400)
        self.assertIn("Datum und Stunde", html)

    def test_archivieren_mit_rueckfrage(self):
        r, html = self.post("/objekt/ethik-8/archivieren", {})
        self.assertEqual(r.status, 200)
        self.assertIn("Klasse 8 archivieren?", html)
        self.assertIn("Dazu gehören 2 Reihen.", html)
        self.assertIn('name="bestaetigt" value="1"', html)
        self.assertFalse(self.s().objekt("ethik-8")["archiviert"])
        self.ok("/objekt/ethik-8/archivieren", {"bestaetigt": "1"})
        self.assertTrue(self.s().reihe(STRAFE)["im_archiv"])
        _, html = self.hole("/")
        self.assertIn("Archiv: Klasse 8 · 2026/27", html)
        self.ok("/objekt/ethik-8/wiederherstellen", {})
        self.assertEqual(self.text(), ECHT)


class TestReihe(Pflege):
    def test_anlegen_mit_terminen_regel_32(self):
        """Testregel 32: Reihe mit zugeteilten Terminen ist eine Aktion, ein Rückgängig."""
        frei = self.mit_plan()
        vorher, aktionen = self.text(), len(self.letzte())
        _, html = self.hole("/klasse/ethik-8/reihe/neu")
        for text in ('name="titel"', 'name="anzahl"', 'name="termin"', 'name="ohne"', termine.anzeige(frei[0]),
                     "Stunden ohne Termin"):
            self.assertIn(text, html)
        self.assertNotIn("Je Termin entsteht", html)  # umbauplan-ux.md Schritt 7
        r, html = self.post("/klasse/ethik-8/reihe/neu", {"titel": " "})
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.PFLICHT["reihe"], html)
        ziel = self.ok("/klasse/ethik-8/reihe/neu", {"titel": "Würde", "anzahl": "6", "ab": frei[2][:10], "ohne": "1"})
        r = self.s().reihe("ethik-8-wuerde")
        self.assertTrue(ziel.startswith("/reihe/ethik-8-wuerde?aktion="))
        self.assertEqual([s["termin"] for s in r["stunden"]], frei[2:8])  # die Stunde ohne Termin bekommt den ersten
        self.assertEqual(len(self.letzte()), aktionen + 1)
        _, html = self.hole(ziel)
        self.assertIn("Reihe „Würde“ in Ethik 8 (2026/27) angelegt", html)
        self.assertIn(app.logik.termin_kurz(frei[2]), html)
        self.post("/rueckgaengig", {"aktion": AKTION.search(ziel)[1], "zurueck": "/reihe/ethik-8-wuerde"})
        self.assertEqual(self.text(), vorher)
        # einzeln angehakt; ohne Stundenplan nur Stunden ohne Termin
        self.ok("/klasse/ethik-8/reihe/neu", {"titel": "Würde", "termin": [frei[1], frei[3]]})
        self.assertEqual([s["termin"] for s in self.s().reihe("ethik-8-wuerde")["stunden"]], [frei[1], frei[3]])
        # ohne Stundenplan: nur die Zahl der Stunden, ohne Erklärsatz (umbauplan-ux.md Schritt 7)
        _, html = self.hole("/klasse/darstellendes-spiel-kurs-11/reihe/neu")
        self.assertIn('<label for="ohne">Stunden</label>', html)
        self.assertIn('id="ohne" type="number" name="ohne"', html)
        self.assertIn('placeholder="z. B. 6"', html)  # Browser-Probe 11.11.: sonst muss man raten, was hinein gehört
        for text in ("noch keine freien Termine", "Stunden ohne Termin", 'name="anzahl"'):
            self.assertNotIn(text, html)
        self.ok("/klasse/darstellendes-spiel-kurs-11/reihe/neu", {"titel": "Körper", "ohne": "3"})
        r = self.s().reihe("darstellendes-spiel-kurs-11-koerper")
        self.assertEqual([(s["termin"], s["thema"]) for s in r["stunden"]], [("", "")] * 3)
        self.assertIn("Thema offen", self.hole("/reihe/darstellendes-spiel-kurs-11-koerper")[1])

    def test_bearbeiten_nur_geaenderte_felder(self):
        """Plan 7.2.4: Lia ändert den Titel, Jan hat inzwischen die Notizen geändert; Jans Änderung bleibt. Ändert
        Lia dasselbe Feld, das Jan geändert hat: neu laden."""
        _, html = self.hole(f"/reihe/{STRAFE}/bearbeiten")
        self.assertIn('<option value="geplant" selected>In Planung</option>', html)
        self.assertIn("Peter Singer\nAristoteles", html)
        r = self.s().reihe(STRAFE)
        felder = {"titel": "Strafe", "reihenfrage": "", "stand": "geplant", "notizen": r["notizen"],
                  "behandelt": "\n".join(r["behandelt"]), "merksaetze": ""}
        alt = {f"alt_{k}": v for k, v in felder.items()}
        alt["alt_titel"] = "Straftheorien"
        self.datei.write_text(self.text().replace("Lia sucht noch nach einer guten.", "Jan war hier."),
                              encoding="utf-8")
        ziel = self.ok(f"/reihe/{STRAFE}/bearbeiten", {**felder, **alt})
        r2 = self.s().reihe(STRAFE)
        self.assertEqual(r2["titel"], "Strafe")
        self.assertTrue(r2["notizen"].endswith("Jan war hier."))
        self.assertIn("(jetzt „Strafe“)", self.hole(ziel)[1])
        r, html = self.post(f"/reihe/{STRAFE}/bearbeiten", {**felder, **alt, "titel": "Strafe", "alt_titel": "Strafe",
                                                            "notizen": "Lias Text"})
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.NEU_LADEN, html)
        r, html = self.post(f"/reihe/{STRAFE}/bearbeiten", {**felder, **alt, "titel": "", "alt_titel": "Strafe"})
        self.assertEqual(r.status, 400)
        self.assertIn(pflege.PFLICHT["reihe"], html)
        self.ok(f"/reihe/{STRAFE}/bearbeiten", {**felder, **alt, "titel": "Strafe", "alt_titel": "Strafe",
                                                "notizen": r2["notizen"], "alt_notizen": r2["notizen"], "stand": "laufend",
                                                "merksaetze": "A\nB"})
        self.assertEqual((self.s().reihe(STRAFE)["stand"], self.s().reihe(STRAFE)["merksaetze"]), ("laufend", ["A", "B"]))

    def test_titel_direkt(self):
        """umbauplan-ux.md Schritt 4: Titel anklicken, umbenennen. Eigene Routen nur für Titel bzw. Namen; Jans
        Änderung an anderen Feldern bleibt, gleichzeitig geänderter Titel: neu laden."""
        _, html = self.hole(f"/reihe/{STRAFE}")
        self.assertIn('<h1 class="titel-gross" data-direkt-titel>Straftheorien</h1>', html)
        self.assertIn(f'action="/reihe/{STRAFE}/titel"', html)
        self.assertIn('<input type="hidden" name="alt_titel" value="Straftheorien">', html)
        self.datei.write_text(self.text().replace("Lia sucht noch nach einer guten.", "Jan war hier."),
                              encoding="utf-8")
        ziel = self.ok(f"/reihe/{STRAFE}/titel", {"titel": " Strafe ", "alt_titel": "Straftheorien"})
        self.assertTrue(ziel.startswith(f"/reihe/{STRAFE}?aktion="))
        r = self.s().reihe(STRAFE)
        self.assertEqual(r["titel"], "Strafe")
        self.assertTrue(r["notizen"].endswith("Jan war hier."))
        self.assertIn("(jetzt „Strafe“)", self.hole(ziel)[1])
        r_, _ = self.post(f"/reihe/{STRAFE}/titel", {"titel": "Strafe", "alt_titel": "Strafe"})
        self.assertEqual(r_.getheader("location"), f"/reihe/{STRAFE}?erledigt=nichts")
        r_, html = self.post(f"/reihe/{STRAFE}/titel", {"titel": "", "alt_titel": "Strafe"})
        self.assertEqual(r_.status, 400)
        self.assertIn(pflege.PFLICHT["reihe"], html)
        self.assertIn(f'href="/reihe/{STRAFE}"', html)  # Weg zurück
        r_, html = self.post(f"/reihe/{STRAFE}/titel", {"titel": "Noch anders", "alt_titel": "Straftheorien"})
        self.assertEqual(r_.status, 400)  # Titel ist inzwischen ein anderer
        self.assertIn(pflege.NEU_LADEN, html)
        self.assertEqual(self.s().reihe(STRAFE)["titel"], "Strafe")
        # Klasse: das Feld ist der Name („8“), angezeigt wird „Klasse 8“
        _, html = self.hole("/klasse/ethik-8")
        self.assertIn('<h1 class="titel-gross" data-direkt-titel>Klasse 8</h1>', html)
        self.assertIn('name="name" type="text" value="8"', html)
        self.ok("/klasse/ethik-8/titel", {"name": "8a", "alt_name": "8"})
        self.assertEqual(self.s().objekt("ethik-8")["name"], "8a")
        self.assertEqual(self.post("/klasse/gibt-es-nicht/titel", {"name": "x", "alt_name": ""})[0].status, 404)
        self.assertEqual(self.post(f"/klasse/{STRAFE}/titel", {"name": "x", "alt_name": ""})[0].status, 404)
        # Stunde: dasselbe Formular wie „Thema und Marke“, mit der Marke unverändert
        self.ok(f"/reihe/{STRAFE}/stunden", {"thema": "Kant"})
        sid = self.s().reihe(STRAFE)["stunden"][0]["id"]
        self.ok(f"/stunde/{sid}/aendern", {"thema": "Kant", "marke": "Prüfung", "alt_thema": "Kant", "alt_marke": ""})
        _, html = self.hole(f"/reihe/{STRAFE}/stunde/1")
        kopf = html.split('<header class="kopf">')[1].split("</header>")[0]
        for teil in ("data-direkt-titel>Kant</h1>", f'action="/stunde/{sid}/aendern"',
                     '<input type="hidden" name="marke" value="Prüfung">', 'name="thema" type="text" value="Kant"'):
            self.assertIn(teil, kopf)
        self.ok(f"/stunde/{sid}/aendern", {"thema": "Kant und Hegel", "marke": "Prüfung", "alt_thema": "Kant",
                                           "alt_marke": "Prüfung"})
        self.assertEqual((self.s().objekt(sid)["thema"], self.s().objekt(sid)["marke"]), ("Kant und Hegel", "Prüfung"))
        # im Archiv: kein Umbenennen am Titel
        self.ok(f"/objekt/{STRAFE}/archivieren", {})
        for pfad in (f"/reihe/{STRAFE}", f"/reihe/{STRAFE}/stunde/1"):
            self.assertNotIn("data-direkt-titel", self.hole(pfad)[1], pfad)

    def test_kopieren_und_verschieben(self):
        """Lia-Test Aufgabe 2: Freundschaft aus der 7 vom letzten Jahr in die neue 9, in die ersten sechs Termine;
        das Original bleibt im Archiv."""
        self.ok("/schule", {"bundesland": "BE"})
        self.ok("/fach/ethik/klasse/neu", {"name": "9", "schuljahr": "2026/27", "zeilen": "2", "tag-0": "Di",
                                           "stunde-0": "3", "ab": "2027-02-01"})
        _, html = self.hole("/reihe/ethik-7-freundschaft/kopieren")
        self.assertIn('<option value="ethik-9">Ethik · Klasse 9 (2026/27)</option>', html)
        self.assertNotIn('value="ethik-7-2025-26"', html.split('id="klasse"')[1])  # nicht ins Archiv
        _, html = self.hole("/reihe/ethik-7-freundschaft/kopieren?klasse=ethik-9")
        self.assertIn("Nach Ethik · Klasse 9 (2026/27)", html)
        erste = self.termine_von("ethik-9")
        ziel = self.ok("/reihe/ethik-7-freundschaft/kopieren", {"klasse": "ethik-9", "anzahl": "6",
                                                                "ab": erste[0][:10]})
        neu = self.s().reihe("ethik-9-freundschaft")
        self.assertTrue(ziel.startswith("/reihe/ethik-9-freundschaft?aktion="))
        self.assertEqual(([s["termin"] for s in neu["stunden"]], neu["herkunft"], neu["stand"], neu["im_archiv"]),
                         (erste[:6], "ethik-7-freundschaft", "geplant", False))
        alt = self.s().reihe("ethik-7-freundschaft")
        self.assertTrue(alt["im_archiv"])
        self.assertEqual(alt["klasse_id"], "ethik-7-2025-26")
        # in eine andere Klasse verschieben (auch ins Archiv), Stunden gehen mit
        self.ok(f"/reihe/{WAHNSINN}/verschieben", {"klasse": "darstellendes-spiel-kurs-11"})
        self.assertEqual(self.s().reihe(WAHNSINN)["klasse"], "Kurs 11")
        r, html = self.post(f"/reihe/{WAHNSINN}/verschieben", {"klasse": "darstellendes-spiel-kurs-11"})
        self.assertEqual(r.status, 400)
        self.assertIn("Die Reihe gehört schon zu dieser Klasse.", html)

    def test_termine_zuteilen_und_freigeben(self):
        frei = self.mit_plan()
        r = self.reihe("Würde", anzahl=2)
        _, html = self.hole(f"/reihe/{r['id']}/termine")
        self.assertIn("Freie Termine dazunehmen", html)
        self.assertIn("Termine abgeben", html)
        self.ok(f"/reihe/{r['id']}/termine", {"was": "zuteilen", "termin": [frei[5]]})
        self.assertEqual([s["termin"] for s in self.s().reihe(r["id"])["stunden"]], [frei[0], frei[1], frei[5]])
        self.ok(f"/reihe/{r['id']}/termine", {"was": "freigeben", "frei": [frei[1]]})
        self.assertEqual([s["termin"] for s in self.s().reihe(r["id"])["stunden"]], [frei[0], frei[5]])
        r2, html = self.post(f"/reihe/{r['id']}/termine", {"was": "zuteilen"})
        self.assertEqual(r2.status, 400)
        self.assertIn("Bitte Termine anhaken", html)

    def test_termine_in_der_rechten_spalte(self):
        """umbauplan-ux.md Schritt 5: Termine stehen rechts; an der Klasse mit „fällt aus“ und Sprungziel #termine,
        an der Reihe als Daten der Stunden (je ein Link), an der Stunde ihr Termin mit Stunde."""
        frei = self.mit_plan()
        r = self.reihe("Würde", anzahl=2)
        def teile(pfad):
            html = self.hole(pfad)[1]
            rechts = html.split('<aside class="rechts" aria-label="')[1].split("</aside>")[0]
            return html.split('<nav class="baum"')[0], rechts
        mitte, rechts = teile("/klasse/ethik-8")
        self.assertIn('<section aria-labelledby="ab2" id="termine">', rechts)
        self.assertIn("Stundenplan: Di 3. Std.", rechts)
        self.assertIn(f'href="/klasse/ethik-8/ausfall?termin={frei[0]}">fällt aus</a>', rechts)
        self.assertNotIn('id="termine"', mitte)
        mitte, rechts = teile(f"/reihe/{r['id']}")
        tage = [app.logik.termin_kurz(k) for k in frei[:2]]
        self.assertIn(f'<a href="/reihe/{r["id"]}/stunde/1" title="Stunde 1: Thema offen">{tage[0]}</a>, '
                      f'<a href="/reihe/{r["id"]}/stunde/2"', rechts)
        self.assertIn('<h2 id="ab-termine">Termine</h2>', rechts)
        _, rechts = teile(f"/reihe/{r['id']}/stunde/2")
        self.assertIn(f"<p>{termine.anzeige(frei[1])}</p>", rechts)

    def test_zeitlich_verschieben_regel_33(self):
        """Testregel 33: Die Reihe beginnt an einem belegten Termin; einmal fragen, dann „nachrücken“ (die getroffene
        Reihe rückt dahinter) oder „tauschen“; ids, Themen, Material bleiben; Rückgängig stellt alles her."""
        frei = self.mit_plan()
        a = self.reihe("A", anzahl=3)
        b = self.reihe("B", anzahl=2)
        self.ok(f"/stunde/{b['stunden'][0]['id']}/aendern", {"thema": "Würde", "alt_thema": ""})
        z = app.zustand_()
        z.schreiben(app.logik.stunde_zuordnen(z.lesen(), "20261030-140944-unterricht-93e29e", b["stunden"][0]["id"]))
        vorher = self.text()
        _, html = self.hole(f"/reihe/{b['id']}")
        self.assertIn(f'<option value="{frei[3]}" selected>', html)  # beginnt heute dort
        r, html = self.post(f"/reihe/{b['id']}/zeitlich", {"start": frei[1]})
        self.assertEqual(r.status, 200)
        for text in ("Der Termin ist belegt", "Dort liegt schon", "Dahinter alles nachrücken", "Tauschen",
                     f'name="start" value="{frei[1]}"'):
            self.assertIn(text, html)
        self.assertEqual(self.text(), vorher)  # Rückfrage schreibt nichts
        ziel = self.ok(f"/reihe/{b['id']}/zeitlich", {"start": frei[1], "bei_belegt": "nachruecken"})
        s = self.s()
        self.assertEqual([x["termin"] for x in s.reihe(b["id"])["stunden"]], frei[1:3])
        self.assertEqual([x["termin"] for x in s.reihe(a["id"])["stunden"]], [frei[0], frei[3], frei[4]])
        self.assertEqual([(x["id"], x["thema"]) for x in s.reihe(b["id"])["stunden"]],
                         [(b["stunden"][0]["id"], "Würde"), (b["stunden"][1]["id"], "")])
        self.assertEqual(app.zustand_().lesen()["stunde_von"]["20261030-140944-unterricht-93e29e"],
                         {"stunde": b["stunden"][0]["id"]})
        self.post("/rueckgaengig", {"aktion": AKTION.search(ziel)[1], "zurueck": f"/reihe/{b['id']}"})
        self.assertEqual(self.text(), vorher)
        self.ok(f"/reihe/{b['id']}/zeitlich", {"start": frei[0], "bei_belegt": "tauschen"})
        s = self.s()
        self.assertEqual([x["termin"] for x in s.reihe(b["id"])["stunden"]], frei[0:2])
        self.assertEqual([x["termin"] for x in s.reihe(a["id"])["stunden"]], frei[2:5])


class TestStunde(Pflege):
    def test_verschieben_regel_34_und_7(self):
        """Lia-Test Aufgabe 3 (von Liszt vor Kant): der Inhalt wandert, die Termine bleiben, das Material folgt der
        Stunde (Testregel 7). Testregel 34: Stunde auf einen freien Termin in einer Lücke, nur sie ändert ihr Datum."""
        frei = self.mit_plan()
        r = self.reihe("Strafe", anzahl=3)
        ids = [s["id"] for s in r["stunden"]]
        for sid, thema in zip(ids, ("Einstieg", "Kant", "von Liszt"), strict=True):
            self.ok(f"/stunde/{sid}/aendern", {"thema": thema, "alt_thema": ""})
        self.material_an(ids[1], r["id"])
        _, html = self.hole(f"/reihe/{r['id']}")
        for text in ('draggable="true"', "ziehen.js", f'<option value="vor:{ids[1]}">vor Stunde 2: Kant</option>',
                     '<optgroup label="Auf einen Termin">', '<optgroup label="In eine andere Reihe">'):
            self.assertIn(text, html)
        ziel = self.ok("/stunden/verschieben", {"stunde": ids[2], "ziel": f"vor:{ids[1]}"})
        self.assertTrue(ziel.startswith(f"/reihe/{r['id']}?aktion=") and ziel.endswith("#stunden"))
        s = self.s().reihe(r["id"])
        self.assertEqual([(x["nr"], x["thema"], x["termin"]) for x in s["stunden"]],
                         [(1, "Einstieg", frei[0]), (2, "von Liszt", frei[1]), (3, "Kant", frei[2])])
        _, html = self.hole(f"/reihe/{r['id']}/stunde/3")
        self.assertIn("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", html)  # das Material ist mit Kant gewandert
        # Testregel 34: Kant auf den freien Termin frei[4] (Lücke), aus der Stunden-Ansicht
        vorher = {x["id"]: x["termin"] for x in s["stunden"]}
        ziel = self.ok("/stunden/verschieben", {"stunde": ids[1], "ziel": f"termin:{frei[4]}", "von": "stunde"})
        self.assertTrue(ziel.startswith(f"/reihe/{r['id']}/stunde/3?aktion="))
        nachher = {x["id"]: x["termin"] for x in self.s().reihe(r["id"])["stunden"]}
        self.assertEqual({k: v for k, v in nachher.items() if v != vorher[k]}, {ids[1]: frei[4]})
        # belegter Termin: einmal fragen
        r2, html = self.post("/stunden/verschieben", {"stunde": ids[1], "ziel": f"termin:{frei[0]}"})
        self.assertEqual(r2.status, 200)
        self.assertIn("„Einstieg“ (Strafe)", html)
        self.ok("/stunden/verschieben", {"stunde": ids[1], "ziel": f"termin:{frei[0]}", "bei_belegt": "tauschen"})
        self.assertEqual(self.s().objekt(ids[0])["termin"], frei[4])
        # in eine andere Reihe (ans Ende rechnet pflege.stelle, test_pflege.py)
        self.ok("/stunden/verschieben", {"stunde": ids[0], "ziel": f"reihe:{STRAFE}"})
        self.assertEqual([x["id"] for x in self.s().reihe(STRAFE)["stunden"]], [ids[0]])
        r3, html = self.post("/stunden/verschieben", {"stunde": ids[1], "ziel": "quatsch"})
        self.assertEqual(r3.status, 400)
        self.assertEqual(self.post("/stunden/verschieben", {"stunde": "s-gibtsnicht", "ziel": "ende"})[0].status, 404)

    def test_aendern_kopieren_ausblenden_loeschen(self):
        r = self.reihe("Strafe")
        self.ok(f"/reihe/{r['id']}/stunden", {"thema": "Kant"})
        (st,) = self.s().reihe(r["id"])["stunden"]
        _, html = self.hole(f"/reihe/{r['id']}/stunde/1")
        for text in ('<option value="Prüfung">Prüfung</option>', "Verschieben nach", "Kopieren nach", "Ausblenden",
                     f'action="/objekt/{st["id"]}/loeschen"'):
            self.assertIn(text, html)
        ziel = self.ok(f"/stunde/{st['id']}/aendern", {"thema": "Kant", "alt_thema": "Kant", "marke": "Prüfung",
                                                       "alt_marke": ""})
        self.assertTrue(ziel.startswith(f"/reihe/{r['id']}/stunde/1?aktion="))
        self.assertEqual(self.s().objekt(st["id"])["marke"], "Prüfung")
        self.assertIn("Stunde 1 · Prüfung", self.hole(f"/reihe/{r['id']}/stunde/1")[1])
        r2, html = self.post(f"/stunde/{st['id']}/aendern", {"thema": "x" * 121, "alt_thema": "Kant"})
        self.assertEqual(r2.status, 400)
        self.assertIn("Das Thema ist zu lang (höchstens 120 Zeichen).", html)
        self.ok(f"/stunde/{st['id']}/kopieren", {"reihe": STRAFE})
        self.assertEqual([(x["thema"], x["marke"]) for x in self.s().reihe(STRAFE)["stunden"]], [("Kant", "")])
        # Material hängt dran: kein Löschen, Ausblenden geht; Material bleibt bei der ausgeblendeten Stunde
        self.material_an(st["id"], r["id"])
        _, html = self.hole(f"/reihe/{r['id']}/stunde/1")
        self.assertIn("Löschen geht nicht, daran hängt: Prüfungsstunde, 1 Zuordnung in der Web-App.",
                      html)
        r3, html = self.post(f"/objekt/{st['id']}/loeschen", {})
        self.assertEqual(r3.status, 400)
        self.assertIn("Löschen geht nicht, weil noch etwas daran hängt", html)
        ziel = self.ok(f"/objekt/{st['id']}/archivieren", {})
        self.assertTrue(ziel.startswith(f"/reihe/{r['id']}?aktion=") and ziel.endswith("#ausgeblendet"))
        html = self.seite(ziel)
        self.assertIn("ausgeblendet", html)
        teil = html.split("Ausgeblendete Stunden")[1]
        self.assertIn("Arbeitsblatt &lt;Kant&gt; &amp; Strafe", teil)
        self.assertNotIn("Arbeitsblatt &lt;Kant&gt;", html.split("Ausgeblendete Stunden")[0])
        self.assertNotIn("Zur ganzen Reihe", html)  # leer, fällt weg (umbauplan-ux.md Schritt 2)
        self.ok(f"/objekt/{st['id']}/wiederherstellen", {})
        self.assertEqual(self.s().objekt(st["id"])["nr"], 1)
        # leere Stunde: Löschen geht
        self.ok(f"/reihe/{r['id']}/stunden", {"thema": ""})
        leer = self.s().reihe(r["id"])["stunden"][1]["id"]
        self.ok(f"/objekt/{leer}/loeschen", {})
        self.assertIsNone(self.s().objekt(leer))

    def test_reihe_archivieren_und_wiederherstellen(self):
        """Lia-Test Aufgaben 5 und 6, Abnahme „Wiederherstellungsprobe“: Reihe mit Material archivieren, ohne
        Rückfrage; wiederherstellen: Datei byte-gleich, Material am selben Ort, Aufträge byte-gleich."""
        schreibe(self.instanz / "auftraege" / "erledigt" / "20261030-150000-theater-dddddd.json", {
            "id": "20261030-150000-theater-dddddd", "agent": "theater", "text": "Spielfassung Akt 1",
            "status": "erledigt", "erstellt": "2026-10-30T15:00:00+01:00",
            "abgeschlossen": "2026-10-30T15:30:00+01:00", "ergebnis": "Fassung", "ergebnis_dateien": []})

        def pruefsummen():
            return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((self.instanz / "auftraege").rglob("*.json"))}
        summen = pruefsummen()
        self.assertIn("Spielfassung Akt 1", self.hole(f"/reihe/{WAHNSINN}")[1])
        ziel = self.ok(f"/objekt/{WAHNSINN}/archivieren", {})
        self.assertTrue(ziel.startswith(f"/reihe/{WAHNSINN}?aktion="))
        _, html = self.hole(ziel)
        self.assertIn("Reihe „Der nackte Wahnsinn“ in Darstellendes Spiel Kurs 12 (2026/27) archiviert", html)
        self.assertIn("Wiederherstellen", html)
        self.assertIn("Spielfassung Akt 1", html)
        self.assertNotIn(f'href="/reihe/{WAHNSINN}"><span>', self.hole("/")[1])  # aus der Übersicht
        _, html = self.hole("/klasse/darstellendes-spiel-kurs-12")
        self.assertIn('<span class="marke">Archiv</span>', html)
        self.ok(f"/objekt/{WAHNSINN}/wiederherstellen", {})
        self.assertEqual(self.text(), ECHT)
        self.assertEqual(pruefsummen(), summen)
        self.assertIn(f'href="/reihe/{WAHNSINN}"><span>', self.hole("/")[1])


class TestRueckgaengig(Pflege):
    def test_hinweis_und_letzte_aenderungen(self):
        ziel = self.ok(f"/reihe/{STRAFE}/stunden", {"thema": "Einstieg"})
        aktion = AKTION.search(ziel)[1]
        html = self.seite(ziel)
        for text in ('class="hinweis hinweis-erledigt aktion-hinweis"', "Stunde „Einstieg“ in „Straftheorien“ angelegt",
                     f'name="aktion" value="{aktion}"', 'name="zurueck" value="/reihe/ethik-8-straftheorien"'):
            self.assertIn(text, html)
        _, html = self.hole("/ich")
        self.assertIn("Letzte Änderungen", html)
        self.assertIn("Stunde „Einstieg“ in „Straftheorien“ angelegt", html)
        r, _ = self.post("/rueckgaengig", {"aktion": aktion, "zurueck": f"/reihe/{STRAFE}/stunde/1"})
        self.assertTrue(r.getheader("location").startswith(f"/reihe/{STRAFE}?aktion="))  # die Stunde gibt es nicht mehr
        self.assertEqual(self.text(), ECHT)
        _, html = self.hole("/ich")
        self.assertIn("Zurückgenommen: Stunde „Einstieg“ in „Straftheorien“ angelegt", html)
        self.assertIn("zurückgenommen", html)
        r, html = self.post("/rueckgaengig", {"aktion": aktion, "zurueck": "/ich"})
        self.assertEqual(r.status, 409)
        self.assertIn("Diese Änderung ist schon rückgängig gemacht.", html)
        # Jan hat den Block inzwischen geändert: Rückgängig geht nicht, nichts geschrieben
        ziel = self.ok(f"/reihe/{STRAFE}/stunden", {"thema": "Kant"})
        self.datei.write_text(self.text().replace('thema = "Kant"', 'thema = "Kant (Jan)"'), encoding="utf-8")
        vorher = self.text()
        r, html = self.post("/rueckgaengig", {"aktion": AKTION.search(ziel)[1], "zurueck": "/ich"})
        self.assertEqual(r.status, 409)
        self.assertIn("inzwischen etwas geändert", html)
        self.assertEqual(self.text(), vorher)
        self.assertEqual(self.post("/rueckgaengig", {"aktion": "../x", "zurueck": "/ich"})[0].status, 409)

    def test_schule_unter_ich(self):
        _, html = self.hole("/ich")
        self.assertIn('<option value="">–</option>', html.split('id="bundesland"')[1])
        ziel = self.ok("/schule", {"bundesland": "BE"})
        self.assertTrue(ziel.startswith("/ich?aktion=") and ziel.endswith("#schule"))
        self.assertIn('<option value="BE" selected>Berlin</option>', self.hole("/ich")[1])
        r, _ = self.post("/schule", {"bundesland": "XX"})
        self.assertEqual(r.status, 400)


class TestSchutz(Pflege):
    def test_regel_25_token_und_herkunft(self):
        """Testregel 25: Jede schreibende Maske nur mit Formular-Token und passendem Origin; sonst wird nichts
        geschrieben."""
        self.mit_berlin()
        st = self.ok(f"/reihe/{STRAFE}/stunden", {"thema": "Kant"})
        sid = self.s().reihe(STRAFE)["stunden"][0]["id"]
        self.assertTrue(st)
        vorher, aktionen = self.text(), len(self.letzte())
        routen = [
            ("/fach/neu", {"name": "Mathe"}), ("/fach/ethik/bearbeiten", {"name": "X", "alt_name": "Ethik"}),
            ("/fach/ethik/klasse/neu", {"name": "10", "schuljahr": "2026/27"}),
            ("/klasse/ethik-8/bearbeiten", {"name": "X", "alt_name": "8", "schuljahr": "2026/27",
                                            "alt_schuljahr": "2026/27"}),
            ("/klasse/ethik-8/lerngruppe", {"lerngruppe": "x"}),
            ("/klasse/ethik-8/verschieben", {"fach": "darstellendes-spiel"}),
            ("/klasse/ethik-8/stundenplan", {"wie": "ganz", "zeilen": "2", "tag-0": "Di", "stunde-0": "3"}),
            ("/klasse/ethik-8/uebernehmen", {"name": "9", "schuljahr": "2027/28"}),
            ("/klasse/ethik-8/zusatztermin", {"datum": "2026-12-02", "stunde": "5"}),
            ("/klasse/ethik-8/reihe/neu", {"titel": "X"}),
            (f"/reihe/{STRAFE}/bearbeiten", {"titel": "X", "alt_titel": "Straftheorien"}),
            (f"/reihe/{STRAFE}/titel", {"titel": "X", "alt_titel": "Straftheorien"}),
            ("/klasse/ethik-8/titel", {"name": "X", "alt_name": "8"}),
            (f"/reihe/{STRAFE}/verschieben", {"klasse": "darstellendes-spiel-kurs-11"}),
            (f"/reihe/{STRAFE}/kopieren", {"klasse": "darstellendes-spiel-kurs-11"}),
            (f"/reihe/{STRAFE}/stunden", {"thema": "x"}), (f"/stunde/{sid}/aendern", {"thema": "x", "alt_thema": "Kant"}),
            ("/stunden/verschieben", {"stunde": sid, "ziel": f"reihe:{WAHNSINN}"}),
            (f"/stunde/{sid}/kopieren", {"reihe": WAHNSINN}), (f"/objekt/{STRAFE}/archivieren", {}),
            ("/objekt/ethik-8/archivieren", {"bestaetigt": "1"}), (f"/objekt/{sid}/loeschen", {}),
            ("/schule", {"bundesland": "BY"}), ("/rueckgaengig", {"aktion": self.letzte()[0]["id"]}),
        ]
        for pfad, felder in routen:
            with self.subTest(pfad=pfad):
                self.assertEqual(self.post(pfad, felder, origin="https://fremd.example")[0].status, 403)
                self.assertEqual(self.post(pfad, felder, origin="")[0].status, 403)
                r, html = self.post(pfad, felder, token=False)
                self.assertEqual(r.status, 400, html[-500:])
                self.assertIn("Die Seite war veraltet", html)
        self.assertEqual(self.text(), vorher)
        self.assertEqual(len(self.letzte()), aktionen)
        self.assertFalse((self.instanz / "lerngruppen.toml").exists())


class TestDiesesLog(Pflege):
    def test_kein_lerngruppen_text_im_log_bei_fehlern(self):
        """Auch abgewiesene Eingaben loggen nie den Text der Lerngruppe (Plan Abschnitt 6, Punkt 4)."""
        with self.assertLogs(level=logging.DEBUG) as logs:
            logging.getLogger("webapp").info("Start")
            r, _ = self.post("/klasse/ethik-8/lerngruppe", {"lerngruppe": "Geheim " * 600, "alt_lerngruppe": ""})
        self.assertEqual(r.status, 400)
        self.assertFalse([z for z in logs.output if "Geheim" in z])


class TestStart(Pflege):
    def test_commits_beim_start_nachholen(self):
        """Beim Start stößt die App die Warteschlange der Commits an (agentkit, eigener Faden); ein Fehler dabei hält
        den Start nicht auf. Speichern selbst wartet nicht auf einen Commit."""
        async def starten():
            async with app.lebenslauf(app.app):
                pass
        with mock.patch.object(app.sp, "anstossen") as anstossen:
            asyncio.run(starten())
        (aufruf,) = anstossen.call_args_list
        u = aufruf.args[0]
        self.assertEqual((u.instanz, u.webapp_daten, u.hintergrund), (self.instanz, self.tmp / "webdaten", True))
        with mock.patch.object(app.sp, "anstossen", side_effect=OSError("kaputt")), \
                self.assertLogs("webapp", level="ERROR") as logs:
            asyncio.run(starten())
        self.assertIn("nicht angestoßen", logs.output[0])
