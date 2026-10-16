"""Textfassung von PDF, Word, PowerPoint und Excel, damit Claude darin suchen kann.

Mit Seiten-, Folien- bzw. Blattangaben ("--- Seite 3"). Alte Formate (doc, ppt, xls)
nicht, dafür bräuchte es LibreOffice.
Die Bibliotheken (pypdf, python-docx, python-pptx, openpyxl) importiert die Funktion
erst bei Bedarf: Jeder Agent installiert in seiner .venv nur, welche Formate er braucht.
"""

import logging
from pathlib import Path


def als_text(pfad: Path) -> str | None:
    """Text aus pdf, docx, pptx oder xlsx (mit Seiten-, Folien- bzw. Blattangabe). Andere Formate: None."""
    endung = pfad.suffix.lower()
    if endung == ".pdf":
        import pypdf
        logging.getLogger("pypdf").setLevel(logging.ERROR)  # kaputte PDFs sonst sehr gesprächig
        teile, mit_text = [], 0
        for nr, seite in enumerate(pypdf.PdfReader(pfad).pages, 1):
            text = (seite.extract_text() or "").strip()
            mit_text += bool(text)
            teile += [f"--- Seite {nr}", text]
        if not mit_text:
            return "(Kein Text gefunden, vermutlich ein Scan. Das PDF selbst mit Read öffnen.)"
        return "\n".join(teile)
    if endung == ".docx":
        import docx
        d = docx.Document(pfad)
        teile = [a.text for a in d.paragraphs if a.text.strip()]
        for t in d.tables:
            teile += [" | ".join(z.text.strip() for z in reihe.cells) for reihe in t.rows]
        return "\n".join(teile)
    if endung == ".pptx":
        import pptx
        teile = []
        for nr, folie in enumerate(pptx.Presentation(pfad).slides, 1):
            teile.append(f"--- Folie {nr}")
            for form in folie.shapes:
                if form.has_text_frame and form.text_frame.text.strip():
                    teile.append(form.text_frame.text.strip())
                if getattr(form, "has_table", False) and form.has_table:
                    teile += [" | ".join(z.text.strip() for z in reihe.cells) for reihe in form.table.rows]
            if folie.has_notes_slide and folie.notes_slide.notes_text_frame.text.strip():
                teile.append(f"Notizen: {folie.notes_slide.notes_text_frame.text.strip()}")
        return "\n".join(teile)
    if endung == ".xlsx":
        import openpyxl
        teile = []
        for blatt in openpyxl.load_workbook(pfad, read_only=True, data_only=True).worksheets:
            teile.append(f"--- Blatt {blatt.title}")
            for reihe in blatt.iter_rows(values_only=True):
                if any(w is not None for w in reihe):
                    teile.append(" | ".join("" if w is None else str(w) for w in reihe))
        return "\n".join(teile)
    return None
