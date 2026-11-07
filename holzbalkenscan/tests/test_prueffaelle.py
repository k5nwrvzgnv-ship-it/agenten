import unittest

import numpy as np

import prueffaelle as pf

# Ebene -> Bild: 2 Px/mm, Bauteilkante v = 0 bei x = 20 Px, u längs = y / 2
H = np.array([[0.0, 2.0, 20.0], [2.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
HI = np.linalg.inv(H)


def balkenbild(h=40, w=100, x0=20, x1=60):
    """Hintergrund mit Streifenmuster, Holz (x0..x1) gleichmäßig 100."""
    b = np.zeros((h, w, 3), np.uint8)
    b[:] = (np.arange(w) % 7 * 10 + 150).astype(np.uint8)[None, :, None]
    b[:, x0:x1] = 100
    return b


class TestRechnung(unittest.TestCase):
    def test_abbilden_umkehrbar(self):
        x, y = np.array([3.0, 50.0]), np.array([7.0, 11.0])
        u, v = pf.abbilden(HI, x, y)
        np.testing.assert_allclose(v, (x - 20) / 2)
        xx, yy = pf.abbilden(H, u, v)
        np.testing.assert_allclose([xx, yy], [x, y])

    def test_spiegeln(self):
        np.testing.assert_allclose(pf.spiegeln(np.array([-1.0, 0.0, 4.0, 5.0, 6.0]), 5), [1, 0, 4, 3, 2])

    def test_abtasten_ganzzahlig_und_halb(self):
        b = np.arange(12, dtype=np.uint8).reshape(3, 4, 1)
        r = pf.abtasten(b, np.array([1.0, 1.5]), np.array([2.0, 0.0]))
        np.testing.assert_allclose(r[:, 0], [9.0, 1.5])

    def test_schmal_ersetzt_nur_den_streifen(self):
        b = balkenbild()
        aus = pf.schmal(b, H, HI, 10.0)  # v < 10 mm = x < 40 Px
        np.testing.assert_array_equal(aus[:, 40:], b[:, 40:])
        # Quelle für x ist x - 20 Px: das Holz bei 20..39 zeigt jetzt den Hintergrund von 0..19
        np.testing.assert_array_equal(aus[:, 20:40], b[:, 0:20])
        self.assertEqual(int((aus[0, 20:, 0] == 100).sum()), 20)  # links davon: gespiegelter Rand

    def test_flau_zieht_den_hintergrund_ans_holz(self):
        b = balkenbild(h=200, w=240, x0=20, x1=140)  # Kante v = 60 mm bei x = 140
        aus, vor, nach = pf.flau(b, HI, 60.0, 5.0)
        self.assertGreater(vor, 50)
        self.assertAlmostEqual(nach, 5.0, delta=1.0)
        np.testing.assert_array_equal(aus[:, :140], b[:, :140])
        # Textur bleibt: Unterschiede im Hintergrund unverändert
        np.testing.assert_array_equal(np.diff(aus[0, 150:].astype(int), axis=0),
                                      np.diff(b[0, 150:].astype(int), axis=0))

    def test_kantenmittel_ausserhalb(self):
        with self.assertRaises(ValueError):
            pf.kantenmittel(balkenbild(), HI, 500.0)

    def test_bauteil_fuer(self):
        d = {"bauteil": "Testbalken", "flaeche_hoehe_mm": 230.0, "lamellen": 7, "laenge_mm": 6485.0}
        s = pf.bauteil_fuer(d, "pf-schmal")
        self.assertEqual(s["flaeche_hoehe_mm"], 115.0)
        self.assertEqual(s["flaeche_hoehe_mm_gemessen"], [115.0] * 3)
        self.assertIsNone(s["lamellen"])
        self.assertEqual(s["laenge_mm"], 6485.0)
        self.assertEqual(pf.bauteil_fuer(d, "pf-flau")["flaeche_hoehe_mm"], 230.0)
        self.assertEqual(d["lamellen"], 7)


if __name__ == "__main__":
    unittest.main()
