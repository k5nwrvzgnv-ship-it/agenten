import unittest

import vorfilter


def mail(von="Anna <anna@example.de>", **kopf):
    return {"uid": 1, "von": von, "betreff": "Hallo", "kopf": {k.replace("_", "-"): v for k, v in kopf.items()}}


class TestGrund(unittest.TestCase):
    def test_persoenliche_mail_bleibt(self):
        self.assertIsNone(vorfilter.grund_weglassen(mail(), []))

    def test_ohne_kopf_bleibt(self):
        self.assertIsNone(vorfilter.grund_weglassen({"von": "a@b.de"}, []))

    def test_spam(self):
        self.assertEqual(vorfilter.grund_weglassen(mail(x_spam_flag="YES"), []), "spam")
        self.assertIsNone(vorfilter.grund_weglassen(mail(x_spam_flag="NO"), []))

    def test_newsletter(self):
        self.assertEqual(vorfilter.grund_weglassen(mail(list_unsubscribe="<mailto:x@y.de>"), []), "newsletter")
        self.assertIsNone(vorfilter.grund_weglassen(mail(list_unsubscribe="  "), []))

    def test_precedence(self):
        self.assertEqual(vorfilter.grund_weglassen(mail(precedence="Bulk"), []), "massenmail")
        self.assertEqual(vorfilter.grund_weglassen(mail(precedence="list"), []), "massenmail")
        self.assertIsNone(vorfilter.grund_weglassen(mail(precedence="first-class"), []))

    def test_automatische_mail_bleibt(self):
        # Rechnungen und Versandmeldungen sind oft auto-generated und sollen zu Claude
        self.assertIsNone(vorfilter.grund_weglassen(mail(auto_submitted="auto-generated"), []))

    def test_absender(self):
        self.assertEqual(vorfilter.grund_weglassen(mail(), ["anna@example.de"]), "absender")


class TestAbsender(unittest.TestCase):
    def test_adresse_genau(self):
        self.assertTrue(vorfilter.absender_gesperrt("Shop <INFO@shop.de>", ["info@shop.de"]))
        self.assertFalse(vorfilter.absender_gesperrt("Shop <service@shop.de>", ["info@shop.de"]))

    def test_domain_und_subdomain(self):
        self.assertTrue(vorfilter.absender_gesperrt("x@shop.de", ["@shop.de"]))
        self.assertTrue(vorfilter.absender_gesperrt("x@mail.shop.de", ["@shop.de"]))
        self.assertFalse(vorfilter.absender_gesperrt("x@meinshop.de", ["@shop.de"]))

    def test_ohne_adresse(self):
        self.assertFalse(vorfilter.absender_gesperrt("", ["@shop.de"]))


class TestRegeln(unittest.TestCase):
    def test_regelzeilen(self):
        zeilen = [
            "- 27.10.2026: Absender weglassen: Info@Shop.de, @newsletter.example.com (Anlass: Werbung)",
            "- 27.10.2026: Rechnungen immer melden",
            "- 28.10.2026: Absender weglassen: x@y.de (Feedback f-12)",
            "- 28.10.2026: absender weglassen: kein-at, @z.de",
        ]
        self.assertEqual(vorfilter.gesperrte_absender(zeilen),
                         ["info@shop.de", "@newsletter.example.com", "x@y.de", "@z.de"])

    def test_keine_regeln(self):
        self.assertEqual(vorfilter.gesperrte_absender(["- (noch keine)"]), [])


class TestVorfiltern(unittest.TestCase):
    def test_teilt_und_behaelt_reihenfolge(self):
        a, b, c = mail("a@a.de"), mail("b@b.de", precedence="bulk"), mail("c@c.de")
        behalten, weg = vorfilter.vorfiltern([a, b, c], [])
        self.assertEqual(behalten, [a, c])
        self.assertEqual(weg, [(b, "massenmail")])


if __name__ == "__main__":
    unittest.main()
