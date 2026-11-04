import json
import stat
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import agent
import schriftverkehr


def mail(uid, betreff, datum="2026-10-26T09:44:02+00:00", message_id=None, **mehr):
    return {"uid": uid, "von": "x", "an": ["y"], "betreff": betreff, "datum": datum, "message_id": message_id or f"<{uid}@x>",
            "wortlaut": "Wortlaut", "text": "kurz", "anhaenge": ["a.pdf"], **mehr}


class Suche:
    def __init__(self, treffer):
        self.treffer, self.aufrufe = treffer, []

    def __call__(self, ordner, **kriterien):
        self.aufrufe.append((ordner, kriterien))
        return self.treffer.get(ordner, [])


JETZT = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
KONTAKT = {"name": "Böhme", "adresse": "b@hnee.de"}


class Auszug(unittest.TestCase):
    def test_sucht_eingang_und_gesendet_ab_datum(self):
        suche = Suche({})
        schriftverkehr.auszug_bauen(date(2026, 10, 1), [KONTAKT], suche, ("INBOX", "Archive"), "Gesendet", JETZT)
        self.assertEqual(suche.aufrufe, [
            ("INBOX", {"seit": date(2026, 10, 1), "max_mails": 50, "von": "b@hnee.de"}),
            ("Archive", {"seit": date(2026, 10, 1), "max_mails": 50, "von": "b@hnee.de"}),
            ("Gesendet", {"seit": date(2026, 10, 1), "max_mails": 50, "an": "b@hnee.de"})])

    def test_felder_richtung_und_doppelte(self):
        suche = Suche({"INBOX": [mail(1, "Antwort", message_id="<m>")], "Archive": [mail(9, "Antwort", message_id="<m>")],
                       "Gesendet": [mail(2, "Anfrage")]})
        a = schriftverkehr.auszug_bauen(date(2026, 10, 1), [KONTAKT], suche, ("INBOX", "Archive"), "Gesendet", JETZT)
        self.assertEqual([(m["betreff"], m["richtung"]) for m in a["mails"]], [("Antwort", "von"), ("Anfrage", "an")])
        self.assertEqual(a["mails"][0]["text"], "Wortlaut")
        self.assertEqual(a["mails"][0]["datum"], "2026-10-26T10:44")
        self.assertEqual(a["stand"], "2026-11-04T13:00")
        self.assertNotIn("message_id", a["mails"][0])
        self.assertFalse(a["gekappt"])

    def test_alte_mail_ohne_wortlaut_und_kaputtes_datum(self):
        m = mail(1, "x", datum="kein datum")
        del m["wortlaut"]
        a = schriftverkehr.auszug_bauen(date(2026, 10, 1), [KONTAKT], Suche({"INBOX": [m]}), ("INBOX",), "G", JETZT)
        self.assertEqual((a["mails"][0]["text"], a["mails"][0]["datum"]), ("kurz", ""))

    def test_grenze_wird_vermerkt(self):
        treffer = [mail(i, "x") for i in range(schriftverkehr.MAX_JE_SUCHE)]
        a = schriftverkehr.auszug_bauen(date(2026, 10, 1), [KONTAKT], Suche({"INBOX": treffer}), ("INBOX",), "G", JETZT)
        self.assertTrue(a["gekappt"])


class Dateien(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.ordner = Path(tmp.name) / "data" / "projekte" / "fehlstellen"
        self.ordner.mkdir(parents=True)
        self.kontakte = self.ordner / "kontakte.json"
        self.kontakte.write_text(json.dumps({"seit": "2026-10-01", "kontakte": [{"name": "B", "adresse": "B@hnee.de "}]}))
        self.hier = Path(tmp.name)

    def test_adresse_wird_klein_und_muss_ganz_sein(self):
        self.assertEqual(schriftverkehr.kontakte_lesen(self.kontakte)[1], [{"name": "B", "adresse": "b@hnee.de"}])
        for falsch in ("hnee", "@hnee.de", "a@b", "a b@c.de", ""):
            self.kontakte.write_text(json.dumps({"seit": "2026-10-01", "kontakte": [{"adresse": falsch}]}))
            with self.assertRaises(schriftverkehr.KontakteFehler, msg=falsch):
                schriftverkehr.kontakte_lesen(self.kontakte)

    def test_seit_ist_pflicht(self):
        self.kontakte.write_text(json.dumps({"kontakte": []}))
        with self.assertRaises(schriftverkehr.KontakteFehler):
            schriftverkehr.kontakte_lesen(self.kontakte)

    def test_auszug_nur_fuer_den_besitzer(self):
        schriftverkehr.abgleichen(self.kontakte, Suche({}), ("INBOX",), "G", JETZT)
        self.assertEqual(stat.S_IMODE((self.ordner / "schriftverkehr.json").stat().st_mode), 0o600)

    def test_fehler_laesst_alten_auszug_stehen(self):
        (self.ordner / "schriftverkehr.json").write_text("ALT")

        def kaputt(*a, **k):
            raise OSError("Postfach weg")

        with self.assertRaises(OSError):
            schriftverkehr.abgleichen(self.kontakte, kaputt, ("INBOX",), "G", JETZT)
        self.assertEqual((self.ordner / "schriftverkehr.json").read_text(), "ALT")

    def test_schritt_im_agenten(self):
        suche = Suche({"INBOX": [mail(1, "Antwort")]})
        with mock.patch.object(agent, "HIER", self.hier), mock.patch.object(agent, "postfach_suchen", suche):
            agent.projekt_post_abgleichen()
        self.assertEqual(json.loads((self.ordner / "schriftverkehr.json").read_text())["mails"][0]["betreff"], "Antwort")


if __name__ == "__main__":
    unittest.main()
