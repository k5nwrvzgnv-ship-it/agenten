"""Calc rechnet dasselbe wie rechnung.py: Werte in die gebaute xlsx eintragen, Calc neu rechnen lassen (CSV), mit
Python vergleichen. Braucht LibreOffice mit Calc (libreoffice-calc-nogui), sonst übersprungen."""

import csv
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from renderer import arbeitsmappe, rechnung, vorschau
from renderer.pruefung import lesen

FORMELN = {
    "s": "summe(a:c)", "m": "mittelwert(a:c)", "lo": "min(a, c)", "hi": "max(a:c)", "n": "anzahl(a:c)",
    "r": "runden(m, 0)", "q": "a / b", "w": "wenn_leer(a * 2, c - 1)", "v": "-(a + b) * c",
    "k": "wenn_leer(q, 0)", "g": "2/3 * m + 1/3 * c", "z": "summe(q, a)",
}
EINGABEN = [  # a, b, c (None: leer)
    (1, 2, 3), (None, None, None), (2.5, 0, None), (None, 5, -1), (0, 0, 0), (1.5, None, 2.5),
    (2.5, None, None), (-2.5, None, None), (14, 15, 13),
]
LEER_AUSGABE = ""


def beschreibung() -> dict:
    spalten = [{"id": i, "kopf": i, "art": "zahl"} for i in "abc"]
    spalten += [{"id": sid, "kopf": sid, "art": "rechnung", "formel": f, "nachkommastellen": 4}
                for sid, f in FORMELN.items()]
    return {"art": "arbeitsmappe", "titel": "Vergleich",
            "blaetter": [{"name": "Vergleich", "zeilen": len(EINGABEN), "spalten": spalten}]}


def eintragen(quelle: Path, ziel: Path, werte: dict[str, float]):
    """Werte in leere Zellen der ersten Tabelle schreiben (wie Lia es in Excel täte)."""
    with zipfile.ZipFile(quelle) as z:
        teile = {n: z.read(n) for n in z.namelist()}
    xml = teile["xl/worksheets/sheet1.xml"].decode()
    for adresse, wert in werte.items():
        xml, anzahl = re.subn(rf'<c r="{adresse}" s="(\d+)"/>', rf'<c r="{adresse}" s="\1"><v>{wert}</v></c>', xml)
        assert anzahl == 1, adresse
    teile["xl/worksheets/sheet1.xml"] = xml.encode()
    with zipfile.ZipFile(ziel, "w") as z:
        for name, inhalt in teile.items():
            z.writestr(name, inhalt)


@unittest.skipUnless(shutil.which(vorschau.SOFFICE), "LibreOffice nicht installiert")
class TestCalcRechnetGleich(unittest.TestCase):
    def test_calc_gleich_python(self):
        tmp = Path(tempfile.mkdtemp())
        b = lesen(beschreibung())
        arbeitsmappe.bauen(b, tmp / "leer.xlsx")
        werte = {}
        for z, zeile in enumerate(EINGABEN, start=2):  # Zeile 1 ist der Kopf
            for spalte, wert in zip("ABC", zeile, strict=True):
                if wert is not None:
                    werte[f"{spalte}{z}"] = wert
        eintragen(tmp / "leer.xlsx", tmp / "probe.xlsx", werte)
        with open(vorschau.umwandeln(tmp / "probe.xlsx", tmp, "csv"), encoding="utf-8") as f:
            calc = list(csv.reader(f))

        spalten = b["blaetter"][0]["spalten"]
        ids = [s["id"] for s in spalten]
        formeln = {s["id"]: s["baum"] for s in spalten if s["art"] == "rechnung"}
        self.assertEqual(calc[0], ids)
        for nr, zeile in enumerate(EINGABEN, start=1):
            python = rechnung.zeile_ausrechnen(formeln, ids, dict(zip("abc", zeile, strict=True)))
            for sid in formeln:
                aus_calc = calc[nr][ids.index(sid)]
                with self.subTest(zeile=zeile, spalte=sid, formel=FORMELN[sid], calc=aus_calc):
                    erwartet = python[sid]
                    if erwartet is rechnung.LEER:
                        self.assertEqual(aus_calc, LEER_AUSGABE)
                    elif erwartet == rechnung.FEHLER:
                        self.assertEqual(aus_calc, "#DIV/0!")
                    else:
                        self.assertAlmostEqual(float(aus_calc), erwartet, delta=0.00006)


if __name__ == "__main__":
    unittest.main()
