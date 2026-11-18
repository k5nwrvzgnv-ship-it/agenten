import json
import tempfile
import unittest
from pathlib import Path

import pilos

RAUM = {"id": "4ws-fom-9z5", "name": "Forschungsprojekt Fehlstellen",
        "url": "https://pilos.hnee.de/rooms/4ws-fom-9z5", "zugangscode": "151390675"}


class TestBrauchtLink(unittest.TestCase):
    def test_ja(self):
        for t in ("antworte Böhme mit einem Link zur Sitzung", "lade mit BBB-Link ein", "schick den Einwahllink",
                  "Termin 23.11. 9 Uhr, Online-Treffen", "Bitte Link zum Meeting mitschicken", "per BigBlueButton"):
            self.assertTrue(pilos.braucht_link(t), t)

    def test_nein(self):
        for t in ("antworte Böhme", "schick Henri den Link zum Exposé", "Sitzung am Montag absagen", "Hobbyraum"):
            self.assertFalse(pilos.braucht_link(t), t)


class TestPruefen(unittest.TestCase):
    def test_eigener_link_erlaubt(self):
        self.assertEqual(pilos.links_pruefen(f"Link: {RAUM['url']}.", RAUM), [])
        self.assertEqual(pilos.links_pruefen("Ohne Link", None), [])

    def test_fremde_links(self):
        text = "https://pilos.hnee.de/rooms/aaa-bbb-ccc und https://teams.microsoft.com/l/x und https://hnee.de"
        self.assertEqual(len(pilos.links_pruefen(text, RAUM)), 2)
        self.assertEqual(pilos.links_pruefen("https://zoom.us/j/1", None, quellen="Link https://zoom.us/j/1"), [])

    def test_warnung(self):
        self.assertEqual(pilos.link_warnung({"text": RAUM["url"]}, RAUM), {"text": RAUM["url"]})
        self.assertEqual(pilos.link_warnung({"text": "x"}, None), {"text": "x"})
        w = pilos.link_warnung({"text": "x", "pruefen": "Anhang fehlt."}, RAUM)
        self.assertEqual(w["pruefen"], f"{pilos.LINK_FEHLT} Anhang fehlt.")

    def test_hinweis(self):
        h = pilos.hinweis(RAUM)
        self.assertIn(RAUM["url"], h)
        self.assertIn("Zugangscode: 151390675", h)
        self.assertIn("Zugangscode ist nicht nötig", pilos.hinweis({**RAUM, "zugangscode": ""}))


class TestAuffrischen(unittest.TestCase):
    def test_neuer_hinweis_ersetzt_alten(self):
        ohne = {**RAUM, "zugangscode": ""}
        g = {"text": "antworte Böhme" + pilos.hinweis(RAUM), "raum": RAUM, "kontext": {}}
        neu = pilos.raum_auffrischen(g, ohne)
        self.assertEqual(neu["text"], "antworte Böhme" + pilos.hinweis(ohne))
        self.assertNotIn("151390675", neu["text"])
        self.assertEqual(neu["raum"], ohne)

    def test_ohne_raum_oder_gleich(self):
        g = {"text": "x", "raum": None}
        self.assertIs(pilos.raum_auffrischen(g, RAUM), g)
        g2 = {"text": "x", "raum": RAUM}
        self.assertIs(pilos.raum_auffrischen(g2, RAUM), g2)
        self.assertIs(pilos.raum_auffrischen(g2, None), g2)


class TestAuswahl(unittest.TestCase):
    def test_raum_waehlen(self):
        raeume = [{"id": "a", "name": "Forschungsprojekt Fehlstellen", "owner": {"id": 2}},
                  {"id": "b", "name": "forschungsprojekt fehlstellen ", "owner": {"id": 1}}]
        self.assertEqual(pilos.raum_waehlen(raeume, besitzer_id=1)["id"], "b")
        self.assertIsNone(pilos.raum_waehlen(raeume, "Anderes"))

    def test_typ_id(self):
        typen = [{"id": 3, "name": "Exam"}, {"id": 2, "name": "Meeting"}]
        self.assertEqual(pilos.typ_id(typen), 2)
        with self.assertRaises(pilos.PilosFehler):
            pilos.typ_id(typen, "Lecture")

    def test_raum_aus(self):
        r = pilos.raum_aus({"id": "x1", "name": "N", "access_code": 42})
        self.assertEqual(r, {"id": "x1", "name": "N", "url": "https://pilos.hnee.de/rooms/x1", "zugangscode": "42"})


class FalschesPilos:
    basis = "https://pilos.hnee.de"

    def __init__(self, raeume):
        self.raeume, self.angelegt = raeume, []

    def anmelden(self):
        return {"id": 1120}

    def eigene_raeume(self):
        return self.raeume

    def raum_anlegen(self, name):
        self.angelegt.append(name)
        return {"id": "neu-123-abc"}

    def raum(self, rid):
        return {"id": rid, "name": pilos.RAUMNAME, "access_code": "999"}


class TestSitzungsraum(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.datei = Path(tmp.name) / "data" / "sitzungsraum.json"

    def test_legt_einmal_an_und_merkt_sich(self):
        p = FalschesPilos([])
        r = pilos.sitzungsraum({}, self.datei, verbindung=p)
        self.assertEqual(r["url"], "https://pilos.hnee.de/rooms/neu-123-abc")
        self.assertEqual(p.angelegt, [pilos.RAUMNAME])
        self.assertEqual(self.datei.stat().st_mode & 0o777, 0o600)
        nochmal = FalschesPilos([])
        self.assertEqual(pilos.sitzungsraum({}, self.datei, verbindung=nochmal), r)
        self.assertEqual(nochmal.angelegt, [])

    def test_nimmt_vorhandenen(self):
        p = FalschesPilos([{"id": "da-111-222", "name": pilos.RAUMNAME, "owner": {"id": 1120}}])
        r = pilos.sitzungsraum({}, self.datei, verbindung=p)
        self.assertEqual((r["id"], r["zugangscode"], p.angelegt), ("da-111-222", "999", []))
        self.assertEqual(json.loads(self.datei.read_text()), r)


if __name__ == "__main__":
    unittest.main()
