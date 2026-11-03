"""Tests für agentkit.strukturpflege (Strukturplan docs/struktur-pflege-plan.md, Abschnitt 10: Regeln 4, 5, 7–14,
16, 18–21, 23, 32–35).

Vorlage: daten/reihen_echt.toml (eingefrorene Kopie der echten reihen.toml im neuen Format), Lerngruppe als
Platzhalter. MIT_TERMINEN entsteht daraus mit den Operationen selbst (Bundesland, Stundenplan, Stunden, Termine).
Die Ablauf-Tests laufen in einem Git-Repo im Temp-Ordner mit dem echten commit-daten.sh.
"""

import difflib
import hashlib
import json
import logging
import os
import random
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from agentkit import blockeditor as be
from agentkit import struktur, termine
from agentkit import strukturpflege as sp

DATEN = Path(__file__).parent / "daten"
AGENTEN = Path(__file__).resolve().parents[3]
ECHT = (DATEN / "reihen_echt.toml").read_text(encoding="utf-8")
GRUPPE = "Platzhalter-Lerngruppe: unruhige Gruppe, mag Medienwechsel"
LG = f'# Lerngruppen je Klasse (Platzhalter für die Tests)\n\n"ethik-8" = """{GRUPPE}"""\n'
BE = termine.kalender_aus_daten(json.loads((DATEN / "ferien_2026.json").read_text(encoding="utf-8")), "BE")
HEUTE = date(2026, 11, 3)
STUNDENPLAN = [{"tag": "Di", "stunde": 3, "ab": "2026-11-02", "bis": "2027-01-29"},
               {"tag": "Do", "stunde": 5, "laenge": 2, "ab": "2026-11-02", "bis": "2027-01-29"}]
STRAF = "ethik-8-straftheorien"


def umgebung(**mehr) -> sp.Umgebung:
    return sp.Umgebung(**{"instanz": None, "heute": HEUTE, "zufall": random.Random(7), "kalender": BE, **mehr})


def rechnen(operation: str, argumente: dict, text: str = ECHT, lg: str = LG, **mehr) -> sp.Rechnung:
    return sp.vorschau(operation, argumente, text, lg, umgebung(**mehr))


def diff(alt: str, neu: str) -> list[str]:
    """Nur die geänderten Zeilen, „-“ weg, „+“ dazu (wie git diff ohne Umgebung)."""
    return [z for z in difflib.unified_diff(alt.splitlines(), neu.splitlines(), n=0, lineterm="")
            if z[:1] in "+-" and not z.startswith(("+++", "---"))]


def kommentare(text: str) -> list[str]:
    return sorted(z for z in text.splitlines() if z.lstrip().startswith("#"))


def ids(text: str, lg: str = LG) -> set[str]:
    s = struktur.aus_text(text, json_lg(lg))
    return {o["id"] for o in s.faecher + s.klassen + s.reihen + s.stunden()}


def json_lg(lg: str) -> dict:
    import tomllib
    return tomllib.loads(lg)


def stunden(text: str, reihe: str = STRAF) -> list[tuple]:
    r = struktur.aus_text(text, json_lg(LG)).reihe(reihe)
    return [(s["thema"], s["termin"]) for s in r["stunden"]]


def _mit_terminen() -> str:
    t = rechnen("schule_setzen", {"bundesland": "BE"}).text
    t = rechnen("stundenplan_setzen", {"klasse": "ethik-8", "zeitplan": STUNDENPLAN}, t).text
    for thema, marke in (("Einstieg: Wozu Gefängnis?", ""), ("Kant: Vergeltung", "Prüfung"),
                         ("von Liszt: Prävention", "UB"), ("Vergleich", "")):
        t = rechnen("stunde_anlegen", {"reihe": STRAF, "thema": thema, "marke": marke}, t).text
    t = rechnen("termine_zuteilen", {"reihe": STRAF, "ab": "2026-11-03", "anzahl": 4}, t).text
    t = rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde", "stunden": ["Menschenwürde", "Grundgesetz"]},
                t).text
    return rechnen("termine_zuteilen", {"reihe": "ethik-8-wuerde", "ab": "2026-11-24", "anzahl": 2}, t).text


MIT_TERMINEN = _mit_terminen()
WUERDE = "ethik-8-wuerde"


def sid(text: str, thema: str) -> str:
    s = struktur.aus_text(text, json_lg(LG))
    return next(st["id"] for st in s.stunden() if st["thema"] == thema)


# Alle Aktionen der Matrix (Abschnitt 4) für die Regeln, die für jede Aktion gelten: (Name, Argumente, Text)
FAELLE = [
    ("schule_setzen", {"bundesland": "BE"}, ECHT),
    ("fach_anlegen", {"name": "Philosophie"}, ECHT),
    ("fach_aendern", {"fach": "ethik", "kurzform": "Eth"}, ECHT),
    ("klasse_anlegen", {"fach": "ethik", "name": "9", "schuljahr": "2026/27"}, ECHT),
    ("klasse_aendern", {"klasse": "darstellendes-spiel-kurs-11", "name": "Kurs 11b"}, ECHT),
    ("klasse_verschieben", {"klasse": "darstellendes-spiel-kurs-11", "fach": "ethik"}, ECHT),
    ("klasse_kopieren", {"klasse": "ethik-8", "name": "9", "lerngruppe_mitnehmen": True}, ECHT),
    ("lerngruppe_setzen", {"klasse": "ethik-8", "text": "Neue Beschreibung"}, ECHT),
    ("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde", "stunden": ["Einstieg", "Kant"]}, ECHT),
    ("reihe_aendern", {"reihe": STRAF, "titel": "Strafe", "reihenfrage": "Warum strafen wir?"}, ECHT),
    ("reihe_verschieben", {"reihe": "ethik-8-helfen", "klasse": "ethik-7-2025-26"}, ECHT),
    ("reihe_kopieren", {"reihe": "ethik-7-freundschaft", "klasse": "ethik-8"}, ECHT),
    ("stunde_anlegen", {"reihe": STRAF, "thema": "Kant"}, ECHT),
    ("archivieren", {"id": STRAF}, ECHT),
    ("archivieren", {"id": "ethik"}, ECHT),
    ("wiederherstellen", {"id": "ethik-7-2025-26"}, ECHT),
    ("loeschen", {"id": "darstellendes-spiel-kurs-11"}, ECHT),
    ("loeschen", {"id": "ethik-8-helfen"}, ECHT),
    ("stundenplan_ab", {"klasse": "ethik-8", "stichtag": "2026-11-16",
                        "zeitplan": [{"tag": "Mi", "stunde": 2, "bis": "2027-01-29"},
                                     {"tag": "Fr", "stunde": 1, "laenge": 2, "bis": "2027-01-29"}]}, MIT_TERMINEN),
    ("zusatztermin", {"klasse": "ethik-8", "termin": "2026-11-28/5"}, MIT_TERMINEN),
    ("reihe_zeitlich", {"reihe": WUERDE, "start": "2026-11-05/5", "bei_belegt": "nachruecken"}, MIT_TERMINEN),
    ("reihe_zeitlich", {"reihe": WUERDE, "start": "2026-11-03/3", "bei_belegt": "tauschen"}, MIT_TERMINEN),
    ("termine_zuteilen", {"reihe": WUERDE, "termine": ["2026-12-01/3"]}, MIT_TERMINEN),
    ("termine_freigeben", {"reihe": WUERDE, "termine": ["2026-11-26/5"]}, MIT_TERMINEN),
    ("ausfall", {"klasse": "ethik-8", "termin": "2026-11-05/5", "folge": "nachruecken"}, MIT_TERMINEN),
    ("ausfall", {"klasse": "ethik-8", "termin": "2026-11-05/5", "folge": "faellt_weg"}, MIT_TERMINEN),
    ("stunde_verschieben", {"stunde": sid(MIT_TERMINEN, "Vergleich"), "stelle": 0}, MIT_TERMINEN),
    ("stunde_verschieben", {"stunde": sid(MIT_TERMINEN, "Vergleich"), "stelle": 1, "reihe": WUERDE}, MIT_TERMINEN),
    ("stunde_auf_termin", {"stunde": sid(MIT_TERMINEN, "Grundgesetz"), "termin": "2026-11-19/5"}, MIT_TERMINEN),
    ("stunde_aendern", {"stunde": sid(MIT_TERMINEN, "Vergleich"), "thema": "Vergleich und Urteil"}, MIT_TERMINEN),
    ("stunde_kopieren", {"stunde": sid(MIT_TERMINEN, "Vergleich"), "reihe": WUERDE}, MIT_TERMINEN),
    ("archivieren", {"id": sid(MIT_TERMINEN, "Vergleich")}, MIT_TERMINEN),
    ("loeschen", {"id": sid(MIT_TERMINEN, "Vergleich")}, MIT_TERMINEN),
]


_ERGEBNISSE: dict[int, sp.Rechnung] = {}


def ergebnis(nr: int) -> sp.Rechnung:
    """Jede Aktion aus FAELLE wird nur einmal gerechnet (mehrere Regeln prüfen dasselbe Ergebnis)."""
    if nr not in _ERGEBNISSE:
        name, argumente, text = FAELLE[nr]
        _ERGEBNISSE[nr] = rechnen(name, argumente, text)
    return _ERGEBNISSE[nr]


def faelle():
    for nr, (name, argumente, text) in enumerate(FAELLE):
        yield nr, name, argumente, text


class TestOperationen(unittest.TestCase):
    def test_alle_aktionen_der_matrix_ergeben_gueltige_dateien(self):
        self.assertEqual(sorted({f[0] for f in FAELLE} | {"ausfall_aufheben", "stundenplan_setzen",
                                                           "zusatztermin_entfernen"}), sorted(sp.OPERATIONEN))
        for nr, name, argumente, text in faelle():
            with self.subTest(name, **{k: str(v) for k, v in argumente.items()}):
                r = ergebnis(nr)
                self.assertTrue(r.text != text or r.lerngruppen != LG)
                struktur.aus_text(r.text, json_lg(r.lerngruppen))  # gültig
                self.assertNotIn(GRUPPE, r.beschreibung)

    def test_regel10_rueckgaengig_byte_gleich(self):
        for nr, name, argumente, text in faelle():
            with self.subTest(name, **{k: str(v) for k, v in argumente.items()}):
                r = ergebnis(nr)
                zurueck = be.zurueck(r.gegen["reihen"], r.text) if r.gegen["reihen"] else r.text
                lg = (be.zurueck(r.gegen["lerngruppen"], r.lerngruppen, kopf_eintraege=True)
                      if r.gegen["lerngruppen"] else r.lerngruppen)
                self.assertEqual((zurueck, lg), (text, LG))

    def test_regel18_kommentare_bleiben(self):
        for nr, name, argumente, text in faelle():
            with self.subTest(name, **{k: str(v) for k, v in argumente.items()}):
                r = ergebnis(nr)
                vorher, nachher = kommentare(text), kommentare(r.text)
                if name == "loeschen":  # der Kommentar direkt über dem Block geht mit (und kommt mit Rückgängig)
                    weg = [z for z in vorher if z not in nachher]
                    self.assertLessEqual(len(weg), 1)
                    self.assertTrue(all(z in r.gegen["reihen"]["vorher"][argumente["id"]] for z in weg))
                else:
                    self.assertEqual(nachher, vorher)

    def test_regel5_kein_auftrag_verliert_seinen_ort(self):
        for nr, name, argumente, text in faelle():
            with self.subTest(name, **{k: str(v) for k, v in argumente.items()}):
                r = ergebnis(nr)
                weg = ids(text) - ids(r.text, r.lerngruppen)
                self.assertEqual(weg, {argumente["id"]} if name == "loeschen" else set())
                s = struktur.aus_text(r.text, json_lg(r.lerngruppen))
                for o in s.reihen + s.stunden():
                    lage = s.ort(o["id"])
                    self.assertTrue(lage["fach"] and lage["klasse"] and lage["reihe"])

    def test_regel4_neue_objekte_sind_gueltiger_ort(self):
        for nr, name, _, _ in faelle():
            if not name.endswith(("anlegen", "kopieren")):
                continue
            with self.subTest(name):
                r = ergebnis(nr)
                lage = struktur.aus_text(r.text, json_lg(r.lerngruppen)).ort(r.neue_id)
                self.assertIsNotNone(lage)
                self.assertIsNotNone(lage["fach"])

    def test_regel35_ohne_termin_aktion_aendert_sich_kein_datum(self):
        for nr, name, _, text in faelle():
            if text is not MIT_TERMINEN or name in ("stundenplan_ab", "reihe_zeitlich", "termine_zuteilen",
                                                    "termine_freigeben", "ausfall", "stunde_verschieben",
                                                    "stunde_auf_termin", "loeschen"):
                continue
            with self.subTest(name):
                r = ergebnis(nr)
                self.assertEqual([z for z in diff(text, r.text) if "termin =" in z or "ausfall" in z], [])

    def test_regel1_id_aendert_sich_nie(self):
        for feld in ("id", "agenten", "klasse", "archiviert"):
            with self.subTest(feld), self.assertRaises(sp.PflegeFehler):
                rechnen("reihe_aendern", {"reihe": STRAF, feld: "x"})
        r = rechnen("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"})
        self.assertEqual(ids(r.text), ids(ECHT))

    def test_regel2_neue_id_auch_nicht_in_auftraegen(self):
        with tempfile.TemporaryDirectory() as tmp:
            instanz = Path(tmp) / "lia" / "instanz"
            (instanz / "auftraege" / "erledigt").mkdir(parents=True)
            (instanz / "auftraege" / "erledigt" / "a.json").write_text(json.dumps({"reihe": "ethik-8-wuerde"}))
            r = rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde"}, instanz=instanz,
                        webapp_daten=instanz / "webapp")
        self.assertEqual(r.neue_id, "ethik-8-wuerde-2")
        self.assertEqual(rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde"}).neue_id, "ethik-8-wuerde")

    def test_eingaben_werden_geprueft(self):
        faelle = {
            "Titel fehlt": ("reihe_anlegen", {"klasse": "ethik-8", "titel": "  "}),
            "zu lang": ("stunde_anlegen", {"reihe": STRAF, "thema": "x" * 121}),
            "doppelte Klasse": ("klasse_anlegen", {"fach": "ethik", "name": "8", "schuljahr": "2026/27"}),
            "Schuljahr": ("klasse_anlegen", {"fach": "ethik", "name": "9", "schuljahr": "2026/28"}),
            "Marke": ("stunde_anlegen", {"reihe": STRAF, "marke": "Test"}),
            "unbekannte Reihe": ("reihe_aendern", {"reihe": "gibt-es-nicht", "titel": "x"}),
            "unbekannte Angabe": ("archivieren", {"id": STRAF, "farbe": "rot"}),
            "unbekannte Aktion": ("umbenennen", {}),
            "schon archiviert": ("archivieren", {"id": "ethik-7-2025-26"}),
            "nur geerbt archiviert": ("wiederherstellen", {"id": "ethik-7-freundschaft"}),
            "Stundenplan kaputt": ("stundenplan_setzen", {"klasse": "ethik-8", "zeitplan": [{"tag": "So"}]}),
        }
        for name, (operation, argumente) in faelle.items():
            with self.subTest(name), self.assertRaises(sp.PflegeFehler):
                rechnen(operation, argumente)

    def test_altes_format_wird_nicht_geschrieben(self):
        with self.assertRaisesRegex(sp.PflegeFehler, "alten Format"):
            rechnen("fach_anlegen", {"name": "X"}, (DATEN / "reihen_alt.toml").read_text(encoding="utf-8"), "")

    def test_konflikt_nur_beim_gesehenen_wert(self):
        u = umgebung()
        sp.vorschau("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"}, ECHT, LG, u,
                    gesehen={STRAF: {"titel": "Straftheorien"}, "ethik-8": {"lerngruppe": GRUPPE}})
        with self.assertRaises(sp.Konflikt) as e:
            sp.vorschau("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"}, ECHT, LG, u,
                        gesehen={"ethik-8": {"lerngruppe": "alter Text"}})
        self.assertNotIn(GRUPPE, str(e.exception))
        with self.assertRaises(sp.Konflikt):
            sp.vorschau("archivieren", {"id": STRAF}, ECHT, LG, u, gesehen={"weg": {"titel": "x"}})


class TestAussehenWieVonHand(unittest.TestCase):
    """Testregel 19: erwartete Diffs, so wie Jan die Datei von Hand ändert."""

    def test_titel_aendern_eine_zeile_weg_eine_dazu(self):
        r = rechnen("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"})
        self.assertEqual(diff(ECHT, r.text), ['-titel = "Straftheorien"', '+titel = "Strafe"'])
        self.assertEqual(r.beschreibung, "Reihe „Straftheorien“ in Ethik 8 (2026/27): Titel geändert (jetzt „Strafe“)")

    def test_regel9_archivieren_eine_zeile_wiederherstellen_byte_gleich(self):
        for kennung in ("ethik", "ethik-8", STRAF, "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"):
            with self.subTest(kennung):
                r = rechnen("archivieren", {"id": kennung})
                self.assertEqual(diff(ECHT, r.text), ['+archiviert = "2026-11-03"'])
                self.assertEqual(rechnen("wiederherstellen", {"id": kennung}, r.text).text, ECHT)
        st = sid(MIT_TERMINEN, "Kant: Vergeltung")
        r = rechnen("archivieren", {"id": st}, MIT_TERMINEN)
        self.assertEqual(diff(MIT_TERMINEN, r.text), ['+archiviert = "2026-11-03"'])
        self.assertTrue(r.beschreibung.endswith("ausgeblendet"))
        self.assertEqual(rechnen("wiederherstellen", {"id": st}, r.text).text, MIT_TERMINEN)
        # Wiederherstellen eines von Jan archivierten Blocks: genau seine Zeile weg
        self.assertEqual(diff(ECHT, rechnen("wiederherstellen", {"id": "ethik-7-2025-26"}).text),
                         ['-archiviert = "2026-10-30"'])

    def test_reihe_anlegen_ein_block_hinter_den_reihen_der_klasse(self):
        r = rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde", "reihenfrage": "Was ist Würde?"})
        danach = '\n[[reihe]]\nid = "darstellendes-spiel-kurs-12-der-nackte-wahnsinn"'  # hinter Helfen
        neu = ('\n[[reihe]]\nid = "ethik-8-wuerde"\nklasse = "ethik-8"\ntitel = "Würde"\n'
               'reihenfrage = "Was ist Würde?"\nstand = "geplant"\n')
        self.assertEqual(r.text, ECHT.replace(danach, neu + danach, 1))
        self.assertEqual(r.beschreibung, "Reihe „Würde“ in Ethik 8 (2026/27) angelegt")

    def test_klasse_anlegen_hinter_den_laufenden_klassen(self):
        r = rechnen("klasse_anlegen", {"fach": "ethik", "name": "9", "schuljahr": "2026/27"})
        danach = "\n# Jan 30.10.2026: das Stück des Theater-Agenten"  # hinter Ethik 8, vor den Kursen
        neu = '\n[[klasse]]\nid = "ethik-9"\nfach = "ethik"\nname = "9"\nschuljahr = "2026/27"\n'
        self.assertEqual(r.text, ECHT.replace(danach, neu + danach, 1))

    def test_stunde_verschieben_ein_block_an_anderer_stelle(self):
        t = ECHT
        for thema in ("Einstieg", "Kant", "von Liszt"):
            t = rechnen("stunde_anlegen", {"reihe": STRAF, "thema": thema}, t).text
        r = rechnen("stunde_verschieben", {"stunde": sid(t, "von Liszt"), "stelle": 1}, t)
        weg = [z[1:] for z in diff(t, r.text) if z[0] == "-"]
        dazu = [z[1:] for z in diff(t, r.text) if z[0] == "+"]
        self.assertEqual(sorted(weg), sorted(dazu))
        self.assertEqual(len(dazu), 4)  # Leerzeile, [[reihe.stunde]], id, thema
        self.assertEqual([x[0] for x in stunden(r.text)], ["Einstieg", "von Liszt", "Kant"])

    def test_loeschen_nimmt_den_kommentar_mit(self):
        r = rechnen("loeschen", {"id": "darstellendes-spiel-kurs-11"})
        block = ('\n# Jan 30.10.2026: neuer Kurs 11 im Schuljahr 2026/27, Reihen noch nicht eingetragen.\n[[klasse]]\n'
                 'id = "darstellendes-spiel-kurs-11"\nfach = "darstellendes-spiel"\nname = "Kurs 11"\n'
                 'schuljahr = "2026/27"\n')
        self.assertIn(block, ECHT)
        self.assertEqual(r.text, ECHT.replace(block, "", 1))

    def test_reihe_in_andere_klasse_eine_zeile_und_der_block_wandert(self):
        r = rechnen("reihe_verschieben", {"reihe": "ethik-8-helfen", "klasse": "ethik-7-2025-26"})
        weg = [z[1:] for z in diff(ECHT, r.text) if z[0] == "-"]
        dazu = [z[1:] for z in diff(ECHT, r.text) if z[0] == "+"]
        self.assertEqual(sorted(set(weg) ^ set(dazu)), ['klasse = "ethik-7-2025-26"', 'klasse = "ethik-8"'])
        self.assertLess(r.text.index('id = "ethik-7-glueckliches-leben"'), r.text.index('id = "ethik-8-helfen"'))

    def test_stunden_mit_terminen_wie_im_plan(self):
        self.assertEqual(stunden(MIT_TERMINEN), [
            ("Einstieg: Wozu Gefängnis?", "2026-11-03/3"), ("Kant: Vergeltung", "2026-11-05/5"),
            ("von Liszt: Prävention", "2026-11-10/3"), ("Vergleich", "2026-11-12/5")])
        self.assertEqual(stunden(MIT_TERMINEN, WUERDE), [("Menschenwürde", "2026-11-24/3"),
                                                         ("Grundgesetz", "2026-11-26/5")])
        self.assertIn('[[klasse.zeitplan]]\ntag = "Di"\nstunde = 3\nlaenge = 1\nab = "2026-11-02"\nbis = "2027-01-29"\n',
                      MIT_TERMINEN)
        self.assertTrue(MIT_TERMINEN.startswith(ECHT.split("[[fach]]")[0] + '[schule]\nbundesland = "BE"\n\n[[fach]]'))


class TestTermineSchreiben(unittest.TestCase):
    """Testregeln 28–30, 32–35 auf der Datei."""

    def test_regel7_und_28_stunde_verschieben_inhalt_wandert_termine_bleiben(self):
        vorher = struktur.aus_text(MIT_TERMINEN).reihe(STRAF)
        r = rechnen("stunde_verschieben", {"stunde": sid(MIT_TERMINEN, "Vergleich"), "stelle": 0}, MIT_TERMINEN)
        nachher = struktur.aus_text(r.text).reihe(STRAF)
        self.assertEqual([s["nr"] for s in nachher["stunden"]], [1, 2, 3, 4])
        self.assertEqual([s["termin"] for s in nachher["stunden"]], [s["termin"] for s in vorher["stunden"]])
        self.assertEqual([s["thema"] for s in nachher["stunden"]],
                         ["Vergleich", "Einstieg: Wozu Gefängnis?", "Kant: Vergeltung", "von Liszt: Prävention"])
        self.assertEqual({s["id"] for s in nachher["stunden"]}, {s["id"] for s in vorher["stunden"]})

    def test_regel28_alles_rueckt_nach_ueber_reihengrenzen(self):
        r = rechnen("ausfall", {"klasse": "ethik-8", "termin": "2026-11-10/3", "folge": "nachruecken"}, MIT_TERMINEN)
        self.assertEqual([t for _, t in stunden(r.text)], ["2026-11-03/3", "2026-11-05/5", "2026-11-12/5",
                                                          "2026-11-17/3"])
        self.assertEqual([t for _, t in stunden(r.text, WUERDE)], ["2026-11-26/5", "2026-12-01/3"])  # F23
        self.assertIn('+ausfall = ["2026-11-10/3"]', diff(MIT_TERMINEN, r.text))
        self.assertIn("fällt aus, alles rückt nach", r.beschreibung)

    def test_regel29_stunde_faellt_weg(self):
        r = rechnen("ausfall", {"klasse": "ethik-8", "termin": "2026-11-05/5", "folge": "faellt_weg"}, MIT_TERMINEN)
        self.assertEqual(diff(MIT_TERMINEN, r.text), ['+ausfall = ["2026-11-05/5"]', '-termin = "2026-11-05/5"',
                                                      '+archiviert = "2026-11-03"'])
        aufheben = rechnen("ausfall_aufheben", {"klasse": "ethik-8", "termin": "2026-11-05/5"}, r.text)
        self.assertEqual(diff(r.text, aufheben.text), ['-ausfall = ["2026-11-05/5"]'])

    def test_regel30_stundenplan_ab_stichtag(self):
        neu = [{"tag": "Mi", "stunde": 2, "bis": "2027-01-29"}, {"tag": "Fr", "stunde": 1, "laenge": 2,
                                                                  "bis": "2027-01-29"}]
        r = rechnen("stundenplan_ab", {"klasse": "ethik-8", "stichtag": "2026-11-11", "zeitplan": neu}, MIT_TERMINEN)
        self.assertEqual([t for _, t in stunden(r.text)], ["2026-11-03/3", "2026-11-05/5", "2026-11-10/3",
                                                          "2026-11-11/2"])  # vor dem Stichtag bleibt
        self.assertEqual([t for _, t in stunden(r.text, WUERDE)], ["2026-11-20/1", "2026-11-25/2"])  # Lücke bleibt
        self.assertEqual(struktur.aus_text(r.text).objekt("ethik-8")["zeitplan"][0]["bis"], "2026-11-10")
        self.assertEqual(r.text.count("[[klasse.zeitplan]]"), 4)

    def test_stundenplan_setzen_nur_ohne_verlorene_stunden(self):
        with self.assertRaisesRegex(sp.PflegeFehler, "Stundenplan ab"):
            rechnen("stundenplan_setzen", {"klasse": "ethik-8", "zeitplan": STUNDENPLAN[:1]}, MIT_TERMINEN)
        kuerzer = [{**e, "bis": "2026-12-18"} for e in STUNDENPLAN]  # keine Stunde verliert ihren Termin
        r = rechnen("stundenplan_setzen", {"klasse": "ethik-8", "zeitplan": kuerzer}, MIT_TERMINEN)
        self.assertEqual(diff(MIT_TERMINEN, r.text), ['-bis = "2027-01-29"', '+bis = "2026-12-18"'] * 2)

    def test_regel32_reihe_mit_terminen_in_einer_aktion(self):
        t = rechnen("termine_freigeben", {"reihe": WUERDE, "termine": ["2026-11-24/3", "2026-11-26/5"]},
                    MIT_TERMINEN).text  # Stunden mit Thema bleiben ohne Termin
        self.assertEqual(stunden(t, WUERDE), [("Menschenwürde", ""), ("Grundgesetz", "")])
        r = rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "Gerechtigkeit",
                                      "termine": ["2026-11-19/5", "2026-11-17/3", "2026-11-24/3"]}, t)
        self.assertEqual(stunden(r.text, "ethik-8-gerechtigkeit"), [("", "2026-11-17/3"), ("", "2026-11-19/5"),
                                                                    ("", "2026-11-24/3")])
        self.assertEqual(list(r.gegen["reihen"]["betroffen"])[:1], ["ethik-8-gerechtigkeit"])
        self.assertEqual(be.zurueck(r.gegen["reihen"], r.text), t)
        with self.assertRaises(termine.Belegt):
            rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "X", "termine": ["2026-11-03/3"]}, t)

    def test_freigeben_leere_stunde_verschwindet(self):
        t = rechnen("termine_zuteilen", {"reihe": WUERDE, "ab": "2026-12-01", "anzahl": 1}, MIT_TERMINEN).text
        self.assertEqual(stunden(t, WUERDE)[-1], ("", "2026-12-01/3"))
        r = rechnen("termine_freigeben", {"reihe": WUERDE, "termine": ["2026-12-01/3"]}, t)
        self.assertEqual(r.text, MIT_TERMINEN)

    def test_regel33_reihe_zeitlich_nachruecken_und_tauschen(self):
        with self.assertRaises(termine.Belegt) as e:
            rechnen("reihe_zeitlich", {"reihe": WUERDE, "start": "2026-11-05/5"}, MIT_TERMINEN)
        self.assertEqual(e.exception.reihen, [STRAF])
        r = rechnen("reihe_zeitlich", {"reihe": WUERDE, "start": "2026-11-05/5", "bei_belegt": "nachruecken"},
                    MIT_TERMINEN)
        self.assertEqual([t for _, t in stunden(r.text, WUERDE)], ["2026-11-05/5", "2026-11-10/3"])
        self.assertEqual([t for _, t in stunden(r.text)], ["2026-11-03/3", "2026-11-12/5", "2026-11-17/3",
                                                          "2026-11-19/5"])
        self.assertEqual(ids(r.text), ids(MIT_TERMINEN))
        self.assertEqual(be.zurueck(r.gegen["reihen"], r.text), MIT_TERMINEN)
        r = rechnen("reihe_zeitlich", {"reihe": WUERDE, "start": "2026-11-03/3", "bei_belegt": "tauschen"},
                    MIT_TERMINEN)
        self.assertEqual([t for _, t in stunden(r.text, WUERDE)], ["2026-11-03/3", "2026-11-05/5"])
        self.assertEqual([t for _, t in stunden(r.text)], ["2026-11-10/3", "2026-11-12/5", "2026-11-24/3",
                                                          "2026-11-26/5"])
        self.assertEqual([th for th, _ in stunden(r.text)], [th for th, _ in stunden(MIT_TERMINEN)])
        self.assertEqual(be.zurueck(r.gegen["reihen"], r.text), MIT_TERMINEN)

    def test_regel34_stunde_in_eine_luecke(self):
        r = rechnen("stunde_auf_termin", {"stunde": sid(MIT_TERMINEN, "Grundgesetz"), "termin": "2026-11-19/5"},
                    MIT_TERMINEN)
        weg = [z for z in diff(MIT_TERMINEN, r.text) if "termin" in z]
        self.assertEqual(sorted(weg), ['+termin = "2026-11-19/5"', '-termin = "2026-11-26/5"'])
        self.assertEqual(stunden(r.text, WUERDE), [("Grundgesetz", "2026-11-19/5"), ("Menschenwürde", "2026-11-24/3")])
        self.assertEqual(stunden(r.text), stunden(MIT_TERMINEN))

    def test_reihe_in_andere_klasse_verliert_termine(self):
        r = rechnen("reihe_verschieben", {"reihe": WUERDE, "klasse": "darstellendes-spiel-kurs-12"}, MIT_TERMINEN)
        self.assertEqual(stunden(r.text, WUERDE), [("Menschenwürde", ""), ("Grundgesetz", "")])
        self.assertTrue(r.hinweise)

    def test_regel11_kopie_einer_reihe(self):
        t = rechnen("reihe_anlegen", {"klasse": "ethik-8", "titel": "Neue Klasse"}, MIT_TERMINEN).text
        r = rechnen("reihe_kopieren", {"reihe": STRAF, "klasse": "ethik-7-2025-26"}, t)
        s = struktur.aus_text(r.text)
        kopie, alt = s.reihe(r.neue_id), s.reihe(STRAF)
        self.assertEqual(r.neue_id, "ethik-7-2025-26-straftheorien")
        self.assertEqual((kopie["herkunft"], kopie["stand"], kopie["agenten"], kopie["archiviert"]),
                         (STRAF, "geplant", [], ""))
        self.assertEqual([st["thema"] for st in kopie["stunden"]], [st["thema"] for st in alt["stunden"]])
        self.assertTrue(all(st["marke"] == "" and st["termin"] == "" for st in kopie["stunden"]))
        self.assertFalse({st["id"] for st in kopie["stunden"]} & {st["id"] for st in alt["stunden"]})
        self.assertEqual(kopie["notizen"], alt["notizen"])
        r = rechnen("reihe_kopieren", {"reihe": "darstellendes-spiel-kurs-12-der-nackte-wahnsinn",
                                       "klasse": "darstellendes-spiel-kurs-11"})
        self.assertEqual(struktur.aus_text(r.text).reihe(r.neue_id)["agenten"], [])  # Regel 6


class TestAblauf(unittest.TestCase):
    """Sperre, Handänderung, Konflikt, atomares Schreiben, Commit, Lerngruppe, Rückgängig (7.2) in einem Git-Repo im
    Temp-Ordner mit dem echten commit-daten.sh."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        self.repo = self.wurzel / "agenten"
        self.instanz = self.repo / "lia" / "instanz"
        self.instanz.mkdir(parents=True)
        (self.repo / "lia" / "unterricht").mkdir()
        os.symlink("../instanz/reihen.toml", self.repo / "lia" / "unterricht" / "reihen.toml")
        shutil.copy(AGENTEN / "commit-daten.sh", self.repo / "commit-daten.sh")
        os.symlink(AGENTEN / "shared", self.repo / "shared")
        self.datei = self.instanz / "reihen.toml"
        self.datei.write_text(ECHT, encoding="utf-8")
        self.lg = self.instanz / "lerngruppen.toml"
        self.lg.write_text(LG, encoding="utf-8")
        self.lg.chmod(0o600)
        (self.repo / ".gitignore").write_text("lia/instanz/lerngruppen.toml\nlia/instanz/.reihen.sperre\nshared\n")
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("add", ".gitignore", "commit-daten.sh", "lia")
        self.git("commit", "-q", "-m", "Anfang")
        self.meldungen = []
        log = logging.getLogger("agentkit.strukturpflege.test")
        log.addHandler(logging.NullHandler())  # Warnungen nicht auf stderr, assertLogs sieht sie trotzdem
        self.u = sp.Umgebung(instanz=self.instanz, ablage=self.wurzel / "ablage", webapp_daten=self.wurzel / "web",
                             kalender=BE, melden=self.meldungen.append, heute=HEUTE, zufall=random.Random(3), log=log)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *argumente: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *argumente], check=True, capture_output=True,
                              text=True, env=sp._umgebung_ohne_git()).stdout  # nie das Repo des Hooks

    def commits(self) -> list[str]:
        return self.git("log", "--format=%s").splitlines()

    def von_hand(self, alt: str, neu: str, committen: bool = True):
        self.datei.write_text(self.datei.read_text(encoding="utf-8").replace(alt, neu, 1), encoding="utf-8")
        if committen:
            self.git("commit", "-q", "-m", "Jan von Hand", "--", "lia/instanz/reihen.toml")

    def test_regel20_genau_ein_commit_nur_dieser_pfad(self):
        aus = sp.ausfuehren("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde"}, umgebung=self.u)
        self.assertTrue(aus.geaendert and aus.gesichert)
        self.assertEqual(self.commits(), ["lia/instanz: Reihe „Würde“ in Ethik 8 (2026/27) angelegt (Lia, Web-App)",
                                          "Anfang"])
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), ["lia/instanz/reihen.toml"])
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), aus.commit)
        self.assertEqual(self.git("status", "--porcelain", "--", "lia"), "")
        self.assertEqual(aus.neue_id, "ethik-8-wuerde")

    def test_ohne_aenderung_kein_commit_keine_aktion(self):
        aus = sp.ausfuehren("reihe_aendern", {"reihe": STRAF, "titel": "Straftheorien"}, umgebung=self.u)
        self.assertFalse(aus.geaendert)
        self.assertEqual(self.commits(), ["Anfang"])
        self.assertEqual(sp.letzte(umgebung=self.u), [])

    def test_regel12_atomar_und_symlink_bleibt(self):
        with mock.patch("agentkit.strukturpflege.os.replace", side_effect=OSError("Abbruch")):
            with self.assertRaises(OSError):
                sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), ECHT)
        self.assertEqual([p.name for p in self.instanz.iterdir() if p.name.endswith(".tmp")], [])
        self.assertEqual(self.commits(), ["Anfang"])
        sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        link = self.repo / "lia" / "unterricht" / "reihen.toml"
        self.assertTrue(link.is_symlink())
        self.assertIn('archiviert = "2026-11-03"', link.read_text(encoding="utf-8"))
        self.assertEqual([p.name for p in self.instanz.iterdir() if p.name.endswith(".tmp")], [])

    def test_regel13_andere_aenderung_bleibt_gleicher_schluessel_bricht_ab(self):
        gesehen = {STRAF: {"titel": struktur.laden(self.instanz).reihe(STRAF)["titel"]}}
        self.von_hand('titel = "Helfen"', 'titel = "Helfen in Not"')
        sp.ausfuehren("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"}, gesehen=gesehen, umgebung=self.u)
        s = struktur.laden(self.instanz)
        self.assertEqual((s.reihe(STRAF)["titel"], s.reihe("ethik-8-helfen")["titel"]), ("Strafe", "Helfen in Not"))
        self.von_hand('titel = "Strafe"', 'titel = "Strafen"')
        vorher = self.datei.read_text(encoding="utf-8")
        with self.assertRaisesRegex(sp.Konflikt, "neu laden"):
            sp.ausfuehren("reihe_aendern", {"reihe": STRAF, "titel": "Strafe 2"}, gesehen={STRAF: {"titel": "Strafe"}},
                          umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher)

    def test_regel14_ungespeicherte_handaenderung(self):
        self.von_hand('titel = "Helfen"', 'titel = "Helfen in Not"', committen=False)
        for _ in range(2):
            with self.assertRaises(sp.Handaenderung):
                sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertEqual(len(self.meldungen), 1)  # nur einmal je Stand
        self.assertIn("ungespeicherte Handänderungen", self.meldungen[0])
        self.assertNotIn('archiviert = "2026-11-03"', self.datei.read_text(encoding="utf-8"))
        # Lerngruppe geht trotzdem (reihen.toml bleibt unberührt)
        sp.ausfuehren("lerngruppe_setzen", {"klasse": "ethik-8", "text": "Neu"}, umgebung=self.u)
        self.git("commit", "-q", "-m", "Jan", "--", "lia/instanz/reihen.toml")
        sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertIn('titel = "Helfen in Not"', self.datei.read_text(encoding="utf-8"))

    def test_eigene_ungesicherte_aenderung_blockiert_nicht(self):
        ohne_commit = sp.Umgebung(**{**self.u.__dict__, "commit": False})
        sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=ohne_commit)
        self.assertEqual(self.commits(), ["Anfang"])
        sp.ausfuehren("archivieren", {"id": "ethik-8-helfen"}, umgebung=self.u)  # committet beide
        self.assertEqual(len(self.commits()), 2)
        self.assertEqual(self.git("status", "--porcelain", "--", "lia"), "")

    def test_commit_fehlgeschlagen_meldet_jan(self):
        (self.repo / "commit-daten.sh").write_text("#!/bin/sh\necho kaputt >&2\nexit 1\n")
        aus = sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertTrue(aus.geaendert)
        self.assertFalse(aus.gesichert)
        self.assertIn("kaputt", self.meldungen[0])
        self.assertIn('archiviert = "2026-11-03"', self.datei.read_text(encoding="utf-8"))

    def test_regel15_ungueltige_datei_wird_nicht_beschrieben(self):
        self.von_hand('stand = "geplant"', 'stand = "irgendwie"')
        vorher = self.datei.read_text(encoding="utf-8")
        with self.assertRaisesRegex(sp.PflegeFehler, "Jan ist informiert"):
            sp.ausfuehren("archivieren", {"id": "ethik-8-helfen"}, umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher)
        self.assertIn("ungültig", self.meldungen[0])

    def test_regel16_editor_lehnt_ab_statt_umzuformatieren(self):
        self.von_hand('titel = "Helfen"', '"titel" = "Helfen"')  # gültiges TOML, struktur liest es
        self.assertEqual(struktur.pruefen(self.instanz), [])
        vorher = self.datei.read_text(encoding="utf-8")
        with self.assertRaisesRegex(sp.PflegeFehler, "Jan ist informiert"):
            sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher)
        self.assertIn("Anführungszeichen", self.meldungen[0])

    def test_regel10_rueckgaengig_als_neuer_commit(self):
        aus = sp.ausfuehren("loeschen", {"id": "darstellendes-spiel-kurs-11"}, umgebung=self.u)
        zurueck = sp.rueckgaengig(aus.aktion, umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), ECHT)
        self.assertEqual(self.commits()[0], "lia/instanz: Rückgängig: Klasse Darstellendes Spiel Kurs 11 (2026/27) "
                                            "gelöscht (Lia, Web-App)")
        liste = sp.letzte(umgebung=self.u)
        self.assertEqual([a["id"] for a in liste], [zurueck.aktion, aus.aktion])
        self.assertEqual((liste[1]["zurueckgenommen"], liste[0]["rueckgaengig_von"]), (zurueck.aktion, aus.aktion))
        with self.assertRaisesRegex(sp.PflegeFehler, "schon rückgängig"):
            sp.rueckgaengig(aus.aktion, umgebung=self.u)
        with self.assertRaises(sp.PflegeFehler):
            sp.rueckgaengig("../../etc/passwd", umgebung=self.u)

    def test_regel10_rueckgaengig_nach_fremder_aenderung_abgelehnt(self):
        aus = sp.ausfuehren("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"}, umgebung=self.u)
        self.von_hand('titel = "Strafe"', 'titel = "Strafe!"')
        vorher = self.datei.read_text(encoding="utf-8")
        with self.assertRaises(sp.Konflikt):
            sp.rueckgaengig(aus.aktion, umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher)
        # anderer Block geändert: Rückgängig geht, Jans Änderung bleibt
        aus = sp.ausfuehren("archivieren", {"id": "ethik-8-helfen"}, umgebung=self.u)
        self.von_hand('titel = "Strafe!"', 'titel = "Strafe?"')
        sp.rueckgaengig(aus.aktion, umgebung=self.u)
        text = self.datei.read_text(encoding="utf-8")
        self.assertIn('titel = "Strafe?"', text)
        self.assertNotIn('archiviert = "2026-11-03"', text)

    def test_regel32_reihe_mit_terminen_ein_commit_ein_rueckgaengig(self):
        sp.ausfuehren("schule_setzen", {"bundesland": "BE"}, umgebung=self.u)
        sp.ausfuehren("stundenplan_setzen", {"klasse": "ethik-8", "zeitplan": STUNDENPLAN}, umgebung=self.u)
        vorher, commits = self.datei.read_text(encoding="utf-8"), len(self.commits())
        aus = sp.ausfuehren("reihe_anlegen", {"klasse": "ethik-8", "titel": "Würde", "ab": "2026-11-10", "anzahl": 6},
                            umgebung=self.u)
        self.assertEqual(len(self.commits()), commits + 1)
        self.assertEqual(len(struktur.laden(self.instanz).reihe("ethik-8-wuerde")["stunden"]), 6)
        sp.rueckgaengig(aus.aktion, umgebung=self.u)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher)
        self.assertEqual(len(self.commits()), commits + 2)

    def test_regel21_lerngruppe_nie_in_commit_log_meldung_aktionsliste(self):
        with self.assertLogs("agentkit.strukturpflege", level=logging.DEBUG) as log:
            aus = sp.ausfuehren("lerngruppe_setzen", {"klasse": "ethik-8", "text": "Ganz neuer Text"},
                                umgebung=self.u)
            sp.ausfuehren("klasse_kopieren", {"klasse": "ethik-8", "name": "9", "lerngruppe_mitnehmen": True},
                          umgebung=self.u)
            sp.rueckgaengig(aus.aktion, umgebung=self.u)
            sp.ausfuehren("loeschen", {"id": "ethik-9"}, umgebung=self.u)
            self.von_hand('titel = "Helfen"', 'titel = "Helfen!"', committen=False)
            with self.assertRaises(sp.Handaenderung):
                sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertEqual(aus.text, "Lerngruppe von Ethik 8 (2026/27) geändert")
        self.assertEqual(self.lg.read_text(encoding="utf-8"), LG)  # Rückgängig stellt den alten Text her
        self.assertEqual(self.lg.stat().st_mode & 0o777, 0o600)
        alles = "\n".join([self.git("log", "--format=%B"), *log.output, *self.meldungen,
                           json.dumps(sp.letzte(umgebung=self.u), ensure_ascii=False)])
        for text in (GRUPPE, "Ganz neuer Text"):
            self.assertNotIn(text, alles)
        self.assertNotIn("lerngruppen", self.git("log", "--name-only", "--format="))
        ablage = self.u.ablage
        self.assertEqual(ablage.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in ablage.iterdir()))
        self.assertIn(GRUPPE, (ablage / f"{aus.aktion}.json").read_text(encoding="utf-8"))  # fürs Rückgängig

    def test_klasse_loeschen_nimmt_lerngruppe_mit(self):
        self.von_hand('[[reihe]]\nid = "ethik-8-straftheorien"\nklasse = "ethik-8"',
                      '[[reihe]]\nid = "ethik-8-straftheorien"\nklasse = "darstellendes-spiel-kurs-11"')
        self.von_hand('[[reihe]]\nid = "ethik-8-helfen"\nklasse = "ethik-8"',
                      '[[reihe]]\nid = "ethik-8-helfen"\nklasse = "darstellendes-spiel-kurs-11"')
        vorher = self.datei.read_text(encoding="utf-8")
        aus = sp.ausfuehren("loeschen", {"id": "ethik-8"}, umgebung=self.u)
        self.assertNotIn("ethik-8", self.lg.read_text(encoding="utf-8"))
        self.assertEqual(struktur.pruefen(self.instanz), [])
        sp.rueckgaengig(aus.aktion, umgebung=self.u)
        self.assertEqual((self.datei.read_text(encoding="utf-8"), self.lg.read_text(encoding="utf-8")), (vorher, LG))

    def test_regel8_loeschen_abgelehnt_je_quelle(self):
        kurs = "darstellendes-spiel-kurs-11"
        faelle = {
            "darunter": ("ethik-8", lambda: None),
            "agenten": ("darstellendes-spiel-kurs-12-der-nackte-wahnsinn", lambda: None),
            "auftraege": (kurs, lambda: self.json_ablegen("auftraege/erledigt/a.json", {"ort": kurs})),
            "entwuerfe": (kurs, lambda: self.json_ablegen("freigabe/offen/e.json", {"reihe": kurs})),
            "webapp": (kurs, lambda: self.webapp_zustand({"reihe_von": {"x": kurs}})),
            "chat": (kurs, lambda: self.chat({"reihe": kurs})),
            "verweise": (kurs, lambda: self.verweis(kurs)),
        }
        for quelle, (kennung, vorbereiten) in faelle.items():
            with self.subTest(quelle):
                self.aufraeumen()
                vorbereiten()
                with self.assertRaises(sp.HaengtDran) as e:
                    sp.ausfuehren("loeschen", {"id": kennung}, umgebung=self.u)
                self.assertIn(quelle, [h["quelle"] for h in e.exception.haken])
                self.assertIn("Archivieren geht immer", str(e.exception))
                self.assertEqual(self.datei.read_text(encoding="utf-8"), ECHT)
        self.aufraeumen()
        sp.ausfuehren("loeschen", {"id": kurs}, umgebung=self.u)

    def json_ablegen(self, name: str, daten: dict):
        pfad = self.instanz / name
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(daten), encoding="utf-8")

    def webapp_zustand(self, daten: dict):
        schluessel = hashlib.sha256(str(self.instanz.resolve()).encode()).hexdigest()[:12]
        pfad = self.u.webapp_daten / "zustand" / f"{schluessel}.json"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(daten), encoding="utf-8")

    def chat(self, daten: dict):
        pfad = self.repo / "lia" / "chat" / "data" / "verlauf.jsonl"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(daten) + "\n", encoding="utf-8")

    def verweis(self, kennung: str):
        pfad = self.repo / "lia" / "recherche" / "einstellungen.toml"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(f'reihe = "{kennung}"\n', encoding="utf-8")

    def aufraeumen(self):
        for name in ("auftraege", "freigabe"):
            shutil.rmtree(self.instanz / name, ignore_errors=True)
        shutil.rmtree(self.u.webapp_daten, ignore_errors=True)
        for name in ("chat", "recherche"):
            shutil.rmtree(self.repo / "lia" / name, ignore_errors=True)

    def test_regel23_auftraege_und_fassungen_byte_gleich(self):
        self.json_ablegen("auftraege/erledigt/a.json", {"reihe": STRAF, "text": "Arbeitsblatt"})
        self.json_ablegen("auftraege/neu/b.json", {"ort": "ethik-8-helfen"})
        self.json_ablegen("freigabe/offen/c.json", {"reihe": STRAF})
        (self.instanz / "fassungen").mkdir()
        (self.instanz / "fassungen" / "f.json").write_text('{"final": "x"}', encoding="utf-8")

        def pruefsummen():
            return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(self.instanz.rglob("*.json"))}

        vorher = pruefsummen()
        for name, argumente in (("reihe_aendern", {"reihe": STRAF, "titel": "Strafe"}),
                                ("reihe_verschieben", {"reihe": STRAF, "klasse": "ethik-7-2025-26"}),
                                ("archivieren", {"id": "ethik-8-helfen"}), ("wiederherstellen", {"id": "ethik-8-helfen"}),
                                ("reihe_kopieren", {"reihe": STRAF, "klasse": "ethik-8"})):
            aus = sp.ausfuehren(name, argumente, umgebung=self.u)
            if name == "archivieren":
                self.assertIn("Auftrag läuft noch", " ".join(aus.hinweise))
        self.assertEqual(pruefsummen(), vorher)

    def test_sperre_liegt_in_der_instanz(self):
        sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=self.u)
        self.assertTrue((self.instanz / sp.SPERRE).exists())

    def test_testinstanz_ohne_git(self):
        andere = self.wurzel / "testinstanz"
        andere.mkdir()
        (andere / "reihen.toml").write_text(ECHT, encoding="utf-8")
        u = sp.Umgebung(**{**self.u.__dict__, "instanz": andere})
        aus = sp.ausfuehren("archivieren", {"id": STRAF}, umgebung=u)
        self.assertTrue(aus.gesichert)
        self.assertIsNone(aus.commit)
        self.assertEqual(self.commits(), ["Anfang"])


if __name__ == "__main__":
    unittest.main()
