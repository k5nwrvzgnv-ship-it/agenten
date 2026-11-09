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
        self.anfragen = []

    def https_open(self, req):
        self.aufrufe.append((req.full_url, req.get_header("User-agent")))
        self.anfragen.append(req)
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


class PostUndHeaderTest(Basis):
    TED = "https://api.ted.europa.eu/v3/notices/search"
    GENESIS = "https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile"
    JOBS = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs?was=Tischler"
    LISTE = ALLOWLIST + ["ted.europa.eu", "destatis.de", "arbeitsagentur.de"]

    def laden(self, url, antworten, **kw):
        self.netz = FalschesNetz(antworten)
        return abruf.laden(url, self.LISTE, self.cache, _opener=abruf.opener(self.LISTE, self.netz), **kw)

    def alle_cache_texte(self):
        return "".join(f.read_bytes().decode("utf-8", "replace") for f in self.cache.iterdir())

    def test_post_json_mit_koerper_und_meta(self):
        daten = json.dumps({"query": "CPV=45000000", "limit": 10}).encode()
        erg = self.laden(self.TED, {self.TED: (200, {"Content-Type": "application/json"}, b'{"notices": []}')},
                         methode="POST", daten=daten, header={"Content-Type": "application/json"})
        anfrage = self.netz.anfragen[0]
        self.assertEqual(anfrage.get_method(), "POST")
        self.assertEqual(anfrage.data, daten)
        self.assertEqual(anfrage.get_header("Content-type"), "application/json")
        self.assertEqual(anfrage.get_header("User-agent"), abruf.USER_AGENT)
        self.assertEqual(erg.meta["methode"], "POST")
        self.assertEqual(erg.meta["daten_sha256"], abruf.hashlib.sha256(daten).hexdigest())
        self.assertEqual(json.loads(erg.text()), {"notices": []})

    def test_post_cache_je_daten(self):
        antwort = {self.TED: (200, {}, b"eins")}
        self.laden(self.TED, antwort, methode="POST", daten=b'{"q": 1}')
        self.assertTrue(self.laden(self.TED, {}, methode="POST", daten=b'{"q": 1}').aus_cache)
        # andere Daten, andere Methode: eigener Eintrag, also neue Anfrage
        erg = self.laden(self.TED, {self.TED: (200, {}, b"zwei")}, methode="POST", daten=b'{"q": 2}')
        self.assertFalse(erg.aus_cache)
        erg = self.laden(self.TED, {self.TED: (200, {}, b"drei")})
        self.assertFalse(erg.aus_cache)
        self.assertEqual(erg.meta["methode"], "GET")
        self.assertNotIn("daten_sha256", erg.meta)
        self.assertEqual(self.laden(self.TED, {}, methode="POST", daten=b'{"q": 1}').inhalt, b"eins")
        self.assertEqual(len(list(self.cache.glob("*.bin"))), 3)

    def test_post_ohne_daten_eigener_eintrag(self):
        self.laden(self.TED, {self.TED: (200, {}, b"get")})
        erg = self.laden(self.TED, {self.TED: (200, {}, b"post")}, methode="post")
        self.assertFalse(erg.aus_cache)
        self.assertEqual(self.netz.anfragen[0].get_method(), "POST")
        self.assertEqual(self.laden(self.TED, {}).inhalt, b"get")

    def test_get_schluessel_wie_bisher(self):
        # Alte Cache-Einträge (Name = sha256 der URL, Meta ohne "methode") bleiben gültig
        self.assertEqual(abruf._schluessel(self.TED), abruf.hashlib.sha256(self.TED.encode()).hexdigest())
        self.laden(self.TED, {self.TED: (200, {}, b"alt")})
        meta_datei = next(self.cache.glob("*.json"))
        meta = json.loads(meta_datei.read_text())
        del meta["methode"]
        meta_datei.write_text(json.dumps(meta))
        self.assertTrue(self.laden(self.TED, {}).aus_cache)

    def test_schluessel_ohne_verwechslung(self):
        self.assertNotEqual(abruf._schluessel("https://a.de/x", "POST", b""),
                            abruf._schluessel("https://a.de/x", "POST", None) + "x")
        self.assertNotEqual(abruf._schluessel("https://a.de/x", "POST", b"y"),
                            abruf._schluessel("https://a.de/xy", "POST", b""))

    def test_header_nie_in_cache_oder_schluessel(self):
        geheim = "GEHEIMER-TOKEN-123"
        erg = self.laden(self.GENESIS, {self.GENESIS: (200, {}, b"Tabelle")}, methode="POST",
                         daten=b"name=61111-0001&format=ffcsv",
                         header={"username": geheim, "password": "",
                                 "Content-Type": "application/x-www-form-urlencoded"})
        anfrage = self.netz.anfragen[0]
        self.assertEqual(anfrage.get_header("Username"), geheim)
        self.assertEqual(anfrage.get_header("Password"), "")
        self.assertNotIn(geheim, json.dumps(erg.meta))
        self.assertNotIn(geheim, self.alle_cache_texte())
        # anderer Token, gleiche Anfrage: Cache-Treffer (Header zählen nicht)
        self.assertTrue(self.laden(self.GENESIS, {}, methode="POST", daten=b"name=61111-0001&format=ffcsv",
                                   header={"username": "anderer"}).aus_cache)

    def test_header_bei_get(self):
        self.laden(self.JOBS, {self.JOBS: (200, {}, b"{}")}, header={"X-API-Key": "jobboerse-jobsuche"})
        self.assertEqual(self.netz.anfragen[0].get_method(), "GET")
        self.assertEqual(self.netz.anfragen[0].get_header("X-api-key"), "jobboerse-jobsuche")
        self.assertIsNone(self.netz.anfragen[0].data)

    def test_eigener_user_agent_ersetzt_standard(self):
        self.laden(self.JOBS, {self.JOBS: (200, {}, b"{}")}, header={"user-agent": "Jobsuche/2.9.2"})
        self.assertEqual(self.netz.anfragen[0].get_header("User-agent"), "Jobsuche/2.9.2")

    def test_fehlertext_ohne_header_wert(self):
        geheim = "GEHEIMER-SCHLUESSEL"
        with self.assertRaises(abruf.AbrufFehler) as fehler:
            self.laden(self.JOBS, {self.JOBS: (401, {}, b"")}, header={"Ocp-Apim-Subscription-Key": geheim})
        self.assertIn("HTTP-Fehler 401", str(fehler.exception))
        self.assertNotIn(geheim, str(fehler.exception))
        with self.assertRaises(abruf.AbrufFehler) as fehler:
            self.laden(self.JOBS, {}, header={"X-Key": geheim + "\nX-Boese: 1"})
        self.assertNotIn(geheim, str(fehler.exception))

    def test_weiterleitung_nimmt_header_mit_aber_nur_erlaubt(self):
        ziel = "https://www.destatis.de/neu"
        erg = self.laden(self.GENESIS, {self.GENESIS: (302, {"Location": ziel}, b""), ziel: (200, {}, b"ok")},
                         header={"username": "t"})
        self.assertEqual(erg.inhalt, b"ok")
        self.assertEqual(self.netz.anfragen[1].get_header("Username"), "t")
        with self.assertRaisesRegex(abruf.AbrufFehler, "Domain nicht erlaubt"):
            self.laden(self.GENESIS, {self.GENESIS: (302, {"Location": "https://evil.example/x"}, b"")},
                       header={"username": "t"}, neu=True)
        self.assertEqual(len(self.netz.anfragen), 1)

    def test_ungueltige_eingaben(self):
        faelle = [
            ({"methode": "DELETE"}, "nicht unterstützt"),
            ({"daten": b"x"}, "GET mit daten"),
            ({"methode": "POST", "daten": "text"}, "bytes"),
            ({"header": [("a", "b")]}, "dict"),
            ({"header": {"a": 1}}, "Ungültiger Wert"),
            ({"header": {"a:b": "c"}}, "Ungültiger Header-Name"),
            ({"header": {"a": "b\r\nc: d"}}, "Ungültiger Wert"),
        ]
        for kw, muster in faelle:
            with self.subTest(kw=kw), self.assertRaisesRegex(abruf.AbrufFehler, muster):
                self.laden(self.TED, {}, **kw)
        self.assertEqual(self.netz.anfragen, [])

    def test_post_cache_beschaedigt_erkannt(self):
        self.laden(self.TED, {self.TED: (200, {}, b"eins")}, methode="POST", daten=b"a")
        meta_datei = next(self.cache.glob("*.json"))
        meta = json.loads(meta_datei.read_text())
        meta["daten_sha256"] = "falsch"
        meta_datei.write_text(json.dumps(meta))
        with self.assertRaisesRegex(abruf.AbrufFehler, "Cache beschädigt für POST"):
            self.laden(self.TED, {}, methode="POST", daten=b"a")


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
