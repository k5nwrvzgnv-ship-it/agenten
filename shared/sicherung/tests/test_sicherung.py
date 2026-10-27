import subprocess
import unittest
from pathlib import Path

from sicherung import sicherung

STAND = "a" * 40


def attrappe(antworten: dict):
    """git-Attrappe: antworten[befehl] = (returncode, stdout, stderr); befehl = erstes git-Argument nach -C."""
    aufrufe = []

    def laufen(cmd, **kw):
        aufrufe.append(cmd)
        befehl = cmd[3]
        if isinstance(antworten.get(befehl), Exception):
            raise antworten[befehl]
        code, aus, fehler = antworten.get(befehl, (0, "", ""))
        return subprocess.CompletedProcess(cmd, code, aus, fehler)
    laufen.aufrufe = aufrufe
    return laufen


class SichernTest(unittest.TestCase):
    def test_ok(self):
        laufen = attrappe({"rev-parse": (0, STAND + "\n", ""), "ls-remote": (0, f"{STAND}\trefs/heads/main\n", "")})
        self.assertEqual(sicherung.sichern(Path("/r"), laufen), (True, "GitHub auf Stand aaaaaaa"))
        push = [c for c in laufen.aufrufe if c[3] == "push"][0]
        self.assertEqual(push[3:], ["push", "--porcelain", "sicherung", "main:main"])

    def test_push_scheitert(self):
        laufen = attrappe({"rev-parse": (0, STAND, ""), "push": (128, "", "Permission denied (publickey).")})
        ok, text = sicherung.sichern(Path("/r"), laufen)
        self.assertFalse(ok)
        self.assertIn("Permission denied", text)

    def test_stand_weicht_ab(self):
        laufen = attrappe({"rev-parse": (0, STAND, ""), "ls-remote": (0, "b" * 40 + "\trefs/heads/main", "")})
        self.assertEqual(sicherung.sichern(Path("/r"), laufen), (False, "GitHub hat bbbbbbb, der Server aaaaaaa"))

    def test_zeitueberschreitung(self):
        laufen = attrappe({"rev-parse": (0, STAND, ""), "push": subprocess.TimeoutExpired("git", 300)})
        self.assertEqual(sicherung.sichern(Path("/r"), laufen), (False, "Zeitüberschreitung nach 300 s"))

    def test_main_meldet_nur_bei_fehler(self):
        gemeldet = []
        alt = sicherung.sichern
        try:
            sicherung.sichern = lambda: (False, "kaputt")
            self.assertEqual(sicherung.main(lambda agent, text: gemeldet.append((agent, text))), 0)
            sicherung.sichern = lambda: (True, "gut")
            sicherung.main(lambda agent, text: gemeldet.append((agent, text)))
        finally:
            sicherung.sichern = alt
        self.assertEqual(gemeldet, [("sicherung", "Sicherung nach GitHub fehlgeschlagen: kaputt")])


sicherung.logger.disabled = True  # Tests sollen nicht ins echte logs/ schreiben

if __name__ == "__main__":
    unittest.main()
