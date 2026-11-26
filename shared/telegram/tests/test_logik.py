import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import logik
from logik import (
    Eingang,
    Gemeldet,
    aufteilen,
    auftrag_nachricht,
    befehl_auswerten,
    bestaetigung,
    dateien_auswaehlen,
    dateiname_bereinigen,
    knopf_auswerten,
    knopf_beschriftung,
    meldung_knoepfe,
    mit_absender,
    passt_als_beschriftung,
    stufe_text,
    verbrauch_text,
    weitergabe_text,
)


class TestLogik(unittest.TestCase):
    def test_befehle(self):
        self.assertEqual(befehl_auswerten("/uni Kapitel 3 zusammenfassen"), ("uni", "erledigen", "Kapitel 3 zusammenfassen"))
        self.assertEqual(befehl_auswerten("/unilern Kapitel 4"), ("uni", "lernen", "Kapitel 4"))
        self.assertEqual(befehl_auswerten("/finance@Agentenzentralebot Solar"), ("finance", "erledigen", "Solar"))
        self.assertIsNone(befehl_auswerten("/einkauf Geschenk"))  # geplant, aber ohne Agent: kein Befehl
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

    def test_entwurf_wie_agentkit(self):
        from agentkit import entwurfsanzeige  # Anzeige und ihre Tests liegen dort
        self.assertIs(logik.entwurf_als_text, entwurfsanzeige.entwurf_als_text)

    def test_nur_freigabe_verweis(self):
        a = {"status": "erledigt", "ergebnis": "Entwurf an a@x.de liegt zur Freigabe."}
        self.assertTrue(logik.nur_freigabe_verweis(a))
        self.assertTrue(logik.nur_freigabe_verweis({**a, "ergebnis": "Mail-Entwurf an a@x.de liegt zur Freigabe: T\n"
                                                                    "Mail-Entwurf an b@x.de liegt zur Freigabe: U"}))
        self.assertTrue(logik.nur_freigabe_verweis({**a, "ergebnis": "Fertig.", "daten": {"nur_freigabe": True}}))
        self.assertFalse(logik.nur_freigabe_verweis({**a, "ergebnis": a["ergebnis"] + "\nAußerdem: zwei Termine."}))
        self.assertFalse(logik.nur_freigabe_verweis({**a, "ergebnis_dateien": ["x.pdf"]}))
        self.assertFalse(logik.nur_freigabe_verweis({**a, "status": "fehlgeschlagen"}))
        self.assertFalse(logik.nur_freigabe_verweis({**a, "ergebnis": ""}))

    def test_verbrauch_text(self):
        def zt(ts):
            return "ZEIT" if ts else "?"

        self.assertEqual(verbrauch_text(None, "normal", {}, zt), "Die Rechenzeit reicht.")
        stand = {"5h": 0.11, "7d": 0.39, "reset_5h": 1, "reset_7d": 2, "zeit": 3}
        heute = {"uni": {"laeufe": 2, "tokens": 12000, "minuten": 1.5, "usd": 0.1, "fehler": 1}}
        text = verbrauch_text(stand, "sparen", heute, zt)
        self.assertLessEqual(len(text.splitlines()), 4)
        for teil in ("11 % in 5 Stunden (frei ZEIT)", "39 % in 7 Tagen", "darum spare ich", "Heute: Uni 2-mal",
                     "1-mal nicht geklappt"):
            self.assertIn(teil, text)
        self.assertNotIn("Tokens", text)
        self.assertIn("Recherche (Lia) 2-mal", verbrauch_text(stand, "normal", {"lia/recherche": heute["uni"]}, zt))

    def test_verbrauch_text_mit_woche(self):
        woche = {"uni": {"laeufe": 12, "usd": 3.4}, "lia/theater": {"laeufe": 2, "usd": 16.8},
                 "posteingang": {"laeufe": 7, "usd": 0.0}}
        text = verbrauch_text(None, "normal", {}, lambda ts: "?", woche)
        self.assertEqual(text.splitlines()[-1], "7 Tage: 20,20 USD Vergleichswert (Theater (Lia) 16,80 USD, "
                                                "Uni 3,40 USD, Posteingang 0,00 USD)")
        self.assertNotIn("7 Tage:", verbrauch_text(None, "normal", {}, lambda ts: "?", {}))

    def test_agenten_finden(self):
        tmp = Path(tempfile.mkdtemp())
        units = tmp / "units"
        units.mkdir()
        for name, agent_py, dienst in (("finance", True, True), ("uni", True, True), ("holzbalkenscan", True, False),
                                       ("einkauf", False, True), ("aaa", True, True), ("shared", False, False),
                                       ("Gross", True, True)):
            (tmp / name).mkdir()
            if agent_py:
                (tmp / name / "agent.py").write_text("")
            if dienst:
                (units / f"{name}.service").write_text("")
        self.assertEqual(logik.agenten_finden(tmp, units), ("uni", "finance", "aaa"))

    def test_agenten_setzen(self):
        alt = logik.AGENTEN
        self.addCleanup(logik.agenten_setzen, alt)
        self.assertEqual(logik.agenten_setzen(()), alt)  # nichts gefunden: Vorgabe bleibt
        self.assertEqual(logik.agenten_setzen(("uni", "neu")), ("uni", "neu"))
        self.assertEqual(befehl_auswerten("/neu Text"), ("neu", "erledigen", "Text"))
        self.assertEqual(logik.panel_auswerten("u:a:neu:erledigen"), ("agent", "neu", "erledigen"))
        self.assertNotIn("einkauf", alt)

    def test_netzfehler_erkennen(self):
        class NetworkError(Exception):
            pass

        class TimedOut(NetworkError):
            pass

        class TransportError(Exception):
            pass

        class ReadError(TransportError):
            pass

        for f in (NetworkError("Bad Gateway"), TimedOut(), ReadError()):
            self.assertTrue(logik.ist_netzfehler(f))
        for f in (ValueError("x"), KeyError("y"), None):
            self.assertFalse(logik.ist_netzfehler(f))

    def test_verfall_text(self):
        eins = [{"titel": "Mail: Rückfrage", "agent": "uni"}]
        text = logik.verfall_text(eins, 7)
        self.assertEqual("Entwurf nach 7 Tagen abgelaufen, nichts ausgeführt: Mail: Rückfrage (Uni).", text)
        zwei = logik.verfall_text(eins + [{"titel": "Mail: Termin", "agent": "posteingang"}], 7)
        self.assertIn("2 Entwürfe nach 7 Tagen abgelaufen", zwei)
        self.assertIn("• Mail: Termin (Posteingang)", zwei)

    def test_erinnerung_einmal_am_tag_und_nicht_nachts(self):
        tag = datetime(2026, 11, 16, 10, 0)
        self.assertIsNone(logik.erinnerung_text([], tag, "", 7))
        self.assertIsNone(logik.erinnerung_text([2.0, 23.9], tag, "", 7))  # nichts älter als ein Tag
        self.assertEqual(logik.erinnerung_text([30.0, 1.0], tag, "", 7),
                         "1 Entwurf wartet seit gestern, er läuft in 5 Tagen ab.")
        self.assertEqual(logik.erinnerung_text([30.0, 150.0], tag, "2026-11-15", 7),
                         "2 Entwürfe warten, der älteste läuft heute ab.")
        self.assertIn("morgen", logik.erinnerung_text([130.0], tag, "", 7))
        self.assertIsNone(logik.erinnerung_text([30.0], tag, "2026-11-16", 7))  # heute schon erinnert
        self.assertIsNone(logik.erinnerung_text([30.0], datetime(2026, 11, 16, 3, 0), "", 7))  # nachts nicht
        self.assertIsNotNone(logik.panel_auswerten(logik.ERINNERUNG_KNOEPFE[0][0][1]))

    def test_freigabe_fehler_abgelaufen(self):
        self.assertIn("schon entschieden", logik.freigabe_fehler("x ist nicht (mehr) offen"))
        text = logik.freigabe_fehler("x ist nicht (mehr) offen", abgelaufen=True)
        self.assertIn("abgelaufen", text)
        self.assertIn("nichts ausgeführt", text)

    def test_entwuerfe_einzeln_antippbar(self):
        eid1, eid2 = "20261027-101500-uni-abcdef", "20261113-090000-posteingang-012345"
        offene = [{"id": eid1, "titel": "Mail: " + "sehr langer Titel " * 5, "agent": "uni"},
                  {"id": eid2, "titel": "Mail: Termin", "agent": "posteingang"}]
        text, knoepfe = logik.ansicht_entwuerfe(offene, {eid1: 20 * 24.0, eid2: 5.0})
        self.assertEqual("2 Entwürfe offen, der älteste seit 20 Tagen.", text)
        self.assertEqual([k[0][1] for k in knoepfe], [f"u:e:{eid1}", f"u:e:{eid2}", "u:home"])
        self.assertLessEqual(len(knoepfe[0][0][0]), 40)
        self.assertTrue(all(len(d.encode()) <= 64 for zeile in knoepfe for _, d in zeile))
        self.assertEqual(logik.panel_auswerten(f"u:e:{eid1}"), ("entwurf", eid1, None))
        self.assertIsNone(logik.panel_auswerten("u:e:../../etc"))
        self.assertNotIn("Alle mit Knöpfen", str(knoepfe))
        viele = [{"id": f"20261027-1015{i:02d}-uni-abcdef", "titel": f"T{i}", "agent": "uni"} for i in range(14)]
        self.assertEqual(len(logik.ansicht_entwuerfe(viele)[1]), logik.MAX_ENTWURF_KNOEPFE + 1)

    def test_gemeldet_merkt_erinnerung_und_abgelaufene(self):
        pfad = Path(tempfile.mkdtemp()) / "data" / "gemeldet.json"
        g = Gemeldet(pfad)
        self.assertEqual((g.erinnert, g.listen["abgelaufen"]), ("", set()))
        g.erinnert = "2026-11-16"
        g.listen["abgelaufen"].add("e1")
        g.speichern()
        g2 = Gemeldet(pfad)
        self.assertEqual((g2.erinnert, g2.listen["abgelaufen"]), ("2026-11-16", {"e1"}))

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
        self.assertEqual(dateiname_bereinigen("nachru\u0308stbare Lo\u0308sung.pdf"), "nachrüstbare Lösung.pdf")
        self.assertEqual(dateiname_bereinigen("nachrüstbare.pdf"), "nachrüstbare.pdf")
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
            logik.ansicht_home(["Stand"], ["uni", "dokumente", "finance"], 2, "Hinweis"),
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
        self.assertEqual(knoepfe[0], [("Uni", "u:a:uni:erledigen")])
        self.assertIn(("Entwürfe (2)", "u:entwuerfe"), knoepfe[1])

    def test_agent_ohne_modus_knopf(self):
        text, knoepfe = logik.ansicht_agent("uni", "erledigen")
        self.assertEqual("Was soll Uni tun?", text)
        self.assertEqual(knoepfe, logik.ZURUECK)  # Lernmodus nicht mehr sichtbar
        self.assertEqual(logik.panel_auswerten("u:a:uni:lernen"), ("agent", "uni", "lernen"))  # alte Knöpfe gehen

    def test_menue_nur_agenten_und_offene_entwuerfe(self):
        text, knoepfe = logik.ansicht_home(logik.home_zeilen("normal", 0), ["uni", "dokumente", "finance"], 0)
        self.assertEqual(text, "Zentrale")
        self.assertEqual([d for z in knoepfe for _, d in z],
                         ["u:a:uni:erledigen", "u:a:dokumente:erledigen", "u:a:finance:erledigen"])
        text, knoepfe = logik.ansicht_home(logik.home_zeilen("limit", 2), ["uni"], 3)
        self.assertEqual(knoepfe[-1], [("Entwürfe (3)", "u:entwuerfe")])
        self.assertIn("2 Dateien warten auf einen Auftrag.", text)
        self.assertIn("aufgebraucht", text)
        self.assertEqual(logik.home_zeilen("sparen", 0), [])

    def test_text_wird_gekuerzt(self):
        text, _ = logik.ansicht_text("Hilfe", "x" * 5000)
        self.assertLessEqual(len(text), logik.MAX_LAENGE)



class TestWeitergabe(unittest.TestCase):
    A = {"id": "20261022-120000-dokumente-abcdef", "agent": "dokumente", "von": "uni", "status": "erledigt",
         "text": "Zusammenfassung Holzschutz als PDF"}

    def test_weitergabe_nur_wenn_sie_liegen_bleibt(self):
        self.assertIsNone(weitergabe_text(self.A, dienst_da=True))
        (text,) = weitergabe_text(self.A, dienst_da=False)
        self.assertTrue(text.startswith("<b>Zentrale</b>\n"))
        self.assertIn("Dokumente ist noch nicht eingerichtet, der Auftrag wartet", text)
        self.assertNotIn(self.A["id"], text)

    def test_stille_weitergabe_beachtet_die_zentrale_nicht(self):
        self.assertTrue(logik.weitergabe_beachten(self.A))
        self.assertFalse(logik.weitergabe_beachten({**self.A, "still": True}))
        self.assertFalse(logik.weitergabe_beachten({**self.A, "von": None}))  # Jans eigener Auftrag

    def test_ergebnis_ohne_technik(self):
        a = {**self.A, "ergebnis": "Zusammenfassung fertig. Bitte GK 4 prüfen."}
        self.assertEqual(auftrag_nachricht(a), ["<b>Dokumente</b>\nZusammenfassung fertig. Bitte GK 4 prüfen."])
        fehl = auftrag_nachricht({**a, "status": "fehlgeschlagen", "ergebnis": ""})
        self.assertTrue(fehl[0].startswith("<b>Dokumente</b> · hat nicht geklappt\n"))
        self.assertEqual(auftrag_nachricht({"agent": "uni", "status": "erledigt"}), ["<b>Uni</b>\nErledigt."])

    def test_absender_escaped_und_aufgeteilt(self):
        self.assertEqual(mit_absender("uni", "a < b & <i>"), ["<b>Uni</b>\na &lt; b &amp; &lt;i&gt;"])
        lang = mit_absender("uni", ("x" * 100 + "\n") * 80)
        self.assertGreater(len(lang), 1)
        self.assertTrue(lang[0].startswith("<b>Uni</b>") and not lang[1].startswith("<b>"))

    def test_beschriftung(self):
        self.assertTrue(passt_als_beschriftung(mit_absender("uni", "&" * 1000)))  # zählt ohne &amp; und <b>
        self.assertTrue(passt_als_beschriftung(mit_absender("uni", "x " * 495)))  # mit zugeklapptem Teil
        self.assertFalse(passt_als_beschriftung(mit_absender("uni", "x" * 1100)))
        self.assertFalse(passt_als_beschriftung(["a", "b"]))

    def test_nur_pdf_wenn_vorhanden(self):
        self.assertEqual(dateien_auswaehlen(["data/a.docx", "data/a.pdf", "data/b.docx", "data/c.PDF"]),
                         ["data/a.pdf", "data/b.docx", "data/c.PDF"])

    def test_stufe_nur_bei_limit(self):
        zeit = lambda ts: "18:00"  # noqa: E731
        self.assertIsNone(stufe_text("normal", "sparen", None, zeit))
        self.assertIsNone(stufe_text("sparen", "nur_auftraege", None, zeit))
        self.assertIn("warten bis 18:00", stufe_text("sparen", "limit", {"reset_status": 1}, zeit)[0])
        self.assertIn("bis wieder Rechenzeit frei ist", stufe_text("normal", "limit", {}, zeit)[0])
        self.assertIn("Rechenzeit wieder frei", stufe_text("limit", "nur_auftraege", None, zeit)[0])
        self.assertTrue(stufe_text("limit", "normal", None, zeit)[0].startswith("<b>Zentrale</b>"))

    def test_bestaetigung(self):
        self.assertEqual(bestaetigung("uni", "erledigen", []), "Uni ist dran.")
        self.assertEqual(bestaetigung("uni", "lernen", ["a.pdf", "b.pdf"]), "Uni ist dran (lernen), mit 2 Dateien.")

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


class AntwortZuordnungTest(unittest.TestCase):
    """Antwort auf eine Bot-Nachricht geht an deren Agenten, ohne „An wen geht das?“ (Jan 26.11.2026)."""

    AGENTEN = ("uni", "posteingang", "dokumente")

    def test_kopfzeile(self):
        self.assertEqual(logik.absender_aus_text("Uni\nZusammenfassung fertig", self.AGENTEN), "uni")

    def test_kopf_mit_zusatz(self):
        self.assertEqual(logik.absender_aus_text("Posteingang · Mail-Entwurf\nAn: x", self.AGENTEN), "posteingang")

    def test_bestaetigung(self):
        self.assertEqual(logik.absender_aus_text("Dokumente ist dran.", self.AGENTEN), "dokumente")

    def test_fremd_oder_leer(self):
        self.assertIsNone(logik.absender_aus_text("Zentrale\nStufe sparen", self.AGENTEN))
        self.assertIsNone(logik.absender_aus_text("Unibibliothek hat neue Bücher", self.AGENTEN))
        self.assertIsNone(logik.absender_aus_text(None, self.AGENTEN))

    def test_entwurf_merken(self):
        with tempfile.TemporaryDirectory() as d:
            g = logik.Gemeldet(Path(d) / "g.json")
            g.entwurf_merken(7, "20261126-x")
            g.meldung_merken(8, "m1")
            self.assertEqual(g.entwurf_zu(7), "20261126-x")
            self.assertIsNone(g.entwurf_zu(8))
            self.assertIsNone(g.meldung_zu(7))
