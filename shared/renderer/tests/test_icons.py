"""Icons: jedes Icon der Liste gibt es in der Schrift, Farbe und Größe stimmen, Fehler sind klar."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageFont

from renderer import icons


def maske(schrift: Path, zeichen: int) -> bytes:
    font = ImageFont.truetype(str(schrift), size=48, layout_engine=ImageFont.Layout.BASIC)
    return bytes(font.getmask(chr(zeichen)))


class TestIcons(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_jedes_icon_gibt_es_in_der_schrift(self):
        """Ein fehlendes Zeichen sähe aus wie das Ersatzzeichen der Schrift (oder wäre leer)."""
        for schrift, stelle in ((icons.SCHRIFT_UMRISS, 1), (icons.SCHRIFT_GEFUELLT, 2)):
            ersatz = maske(schrift, 0x10FFFD)
            for name, eintrag in icons.ICONS.items():
                if eintrag[stelle] is None:
                    continue
                m = maske(schrift, eintrag[stelle])
                self.assertTrue(any(m), f"{name}: leer")
                self.assertNotEqual(m, ersatz, f"{name}: nicht in {schrift.name}")

    def test_namen(self):
        self.assertEqual(len(icons.NAMEN), 55)
        for name in icons.NAMEN:
            self.assertRegex(name, r"^[a-z_]+$")  # ohne Umlaute, wie Bezeichner

    def test_farbe_groesse_und_transparenz(self):
        ziel = icons.zeichnen("wecker", self.tmp / "w.png", farbe="#c00000", px=200)
        with Image.open(ziel) as bild:
            self.assertEqual((bild.mode, bild.size), ("RGBA", (200, 200)))
            self.assertEqual(bild.getpixel((0, 0))[3], 0)  # Ecke durchsichtig
            deckend = {p[:3] for p in bild.get_flattened_data() if p[3] == 255}
            self.assertEqual(deckend, {(0xC0, 0, 0)})

    def test_mittig(self):
        with Image.open(icons.zeichnen("smiley", self.tmp / "s.png", px=300)) as bild:
            links, oben, rechts, unten = bild.getbbox()
        self.assertLessEqual(abs((links + rechts) / 2 - 150), 2)
        self.assertLessEqual(abs((oben + unten) / 2 - 150), 2)

    def test_gefuellt_und_ersatz(self):
        umriss = icons.zeichnen("schale", self.tmp / "u.png")
        voll = icons.zeichnen("schale", self.tmp / "v.png", gefuellt=True)
        with Image.open(umriss) as a, Image.open(voll) as b:
            self.assertGreater(sum(p[3] for p in b.get_flattened_data()), sum(p[3] for p in a.get_flattened_data()))
        # Zeigefinger gibt es nur als Umriss: gefuellt=True liefert dann den Umriss
        icons.zeichnen("zeigefinger", self.tmp / "z1.png")
        icons.zeichnen("zeigefinger", self.tmp / "z2.png", gefuellt=True)
        self.assertEqual((self.tmp / "z1.png").read_bytes(), (self.tmp / "z2.png").read_bytes())

    def test_fehler(self):
        with self.assertRaisesRegex(ValueError, "Icon 'hand' gibt es nicht, erlaubt sind: achtung"):
            icons.zeichnen("hand", self.tmp / "x.png")
        with self.assertRaisesRegex(ValueError, "keine Farbe"):
            icons.zeichnen("haus", self.tmp / "x.png", farbe="rot")


if __name__ == "__main__":
    unittest.main()
