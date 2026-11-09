"""Bericht als docx bauen, aus einer geprüften Beschreibung (pruefung.lesen), z. B. eine Recherche mit Zahlen.

Wie die Zusammenfassung (Seite, Schrift, Überschriften, Kästen, Belege klein am Absatzende), aber ohne
Vorlesungskopf: Kopf aus Rubrik, Titel, Untertitel, Stand und erstellt von, Legende der Kennzeichen (nur wenn
benutzt). Belege sind Quellen-IDs (art "quelle") oder Normen, Kennzeichen "annahme" und "unsicher". In Tabellen
darf jede Zelle eigene Belege tragen (klein in der Zelle), Zahlen stehen rechtsbündig. Am Ende offene Fragen und
das Quellenverzeichnis. Fußzeile: Rubrik · Titel, Seite x von y (außer die Vorlage hat eine eigene).
"""

import re
from pathlib import Path

from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.shared import Cm, Pt

from renderer import design, expose, zusammenfassung
from renderer.arbeitsblatt import _breiten, _xml_rahmen, _xml_zeile_wiederholen, _xml_zelle_farbe

KENNZEICHEN = {"annahme": "Annahme", "unsicher": "unsicher"}
LEGENDE = {"annahme": "nicht durch eine Quelle belegt, angenommen",
           "unsicher": "Quelle nicht eindeutig, bitte prüfen"}
HINWEIS_TITEL = {"wichtig": "Wichtig", "einschraenkung": "Einschränkung"}
HINWEIS_FARBE = {"wichtig": "pruefungsrelevant", "einschraenkung": "organisatorisch"}  # Farben aus dem Profil
QUELLE_VOR = {"quelle": "", "norm": ""}
VERZEICHNIS_TITEL = "Quellen"
VERZEICHNIS_EINZUG_CM = 1.27
# Zelle mit Zahl: rechtsbündig ("1.234,5", "-12 %", "3,2 Mio. EUR", "~40", "+5,1")
ZAHL_IN_ZELLE = re.compile(r"^[~≈<>+\-−]?\s?\d[\d.,  ]*\s?(%|[A-Za-zÄÖÜäöü€$.\s/]{0,12})$")


def bauen(beschreibung: dict, ziel: Path, profil: dict | None = None, vorlage: Path | None = None) -> Path:
    """Baut den Bericht nach `ziel` (.docx). `profil` siehe design.py (z. B. beispiele/profil-jan-zusammenfassung.toml),
    `vorlage` eine .docx (Kopfzeile mit Logo, Ränder)."""
    b = _Bau(design.profil_lesen(profil), vorlage)
    b.kopf(beschreibung)
    for block in beschreibung["bloecke"]:
        getattr(b, block["typ"])(block)
    b.schluss_bericht(beschreibung["offene_fragen"], beschreibung["quellenverzeichnis"])
    b.fusszeile(beschreibung)
    b.d.save(ziel)
    return ziel


class _Bau(zusammenfassung._Bau):
    def kopf(self, b: dict):
        p = self.profil
        self.d.core_properties.title = b["titel"]
        self.d.core_properties.author = p["erstellt_von"]
        if b["rubrik"]:
            self._zeile(b["rubrik"], zusammenfassung.KLEIN_PT + 2, fett=True, farbe=self.farben["ueberschrift"], nach=2)
        self._zeile(b["titel"], zusammenfassung.TITEL_PT, fett=True, nach=2 if b["untertitel"] else 6)
        if b["untertitel"]:
            self._zeile(b["untertitel"], zusammenfassung.UEBERSCHRIFT_PT[2], nach=6)
        angaben = [f"Stand {b['datum'] or zusammenfassung.heute()}"]
        if p["erstellt_von"]:
            angaben.append(f"erstellt von {p['erstellt_von']}")
        self._zeile(" · ".join(angaben), zusammenfassung.KLEIN_PT + 1, nach=2)
        benutzt = [k for k in KENNZEICHEN if k in kennzeichen(b)]
        if benutzt:
            zeile = self.d.add_paragraph()
            zeile.paragraph_format.space_after = Pt(2)
            for i, k in enumerate(benutzt):
                self._kennzeichen(zeile, k, davor="" if i == 0 else "   ")
                self._klein(zeile, f" {LEGENDE[k]}")
        trenner = self.d.add_paragraph()
        trenner.paragraph_format.space_after = Pt(6)
        zusammenfassung._xml_absatz_rahmen(trenner, "single", "6", self.farben["ueberschrift"], ("bottom",),
                                           abstand="1")

    def fusszeile(self, b: dict):
        fuss = self.d.sections[0].footer
        if self.vorlage and zusammenfassung._hat_inhalt(fuss):
            return
        p = fuss.paragraphs[0]
        tabs = p.paragraph_format.tab_stops
        for stopp in self.d.styles["Footer"].paragraph_format.tab_stops:
            tabs.add_tab_stop(stopp.position, WD_TAB_ALIGNMENT.CLEAR)
        tabs.add_tab_stop(Cm(self.textbreite_cm - 0.01), WD_TAB_ALIGNMENT.RIGHT)
        links = " · ".join(t for t in (b["rubrik"], b["titel"]) if t)
        self._klein(p, f"{links}\tSeite ")
        self._feld(p, "PAGE")
        self._klein(p, " von ")
        self._feld(p, "NUMPAGES")

    def tabelle(self, block: dict):
        if block["titel"]:
            titel = self.d.add_paragraph()
            titel.add_run(block["titel"]).bold = True
            titel.paragraph_format.space_after = Pt(3)
            titel.paragraph_format.keep_with_next = True
        zeilen = ([block["kopf"]] if block["kopf"] else []) + block["zeilen"]
        belege = ([[None] * len(block["kopf"])] if block["kopf"] else []) + block["belege"]
        t = self.d.add_table(rows=len(zeilen), cols=len(zeilen[0]))
        _xml_rahmen(t)
        # Breite nach Inhalt, Belege (kleiner, eigene Zeile in der Zelle) zählen mit
        breit = [[max(w, "x" * int(len(_belegtext(b)) * 0.8)) if b else w for w, b in zip(werte, zb, strict=True)]
                 for werte, zb in zip(zeilen, belege, strict=True)]
        _breiten(t, expose._spaltenbreiten(breit, self.textbreite_cm))
        for nr, (reihe, werte, zbelege) in enumerate(zip(t.rows, zeilen, belege, strict=True)):
            ist_kopf = block["kopf"] is not None and nr == 0
            reihe.height, reihe.height_rule = Cm(0.6), WD_ROW_HEIGHT_RULE.AT_LEAST
            for spalte, (zelle, wert, beleg) in enumerate(zip(reihe.cells, werte, zbelege, strict=True)):
                p = zelle.paragraphs[0]
                p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(2)
                run = p.add_run(wert)
                run.bold = ist_kopf or (block["erste_spalte_fett"] and spalte == 0)
                if ist_kopf:
                    _xml_zelle_farbe(zelle, self.farben["tabellenkopf"])
                elif spalte > 0 and ZAHL_IN_ZELLE.match(wert.strip()):
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                if beleg:  # eigene Zeile, damit die ID nicht mitten im Wort umbricht
                    if wert:
                        p.add_run().add_break()
                    self._beleg(p, beleg, davor="")
        if block["kopf"]:
            _xml_zeile_wiederholen(t.rows[0])
        unter = self.d.add_paragraph()  # trennt auch zwei Tabellen (siehe arbeitsblatt._abstand)
        self._beleg(unter, block)

    def hinweis(self, block: dict):
        titel = block["titel"] or HINWEIS_TITEL[block["art"]]
        absaetze = self._kasten(titel, block["text"].split("\n"), self.farben[HINWEIS_FARBE[block["art"]]])
        self._beleg(absaetze[-1], block)
        self._nach_kasten()

    def schluss_bericht(self, offene: list, verzeichnis: list):
        if offene:
            self._abschnitt("Offene Fragen")
            self.liste({"nummeriert": False, "punkte": offene})
        if verzeichnis:
            self._abschnitt(VERZEICHNIS_TITEL)
            for eintrag in verzeichnis:
                p = self.d.add_paragraph()
                f = p.paragraph_format
                f.left_indent, f.first_line_indent = Cm(VERZEICHNIS_EINZUG_CM), Cm(-VERZEICHNIS_EINZUG_CM)
                f.space_after = Pt(3)
                f.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.add_run(eintrag["id"]).bold = True
                p.add_run("\n")
                rest = 0
                for treffer in expose.LINK.finditer(eintrag["text"]):
                    p.add_run(eintrag["text"][rest:treffer.start()])
                    expose._Bau._link(self, p, treffer.group())
                    rest = treffer.end()
                p.add_run(eintrag["text"][rest:])

    def _beleg(self, p, d: dict, davor: str | None = None):
        """Kennzeichen und Quellen klein ans Ende des Absatzes, `davor`: Abstand vor dem ersten (Standard: " ",
        wenn der Absatz schon Text hat)."""
        if d.get("kennzeichnung"):
            self._kennzeichen(p, d["kennzeichnung"], davor=(" " if p.text else "") if davor is None else davor)
            davor = None
        if d["quellen"]:
            abstand = (" " if p.text else "") if davor is None else davor
            self._klein(p, f"{abstand}[{_quellen(d)}]")

    def _kennzeichen(self, p, art: str, davor: str):
        run = self._klein(p, f"{davor}[{KENNZEICHEN[art]}]")
        run.bold = True
        return run


def _quellen(d: dict) -> str:
    return "; ".join(QUELLE_VOR[q["art"]] + q["stelle"] for q in d["quellen"])


def _belegtext(d: dict) -> str:
    """Beleg so lang, wie er gedruckt wird (für die Spaltenbreite)."""
    teile = [f"[{KENNZEICHEN[d['kennzeichnung']]}]"] if d.get("kennzeichnung") else []
    return " ".join(teile + ([f"[{_quellen(d)}]"] if d["quellen"] else []))


def kennzeichen(b: dict) -> set:
    """Alle Kennzeichen des Berichts (für die Legende im Kopf), auch aus Tabellenzellen."""
    gefunden = set()
    for block in b["bloecke"]:
        for d in [block] + block.get("punkte", []) + [z for zeile in block.get("belege", []) for z in zeile if z]:
            if d.get("kennzeichnung"):
                gefunden.add(d["kennzeichnung"])
    gefunden.update(f["kennzeichnung"] for f in b["offene_fragen"] if f["kennzeichnung"])
    return gefunden
