"""Kontrolltext: der Inhalt einer gebauten Datei in Lesereihenfolge, damit Claude ihn prüfen kann.

Liest nur Dateien, die der Renderer selbst gebaut hat, und kennt deren Bausteine: Kopf-Tabelle, Kästen,
Ankreuzfelder (☐), Schreiblinien, Seitenwechsel, Folien mit Icons, Blätter einer Arbeitsmappe (xlsx, mit zipfile und
xml.etree gelesen). Für beliebige fremde Dateien gibt es agentkit.textfassung. Das Aussehen zeigen die
Vorschaubilder (vorschau.py).
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import docx
import pptx
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from pptx.enum.shapes import MSO_SHAPE_TYPE

from renderer import rechnung

FUSSZEILE_CM = 17.9  # ab hier steht auf Folien die Fußzeile
_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_EINGEBAUT = {0: "Standard", 1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00", 9: "0%", 10: "0.00%", 49: "@"}
_PRUEFART = {"whole": "ganze Zahl", "decimal": "Zahl", "textLength": "Textlänge"}
_ZELLE = re.compile(r"^([A-Z]+)(\d+)$")


def kontrolltext(pfad: Path) -> str:
    """Text der docx- oder pptx-Datei in Lesereihenfolge, mit Markierungen in eckigen Klammern."""
    endung = Path(pfad).suffix.lower()
    if endung == ".docx":
        return _docx(Path(pfad))
    if endung == ".pptx":
        return _pptx(Path(pfad))
    if endung == ".xlsx":
        return _xlsx(Path(pfad))
    raise ValueError(f"{Path(pfad).name}: nur .docx, .pptx oder .xlsx")


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


def _xlsx(pfad: Path) -> str:
    with zipfile.ZipFile(pfad) as z:
        def lesen(name: str):
            return ET.fromstring(z.read(name))

        texte = []
        if "xl/sharedStrings.xml" in z.namelist():
            texte = ["".join(t.text or "" for t in si.iter(f"{_M}t")) for si in lesen("xl/sharedStrings.xml")]
        ziele = {r.get("Id"): r.get("Target") for r in lesen("xl/_rels/workbook.xml.rels")}
        stile = _xlsx_stile(lesen("xl/styles.xml"))
        zeilen = []
        for blatt in lesen("xl/workbook.xml").find(f"{_M}sheets"):
            ziel = ziele[blatt.get(_R_ID)].lstrip("/")
            zeilen += _xlsx_blatt(blatt.get("name"), lesen(ziel if ziel.startswith("xl/") else f"xl/{ziel}"),
                                  texte, stile)
    return "\n".join(zeilen)


def _xlsx_stile(stile) -> list[tuple[str, str | None]]:
    """Je Zellstil (Index s): Zahlformat und Hintergrundfarbe."""
    formate = {int(f.get("numFmtId")): f.get("formatCode") for f in stile.iter(f"{_M}numFmt")}
    flaechen = []
    for fill in stile.find(f"{_M}fills"):
        muster = fill.find(f"{_M}patternFill")
        farbe = muster.find(f"{_M}fgColor") if muster is not None else None
        flaechen.append(farbe.get("rgb")[-6:] if farbe is not None and farbe.get("rgb") else None)
    ergebnis = []
    for xf in stile.find(f"{_M}cellXfs"):
        nr = int(xf.get("numFmtId", 0))
        ergebnis.append((formate.get(nr) or _EINGEBAUT.get(nr, f"Nr. {nr}"), flaechen[int(xf.get("fillId", 0))]))
    return ergebnis


def _xlsx_blatt(name: str, ws, texte: list[str], stile: list) -> list[str]:
    zellen = {}  # (zeile, spalte) -> (text, formel, stil)
    for c in ws.iter(f"{_M}c"):
        spalte, zeile = _ZELLE.match(c.get("r")).groups()
        v, f = c.find(f"{_M}v"), c.find(f"{_M}f")
        text = (v.text or "") if v is not None else ""
        if c.get("t") == "s":
            text = texte[int(text)]
        zellen[(int(zeile), spalte)] = (text, f.text if f is not None else None, int(c.get("s", 0)))
    if not zellen:
        return [f"=== Blatt „{name}“ (leer)"]
    pane = ws.find(f".//{_M}pane")
    kopf = int(float(pane.get("ySplit", 1))) if pane is not None else 1
    fixiert_links = int(float(pane.get("xSplit", 0))) if pane is not None else 0
    letzte = max(z for z, _ in zellen)
    erste = kopf + 1
    breiten = {}
    for col in ws.iter(f"{_M}col"):
        for nr in range(int(col.get("min")), int(col.get("max")) + 1):
            breiten[rechnung.spaltenbuchstabe(nr - 1)] = float(col.get("width")) - 0.7109375  # Rand von xlsxwriter
    pruefungen = {}
    for dv in ws.iter(f"{_M}dataValidation"):
        art = _PRUEFART.get(dv.get("type"), dv.get("type"))
        werte = [x.text for x in (dv.find(f"{_M}formula1"), dv.find(f"{_M}formula2")) if x is not None]
        grenzen = " bis ".join(werte) if dv.get("operator", "between") == "between" else \
            f"{dv.get('operator')} {werte[0]}"
        beschreibung = f"Prüfung {art} {grenzen}, Meldung „{dv.get('error', '')}“"
        for bereich in dv.get("sqref").split():
            pruefungen[_ZELLE.match(bereich.split(":")[0]).group(1)] = beschreibung

    einrichtung = ws.find(f"{_M}pageSetup")
    druck = ["A4" if einrichtung is not None and einrichtung.get("paperSize") == "9" else "Papier unbekannt",
             "quer" if einrichtung is not None and einrichtung.get("orientation") == "landscape" else "hoch"]
    einpassen = ws.find(f".//{_M}pageSetUpPr")
    if einpassen is not None and einpassen.get("fitToPage") == "1" and einrichtung is not None:
        hoch, breit = einrichtung.get("fitToHeight", "1"), einrichtung.get("fitToWidth", "1")
        druck.append("auf eine Seite" if (hoch, breit) == ("1", "1") else
                     "auf Seitenbreite" if (hoch, breit) == ("0", "1") else f"auf {breit} x {hoch} Seiten")
    fixiert = f"bis Zeile {kopf}" + (f" und Spalte {rechnung.spaltenbuchstabe(fixiert_links - 1)}"
                                      if fixiert_links else "")
    zeilen = [f"=== Blatt „{name}“ ({' '.join(druck)}, fixiert {fixiert}, "
              f"{letzte - kopf} Zeilen zum Ausfüllen ab Zeile {erste})"]
    for z in range(1, kopf):
        text = " ".join(t for (zz, _), (t, _, _) in sorted(zellen.items()) if zz == z and t)
        if text:
            zeilen.append(f"Zeile {z}: {text}")
    for spalte in sorted({s for z, s in zellen if z == kopf}, key=lambda s: (len(s), s)):
        kopftext = zellen[(kopf, spalte)][0]
        breite = breiten.get(spalte)
        angaben = [f"{spalte} „{kopftext}“" + (f" (Breite {breite:g})" if breite else "") + ":"]
        text, formel, stil = zellen.get((erste, spalte), ("", None, 0))
        zahlformat, flaeche = stile[stil]
        if formel is not None:
            angaben.append(f"Rechnung {rechnung.deutsch('=' + formel)}")
            abweichend = _formel_abweichend(zellen, spalte, erste, letzte, formel)
            angaben.append(f"gleich in allen Zeilen bis {letzte}" if not abweichend
                           else f"ABWEICHEND in Zeile {', '.join(map(str, abweichend[:5]))}")
        elif [zellen.get((z, spalte), ("",))[0] for z in range(erste, letzte + 1)] == \
                [str(n) for n in range(1, letzte - kopf + 1)]:
            angaben.append(f"laufende Nummer 1 bis {letzte - kopf}")
        else:
            angaben.append("Eingabe" + (f", {pruefungen[spalte]}" if spalte in pruefungen else ", ohne Prüfung"))
        if zahlformat != "Standard":
            angaben.append(f"Format {zahlformat}")
        if flaeche:
            angaben.append(f"hinterlegt {flaeche}")
        zeilen.append(angaben[0] + " " + ", ".join(angaben[1:]))
    return zeilen


def _formel_abweichend(zellen: dict, spalte: str, erste: int, letzte: int, formel: str) -> list[int]:
    """Zeilen, deren Formel nicht dieselbe ist wie in der ersten Zeile (nur mit anderer Zeilennummer)."""
    muster = re.compile(rf"(?<=[A-Z]){erste}\b")
    return [z for z in range(erste + 1, letzte + 1)
            if (zellen.get((z, spalte), ("", None, 0))[1] or "") != muster.sub(str(z), formel)]

