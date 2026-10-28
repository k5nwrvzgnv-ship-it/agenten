import json
import tempfile
import unittest
from pathlib import Path

import sprachpruefung


def plan(**f):
    return {
        "modul": "Holzschutz und Sanierung",
        "teile": {"IHS": "Integrierter Holzschutz, Prof. Dr. A. Muster", "SHB": "Sanierung, Prof. B. Beispiel"},
        "pruefung": {"form": "Vortrag mit mündlicher Prüfung", "termin": "Januar 2027"},
        "themen": [
            {"id": "gk", "teil": "IHS+SHB", "titel": "Gebrauchsklassen", "score": 4,
             "lernziele": [{"text": "GK zuordnen", "aufgabentyp": "Zuordnen"}], "quellen": ["DIN 68800-1"]},
            {"id": "pilze", "teil": "IHS", "titel": "Pilze bestimmen", "score": 5, "lernziele": [], "quellen": []},
            {"id": "dach", "teil": "SHB", "titel": "Dachtragwerke", "score": 3},
        ],
    } | f


def karte(**f):
    return {"id": "k1", "thema": "pilze", "typ": "text", "frage": "Was ist Würfelbruch?",
            "antwort": "Risse längs und quer.", "quelle": "IHS S. 90", "bild": None} | f


class TestSprachpruefung(unittest.TestCase):
    def test_themen_des_teils_filtert_und_sortiert(self):
        titel = [t["titel"] for t in sprachpruefung.themen_des_teils(plan(), "IHS")]
        self.assertEqual(titel, ["Pilze bestimmen", "Gebrauchsklassen"])

    def test_teil_fehlt(self):
        with self.assertRaises(sprachpruefung.PaketFehler):
            sprachpruefung.teil_lesen(plan(), "XYZ")

    def test_teil_ohne_pruefer(self):
        with self.assertRaises(sprachpruefung.PaketFehler):
            sprachpruefung.teil_lesen(plan(teile={"IHS": "Integrierter Holzschutz"}), "IHS")

    def test_prompt_enthaelt_rolle_und_themen(self):
        text = sprachpruefung.prompt_bauen(plan(), "IHS")
        self.assertIn("Prof. Dr. A. Muster", text)
        self.assertIn("- 5: Pilze bestimmen\n- 4: Gebrauchsklassen", text)
        self.assertNotIn("Dachtragwerke", text)

    def test_prompt_ohne_themen(self):
        with self.assertRaises(sprachpruefung.PaketFehler):
            sprachpruefung.prompt_bauen(plan(themen=[]), "IHS")

    def test_wissen_themen_bildkarte_ohne_bildfrage(self):
        karten = [karte(), karte(id="k2", typ="bild", frage="Welcher Schädling ist das?",
                                 antwort="Echter Hausschwamm.\nStränge knacken."),
                  karte(id="k3", thema="dach", antwort="Kehlbalken.")]
        text = sprachpruefung.wissen_themen(plan(), karten, "IHS")
        self.assertIn("### Was ist Würfelbruch?", text)
        self.assertIn("### Merkmale: Echter Hausschwamm.\n\nEchter Hausschwamm.\nStränge knacken.", text)
        self.assertNotIn("Welcher Schädling ist das?", text)
        self.assertNotIn("Kehlbalken", text)
        self.assertIn("- GK zuordnen (Zuordnen)", text)

    def test_paket_bauen(self):
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            modul = basis / "lernen" / "holzschutz"
            modul.mkdir(parents=True)
            (modul / "pruefungsplan.json").write_text(json.dumps(plan()), encoding="utf-8")
            (modul / "karten.json").write_text(json.dumps([karte()]), encoding="utf-8")
            transkripte = basis / "kurse" / "Integrierter Holzschutz" / "transkripte"
            transkripte.mkdir(parents=True)
            (transkripte / "2026-10-20.md").write_text("# Vorlesung 1\nDKL gilt für Kernholz.", encoding="utf-8")
            ziel = sprachpruefung.paket_bauen(modul, basis / "kurse", "IHS")
            self.assertEqual(sorted(p.name for p in ziel.iterdir()),
                             ["ANLEITUNG.md", "begruessung.txt", "prompt.md", "wissen_themen.md",
                              "wissen_vorlesung.md"])
            self.assertIn("DKL gilt für Kernholz.", (ziel / "wissen_vorlesung.md").read_text(encoding="utf-8"))
            self.assertIn("sprachpruefung.py holzschutz IHS", (ziel / "ANLEITUNG.md").read_text(encoding="utf-8"))

    def test_paket_ohne_transkripte(self):
        with tempfile.TemporaryDirectory() as tmp:
            modul = Path(tmp) / "holzschutz"
            modul.mkdir()
            (modul / "pruefungsplan.json").write_text(json.dumps(plan()), encoding="utf-8")
            with self.assertRaises(sprachpruefung.PaketFehler):
                sprachpruefung.paket_bauen(modul, Path(tmp) / "kurse", "IHS")


if __name__ == "__main__":
    unittest.main()
