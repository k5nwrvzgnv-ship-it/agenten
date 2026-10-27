"""Prüft, dass die .venv vollständig ist: agentkit per .pth eingebunden, imap vorhanden."""

import unittest

from agentkit import imap


class TestUmgebung(unittest.TestCase):
    def test_agentkit_imap(self):
        self.assertTrue(callable(imap.neue_mails))


if __name__ == "__main__":
    unittest.main()
