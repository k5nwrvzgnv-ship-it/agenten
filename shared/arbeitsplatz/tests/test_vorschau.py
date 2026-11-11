"""Eigene Vorschauen (vorschau.py, umbauplan-ux.md Schritt 6) mit nachgestellter Umwandlung."""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import vorschau


def bilder(seiten):
    def machen(quelle, ziel):
        for n in range(1, seiten + 1):
            (ziel / f"{quelle.stem}-seite-{n:02d}.png").write_bytes(b"PNG")
        if quelle.suffix != ".pdf":
            (ziel / f"{quelle.stem}.pdf").write_bytes(b"%PDF")
    return machen


class TestVorschauen(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.quelle = self.tmp / "Blatt.docx"
        self.quelle.write_bytes(b"DOCX")

    def test_anstossen_fertig_und_geaendert(self):
        v = vorschau.Vorschauen(self.tmp / "vorschau", bilder(12))
        self.assertEqual(v.stand("a1", 0, self.quelle), vorschau.FEHLT)
        self.assertEqual(v.seiten("a1", 0, self.quelle), [])
        self.assertTrue(v.anstossen("a1", 0, self.quelle))
        v.warten()
        self.assertEqual(v.stand("a1", 0, self.quelle), vorschau.FERTIG)
        seiten = v.seiten("a1", 0, self.quelle)
        self.assertEqual([p.name for p in seiten][:2], ["Blatt-seite-01.png", "Blatt-seite-02.png"])
        self.assertEqual(seiten[-1].name, "Blatt-seite-12.png")  # nach Zahl, nicht nach Text
        self.assertEqual(v.pdf("a1", 0, self.quelle).name, "Blatt.pdf")
        self.assertFalse(v.anstossen("a1", 0, self.quelle))  # schon da
        # Datei geändert: Vorschau gilt als fehlend
        self.quelle.write_bytes(b"DOCX neu, laenger")
        self.assertEqual(v.stand("a1", 0, self.quelle), vorschau.FEHLT)
        self.assertEqual(v.seiten("a1", 0, self.quelle), [])

    def test_fehler_und_neuer_versuch(self):
        def kaputt(quelle, ziel):
            raise RuntimeError("LibreOffice weg")
        v = vorschau.Vorschauen(self.tmp / "vorschau", kaputt)
        v.anstossen("a1", 0, self.quelle)
        v.warten()
        self.assertEqual(v.stand("a1", 0, self.quelle), vorschau.FEHLER)
        self.assertFalse(v.anstossen("a1", 0, self.quelle))  # nicht gleich noch einmal
        fehler = v.ziel("a1", 0) / "fehler.txt"
        self.assertIn("LibreOffice weg", fehler.read_text())
        alt = time.time() - vorschau.NEUER_VERSUCH_S - 10
        os.utime(fehler, (alt, alt))
        self.assertEqual(v.stand("a1", 0, self.quelle), vorschau.FEHLT)
        v.ausfuehren = bilder(1)
        self.assertTrue(v.anstossen("a1", 0, self.quelle))
        v.warten()
        self.assertEqual(len(v.seiten("a1", 0, self.quelle)), 1)
        self.assertFalse((v.ziel("a1", 0) / "fehler.txt").exists())

    def test_nur_passende_endungen_und_pdf_ohne_kopie(self):
        v = vorschau.Vorschauen(self.tmp / "vorschau", bilder(2))
        md = self.tmp / "Bericht.md"
        md.write_text("# x")
        self.assertFalse(v.anstossen("a1", 0, md))
        pdf = self.tmp / "Blatt.pdf"
        pdf.write_bytes(b"%PDF")
        v.anstossen("a1", 1, pdf)
        v.warten()
        self.assertEqual(len(v.seiten("a1", 1, pdf)), 2)
        self.assertIsNone(v.pdf("a1", 1, pdf))  # die PDF ist das Original

    def test_lauf_ruft_eigenen_prozess_mit_grenze(self):
        aufrufe = []

        class Ergebnis:
            returncode, stdout, stderr = 0, "2 Seiten", ""
        alt = vorschau.subprocess.run
        vorschau.subprocess.run = lambda befehl, **k: aufrufe.append(befehl) or Ergebnis()
        try:
            vorschau._lauf(self.quelle, self.tmp)
        finally:
            vorschau.subprocess.run = alt
        befehl = aufrufe[0]
        self.assertEqual(befehl[:4], ["systemd-run", "--user", "--scope", "--quiet"])
        self.assertIn(f"MemoryMax={vorschau.SPEICHER}", befehl)
        self.assertTrue(befehl[-3].endswith("vorschau_lauf.py"))
