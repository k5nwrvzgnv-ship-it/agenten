"""Prüft, dass die .venv vollständig ist: agentkit sowie numpy und Pillow für das Verfahren."""

import unittest

import numpy as np
from PIL import Image

from agentkit import auftraege  # noqa: F401 – Einbindung per .pth


class TestUmgebung(unittest.TestCase):
    def test_numpy_und_pillow(self):
        bild = Image.fromarray(np.zeros((4, 6, 3), np.uint8))
        self.assertEqual(bild.size, (6, 4))


if __name__ == "__main__":
    unittest.main()
