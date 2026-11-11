"""Prüft, dass die .venv vollständig ist: agentkit sowie numpy und Pillow (auch BMP, das Format von Kodytek et al.)."""

import io
import unittest

import numpy as np
from PIL import Image

from agentkit import auftraege  # noqa: F401 – Einbindung per .pth


class TestUmgebung(unittest.TestCase):
    def test_bmp_hin_und_zurueck(self):
        puffer = io.BytesIO()
        Image.fromarray(np.zeros((4, 6, 3), np.uint8)).save(puffer, format="BMP")
        bild = Image.open(io.BytesIO(puffer.getvalue()))
        self.assertEqual((bild.format, bild.size), ("BMP", (6, 4)))


if __name__ == "__main__":
    unittest.main()
