"""Gemeinsames für die Tests: Beispielangaben (erfunden) und das echte Paket, falls geladen."""

import tomllib
import unittest
from pathlib import Path

from angaben import Angaben

ORDNER = Path(__file__).resolve().parent.parent
PAKET = ORDNER / "data" / "quellen" / "formularpaket-beamte.pdf"


def beispiel(**aenderungen) -> Angaben:
    """Angaben aus angaben.beispiel.toml; aenderungen: {"familie": {"stand": "verheiratet"}} usw."""
    daten = tomllib.loads((ORDNER / "angaben.beispiel.toml").read_text(encoding="utf-8"))
    for teil, werte in aenderungen.items():
        if werte is None:
            daten.pop(teil, None)
        else:
            daten.setdefault(teil, {}).update(werte)
    return Angaben(daten)


def braucht_paket(test):
    """Tests mit dem echten Paket von berlin.de (data/ ist nicht im Repo): ohne Paket übersprungen."""
    return unittest.skipUnless(PAKET.exists(), "Paket nicht geladen (agent.py laden)")(test)
