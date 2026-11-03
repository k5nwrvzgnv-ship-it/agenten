"""ordnung.laden über agentkit.struktur (Strukturplan Bauschritt 2): gleiche Ansichten wie vorher für die echte
Datei, neues Format, Testregeln 7 und 22 aus Abschnitt 10 (lesend)."""

import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import logik
import ordnung

DATEN = Path(__file__).parent / "daten"
JETZT = datetime(2026, 10, 30, 15, 0, tzinfo=ZoneInfo("Europe/Berlin"))
STUNDEN = [{"id": "s-1", "thema": "Einstieg"}, {"id": "s-2", "thema": "Kant", "marke": "UB"}]


def bild(reihen: list[dict], gruppen: list[dict] | None = None) -> dict:
    """Was Lia von der Struktur sieht: Baum, Brotkrumen, Klassen-, Fach- und Reihen-Ansicht, Auswahl in „Neu“.
    Mit dem Code vor der Umstellung (ordnung.laden mit eigener Prüfung, Commit 5ce91c0) für reihen_alt.toml
    erzeugt und in daten/ansicht_vorher.json eingefroren."""
    gids = list(dict.fromkeys(r["gruppe_id"] for r in reihen))
    fids = list(dict.fromkeys(r["fach_id"] for r in reihen))
    zeilen_je = {"ethik-8-straftheorien": [{}, {}], "ethik-7-freundschaft": [{}]}
    aktive = ["heute", ""] + [r["id"] for r in reihen] + [logik.klasse_aktiv(g) for g in gids] \
        + [logik.fach_aktiv(f) for f in fids]
    klassen = {g: logik.klasse_ansicht(g, reihen, zeilen_je, gruppen) for g in gids}
    for k in klassen.values():
        k.pop("gruppe", None)  # vorher stand hier die erste Reihe der Klasse (nur für krumen_klasse)
        k.pop("reihe", None)
    return {
        "baum": {a: logik.baum(reihen, 3, a, gruppen=gruppen) for a in aktive},
        "baum_stunde": logik.baum(reihen, 0, "ethik-8-straftheorien", {"ethik-8-straftheorien": STUNDEN}, 2,
                                  gruppen),
        "krumen": {r["id"]: [logik.krumen(reihe=r), logik.krumen("Neu", r), logik.krumen_klasse(r)] for r in reihen},
        "klasse": klassen,
        "fach": {f: logik.fach_ansicht(f, reihen, zeilen_je, gruppen) for f in fids},
        "auswahl": logik.reihen_auswahl(reihen),
        "texte": {r["id"]: [logik.reihe_text(r), logik.ort_text(r, (2, "Kant")), list(logik.stunden_wort(r)),
                            r["laufend"], logik.reihe_link(r), logik.klasse_link(r)] for r in reihen},
        "reihe_ansicht": {r["id"]: _wie_vorher(logik.reihe_ansicht(r, reihen, [], JETZT, stunden_=STUNDEN))
                          for r in reihen},
        "reihe_von": {a: (logik.reihe_von({"agent": a}, reihen) or {}).get("id")
                      for a in ("examen", "theater", "unterricht")},
    }


def _wie_vorher(a: dict) -> dict:
    """Reihen-Ansicht ohne das, was Bauschritt 5 bewusst geändert hat: „+ Stunde“ steht nicht mehr als Link in der
    Ansicht (das Formular kommt aus reihe_pflege), Stunden haben id und Datum, dazu „Ausgeblendete Stunden“."""
    a = {k: v for k, v in a.items() if k != "ausgeblendete"}
    a["stunden"] = [{k: v for k, v in s.items() if k not in ("id", "datum")} for s in a["stunden"]]
    return a


def baum_texte(reihen: list[dict], gruppen: list[dict], aktiv: str = "") -> list[str]:
    return [e["text"] for e in logik.baum(reihen, 0, aktiv, gruppen=gruppen)]


class Instanz(unittest.TestCase):
    def setUp(self):
        self.agenten = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.agenten)
        self.instanz = self.agenten / "instanz"
        self.instanz.mkdir()

    def schreiben(self, text: str) -> None:
        (self.instanz / "reihen.toml").write_text(text, encoding="utf-8")

    def laden(self, text: str) -> tuple[list[dict], list[dict]]:
        self.schreiben(text)
        reihen, gruppen, fehler = ordnung.laden(self.instanz)
        self.assertEqual(fehler, [])
        return reihen, gruppen


class TestLaden(Instanz):
    def test_ohne_datei_keine_reihen(self):
        self.assertEqual(ordnung.laden(self.instanz), ([], [], []))

    def test_ersatzweg_entfaellt(self):
        """Die Reihen stehen seit 30.10. in der Instanz; aus den Agent-Ordnern setzt die App nichts mehr zusammen."""
        (self.agenten / "unterricht").mkdir()
        (self.agenten / "unterricht" / "reihen.toml").write_text('[[reihe]]\nfach = "Ethik"\nklasse = "8"\n')
        self.assertEqual(ordnung.laden(self.instanz), ([], [], []))

    def test_kaputte_datei_meldet_und_zeigt_nichts(self):
        for text in ("[[reihe]\n", 'reihe = "x"\n', '[[reihe]]\nfach = "Ethik"\nklasse = "8"\nstand = "fertig"\n'):
            with self.subTest(text=text):
                self.schreiben(text)
                reihen, gruppen, fehler = ordnung.laden(self.instanz)
                self.assertEqual((reihen, gruppen), ([], []))
                self.assertIn("reihen.toml", fehler[0])

    def test_gleiche_ansicht_wie_vorher(self):
        """Die echte Datei (eingefrorene Kopie) sieht nach der Umstellung genau so aus wie vorher."""
        reihen, gruppen = self.laden((DATEN / "reihen_alt.toml").read_text(encoding="utf-8"))
        vorher = json.loads((DATEN / "ansicht_vorher.json").read_text(encoding="utf-8"))
        for k in vorher["klasse"].values():
            k.pop("reihe")
        for a in vorher["reihe_ansicht"].values():
            a.pop("stunden_neu")  # „+ Stunde“ kommt seit Bauschritt 5 aus reihe_pflege (app.py), siehe _wie_vorher
        jetzt = json.loads(json.dumps(bild(reihen, gruppen), ensure_ascii=False))
        for teil in vorher:
            with self.subTest(teil=teil):
                self.assertEqual(jetzt[teil], vorher[teil])

    def test_stunden_aus_der_datei_haben_ids(self):
        reihen, _ = self.laden('[[reihe]]\nid = "r"\nfach = "Ethik"\nklasse = "8"\n'
                               '[[reihe.stunde]]\nnr = 2\nthema = "Kant"\n[[reihe.stunde]]\nnr = 1\nthema = "Einstieg"\n')
        self.assertEqual([(s["id"], s["thema"]) for s in reihen[0]["stunden"]],
                         [("r-stunde-1", "Einstieg"), ("r-stunde-2", "Kant")])


class TestNeuesFormat(Instanz):
    def setUp(self):
        super().setUp()
        self.neu = (DATEN / "reihen_neu.toml").read_text(encoding="utf-8")

    def test_wie_das_alte_format(self):
        """Nach der Migration sieht Lia dasselbe; nur Kurs 11 hat keine Platzhalter-Reihe „Noch ohne Titel“ mehr."""
        alt_r, alt_g = self.laden((DATEN / "reihen_alt.toml").read_text(encoding="utf-8"))
        neu_r, neu_g = self.laden(self.neu)
        platzhalter = "darstellendes-spiel-kurs-11"
        self.assertEqual(sorted(g["gruppe_id"] for g in neu_g), sorted(g["gruppe_id"] for g in alt_g))
        for aktiv in ["heute", "ethik-8-straftheorien", "ethik-7-freundschaft", logik.klasse_aktiv(platzhalter)]:
            with self.subTest(aktiv=aktiv):
                erwartet = [e for e in logik.baum(alt_r, 0, aktiv, gruppen=alt_g)
                            if e.get("link") != f"/reihe/{platzhalter}"]
                self.assertEqual(logik.baum(neu_r, 0, aktiv, gruppen=neu_g), erwartet)
        # Brotkrumen und Auswahl nennen den Titel ohne „(in Planung)“, sonst gleich
        alt_b = json.loads(json.dumps(bild([r for r in alt_r if r["id"] != platzhalter], alt_g), ensure_ascii=False)
                           .replace("Straftheorien (in Planung)", "Straftheorien"))
        neu_b = bild(neu_r, neu_g)
        for teil in ("krumen", "auswahl", "reihe_von"):
            self.assertEqual(neu_b[teil], alt_b[teil])
        # „(in Planung)“ steht jetzt im Stand, nicht im Titel; Behandeltes wie vorher
        r = next(x for x in neu_r if x["id"] == "ethik-8-straftheorien")
        self.assertEqual((r["titel"], r["stand"], r["laufend"]), ("Straftheorien", "geplant", True))
        self.assertIn("Straftheorien (in Planung)", baum_texte(neu_r, neu_g))
        self.assertEqual(logik.reihe_ansicht(r, neu_r, [], JETZT)["unter"], "Ethik · Klasse 8 · in Planung")

    def test_leere_klasse(self):
        reihen, gruppen = self.laden(self.neu)
        e = logik.klasse_ansicht("darstellendes-spiel-kurs-11", reihen, {}, gruppen)
        self.assertEqual((e["titel"], e["zeilen"]), ("Kurs 11", []))
        self.assertEqual(logik.krumen_klasse(e["gruppe"])["hier"], "Kurs 11")
        f = logik.fach_ansicht("darstellendes-spiel", reihen, {}, gruppen)
        self.assertEqual([(z["titel"], z["hinweis"]) for z in f["zeilen"]], [
            ("Kurs 12", "1 Reihe · noch nichts"), ("Kurs 11", "0 Reihen · noch nichts"),
            ("Kurs 11 · 2025/26", "6 Reihen · noch nichts")])

    def test_archiv_ueber_im_archiv(self):
        """Im neuen Format gilt archiviert (auch geerbt), nicht mehr „schuljahr + abgeschlossen“."""
        text = self.neu.replace('name = "7"\nschuljahr = "2025/26"\narchiviert = "2026-08-01"\n',
                                'name = "7"\nschuljahr = "2025/26"\n')
        reihen, gruppen = self.laden(text)
        self.assertIn("Klasse 7", baum_texte(reihen, gruppen))  # abgeschlossen, aber nicht archiviert
        self.assertIn("Freundschaft (abgeschlossen)", baum_texte(reihen, gruppen))
        # einzeln archivierte Reihe einer laufenden Klasse: nur in der Klassen-Ansicht
        text = self.neu.replace('titel = "Der nackte Wahnsinn"\n', 'titel = "Der nackte Wahnsinn"\n'
                                'archiviert = "2026-11-03"\n')
        reihen, gruppen = self.laden(text)
        r = next(x for x in reihen if x["agenten"] == ["theater"])
        self.assertEqual((r["archiv"], r["laufend"]), (True, False))
        self.assertNotIn("Der nackte Wahnsinn", baum_texte(reihen, gruppen))
        self.assertIn("Der nackte Wahnsinn", baum_texte(reihen, gruppen, r["id"]))
        e = logik.klasse_ansicht(r["gruppe_id"], reihen, {}, gruppen)
        self.assertEqual([(z["titel"], z["marke"]) for z in e["zeilen"]], [("Der nackte Wahnsinn", "Archiv")])
        self.assertEqual(logik.reihen_auswahl(reihen), [{"id": "ethik-8-straftheorien",
                                                         "text": "Straftheorien (Ethik, Klasse 8)"}])

    def test_regel_7_stunde_verschieben(self):
        """Testregel 7 (lesend): Material hängt an der Stunden-id und folgt der Stunde; die Nummern sind 1..n
        lückenlos, auch mit einer ausgeblendeten Stunde dazwischen."""
        stunden = ('[[reihe.stunde]]\nid = "s-einstieg"\nthema = "Einstieg"\n\n'
                   '[[reihe.stunde]]\nid = "s-alt"\nthema = "Alt"\narchiviert = "2026-11-02"\n\n'
                   '[[reihe.stunde]]\nid = "s-kant"\nthema = "Kant"\nmarke = "Prüfung"\n\n'
                   '[[reihe.stunde]]\nid = "s-liszt"\nthema = "von Liszt"\n\n')
        kopf = '[[reihe]]\nid = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"'
        vorher = self.neu.replace(kopf, stunden + kopf)
        nachher = self.neu.replace(kopf, stunden.replace(  # von Liszt vor Kant (Aufgabe 3 im Test mit Lia)
            '[[reihe.stunde]]\nid = "s-kant"\nthema = "Kant"\nmarke = "Prüfung"\n\n', "") + (
            '[[reihe.stunde]]\nid = "s-kant"\nthema = "Kant"\nmarke = "Prüfung"\n\n') + kopf)
        z = logik.stunde_zuordnen({}, "K", "s-kant")
        zeilen = [{"id": "K", "titel": "AB Kant"}, {"id": "L", "titel": "Folien"}]
        for text, nummern, kant in ((vorher, ["Einstieg", "Kant", "von Liszt"], 2),
                                    (nachher, ["Einstieg", "von Liszt", "Kant"], 3)):
            reihen, gruppen = self.laden(text)
            r = reihen[0]
            st = logik.reihe_stunden(r)
            self.assertEqual([(s["thema"]) for s in st], nummern)
            je = logik.material_je_stunde(zeilen, z["stunde_von"], st)
            self.assertEqual({k: [x["titel"] for x in v] for k, v in je.items()}, {kant: ["AB Kant"], 0: ["Folien"]})
            a = logik.reihe_ansicht(r, reihen, [], JETZT, stunden_=st, stunde_von=z["stunde_von"])
            self.assertEqual([(s["nr"], s["titel"]) for s in a["stunden"]], list(enumerate(nummern, 1)))
            self.assertEqual([e["text"] for e in logik.baum(reihen, 0, r["id"], {r["id"]: st}, kant, gruppen)
                              if e.get("aktiv")], [f"{kant}  Kant"])
        # ausgeblendet: das Material fällt an die ganze Reihe zurück, die Zuordnung bleibt gespeichert
        reihen, _ = self.laden(nachher.replace('thema = "Kant"\n', 'thema = "Kant"\narchiviert = "2026-11-03"\n'))
        self.assertEqual(list(logik.material_je_stunde(zeilen, z["stunde_von"], reihen[0]["stunden"])), [0])
        self.assertEqual(z["stunde_von"], {"K": {"stunde": "s-kant"}})

    def test_regel_22_reihe_nach_aenderungen(self):
        """Testregel 22 (Web-App, lesend): Nach Handänderungen, wie sie die Operationen später machen, zeigt der
        Baum die Reihe richtig; die id und damit Links und Zuordnungen bleiben."""
        rid = "ethik-8-straftheorien"
        faelle = {
            "Titel ändern": (self.neu.replace('titel = "Straftheorien"', 'titel = "Strafe"'),
                             ["Ethik", "Klasse 8", "Strafe (in Planung)"]),
            "Stand ändern": (self.neu.replace('stand = "geplant"', 'stand = "laufend"'),
                             ["Ethik", "Klasse 8", "Straftheorien"]),
            "in andere Klasse verschieben": (
                self.neu.replace('klasse = "ethik-8"\ntitel = "Straftheorien"',
                                 'klasse = "darstellendes-spiel-kurs-11"\ntitel = "Straftheorien"'),
                ["Darstellendes Spiel", "Kurs 11", "Straftheorien (in Planung)"]),
            "Klasse archivieren": (
                self.neu.replace('name = "8"\nschuljahr = "2026/27"\n',
                                 'name = "8"\nschuljahr = "2026/27"\narchiviert = "2027-08-01"\n'),
                ["Ethik", "Archiv: Klasse 8 · 2026/27", "Straftheorien (in Planung)"]),
        }
        for name, (text, (fach, gruppe, titel)) in faelle.items():
            with self.subTest(name=name):
                reihen, gruppen = self.laden(text)
                r = next(x for x in reihen if x["id"] == rid)
                texte = baum_texte(reihen, gruppen, rid)
                self.assertLess(texte.index(fach), texte.index(gruppe))
                self.assertLess(texte.index(gruppe), texte.index(titel))
                aktiv = [e for e in logik.baum(reihen, 0, rid, gruppen=gruppen) if e.get("aktiv")]
                self.assertEqual([(e["text"], e["link"]) for e in aktiv], [(titel, f"/reihe/{rid}")])
                self.assertEqual(logik.reihe_von({"agent": "examen"}, reihen)["id"], rid)
                self.assertEqual(logik.reihe_von({"agent": "unterricht", "reihe": rid}, reihen)["id"], rid)
                self.assertEqual(logik.krumen(reihe=r)["teile"][1]["text"], gruppe.removeprefix("Archiv: "))


if __name__ == "__main__":
    unittest.main()
