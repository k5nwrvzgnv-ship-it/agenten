"""Tests für aufnahme/auswahl.py: welche Fotos einer Seite ins Labeln kommen."""

import unittest

from aufnahme import auswahl as au


def serie(schritt: float, feld: float, n: int, **extra) -> list[dict]:
    return [{"a": i * schritt, "b": i * schritt + feld, **extra} for i in range(n)]


def abgedeckt(fotos: list[dict], wahl: list[str], ueberlappung: float) -> bool:
    drin = sorted((f["a"], f["b"]) for f, w in zip(fotos, wahl, strict=True) if w == "drin")
    ende = max(f["b"] for f in fotos if f["a"] is not None)
    if drin[0][0] > min(f["a"] for f in fotos if f["a"] is not None):
        return False
    bis = drin[0][1]
    for a, b in drin[1:]:
        if a > bis - ueberlappung:
            return False
        bis = max(bis, b)
    return bis >= ende


class Auswahl(unittest.TestCase):
    def test_dichte_serie_wird_ausgeduennt(self):
        fotos = serie(50, 280, 30)            # 1,73 m, alle 5 cm ein Foto, Bildfeld 28 cm
        wahl = au.auswaehlen(fotos)
        self.assertTrue(abgedeckt(fotos, wahl, au.UEBERLAPPUNG_MM))
        self.assertLessEqual(wahl.count("drin"), 9)
        self.assertEqual(wahl[0], "drin")
        self.assertEqual(wahl[-1], "drin")
        self.assertNotIn("leer", wahl)

    def test_leere_fotos(self):
        fotos = serie(100, 280, 5) + [{"a": None, "b": None}, {"a": None, "b": None}]
        wahl = au.auswaehlen(fotos)
        self.assertEqual(wahl[-2:], ["leer", "leer"])
        self.assertEqual(au.auswaehlen([{"a": None, "b": None}]), ["leer"])

    def test_luecke_alle_behalten(self):
        fotos = serie(300, 283, 6)             # Plan mit Lücke (B004 Seite 1): nichts ist doppelt
        self.assertEqual(au.auswaehlen(fotos), ["drin"] * 6)

    def test_knappe_ueberlappung_nimmt_naechstes(self):
        fotos = serie(150, 180, 8)              # Nachbarn überlappen nur 30 mm: jedes Foto wird gebraucht
        self.assertEqual(au.auswaehlen(fotos).count("drin"), 8)

    def test_schaerferes_gewinnt(self):
        fotos = serie(20, 280, 15, schaerfe=1.0)
        ohne = au.auswaehlen(fotos)
        zweites = [i for i, w in enumerate(ohne) if w == "drin"][1]
        fotos[zweites - 1]["schaerfe"] = 5.0     # reicht 20 mm weniger weit, ist aber schärfer
        mit = au.auswaehlen(fotos)
        self.assertEqual(mit[zweites - 1], "drin")
        self.assertEqual(mit[zweites], "doppelt")
        self.assertTrue(abgedeckt(fotos, mit, au.UEBERLAPPUNG_MM))

    def test_unsichere_bleiben(self):
        fotos = serie(40, 280, 20)
        for i in au.unsichere_fotos(len(fotos), [7]):
            fotos[i]["unsicher"] = True
        wahl = au.auswaehlen(fotos)
        self.assertEqual((wahl[7], wahl[8]), ("drin", "drin"))
        self.assertEqual(au.unsichere_fotos(3, [2]), {2})

    def test_ganz(self):
        fotos = serie(40, 280, 6) + [{"a": None, "b": None}]
        self.assertEqual(au.auswaehlen(fotos, ganz=True), ["drin"] * 6 + ["leer"])

    def test_rueckwaerts_gezaehlt(self):
        fotos = [{"a": 1500 - f["b"], "b": 1500 - f["a"]} for f in serie(50, 280, 25)]
        wahl = au.auswaehlen(fotos)
        self.assertTrue(abgedeckt(fotos, wahl, au.UEBERLAPPUNG_MM))
        self.assertLess(wahl.count("drin"), 12)


if __name__ == "__main__":
    unittest.main()
