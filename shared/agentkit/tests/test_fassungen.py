import tempfile
import unittest
from pathlib import Path

from agentkit import auftraege, fassungen


class TestFassungen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.basis = self.tmp / "instanz" / "auftraege"
        self.agenten = self.tmp
        (self.agenten / "unterricht").mkdir()

    def auftrag(self, text="Arbeitsblatt Kant", bezug=None, erledigen=True, datei=None):
        aid = auftraege.neuer_auftrag("unterricht", text, bezug=bezug, basis=self.basis, agenten_dir=self.agenten)
        if erledigen:
            dateien = []
            if datei:
                (self.agenten / "unterricht" / datei).write_text("x")
                dateien = [datei]
            auftraege.abschliessen(aid, "fertig", dateien=dateien, basis=self.basis, agenten_dir=self.agenten)
        return aid

    def hochgeladen(self, name="Blatt.docx"):
        pfad = self.tmp / name
        pfad.write_text("lias fassung")
        return pfad

    def test_kette_und_ursprung(self):
        a = self.auftrag()
        b = self.auftrag("Nachbesserung", bezug=a)
        c = self.auftrag("noch einmal", bezug=b, erledigen=False)
        anderer = self.auftrag("anderes")
        self.assertEqual(fassungen.ursprung(c, self.basis), a)
        self.assertEqual([x["id"] for x in fassungen.kette(b, self.basis)], [a, b, c])
        self.assertEqual(fassungen.ursprung(anderer, self.basis), anderer)
        with self.assertRaises(fassungen.FassungFehler):
            fassungen.ursprung("20260101-000000-unterricht-abcdef", self.basis)

    def test_final_setzen_und_finale(self):
        a = self.auftrag(datei="a.docx")
        b = self.auftrag("Nachbesserung", bezug=a, datei="b.docx")
        stand = fassungen.final_setzen(a, b, self.basis)
        self.assertEqual(stand["final"]["fassung"], b)
        self.assertEqual(fassungen.lesen(b, self.basis)["final"]["fassung"], b)
        f = fassungen.finale("unterricht", self.basis)
        self.assertEqual([(x["ursprung"], x["dateien"], x["auftrag"]) for x in f], [(a, ["b.docx"], "Arbeitsblatt Kant")])
        fassungen.final_setzen(b, None, self.basis)
        self.assertEqual(fassungen.finale("unterricht", self.basis), [])

    def test_final_nur_fassungen_der_kette(self):
        a = self.auftrag()
        fremd = self.auftrag("anderes")
        offen = self.auftrag("läuft", bezug=a, erledigen=False)
        for falsch in (fremd, offen, "eigene-1", "../x"):
            with self.assertRaises(fassungen.FassungFehler):
                fassungen.final_setzen(a, falsch, self.basis)

    def test_eigene_fassung(self):
        a = self.auftrag()
        b = self.auftrag("Nachbesserung", bezug=a)
        e = fassungen.eigene_dazu(b, self.hochgeladen(), "meine Kommentare", self.basis, self.agenten)
        self.assertEqual(e["n"], 1)
        self.assertEqual(e["datei"], f"data/eingang/{a}/eigene-1/Blatt.docx")
        self.assertEqual((self.agenten / "unterricht" / e["datei"]).read_text(), "lias fassung")
        self.assertFalse((self.tmp / "Blatt.docx").exists())  # verschoben
        e2 = fassungen.eigene_dazu(a, self.hochgeladen(), basis=self.basis, agenten_dir=self.agenten)
        self.assertEqual(e2["datei"], f"data/eingang/{a}/eigene-2/Blatt.docx")
        self.assertEqual(fassungen.grundlage(b, self.basis)["n"], 2)
        fassungen.final_setzen(a, "eigene-2", self.basis)
        self.assertEqual(fassungen.finale("unterricht", self.basis)[0]["dateien"], [e2["datei"]])

    def test_grundlage_nur_nach_letztem_ergebnis(self):
        a = self.auftrag()
        self.assertIsNone(fassungen.grundlage(a, self.basis))
        fassungen.eigene_dazu(a, self.hochgeladen(), basis=self.basis, agenten_dir=self.agenten)
        self.assertIsNotNone(fassungen.grundlage(a, self.basis))
        b = self.auftrag("Nachbesserung", bezug=a)  # neueres Ergebnis des Agenten
        p = self.basis / "erledigt" / f"{b}.json"
        p.write_text(p.read_text().replace('"abgeschlossen": "', '"abgeschlossen": "9'))
        self.assertIsNone(fassungen.grundlage(b, self.basis))

    def test_rueckmeldung(self):
        a = self.auftrag()
        fid, eigene = fassungen.rueckmeldung(a, "siehe Kommentare", self.hochgeladen(), basis=self.basis,
                                             agenten_dir=self.agenten)
        fb = auftraege.neue("feedback", self.basis)[0]
        self.assertEqual((fb["id"], fb["bezug"], fb["quelle"], fb["dateien"]), (fid, a, "feedback", []))
        self.assertEqual(fassungen.grundlage(a, self.basis), eigene)
        fid2, ohne = fassungen.rueckmeldung(a, "nur Text", basis=self.basis, agenten_dir=self.agenten)
        self.assertIsNone(ohne)
        offen = self.auftrag("läuft", bezug=a, erledigen=False)
        with self.assertRaises(fassungen.FassungFehler):
            fassungen.rueckmeldung(offen, "zu früh", basis=self.basis, agenten_dir=self.agenten)

    def test_kopieren_beim_auftrag(self):
        quelle = self.hochgeladen()
        aid = auftraege.neuer_auftrag("unterricht", "x", dateien=[quelle], kopieren=True, basis=self.basis,
                                      agenten_dir=self.agenten)
        self.assertTrue(quelle.exists())
        self.assertEqual(auftraege.neue("unterricht", self.basis)[0]["dateien"], [f"data/eingang/{aid}/Blatt.docx"])

    def test_eigene_pruefungen(self):
        a = self.auftrag()
        with self.assertRaises(fassungen.FassungFehler):
            fassungen.eigene_dazu(a, self.tmp / "fehlt.docx", basis=self.basis, agenten_dir=self.agenten)
        with self.assertRaises(fassungen.FassungFehler):
            fassungen.eigene_dazu(a, self.hochgeladen(), "x" * 3000, basis=self.basis, agenten_dir=self.agenten)


if __name__ == "__main__":
    unittest.main()
