import unittest

import auslesen
from agentkit import wortlaut

GESETZ = """<html><head><meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
<title>&#167; 2 JGG - Einzelnorm</title></head><body>
<div id="blaettern_zurueck"><a href='__1.html'>zur&uuml;ck</a></div>
<div class="jnheader"><a href="index.html">Nichtamtliches Inhaltsverzeichnis</a><h1>Testgesetz (TG)<br />
<span class="jnenbez">&#167; 7</span>&#160;<span class="jnentitel">Gr&#252;nde der Strafe</span></h1></div>
<div><div class="jnhtml"><div><div class="jurAbsatz">(1) Die Strafe soll   wirken.</div>
<div class="jurAbsatz">(2) Dabei z&#228;hlen: <dl><dt></dt><dd><div>die Beweggr&#252;nde,</div>
<div>das Vorleben.</div></dd></dl></div><div class="jurAbsatz">(3) Ende.</div></div></div></div>
<div id="fusszeile"><ul><li><a href="#Seitenanfang">zum Seitenanfang</a></li></ul></div>
</body></html>"""

KORPORA = """<html><head><title>Kant: AA VI, Die Metaphysik der Sitten. ... , Seite 331</title></head><body>
<table>
<tr><td>&nbsp;</td><td>&nbsp;</td><td colspan="3"><p>Kant: AA VI, ... , <b>Seite 331</b></p></td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td><p>Zeile:</p></td><td colspan="3"><p>Text (Kant):</p></td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td><font>01<a name="z01"></a></td><td colspan="3"><h5><center> Vom Straf= und Begnadigungsrecht. </center></h5></td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td><td colspan="3">&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td><font>02<a name="z02"></a></td><td colspan="3"> zu sein, hei&#223;t Verbrechen schlechthin (<i> crimen </i>), aber </td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td><font>03<a name="z03"></a></td><td colspan="3"> vor die Civil=, das andere vor die <i> Criminal </i> gezogen. </td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td><td colspan="3"><p>[ <a href="330.html">Seite 330</a> ] [ <a href="332.html">Seite 332</a> ]</p></td></tr>
</table></body></html>"""


class GesetzTest(unittest.TestCase):
    def test_ueberschrift_und_normtext(self):
        g = auslesen.gesetz(GESETZ)
        self.assertEqual(g.ueberschrift, "§ 7 Gründe der Strafe")
        self.assertEqual(g.normtext.split("\n"), [
            "(1) Die Strafe soll wirken.", "(2) Dabei zählen:", "die Beweggründe,", "das Vorleben.", "(3) Ende."])

    def test_kein_rahmen(self):
        g = auslesen.gesetz(GESETZ)
        for rahmen in ("Inhaltsverzeichnis", "zurück", "Seitenanfang", "Testgesetz"):
            self.assertNotIn(rahmen, g.ueberschrift + g.normtext)

    def test_ohne_norm(self):
        with self.assertRaises(auslesen.ParserFehler):
            auslesen.gesetz("<html><body><p>Wartungsarbeiten</p></body></html>")

    def test_zeichensatz_aus_meta(self):
        roh = GESETZ.encode("latin-1") + "Grüße".encode("latin-1")
        self.assertTrue(auslesen.html_text(roh, "text/html").endswith("Grüße"))

    def test_zeichensatz_aus_header_geht_vor(self):
        self.assertEqual(auslesen.html_text("ä".encode("utf-8"), "text/html; charset=utf-8"), "ä")


class KorporaTest(unittest.TestCase):
    def test_seite_und_zeilen(self):
        seite, text = auslesen.korpora_seite(KORPORA)
        self.assertEqual(seite, 331)
        self.assertEqual(text.split("\n"), [
            "Vom Straf= und Begnadigungsrecht.",
            "zu sein, heißt Verbrechen schlechthin (crimen), aber",
            "vor die Civil=, das andere vor die Criminal gezogen."])

    def test_ohne_seitenzahl(self):
        with self.assertRaises(auslesen.ParserFehler):
            auslesen.korpora_seite(KORPORA.replace("Seite 331</title>", "</title>"))

    def test_ohne_text(self):
        with self.assertRaises(auslesen.ParserFehler):
            auslesen.korpora_seite("<html><head><title>Seite 5</title></head><body></body></html>")


class TextfassungTest(unittest.TestCase):
    def test_lesbar_fuer_wortlaut(self):
        text = auslesen.textfassung({332: "zweite\nSeite", 331: "erste Seite\n"})
        self.assertEqual(text, "--- Seite 331\nerste Seite\n--- Seite 332\nzweite\nSeite\n")
        self.assertEqual(wortlaut.seiten(text), {331: "\nerste Seite\n", 332: "\nzweite\nSeite\n"})

    def test_art_der_seite(self):
        self.assertEqual(auslesen.art_der_seite("https://www.gesetze-im-internet.de/jgg/__2.html"), "gesetz")
        self.assertEqual(auslesen.art_der_seite("https://korpora.org/kant/aa06/331.html"), "korpora")
        with self.assertRaises(auslesen.ParserFehler):
            auslesen.art_der_seite("https://zeno.org/x")


if __name__ == "__main__":
    unittest.main()
