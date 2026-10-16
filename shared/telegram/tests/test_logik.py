import tempfile
import unittest
from pathlib import Path

from logik import Gemeldet, aufteilen, befehl_auswerten, entwurf_als_text, verbrauch_text


class TestLogik(unittest.TestCase):
    def test_befehle(self):
        self.assertEqual(befehl_auswerten("/uni Kapitel 3 zusammenfassen"), ("uni", "erledigen", "Kapitel 3 zusammenfassen"))
        self.assertEqual(befehl_auswerten("/unilern Kapitel 4"), ("uni", "lernen", "Kapitel 4"))
        self.assertEqual(befehl_auswerten("/einkauf@Agentenzentralebot Geschenk"), ("einkauf", "erledigen", "Geschenk"))
        self.assertEqual(befehl_auswerten("/uni"), ("uni", "erledigen", ""))
        self.assertIsNone(befehl_auswerten("/quatsch hallo"))
        self.assertIsNone(befehl_auswerten("/lern x"))

    def test_aufteilen_verliert_nichts(self):
        text = "\n".join(f"Zeile {i} " + "x" * 50 for i in range(300))
        stuecke = aufteilen(text, 1000)
        self.assertTrue(all(len(s) <= 1000 for s in stuecke))
        self.assertEqual("\n".join(stuecke), text)
        self.assertEqual(aufteilen("kurz"), ["kurz"])
        lang = "y" * 2500
        self.assertEqual("".join(aufteilen(lang, 1000)), lang)

    def test_entwurf_zeigt_alles(self):
        e = {"agent": "posteingang", "typ": "mail", "titel": "Antwort", "inhalt": "Hallo " * 2000,
             "daten": {"an": "prof@example.org"}, "vorgaenger": None}
        text = "".join(entwurf_als_text(e))
        self.assertIn("prof@example.org", text)
        self.assertEqual(text.count("Hallo"), 2000)

    def test_verbrauch_text(self):
        zt = lambda ts: "ZEIT" if ts else "?"
        self.assertIn("unbekannt", verbrauch_text(None, "normal", {}, zt))
        stand = {"5h": 0.11, "7d": 0.39, "reset_5h": 1, "reset_7d": 2, "zeit": 3}
        heute = {"uni": {"laeufe": 2, "tokens": 12000, "minuten": 1.5, "usd": 0.1, "fehler": 1}}
        text = verbrauch_text(stand, "sparen", heute, zt)
        for teil in ("5 Stunden: 11 %", "7 Tage: 39 %", "sparen", "uni: 2 Läufe, 12k Tokens", "1 mit Fehler"):
            self.assertIn(teil, text)

    def test_gemeldet_speichern_laden(self):
        pfad = Path(tempfile.mkdtemp()) / "data" / "gemeldet.json"
        g = Gemeldet(pfad)
        g.angezeigt["x"] = "abc"
        g.listen["auftraege"].add("a1")
        g.stufe = "sparen"
        g.speichern()
        g2 = Gemeldet(pfad)
        self.assertEqual(g2.angezeigt, {"x": "abc"})
        self.assertEqual(g2.listen["auftraege"], {"a1"})
        self.assertEqual(g2.stufe, "sparen")

    def test_nachrichten_zuordnung(self):
        pfad = Path(tempfile.mkdtemp()) / "gemeldet.json"
        g = Gemeldet(pfad)
        g.MAX_NACHRICHTEN = 2
        for mid, aid in ((1, "a1"), (2, "a2"), (3, "a2")):
            g.nachricht_merken(mid, aid)
        g.listen["am_pc"].add("s-1")
        g.speichern()
        g2 = Gemeldet(pfad)
        self.assertEqual(g2.nachrichten, {"2": "a2", "3": "a2"})  # älteste fällt weg
        self.assertEqual(g2.listen["am_pc"], {"s-1"})


if __name__ == "__main__":
    unittest.main()
