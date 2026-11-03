"""Tests für agentkit.termine und agentkit.ferien_holen (Strukturplan docs/struktur-pflege-plan.md, Abschnitt 10:
Regeln 26–31, 33–35, soweit es um Rechnung geht).

Prüfstand: daten/ferien_2026.json (eingefrorene Kopie von agentkit/ferien.json, geholt 03.11.2026) und
daten/openholidays_auszug.json (Auszug aus den Antworten der API). Ein neuer Abruf ändert die Tests nicht.
"""

import copy
import json
import random
import unittest
from datetime import date
from pathlib import Path

from agentkit import ferien_holen, termine
from agentkit.termine import NACHRUECKEN, TAUSCHEN, Belegt, Plan, TermineFehler

DATEN = Path(__file__).parent / "daten"
FERIEN = json.loads((DATEN / "ferien_2026.json").read_text(encoding="utf-8"))
AUSZUG = json.loads((DATEN / "openholidays_auszug.json").read_text(encoding="utf-8"))
BE = termine.kalender_aus_daten(FERIEN, "BE")


def tage(*texte: str) -> list[date]:
    return [date.fromisoformat(t) for t in texte]


def zeitplan(tag: str, stunde: int, ab: str, bis: str, laenge: int = 1) -> dict:
    return {"tag": tag, "stunde": stunde, "laenge": laenge, "ab": ab, "bis": bis}


# Di 3. und Do 5. Stunde, 02.11.2026 bis 29.01.2027 in Berlin: 23 Termine (Weihnachtsferien 23.12.–02.01.)
NOV_JAN = (zeitplan("Di", 3, "2026-11-02", "2027-01-29"), zeitplan("Do", 5, "2026-11-02", "2027-01-29"))


def klassenplan(**reihen_lage) -> tuple[Plan, list[str]]:
    """Plan mit Reihen auf Termin-Stellen: klassenplan(S=(0, 5), W=(5, 3)) heißt Reihe S mit 5 Stunden ab Stelle 0,
    W mit 3 ab Stelle 5. Eine Lage (None, 2) heißt zwei Stunden ohne Termin. Gibt (Plan, Kennungen) zurück."""
    alle = termine.termine(NOV_JAN, BE)
    t = [x.kennung for x in alle]
    belegung, reihen = {}, {}
    for rid, (start, anzahl) in reihen_lage.items():
        ids = [f"{rid.lower()}{i + 1}" for i in range(anzahl)]
        reihen[rid] = ids
        for i, sid in enumerate(ids):
            belegung[sid] = t[start + i] if start is not None else None
    return Plan(zeitplan=NOV_JAN, belegung=belegung, reihen=reihen, kalender=BE), t


def stellen(plan_oder_belegung, t: list[str]) -> dict:
    """Belegung als Stellen in der Terminliste (None = ohne Termin), lesbarer als Kennungen."""
    belegung = plan_oder_belegung.belegung if isinstance(plan_oder_belegung, Plan) else plan_oder_belegung
    return {s: (t.index(k) if k else None) for s, k in belegung.items()}


def zufalls_regel(plan: Plan, nr: int, termin: str, sid: str, rid: str, modus: str) -> termine.Ergebnis:
    if nr == 0:
        return plan.alles_rueckt_nach(termin)
    if nr == 1:
        return plan.stunde_faellt_weg(termin)
    if nr == 2:
        return plan.stunde_auf_termin(sid, termin, modus)
    if nr == 3:
        return plan.reihe_verschieben(rid, termin, modus)
    if nr == 4:
        return plan.stunde_verschieben(plan.reihen[rid], plan.reihen[rid][0], len(plan.reihen[rid]) - 1)
    return plan.zuteilen(plan.reihen[rid])


class TestKennungen(unittest.TestCase):
    def test_lesen_und_anzeige(self):
        self.assertEqual(termine.kennung_lesen("2026-11-11/3"), (date(2026, 11, 11), 3))
        self.assertEqual(termine.anzeige("2026-11-11/3"), "Mi 11.11., 3. Std.")
        self.assertEqual(termine.anzeige("2026-11-10/3", 2), "Di 10.11., 3./4. Std.")

    def test_falsche_kennungen(self):
        for falsch in ("2026-11-11", "2026-13-01/3", "2026-11-11/16", "11.11.2026/3", 3, None):
            with self.subTest(falsch=falsch), self.assertRaises(TermineFehler):
                termine.kennung_lesen(falsch)


class TestKalender(unittest.TestCase):
    """Schuljahr und Halbjahr aus den Ferien (F9, F24)."""

    def test_schuljahr_berlin(self):
        self.assertEqual(BE.schuljahr("2026/27"), (date(2026, 8, 23), date(2027, 6, 30)))
        self.assertEqual(BE.schuljahr_von(date(2026, 11, 3)), "2026/27")
        self.assertEqual(BE.schuljahr_von(date(2026, 7, 20)), "2026/27")  # Sommerferien zählen zum nächsten
        self.assertEqual(BE.schuljahr_von(date(2026, 6, 1)), "2025/26")

    def test_halbjahr_endet_mit_den_winterferien(self):
        self.assertEqual(BE.halbjahr_stichtag("2026/27"), date(2027, 2, 1))
        self.assertEqual(BE.halbjahre("2026/27"), [(date(2026, 8, 23), date(2027, 1, 31)),
                                                   (date(2027, 2, 1), date(2027, 6, 30))])
        # Stichtag änderbar (F24)
        self.assertEqual(BE.halbjahre("2026/27", date(2027, 1, 25))[1][0], date(2027, 1, 25))
        ni = termine.kalender_aus_daten(FERIEN, "NI")
        self.assertEqual(ni.halbjahr_stichtag("2026/27"), date(2027, 2, 1))  # „Halbjahresferien“

    def test_land_ohne_winterferien_fragt(self):
        nw = termine.kalender_aus_daten(FERIEN, "NW")
        self.assertIsNone(nw.halbjahr_stichtag("2026/27"))
        with self.assertRaisesRegex(TermineFehler, "Stichtag"):
            nw.halbjahre("2026/27")
        self.assertEqual(nw.halbjahre("2026/27", date(2027, 2, 1))[1][0], date(2027, 2, 1))

    def test_fehlendes_schuljahr_und_land(self):
        with self.assertRaisesRegex(TermineFehler, "Sommerferien 2028"):
            BE.schuljahr("2027/28")
        with self.assertRaises(TermineFehler):
            BE.schuljahr("2026/28")
        with self.assertRaisesRegex(TermineFehler, "keine Ferien"):
            termine.kalender_aus_daten({"laender": {}}, "BE")
        with self.assertRaisesRegex(TermineFehler, "gibt es nicht"):
            termine.kalender_aus_daten(FERIEN, "XX")

    def test_nur_und_schulart(self):
        # SH: Herbstferien der Inseln beginnen früher, zählen aber nicht fürs Land
        sh = termine.kalender_aus_daten(FERIEN, "SH")
        self.assertIsNone(sh.frei(date(2026, 10, 6)))
        self.assertEqual(sh.frei(date(2026, 10, 13)), "Herbstferien")
        # MV: Winterferien der allgemeinbildenden Schulen dauern länger als die der beruflichen
        self.assertEqual(termine.kalender_aus_daten(FERIEN, "MV").frei(date(2027, 2, 17)), "Winterferien")
        self.assertIsNone(termine.kalender_aus_daten(FERIEN, "MV", "Berufliche Schulen").frei(date(2027, 2, 17)))

    def test_echte_ferien_datei_ist_gueltig(self):
        echt = json.loads(termine.FERIEN_DATEI.read_text(encoding="utf-8"))
        self.assertEqual(termine.ferien_pruefen(echt), [])
        self.assertEqual(set(echt["laender"]), set(termine.BUNDESLAENDER))
        for land in termine.BUNDESLAENDER:
            termine.kalender_aus_daten(echt, land).abgedeckt_pruefen(date(2026, 8, 1), date(2027, 7, 31))

    def test_ferien_datei_kaputt(self):
        kaputt = copy.deepcopy(FERIEN)
        kaputt["laender"]["BE"]["ferien"][0]["von"] = "2026-13-01"
        self.assertTrue(termine.ferien_pruefen(kaputt))
        with self.assertRaises(TermineFehler):
            termine.kalender_aus_daten(kaputt, "BE")


class TestRegel26SchultageOhneFerien(unittest.TestCase):
    def test_dienstag_erstes_halbjahr_berlin(self):
        erg = termine.termine([zeitplan("Di", 3, "2026-08-24", "2027-01-31")], BE)
        self.assertEqual([t.datum for t in erg], tage(
            "2026-08-25", "2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22", "2026-09-29", "2026-10-06",
            "2026-10-13",  # Herbstferien 19.10.–31.10.
            "2026-11-03", "2026-11-10", "2026-11-17", "2026-11-24", "2026-12-01", "2026-12-08", "2026-12-15",
            "2026-12-22",  # Weihnachtsferien 23.12.–02.01.
            "2027-01-05", "2027-01-12", "2027-01-19", "2027-01-26"))
        self.assertTrue(all(t.stunde == 3 and not t.zusatz for t in erg))

    def test_feiertage_und_freie_tage(self):
        # Mo 08.03.2027 Frauentag (Berlin), Do 06.05.2027 Himmelfahrt, Fr 07.05.2027 unterrichtsfreier Tag
        self.assertEqual([t.datum for t in termine.termine([zeitplan("Mo", 1, "2027-02-08", "2027-03-15")], BE)],
                         tage("2027-02-08", "2027-02-15", "2027-02-22", "2027-03-01", "2027-03-15"))
        self.assertEqual([t.datum for t in termine.termine([zeitplan("Do", 1, "2027-04-29", "2027-05-20"),
                                                            zeitplan("Fr", 1, "2027-04-29", "2027-05-20")], BE)],
                         tage("2027-04-29", "2027-04-30", "2027-05-13", "2027-05-14", "2027-05-20"))

    def test_ausfall_und_zusatz(self):
        plan = [zeitplan("Di", 3, "2026-11-02", "2026-11-30")]
        erg = termine.termine(plan, BE, ausfall=["2026-11-10/3"], zusatz=["2026-11-28/5", "2026-12-24/2"])
        self.assertEqual([t.kennung for t in erg], ["2026-11-03/3", "2026-11-17/3", "2026-11-24/3", "2026-11-28/5",
                                                    "2026-12-24/2"])  # Zusatztermin gilt auch in den Ferien
        self.assertEqual([t.zusatz for t in erg], [False, False, False, True, True])
        mit = termine.termine(plan, BE, ausfall=["2026-11-10/3"], mit_ausfall=True)
        self.assertEqual([(t.kennung, t.ausgefallen) for t in mit][:2], [("2026-11-03/3", False),
                                                                         ("2026-11-10/3", True)])

    def test_zeitraum_ohne_ferien_daten(self):
        with self.assertRaisesRegex(TermineFehler, "ab 2028-01-01 fehlen"):
            termine.termine([zeitplan("Di", 3, "2027-08-30", "2028-01-31")], BE)

    def test_ohne_kalender_nur_zusatz(self):
        self.assertEqual(len(termine.termine([], None, zusatz=["2026-11-28/5"])), 1)
        with self.assertRaisesRegex(TermineFehler, "Bundesland"):
            termine.termine([zeitplan("Di", 3, "2026-11-02", "2026-11-30")], None)


class TestRegel27DoppelstundeUndMehrereJeWoche(unittest.TestCase):
    def test_doppelstunde_ist_ein_termin(self):
        erg = termine.termine([zeitplan("Di", 3, "2026-11-02", "2026-11-15", laenge=2)], BE)
        self.assertEqual([(t.kennung, t.laenge) for t in erg], [("2026-11-03/3", 2), ("2026-11-10/3", 2)])
        self.assertEqual(erg[0].text, "Di 03.11., 3./4. Std.")

    def test_mehrere_je_woche_in_datumsfolge(self):
        erg = termine.termine([zeitplan("Do", 5, "2026-11-02", "2026-11-15"), zeitplan("Di", 5, "2026-11-02",
                               "2026-11-15"), zeitplan("Di", 1, "2026-11-02", "2026-11-15")], BE)
        self.assertEqual([t.kennung for t in erg], ["2026-11-03/1", "2026-11-03/5", "2026-11-05/5",
                                                    "2026-11-10/1", "2026-11-10/5", "2026-11-12/5"])

    def test_stundenplan_pruefen(self):
        faelle = {
            "tag": [zeitplan("So", 3, "2026-11-02", "2026-11-30")],
            "stunde als Zahl": [zeitplan("Di", "3", "2026-11-02", "2026-11-30")],
            "laenge": [zeitplan("Di", 3, "2026-11-02", "2026-11-30", laenge=3)],
            "als Datum": [zeitplan("Di", 3, "02.11.2026", "2026-11-30")],
            "ab liegt nach bis": [zeitplan("Di", 3, "2026-12-02", "2026-11-30")],
            "unbekannte Felder": [{**zeitplan("Di", 3, "2026-11-02", "2026-11-30"), "woche": "A"}],  # F22
            "überschneiden": [zeitplan("Di", 3, "2026-11-02", "2026-11-30", laenge=2),
                              zeitplan("Di", 4, "2026-11-20", "2026-12-30")],
        }
        for erwartet, plan in faelle.items():
            with self.subTest(erwartet):
                self.assertIn(erwartet, " ".join(termine.zeitplan_pruefen(plan)))
        # gleicher Tag und Stunde, aber nacheinander (Halbjahr): erlaubt
        self.assertEqual(termine.zeitplan_pruefen([zeitplan("Di", 3, "2026-08-24", "2027-01-31"),
                                                   zeitplan("Di", 3, "2027-02-01", "2027-06-30")]), [])


class TestRegel28AllesRueckt(unittest.TestCase):
    def setUp(self):
        # S auf 0–3, Lücke 4, W auf 5–7, w4 ohne Termin
        self.plan, self.t = klassenplan(S=(0, 4), W=(5, 3))
        self.plan.belegung["w4"] = None
        self.plan.reihen["W"].append("w4")

    def test_spaetere_stunden_wandern_um_genau_einen_termin(self):
        erg = self.plan.alles_rueckt_nach(self.t[1])
        self.assertEqual(stellen(erg.termine, self.t),
                         {"s1": 0, "s2": 2, "s3": 3, "s4": 4, "w1": 6, "w2": 7, "w3": 8, "w4": None})
        self.assertEqual(erg.ausfall, [self.t[1]])
        self.assertEqual(set(erg.termine), set(self.plan.belegung))  # ids bleiben, keine neu, keine weg
        self.assertEqual(erg.ausblenden, [])
        self.assertEqual(termine.belegung_pruefen(erg.termine, erg.ausfall), [])

    def test_ueber_reihengrenzen_und_luecke_bleibt_gleich_gross(self):
        nachher = self.plan.alles_rueckt_nach(self.t[1]).anwenden()
        frei = [t.kennung for t in nachher.freie(anzahl=1)]
        self.assertEqual(frei, [self.t[5]])  # die Lücke ist einen Termin weiter, gleich groß

    def test_rueckgaengig_stellt_alles_her(self):
        erg = self.plan.alles_rueckt_nach(self.t[1])
        self.assertEqual(erg.rueckgaengig().anwenden(), self.plan)

    def test_letzte_stunde_ohne_termin(self):
        plan, t = klassenplan(S=(20, 3))  # 23 Termine, S auf den letzten drei
        erg = plan.alles_rueckt_nach(t[21])
        self.assertEqual(stellen(erg.termine, t), {"s1": 20, "s2": 22, "s3": None})
        self.assertEqual(erg.ohne_termin, ["s3"])
        self.assertIn("keinen Termin mehr", erg.hinweise[0])

    def test_freier_termin_wird_nur_gestrichen(self):
        erg = self.plan.alles_rueckt_nach(self.t[4])
        self.assertEqual(erg.geaendert, {})
        self.assertEqual(erg.ausfall, [self.t[4]])

    def test_gestrichen_oder_kein_termin(self):
        nachher = self.plan.alles_rueckt_nach(self.t[1]).anwenden()
        with self.assertRaisesRegex(TermineFehler, "schon gestrichen"):
            nachher.alles_rueckt_nach(self.t[1])
        with self.assertRaisesRegex(TermineFehler, "kein Termin"):
            self.plan.alles_rueckt_nach("2026-11-04/3")
        self.assertEqual(nachher.ausfall_aufheben(self.t[1]).ausfall, [])


class TestRegel29StundeFaelltWeg(unittest.TestCase):
    def test_nur_diese_stunde_ausgeblendet(self):
        plan, t = klassenplan(S=(0, 4), W=(5, 3))
        erg = plan.stunde_faellt_weg(t[1])
        self.assertEqual(erg.geaendert, {"s2": None})
        self.assertEqual(erg.ausblenden, ["s2"])
        self.assertEqual(erg.ausfall, [t[1]])
        self.assertEqual(erg.ohne_termin, [])  # ausgeblendet, nicht „ohne Termin“
        nachher = erg.anwenden()
        self.assertIn("s2", nachher.ausgeblendet)
        self.assertEqual(erg.rueckgaengig().anwenden(), plan)


class TestRegel30StundenplanAbStichtag(unittest.TestCase):
    def setUp(self):
        self.plan_ganz = [zeitplan("Di", 3, "2026-08-24", "2027-06-30")]
        alle = [t.kennung for t in termine.termine(self.plan_ganz, BE)]
        self.stichtag = BE.halbjahr_stichtag("2026/27")
        vorher = [k for k in alle if termine.kennung_lesen(k)[0] < self.stichtag]
        danach = [k for k in alle if termine.kennung_lesen(k)[0] >= self.stichtag]
        # 3 Stunden vor dem Stichtag, 10 danach mit einer Lücke an Stelle 2
        self.belegung = {"a1": vorher[-3], "a2": vorher[-2], "a3": vorher[-1]}
        self.belegung.update({f"b{i}": danach[i if i < 2 else i + 1] for i in range(10)})
        self.plan = Plan(zeitplan=tuple(self.plan_ganz), belegung=self.belegung,
                         reihen={"A": ["a1", "a2", "a3"], "B": [f"b{i}" for i in range(10)]}, kalender=BE)

    def test_neuer_wochentag_reihenfolge_bleibt(self):
        erg = self.plan.stundenplan_ab(self.stichtag, [{"tag": "Do", "stunde": 2, "bis": "2027-06-30"}])
        self.assertEqual(erg.zeitplan, [zeitplan("Di", 3, "2026-08-24", "2027-01-31"),
                                        zeitplan("Do", 2, "2027-02-01", "2027-06-30")])
        for s in ("a1", "a2", "a3"):
            self.assertEqual(erg.termine[s], self.belegung[s])
        neu = [termine.kennung_lesen(erg.termine[f"b{i}"]) for i in range(10)]
        self.assertEqual(neu, sorted(neu))  # Reihenfolge bleibt
        self.assertTrue(all(d.weekday() == 3 and st == 2 and d >= self.stichtag for d, st in neu))
        donnerstage = [t.kennung for t in termine.termine(erg.zeitplan, BE) if t.datum >= self.stichtag]
        self.assertEqual(erg.termine["b0"], donnerstage[0])
        self.assertEqual(erg.termine["b2"], donnerstage[3])  # die Lücke an Stelle 2 bleibt
        self.assertEqual(erg.ohne_termin, [])
        self.assertEqual(erg.rueckgaengig().anwenden(), self.plan)

    def test_weniger_termine_sagt_welche(self):
        erg = self.plan.stundenplan_ab(self.stichtag, [{"tag": "Do", "stunde": 2, "bis": "2027-02-28"}])
        self.assertEqual(len([s for s in erg.ohne_termin if s.startswith("b")]), len(erg.ohne_termin))
        self.assertTrue(erg.ohne_termin)
        self.assertTrue(any("Termine, der alte hatte" in h for h in erg.hinweise))

    def test_neuer_plan_vor_dem_stichtag_geht_nicht(self):
        with self.assertRaisesRegex(TermineFehler, "frühestens"):
            self.plan.stundenplan_ab(self.stichtag, [zeitplan("Do", 2, "2027-01-04", "2027-06-30")])

    def test_halbjahr_ohne_alte_termine_danach(self):
        # Erstes Halbjahr endet vor dem Stichtag: neue Termine entstehen frei, keine Stunde rückt
        plan = Plan(zeitplan=(zeitplan("Di", 3, "2026-08-24", "2027-01-31"),), belegung={"a1": "2027-01-26/3"},
                    reihen={"A": ["a1"]}, kalender=BE)
        erg = plan.stundenplan_ab(self.stichtag, [{"tag": "Do", "stunde": 2, "bis": "2027-06-30"}])
        self.assertEqual(erg.geaendert, {})
        self.assertEqual(erg.anwenden().freie(ab=self.stichtag, anzahl=1)[0].kennung,
                         "2027-02-11/2")  # 04.02. Winterferien


class TestRegel31EinTerminEineStunde(unittest.TestCase):
    def test_pruefen(self):
        self.assertEqual(termine.belegung_pruefen({"a": "2026-11-03/3", "b": "2026-11-05/5", "c": None}), [])
        self.assertIn("zwei Stunden", termine.belegung_pruefen({"a": "2026-11-03/3", "b": "2026-11-03/3"})[0])
        self.assertIn("gestrichen", termine.belegung_pruefen({"a": "2026-11-03/3"}, ["2026-11-03/3"])[0])

    def test_keine_regel_macht_daten_kaputt(self):
        """Zufällige Folgen aller Regeln: nie zwei Stunden auf einem Termin, nie eine auf einem gestrichenen,
        nie verschwindet eine Stunde."""
        zufall = random.Random(31)
        for _ in range(40):
            plan, t = klassenplan(S=(0, 5), W=(6, 3), F=(12, 4), N=(None, 2))
            for _ in range(8):
                frei = [k for k in t if k in plan._pos]
                sid = zufall.choice(sorted(plan.belegung))
                rid = zufall.choice(sorted(plan.reihen))
                modus = zufall.choice([NACHRUECKEN, TAUSCHEN])
                nr = zufall.randrange(6)
                try:
                    erg = zufalls_regel(plan, nr, zufall.choice(frei), sid, rid, modus)
                except TermineFehler:
                    continue
                self.assertEqual(termine.belegung_pruefen(erg.termine, erg.ausfall), [])
                self.assertEqual(set(erg.termine), set(plan.belegung))
                self.assertEqual(erg.rueckgaengig().anwenden(), plan)
                plan = erg.anwenden()


class TestStundeVerschieben(unittest.TestCase):
    def test_inhalt_wandert_termine_bleiben(self):
        plan, t = klassenplan(S=(0, 4))
        erg = plan.stunde_verschieben(["s1", "s2", "s3", "s4"], "s4", 1)
        self.assertEqual(erg.reihenfolge, ["s1", "s4", "s2", "s3"])
        self.assertEqual(stellen(erg.termine, t), {"s1": 0, "s4": 1, "s2": 2, "s3": 3})
        self.assertEqual(erg.anwenden().reihen["S"], ["s1", "s4", "s2", "s3"])
        self.assertEqual(erg.rueckgaengig().anwenden(), plan)

    def test_ohne_termin_bleibt_der_platz_ohne(self):
        plan, t = klassenplan(S=(0, 2), N=(None, 1))
        erg = plan.stunde_verschieben(["s1", "s2", "n1"], "n1", 0)
        self.assertEqual(stellen(erg.termine, t), {"n1": 0, "s1": 1, "s2": None})


class TestRegel33ReiheZeitlichVerschieben(unittest.TestCase):
    def setUp(self):
        # Strafe 0–4, Würde 5–7, Lücke 8–9, Freundschaft 10–11
        self.plan, self.t = klassenplan(S=(0, 5), W=(5, 3), F=(10, 2))

    def test_belegt_fragt(self):
        with self.assertRaises(Belegt) as fall:
            self.plan.reihe_verschieben("W", self.t[0])
        self.assertEqual(fall.exception.reihen, ["S"])
        self.assertEqual(fall.exception.stunden, ["s1", "s2", "s3"])

    def test_nachruecken_wuerde_vor_strafe(self):
        erg = self.plan.reihe_verschieben("W", self.t[0], NACHRUECKEN)
        self.assertEqual(stellen(erg.termine, self.t), {"s1": 3, "s2": 4, "s3": 5, "s4": 6, "s5": 7,
                                                        "w1": 0, "w2": 1, "w3": 2, "f1": 10, "f2": 11})
        self.assertEqual(erg.rueckgaengig().anwenden(), self.plan)

    def test_nachruecken_nur_so_weit_wie_noetig(self):
        # Würde in die Lücke ab 8: Freundschaft rückt um einen, nicht um drei
        erg = self.plan.reihe_verschieben("W", self.t[8], NACHRUECKEN)
        self.assertEqual(stellen(erg.termine, self.t), {"s1": 0, "s2": 1, "s3": 2, "s4": 3, "s5": 4,
                                                        "w1": 8, "w2": 9, "w3": 10, "f1": 11, "f2": 12})

    def test_tauschen(self):
        # Strafe und Freundschaft tauschen: zusammen dieselben Termine, Würde und die Lücke bleiben
        erg = self.plan.reihe_verschieben("S", self.t[10], TAUSCHEN)
        self.assertEqual(stellen(erg.termine, self.t), {"f1": 0, "f2": 1, "s1": 2, "s2": 3, "s3": 4, "s4": 10,
                                                        "s5": 11, "w1": 5, "w2": 6, "w3": 7})
        self.assertEqual(erg.rueckgaengig().anwenden(), self.plan)
        # nach vorn genauso
        erg = self.plan.reihe_verschieben("W", self.t[0], TAUSCHEN)
        self.assertEqual(stellen(erg.termine, self.t), {"w1": 0, "w2": 1, "w3": 2, "s1": 3, "s2": 4, "s3": 5,
                                                        "s4": 6, "s5": 7, "f1": 10, "f2": 11})

    def test_freie_termine_nur_diese_reihe(self):
        erg = self.plan.reihe_verschieben("F", self.t[15])
        self.assertEqual(stellen(erg.geaendert, self.t), {"f1": 15, "f2": 16})

    def test_neue_reihe_ohne_termine(self):
        plan, t = klassenplan(S=(0, 2), N=(None, 2))
        self.assertEqual(stellen(plan.reihe_verschieben("N", t[1], NACHRUECKEN).termine, t),
                         {"n1": 1, "n2": 2, "s1": 0, "s2": 3})
        with self.assertRaisesRegex(TermineFehler, "Tauschen geht nur"):
            plan.reihe_verschieben("N", t[1], TAUSCHEN)

    def test_zu_wenige_termine(self):
        erg = self.plan.reihe_verschieben("S", self.t[21])
        self.assertEqual(stellen(erg.termine, self.t)["s3"], None)
        self.assertEqual(erg.ohne_termin, ["s3", "s4", "s5"])


class TestRegel34StundeAufTermin(unittest.TestCase):
    def setUp(self):
        self.plan, self.t = klassenplan(S=(0, 3), W=(5, 2))

    def test_in_eine_luecke_nur_diese_stunde(self):
        erg = self.plan.stunde_auf_termin("w2", self.t[3])
        self.assertEqual(erg.geaendert, {"w2": self.t[3]})
        self.assertEqual(termine.nach_datum(["w1", "w2"], erg.termine), ["w2", "w1"])

    def test_belegt(self):
        with self.assertRaises(Belegt):
            self.plan.stunde_auf_termin("w2", self.t[1])
        self.assertEqual(stellen(self.plan.stunde_auf_termin("w2", self.t[1], TAUSCHEN).geaendert, self.t),
                         {"w2": 1, "s2": 6})
        self.assertEqual(stellen(self.plan.stunde_auf_termin("w2", self.t[1], NACHRUECKEN).termine, self.t),
                         {"s1": 0, "w2": 1, "s2": 2, "s3": 3, "w1": 5})

    def test_zuteilen(self):
        plan, t = klassenplan(S=(0, 2), N=(None, 3))
        self.assertEqual(stellen(plan.zuteilen(["n1", "n2", "n3"]).geaendert, t), {"n1": 2, "n2": 3, "n3": 4})
        auswahl = plan.zuteilen(["n1", "n2", "n3"], auswahl=[t[9], t[7]])
        self.assertEqual(stellen(auswahl.geaendert, t), {"n1": 7, "n2": 9})
        self.assertIn("1 Stunde bekommt keinen Termin", auswahl.hinweise[0])
        with self.assertRaises(Belegt):
            plan.zuteilen(["n1"], auswahl=[t[0]])
        self.assertEqual(plan.freie(ab=termine.kennung_lesen(t[5])[0], anzahl=2)[0].kennung, t[5])


class TestRegel35NichtsOhneLia(unittest.TestCase):
    def test_regeln_veraendern_den_plan_nie(self):
        plan, t = klassenplan(S=(0, 5), W=(5, 3))
        vorher = copy.deepcopy((plan.belegung, plan.reihen, plan.ausfall, plan.zeitplan))
        plan.alles_rueckt_nach(t[1])
        plan.stunde_faellt_weg(t[2])
        plan.reihe_verschieben("W", t[0], NACHRUECKEN)
        plan.stunde_auf_termin("s1", t[12])
        plan.stunde_verschieben(plan.reihen["S"], "s1", 4)
        plan.stundenplan_ab(date(2026, 12, 1), [{"tag": "Mi", "stunde": 1, "bis": "2027-01-29"}])
        plan.hinweise()
        self.assertEqual((plan.belegung, plan.reihen, plan.ausfall, plan.zeitplan), vorher)

    def test_termine_rechnen_ist_immer_gleich(self):
        self.assertEqual(termine.termine(NOV_JAN, BE), termine.termine(NOV_JAN, BE))

    def test_hinweis_statt_aenderung(self):
        plan = Plan(zeitplan=NOV_JAN, belegung={"a": "2026-11-04/3"}, reihen={"A": ["a"]}, kalender=BE)
        self.assertIn("kein Termin der Klasse", plan.hinweise()[0])
        self.assertEqual(plan.belegung, {"a": "2026-11-04/3"})


class TestFerienHolen(unittest.TestCase):
    def setUp(self):
        self.laender = ferien_holen.umwandeln(AUSZUG["schulferien"], AUSZUG["feiertage"], AUSZUG["gruppen"])

    def test_alle_laender_und_bundesweite_feiertage(self):
        self.assertEqual(set(self.laender), set(termine.BUNDESLAENDER))
        for land in termine.BUNDESLAENDER:
            self.assertIn({"name": "Tag der Deutschen Einheit", "datum": "2026-10-03"}, self.laender[land]["feiertage"])
        self.assertIn({"name": "Internationaler Frauentag", "datum": "2027-03-08"}, self.laender["BE"]["feiertage"])
        self.assertNotIn("Internationaler Frauentag", json.dumps(self.laender["BY"], ensure_ascii=False))
        self.assertEqual(self.laender["BE"]["ferien"], [{"name": "Herbstferien", "von": "2026-10-19",
                                                         "bis": "2026-10-31"}])

    def test_ausnahmen_oertliches_und_schularten(self):
        sh = self.laender["SH"]["ferien"]
        self.assertIn({"name": "Sommerferien", "von": "2026-07-04", "bis": "2026-08-15"}, sh)
        self.assertTrue(any(e.get("nur", "").startswith("Inseln") for e in sh))
        self.assertIn({"name": "Friedensfest", "datum": "2026-08-08", "nur": "DE-BY-AU"},
                      self.laender["BY"]["feiertage"])
        self.assertEqual({e["schulart"] for e in self.laender["MV"]["ferien"]},
                         {"Allgemeinbildende Schulen", "Berufliche Schulen"})

    def test_einfuegen_ersetzt_nur_den_zeitraum(self):
        alt = {"laender": {"BE": {"abgedeckt": [{"von": "2025-01-01", "bis": "2025-12-31", "quelle": "von Hand",
                                                  "abgerufen": "2025-08-01"}],
                                  "ferien": [{"name": "Herbstferien", "von": "2025-10-20", "bis": "2025-11-01"},
                                             {"name": "Alt", "von": "2026-10-01", "bis": "2026-10-02"}],
                                  "feiertage": []}}}
        neu = ferien_holen.einfuegen(alt, self.laender, "2026-01-01", "2027-12-31", "2026-11-03")
        self.assertEqual(termine.ferien_pruefen(neu), [])
        namen = [e["name"] for e in neu["laender"]["BE"]["ferien"]]
        self.assertEqual(namen, ["Herbstferien", "Herbstferien"])  # 2025 bleibt, „Alt“ im Zeitraum ist ersetzt
        self.assertEqual([a["von"] for a in neu["laender"]["BE"]["abgedeckt"]], ["2025-01-01", "2026-01-01"])
        self.assertEqual(alt["laender"]["BE"]["ferien"][1]["name"], "Alt")  # alt unverändert
        self.assertEqual(json.loads(ferien_holen.als_text(neu)), neu)

    def test_zeitraum(self):
        self.assertEqual(ferien_holen.zeitraum(None, date(2026, 11, 3)), ("2026/27", "2026-01-01", "2027-12-31"))
        self.assertEqual(ferien_holen.zeitraum(None, date(2027, 3, 1))[0], "2026/27")
        self.assertEqual(ferien_holen.zeitraum("2027/28", date(2026, 11, 3))[1], "2027-01-01")
        with self.assertRaises(TermineFehler):
            ferien_holen.zeitraum("2027/29", date(2026, 11, 3))

    def test_echte_datei_ist_so_formatiert(self):
        text = termine.FERIEN_DATEI.read_text(encoding="utf-8")
        self.assertEqual(ferien_holen.als_text(json.loads(text)), text)


if __name__ == "__main__":
    unittest.main()
