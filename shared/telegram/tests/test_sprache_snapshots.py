"""Alle Snapshots (tests/snapshots/*.txt) gegen die Sprachregel prüfen (agentkit.sprache, docs/sprache/sprachregel.md).

lia_* geht an Lia, jan_* an Jan. Geprüft wird jede Nachricht (Jargon, Lesbarkeit, Satzlänge, Länge) und jede
Knopf-Beschriftung (nur Jargon).

Bis alle Texte umgeschrieben sind, stehen die heutigen Befunde in sprache_altlasten.json. Ein neuer Befund macht den
Test rot. Ein behobener auch, damit die Liste nur kürzer wird: SPRACHE_ALTLASTEN_KUERZEN=1 streicht behobene
Einträge (fügt nie etwas hinzu). Ziel (Nachweis): die Liste ist leer.
"""

import json
import os
import re
import unittest
from pathlib import Path

from agentkit import sprache

ORDNER = Path(__file__).parent / "snapshots"
ALTLASTEN = Path(__file__).parent / "sprache_altlasten.json"
AUSNAHMEN = {
    "jan_entwurf_mail": ("laenge",),  # freigegeben wird genau der angezeigte Text, er wird nicht gekürzt
}


def zerlegen(inhalt: str) -> tuple[list[str], list[str]]:
    """Snapshot -> (Nachrichten, Knopf-Beschriftungen)."""
    text, _, knoepfe = inhalt.partition("--- Knöpfe ---\n")
    nachrichten = [n for n in text.rstrip("\n").split("\n--- nächste Nachricht ---\n") if n.strip()]
    return nachrichten, re.findall(r"\[([^\]]+)\] ", knoepfe)


def schluessel(befund: str) -> str:
    """Befund ohne Messwert (sonst ändert jede Umformulierung die Altlast): 'lesbarkeit', 'glossar: Kontingent'."""
    art = befund.split(":", 1)[0]
    return art if art in ("lesbarkeit", "satz", "laenge") else sprache.log_text([befund])


def befunde(name: str) -> list[str]:
    fuer = sprache.LIA if name.startswith("lia_") else sprache.JAN
    nachrichten, knoepfe = zerlegen((ORDNER / f"{name}.txt").read_text(encoding="utf-8"))
    gefunden = {schluessel(b) for n in nachrichten for b in sprache.pruefen(n, fuer, AUSNAHMEN.get(name, ()))}
    gefunden |= {"knopf " + sprache.log_text([b]) for k in knoepfe for b in sprache.pruefen(k, fuer, ("laenge",))}
    return sorted(gefunden)


class SpracheSnapshotTest(unittest.TestCase):
    def test_jeder_snapshot_hat_empfaenger(self):
        for datei in ORDNER.glob("*.txt"):
            self.assertRegex(datei.stem, r"^(lia|jan)_", "Snapshot-Name beginnt mit lia_ oder jan_")

    def test_keine_neuen_befunde(self):
        alt = json.loads(ALTLASTEN.read_text(encoding="utf-8")) if ALTLASTEN.exists() else {}
        ist = {d.stem: befunde(d.stem) for d in sorted(ORDNER.glob("*.txt"))}
        neu = {n: [b for b in bs if b not in alt.get(n, [])] for n, bs in ist.items()}
        self.assertEqual({n: b for n, b in neu.items() if b}, {}, "neue Verstöße gegen die Sprachregel")
        behoben = {n: [b for b in bs if b not in ist.get(n, [])] for n, bs in alt.items()}
        behoben = {n: b for n, b in behoben.items() if b}
        if behoben and os.environ.get("SPRACHE_ALTLASTEN_KUERZEN"):
            rest = {n: [b for b in bs if b in ist.get(n, [])] for n, bs in alt.items()}
            ALTLASTEN.write_text(json.dumps({n: b for n, b in rest.items() if b}, ensure_ascii=False, indent=1) + "\n",
                                 encoding="utf-8")
            return
        self.assertEqual(behoben, {}, "behoben: mit SPRACHE_ALTLASTEN_KUERZEN=1 aus der Altlasten-Liste streichen")


if __name__ == "__main__":
    unittest.main()
