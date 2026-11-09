"""Tests für bericht.py (Renderer-Beschreibungen aus geprüften Schritten) und agent.dokumente (ohne Netz)."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import renderer

import ablauf
import agent
import bericht
from tests.test_ablauf import GUELTIG, annahme

HEUTE = date(2026, 11, 9)
QID = "Q-20261109-web-abcdef"
META = {QID: {"id": QID, "art": "web", "beschreibung": "GB 2025", "abgerufen": "2026-11-09T12:00:00+01:00",
              "url": "https://firma.de/gb"}}


def quelle(wert, einheit="%"):
    return {"wert": wert, "einheit": einheit, "quelle": QID}


def daten():
    d = {n: dict(v) for n, v in GUELTIG.items()}
    d[1] = {"thema": "Robotik", "offene_punkte": [f"Siehe {QID} für Details"],
            "stufen": [{"name": "Hersteller", "beschreibung": f"Text mit [{QID}] darin",
                        "firmen": [{"name": "X", "jahr": 2025, "marge": quelle(8.2)}]}]}
    return d


class Zahlen(unittest.TestCase):
    def test_zahl_text_deutsch(self):
        self.assertEqual(bericht.zahl_text(1234.5), "1.234,5")
        self.assertEqual(bericht.zahl_text(51065645), "51.065.645")
        self.assertEqual(bericht.zahl_text(0.0478), "0,0478")
        self.assertEqual(bericht.zahl_text(-65124.0), "-65.124")

    def test_zelle_mit_beleg_und_annahme(self):
        self.assertEqual(bericht.zelle(quelle(8.2)),
                         {"text": "8,2 %", "quellen": [{"art": "quelle", "stelle": QID}]})
        self.assertEqual(bericht.zelle(annahme(3))["kennzeichnung"], "annahme")
        berechnet = {"wert": 16.4, "einheit": "%", "berechnet": {"art": "summe", "aus": [quelle(8.2), annahme(8.2)]}}
        z = bericht.zelle(berechnet)
        self.assertEqual((z["kennzeichnung"], z["quellen"][0]["stelle"]), ("annahme", QID))
        self.assertEqual(bericht.zelle(None), "")


class Beschreibung(unittest.TestCase):
    def test_gueltig_fuer_renderer_ohne_ids_im_text(self):
        b = bericht.beschreibung("Robotik", daten(), META, HEUTE)
        renderer.pruefen(b)
        self.assertEqual(b["quellenverzeichnis"][0]["id"], QID)
        self.assertNotIn(QID, b["offene_fragen"][0])
        absaetze = [x["text"] for x in b["bloecke"] if x["typ"] == "absatz"]
        self.assertTrue(all(QID not in t for t in absaetze))
        self.assertIn("Hypothesen", [x["text"] for x in b["bloecke"] if x["typ"] == "ueberschrift"])

    def test_abgebrochen_und_unbekannte_quelle(self):
        d = daten()
        del d[5]
        b = bericht.beschreibung("Robotik", d, {}, HEUTE, abgebrochen=(5, ["Lauf ohne Ergebnis"]))
        renderer.pruefen(b)
        self.assertEqual(b["bloecke"][0]["titel"], "Recherche unvollständig")
        self.assertIn("Schritte 1, 2, 3, 4", b["bloecke"][0]["text"])
        self.assertNotIn("quellenverzeichnis", b)
        tabelle = next(x for x in b["bloecke"] if x["typ"] == "tabelle")
        self.assertEqual(tabelle["zeilen"][0][3], {"text": "8,2 %", "kennzeichnung": "unsicher"})

    def test_modell_rechnet_wie_die_pruefung(self):
        m = bericht.modell("Robotik", daten())
        renderer.pruefen(m)
        markt = m["blaetter"][0]["werte"][0]
        self.assertEqual((markt["f1"], markt["f2"], markt["f3"]), (1200, 0.25, 80000))
        self.assertIn("Annahme", markt["e1"])
        self.assertEqual(len(m["blaetter"][1]["werte"]), 3)  # drei Szenarien
        self.assertIsNone(bericht.modell("Robotik", {1: daten()[1]}))

    def test_aus_ergebnissen(self):
        erg = [ablauf.SchrittErgebnis(1, True, daten={"a": 1}), ablauf.SchrittErgebnis(0, True),
               ablauf.SchrittErgebnis(2, False, fehler=["x"], daten={"b": 2})]
        self.assertEqual(bericht.aus_ergebnissen(erg), ({1: {"a": 1}}, (2, ["x"])))


class Dokumente(unittest.TestCase):
    def test_fehler_des_renderers_gehen_an_jan(self):
        erg = [ablauf.SchrittErgebnis(n, True, daten=d) for n, d in daten().items()]
        aufrufe = []

        def bauen(beschreibung, ziel, profil, vorschau):
            aufrufe.append((beschreibung["art"], ziel.name, vorschau, profil["erstellt_von"]))
            if beschreibung["art"] == "arbeitsmappe":
                raise renderer.BeschreibungUngueltig(["blaetter[0]: kaputt"])
            return mock.Mock(pdf=ziel.with_suffix(".pdf"), pfad=ziel, hinweise=[])

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(agent, "QUELLEN", Path(tmp)), \
                mock.patch.object(agent, "logger"):  # nicht ins echte Log schreiben
            dateien, fehler = agent.dokumente("Robotik", erg, Path(tmp), _bauen=bauen)
        self.assertEqual([d.name for d in dateien], ["bericht.pdf"])
        self.assertEqual(aufrufe[0], ("bericht", "bericht.docx", True, "Agent finance"))
        self.assertIn("Modell nicht gebaut", fehler[0])


if __name__ == "__main__":
    unittest.main()
