import email.message
import io
import json
import socket
import tempfile
import unittest
import urllib.error
import urllib.request
import urllib.response
from pathlib import Path
from unittest import mock

from agentkit import abruf

ALLOWLIST = ["gesetze-im-internet.de", "de.wikisource.org", "zeno.org", "korpora.org", "archive.org"]


class FalschesNetz(urllib.request.BaseHandler):
    """Beantwortet https-Anfragen aus einem dict url -> (status, headers, body). Kein echtes Netz."""
    handler_order = 100

    def __init__(self, antworten):
        self.antworten = antworten
        self.aufrufe = []

    def https_open(self, req):
        self.aufrufe.append((req.full_url, req.get_header("User-agent")))
        if req.full_url not in self.antworten:
            raise AssertionError(f"unerwartete Anfrage {req.full_url}")
        status, kopf, inhalt = self.antworten[req.full_url]
        if isinstance(status, BaseException):
            raise status
        nachricht = email.message.Message()
        for k, v in kopf.items():
            nachricht[k] = v
        antwort = urllib.response.addinfourl(io.BytesIO(inhalt), nachricht, req.full_url, status)
        antwort.msg = "OK" if status == 200 else "Fehler"
        return antwort


class Basis(unittest.TestCase):
    def setUp(self):
        self.cache = Path(tempfile.mkdtemp()) / "cache"
        abruf._zuletzt.clear()
        self.zeit = [1000.0]
        self.pausen = []
        mock.patch.object(abruf, "_uhr", lambda: self.zeit[0]).start()
        mock.patch.object(abruf, "_schlafen", self.schlafen).start()
        self.addCleanup(mock.patch.stopall)

    def schlafen(self, s):
        self.pausen.append(s)
        self.zeit[0] += s

    def laden(self, url, antworten, **kw):
        self.netz = FalschesNetz(antworten)
        return abruf.laden(url, ALLOWLIST, self.cache, _opener=abruf.opener(ALLOWLIST, self.netz), **kw)


class AllowlistTest(unittest.TestCase):
    def test_domain_und_subdomain(self):
        self.assertTrue(abruf.host_erlaubt("archive.org", ALLOWLIST))
        self.assertTrue(abruf.host_erlaubt("ia800204.us.archive.org", ALLOWLIST))
        self.assertTrue(abruf.host_erlaubt("www.korpora.org", ALLOWLIST))
        self.assertTrue(abruf.host_erlaubt("ARCHIVE.ORG.", ALLOWLIST))

    def test_fremde_hosts(self):
        for host in ["evilarchive.org", "archive.org.evil.com", "wikisource.org", "en.wikisource.org",
                     "korpora.org.example", "", "xarchive.org"]:
            self.assertFalse(abruf.host_erlaubt(host, ALLOWLIST), host)

    def test_leere_allowlist(self):
        self.assertFalse(abruf.host_erlaubt("archive.org", []))
        self.assertFalse(abruf.host_erlaubt("archive.org", [""]))

    def test_pruefen(self):
        self.assertEqual(abruf.pruefen("https://korpora.org/kant/aa06/331.html", ALLOWLIST), "korpora.org")
        with self.assertRaisesRegex(abruf.AbrufFehler, "Nur https"):
            abruf.pruefen("http://korpora.org/", ALLOWLIST)
        with self.assertRaisesRegex(abruf.AbrufFehler, "Nur https"):
            abruf.pruefen("ftp://archive.org/x", ALLOWLIST)
        with self.assertRaisesRegex(abruf.AbrufFehler, "Domain nicht erlaubt: evilarchive.org"):
            abruf.pruefen("https://evilarchive.org/x", ALLOWLIST)
        with self.assertRaisesRegex(abruf.AbrufFehler, "Domain nicht erlaubt"):
            abruf.pruefen("https://archive.org@evil.com/x", ALLOWLIST)


class ZeichensatzTest(unittest.TestCase):
    def test_korpora_doppelt(self):
        self.assertEqual(abruf.zeichensatz("text/html; charset=Charset=ISO-8859-1"), "iso8859-1")
        self.assertEqual(abruf.als_text("Würde".encode("latin-1"), "text/html; charset=Charset=ISO-8859-1"), "Würde")

    def test_ohne_angabe_utf8(self):
        self.assertEqual(abruf.zeichensatz(None), "utf-8")
        self.assertEqual(abruf.zeichensatz("text/plain"), "utf-8")
        self.assertEqual(abruf.als_text("Würde".encode(), None), "Würde")

    def test_varianten(self):
        self.assertEqual(abruf.zeichensatz('text/html; charset="UTF-8"'), "utf-8")
        self.assertEqual(abruf.zeichensatz("text/html;charset=windows-1252"), "cp1252")

    def test_unbekannt_und_falsch(self):
        with self.assertRaisesRegex(abruf.AbrufFehler, "Unbekannter Zeichensatz"):
            abruf.zeichensatz("text/html; charset=quatsch-99")
        with self.assertRaisesRegex(abruf.AbrufFehler, "passt nicht"):
            abruf.als_text("Würde".encode("latin-1"), "text/html")


class HtmlTest(unittest.TestCase):
    def test_ohne_script_und_style(self):
        quelle = """<html><head><title>§ 46 StGB</title><style>p {color: red}</style>
        <script>var x = "<p>nicht</p>";</script></head><body>
        <h1>Grundsätze der Strafzumessung</h1><p>(1) Die Schuld des T&auml;ters ist Grundlage
        für die Zumessung&nbsp;der Strafe.</p><noscript>Bitte JS</noscript><div>Ende<br>Zeile</div></body></html>"""
        text = abruf.html_zu_text(quelle)
        self.assertEqual(text.splitlines()[0], "§ 46 StGB")
        self.assertIn("Grundsätze der Strafzumessung", text.splitlines())
        self.assertNotIn("color", text)
        self.assertNotIn("var x", text)
        self.assertNotIn("nicht", text)
        self.assertNotIn("Bitte JS", text)
        self.assertIn("Ende\nZeile", text)
        from agentkit import wortlaut
        self.assertTrue(wortlaut.steht_in("Die Schuld des Täters ist Grundlage für die Zumessung der Strafe.", text))

    def test_meta_bei_youtube(self):
        quelle = """<!DOCTYPE html><html><head><title>Strafe muss sein? - YouTube</title>
        <meta property="og:title" content="Strafe muss sein?">
        <meta property="og:description" content="Warum strafen wir? Ein Erkl&auml;rvideo.">
        <meta name="description" content="Warum strafen wir? Ein Erkl&auml;rvideo.">
        <meta property="og:image" content="https://i.ytimg.com/x.jpg"></head>
        <body><script>ytInitialData = {"a": 1}</script></body></html>"""
        self.assertEqual(abruf.html_zu_text(quelle).splitlines(),
                         ["Strafe muss sein? - YouTube", "Strafe muss sein?", "Warum strafen wir? Ein Erklärvideo."])

    def test_ohne_kopf_und_kaputtes_html(self):
        self.assertEqual(abruf.html_zu_text("<p>Kant <b>sagt</b>:<p>Strafe"), "Kant sagt:\nStrafe")
        self.assertEqual(abruf.html_zu_text(""), "")
        self.assertEqual(abruf.html_zu_text("<svg/><p>a</p><svg><text>b</text></svg><p>c</p>"), "a\nc")


class LadenTest(Basis):
    URL = "https://korpora.org/kant/aa06/331.html"

    def test_laden_mit_meta_und_text(self):
        erg = self.laden(self.URL, {self.URL: (200, {"Content-Type": "text/html; charset=Charset=ISO-8859-1"},
                                               "Strafe".encode("latin-1"))})
        self.assertFalse(erg.aus_cache)
        self.assertEqual(erg.text(), "Strafe")
        self.assertEqual(erg.text_ohne_html(), "Strafe")
        self.assertEqual(erg.meta["url"], self.URL)
        self.assertEqual(erg.meta["endgueltige_url"], self.URL)
        self.assertEqual(erg.meta["status"], 200)
        self.assertEqual(erg.meta["groesse"], 6)
        self.assertIn("abgerufen", erg.meta)
        self.assertEqual(self.netz.aufrufe[0][1], abruf.USER_AGENT)
        self.assertNotIn("@", abruf.USER_AGENT)
        meta = json.loads(next(self.cache.glob("*.json")).read_text())
        self.assertEqual(meta["sha256"], erg.meta["sha256"])

    def test_cache_treffer_ohne_netz(self):
        self.laden(self.URL, {self.URL: (200, {}, b"eins")})
        erg = self.laden(self.URL, {})  # FalschesNetz ohne Antworten: jede Anfrage wäre ein Fehler
        self.assertTrue(erg.aus_cache)
        self.assertEqual(erg.inhalt, b"eins")
        self.assertEqual(self.netz.aufrufe, [])

    def test_neu_laedt_trotz_cache(self):
        self.laden(self.URL, {self.URL: (200, {}, b"eins")})
        erg = self.laden(self.URL, {self.URL: (200, {}, b"zwei")}, neu=True)
        self.assertFalse(erg.aus_cache)
        self.assertEqual(self.laden(self.URL, {}).inhalt, b"zwei")

    def test_cache_beschaedigt(self):
        self.laden(self.URL, {self.URL: (200, {}, b"eins")})
        next(self.cache.glob("*.bin")).write_bytes(b"anders")
        with self.assertRaisesRegex(abruf.AbrufFehler, "Cache beschädigt"):
            self.laden(self.URL, {})

    def test_domain_vor_cache_geprueft(self):
        with self.assertRaisesRegex(abruf.AbrufFehler, "Domain nicht erlaubt"):
            self.laden("https://evilarchive.org/x", {})
        with self.assertRaisesRegex(abruf.AbrufFehler, "Nur https"):
            self.laden("http://korpora.org/x", {})
        self.assertEqual(self.netz.aufrufe, [])

    def test_weiterleitung_archive_erlaubt(self):
        start = "https://archive.org/download/zweckgedanke/text.txt"
        ziel = "https://ia800204.us.archive.org/1/items/zweckgedanke/text.txt"
        erg = self.laden(start, {start: (302, {"Location": ziel}, b""), ziel: (200, {}, b"Liszt")})
        self.assertEqual(erg.inhalt, b"Liszt")
        self.assertEqual(erg.meta["endgueltige_url"], ziel)

    def test_weiterleitung_nach_aussen(self):
        start = "https://archive.org/download/x"
        with self.assertRaisesRegex(abruf.AbrufFehler, "Weiterleitung.*Domain nicht erlaubt: evilarchive.org"):
            self.laden(start, {start: (302, {"Location": "https://evilarchive.org/x"}, b"")})
        self.assertEqual(len(self.netz.aufrufe), 1)
        self.assertEqual(list(self.cache.glob("*")) if self.cache.exists() else [], [])

    def test_weiterleitung_auf_http(self):
        start = "https://archive.org/download/x"
        with self.assertRaisesRegex(abruf.AbrufFehler, "Weiterleitung.*Nur https"):
            self.laden(start, {start: (301, {"Location": "http://archive.org/x"}, b"")})

    def test_http_fehler(self):
        with self.assertRaisesRegex(abruf.AbrufFehler, "HTTP-Fehler 404"):
            self.laden(self.URL, {self.URL: (404, {}, b"weg")})

    def test_zu_gross_laut_kopf(self):
        with self.assertRaisesRegex(abruf.AbrufFehler, "Zu groß: 100 Bytes"):
            self.laden(self.URL, {self.URL: (200, {"Content-Length": "100"}, b"x")}, max_bytes=10)

    def test_zu_gross_beim_lesen(self):
        with self.assertRaisesRegex(abruf.AbrufFehler, "Zu groß: mehr als 10"):
            self.laden(self.URL, {self.URL: (200, {}, b"x" * 11)}, max_bytes=10)
        self.assertEqual(self.laden(self.URL, {self.URL: (200, {}, b"x" * 10)}, max_bytes=10).meta["groesse"], 10)

    def test_zeitueberschreitung(self):
        for fehler in [urllib.error.URLError(socket.timeout("timed out")), TimeoutError("timed out")]:
            with self.assertRaisesRegex(abruf.AbrufFehler, "Zeitüberschreitung"):
                self.laden(self.URL, {self.URL: (fehler, {}, b"")}, neu=True)

    def test_netzfehler(self):
        with self.assertRaisesRegex(abruf.AbrufFehler, "Netzfehler"):
            self.laden(self.URL, {self.URL: (urllib.error.URLError("Name or service not known"), {}, b"")})


class PauseTest(Basis):
    def test_pause_je_host(self):
        a, b = "https://korpora.org/a", "https://korpora.org/b"
        c = "https://zeno.org/c"
        self.laden(a, {a: (200, {}, b"1")})
        self.assertEqual(self.pausen, [])
        self.zeit[0] += 0.5
        self.laden(b, {b: (200, {}, b"2")})
        self.assertEqual(self.pausen, [1.5])
        self.laden(c, {c: (200, {}, b"3")})  # anderer Host: keine Pause
        self.assertEqual(self.pausen, [1.5])
        self.zeit[0] += 5
        self.laden(a, {a: (200, {}, b"1")}, neu=True)  # lange genug her
        self.assertEqual(self.pausen, [1.5])

    def test_cache_ohne_pause(self):
        a = "https://korpora.org/a"
        self.laden(a, {a: (200, {}, b"1")})
        self.laden(a, {})
        self.assertEqual(self.pausen, [])


if __name__ == "__main__":
    unittest.main()
