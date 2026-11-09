import tempfile
import unittest
from pathlib import Path

from agentkit import orte

import logik


def auftrag(id_, status="erledigt", **mehr):
    return {"id": id_, "agent": id_.split("-")[2], "status": status, "text": "Art: Exposé\nThema: Holz",
            "erstellt": f"2026-11-09T{id_[9:11]}:{id_[11:13]}:00+01:00", **mehr}


U = "20261109-100000-uni-aaaaaa"
NB = "20261109-110000-uni-bbbbbb"
FB = "20261109-105000-feedback-cccccc"


class TestBaum(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        i = Path(self._tmp.name)
        self.p = orte.anlegen("Projekt", instanz=i).id
        self.t = orte.anlegen("Teil", self.p, instanz=i).id
        self.k = orte.anlegen("Kapitel", self.t, instanz=i).id
        self.m = orte.anlegen("Modul", instanz=i).id
        orte.anlegen("Unter Modul", self.m, instanz=i)
        self.baum = orte.laden(i)

    def test_baum_klappt_nur_den_weg_auf(self):
        zeilen = logik.baum_zeilen(self.baum, self.t)
        self.assertEqual([(z["text"], z["tiefe"]) for z in zeilen],
                         [("Projekt", 0), ("Teil", 1), ("Kapitel", 2), ("+ Seite", 2), ("Modul", 0)])
        self.assertTrue(zeilen[1]["aktiv"])
        self.assertTrue(zeilen[0]["ueber"])
        self.assertTrue(zeilen[4]["zu"])  # Modul hat zugeklappte Unterseiten
        self.assertEqual(zeilen[3]["link"], f"/seite/neu?eltern={self.t}")
        self.assertEqual([z["text"] for z in logik.baum_zeilen(self.baum, None)], ["Projekt", "Modul"])

    def test_krumen(self):
        self.assertEqual(logik.krumen(self.baum, None), {"teile": [], "hier": "Heute"})
        k = logik.krumen(self.baum, self.k)
        self.assertEqual([t["text"] for t in k["teile"]], ["Heute", "Projekt", "Teil"])
        self.assertEqual(k["hier"], "Kapitel")
        k = logik.krumen(self.baum, self.k, "Exposé Holz")
        self.assertEqual((k["teile"][-1]["link"], k["hier"]), (f"/ort/{self.k}", "Exposé Holz"))
        self.assertEqual(logik.ort_text(self.baum, self.k), "Projekt › Teil › Kapitel")

    def test_ziele_ohne_sich_selbst_und_unterseiten(self):
        ziele = logik.ziele_zum_verschieben(self.baum, self.t)
        self.assertEqual([z["text"] for z in ziele], ["Oberste Ebene", "Projekt", "Modul", "Unter Modul"])
        self.assertTrue(next(z for z in ziele if z["id"] == self.p)["jetzt"])


class TestDokumente(unittest.TestCase):
    def test_kette_mit_nachbesserung_ist_ein_dokument(self):
        alle = [auftrag(U, ort="kapitel", art="expose", felder={"Thema": "Holz"}, abgeschlossen="2026-11-09T10:30:00",
                        ergebnis_dateien=["data/x/Expose-Holz.pdf"]),
                auftrag(FB, bezug=U),
                auftrag(NB, status="neu", bezug=U, ort="kapitel", art="expose")]
        docs = logik.dokumente(alle, "kapitel", {"expose": "Exposé"}, {})
        self.assertEqual(len(docs), 1)
        d = docs[0]
        self.assertEqual((d["id"], d["titel"], d["marke"], d["art"], d["fassungen"]),
                         (U, "Expose-Holz", "Läuft", "Exposé", 1))
        self.assertEqual(logik.dokumente(alle, "anders", {}, {}), [])
        self.assertEqual(len(logik.dokumente(alle, None, {}, {})), 1)

    def test_titel_und_marke(self):
        namen = {"expose": "Exposé"}
        u = auftrag(U, status="neu", art="expose", felder={"Thema": "Holz", "Hinweise": ""})
        self.assertEqual(logik.titel_von([u], namen), "Exposé: Holz")
        self.assertEqual(logik.titel_von([auftrag(U, status="neu")], {}), "Art: Exposé")
        fertig = auftrag(U, daten={"titel": "Holzschutz im Bestand"}, ergebnis_dateien=["a/b.pdf"])
        self.assertEqual(logik.titel_von([fertig], namen), "Holzschutz im Bestand")
        self.assertEqual(logik.marke_von([fertig], None), ("Fassung 1", False))
        self.assertEqual(logik.marke_von([fertig], {"fassung": U}), ("Final", False))
        self.assertEqual(logik.marke_von([fertig, auftrag(NB, status="fehlgeschlagen")], None),
                         ("Hat nicht geklappt", True))
        self.assertEqual(logik.marke_von([auftrag(U, status="zurueckgezogen")], None), ("Zurückgezogen", False))

    def test_laufend_nur_arbeitsplatz(self):
        alle = [auftrag(U, status="neu", quelle="arbeitsplatz", art="expose", felder={"Thema": "Holz"}),
                auftrag("20261109-120000-uni-dddddd", status="neu", quelle="telegram"),
                auftrag(FB, status="neu", quelle="feedback")]
        z = logik.laufend(alle, {"expose": "Exposé"})
        self.assertEqual([(x["id"], x["titel"]) for x in z], [(U, "Exposé: Holz")])


class TestSchutz(unittest.TestCase):
    def test_herkunft(self):
        self.assertTrue(logik.herkunft_passt("https://a.de", "a.de", "same-origin"))
        self.assertTrue(logik.herkunft_passt("http://localhost:8795", "localhost:8795", None))
        for origin, host, site in [(None, "a.de", None), ("null", "a.de", None), ("https://b.de", "a.de", None),
                                   ("https://a.de", "a.de", "cross-site")]:
            self.assertFalse(logik.herkunft_passt(origin, host, site))

    def test_token_und_ziel(self):
        self.assertTrue(logik.token_passt(b"g", logik.formular_token(b"g")))
        self.assertFalse(logik.token_passt(b"g", logik.formular_token(b"h")))
        self.assertFalse(logik.token_passt(b"g", ""))
        self.assertEqual(logik.ziel_sicher("/ort/a?x=1"), "/ort/a?x=1")
        for boese in ["//boese.de", "https://boese.de", "ort", "/a\r\nSet-Cookie: x"]:
            self.assertEqual(logik.ziel_sicher(boese), "/")

    def test_port_und_zeit(self):
        self.assertIsNone(logik.port_pruefen(""))
        self.assertEqual(logik.port_pruefen("8794"), 8794)
        with self.assertRaises(ValueError):
            logik.port_pruefen("80")
        self.assertEqual(logik.zeit_kurz("2026-11-09T14:16:00+01:00", "2026-11-09"), "heute 14:16")
        self.assertEqual(logik.zeit_kurz("2026-11-08T14:16:00+01:00", "2026-11-09"), "08.11. 14:16")


if __name__ == "__main__":
    unittest.main()
