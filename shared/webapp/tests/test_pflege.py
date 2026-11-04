"""pflege.py: Formularwerte der Masken (Struktur pflegen, Bauschritt 5), Termine für die Ansicht, Texte für Lia."""

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from agentkit import struktur, termine
from agentkit import strukturpflege as sp

import pflege

BE = termine.kalender("BE")
TEXT = """[schule]
bundesland = "BE"

[[fach]]
id = "ethik"
name = "Ethik"

[[klasse]]
id = "ethik-9"
fach = "ethik"
name = "9"
schuljahr = "2026/27"
ausfall = ["2026-11-10/3"]
zusatz = ["2026-11-13/5"]

[[klasse.zeitplan]]
tag = "Di"
stunde = 3
ab = "2026-11-01"
bis = "2026-11-30"

[[reihe]]
id = "wuerde"
klasse = "ethik-9"
titel = "Würde"

[[reihe.stunde]]
id = "s-a"
termin = "2026-11-03/3"
thema = "Einstieg"

[[reihe.stunde]]
id = "s-b"
termin = "2026-11-17/3"

[[reihe.stunde]]
id = "s-c"
thema = "weg"
termin = "2026-11-24/3"
archiviert = "2026-11-01"
"""


def werte(d: dict):
    return lambda name: d.get(name, "")


class TestEingaben(unittest.TestCase):
    def test_text_und_zeilen(self):
        self.assertEqual(pflege.text("  Würde ", "titel", pflege.PFLICHT["reihe"]), ("Würde", []))
        self.assertEqual(pflege.text(" ", "titel", pflege.PFLICHT["reihe"]),
                         ("", ["Wie heißt die Reihe? Bitte gib einen Titel ein."]))
        self.assertEqual(pflege.text("x" * (sp.LAENGE["titel"] + 1), "titel")[1],
                         [f"Der Titel ist zu lang (höchstens {sp.LAENGE['titel']} Zeichen)."])
        self.assertEqual(pflege.text(None, "thema"), ("", []))
        self.assertEqual(pflege.zeilen("Kant\n\n  Bentham \r\n", "behandelt"), (["Kant", "Bentham"], []))
        self.assertTrue(pflege.zeilen("x" * 999, "behandelt")[1])

    def test_schuljahr(self):
        self.assertEqual(pflege.schuljahr(" 2026/27 "), ("2026/27", []))
        for falsch in ("2026/28", "2026", "", "26/27"):
            self.assertEqual(pflege.schuljahr(falsch)[1], ["Schreib das Schuljahr bitte so: 2026/27."], falsch)
        self.assertEqual(pflege.naechstes_schuljahr("2025/26"), "2026/27")
        self.assertEqual(pflege.naechstes_schuljahr("2099/00"), "2100/01")
        self.assertEqual(pflege.naechstes_schuljahr(""), "")
        # Vorbelegung: aus den Ferien (die Sommerferien zählen schon zum nächsten), sonst ab August
        self.assertEqual(pflege.schuljahr_vorschlag(date(2026, 10, 30), BE), "2026/27")
        self.assertEqual(pflege.schuljahr_vorschlag(date(2027, 7, 20), BE), "2027/28")  # Sommerferien
        self.assertEqual(pflege.schuljahr_vorschlag(date(2027, 3, 1)), "2026/27")
        self.assertEqual(pflege.schuljahr_vorschlag(date(2026, 8, 1)), "2026/27")

    def test_stundenplan(self):
        form = {"tag-0": "Di", "stunde-0": "3", "laenge-0": "1", "tag-1": "Do", "stunde-1": "5", "laenge-1": "2",
                "tag-2": "", "stunde-2": ""}
        eintraege, gezeigt, fehler = pflege.stundenplan(werte(form), 3)
        self.assertEqual(eintraege, [{"tag": "Di", "stunde": 3, "laenge": 1}, {"tag": "Do", "stunde": 5, "laenge": 2}])
        self.assertEqual((len(gezeigt), fehler), (3, []))
        _, _, fehler = pflege.stundenplan(werte({"tag-0": "Di", "stunde-1": "4"}), 2)
        self.assertEqual(fehler, ["Termin 1: In welcher Stunde?", "Termin 2: Welcher Wochentag?"])
        _, _, fehler = pflege.stundenplan(werte({"tag-0": "Di", "stunde-0": "3", "laenge-0": "2",
                                                 "tag-1": "Di", "stunde-1": "4"}), 2)
        self.assertEqual(fehler, ["Zwei Termine liegen zur selben Zeit (Dienstag, 4. Stunde)."])
        self.assertEqual([pflege.zeilen_zahl(w, m) for w, m in (("", False), ("3", True), ("99", True), ("x", True))],
                         [pflege.ZEILEN_MIN, 4, pflege.ZEILEN_MAX, pflege.ZEILEN_MIN + 1])

    def test_zeitraum(self):
        grenzen = BE.schuljahr("2026/27")
        self.assertEqual(pflege.zeitraum("", "", grenzen), (grenzen[0].isoformat(), grenzen[1].isoformat(), []))
        self.assertEqual(pflege.zeitraum("2027-02-01", "", grenzen), ("2027-02-01", grenzen[1].isoformat(), []))
        self.assertEqual(pflege.zeitraum("", "", None)[2], [pflege.BUNDESLAND_FEHLT])
        self.assertEqual(pflege.zeitraum("2027-02-01", "2026-09-01", None)[2], ["„ab“ liegt nach „bis“."])
        self.assertEqual(pflege.zeitraum("quatsch", "", grenzen)[2], ["Bitte bei „ab“ und „bis“ ein Datum wählen."])
        plan = pflege.mit_zeitraum([{"tag": "Di", "stunde": 3, "laenge": 1}], "2026-11-01", "2026-11-30")
        self.assertEqual(termine.zeitplan_pruefen(plan), [])

    def test_stundenplan_zeilen_und_text(self):
        plan = [{"tag": "Di", "stunde": 3, "laenge": 1, "ab": "2026-08-31", "bis": "2027-01-29"},
                {"tag": "Do", "stunde": 5, "laenge": 2, "ab": "2026-08-31", "bis": "2027-01-29"},
                {"tag": "Mi", "stunde": 3, "laenge": 1, "ab": "2027-02-08", "bis": "2027-07-07"}]
        self.assertEqual([z["tag"] for z in pflege.stundenplan_zeilen(plan, date(2026, 11, 1))], ["Di", "Do"])
        self.assertEqual([z["tag"] for z in pflege.stundenplan_zeilen(plan, date(2027, 3, 1))], ["Mi"])
        self.assertEqual(pflege.stundenplan_text(plan), "Di 3. Std., Do 5./6. Std., Mi 3. Std.")
        self.assertEqual(len(pflege.aufgefuellt([{"tag": "Di", "stunde": "3", "laenge": "1"}], 3)), 3)

    def test_termine_wahl_und_ohne(self):
        liste = lambda name: {"termin": ["2026-11-17/3", ""]}.get(name, [])  # noqa: E731
        self.assertEqual(pflege.termine_wahl(werte({"anzahl": "6"}), liste), ({"termine": ["2026-11-17/3"]}, []))
        leer = lambda name: []  # noqa: E731
        self.assertEqual(pflege.termine_wahl(werte({"anzahl": "6", "ab": "2026-11-17"}), leer),
                         ({"anzahl": 6, "ab": "2026-11-17"}, []))
        self.assertEqual(pflege.termine_wahl(werte({"anzahl": "0"}), leer), ({}, []))
        self.assertEqual(pflege.termine_wahl(werte({"anzahl": "x"}), leer)[1],
                         ["Bitte die Zahl der Termine als Zahl angeben."])
        self.assertEqual([pflege.ohne_termin_zahl(w)[0] for w in ("", "3", "61", "x")], [0, 3, 0, 0])
        self.assertTrue(pflege.ohne_termin_zahl("61")[1])

    def test_geaendert_nur_was_lia_aendert(self):
        neu, gesehen = pflege.geaendert({"titel": ("Würde", "Würde "), "notizen": ("neu", "alt"),
                                         "behandelt": (["Kant"], ["Kant"])})
        self.assertEqual((neu, gesehen), ({"notizen": "neu"}, {"notizen": "alt"}))

    def test_stelle(self):
        folge = ["a", "b", "c", "d"]
        self.assertEqual(pflege.stelle(folge, "c", "b"), 1)  # c vor b
        self.assertEqual(pflege.stelle(folge, "a", "d"), 2)  # a vor d
        self.assertEqual(pflege.stelle(folge, "b", ""), 3)  # ans Ende
        self.assertIsNone(pflege.stelle(folge, "x", "a"))
        self.assertIsNone(pflege.stelle(folge, "a", "x"))


class TestTexte(unittest.TestCase):
    def test_haken_ohne_technik(self):
        haken = [{"quelle": "agenten", "anzahl": 1, "text": "Agenten: theater"},
                 {"quelle": "verweise", "anzahl": 1, "text": "Prüfungsstunde (lia/examen)"},
                 {"quelle": "darunter", "anzahl": 2, "text": "2 Stunden"}]
        self.assertEqual(pflege.haken_text(haken), "meine Arbeit daran, Prüfungsstunde, 2 Stunden")

    def test_aktion_text(self):
        self.assertEqual(pflege.aktion_text("Rückgängig: Stunde angelegt"), "Zurückgenommen: Stunde angelegt")
        self.assertEqual(pflege.aktion_text("Stunde angelegt"), "Stunde angelegt")


class TestAnsichten(unittest.TestCase):
    def setUp(self):
        self.s = struktur.aus_text(TEXT)

    def test_termine_liste(self):
        liste = pflege.termine_liste(self.s, "ethik-9", self.s.kalender(), date(2026, 11, 12))
        self.assertEqual([(t["kennung"], t["ausgefallen"], t["zusatz"], t["vergangen"]) for t in liste], [
            ("2026-11-03/3", False, False, True), ("2026-11-10/3", True, False, True),
            ("2026-11-13/5", False, True, False), ("2026-11-17/3", False, False, False),
            ("2026-11-24/3", False, False, False)])
        auf = {t["kennung"]: t["stunde"] for t in liste}
        self.assertEqual((auf["2026-11-03/3"]["nr"], auf["2026-11-03/3"]["thema"]), (1, "Einstieg"))
        self.assertEqual(auf["2026-11-17/3"]["thema"], "Thema offen")
        self.assertIsNone(auf["2026-11-24/3"]["nr"])  # ausgeblendet
        self.assertIsNone(auf["2026-11-10/3"])
        wahl = pflege.termin_optionen(liste)
        self.assertEqual([w["wert"] for w in wahl], ["2026-11-03/3", "2026-11-13/5", "2026-11-17/3", "2026-11-24/3"])
        self.assertEqual(wahl[0]["text"], "Di 03.11., 3. Std. · Stunde 1: Einstieg (Würde)")
        self.assertEqual(wahl[3]["text"], "Di 24.11., 3. Std. · ausgeblendet: weg (Würde)")
        self.assertEqual([w["wert"] for w in pflege.termin_optionen(liste, nur_frei=True)], ["2026-11-13/5"])
        self.assertNotIn("2026-11-03/3", [w["wert"] for w in pflege.termin_optionen(liste, ohne="s-a")])
        self.assertEqual(pflege.erster_freier(liste, date(2026, 11, 12)), "2026-11-13")
        self.assertEqual(pflege.erster_freier(liste, date(2026, 11, 14)), "")

    def test_belegt_und_fehler(self):
        belegt = termine.Belegt("x", ["s-a", "s-b"], ["wuerde"])
        self.assertEqual(pflege.belegt_text(self.s, belegt), "Dort liegt schon „Einstieg“ (Würde), „Thema offen“ (Würde).")
        self.assertEqual(pflege.fehler_text(sp.Konflikt("Inzwischen geändert (Titel), bitte neu laden")),
                         pflege.NEU_LADEN)
        self.assertEqual(pflege.fehler_text(sp.PflegeFehler("Reihe 'x' gibt es nicht")), pflege.GIBT_ES_NICHT)
        self.assertEqual(pflege.fehler_text(sp.PflegeFehler("Titel fehlt")), "Titel: bitte ausfüllen.")
        self.assertEqual(pflege.fehler_text(sp.PflegeFehler("Klasse 9 (2026/27) in Ethik gibt es schon")),
                         "Klasse 9 (2026/27) in Ethik gibt es schon.")
        haken = [{"quelle": "darunter", "anzahl": 2, "text": "2 Stunden"}, {"quelle": "auftraege", "anzahl": 1,
                                                                             "text": "1 Auftrag"}]
        self.assertEqual(pflege.loeschen_text(haken), "Löschen geht nicht, weil noch etwas daran hängt: 2 Stunden, "
                         "1 Auftrag. Archivieren geht immer, dabei geht nichts verloren.")

    def test_aenderungen(self):
        jetzt = datetime(2026, 11, 3, 18, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        liste = pflege.aenderungen([
            {"id": "a", "zeit": "2026-11-03T17:00:00+01:00", "text": "Reihe „Würde“ angelegt", "zurueckgenommen": None},
            {"id": "b", "zeit": "2026-11-02T09:05:00+01:00", "text": "x", "zurueckgenommen": "c"},
            {"id": "d", "zeit": "kaputt", "text": "y"}], jetzt)
        self.assertEqual([(a["zeit"], a["zurueck"], a["hinweis"]) for a in liste],
                         [("heute 17:00", True, ""), ("gestern 09:05", False, "zurückgenommen"), ("", True, "")])


if __name__ == "__main__":
    unittest.main()
