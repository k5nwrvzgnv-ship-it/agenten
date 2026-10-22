import tempfile
import unittest
from pathlib import Path

import logik
from logik import (
    Eingang,
    Gemeldet,
    auftrag_kopf,
    aufteilen,
    befehl_auswerten,
    dateiname_bereinigen,
    entwurf_als_text,
    knopf_auswerten,
    knopf_beschriftung,
    meldung_knoepfe,
    verbrauch_text,
    weitergabe_text,
)


class TestLogik(unittest.TestCase):
    def test_befehle(self):
        self.assertEqual(befehl_auswerten("/uni Kapitel 3 zusammenfassen"), ("uni", "erledigen", "Kapitel 3 zusammenfassen"))
        self.assertEqual(befehl_auswerten("/unilern Kapitel 4"), ("uni", "lernen", "Kapitel 4"))
        self.assertEqual(befehl_auswerten("/einkauf@Agentenzentralebot Geschenk"), ("einkauf", "erledigen", "Geschenk"))
        self.assertEqual(befehl_auswerten("/uni"), ("uni", "erledigen", ""))
        self.assertIsNone(befehl_auswerten("/quatsch hallo"))
        self.assertIsNone(befehl_auswerten("/lern x"))

    def test_aufteilen_verliert_nichts(self):
        text = "\n".join(f"Zeile {i} " + "x" * 50 for i in range(300))
        stuecke = aufteilen(text, 1000)
        self.assertTrue(all(len(s) <= 1000 for s in stuecke))
        self.assertEqual("\n".join(stuecke), text)
        self.assertEqual(aufteilen("kurz"), ["kurz"])
        lang = "y" * 2500
        self.assertEqual("".join(aufteilen(lang, 1000)), lang)

    def test_entwurf_zeigt_alles(self):
        e = {"agent": "posteingang", "typ": "mail", "titel": "Antwort", "inhalt": "Hallo " * 2000,
             "daten": {"an": "prof@example.org"}, "vorgaenger": None}
        text = "".join(entwurf_als_text(e))
        self.assertIn("prof@example.org", text)
        self.assertEqual(text.count("Hallo"), 2000)

    def test_verbrauch_text(self):
        def zt(ts):
            return "ZEIT" if ts else "?"

        self.assertIn("unbekannt", verbrauch_text(None, "normal", {}, zt))
        stand = {"5h": 0.11, "7d": 0.39, "reset_5h": 1, "reset_7d": 2, "zeit": 3}
        heute = {"uni": {"laeufe": 2, "tokens": 12000, "minuten": 1.5, "usd": 0.1, "fehler": 1}}
        text = verbrauch_text(stand, "sparen", heute, zt)
        for teil in ("5 Stunden: 11 %", "7 Tage: 39 %", "sparen", "uni: 2 Läufe, 12k Tokens", "1 mit Fehler"):
            self.assertIn(teil, text)

    def test_gemeldet_speichern_laden(self):
        pfad = Path(tempfile.mkdtemp()) / "data" / "gemeldet.json"
        g = Gemeldet(pfad)
        g.angezeigt["x"] = "abc"
        g.listen["auftraege"].add("a1")
        g.stufe = "sparen"
        g.speichern()
        g2 = Gemeldet(pfad)
        self.assertEqual(g2.angezeigt, {"x": "abc"})
        self.assertEqual(g2.listen["auftraege"], {"a1"})
        self.assertEqual(g2.stufe, "sparen")

    def test_nachrichten_zuordnung(self):
        pfad = Path(tempfile.mkdtemp()) / "gemeldet.json"
        g = Gemeldet(pfad)
        g.MAX_NACHRICHTEN = 2
        for mid, aid in ((1, "a1"), (2, "a2"), (3, "a2")):
            g.nachricht_merken(mid, aid)
        g.listen["am_pc"].add("s-1")
        g.speichern()
        g2 = Gemeldet(pfad)
        self.assertEqual(g2.nachrichten, {"2": "a2", "3": "a2"})  # älteste fällt weg
        self.assertEqual(g2.listen["am_pc"], {"s-1"})


    def test_meldung_knoepfe(self):
        mid = "20261020-120000-uni-abcdef"
        m = {"id": mid, "knoepfe": [["Nochmal", "Schwer", "Gut", "Leicht"], ["Antwort zeigen"]]}
        knoepfe = meldung_knoepfe(m)
        self.assertEqual(knoepfe[0][2], ("Gut", f"m:{mid}:0:2"))
        self.assertEqual(knoepfe[1], [("Antwort zeigen", f"m:{mid}:1:0")])
        self.assertTrue(all(len(d.encode()) <= 64 for zeile in knoepfe for _, d in zeile))
        self.assertEqual(meldung_knoepfe({"id": mid, "knoepfe": []}), [])
        self.assertEqual(knopf_auswerten(f"m:{mid}:0:2"), (mid, 0, 2))
        self.assertIsNone(knopf_auswerten("f:20261020-120000-uni-abcdef"))
        self.assertIsNone(knopf_auswerten("m:../x:0:0"))
        self.assertEqual(knopf_beschriftung(m, 0, 2), "Gut")
        self.assertIsNone(knopf_beschriftung(m, 1, 1))
        self.assertIsNone(knopf_beschriftung(m, 5, 0))

    def test_meldung_zuordnung_und_geklickt(self):
        pfad = Path(tempfile.mkdtemp()) / "gemeldet.json"
        g = Gemeldet(pfad)
        g.meldung_merken(7, "20261020-120000-uni-abcdef")
        g.nachricht_merken(8, "20261020-120000-uni-123456")
        g.geklickt("20261020-120000-uni-abcdef")
        g.speichern()
        g = Gemeldet(pfad)
        self.assertEqual(g.meldung_zu(7), "20261020-120000-uni-abcdef")
        self.assertIsNone(g.meldung_zu(8))  # Auftrag, keine Meldung
        self.assertIsNone(g.meldung_zu(9))
        self.assertIn("20261020-120000-uni-abcdef", g.listen["geklickt"])
        for i in range(Gemeldet.MAX_GEKLICKT + 5):
            g.geklickt(f"20261021-{i:06d}-uni-abcdef")
        self.assertEqual(len(g.listen["geklickt"]), Gemeldet.MAX_GEKLICKT)
        self.assertNotIn("20261020-120000-uni-abcdef", g.listen["geklickt"])

    def test_dateiname_bereinigen(self):
        self.assertEqual(dateiname_bereinigen("Skript Kapitel 3.pdf"), "Skript Kapitel 3.pdf")
        self.assertEqual(dateiname_bereinigen("../../.env"), "env")
        self.assertEqual(dateiname_bereinigen(".env"), "env")
        self.assertEqual(dateiname_bereinigen("C:\\Users\\jan\\a.docx"), "a.docx")
        self.assertEqual(dateiname_bereinigen("a/b;rm -rf.txt"), "b_rm -rf.txt")
        self.assertEqual(dateiname_bereinigen(None, "foto.jpg"), "foto.jpg")
        self.assertEqual(dateiname_bereinigen("..."), "datei")
        lang = dateiname_bereinigen("x" * 300 + ".pdf")
        self.assertEqual(len(lang), 100)
        self.assertTrue(lang.endswith(".pdf"))

    def test_eingang(self):
        eingang = Eingang(Path(tempfile.mkdtemp()) / "eingang")
        self.assertEqual(eingang.wartende(), [])
        a = eingang.neuer_platz("a.pdf")
        a.write_text("1")
        b = eingang.neuer_platz("a.pdf")  # gleicher Name: eigener Ordner, nichts wird überschrieben
        b.write_text("2")
        self.assertEqual(eingang.wartende(), [a, b])
        eingang.neuer_platz("leer.txt")  # Download fehlgeschlagen: zählt nicht als wartend
        self.assertEqual(len(eingang.wartende()), 2)
        a.unlink()
        eingang.aufraeumen()
        self.assertEqual(eingang.wartende(), [b])
        self.assertEqual(eingang.verwerfen(), 1)
        self.assertEqual(eingang.wartende(), [])


class PanelTest(unittest.TestCase):
    def test_auswerten(self):
        self.assertEqual(logik.panel_auswerten("u:status"), ("status", None, None))
        self.assertEqual(logik.panel_auswerten("u:a:uni:lernen"), ("agent", "uni", "lernen"))
        self.assertIsNone(logik.panel_auswerten("u:a:fremd:lernen"))
        self.assertIsNone(logik.panel_auswerten("u:a:uni:quatsch"))
        self.assertIsNone(logik.panel_auswerten("f:123"))

    def test_alle_knoepfe_gueltig(self):
        ansichten = [
            logik.ansicht_home(["Stand"], ["uni", "dokumente", "einkauf"], 2, "Hinweis"),
            logik.ansicht_agent("uni", "erledigen"), logik.ansicht_agent("uni", "lernen"),
            logik.ansicht_entwuerfe([{"titel": "Mail", "agent": "uni"}]), logik.ansicht_entwuerfe([]),
            logik.ansicht_text("Status", "x"),
        ]
        for _, knoepfe in ansichten:
            for zeile in knoepfe:
                for _, daten in zeile:
                    self.assertLessEqual(len(daten.encode()), 64)
                    self.assertIsNotNone(logik.panel_auswerten(daten), daten)

    def test_home(self):
        text, knoepfe = logik.ansicht_home(["Offene Entwürfe: 2"], ["uni"], 2, "Auftrag weitergegeben.")
        self.assertIn("Offene Entwürfe: 2", text)
        self.assertIn("Auftrag weitergegeben.", text)
        self.assertEqual(knoepfe[0], [("uni", "u:a:uni:erledigen")])
        self.assertIn(("Entwürfe (2)", "u:entwuerfe"), knoepfe[1])

    def test_agent_modus_wechseln(self):
        text, knoepfe = logik.ansicht_agent("uni", "erledigen")
        self.assertIn("Modus: erledigen", text)
        self.assertEqual(knoepfe[0][0][1], "u:a:uni:lernen")

    def test_text_wird_gekuerzt(self):
        text, _ = logik.ansicht_text("Hilfe", "x" * 5000)
        self.assertLessEqual(len(text), logik.MAX_LAENGE)



class TestWeitergabe(unittest.TestCase):
    A = {"id": "20261022-120000-dokumente-abcdef", "agent": "dokumente", "von": "uni", "status": "erledigt",
         "text": "Zusammenfassung Holzschutz als PDF"}

    def test_info_an_jan(self):
        text = weitergabe_text(self.A, dienst_da=True)
        self.assertTrue(text.startswith("[uni -> dokumente] Neuer Auftrag: Zusammenfassung Holzschutz"))
        self.assertIn(self.A["id"], text)
        self.assertNotIn("keinen Dienst", text)
        self.assertIn("dokumente hat noch keinen Dienst", weitergabe_text(self.A, dienst_da=False))
        lang = weitergabe_text({**self.A, "text": "x" * 5000}, dienst_da=True)
        self.assertLess(len(lang), 500)

    def test_kopf_nennt_absender(self):
        self.assertEqual(auftrag_kopf(self.A), "Auftrag erledigt (dokumente, von uni)")
        self.assertEqual(auftrag_kopf({**self.A, "status": "fehlgeschlagen", "von": None}),
                         "Auftrag fehlgeschlagen (dokumente)")
        self.assertEqual(auftrag_kopf({"agent": "uni", "status": "erledigt"}), "Auftrag erledigt (uni)")  # alter Eintrag

    def test_weitergaben_werden_gemerkt(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = Path(d) / "gemeldet.json"
            pfad.write_text('{"auftraege": ["a"]}')  # alte Datei ohne Liste
            g = Gemeldet(pfad)
            self.assertEqual(g.listen["weitergaben"], set())
            g.listen["weitergaben"].add(self.A["id"])
            g.speichern()
            self.assertEqual(Gemeldet(pfad).listen["weitergaben"], {self.A["id"]})


if __name__ == "__main__":
    unittest.main()
