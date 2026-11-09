"""Agent verwaltung (Lia): Formulare für die Verbeamtung in Berlin vorausfüllen.

Ablauf (von Hand gestartet, noch kein Dienst):
    .venv/bin/python agent.py laden     Gesamtpaket von berlin.de nach data/quellen/ (Prüfsumme muss passen)
    .venv/bin/python agent.py fuellen   data/angaben.toml -> data/ausgang/verbeamtung-formulare.pdf
                                        und data/ausgang/verbeamtung-checkliste.txt

Python füllt, Claude sieht Lias Daten nicht. Ins Log kommen nur Formularschlüssel und Zahlen, keine Angaben.
"""

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

from agentkit import abruf, log

import angaben
import checkliste
import druck
import formulare

ORDNER = Path(__file__).resolve().parent
DATEN = ORDNER / "data"
PAKET = DATEN / "quellen" / "formularpaket-beamte.pdf"
ANGABEN = DATEN / "angaben.toml"
AUSGANG = DATEN / "ausgang"
DRUCK = "verbeamtung-formulare.pdf"
LISTE = "verbeamtung-checkliste.txt"
ALLOWLIST = ["berlin.de"]
STICHTAG = date(2026, 11, 10)  # Termin; maßgeblich für "47. Lebensjahr noch nicht vollendet"

logger = log.hole_logger(ORDNER, "verwaltung")
logging.getLogger("pypdf").setLevel(logging.ERROR)  # Schriftwarnungen des Pakets, harmlos


def _privat_schreiben(pfad: Path, inhalt: bytes) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(inhalt)
    tmp.replace(pfad)


def laden() -> None:
    erg = abruf.laden(formulare.PAKET_URL, ALLOWLIST, DATEN / "cache")
    PAKET.parent.mkdir(parents=True, exist_ok=True)
    PAKET.write_bytes(erg.inhalt)
    druck.paket_oeffnen(PAKET, formulare.PAKET_SHA256, formulare.SEITEN_PAKET)  # wirft, wenn geändert
    logger.info("Paket geladen (%d Bytes, aus Cache: %s)", len(erg.inhalt), erg.aus_cache)


def fuellen(stichtag: date) -> tuple[Path, Path]:
    a = angaben.laden(ANGABEN)
    paket = druck.paket_oeffnen(PAKET, formulare.PAKET_SHA256, formulare.SEITEN_PAKET)
    auswahl = formulare.auswahl(a)
    teile, seiten, seite = [], {}, 1
    for f, gilt, _ in auswahl:
        if gilt is False:
            continue
        teile.append(druck.formular_bauen(paket, f.seiten, f.felder(a, stichtag), f.schluessel))
        seiten[f.schluessel] = (seite, seite + len(f.seiten) - 1)
        seite += len(f.seiten)
    pdf_pfad, liste_pfad = AUSGANG / DRUCK, AUSGANG / LISTE
    _privat_schreiben(pdf_pfad, druck.zusammenfuegen(teile))
    _privat_schreiben(liste_pfad, checkliste.erstellen(a, auswahl, seiten, DRUCK).encode("utf-8"))
    logger.info("Gefüllt: %d Formulare, %d Seiten, %d Angaben fehlen (%s)", len(teile), seite - 1,
                len(a.fehlend), ", ".join(seiten))
    return pdf_pfad, liste_pfad


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("schritt", choices=["laden", "fuellen"])
    p.add_argument("--stichtag", default=STICHTAG.strftime("%d.%m.%Y"), help="TT.MM.JJJJ")
    args = p.parse_args(argv)
    try:
        if args.schritt == "laden":
            laden()
        else:
            pdf, liste = fuellen(datetime.strptime(args.stichtag, "%d.%m.%Y").date())
            print(f"{pdf}\n{liste}")
    except (abruf.AbrufFehler, angaben.AngabenFehler, druck.DruckFehler, ValueError, OSError) as e:
        logger.error("%s fehlgeschlagen: %s", args.schritt, e)
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
