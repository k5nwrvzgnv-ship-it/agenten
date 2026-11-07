"""Zuordnung im Rohbild (verfahren_neu/zuordnung_roh.py) an künstlichen Texturen."""

import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "verfahren_neu"))
import zuordnung_roh as zr  # noqa: E402


def textur(h, w, seed=1, glatt=13):
    """Zufällige, geglättete Textur (0..255, float32) mit Struktur in beiden Richtungen."""
    rng = np.random.default_rng(seed)
    t = rng.normal(0, 1, (h, w))
    k = np.ones(glatt) / glatt
    for _ in range(2):
        t = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, t)
        t = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 0, t)
    t = (t - t.min()) / (np.ptp(t) + 1e-9) * 200 + 25
    return t.astype(np.float32)


def verkleinern(a, f=4):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3)).astype(np.float32)


def verzerrt(a, H):
    """Bild b mit b(H(p)) = a(p), H bildet a -> b ab."""
    Hi = np.linalg.inv(H)
    Hi = Hi / Hi[2, 2]
    return np.asarray(Image.fromarray(a).transform((a.shape[1], a.shape[0]), Image.PERSPECTIVE,
                                                   tuple(Hi.flatten()[:8]), Image.BILINEAR), np.float32)


class TestBausteine(unittest.TestCase):
    def test_ncc_findet_kachel(self):
        b = textur(120, 140)
        r = zr.ncc(b, b[30:62, 50:82].copy())
        self.assertAlmostEqual(r[0], 30, delta=0.1)
        self.assertAlmostEqual(r[1], 50, delta=0.1)
        self.assertGreater(r[2], 0.99)

    def test_ncc_flache_kachel(self):
        self.assertIsNone(zr.ncc(textur(50, 50), np.full((8, 8), 7.0, np.float32)))

    def test_homographie_und_ransac(self):
        H = np.array([[1.02, 0.01, 5.0], [-0.01, 0.98, -40.0], [1e-5, 0.0, 1.0]])
        rng = np.random.default_rng(3)
        p = rng.uniform(0, 500, (60, 2))
        q = zr.anwenden(H, p)
        q[:15] += rng.uniform(30, 80, (15, 2))  # Ausreißer
        G, m = zr.ransac_homographie(p, q, 1.0)
        self.assertEqual(int(m.sum()), 45)
        np.testing.assert_allclose(zr.anwenden(G, p[15:]), q[15:], atol=1e-6)

    def test_skaliert(self):
        H = np.array([[1.0, 0.0, 3.0], [0.0, 1.0, -2.0], [0.0, 0.0, 1.0]])
        np.testing.assert_allclose(zr.anwenden(zr.skaliert(H, 4.0), [[8.0, 8.0]]), [[20.0, 0.0]])

    def test_ebene_mit_groesster_bewegung(self):
        rng = np.random.default_rng(5)
        pa = rng.uniform(0, 300, (80, 2))
        pb = pa.copy()
        pb[:40, 1] -= 120   # nah: Bauteil
        pb[40:, 1] -= 20    # fern: Hintergrund
        gef = zr.ebenen(pa, pb, schwelle=1.0)
        self.assertEqual(len(gef), 2)
        H, m = zr.ebene_waehlen(gef, pa, pb, (300, 300))
        self.assertTrue(m[:40].all() and not m[40:].any())
        # mit Erwartung aus der Reihe: die passende Ebene, auch wenn sie sich weniger bewegt
        H, m = zr.ebene_waehlen(gef, pa, pb, (300, 300), erwartet=25)
        self.assertTrue(m[40:].all() and not m[:40].any())
        self.assertIsNone(zr.ebene_waehlen(gef, pa, pb, (300, 300), erwartet=60))

    def test_fleck_zaehlt_nicht(self):
        pa = np.c_[np.full(20, 50.0) + np.arange(20) * 0.1, np.arange(20) * 10.0]
        pb = pa - [0, 100]
        gef = zr.ebenen(pa, pb, schwelle=1.0)
        self.assertIsNone(zr.ebene_waehlen(gef, pa, pb, (300, 1000)))


class TestAchse(unittest.TestCase):
    def test_nccfeld_wie_ncc(self):
        b = textur(150, 170, seed=4)
        k = b[40:88, 60:108].copy()
        r = zr.NccFeld(b, 48).suche(k)
        self.assertEqual((r[0], r[1]), (40.0, 60.0))
        self.assertGreater(r[2], 0.99)
        self.assertLess(r[3], r[2])

    def test_urteil(self):
        self.assertEqual(zr.achse_urteil([(1, 300), (-5, 250), (3, 280), None]), "zeilen")
        self.assertEqual(zr.achse_urteil([(300, 1), (250, -5), (280, 3), (2, 260)]), "spalten")
        self.assertIsNone(zr.achse_urteil([(300, 1), (2, 250), (280, 3), (2, 260)]))   # keine Mehrheit
        self.assertIsNone(zr.achse_urteil([(1, 300), (2, 250)]))                       # zu wenig Stimmen
        self.assertIsNone(zr.achse_urteil([(100, 120), (90, 110), (80, 100)]))         # schräg: keine Stimme

    def test_paare(self):
        self.assertEqual(zr.paare_fuer_achse(26), [(0, 1), (5, 6), (10, 11), (14, 15), (19, 20), (24, 25)])
        self.assertEqual(zr.paare_fuer_achse(3), [(0, 1), (1, 2)])
        self.assertEqual(zr.paare_fuer_achse(1), [])

    def test_bewegung_quer_zur_annahme(self):
        a = verkleinern(textur(1000, 1200, seed=9))
        H = np.array([[1.0, 0.0, -70.0], [0.0, 1.0, 3.0], [0.0, 0.0, 1.0]])  # Bewegung längs x
        b = verzerrt(a, H)
        dx, dy = zr.bewegung_beidseitig(a, b)
        self.assertAlmostEqual(dx, -70.0, delta=0.5)
        self.assertAlmostEqual(dy, 3.0, delta=0.5)


class TestZuordnen(unittest.TestCase):
    def test_verschiebung_und_leichte_drehung(self):
        a2 = textur(1100, 1300, seed=7)
        c, s = np.cos(np.radians(1.5)), np.sin(np.radians(1.5))
        H = np.array([[c * 1.03, -s, -10.0], [s, c * 1.03, -330.0], [0.0, 0.0, 1.0]])  # a -> b
        b2 = verzerrt(a2, H)
        r = zr.zuordnen(verkleinern(a2), verkleinern(b2), a2, b2)
        self.assertIsNotNone(r)
        pA, pB, info = r
        self.assertGreaterEqual(len(pA), 20)
        # Ergebnis im vollen Bild (Teiler 2): pB = 2 * H(pA / 2)
        soll = zr.anwenden(H, pA / 2.0) * 2.0
        self.assertLess(float(np.median(np.linalg.norm(pB - soll, axis=1))), 0.5)
        self.assertGreater(info["bewegung_px"], 2 * 250)

    def test_ohne_gemeinsamen_inhalt(self):
        a2 = textur(800, 1000, seed=1)
        b2 = textur(800, 1000, seed=2)
        self.assertIsNone(zr.zuordnen(verkleinern(a2), verkleinern(b2), a2, b2))


if __name__ == "__main__":
    unittest.main()
