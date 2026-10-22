"""Dateien eines Auftrags für Claude lesbar machen, bevor der Lauf beginnt.

Claude liest Text, Markdown und Bilder direkt, aber nicht docx/pptx/xlsx und auf diesem Server auch keine PDFs
(Read braucht dafür poppler, das fehlt). Daher legt Python daneben:
- zu docx, pptx, xlsx: <datei>.txt (agentkit.textfassung),
- zu PDFs: <datei>.txt (Text je Seite, pypdfium2) und <datei>-seiten/ mit einem PNG je Seite (Renderer-Vorschau).
"""

from pathlib import Path

from agentkit.textfassung import als_text

OFFICE = (".docx", ".pptx", ".xlsx")


def vorbereiten(pfad: Path) -> list[Path]:
    """Legt Textfassung und Seitenbilder neben die Datei, gibt die neuen Pfade zurück. Vorhandene bleiben."""
    pfad = Path(pfad)
    endung = pfad.suffix.lower()
    txt = pfad.with_name(pfad.name + ".txt")
    if endung in OFFICE:
        if not txt.exists():
            txt.write_text(als_text(pfad) or "", encoding="utf-8")
        return [txt]
    if endung == ".pdf":
        from renderer.vorschau import als_bilder

        if not txt.exists():
            txt.write_text(pdf_text(pfad), encoding="utf-8")
        ordner = pfad.with_name(pfad.stem + "-seiten")
        bilder = sorted(ordner.glob("*.png")) if ordner.is_dir() else []
        if not bilder:
            ordner.mkdir(exist_ok=True)
            bilder = als_bilder(pfad, ordner)
        return [txt, *bilder]
    return []


def pdf_text(pfad: Path) -> str:
    """Text aller Seiten mit "--- Seite n" davor. Scans haben keinen Text, dann helfen nur die Seitenbilder."""
    import pypdfium2

    dokument = pypdfium2.PdfDocument(pfad)
    try:
        teile, mit_text = [], 0
        for nr in range(len(dokument)):
            text = dokument[nr].get_textpage().get_text_range().replace("\r\n", "\n").strip()
            mit_text += bool(text)
            teile += [f"--- Seite {nr + 1}", text]
    finally:
        dokument.close()
    if not mit_text:
        return "(Kein Text gefunden, vermutlich ein Scan. Die Seitenbilder ansehen.)"
    return "\n".join(teile)
