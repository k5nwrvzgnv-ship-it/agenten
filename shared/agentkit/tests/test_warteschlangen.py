import json
import tempfile
import unittest
from pathlib import Path

from agentkit import auftraege, freigabe


def freigeben(eid, basis):
    """Wie die Telegram-Zentrale: Fingerabdruck des angezeigten Entwurfs mitgeben."""
    angezeigt = next(e for e in freigabe.offene(basis=basis) if e["id"] == eid)
    return freigabe.entscheide(eid, "freigegeben", gesehen=angezeigt["fingerabdruck"], basis=basis)


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

        ergebnis = freigeben(eid, self.basis)
        self.assertEqual(ergebnis["status"], "freigegeben")
        self.assertEqual(freigabe.offene(basis=self.basis), [])
        self.assertEqual(freigabe.erledigte("uni", basis=self.basis)[0]["status"], "freigegeben")
        # keine Reste (temporäre Dateien) übrig
        self.assertEqual(sorted(p.name for p in (self.basis / "erledigt").iterdir()), [f"{eid}.json"])

    def test_nicht_doppelt_entscheiden(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        freigabe.entscheide(eid, "abgelehnt", "passt nicht", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "freigegeben", gesehen="0" * 64, basis=self.basis)

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


class TestAusfuehrung(unittest.TestCase):
    def setUp(self):
        self.basis = Path(tempfile.mkdtemp())

    def test_freigeben_ohne_oder_mit_falschem_fingerabdruck(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "freigegeben", basis=self.basis)
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "freigegeben", gesehen="0" * 64, basis=self.basis)
        self.assertEqual(len(freigabe.offene(basis=self.basis)), 1)

    def test_entwurf_nach_anzeige_veraendert(self):
        eid = freigabe.neuer_entwurf("uni", "t", "Original", basis=self.basis)
        alter_abdruck = freigabe.offene(basis=self.basis)[0]["fingerabdruck"]
        pfad = self.basis / "offen" / f"{eid}.json"
        daten = json.loads(pfad.read_text())
        daten["inhalt"] = "Heimlich geändert"
        pfad.write_text(json.dumps(daten))
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.entscheide(eid, "freigegeben", gesehen=alter_abdruck, basis=self.basis)

    def test_ablauf_genau_einmal(self):
        eid = freigabe.neuer_entwurf("posteingang", "Antwort", "Hallo", typ="mail", basis=self.basis)
        freigeben(eid, self.basis)
        self.assertEqual([e["id"] for e in freigabe.zur_ausfuehrung("posteingang", basis=self.basis)], [eid])

        entwurf = freigabe.ausfuehrung_beginnen(eid, basis=self.basis)
        self.assertEqual(entwurf["inhalt"], "Hallo")
        self.assertEqual(freigabe.zur_ausfuehrung(basis=self.basis), [])
        self.assertEqual([e["id"] for e in freigabe.unklare(basis=self.basis)], [eid])
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.ausfuehrung_beginnen(eid, basis=self.basis)

        fertig = freigabe.ausfuehrung_abschliessen(eid, "Mail gesendet", basis=self.basis)
        self.assertTrue(fertig["erfolgreich"])
        self.assertEqual(freigabe.unklare(basis=self.basis), [])
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.ausfuehrung_abschliessen(eid, "nochmal", basis=self.basis)

    def test_abgelehnt_wird_nicht_ausgefuehrt(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        freigabe.entscheide(eid, "abgelehnt", basis=self.basis)
        self.assertEqual(freigabe.zur_ausfuehrung(basis=self.basis), [])
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.ausfuehrung_beginnen(eid, basis=self.basis)

    def test_nach_freigabe_veraendert(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis)
        freigeben(eid, self.basis)
        pfad = self.basis / "erledigt" / f"{eid}.json"
        daten = json.loads(pfad.read_text())
        daten["daten"] = {"an": "jemand-anderes@example.org"}
        pfad.write_text(json.dumps(daten))
        with self.assertRaises(freigabe.FreigabeFehler):
            freigabe.ausfuehrung_beginnen(eid, basis=self.basis)

    def kauf(self, betrag):
        daten = {} if betrag is None else {"betrag_euro": betrag}
        eid = freigabe.neuer_entwurf("einkauf", "Buch", "Link ...", typ="kauf", daten=daten, basis=self.basis)
        freigeben(eid, self.basis)
        return eid

    def test_kauf_limit(self):
        ok = self.kauf(19.99)
        with self.assertRaises(freigabe.FreigabeFehler):  # kein Limit gesetzt
            freigabe.ausfuehrung_beginnen(ok, kauf_limit_euro="", basis=self.basis)
        self.assertEqual(freigabe.ausfuehrung_beginnen(ok, kauf_limit_euro="20,00", basis=self.basis)["id"], ok)
        for betrag in (25, None, "viel", 0):
            eid = self.kauf(betrag)
            with self.assertRaises(freigabe.FreigabeFehler):
                freigabe.ausfuehrung_beginnen(eid, kauf_limit_euro="20", basis=self.basis)
            self.assertIn(eid, [e["id"] for e in freigabe.zur_ausfuehrung(basis=self.basis)])


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

    def test_modus(self):
        a1 = auftraege.neuer_auftrag("uni", "Kapitel 3", basis=self.basis)
        a2 = auftraege.neuer_auftrag("uni", "Kapitel 4", modus="lernen", basis=self.basis)
        modi = {a["id"]: a["modus"] for a in auftraege.neue(basis=self.basis)}
        self.assertEqual(modi, {a1: "erledigen", a2: "lernen"})
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.neuer_auftrag("uni", "x", modus="halbautomatisch", basis=self.basis)

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
