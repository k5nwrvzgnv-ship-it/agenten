"""Adapter Webauftrag -> Wissensbasis (projekt.py), gegen kleine Kopien echter geprueft.json (tests/daten/web)."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import projekt
from agentkit import recherche

DATEN = Path(__file__).parent / "daten" / "web"
STRAFE_V2 = "20261025-211917-lia-reihe-strafe-v2"
MILDE_V1 = "20261114-130748-lia-milde-jugendtaten"
MILDE_V2 = "20261114-133343-lia-milde-jugendtaten-v2"
REGISTER = {"kant-mds-strafrecht": {"id": "kant-mds-strafrecht", "autor": "Immanuel Kant", "werk": "MdS",
                                    "stellen": [{"seite": 331, "zitat": "niemals bloß als Mittel"},
                                                {"seite": 331, "zitat": "vorher strafbar befunden"},
                                                {"seite": 332, "zitat": "Beschimpfst du ihn"}]}}


def lies(ordner: str, datei: str = "geprueft.json") -> dict:
    return json.loads((DATEN / ordner / datei).read_text(encoding="utf-8"))


def basis() -> dict:
    return recherche.neu("test", "Test", "lia", "recherche", fach="Ethik")


class Eingang(unittest.TestCase):
    def test_abschnitte_werden_fragen(self):
        e = projekt.eingang(lies(STRAFE_V2), REGISTER)
        self.assertEqual([f["id"] for f in e["fragen"]], ["F1", "F2"])
        self.assertEqual(e["fragen"][0]["frage"], lies(STRAFE_V2)["abschnitte"][0]["titel"])
        self.assertEqual([a["frage"] for a in e["aussagen"]], ["F1", "F1", "F2", "F2"])

    def test_register_beleg_mit_seite_und_wortlaut(self):
        e = projekt.eingang(lies(STRAFE_V2), REGISTER)
        b = e["aussagen"][0]["belege"][0]
        self.assertEqual((b["register"], b["seite"]), ("kant-mds-strafrecht", "331"))
        self.assertEqual(b["zitat"], "niemals bloß als Mittel […] vorher strafbar befunden")
        self.assertEqual(b["pruefung"], {"status": "bestanden", "grund": "Quellenregister (geprüft)"})
        self.assertEqual(e["quellen"], [{"register": "kant-mds-strafrecht", "titel": "Immanuel Kant: MdS",
                                         "art": "register"}])

    def test_register_unbekannt(self):
        e = projekt.eingang(lies(STRAFE_V2), {})
        self.assertEqual(e["quellen"][0]["titel"], "kant-mds-strafrecht")
        self.assertEqual(e["aussagen"][0]["belege"][0]["zitat"], "")

    def test_art_und_traegt(self):
        e = projekt.eingang(lies(STRAFE_V2), REGISTER)
        hegel, einsch = e["aussagen"][2], e["aussagen"][3]
        self.assertEqual(hegel["art"], "tatsache")
        self.assertEqual(hegel["traegt"]["urteil"], "nein")
        self.assertTrue(hegel["traegt"]["fehlt"])
        self.assertEqual(einsch["art"], "einschaetzung")
        self.assertIsNone(einsch["traegt"])
        self.assertEqual(einsch["belege"], [])

    def test_nicht_geprueft_wird_offen(self):
        d = lies(MILDE_V1)
        d["abschnitte"][0]["aussagen"][0]["traegt"] = {"traegt": "nicht geprüft", "fehlt": ""}
        self.assertEqual(projekt.eingang(d)["aussagen"][0]["traegt"]["urteil"], "offen")

    def test_luecken_rueckfragen(self):
        d = lies(MILDE_V1)
        e = projekt.eingang(d)
        self.assertEqual(e["luecken"], d["luecken"])
        self.assertEqual(e["rueckfragen"], d["rueckfragen"])

    def test_einarbeiten_nimmt_eingang_an_und_status(self):
        b = basis()
        recherche.einarbeiten(b, {"art": "suche"}, projekt.eingang(lies(STRAFE_V2), REGISTER))
        self.assertEqual([a["status"] for a in b["aussagen"]], ["teilweise", "gesichert", "verworfen", "einschaetzung"])
        recherche.einarbeiten(b, {"art": "suche"}, projekt.eingang(lies(MILDE_V1)))
        neu = b["aussagen"][4:]
        self.assertEqual([a["status"] for a in neu], ["gesichert", "teilweise", "unbelegt"])
        self.assertEqual(neu[2]["belege"][0]["pruefung"]["status"], "ungeprueft")


class Kosten(unittest.TestCase):
    def test_kosten(self):
        self.assertEqual(projekt.kosten(lies(MILDE_V1)), 2.6268)

    def test_nachtraeglicher_pruflauf_zaehlt_beide(self):
        self.assertEqual(projekt.kosten(lies(STRAFE_V2), lies(STRAFE_V2, "geprueft_vor_traegt.json")), 2.1122)

    def test_ohne_kosten(self):
        self.assertIsNone(projekt.kosten({}))


class Lauf(unittest.TestCase):
    def test_lauf(self):
        x = projekt.lauf(MILDE_V2, lies(MILDE_V2), 2.0193)
        self.assertEqual(x["art"], "suche")
        self.assertEqual(x["datum"], "2026-11-14T13:33:43")
        self.assertEqual(x["auftrag"], "20261114-134556-recherche-f0c349")
        self.assertEqual(x["ordner"], f"data/web/{MILDE_V2}")
        self.assertEqual(x["zusammenfassung"], lies(MILDE_V2)["kern"])

    def test_lauf_ohne_datum_und_an_lia(self):
        x = projekt.lauf("von-hand", {}, None)
        self.assertIsNone(x["datum"])
        self.assertIsNone(x["auftrag"])


class Einlesen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copytree(DATEN, self.tmp / "data" / "web")

    def ordner(self, *namen):
        return [self.tmp / "data" / "web" / n for n in namen]

    def test_zwei_laeufe_ein_projekt(self):
        b = projekt.einlesen("milde", "Milde", "Ethik", self.ordner(MILDE_V1, MILDE_V2), hier=self.tmp)
        gespeichert = recherche.laden(self.tmp / "data" / "projekte" / "milde" / "wissen.json")
        self.assertEqual(gespeichert, b)
        self.assertEqual([x["nr"] for x in b["laeufe"]], [1, 2])
        self.assertEqual([x["usd"] for x in b["laeufe"]], [2.6268, 2.0193])
        self.assertEqual(len(b["fragen"]), 4)
        # Zweimal „Straftatbestand: Sachbeschädigung.“ ohne Beleg in zwei Fällen: agentkit vereint sie.
        self.assertEqual(b["laeufe"][1]["doppelt"], 1)
        self.assertEqual(len(b["aussagen"]), 3 + 3)
        self.assertTrue(projekt.bericht(b).startswith("milde: 6 Aussagen (1 gesichert"))

    def test_schon_eingelesen_wird_uebersprungen(self):
        projekt.einlesen("milde", "Milde", "Ethik", self.ordner(MILDE_V1), hier=self.tmp)
        b = projekt.einlesen("milde", "anders", "Ethik", self.ordner(MILDE_V1, MILDE_V2), hier=self.tmp)
        self.assertEqual(len(b["laeufe"]), 2)
        self.assertEqual(b["titel"], "Milde")

    def test_gleiche_aussage_im_zweiten_lauf(self):
        pfad = self.tmp / "data" / "web" / MILDE_V2 / "geprueft.json"
        d = json.loads(pfad.read_text(encoding="utf-8"))
        d["abschnitte"][0]["aussagen"].append(lies(MILDE_V1)["abschnitte"][0]["aussagen"][0])
        pfad.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        b = projekt.einlesen("milde", "Milde", "Ethik", self.ordner(MILDE_V1, MILDE_V2), hier=self.tmp)
        self.assertEqual(b["laeufe"][1]["doppelt"], 2)
        self.assertEqual(len(b["aussagen"]), 6)

    def test_ohne_geprueft(self):
        leer = self.tmp / "data" / "web" / "20261113-192903-abgebrochen"
        leer.mkdir()
        with self.assertRaises(FileNotFoundError):
            projekt.einlesen("x", "X", "Ethik", [leer], hier=self.tmp)
        self.assertEqual(recherche.laden(self.tmp / "data" / "projekte" / "x" / "wissen.json")["laeufe"], [])


if __name__ == "__main__":
    unittest.main()
