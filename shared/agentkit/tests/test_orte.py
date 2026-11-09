import json
import tempfile
import threading
import unittest
from pathlib import Path

from agentkit import orte


class TestOrte(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.inst = Path(self._tmp.name)

    def anlegen(self, titel, eltern=None):
        return orte.anlegen(titel, eltern, instanz=self.inst).id

    def baum(self):
        return orte.laden(self.inst)

    def test_leer_ohne_datei(self):
        self.assertEqual(self.baum(), [])

    def test_anlegen_mit_lesbarer_id_und_reihenfolge(self):
        p = self.anlegen("Forschungsprojekt Fehlstellen")
        t = self.anlegen("Schriftlicher Teil", p)
        k = self.anlegen("Kapitel 3", t)
        self.assertEqual(p, "forschungsprojekt-fehlstellen")
        self.assertEqual(self.anlegen("Kapitel 3", t), "kapitel-3-2")  # gleicher Titel: neue id
        self.assertEqual(self.anlegen("Größe & Übung"), "groesse-uebung")
        self.assertEqual([x["titel"] for x in orte.pfad(self.baum(), k)],
                         ["Forschungsprojekt Fehlstellen", "Schriftlicher Teil", "Kapitel 3"])
        self.assertEqual([x["position"] for x in orte.kinder(self.baum(), t)], [0, 1])
        self.assertEqual(orte.anlegen("Fest", ort_id="finanzen", instanz=self.inst).id, "finanzen")
        for falsch in ["", "   ", "x" * 201, None]:
            with self.subTest(titel=falsch), self.assertRaises(orte.OrtFehler):
                orte.anlegen(falsch, instanz=self.inst)
        with self.assertRaises(orte.OrtFehler):
            orte.anlegen("x", eltern="gibt-es-nicht", instanz=self.inst)
        with self.assertRaises(orte.OrtFehler):
            orte.anlegen("x", ort_id="finanzen", instanz=self.inst)
        with self.assertRaises(orte.OrtFehler):
            orte.anlegen("x", ort_id="../x", instanz=self.inst)

    def test_umbenennen_behaelt_id(self):
        m = self.anlegen("Modul Holzschutz")
        aus = orte.umbenennen(m, "  Holzschutz   II ", instanz=self.inst)
        self.assertEqual(aus.text, "„Modul Holzschutz“ heißt jetzt „Holzschutz II“")
        self.assertEqual([(x["id"], x["titel"]) for x in self.baum()], [(m, "Holzschutz II")])

    def test_verschieben_ohne_zyklus(self):
        a, b = self.anlegen("A"), self.anlegen("B")
        a1 = self.anlegen("A1", a)
        a11 = self.anlegen("A11", a1)
        for ziel in (a, a1, a11):
            with self.subTest(ziel=ziel), self.assertRaises(orte.OrtFehler):
                orte.verschieben(a, ziel, instanz=self.inst)
        orte.verschieben(a1, b, instanz=self.inst)
        self.assertEqual(orte.pfad(self.baum(), a11)[0]["id"], b)
        orte.verschieben(b, None, 0, instanz=self.inst)  # Reihenfolge oben: B, A
        self.assertEqual([x["id"] for x in orte.kinder(self.baum(), None)], [b, a])
        orte.verschieben(a1, None, 1, instanz=self.inst)
        self.assertEqual([(x["id"], x["position"]) for x in orte.kinder(self.baum(), None)], [(b, 0), (a1, 1), (a, 2)])
        with self.assertRaises(orte.OrtFehler):
            orte.verschieben(a, None, -1, instanz=self.inst)

    def test_archivieren_und_wiederherstellen(self):
        a = self.anlegen("A")
        a1 = self.anlegen("A1", a)
        orte.archivieren(a, instanz=self.inst)
        baum = self.baum()
        self.assertEqual(orte.kinder(baum, None), [])
        self.assertFalse(orte.sichtbar(baum, a1))
        self.assertEqual([x["id"] for x in orte.archiv(baum)], [a])  # nur der oberste des Zweigs
        with self.assertRaises(orte.OrtFehler):
            orte.archivieren(a, instanz=self.inst)
        orte.wiederherstellen(a, instanz=self.inst)
        self.assertTrue(orte.sichtbar(self.baum(), a1))
        with self.assertRaises(orte.OrtFehler):
            orte.wiederherstellen(a, instanz=self.inst)

    def test_rueckgaengig(self):
        a = self.anlegen("A")
        aus = orte.umbenennen(a, "B", instanz=self.inst)
        zurueck = orte.rueckgaengig(aus.aktion, instanz=self.inst)
        self.assertEqual(self.baum()[0]["titel"], "A")
        self.assertEqual(zurueck.text, "Rückgängig: „A“ heißt jetzt „B“")
        orte.rueckgaengig(zurueck.aktion, instanz=self.inst)  # Rückgängig vom Rückgängig
        self.assertEqual(self.baum()[0]["titel"], "B")
        neu = orte.anlegen("C", a, instanz=self.inst)
        orte.rueckgaengig(neu.aktion, instanz=self.inst)
        self.assertEqual([x["id"] for x in self.baum()], [a])
        # Konflikt: nach der Aktion weiter geändert
        aus = orte.umbenennen(a, "D", instanz=self.inst)
        orte.umbenennen(a, "E", instanz=self.inst)
        with self.assertRaises(orte.Konflikt):
            orte.rueckgaengig(aus.aktion, instanz=self.inst)
        with self.assertRaises(orte.OrtFehler):
            orte.rueckgaengig("gibt-es-nicht", instanz=self.inst)
        letzte = orte.letzte(3, self.inst)
        self.assertEqual([x["text"] for x in letzte][:2], ["„D“ heißt jetzt „E“", "„B“ heißt jetzt „D“"])

    def test_rueckgaengig_anlegen_mit_kind_ist_konflikt(self):
        aus = orte.anlegen("A", instanz=self.inst)
        self.anlegen("A1", aus.id)
        with self.assertRaises(orte.Konflikt):
            orte.rueckgaengig(aus.aktion, instanz=self.inst)

    def test_kaputte_datei(self):
        for inhalt in ["kein json", '{"orte": {}}', '{"orte": [{"id": "A", "titel": "x"}]}',
                       '{"orte": [{"id": "a", "titel": "x", "eltern": "b"}]}',
                       '{"orte": [{"id": "a", "titel": "x", "eltern": "b"}, {"id": "b", "titel": "y", "eltern": "a"}]}',
                       '{"orte": [{"id": "a", "titel": "x"}, {"id": "a", "titel": "y"}]}']:
            (self.inst / orte.DATEI).write_text(inhalt)
            with self.subTest(inhalt=inhalt), self.assertRaises(orte.OrtFehler):
                orte.laden(self.inst)

    def test_gleichzeitig_anlegen_verliert_nichts(self):
        faeden = [threading.Thread(target=self.anlegen, args=(f"Seite {i}",)) for i in range(12)]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join()
        baum = self.baum()
        self.assertEqual(len(baum), 12)
        self.assertEqual(sorted(x["position"] for x in baum), list(range(12)))
        gespeichert = json.loads((self.inst / orte.DATEI).read_text())
        self.assertEqual(len(gespeichert["orte"]), 12)


if __name__ == "__main__":
    unittest.main()
