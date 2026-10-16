import tempfile
import unittest
from pathlib import Path

from agentkit import auftraege, freigabe


class TestFreigabe(unittest.TestCase):
    def setUp(self):
        self.basis = Path(tempfile.mkdtemp())

    def test_ablauf_freigeben(self):
        eid = freigabe.neuer_entwurf("uni", "Mail an Prof", "Hallo ...", typ="mail",
                                     daten={"an": "prof@example.org"}, basis=self.basis)
        offen = freigabe.offene("uni", basis=self.basis)
        self.assertEqual([e["id"] for e in offen], [eid])
        self.assertEqual(offen[0]["daten"], {"an": "prof@example.org"})
        self.assertEqual(freigabe.offene("einkauf", basis=self.basis), [])

        ergebnis = freigabe.entscheide(eid, "freigegeben", basis=self.basis)
        self.assertEqual(ergebnis["status"], "freigegeben")
        self.assertEqual(freigabe.offene(basis=self.basis), [])
        self.assertEqual(freigabe.erledigte("uni", basis=self.basis)[0]["status"], "freigegeben")
        # keine Reste (temporäre Dateien) übrig
        self.assertEqual(sorted(p.name for p in (self.basis / "erledigt").iterdir()), [f"{eid}.json"])

    def test_nicht_doppelt_entscheiden(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        freigabe.entscheide(eid, "abgelehnt", "passt nicht", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "freigegeben", basis=self.basis)

    def test_aendern_braucht_kommentar_und_vorgaenger(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "aendern", basis=self.basis)
        freigabe.entscheide(eid, "aendern", "kürzer bitte", basis=self.basis)
        neu = freigabe.neuer_entwurf("uni", "t", "kurz", vorgaenger=eid, basis=self.basis)
        self.assertEqual(freigabe.offene(basis=self.basis)[0]["vorgaenger"], eid)
        self.assertNotEqual(neu, eid)

    def test_ungueltige_eingaben(self):
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide("../../etc/passwd", "freigegeben", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.neuer_entwurf("Uni/../x", "t", "i", basis=self.basis)
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "vielleicht", basis=self.basis)


class TestAuftraege(unittest.TestCase):
    def setUp(self):
        self.basis = Path(tempfile.mkdtemp())

    def test_ablauf(self):
        a1 = auftraege.neuer_auftrag("einkauf", "Geschenk für Mama", basis=self.basis)
        a2 = auftraege.neuer_auftrag("uni", "Fristen prüfen", basis=self.basis)
        self.assertEqual([a["id"] for a in auftraege.neue("einkauf", basis=self.basis)], [a1])
        self.assertEqual(len(auftraege.neue(basis=self.basis)), 2)

        auftraege.abschliessen(a1, "3 Vorschläge in Freigabe", basis=self.basis)
        self.assertEqual([a["id"] for a in auftraege.neue(basis=self.basis)], [a2])
        fertig = auftraege.erledigte("einkauf", basis=self.basis)[0]
        self.assertEqual((fertig["status"], fertig["ergebnis"]), ("erledigt", "3 Vorschläge in Freigabe"))
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.abschliessen(a1, basis=self.basis)

    def test_fehlgeschlagen_und_bezug(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis / "f")
        aid = auftraege.neuer_auftrag("uni", "anders formulieren", bezug=eid, basis=self.basis)
        self.assertEqual(auftraege.neue(basis=self.basis)[0]["bezug"], eid)
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.abschliessen(aid, status="halb", basis=self.basis)
        self.assertEqual(auftraege.abschliessen(aid, "Timeout", "fehlgeschlagen", basis=self.basis)["status"],
                         "fehlgeschlagen")


if __name__ == "__main__":
    unittest.main()
