"""Arbeitsmappe (xlsx) aus der geprüften Beschreibung bauen: leere Tabellen zum Ausfüllen, in denen Excel rechnet.

Je Blatt: Titel, Hinweise, Kopfzeile, dann `zeilen` leere Zeilen. Eingabefelder mit Datenüberprüfung (Excel weist
falsche Werte mit deutscher Meldung ab), Rechenfelder grau mit Formeln aus rechnung.py, kein Blattschutz (Jan
29.10.). Kopf fixiert, Druck A4 quer auf Seitenbreite, Titel bis Kopfzeile auf jeder Seite, unten Seitenzahl.
Texte von Claude werden nie als Formel gelesen (strings_to_formulas aus), Formeln entstehen nur aus dem Baum.
"""

import math
from pathlib import Path

import xlsxwriter

from renderer import design, rechnung
from renderer.pruefung import MAX_ZAHL

STANDARD_BREITE = {"nummer": 5, "text": 25, "zahl": 9, "rechnung": 12}  # Zeichen
TITEL_PT = 14
HINWEIS_PT = 10
ZEILE_PT = 15  # Höhe einer Textzeile bei 11 pt


def bauen(beschreibung: dict, ziel: Path, profil: dict | None = None, vorlage: Path | None = None) -> Path:
    if vorlage is not None:
        raise ValueError("Arbeitsmappe: Vorlagen gibt es für xlsx nicht, vorlage=None übergeben")
    p = design.profil_lesen(profil)
    mappe = xlsxwriter.Workbook(str(ziel), {
        "strings_to_formulas": False, "strings_to_urls": False, "strings_to_numbers": False,
        "default_format_properties": {"font_name": p["schrift"], "font_size": p["schriftgroesse_pt"]},
    })
    mappe.set_properties({"title": beschreibung["titel"], "author": "", "company": ""})
    try:
        formate = _formate(mappe, p)
        for blatt in beschreibung["blaetter"]:
            _blatt(mappe.add_worksheet(blatt["name"]), blatt, formate)
    finally:
        mappe.close()
    return ziel


def zahlformat(spalte: dict) -> str | None:
    """Excel-Zahlformat einer Spalte, None: Standard."""
    if spalte["art"] == "nummer" or spalte["ganz"]:
        return "0"
    stellen = spalte["nachkommastellen"]
    if stellen is None:
        return None
    return "0" + ("." + "0" * stellen if stellen else "")


def pruefregel(spalte: dict) -> dict | None:
    """Datenüberprüfung für xlsxwriter (Eingabefelder), None: keine."""
    if spalte["art"] == "text" and spalte["max_zeichen"]:
        return {"validate": "length", "criteria": "<=", "value": spalte["max_zeichen"],
                "error_title": "Zu lang", "error_message": f"Bitte höchstens {spalte['max_zeichen']} Zeichen eintragen.",
                "error_type": "stop", "ignore_blank": True}
    if spalte["art"] != "zahl":
        return None
    # Ohne min/max: weite Grenzen, damit Excel trotzdem nur Zahlen annimmt
    unten = spalte["min"] if spalte["min"] is not None else -MAX_ZAHL
    oben = spalte["max"] if spalte["max"] is not None else MAX_ZAHL
    wort = "eine ganze Zahl" if spalte["ganz"] else "eine Zahl"
    if spalte["min"] is not None and spalte["max"] is not None:
        text = f"{wort} von {_zahl(unten)} bis {_zahl(oben)}"
    elif spalte["min"] is not None:
        text = f"{wort} ab {_zahl(unten)}"
    elif spalte["max"] is not None:
        text = f"{wort} bis {_zahl(oben)}"
    else:
        text = wort
    if spalte["ganz"]:
        unten, oben = int(unten), int(oben)
    return {"validate": "integer" if spalte["ganz"] else "decimal", "criteria": "between", "minimum": unten,
            "maximum": oben, "error_title": "Ungültige Eingabe", "error_message": f"Bitte {text} eintragen.",
            "error_type": "stop", "ignore_blank": True}


def _zahl(wert: float) -> str:
    """15 -> "15", 2.5 -> "2,5" (deutsch, für Meldungen)."""
    return (str(int(wert)) if wert == int(wert) else repr(wert)).replace(".", ",")


def _formate(mappe, p: dict) -> dict:
    rahmen = {"border": 1, "border_color": "808080", "valign": "vcenter"}
    f = {
        "titel": mappe.add_format({"bold": True, "font_size": TITEL_PT, "valign": "vcenter"}),
        "hinweis": mappe.add_format({"font_size": HINWEIS_PT, "text_wrap": True, "valign": "top"}),
        "kopf": mappe.add_format({**rahmen, "bold": True, "text_wrap": True, "align": "center",
                                  "bg_color": "#" + p["farben"]["tabellenkopf"]}),
    }

    def zelle(art: str, zahlformat_: str | None):
        name = (art, zahlformat_)
        if name not in f:
            eigen = {**rahmen}
            if zahlformat_:
                eigen["num_format"] = zahlformat_
            if art == "nummer":
                eigen["align"] = "center"
            if art == "rechnung":
                eigen["bg_color"] = "#" + p["farben"]["rechenfeld"]
            f[name] = mappe.add_format(eigen)
        return f[name]

    f["zelle"] = zelle
    return f


def _blatt(ws, blatt: dict, formate: dict):
    spalten = blatt["spalten"]
    ids = [s["id"] for s in spalten]
    letzte = len(spalten) - 1
    breiten = [s["breite"] or STANDARD_BREITE[s["art"]] for s in spalten]
    for nr, breite in enumerate(breiten):
        ws.set_column(nr, nr, breite)

    zeile = 0
    if blatt["titel"]:
        _ueber_alle(ws, zeile, letzte, blatt["titel"], formate["titel"])
        ws.set_row(zeile, TITEL_PT * 1.5)
        zeile += 1
    for hinweis in blatt["hinweise"]:
        _ueber_alle(ws, zeile, letzte, hinweis, formate["hinweis"])
        ws.set_row(zeile, _hoehe(hinweis, sum(breiten) * 11 / HINWEIS_PT, HINWEIS_PT * 1.35))
        zeile += 1
    if zeile:
        zeile += 1  # eine Zeile Abstand zur Tabelle
    kopf = zeile
    for nr, s in enumerate(spalten):
        ws.write_string(kopf, nr, s["kopf"], formate["kopf"])
    ws.set_row(kopf, max(_hoehe(s["kopf"], breiten[nr], ZEILE_PT) for nr, s in enumerate(spalten)))

    erste, letzte_zeile = kopf + 1, kopf + blatt["zeilen"]
    formeln = {s["id"]: s["baum"] for s in spalten if s["art"] == "rechnung"}
    # Werte einer leeren Zeile, damit die Datei auch ohne Neuberechnung das Richtige zeigt (z. B. Vorschau am Handy)
    leer = rechnung.zeile_ausrechnen(formeln, ids, {s["id"]: rechnung.LEER for s in spalten if s["art"] == "zahl"})
    for nr, s in enumerate(spalten):
        fmt = formate["zelle"](s["art"], zahlformat(s))
        for z in range(erste, letzte_zeile + 1):
            if s["art"] == "nummer":
                ws.write_number(z, nr, z - kopf, fmt)
            elif s["art"] == "rechnung":
                adresse = {sid: f"{rechnung.spaltenbuchstabe(k)}{z + 1}" for k, sid in enumerate(ids)}.__getitem__
                ws.write_formula(z, nr, rechnung.excel(s["baum"], adresse), fmt, _gespeichert(leer[s["id"]]))
            else:
                ws.write_blank(z, nr, None, fmt)
        regel = pruefregel(s)
        if regel:
            ws.data_validation(erste, nr, letzte_zeile, nr, regel)

    ws.freeze_panes(kopf + 1, blatt["fixierte_spalten"])
    ws.set_paper(9)  # A4
    if not blatt["hochformat"]:
        ws.set_landscape()
    ws.fit_to_pages(1, 0)  # Seitenbreite, Höhe beliebig
    ws.repeat_rows(0, kopf)
    ws.print_area(0, 0, letzte_zeile, letzte)
    ws.set_margins(left=0.6, right=0.6, top=0.6, bottom=0.75)
    ws.center_horizontally()
    ws.set_footer("&CSeite &P von &N")


def _gespeichert(wert):
    """Wert, den die Datei vor dem ersten Neuberechnen zeigt. "" schreibt xlsxwriter ohne Typ (erzwingt Neuberechnung)."""
    if wert is rechnung.LEER:
        return ""
    if wert == rechnung.FEHLER:
        return wert
    return int(wert) if float(wert).is_integer() else wert


def _ueber_alle(ws, zeile: int, letzte: int, text: str, fmt):
    if letzte == 0:
        ws.write_string(zeile, 0, text, fmt)
    else:
        ws.merge_range(zeile, 0, zeile, letzte, text, fmt)


def _hoehe(text: str, zeichen_je_zeile: float, zeilenhoehe: float) -> float:
    """Geschätzte Zeilenhöhe in pt für umbrochenen Text (Excel passt verbundene Zellen nicht selbst an)."""
    zeilen = sum(max(1, math.ceil(len(teil) * 1.1 / max(zeichen_je_zeile, 1))) for teil in text.split("\n"))
    return zeilen * zeilenhoehe
