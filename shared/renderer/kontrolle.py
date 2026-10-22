"""Kontrolltext: der Inhalt einer gebauten Datei in Lesereihenfolge, damit Claude ihn prüfen kann.

Liest nur Dateien, die der Renderer selbst gebaut hat, und kennt deren Bausteine: Kopf-Tabelle, Kästen,
Ankreuzfelder (☐), Schreiblinien, Seitenwechsel, Folien mit Icons. Für beliebige fremde Dateien gibt es
agentkit.textfassung. Das Aussehen zeigen die Vorschaubilder (vorschau.py).
"""

from pathlib import Path

import docx
import pptx
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from pptx.enum.shapes import MSO_SHAPE_TYPE

FUSSZEILE_CM = 17.9  # ab hier steht auf Folien die Fußzeile


def kontrolltext(pfad: Path) -> str:
    """Text der docx- oder pptx-Datei in Lesereihenfolge, mit Markierungen in eckigen Klammern."""
    endung = Path(pfad).suffix.lower()
    if endung == ".docx":
        return _docx(Path(pfad))
    if endung == ".pptx":
        return _pptx(Path(pfad))
    raise ValueError(f"{Path(pfad).name}: nur .docx oder .pptx")


def _docx(pfad: Path) -> str:
    d = docx.Document(pfad)
    zeilen = []
    kopf = "\n".join(p.text for p in d.sections[0].header.paragraphs if p.text.strip())
    if kopf:
        zeilen.append(f"[Kopfzeile der Vorlage] {kopf}")
    linien, abschnitt, zaehler = 0, 0, {}

    def linien_ausgeben():
        nonlocal linien
        if linien:
            zeilen.append(f"[{linien} Schreiblinie{'n' if linien > 1 else ''}]")
            linien = 0

    for el in d.element.body.iterchildren():
        if el.tag == qn("w:tbl"):
            linien_ausgeben()
            zeilen += _tabelle(Table(el, d))
        elif el.tag == qn("w:p"):
            p = Paragraph(el, d)
            ppr = el.pPr
            rahmen = ppr.find(qn("w:pBdr")) if ppr is not None else None
            if rahmen is not None and rahmen.find(qn("w:between")) is not None:
                linien += 1
                continue
            linien_ausgeben()
            text = _absatztext(p)
            umbruch = ppr.find(qn("w:pageBreakBefore")) if ppr is not None else None
            if umbruch is not None and umbruch.get(qn("w:val")) not in ("0", "false"):
                zeilen.append("--- neue Seite")
            if text.strip():
                zeilen.append(_markiert(p, text, rahmen, ppr, zaehler))
            if ppr is not None and ppr.find(qn("w:sectPr")) is not None:  # Abschnittswechsel
                abschnitt += 1
                quer = d.sections[abschnitt].orientation == WD_ORIENT.LANDSCAPE
                zeilen.append(f"--- neue Seite{' (quer)' if quer else ''}")
    linien_ausgeben()
    return "\n".join(zeilen)


def _absatztext(p) -> str:
    teile = []
    for r in p.runs:
        if r._r.find(qn("w:sym")) is not None:
            teile.append("☐")
        teile.append(r.text)
    return "".join(teile)


def _markiert(p, text: str, rahmen, ppr, zaehler: dict) -> str:
    stil = p.style.name if p.style is not None else ""
    if stil.startswith("Heading"):
        return "#" * int(stil.split()[-1]) + " " + text
    if stil == "List Bullet":
        return "• " + text
    if stil == "List Number":
        num = ppr.find(qn("w:numPr")) if ppr is not None else None
        schluessel = num.find(qn("w:numId")).get(qn("w:val")) if num is not None else stil
        zaehler[schluessel] = zaehler.get(schluessel, 0) + 1
        return f"{zaehler[schluessel]}. {text}"
    if rahmen is not None:
        return "[Kasten] " + text
    if ppr is not None and ppr.find(qn("w:shd")) is not None:
        return "[hinterlegt] " + text
    return text


def _tabelle(t) -> list[str]:
    """Zeilen der Tabelle mit | getrennt, verbundene Zellen nur einmal. Leerer 1x1-Kasten: Antwortkasten."""
    if len(t.rows) == 1 and len(t.columns) == 1 and not t.cell(0, 0).text.strip():
        hoehe = t.rows[0].height
        return [f"[leerer Kasten{f', {hoehe.cm:.1f} cm hoch' if hoehe else ''}]"]
    # Elemente festhalten, nicht id() merken: lxml baut Proxy-Objekte neu, Adressen werden wiederverwendet.
    gesehen, zeilen = [], []
    for reihe in t.rows:
        zellen = []
        for zelle in reihe.cells:
            if any(zelle._tc is g for g in gesehen):
                continue
            gesehen.append(zelle._tc)
            zellen.append(zelle.text.strip() or "…")
        if zellen:
            zeilen.append("| " + " | ".join(zellen) + " |")
    return zeilen


def _pptx(pfad: Path) -> str:
    prs = pptx.Presentation(pfad)
    zeilen = []
    for nr, folie in enumerate(prs.slides, 1):
        zeilen.append(f"--- Folie {nr}")
        formen = sorted(folie.shapes, key=lambda s: (round(s.top / 360000, 1), s.left))
        for s in formen:
            if s.top / 360000 >= FUSSZEILE_CM:
                continue
            if s.shape_type == MSO_SHAPE_TYPE.PICTURE:
                zeilen.append(f"[{s.name.replace('Icon ', 'Icon: ')}]")
            elif s.has_text_frame and s.text_frame.text.strip():
                for p in s.text_frame.paragraphs:
                    if not p.text.strip():
                        continue
                    punkt = p._p.pPr is not None and p._p.pPr.find(qn("a:buChar")) is not None
                    zeilen.append(("• " if punkt else "") + p.text)
    return "\n".join(zeilen)
