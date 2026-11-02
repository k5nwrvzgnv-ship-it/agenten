import tempfile
import unittest
import zipfile
from pathlib import Path

from agentkit import auftraege, fassungen

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
SZENEN = [f"Szene {n}: Der Regisseur ruft von hinten in den Saal." for n in range(8)]


def word(pfad, absaetze, kommentar=False):
    koerper = "".join(f"<w:p><w:r><w:t>{a}</w:t></w:r></w:p>" for a in absaetze)
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("word/document.xml", f"<w:document {W}><w:body>{koerper}</w:body></w:document>")
        if kommentar:
            z.writestr("word/comments.xml", f'<w:comments {W}><w:comment w:id="1"><w:p><w:r><w:t>raus</w:t></w:r></w:p>'
                                            "</w:comment></w:comments>")
    return pfad


class TestArt(unittest.TestCase):
    LANG = [f"Das ist Absatz Nummer {n} aus dem Ergebnis." for n in range(20)]

    def test_kommentare_sind_immer_fassung(self):
        self.assertEqual(fassungen.art_bestimmen(True, [], []), fassungen.ART_FASSUNG)

    def test_nach_anteil_im_ergebnis(self):
        fremd = [f"Das ist Lias eigene Anmerkung Nummer {n}." for n in range(20)]
        for gleich, art in ((20, fassungen.ART_FASSUNG), (5, fassungen.ART_FASSUNG), (4, fassungen.ART_UNKLAR),
                            (2, fassungen.ART_UNKLAR), (1, fassungen.ART_ANMERKUNGEN), (0, fassungen.ART_ANMERKUNGEN)):
            with self.subTest(gleich=gleich):
                self.assertEqual(fassungen.art_bestimmen(False, self.LANG[:gleich] + fremd[gleich:], self.LANG), art)

    def test_ohne_vergleich_unklar(self):
        self.assertEqual(fassungen.art_bestimmen(False, self.LANG, []), fassungen.ART_UNKLAR)  # Ergebnis ohne Word
        self.assertEqual(fassungen.art_bestimmen(False, [], self.LANG), fassungen.ART_UNKLAR)  # PDF, Foto
        self.assertEqual(fassungen.art_bestimmen(False, ["kürzer"], self.LANG), fassungen.ART_UNKLAR)  # nichts Langes

    def test_vergleich_ignoriert_leerraum_und_gross(self):
        self.assertEqual(fassungen.art_bestimmen(False, ["  DAS  ist ABSATZ Nummer 1 aus dem Ergebnis. "], self.LANG),
                         fassungen.ART_FASSUNG)

    def test_alter_eintrag_ist_fassung(self):
        self.assertEqual(fassungen.art({"n": 1}), fassungen.ART_FASSUNG)


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

    def ergebnis_mit_word(self):
        (self.agenten / "unterricht" / "Stueck.docx").unlink(missing_ok=True)
        a = self.auftrag(datei="Stueck.docx")
        word(self.agenten / "unterricht" / "Stueck.docx", SZENEN)
        return a

    def test_rueckmeldung_erkennt_die_art(self):
        a = self.ergebnis_mit_word()
        anmerkungen = word(self.tmp / "feedback.docx", [f"Bitte in Szene {n} mehr Tempo und eine Wiederholung." for n in range(9)])
        _, e = fassungen.rueckmeldung(a, "siehe Datei", anmerkungen, basis=self.basis, agenten_dir=self.agenten)
        self.assertEqual((e["art"], e["notiz"]), (fassungen.ART_ANMERKUNGEN, ""))
        bearbeitet = word(self.tmp / "Stueck2.docx", SZENEN[:6] + ["Szene 6 hat Lia ganz neu geschrieben, mit Musik."])
        _, e = fassungen.rueckmeldung(a, "meine Fassung", bearbeitet, basis=self.basis, agenten_dir=self.agenten)
        self.assertEqual((e["art"], e["notiz"]), (fassungen.ART_FASSUNG, fassungen.NOTIZ_FASSUNG))
        kommentiert = word(self.tmp / "Blatt.docx", ["Ein ganz anderer Text ohne jeden Bezug zum Ergebnis."], kommentar=True)
        self.assertEqual(fassungen.rueckmeldung(a, "x", kommentiert, basis=self.basis, agenten_dir=self.agenten)[1]["art"],
                         fassungen.ART_FASSUNG)
        foto = self.tmp / "Foto.jpg"
        foto.write_bytes(b"JPG")
        self.assertEqual(fassungen.rueckmeldung(a, "x", foto, basis=self.basis, agenten_dir=self.agenten)[1]["art"],
                         fassungen.ART_UNKLAR)

    def test_rueckmeldung_vergleicht_auch_mit_lias_fassung(self):
        a = self.auftrag()  # Ergebnis ohne Word-Datei, aber Lia hat schon eine eigene Fassung hochgeladen
        fassungen.eigene_dazu(a, word(self.tmp / "Meine.docx", SZENEN), basis=self.basis, agenten_dir=self.agenten)
        weiter = word(self.tmp / "Meine2.docx", SZENEN)
        self.assertEqual(fassungen.rueckmeldung(a, "x", weiter, basis=self.basis, agenten_dir=self.agenten)[1]["art"],
                         fassungen.ART_FASSUNG)

    def test_kaputte_word_datei_unklar_und_grundlage_bleibt(self):
        a = self.ergebnis_mit_word()
        _, e = fassungen.rueckmeldung(a, "x", self.hochgeladen(), basis=self.basis, agenten_dir=self.agenten)
        self.assertEqual(e["art"], fassungen.ART_UNKLAR)
        self.assertEqual(fassungen.grundlage(a, self.basis), e)  # der Feedback-Dienst hängt sie trotzdem an

    def test_eigene_ohne_art_ist_fassung_und_final_nur_dafuer(self):
        a = self.ergebnis_mit_word()
        fassungen.eigene_dazu(a, self.hochgeladen(), basis=self.basis, agenten_dir=self.agenten)
        anmerkungen = word(self.tmp / "feedback.docx", ["Bitte mehr Tempo und noch eine Wiederholung am Ende."])
        fassungen.rueckmeldung(a, "x", anmerkungen, basis=self.basis, agenten_dir=self.agenten)
        with self.assertRaises(fassungen.FassungFehler):
            fassungen.final_setzen(a, "eigene-2", self.basis)
        self.assertEqual(fassungen.final_setzen(a, "eigene-1", self.basis)["final"]["fassung"], "eigene-1")

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
