"""Projektseiten: Inhalte kommen an, Filter wirken, fremde Links werden nicht zu Links."""

import unittest

import ablage
import projekt

from tests.hilfe import AUSZUG, EXPOSE, GEPRUEFT, Aufbau


class Logik(unittest.TestCase):
    def test_teile_markiert_offen(self):
        self.assertEqual(projekt.teile("a [OFFEN: x] b [OFFEN]"), [
            {"text": "a ", "offen": False}, {"text": "[OFFEN: x]", "offen": True}, {"text": " b ", "offen": False},
            {"text": "[OFFEN]", "offen": True}])
        self.assertEqual(projekt.teile(None), [])

    def test_offene_stellen_mit_abschnitt(self):
        self.assertEqual(projekt.offene_stellen(EXPOSE), [
            {"was": "Branchenzahlen", "abschnitt": "Ausgangslage"}, {"was": "ohne Angabe", "abschnitt": "Daten"},
            {"was": "Seitenzahl", "abschnitt": "Literatur"}])

    def test_unbekannter_block_wird_gezaehlt(self):
        self.assertEqual(projekt.expose_ansicht(EXPOSE)["ausgelassen"], 1)

    def test_links_nur_http_und_doi(self):
        for falsch in ("javascript:alert(1)", "data:text/html,x", "/data/mails/1.json", "https://x y.de", None, 3):
            self.assertIsNone(projekt.link_oder_none(falsch), falsch)
        self.assertEqual(projekt.link_oder_none("https://x.de/a"), "https://x.de/a")
        self.assertEqual(projekt.doi_link("10.1/ab"), "https://doi.org/10.1/ab")
        for falsch in ("keine doi", "javascript:alert(1)", None):
            self.assertIsNone(projekt.doi_link(falsch), falsch)

    def test_filter(self):
        self.assertEqual(projekt.aussagen_ansicht(GEPRUEFT, "gesichert", None)["anzahl"], 1)
        self.assertEqual(projekt.aussagen_ansicht(GEPRUEFT, None, "F2")["anzahl"], 1)
        unbekannt = projekt.aussagen_ansicht(GEPRUEFT, "<b>", "../F1")
        self.assertEqual((unbekannt["anzahl"], unbekannt["status"], unbekannt["frage"]), (2, None, None))

    def test_aussage_ohne_bekannte_frage_geht_nicht_verloren(self):
        daten = {**GEPRUEFT, "aussagen": [*GEPRUEFT["aussagen"], {"id": "x", "frage": "F99", "text": "Rest", "status": "teilweise"}]}
        self.assertEqual(projekt.aussagen_ansicht(daten, None, None)["anzahl"], 3)

    def test_zahlen_aus_den_aussagen(self):
        zahlen = projekt.recherche_zahlen(GEPRUEFT)
        self.assertEqual((zahlen["gesichert"], zahlen["unbelegt"], zahlen["teilweise"]), (1, 1, 0))

    def test_markdown(self):
        bloecke = projekt.markdown_bloecke("# K\n\n- a **b**\n1. c\n\nx\ny\n\nz")
        self.assertEqual([b["art"] for b in bloecke], ["kopf", "punkte", "absatz", "absatz"])
        self.assertEqual(bloecke[1]["punkte"][0][1], {"text": "b", "fett": True})

    def test_schriftverkehr_neueste_zuerst(self):
        ansicht = projekt.schriftverkehr_ansicht(AUSZUG)
        self.assertEqual([m["betreff"] for m in ansicht["kontakte"][0]["mails"]], ["AW: Anfrage", "Anfrage"])
        self.assertEqual(ansicht["kontakte"][1]["mails"], [])
        self.assertFalse(projekt.schriftverkehr_ansicht(None)["da"])


class Seiten(Aufbau):
    def test_navigation_auf_allen_seiten(self):
        for pfad in ("/projekt/fehlstellen", "/modul/holzschutz"):
            html = self.text(pfad)
            self.assertIn('href="/projekt/fehlstellen"', html)
            self.assertIn('href="/modul/holzschutz"', html)

    def test_expose(self):
        html = self.text("/projekt/fehlstellen")
        for erwartet in ("Fehlstellen &lt;erkennen&gt;", "Noch offen (3)", "Branchenzahlen", '<mark class="offen">[OFFEN: Branchenzahlen]</mark>',
                         "&lt;b&gt;danach&lt;/b&gt;", "Punkt eins", "Zeitplan", "kann diese Ansicht nicht anzeigen",
                         'href="/projekt/fehlstellen/fassung/pdf"', 'href="/projekt/fehlstellen/fassung/docx"'):
            self.assertIn(erwartet, html)

    def test_fassung_laden(self):
        antwort, inhalt = self.holen("/projekt/fehlstellen/fassung/pdf")
        self.assertEqual((antwort.status, inhalt), (200, b"%PDF-TEST"))
        self.assertIn("inline", antwort.getheader("content-disposition"))
        antwort, inhalt = self.holen("/projekt/fehlstellen/fassung/docx")
        self.assertEqual((antwort.status, inhalt), (200, b"DOCX-TEST"))
        self.assertIn("attachment", antwort.getheader("content-disposition"))
        self.assertEqual(antwort.getheader("cache-control"), "no-store")

    def test_recherche_aussagen(self):
        html = self.text("/projekt/fehlstellen/recherche")
        for erwartet in ("Was kostet es?", "Kamera kostet wenig", "wenig Geld", 'href="https://example.org/a"', "Beleg fehlt", "Keine Studie",
                         "DIN 4074-1.pdf, Seite 8"):
            self.assertIn(erwartet, html)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn("data/normen", html)

    def test_recherche_filter(self):
        html = self.text("/projekt/fehlstellen/recherche?status=gesichert")
        self.assertIn("Kamera kostet wenig", html)
        self.assertNotIn("Gut genug", html)
        self.assertNotIn("Kamera kostet wenig", self.text("/projekt/fehlstellen/recherche?frage=F2"))
        self.assertNotIn("<script", self.text("/projekt/fehlstellen/recherche?status=<script>&frage=<script>&ansicht=<script>"))

    def test_recherche_weitere_ansichten(self):
        quellen = self.text("/projekt/fehlstellen/recherche?ansicht=quellen")
        self.assertIn("Quelle A", quellen)
        self.assertIn('href="https://doi.org/10.1/ab"', quellen)
        self.assertNotIn('href="javascript:', quellen)
        self.assertLess(quellen.index("Quelle A"), quellen.index("Quelle B"))
        luecken = self.text("/projekt/fehlstellen/recherche?ansicht=luecken")
        self.assertIn("Preise fehlen", luecken)
        self.assertIn("passt nicht", luecken)
        self.assertIn("TITLE-ABS-KEY(wood)", self.text("/projekt/fehlstellen/recherche?ansicht=suche"))

    def test_protokoll(self):
        html = self.text("/projekt/fehlstellen/protokoll")
        self.assertIn("<strong>kurz</strong>", html)
        self.assertIn("&lt;i&gt;eins&lt;/i&gt; weiter", html)

    def test_schriftverkehr(self):
        html = self.text("/projekt/fehlstellen/schriftverkehr")
        for erwartet in ("Prof. Böhme", "AW: Anfrage", "Guten Tag &lt;b&gt;Herr&lt;/b&gt; Kleinke", "plan.pdf", "von dir", "an dich", "Keine Mails gefunden"):
            self.assertIn(erwartet, html)
        self.assertLess(html.index("AW: Anfrage"), html.index("Sehr geehrter"))

    def test_seiten_ohne_daten(self):
        (self.uni / "data" / "projekte" / "fehlstellen" / "schriftverkehr.json").unlink()
        self.assertIn("noch nicht abgeglichen", self.text("/projekt/fehlstellen/schriftverkehr"))
        kette = self.uni / "data" / "expose" / ablage.PROJEKTE["fehlstellen"]["kette"]
        (kette / "expose.json").unlink()
        (kette / "recherche" / "geprueft.json").unlink()
        self.assertIn("noch keine Fassung", self.text("/projekt/fehlstellen"))
        self.assertIn("noch keine geprüfte Recherche", self.text("/projekt/fehlstellen/recherche"))


if __name__ == "__main__":
    unittest.main()
