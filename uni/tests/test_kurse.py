import unittest

import kurse


class TestKurse(unittest.TestCase):
    def test_sicherer_name(self):
        self.assertEqual(kurse.sicherer_name("../../etc/passwd"), "_.._etc_passwd")
        self.assertEqual(kurse.sicherer_name(".."), "_")
        self.assertEqual(kurse.sicherer_name("Folie 3: Holz/Beton?.pdf"), "Folie 3_ Holz_Beton_.pdf")
        self.assertEqual(kurse.sicherer_name(""), "_")

    def test_html_zu_text(self):
        self.assertEqual(kurse.html_zu_text("<p>Klausur am <b>12.02.</b></p><p>Raum&nbsp;5</p>"),
                         "Klausur am 12.02.\nRaum\xa05")
        self.assertEqual(kurse.html_zu_text(None), "")


if __name__ == "__main__":
    unittest.main()
