import unittest
from datetime import date, datetime
from types import SimpleNamespace

import auftrag
from auftrag import AuftragFehler

HEUTE = date(2026, 10, 27)


def mail(uid, ordner="INBOX", datum="2026-10-01T10:00:00+02:00", **felder):
    return {"uid": uid, "ordner": ordner, "von": f"x{uid}@example.de", "datum": datum, "betreff": f"B{uid}",
            "message_id": f"<{ordner}{uid}@x>", "wortlaut": f"Text {uid}", **felder}


class Postfach:
    """Gibt je (ordner, Kriterium) feste Mails zurück und merkt sich die Aufrufe."""

    def __init__(self, treffer=None):
        self.treffer = treffer or {}
        self.aufrufe = []

    def __call__(self, ordner, von=None, an=None, text=None, seit=None, max_mails=20):
        self.aufrufe.append((ordner, von, an, text, seit))
        return list(self.treffer.get((ordner, von or an or text), []))


def termin(titel, tag=3):
    return SimpleNamespace(beginn=datetime(2026, 11, tag, 16), ende=datetime(2026, 11, tag, 17), titel=titel,
                           ort="Praxis", ganztags=False)


class TestSuche(unittest.TestCase):
    def test_prompt_enthaelt_auftrag_und_datum(self):
        p = auftrag.prompt_suche("Termin absagen", HEUTE)
        self.assertIn("Termin absagen", p)
        self.assertIn("27.10.2026", p)

    def test_suche_lesen_aus_codeblock(self):
        s = auftrag.suche_lesen('```json\n{"personen": ["Oppenheimer"], "stichworte": ["Paarberatung"], '
                                '"tage_zurueck": 365, "kalender_tage": 14}\n```')
        self.assertEqual(s, {"personen": ["Oppenheimer"], "stichworte": ["Paarberatung"], "tage_zurueck": 365,
                             "kalender_tage": 14})

    def test_suche_begrenzt(self):
        s = auftrag.suche_lesen('{"personen": ["a1", "a2", "A1", "a3", "a4", "x"], "stichworte": [], '
                                '"tage_zurueck": 99999, "kalender_tage": "viel"}')
        self.assertEqual(s["personen"], ["a1", "a2", "a3"])
        self.assertEqual(s["tage_zurueck"], auftrag.MAX_TAGE_ZURUECK)
        self.assertEqual(s["kalender_tage"], 14)

    def test_ohne_begriffe_fehler(self):
        with self.assertRaises(AuftragFehler):
            auftrag.suche_lesen('{"personen": [], "stichworte": []}')
        with self.assertRaises(AuftragFehler):
            auftrag.suche_lesen("Ich brauche mehr Infos.")


class TestKontext(unittest.TestCase):
    SUCHE = {"personen": ["Oppenheimer"], "stichworte": ["Paarberatung"], "tage_zurueck": 365, "kalender_tage": 14}

    def test_sucht_eingang_und_gesendet_und_entdoppelt(self):
        doppelt = mail(5, datum="2026-10-20T09:00:00+02:00")
        gesendet = [mail(7, "Sent", "2026-10-21T09:00:00+02:00", an=["o@praxis.de"]),
                    mail(8, "Sent", "2026-09-01T09:00:00+02:00")]
        postfach = Postfach({("INBOX", "Oppenheimer"): [doppelt], ("INBOX", "Paarberatung"): [doppelt],
                             ("Sent", "Oppenheimer"): gesendet})
        k = auftrag.kontext_sammeln(self.SUCHE, postfach, lambda von, bis: [termin("Paarberatung")], HEUTE)
        self.assertEqual([m["uid"] for m in k["mails"]], [7, 5, 8])  # neueste zuerst, 5 nur einmal
        self.assertEqual([m["schluessel"] for m in k["mails"]], ["m1", "m2", "m3"])
        self.assertEqual([m["uid"] for m in k["stil"]], [7, 8])
        self.assertEqual(k["termine"][0]["titel"], "Paarberatung")
        ordner = {a[0] for a in postfach.aufrufe}
        self.assertEqual(ordner, {"INBOX", "Archive", "Sent"})
        self.assertTrue(all(a[4] == date(2025, 10, 27) for a in postfach.aufrufe))

    def test_ohne_eigene_mails_allgemeine_stilvorlage(self):
        allgemein = [mail(9, "Sent")]
        postfach = Postfach({("Sent", None): allgemein})
        k = auftrag.kontext_sammeln(self.SUCHE, postfach, lambda von, bis: [], HEUTE)
        self.assertEqual(k["mails"], [])
        self.assertEqual([m["uid"] for m in k["stil"]], [9])

    def test_kalender_fehler_bricht_nicht_ab(self):
        def kaputt(von, bis):
            raise OSError("weg")
        k = auftrag.kontext_sammeln(self.SUCHE, Postfach(), kaputt, HEUTE)
        self.assertEqual(k["kalender_fehler"], "OSError")
        self.assertIn("nicht lesbar: OSError", auftrag.kontext_als_text(k))

    def test_ohne_kalendertage_kein_kalender(self):
        aufrufe = []
        k = auftrag.kontext_sammeln({**self.SUCHE, "kalender_tage": 0}, Postfach(),
                                    lambda von, bis: aufrufe.append(1), HEUTE)
        self.assertEqual(aufrufe, [])
        self.assertIn("(nicht gesucht)", auftrag.kontext_als_text(k))

    def test_prompt_entwurf_zeigt_schluessel_und_termine(self):
        postfach = Postfach({("INBOX", "Oppenheimer"): [mail(1, von="Oppenheimer <o@praxis.de>")]})
        k = auftrag.kontext_sammeln(self.SUCHE, postfach, lambda von, bis: [termin("Paarberatung")], HEUTE)
        p = auftrag.prompt_entwurf("absagen", k, HEUTE)
        self.assertIn("--- m1\nOrdner: INBOX\nVon: Oppenheimer <o@praxis.de>", p)
        self.assertIn("2026-11-03T16:00:00 bis 2026-11-03T17:00:00: Paarberatung (Praxis)", p)


class TestAntwort(unittest.TestCase):
    KONTEXT = {"mails": [{**mail(1), "schluessel": "m1"}]}

    def test_entwurf_mit_bezug(self):
        art, roh, original = auftrag.antwort_lesen(
            '{"entwurf": {"an": ["o@praxis.de"], "betreff": "Termin", "text": "Hallo", "antwort_auf": "m1"}}',
            self.KONTEXT)
        self.assertEqual(art, "entwurf")
        self.assertNotIn("antwort_auf", roh)
        self.assertEqual(original["uid"], 1)

    def test_neue_mail(self):
        art, roh, original = auftrag.antwort_lesen('{"entwurf": {"an": ["a@b.de"], "antwort_auf": null}}',
                                                   self.KONTEXT)
        self.assertIsNone(original)

    def test_unbekannter_bezug(self):
        with self.assertRaises(AuftragFehler):
            auftrag.antwort_lesen('{"entwurf": {"antwort_auf": "m9"}}', self.KONTEXT)

    def test_rueckfrage(self):
        self.assertEqual(auftrag.antwort_lesen('{"rueckfrage": "Welche Adresse?"}', self.KONTEXT),
                         ("rueckfrage", "Welche Adresse?", None))

    def test_falsche_form(self):
        with self.assertRaises(AuftragFehler):
            auftrag.antwort_lesen('{"text": "x"}', self.KONTEXT)

    def test_prompt_aendern(self):
        p = auftrag.prompt_aendern("kürzer", {"an": ["a@b.de"], "text": "lang"}, "absagen",
                                   {"suche": {"kalender_tage": 0}, "mails": [], "stil": [], "termine": []}, HEUTE)
        self.assertIn("kürzer", p)
        self.assertIn('"text": "lang"', p)
        self.assertIn("Auftrag von Jan:\nabsagen", p)


if __name__ == "__main__":
    unittest.main()
