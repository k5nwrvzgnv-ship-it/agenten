import json
import tempfile
import unittest
from pathlib import Path

from agentkit import auftraege, ereignis, freigabe


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

    def test_ereignisse_der_freigabe(self):
        eid = freigabe.neuer_entwurf("posteingang", "Antwort", "Hallo", typ="mail", basis=self.basis)
        freigeben(eid, self.basis)
        freigabe.ausfuehrung_beginnen(eid, basis=self.basis)
        freigabe.ausfuehrung_abschliessen(eid, "Mail gesendet", basis=self.basis)
        ev = ereignis.lesen(ordner=self.basis / "ereignisse")
        self.assertEqual([e["typ"] for e in ev], ["freigabe.wartet", "freigabe.entschieden",
                                                   "freigabe.ausfuehrung_begonnen", "freigabe.ausgefuehrt"])
        self.assertEqual({e["agent"] for e in ev}, {"posteingang"})
        self.assertEqual({e["daten"]["freigabe"] for e in ev}, {eid})
        self.assertEqual(ev[1]["daten"]["status"], "freigegeben")
        self.assertNotIn("Hallo", json.dumps(ev))

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

    def test_ereignisse_der_auftraege(self):
        agenten = Path(tempfile.mkdtemp())
        a = auftraege.neuer_auftrag("uni", "Geheimer Text", quelle="knopf", basis=self.basis, agenten_dir=agenten)
        auftraege.abschliessen(a, "Fertig", status="fehlgeschlagen", basis=self.basis, agenten_dir=agenten)
        ev = ereignis.lesen(ordner=self.basis / "ereignisse")
        self.assertEqual([(e["typ"], e["agent"], e["auftrag"]) for e in ev],
                         [("auftrag.angelegt", "uni", a), ("auftrag.abgeschlossen", "uni", a)])
        self.assertEqual((ev[0]["daten"]["quelle"], ev[1]["daten"]["status"]), ("knopf", "fehlgeschlagen"))
        self.assertNotIn("Geheim", json.dumps(ev))

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

    def test_antwort_auf_meldung_mit_dienst(self):
        mid = "20261020-120000-uni-abcdef"
        a1 = auftraege.neuer_auftrag("uni", "Kapitel 3", basis=self.basis)
        a2 = auftraege.neuer_auftrag("uni", "Hingehen", quelle="knopf", meldung=mid, dienst="uni-lernen",
                                     basis=self.basis)
        self.assertEqual({a["id"] for a in auftraege.neue("uni", basis=self.basis)}, {a1, a2})
        self.assertEqual([a["id"] for a in auftraege.neue("uni", basis=self.basis, dienst=None)], [a1])
        lern = auftraege.neue("uni", basis=self.basis, dienst="uni-lernen")
        self.assertEqual([(a["id"], a["meldung"], a["quelle"]) for a in lern], [(a2, mid, "knopf")])
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.neuer_auftrag("uni", "x", meldung="../x", basis=self.basis)
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.neuer_auftrag("uni", "x", dienst="einkauf", basis=self.basis)

    def test_antwort_setzt_sitzung_fort(self):
        a1 = auftraege.neuer_auftrag("uni", "Kapitel 3", modus="lernen", basis=self.basis)
        auftraege.abschliessen(a1, "Erste Frage an Jan", sitzung="s-1", basis=self.basis)
        alt = auftraege.erledigter(a1, basis=self.basis)
        self.assertEqual(alt["sitzung"], "s-1")
        a2 = auftraege.neuer_auftrag("uni", "Meine Antwort", modus=alt["modus"], bezug=a1,
                                     sitzung=alt["sitzung"], basis=self.basis)
        neu = auftraege.neue(basis=self.basis)[0]
        self.assertEqual((neu["id"], neu["bezug"], neu["sitzung"]), (a2, a1, "s-1"))
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.erledigter(a2, basis=self.basis)  # noch offen

    def test_fehlgeschlagen_und_bezug(self):
        eid = freigabe.neuer_entwurf("uni", "t", "i", basis=self.basis / "f")
        aid = auftraege.neuer_auftrag("uni", "anders formulieren", bezug=eid, basis=self.basis)
        self.assertEqual(auftraege.neue(basis=self.basis)[0]["bezug"], eid)
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.abschliessen(aid, status="halb", basis=self.basis)
        self.assertEqual(auftraege.abschliessen(aid, "Timeout", "fehlgeschlagen", basis=self.basis)["status"],
                         "fehlgeschlagen")

    def test_daten_und_zurueckgezogen(self):
        aid = auftraege.neuer_auftrag("uni", "kürzer", basis=self.basis)
        a = auftraege.abschliessen(aid, "", "zurueckgezogen", daten={"gestoppt": True}, basis=self.basis)
        self.assertEqual((a["status"], a["daten"]), ("zurueckgezogen", {"gestoppt": True}))
        aid = auftraege.neuer_auftrag("uni", "x", basis=self.basis)
        self.assertNotIn("daten", auftraege.abschliessen(aid, "ok", basis=self.basis))
        auftraege.daten_setzen(aid, {"stand": "gestoppt"}, basis=self.basis)
        self.assertEqual(auftraege.erledigter(aid, basis=self.basis)["daten"], {"stand": "gestoppt"})

    def test_dateien_kommen_in_den_agent_ordner(self):
        agenten = self.basis / "agenten"
        (agenten / "uni").mkdir(parents=True)
        eingang = self.basis / "eingang"
        (eingang / "1").mkdir(parents=True)
        (eingang / "2").mkdir()
        a = eingang / "1" / "Skript.pdf"
        b = eingang / "2" / "Skript.pdf"  # gleicher Name
        a.write_text("A")
        b.write_text("B")
        aid = auftraege.neuer_auftrag("uni", "Fasse zusammen", dateien=[a, b], basis=self.basis,
                                      agenten_dir=agenten)
        auftrag = auftraege.neue(basis=self.basis)[0]
        erwartet = [f"data/eingang/{aid}/Skript.pdf", f"data/eingang/{aid}/Skript-2.pdf"]
        self.assertEqual(auftrag["dateien"], erwartet)
        self.assertEqual([(agenten / "uni" / p).read_text() for p in erwartet], ["A", "B"])
        self.assertFalse(a.exists() or b.exists())
        self.assertTrue(auftrag["text"].startswith("Fasse zusammen\n\nAngehängte Dateien"))
        self.assertIn(f"- data/eingang/{aid}/Skript-2.pdf", auftrag["text"])

    def test_ohne_dateien_bleibt_text_gleich(self):
        auftraege.neuer_auftrag("uni", "Fristen", basis=self.basis, agenten_dir=self.basis / "fehlt")
        auftrag = auftraege.neue(basis=self.basis)[0]
        self.assertEqual((auftrag["text"], auftrag["dateien"]), ("Fristen", []))

    def test_dateien_ohne_agent_ordner(self):
        datei = self.basis / "x.pdf"
        datei.write_text("x")
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.neuer_auftrag("uni", "x", dateien=[datei], basis=self.basis,
                                    agenten_dir=self.basis / "fehlt")
        self.assertTrue(datei.exists())
        self.assertEqual(auftraege.neue(basis=self.basis), [])

    def test_ergebnis_dateien(self):
        agenten = self.basis / "agenten"
        (agenten / "dokumente" / "data" / "ausgang").mkdir(parents=True)
        datei = agenten / "dokumente" / "data" / "ausgang" / "Bericht.docx"
        datei.write_text("x")
        aid = auftraege.neuer_auftrag("dokumente", "Bericht", basis=self.basis)
        a = auftraege.abschliessen(aid, "fertig", dateien=[datei], basis=self.basis, agenten_dir=agenten)
        self.assertEqual(a["ergebnis_dateien"], ["data/ausgang/Bericht.docx"])
        aid = auftraege.neuer_auftrag("dokumente", "ohne", basis=self.basis)
        self.assertEqual(auftraege.abschliessen(aid, basis=self.basis)["ergebnis_dateien"], [])

    def test_ergebnis_dateien_unzulaessig(self):
        agenten = self.basis / "agenten"
        (agenten / "dokumente").mkdir(parents=True)
        (agenten / "dokumente" / ".env").write_text("GEHEIM=1")
        (agenten / "uni").mkdir()
        (agenten / "uni" / "x.txt").write_text("x")
        aid = auftraege.neuer_auftrag("dokumente", "t", basis=self.basis)
        for datei in [".env", "../uni/x.txt", agenten / "uni" / "x.txt", "fehlt.docx", "/etc/passwd"]:
            with self.subTest(datei=datei), self.assertRaises(auftraege.AuftragFehler):
                auftraege.abschliessen(aid, dateien=[datei], basis=self.basis, agenten_dir=agenten)
        self.assertEqual([a["id"] for a in auftraege.neue(basis=self.basis)], [aid])  # bleibt offen


class TestWeitergabe(unittest.TestCase):
    CFG = {"weitergabe": {"uni": ["dokumente"]}}

    def setUp(self):
        self.basis = Path(tempfile.mkdtemp())
        self.agenten = self.basis / "agenten"
        for a in ("uni", "dokumente", "einkauf"):
            (self.agenten / a).mkdir(parents=True)

    def weitergeben(self, von="uni", an="dokumente", aus_auftrag=None, dateien=None):
        return auftraege.weitergeben(von, an, "Zusammenfassung als PDF", aus_auftrag, dateien=dateien,
                                     cfg=self.CFG, basis=self.basis, agenten_dir=self.agenten)

    def test_ablauf(self):
        jan = auftraege.neuer_auftrag("uni", "Transkript aufbereiten", basis=self.basis)
        aid = self.weitergeben(aus_auftrag=jan)
        a = auftraege.neue("dokumente", basis=self.basis)[0]
        self.assertEqual((a["id"], a["von"], a["aus_auftrag"], a["quelle"], a["modus"], a["dienst"]),
                         (aid, "uni", jan, "agent:uni", "erledigen", None))
        self.assertIsNone(auftraege.neue("uni", basis=self.basis)[0]["von"])  # Jans Auftrag

    def test_nur_erlaubte_paare(self):
        for von, an in [("dokumente", "uni"), ("uni", "einkauf"), ("uni", "uni"), ("Uni", "dokumente")]:
            with self.subTest(von=von, an=an), self.assertRaises(auftraege.AuftragFehler):
                self.weitergeben(von, an)
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.weitergeben("uni", "dokumente", "x", None, cfg={}, basis=self.basis, agenten_dir=self.agenten)
        self.assertEqual(auftraege.neue(basis=self.basis), [])

    def test_keine_kette(self):
        aid = self.weitergeben()
        cfg = {"weitergabe": {"dokumente": ["uni"]}}
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.weitergeben("dokumente", "uni", "zurück", aid, cfg=cfg, basis=self.basis,
                                  agenten_dir=self.agenten)
        auftraege.abschliessen(aid, basis=self.basis)  # auch abgeschlossen nicht
        with self.assertRaises(auftraege.AuftragFehler):
            auftraege.weitergeben("dokumente", "uni", "zurück", aid, cfg=cfg, basis=self.basis,
                                  agenten_dir=self.agenten)
        for falsch in ["20261022-120000-uni-abcdef", "../x"]:  # unbekannt, ungültig
            with self.subTest(aus_auftrag=falsch), self.assertRaises(auftraege.AuftragFehler):
                self.weitergeben(aus_auftrag=falsch)

    def test_dateien_werden_kopiert(self):
        quelle = self.agenten / "uni" / "data" / "kurse" / "notizen.md"
        quelle.parent.mkdir(parents=True)
        quelle.write_text("Inhalt")
        aid = self.weitergeben(dateien=["data/kurse/notizen.md"])
        a = auftraege.neue(basis=self.basis)[0]
        self.assertEqual(a["dateien"], [f"data/eingang/{aid}/notizen.md"])
        self.assertEqual((self.agenten / "dokumente" / a["dateien"][0]).read_text(), "Inhalt")
        self.assertTrue(quelle.exists())  # uni behält seine Datei
        self.assertIn("Angehängte Dateien von uni", a["text"])

    def test_dateien_nur_aus_dem_eigenen_ordner(self):
        (self.agenten / "uni" / ".env").write_text("GEHEIM=1")
        (self.agenten / "einkauf" / "x.txt").write_text("x")
        for datei in [".env", "../einkauf/x.txt", self.agenten / "einkauf" / "x.txt", "fehlt.md"]:
            with self.subTest(datei=datei), self.assertRaises(auftraege.AuftragFehler):
                self.weitergeben(dateien=[datei])
        self.assertEqual(auftraege.neue(basis=self.basis), [])


if __name__ == "__main__":
    unittest.main()
