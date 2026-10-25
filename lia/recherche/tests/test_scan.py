import gzip
import json
import unittest

import scan


def zahlen(*eintraege):
    """eintraege: (Blatt, Seitenzahl, confidence)"""
    return {"pages": [{"leafNum": b, "pageNumber": s, "confidence": c} for b, s, c in eintraege]}


# Wie der Toronto-Scan: S. 1 und 2 ohne Eintrag, ungerade Seiten belegt, gerade nur geschätzt
TORONTO = zahlen((1, "", None), (25, "3", 100), (26, "4", None), (27, "5", 100), (28, "6", None),
                 (29, "7", 100), (790, "3", 100))


class ZuordnungTest(unittest.TestCase):
    def test_anker_und_luecken(self):
        self.assertEqual(scan.zuordnung(TORONTO, 3, 7, -1), {3: 24, 4: 25, 5: 26, 6: 27, 7: 28})

    def test_vor_dem_ersten_anker_nur_von_hand(self):
        with self.assertRaises(scan.ScanFehler) as f:
            scan.zuordnung(TORONTO, 1, 5, -1)
        self.assertIn("Seite 1 ist nicht belegt", str(f.exception))
        z = scan.zuordnung(TORONTO, 1, 5, -1, {"1": 22, "2": 23})
        self.assertEqual((z[1], z[2], z[3]), (22, 23, 24))

    def test_hand_widerspricht_anker(self):
        with self.assertRaises(scan.ScanFehler):
            scan.zuordnung(TORONTO, 3, 5, -1, {"3": 30})

    def test_luecke_mit_tafel_wird_nicht_geraten(self):
        mit_tafel = zahlen((10, "1", 100), (13, "3", 100))  # ein Blatt zu viel zwischen S. 1 und 3
        with self.assertRaises(scan.ScanFehler):
            scan.zuordnung(mit_tafel, 1, 3, 0)

    def test_register_am_bandende_stoert_nicht(self):
        self.assertEqual(scan.zuordnung(TORONTO, 3, 7, -1)[3], 24)  # Blatt 790 "3" (Beilage) passt nicht zum Abstand

    def test_doppelt_ohne_vergleich(self):
        with self.assertRaises(scan.ScanFehler):
            scan.zuordnung(zahlen((5, "1", 100), (9, "1", 100)), 1, 1, 0)


class OcrTest(unittest.TestCase):
    def test_seiten(self):
        text = "aaaBBBcc"
        index = [[0, 3, 0, 0], [3, 6, 0, 0], [6, 8, 0, 0]]
        seiten = scan.ocr_seiten(gzip.compress(text.encode()), gzip.compress(json.dumps(index).encode()), {1: 1, 2: 2})
        self.assertEqual(seiten, {1: "BBB", 2: "cc"})
        with self.assertRaises(scan.ScanFehler):
            scan.ocr_seiten(gzip.compress(b"x"), gzip.compress(b"[[0,1]]"), {1: 5})

    def test_links(self):
        self.assertEqual(scan.link("x", 22), "https://archive.org/details/x/page/n22")
        self.assertEqual(scan.bild_url("x", 22), "https://archive.org/download/x/page/n22.jpg")
        self.assertEqual(sorted(scan.dateien("x")), ["index", "seitenzahlen", "text"])


if __name__ == "__main__":
    unittest.main()
