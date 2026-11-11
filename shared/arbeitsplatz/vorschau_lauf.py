"""Eine Vorschau machen: python vorschau_lauf.py <quelle> <zielordner> (vorschau.py ruft das mit Speichergrenze auf).

Nutzt renderer.vorschau (LibreOffice für docx/pptx/xlsx, pypdfium2 für die Bilder). Exit 0, wenn Bilder da sind.
"""

import sys
from pathlib import Path

from renderer.vorschau import VorschauFehler, vorschau


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Aufruf: vorschau_lauf.py <quelle> <zielordner>", file=sys.stderr)
        return 2
    try:
        bilder = vorschau(Path(argv[1]), Path(argv[2]))
    except VorschauFehler as f:
        print(f, file=sys.stderr)
        return 1
    print(f"{len(bilder)} Seiten")
    return 0 if bilder else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
