"""Schreibschutz für Claude (Untersuchung 11/2026, B1): Jede von Git verfolgte Datei eines Agent-Ordners fällt
unter ein Verbotsmuster für Edit und Write, oder sie steht mit Grund in AUSNAHMEN.

Geprüft wird die Liste, nicht claude selbst (das setzt die Muster durch, von Hand getestet 16.10. und 10.11.2026).
Die Muster werden hier gelesen wie in .gitignore: "*.py" trifft den Dateinamen in jeder Tiefe, "tests/**" alles
unter einem Ordner dieses Namens in jeder Tiefe.
"""

import fnmatch
import subprocess
import unittest
from pathlib import Path, PurePosixPath

from agentkit import claude_lauf

WURZEL = Path(__file__).resolve().parents[3]
# Ordner, in denen ein Agent arbeitet (claude läuft dort mit Schreibrecht) oder die als Gerüst dafür dienen.
# Neue Ordner mit agent.py kommen von selbst dazu.
WEITERE_ORDNER = ("kleinanzeigen", "shared/feedback", "shared/vorlagen", "lia/auswertung", "lia/examen")
# Verfolgte Dateien ohne Schutz, jeweils mit Grund. Ein Eintrag mit / am Ende gilt für den ganzen Ordner.
AUSNAHMEN = {
    "uni/reports/": "Rechercheergebnis, wird von keinem Programm gelesen",
    "uni/research_notes/": "Notizen zur Recherche, werden von keinem Programm gelesen",
    "uni/portal-oberflaeche.md": "Plan, wird von keinem Programm gelesen",
    "uni/webapp-plan.md": "Plan, wird von keinem Programm gelesen",
    "fehlstellenscan/docs/": "Dokumentation, der Agent läuft ohne Claude",
    "lia/auswertung/anleitung-export.md": "Anleitung für Menschen, wird von keinem Programm gelesen",
    "lia/auswertung/einwilligung.md": "Text für Menschen, wird von keinem Programm gelesen",
    "lia/examen/impuls.md": "Notiz, wird von keinem Programm gelesen",
    "lia/chat/plan.md": "Plan, wird von keinem Programm gelesen",
    "shared/vorlagen/STATUS-agent.md": "Gerüst für die STATUS.md neuer Agenten, in shared/vorlagen läuft kein Agent",
}


def muster() -> list[str]:
    """Die Muster, die für Edit UND Write verboten sind (aus der echten Verbotsliste, nicht aus GESCHUETZT)."""
    je = {w: {r[len(w) + 4:-1] for r in claude_lauf.VERBOTEN if r.startswith(f"{w}(**/")} for w in ("Edit", "Write")}
    return sorted(je["Edit"] & je["Write"])


def geschuetzt(pfad: str, liste: list[str]) -> bool:
    """pfad relativ zum Agent-Ordner."""
    teile = PurePosixPath(pfad).parts
    for m in liste:
        if m.endswith("/**"):
            if m[:-3] in teile[:-1]:
                return True
        elif fnmatch.fnmatchcase(teile[-1], m):
            return True
    return False


def verfolgt() -> list[str]:
    aus = subprocess.run(["git", "-c", "core.quotepath=off", "ls-files"], cwd=WURZEL, capture_output=True,
                         text=True, check=True)
    return aus.stdout.splitlines()


def agent_ordner(dateien: list[str]) -> list[str]:
    ordner = {str(PurePosixPath(d).parent) for d in dateien if PurePosixPath(d).name == "agent.py"}
    return sorted(o for o in ordner | set(WEITERE_ORDNER) if o != ".")


def ist_ausnahme(datei: str) -> bool:
    return any(datei == a or (a.endswith("/") and datei.startswith(a)) for a in AUSNAHMEN)


class TestMuster(unittest.TestCase):
    def test_lesart(self):
        liste = ["*.py", "tests/**", "STATUS.md"]
        self.assertTrue(geschuetzt("agent.py", liste))
        self.assertTrue(geschuetzt("portal/app.py", liste))
        self.assertTrue(geschuetzt("tests/daten/x.json", liste))
        self.assertTrue(geschuetzt("portal/tests/daten/x.json", liste))
        self.assertTrue(geschuetzt("STATUS.md", liste))
        self.assertFalse(geschuetzt("data/ergebnis.json", liste))
        self.assertFalse(geschuetzt("protokolle/notiz.md", liste))
        self.assertFalse(geschuetzt("tests", liste))  # eine Datei namens tests ist kein Ordner

    def test_luecken_von_b1_geschlossen(self):
        liste = muster()
        for pfad in ("portal/vorlagen/basis.html", "portal/statisch/stil.css", "portal/statisch/htmx-2.0.4.min.js",
                     "portal/systemd/uni-portal-frage.path", "systemd/lia-chat.path", "tests/daten/suchseite.html",
                     "skills/einzelmaterial/SKILL.md", "leitfaden.md", "data/vorlagen/expose_vorlage.md"):
            self.assertTrue(geschuetzt(pfad, liste), pfad)

    def test_ergebnisse_bleiben_schreibbar(self):
        """Claude schreibt Ergebnisse als JSON und Markdown: Das darf kein Muster treffen."""
        liste = muster()
        for pfad in ("data/ergebnis.json", "data/recherche/a1/stand.json", "data/wissen/beispiele-vorschlag.md",
                     "protokolle/2026-11-16.md", "data/entwuerfe/a1.json", "data/lernblatt/a1/blatt.json",
                     "reports/thema.md", "data/nur_lesen/notiz.txt"):
            self.assertFalse(geschuetzt(pfad, liste), pfad)

    def test_env_bleibt_gesperrt(self):
        for w in ("Read", "Grep", "Edit", "Write"):
            self.assertIn(f"{w}(**/.env)", claude_lauf.VERBOTEN)
            self.assertIn(f"{w}(**/.env.*)", claude_lauf.VERBOTEN)


class TestVerfolgteDateien(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dateien = verfolgt()
        cls.ordner = agent_ordner(cls.dateien)
        cls.liste = muster() + [".env", ".env.*"]

    def je_ordner(self):
        for o in self.ordner:
            for d in self.dateien:
                if d.startswith(o + "/"):
                    yield o, d

    def test_ordner_gefunden(self):
        for o in ("uni", "posteingang", "finance", "kleinanzeigen", "lia/unterricht", "lia/theater", "lia/chat"):
            self.assertIn(o, self.ordner)

    def test_jede_datei_geschuetzt_oder_ausnahme(self):
        offen = [d for o, d in self.je_ordner()
                 if not geschuetzt(d[len(o) + 1:], self.liste) and not ist_ausnahme(d)]
        self.assertEqual(offen, [], "Ohne Schreibschutz für Claude. Muster in claude_lauf.GESCHUETZT ergänzen "
                                    "oder mit Grund in AUSNAHMEN eintragen.")

    def test_ausnahmen_sind_noch_noetig(self):
        """Eine Ausnahme, die keine ungeschützte Datei mehr trifft, wird gelöscht (die Liste bleibt ehrlich)."""
        ungeschuetzt = [d for o, d in self.je_ordner() if not geschuetzt(d[len(o) + 1:], self.liste)]
        for a in AUSNAHMEN:
            self.assertTrue(any(d == a or (a.endswith("/") and d.startswith(a)) for d in ungeschuetzt), a)

    def test_ausnahmen_sind_nur_texte(self):
        for _, d in self.je_ordner():
            if ist_ausnahme(d):
                self.assertIn(PurePosixPath(d).suffix, (".md", ".txt"), d)
