import unittest

import logik


def ev(i, typ, lauf="l1", agent="uni", zeit=100.0, instanz=None, auftrag="A1", **daten):
    return {"id": f"2026-10-28:{i}", "zeit": zeit, "typ": typ, "agent": agent, "instanz": instanz,
            "lauf": lauf, "auftrag": auftrag, "daten": daten}


SHOW = """Id=uni.timer
ActiveState=active
SubState=waiting
Result=success
NextElapseUSecRealtime=Thu 2026-10-29 08:00:00 CET

Id=uni.service
ActiveState=inactive
SubState=dead
Result=success
StateChangeTimestamp=Wed 2026-10-28 19:00:31 CET

Id=posteingang.service
ActiveState=failed
SubState=failed
Result=oom-kill

Id=agentenzentrale.service
ActiveState=active
SubState=running
Result=success
"""


class TestLaeufe(unittest.TestCase):
    def test_fertiger_lauf(self):
        (lauf,) = logik.laeufe([
            ev(0, "lauf.gestartet", modell="sonnet", stufe="normal", konto="token", pid=7, zeitgesteuert=False),
            ev(1, "werkzeug", name="Read", zeit=101), ev(2, "werkzeug", name="Write", zeit=102),
            ev(3, "lauf.beendet", ok=True, tokens=900, dauer_s=4.2, zeit=104),
            ev(4, "auftrag.abgeschlossen", lauf=None, status="erledigt"),
        ])
        self.assertEqual((lauf["status"], lauf["werkzeuge"], lauf["tokens"], lauf["modell"]), ("ok", 2, 900, "sonnet"))
        self.assertEqual(len(lauf["ereignisse"]), 4)

    def test_laufend_abgestuerzt_und_fehler(self):
        ereignisse = [
            ev(0, "lauf.gestartet", lauf="lebt", pid=1, zeit=1),
            ev(1, "lauf.gestartet", lauf="tot", pid=2, zeit=2),
            ev(2, "lauf.fehler", lauf="limit", grund="limit", zeit=3),
            ev(3, "lauf.gestartet", lauf="zeit", pid=3, zeit=4),
            ev(4, "lauf.beendet", lauf="zeit", ok=False, zeit=5),
            ev(5, "lauf.fehler", lauf="zeit", grund="zeit", zeit=5),
            ev(6, "lauf.gestartet", lauf="schlecht", pid=4, zeit=6),
            ev(7, "lauf.beendet", lauf="schlecht", ok=False, zeit=7),
        ]
        laeufe = logik.laeufe(ereignisse, lebt=lambda pid: pid == 1)
        self.assertEqual([(x["id"], x["status"]) for x in laeufe], [
            ("schlecht", "fehlgeschlagen"), ("zeit", "fehler:zeit"), ("limit", "fehler:limit"),
            ("tot", "abgestuerzt"), ("lebt", "laeuft")])


class TestAuftragAnzeigen(unittest.TestCase):
    A = {"id": "x", "agent": "uni", "text": "t" * 2000, "ergebnis": "Fertig", "status": "erledigt", "geheim": 1}

    def test_jan_mit_text_gekuerzt(self):
        teil = logik.auftrag_anzeigen(self.A, None)
        self.assertEqual((len(teil["text"]), teil["ergebnis"]), (logik.TEXT_MAX, "Fertig"))
        self.assertNotIn("geheim", teil)

    def test_lia_ohne_texte(self):
        teil = logik.auftrag_anzeigen(self.A, "lia")
        self.assertNotIn("text", teil)
        self.assertNotIn("ergebnis", teil)
        self.assertIsNone(logik.auftrag_anzeigen(None, None))


class TestDienste(unittest.TestCase):
    def test_systemctl_lesen(self):
        units = logik.systemctl_lesen(SHOW)
        self.assertEqual(sorted(units), ["agentenzentrale.service", "posteingang.service", "uni.service", "uni.timer"])
        self.assertEqual(units["uni.timer"]["NextElapseUSecRealtime"], "Thu 2026-10-29 08:00:00 CET")

    def test_agenten(self):
        units = logik.systemctl_lesen(SHOW)
        laeufe = logik.laeufe([ev(0, "lauf.gestartet", pid=1), ev(1, "lauf.gestartet", lauf="l2", agent="unterricht",
                                                                   instanz="lia", pid=1, zeit=50)])
        namen = ["uni.service", "uni.timer", "posteingang.service", "agentenzentrale.service", "ausfall@.service",
                 "lia-unterricht.service", "vinted-bot.service"]
        offene = [{"agent": "uni"}, {"agent": "uni"}, {"agent": "posteingang"}]
        karten = {k["name"]: k for k in logik.agenten(namen, units, laeufe, offene, [{"agent": "posteingang"}])}
        self.assertNotIn("ausfall@", karten)
        uni = karten["uni"]
        self.assertEqual((uni["zustand"], uni["naechster_lauf"], uni["freigaben_offen"]),
                         ("laeuft", "Thu 2026-10-29 08:00:00 CET", 2))  # Lauf ohne beendet zählt als laeuft
        self.assertEqual(uni["letzter_lauf"]["id"], "l1")
        self.assertEqual((karten["posteingang"]["zustand"], karten["posteingang"]["unklar"]), ("gestoert", 1))
        self.assertEqual((karten["agentenzentrale"]["anzeige"], karten["agentenzentrale"]["agent"]), ("Zentrale", None))
        lia = karten["lia-unterricht"]
        self.assertEqual((lia["instanz"], lia["agent"], lia["letzter_lauf"]["id"], lia["freigaben_offen"]),
                         ("lia", "unterricht", "l2", 0))
        self.assertEqual(lia["zustand"], "laeuft")
        self.assertTrue(karten["vinted-bot"]["nur_anzeige"])
        self.assertEqual(karten["vinted-bot"]["zustand"], "unbekannt")

    def test_verbrauch(self):
        v = logik.verbrauch_anzeigen({"5h": 0.034, "7d": 0.35, "zeit": 9}, "normal", "token")
        self.assertEqual((v["5h"], v["7d"], v["stand"], v["konto"]), (3, 35, 9, "token"))
        self.assertIsNone(logik.verbrauch_anzeigen(None, "normal", "login")["stand"])


if __name__ == "__main__":
    unittest.main()
