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


class TestDokumentAnsicht(unittest.TestCase):
    def test_fassungen_haupt_final_und_rueckmeldung(self):
        kette = [auftrag(U, abgeschlossen="2026-11-09T10:30:00", daten={"kern": "Kurz", "punkte": ["a", 3]},
                         ergebnis_dateien=["data/x/E.docx", "data/x/E.pdf"]),
                 auftrag(NB, bezug=U, abgeschlossen="2026-11-09T11:30:00", ergebnis_dateien=["data/x/E2.docx"])]
        stand = {"final": None, "eigene": [
            {"n": 1, "name": "Meine.docx", "zeit": "2026-11-09T12:00:00", "art": "fassung", "notiz": ""},
            {"n": 2, "name": "Notizen.pdf", "zeit": "2026-11-09T12:05:00", "art": "unklar"}]}
        vorschauen = {U: [(True, True, 2), (True, False, 0)], NB: [(True, False, 0)]}
        d = logik.dokument_ansicht(kette, [auftrag(FB, bezug=NB, ergebnis="Mache ich")], stand, vorschauen,
                                   {U: 0.5, NB: 0.25}, {"rueckmeldung": True}, "2026-11-09")
        self.assertEqual([f["name"] for f in d["fassungen"]], ["Deine Fassung 1", "Fassung 2", "Fassung 1"])
        self.assertEqual(d["haupt"]["ref"], "eigene-1")
        self.assertEqual(d["bezug"], NB)  # Rückmeldung an die neueste Fassung des Agenten
        self.assertEqual(d["kosten"], 0.75)
        self.assertEqual([a["name"] for a in d["anmerkungen"]], ["Notizen.pdf"])
        f1 = d["fassungen"][2]
        self.assertEqual(f1["punkte"], ["a"])
        self.assertEqual([(x["name"], x["pdf"], x["seiten"]) for x in f1["dateien"]],
                         [("E.docx", True, 2), ("E.pdf", True, 0)])
        self.assertTrue(logik.final_erlaubt(U, d))
        self.assertFalse(logik.final_erlaubt("eigene-2", d))  # nur Anmerkungen, keine Fassung
        stand["final"] = {"fassung": U}
        d = logik.dokument_ansicht(kette, [], stand, vorschauen, {}, {"rueckmeldung": False}, "2026-11-09")
        self.assertEqual(d["haupt"]["ref"], U)
        self.assertFalse(d["rueckmeldung_moeglich"])
        self.assertIsNone(d["kosten"])

    def test_laeuft_ohne_fertige_fassung(self):
        d = logik.dokument_ansicht([auftrag(U, status="neu")], [], {}, {}, {}, None, "2026-11-09")
        self.assertTrue(d["laeuft"])
        self.assertIsNone(d["haupt"])
        self.assertFalse(d["rueckmeldung_moeglich"])

    def test_pruefen_und_namen(self):
        self.assertEqual(logik.rueckmeldung_pruefen("  x\r\ny ", False), ("x\ny", []))
        self.assertTrue(logik.rueckmeldung_pruefen("", False)[1])
        self.assertEqual(logik.rueckmeldung_pruefen("", True)[1], [])
        self.assertTrue(logik.rueckmeldung_pruefen("x" * 4001, False)[1])
        self.assertEqual(logik.datei_erlaubt("a.DOCX", {".docx"}), "")
        self.assertTrue(logik.datei_erlaubt("a.exe", {".docx"}))
        self.assertEqual(logik.dateiname_bereinigen("..\\..\\böse<>.docx"), "böse__.docx")
        self.assertEqual(logik.dateiname_bereinigen(".env"), "env")

    def test_wartet_und_kosten(self):
        docs = [{"marke": "Fassung 1", "rot": False, "zeit": "2026-11-08T10:00"},
                {"marke": "Fassung 2", "rot": False, "zeit": "2026-10-01T10:00"},
                {"marke": "Final", "rot": False, "zeit": "2026-11-09T10:00"},
                {"marke": "Hat nicht geklappt", "rot": True, "zeit": "2026-09-01T10:00"},
                {"marke": "Läuft", "rot": False, "zeit": "2026-11-09T10:00"}]
        self.assertEqual([d["marke"] for d in logik.wartet_auf_mich(docs, "2026-11-09")],
                         ["Fassung 1", "Hat nicht geklappt"])
        z = logik.kosten_zeilen([{"zeit": 1794256394, "agent": "uni", "auftrag": NB, "usd": 0.123, "ok": True},
                                 {"zeit": None, "agent": "finance", "auftrag": "x", "usd": None, "ok": False}],
                                {NB: U}, {U: "Exposé"})
        self.assertEqual([(x["text"], x["usd"], x["link"], x["ok"]) for x in z],
                         [("Exposé", "0.12", f"/dokument/{U}", True), ("", "0.00", "", False)])


class TestZuordnung(unittest.TestCase):
    def test_alte_ergebnisse_ueber_zuordnung(self):
        alle = [auftrag(U, ergebnis_dateien=["a/E.pdf"]), auftrag(NB, bezug=U),
                auftrag("20261109-120000-uni-dddddd", ort="hier")]
        z = logik.zuordnung_pruefen({"zuordnung": {U: "expose", "../x": "expose", NB: "Böse Id", "x": 3}})
        self.assertEqual(z, {U: "expose"})
        self.assertEqual([d["id"] for d in logik.dokumente(alle, "expose", {}, {}, z)], [U])
        self.assertEqual(logik.dokumente(alle, "expose", {}, {}), [])
        self.assertEqual(len(logik.dokumente(alle, None, {}, {}, z)), 2)
        # Feld ort im Auftrag geht vor
        self.assertEqual(logik.ort_von({"id": U, "ort": "hier"}, {U: "expose"}), "hier")
        self.assertEqual(logik.zuordnung_pruefen([]), {})


class TestBetrachterUndZiel(unittest.TestCase):
    """umbauplan-ux.md Schritt 6: Seiten-Betrachter und Rückmeldung an einer Datei/Seite."""

    def test_betrachter(self):
        b = logik.betrachter(3, "2", "/x/ansehen")
        self.assertEqual((b["seite"], b["anzahl"], b["vorher"], b["nachher"]),
                         (2, 3, "/x/ansehen?seite=1", "/x/ansehen?seite=3"))
        self.assertEqual([s["aktiv"] for s in b["seiten"]], [False, True, False])
        self.assertEqual(logik.betrachter(3, None, "/x")["seite"], 1)
        self.assertEqual(logik.betrachter(1, "1", "/x")["nachher"], "")
        for falsch in ("0", "4", "x", "-1"):
            self.assertIsNone(logik.betrachter(3, falsch, "/x"), falsch)
        self.assertIsNone(logik.betrachter(0, "1", "/x"))

    def test_rueckmeldung_ziel(self):
        kette = [{"id": "a1", "status": "erledigt", "ergebnis_dateien": ["data/x/Expose.docx", "data/x/Expose.pdf"]},
                 {"id": "a2", "status": "neu", "ergebnis_dateien": ["data/y.pdf"]}]
        ansicht = {"fassungen": [{"ref": "a1", "name": "Fassung 1"}]}
        z = logik.rueckmeldung_ziel(kette, ansicht, "a1", "1", "3")
        self.assertEqual((z["fassung"], z["nr"], z["seite"], z["text"], z["fassung_name"]),
                         ("a1", 1, 3, "„Expose.pdf“, Seite 3", "Fassung 1"))
        self.assertEqual(logik.rueckmeldung_ziel(kette, ansicht, "a1", "0", "")["text"], "„Expose.docx“")
        for fassung, nr in (("a2", "0"), ("a1", "2"), ("a1", "x"), ("zz", "0"), ("", "")):
            self.assertIsNone(logik.rueckmeldung_ziel(kette, ansicht, fassung, nr, ""), (fassung, nr))
        self.assertEqual(logik.rueckmeldung_ziel(kette, ansicht, "a1", "0", "1000")["seite"], "")
        self.assertEqual(logik.rueckmeldung_text("kürzer", z), "Zur Datei „Expose.pdf“, Seite 3: kürzer")
        self.assertEqual(logik.rueckmeldung_text("", None), "Siehe angehängte Datei.")
        self.assertEqual(logik.rueckmeldung_text("kürzer", None), "kürzer")

    def test_datei_zeilen_mit_vorschau_laeuft(self):
        z = logik._datei_zeilen(["a.pdf", "b.docx"], [(True, False, 0, True), (True, True, 4)])
        self.assertEqual([(x["vorschau_laeuft"], x["seiten"], x["pdf"]) for x in z], [(True, 0, True), (False, 4, True)])
