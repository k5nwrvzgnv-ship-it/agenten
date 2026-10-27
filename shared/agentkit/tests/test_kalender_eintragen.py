import io
import unittest
import urllib.error
from datetime import date, datetime, timezone
from email.message import Message
from unittest import mock

from agentkit import kalender
from agentkit.kalender import ZONE, KalenderFehler, TerminSchonDa, aus_text

ZUGANG = {"ICLOUD_APPLE_ID": "jan@example.org", "ICLOUD_APP_PASSWORT": "abcd-efgh-ijkl-mnop",
          "ICLOUD_KALENDER": "Kalender"}
JETZT = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def multistatus(*antworten: str) -> bytes:
    return ('<?xml version="1.0"?><d:multistatus xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">'
            + "".join(antworten) + "</d:multistatus>").encode()


PRINCIPAL = multistatus("<d:response><d:href>/</d:href><d:propstat><d:prop><d:current-user-principal>"
                        "<d:href>/123456/principal/</d:href></d:current-user-principal></d:prop></d:propstat>"
                        "</d:response>")
HOME = multistatus("<d:response><d:href>/123456/principal/</d:href><d:propstat><d:prop><c:calendar-home-set>"
                   "<d:href>https://p42-caldav.icloud.com:443/123456/calendars/</d:href></c:calendar-home-set>"
                   "</d:prop></d:propstat></d:response>")


def kalender_eintrag(href: str, name: str, komponenten=("VEVENT",), kalender_typ=True) -> str:
    typ = "<d:collection/>" + ("<c:calendar/>" if kalender_typ else "")
    komp = "".join(f'<c:comp name="{k}"/>' for k in komponenten)
    return (f"<d:response><d:href>{href}</d:href><d:propstat><d:prop><d:displayname>{name}</d:displayname>"
            f"<d:resourcetype>{typ}</d:resourcetype><c:supported-calendar-component-set>{komp}"
            "</c:supported-calendar-component-set></d:prop></d:propstat></d:response>")


LISTE = multistatus(
    kalender_eintrag("/123456/calendars/", "", kalender_typ=False),
    kalender_eintrag("/123456/calendars/home/", "Kalender"),
    kalender_eintrag("/123456/calendars/uni/", "Uni"),
    kalender_eintrag("/123456/calendars/tasks/", "Erinnerungen", komponenten=("VTODO",)),
)


class FalscherServer:
    """Ersetzt _anfrage: gibt Antworten der Reihe nach und merkt sich die Anfragen."""

    def __init__(self, *antworten):
        self.antworten = list(antworten)
        self.anfragen = []

    def __call__(self, methode, url, zugang, daten, kopf):
        self.anfragen.append((methode, url, zugang, daten, kopf))
        status, endgueltig, inhalt = self.antworten.pop(0)
        return status, endgueltig or url, inhalt


def server(put_status=201):
    return FalscherServer((207, "https://p42-caldav.icloud.com/", PRINCIPAL), (207, None, HOME),
                          (207, None, LISTE), (put_status, None, b""))


class TestIcs(unittest.TestCase):
    def test_termin_mit_erinnerungen_ist_lesbar(self):
        beginn = datetime(2026, 11, 3, 14, 0, tzinfo=ZONE)
        text = kalender.ics("Gespräch Böhme, Exposé", beginn, datetime(2026, 11, 3, 15, 0, tzinfo=ZONE), "u1@x",
                            ort="Haus 2; Raum 105", beschreibung="Zeile 1\nZeile 2", erinnerungen=(1440, 120),
                            jetzt=JETZT)
        self.assertIn("METHOD:PUBLISH\r\n", text)
        self.assertIn("DTSTART:20261103T130000Z\r\n", text)
        self.assertEqual(text.count("BEGIN:VALARM"), 2)
        self.assertIn("TRIGGER:-PT1440M", text)
        (t,) = aus_text(text, datetime(2026, 11, 1, tzinfo=ZONE), datetime(2026, 11, 30, tzinfo=ZONE))
        self.assertEqual((t.titel, t.ort, t.beginn, t.uid), ("Gespräch Böhme, Exposé", "Haus 2; Raum 105", beginn, "u1@x"))

    def test_ganztags_ende_einschliesslich_und_ohne_methode(self):
        text = kalender.ics("Exkursion", date(2026, 11, 5), date(2026, 11, 6), "u2@x", ganztags=True,
                            methode=None, jetzt=JETZT)
        self.assertNotIn("METHOD", text)
        self.assertIn("DTSTART;VALUE=DATE:20261105\r\n", text)
        self.assertIn("DTEND;VALUE=DATE:20261107\r\n", text)

    def test_lange_zeilen_gefaltet_ohne_zeichen_zu_zerschneiden(self):
        text = kalender.ics("Ä" * 100, datetime(2026, 11, 3, 14, tzinfo=ZONE),
                            datetime(2026, 11, 3, 15, tzinfo=ZONE), "u3@x", jetzt=JETZT)
        for zeile in text.split("\r\n"):
            self.assertLessEqual(len(zeile.encode()), 75)
        self.assertIn("Ä" * 100, text.replace("\r\n ", ""))

    def test_feste_uid(self):
        beginn = datetime(2026, 11, 3, 14, tzinfo=ZONE)
        self.assertEqual(kalender.feste_uid("A", beginn), kalender.feste_uid("A", beginn))
        self.assertNotEqual(kalender.feste_uid("A", beginn), kalender.feste_uid("B", beginn))
        self.assertTrue(kalender.feste_uid("A", beginn, "uni.agenten").endswith("@uni.agenten"))


class TestPruefen(unittest.TestCase):
    def test_fehlerhafte_termine(self):
        b = datetime(2026, 11, 3, 14, tzinfo=ZONE)
        faelle = [("", b, b.replace(hour=15), False, ()),
                  ("T", b, b, False, ()),
                  ("T", b.replace(tzinfo=None), b.replace(hour=15, tzinfo=None), False, ()),
                  ("T", date(2026, 11, 3), date(2026, 11, 3), False, ()),
                  ("T", date(2026, 11, 3), date(2026, 11, 2), True, ()),
                  ("T", b, b.replace(hour=15), False, (-5,))]
        for fall in faelle:
            with self.subTest(fall=fall), self.assertRaises(KalenderFehler):
                kalender.termin_pruefen(*fall)
        kalender.termin_pruefen("T", date(2026, 11, 3), date(2026, 11, 3), True, (900,))


class TestKalenderliste(unittest.TestCase):
    def test_nur_kalender_mit_terminen(self):
        self.assertEqual(kalender.kalenderliste(LISTE), [("/123456/calendars/home/", "Kalender"),
                                                         ("/123456/calendars/uni/", "Uni")])

    def test_waehlen_genau_ein_treffer(self):
        liste = kalender.kalenderliste(LISTE)
        self.assertEqual(kalender.kalender_waehlen(liste, "Uni"), "/123456/calendars/uni/")
        with self.assertRaisesRegex(KalenderFehler, "Vorhanden: Kalender, Uni"):
            kalender.kalender_waehlen(liste, "Privat")
        with self.assertRaisesRegex(KalenderFehler, "umbenennen"):
            kalender.kalender_waehlen(liste + [("/x/", "Uni")], "Uni")

    def test_kaputte_antwort(self):
        with self.assertRaises(KalenderFehler):
            kalender.kalenderliste(b"<kein xml")


class TestEintragen(unittest.TestCase):
    def eintragen(self, falsch, **extra):
        args = dict(agent="uni", ort="Haus 2", notiz="Mit Felix und Henri", erinnerungen=(1440, 120), config=ZUGANG)
        args.update(extra)
        with mock.patch.object(kalender, "_anfrage", falsch):
            return kalender.eintragen("Gespräch Böhme", datetime(2026, 11, 3, 14, tzinfo=ZONE),
                                      datetime(2026, 11, 3, 15, tzinfo=ZONE), **args)

    def test_ablauf_und_put(self):
        falsch = server()
        uid = self.eintragen(falsch)
        self.assertEqual(uid, kalender.feste_uid("Gespräch Böhme", datetime(2026, 11, 3, 14, tzinfo=ZONE)))
        urls = [a[1] for a in falsch.anfragen]
        self.assertEqual(urls[:3], ["https://caldav.icloud.com/", "https://p42-caldav.icloud.com/123456/principal/",
                                    "https://p42-caldav.icloud.com:443/123456/calendars/"])
        methode, url, zugang, daten, kopf = falsch.anfragen[3]
        self.assertEqual(methode, "PUT")
        self.assertEqual(url, f"https://p42-caldav.icloud.com:443/123456/calendars/home/{uid.replace('@', '%40')}.ics")
        self.assertEqual(kopf["If-None-Match"], "*")
        self.assertEqual(zugang, ("jan@example.org", "abcd-efgh-ijkl-mnop"))
        text = daten.decode()
        self.assertNotIn("METHOD", text)
        self.assertEqual(text.count("BEGIN:VALARM"), 2)
        self.assertIn("Mit Felix und Henri\\n\\nangelegt vom Uni-Agenten", text.replace("\r\n ", ""))

    def test_eigene_uid(self):
        self.assertEqual(self.eintragen(server(), uid="abc@uni.agenten"), "abc@uni.agenten")

    def test_schon_da(self):
        with self.assertRaises(TerminSchonDa):
            self.eintragen(server(412))

    def test_anderer_fehler_beim_put(self):
        with self.assertRaisesRegex(KalenderFehler, "HTTP 403"):
            self.eintragen(server(403))

    def test_fehlender_zugang_ohne_anfrage(self):
        falsch = FalscherServer()
        with self.assertRaisesRegex(KalenderFehler, "ICLOUD_APP_PASSWORT"):
            self.eintragen(falsch, config={**ZUGANG, "ICLOUD_APP_PASSWORT": ""})
        self.assertEqual(falsch.anfragen, [])

    def test_ungueltiger_termin_ohne_anfrage(self):
        falsch = FalscherServer()
        with self.assertRaises(KalenderFehler):
            self.eintragen(falsch, erinnerungen=(-1,))
        self.assertEqual(falsch.anfragen, [])

    def test_kalender_unbekannt(self):
        falsch = server()
        with self.assertRaisesRegex(KalenderFehler, "Privat"):
            self.eintragen(falsch, config={**ZUGANG, "ICLOUD_KALENDER": "Privat"})
        self.assertEqual(len(falsch.anfragen), 3)  # kein PUT


def http_fehler(url, status, location=None):
    kopf = Message()
    if location:
        kopf["Location"] = location
    return urllib.error.HTTPError(url, status, "x", kopf, io.BytesIO(b""))


class Antwort(io.BytesIO):
    def __init__(self, url, status=207, inhalt=b"<ok/>"):
        super().__init__(inhalt)
        self.status, self._url = status, url

    def geturl(self):
        return self._url


class TestAnfrage(unittest.TestCase):
    def test_weiterleitung_innerhalb_icloud_mit_anmeldung(self):
        gesehen = []

        def oeffnen(anfrage, timeout):
            gesehen.append((anfrage.full_url, anfrage.get_method(), anfrage.get_header("Authorization")))
            if len(gesehen) == 1:
                raise http_fehler(anfrage.full_url, 301, "https://p42-caldav.icloud.com/")
            return Antwort(anfrage.full_url)

        with mock.patch.object(kalender._OEFFNER, "open", oeffnen):
            status, url, _ = kalender._anfrage("PROPFIND", "https://caldav.icloud.com/", ("a", "b"), b"x", {})
        self.assertEqual((status, url), (207, "https://p42-caldav.icloud.com/"))
        self.assertEqual([g[1] for g in gesehen], ["PROPFIND", "PROPFIND"])
        self.assertTrue(all(g[2] == "Basic YTpi" for g in gesehen))

    def test_weiterleitung_nach_aussen_abgelehnt(self):
        for ziel in ("https://evil.example/", "http://p42-caldav.icloud.com/", "https://icloud.com.evil.example/"):
            def oeffnen(anfrage, timeout, ziel=ziel):
                if "evil" in anfrage.full_url or anfrage.full_url.startswith("http:"):
                    self.fail("Anfrage nach außen geschickt")
                raise http_fehler(anfrage.full_url, 302, ziel)
            with self.subTest(ziel=ziel), mock.patch.object(kalender._OEFFNER, "open", oeffnen), \
                    self.assertRaisesRegex(KalenderFehler, "außerhalb"):
                kalender._anfrage("PROPFIND", "https://caldav.icloud.com/", ("a", "b"), b"x", {})

    def test_anmeldung_abgelehnt_ohne_passwort_in_meldung(self):
        def oeffnen(anfrage, timeout):
            raise http_fehler(anfrage.full_url, 401)
        with mock.patch.object(kalender._OEFFNER, "open", oeffnen), self.assertRaises(KalenderFehler) as f:
            kalender._anfrage("PROPFIND", "https://caldav.icloud.com/", ("jan", "geheim"), b"x", {})
        self.assertNotIn("geheim", str(f.exception))

    def test_netzfehler(self):
        def oeffnen(anfrage, timeout):
            raise urllib.error.URLError("timed out")
        with mock.patch.object(kalender._OEFFNER, "open", oeffnen), \
                self.assertRaisesRegex(KalenderFehler, "nicht erreichbar"):
            kalender._anfrage("PUT", "https://p42-caldav.icloud.com/x.ics", ("a", "b"), b"x", {})

    def test_412_wird_durchgereicht(self):
        def oeffnen(anfrage, timeout):
            raise http_fehler(anfrage.full_url, 412)
        with mock.patch.object(kalender._OEFFNER, "open", oeffnen):
            self.assertEqual(kalender._anfrage("PUT", "https://p42-caldav.icloud.com/x.ics", ("a", "b"), b"x", {})[0],
                             412)
