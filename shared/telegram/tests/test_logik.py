import re
import tempfile
import unittest
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
    entwurf_als_text,
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
        e = {"agent": "posteingang", "typ": "mail", "titel": "Antwort", "inhalt": "x", "vorgaenger": None,
             "daten": {"an": ["prof@example.org"], "betreff": "Termin", "text": "Hallo " * 2000}}
        text = "".join(entwurf_als_text(e))
        self.assertEqual(text.count("prof@example.org"), 1)
        self.assertEqual(text.count("Hallo"), 2000)
        self.assertTrue(text.startswith("<b>Posteingang</b> · Mail-Entwurf\n<b>An prof@example.org</b>\nTermin\n"))
        self.assertGreater(len(entwurf_als_text(e)[0]), 1000)  # Kopf nicht allein in der ersten Nachricht
        kauf = entwurf_als_text({"agent": "einkauf", "typ": "kauf", "titel": "Kabel <USB>", "inhalt": "x",
                                 "daten": {"preis": 12.5, "menge": [1, 2]}, "vorgaenger": "alt"})
        self.assertIn("Kauf-Entwurf, überarbeitet\n<b>Kabel &lt;USB&gt;</b>\nPreis: 12.5\nMenge: 1, 2\n\n"
                      "<blockquote>x</blockquote>", kauf[0])

    def test_entwurf_mail_aus_daten(self):
        text = "Sehr geehrter Herr Böhme,\n\nvielen Dank & bis bald.\n\nMit besten Grüßen\nJan"
        e = {"agent": "uni", "typ": "mail", "titel": "Mail: AW: Betreuung", "vorgaenger": None, "inhalt": "egal",
             "daten": {"an": ["boehme@example.org"], "cc": ["a@example.org"], "betreff": "AW: Betreuung",
                       "text": text, "begruendung": "Er hat zugesagt. Bitte prüfe, ob Freitag passt.",
                       "in_reply_to": "<x@example.org>", "antwort_auf_uid": 7, "bcc": [], "anhang": "plan.pdf",
                       "antwort_auf": "\"Böhme, Klaus\" <boehme@example.org>: AW: AW: Betreuung"}}
        (n,) = entwurf_als_text(e)
        self.assertEqual(n.count("vielen Dank &amp; bis bald"), 1)
        self.assertIn("<b>An Klaus Böhme</b> (boehme@example.org)\nAW: Betreuung\n"
                      "<i>Antwort auf die Mail</i>\nCc: a@example.org\nAnhang: plan.pdf\n\n<blockquote>Sehr", n)
        self.assertTrue(n.endswith("</blockquote>\n\n<b>Bitte prüfen:</b> ob Freitag passt."))
        for weg in ("Details", "zugesagt", "x@example.org", "expandable"):
            self.assertNotIn(weg, n)
        termin = entwurf_als_text({"agent": "uni", "typ": "termin", "titel": "T", "inhalt": "x", "vorgaenger": None,
                                   "daten": {"titel": "x"}})
        self.assertIn("Termin-Entwurf", termin[0])
        self.assertNotIn("Titel:", termin[0])

    def test_betreff_und_bezug(self):
        self.assertEqual(logik.betreff_kurz("AW: AW: Re: AW:Anfrage"), "Re: Anfrage")
        self.assertEqual(logik.betreff_kurz("WG: AW: Plan"), "Fwd: Plan")
        self.assertEqual(logik.betreff_kurz("Plan"), "Plan")
        self.assertEqual(logik.name_aus('"Oppermann, J." <j@x.de>'), ("J. Oppermann", "j@x.de"))
        self.assertEqual(logik.name_aus("j@x.de"), ("j@x.de", "j@x.de"))
        daten = {"an": ["a@x.de"], "betreff": "Re: Neu", "antwort_auf_von": "Frau B <b@x.de>",
                 "antwort_auf_datum": "2026-08-11T10:00:00+02:00", "antwort_auf": "Frau B <b@x.de>: AW: AW: Alt"}
        self.assertEqual(logik.bezug_text(daten), "Antwort auf die Mail von Frau B vom 11.08.2026: „Re: Alt“")
        self.assertEqual(logik.bezug_text({"an": ["a@x.de"], "in_reply_to": "<y>"}), "Antwort auf eine frühere Mail")
        self.assertEqual(logik.bezug_text({"an": ["a@x.de"]}), "")

    def test_warum_und_frage(self):
        self.assertEqual(logik.warum_und_frage({"begruendung": "A. Bitte prüfe, ob x stimmt. B."}),
                         ("A. B.", "ob x stimmt."))
        self.assertEqual(logik.warum_und_frage({"begruendung": "A.", "pruefen": "ob x stimmt"}), ("A.", "ob x stimmt"))
        self.assertEqual(logik.warum_und_frage({}), ("", ""))

    def test_html_aufteilen_schneidet_keine_tags(self):
        html = "<b>Kopf</b>\n\n<blockquote>" + "\n".join(f"Zeile {i} &amp; " + "x" * 50 for i in range(300)) \
            + "</blockquote>\n\n<blockquote expandable><b>Warum so</b>\n" + "y" * 2500 + "</blockquote>"
        stuecke = logik.html_aufteilen(html, 1000)
        self.assertGreater(len(stuecke), 10)
        for s in stuecke:
            self.assertLessEqual(len(s), 1000)
            self.assertEqual(s.count("<blockquote"), s.count("</blockquote>"), s[:80])
            self.assertEqual(s.count("<b>"), s.count("</b>"))
            self.assertNotRegex(s, r"&[a-z]*$|<[^>]*$")
        self.assertTrue(stuecke[1].startswith("<blockquote>Zeile"))
        self.assertTrue(stuecke[-1].startswith("<blockquote expandable>"))
        ohne = re.compile(r"<[^>]+>|\s")
        self.assertEqual(ohne.sub("", "".join(stuecke)), ohne.sub("", html))
        self.assertEqual(logik.html_aufteilen("<b>kurz</b>"), ["<b>kurz</b>"])

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

        self.assertIn("erst nach der ersten Aufgabe", verbrauch_text(None, "normal", {}, zt))
        stand = {"5h": 0.11, "7d": 0.39, "reset_5h": 1, "reset_7d": 2, "zeit": 3}
        heute = {"uni": {"laeufe": 2, "tokens": 12000, "minuten": 1.5, "usd": 0.1, "fehler": 1}}
        text = verbrauch_text(stand, "sparen", heute, zt)
        for teil in ("5 Stunden: 11 %", "7 Tage: 39 %", "darum spare ich", "Uni: 2-mal gearbeitet, 1,5 Minuten",
                     "1-mal hat es nicht geklappt"):
            self.assertIn(teil, text)
        self.assertNotIn("Tokens", text)
        self.assertIn("Recherche (Lia): 2-mal", verbrauch_text(stand, "normal", {"lia/recherche": heute["uni"]}, zt))

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
        self.assertEqual(knoepfe[0], [("Uni", "u:a:uni:erledigen")])
        self.assertIn(("Entwürfe (2)", "u:entwuerfe"), knoepfe[1])

    def test_agent_modus_wechseln(self):
        text, knoepfe = logik.ansicht_agent("uni", "erledigen")
        self.assertIn("Auftrag an Uni (erledigen)", text)
        self.assertEqual(knoepfe[0][0][1], "u:a:uni:lernen")

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
        self.assertIn("Dokumente ist aber noch nicht eingerichtet", text)
        self.assertNotIn(self.A["id"], text)

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
        self.assertIn("sobald wieder Rechenzeit frei ist", stufe_text("normal", "limit", {}, zeit)[0])
        self.assertIn("wieder Rechenzeit frei", stufe_text("limit", "nur_auftraege", None, zeit)[0])
        self.assertTrue(stufe_text("limit", "normal", None, zeit)[0].startswith("<b>Zentrale</b>"))

    def test_bestaetigung(self):
        self.assertEqual(bestaetigung("uni", "erledigen", []), "Uni ist dran. Das Ergebnis kommt hierher.")
        self.assertEqual(bestaetigung("uni", "lernen", ["a.pdf", "b.pdf"]),
                         "Uni ist dran (lernen), mit 2 Dateien. Das Ergebnis kommt hierher.")

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
