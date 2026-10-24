"""Text aus den Webseiten der Quellen holen (ohne Netz, nur html.parser).

- gesetz(html) -> Gesetz(ueberschrift, normtext): gesetze-im-internet.de, Einzelnorm. Nur Überschrift
  ("§ 2 Ziel des ...") und Normtext (Absätze aus div.jurAbsatz, Aufzählungen je Zeile), kein Rahmen.
- korpora_seite(html) -> (seite, text): korpora.org, eine HTML-Seite = eine Seite der Akademie-Ausgabe.
  Zeilennummern weg, eine Zeile der Vorlage = eine Zeile. "=" (Bindestrich der Vorlage) bleibt.
  Leerzeichen innen an Klammern und vor Satzzeichen entfallen ("( crimen )" -> "(crimen)"), sie
  stammen aus dem HTML um kursive Wörter, nicht aus der Vorlage.
- textfassung({seite: text}) -> Text mit "--- Seite N" (lesbar mit agentkit.wortlaut.seiten).
- html_text(inhalt, content_type): Zeichensatz aus dem Content-Type, sonst aus <meta>
  (gesetze-im-internet nennt ihn nur dort), sonst utf-8.

Fehler: ParserFehler, wenn die Seite nicht wie erwartet aussieht (Aufbau der Website geändert?).
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlsplit

from agentkit import abruf


class ParserFehler(Exception):
    pass


_META_CHARSET = re.compile(rb'<meta[^>]+charset\s*=\s*["\']?([\w.:-]+)', re.IGNORECASE)
_LEER = re.compile(r"\s+")
_KLAMMER_AUF = re.compile(r"([(\[]) ")
_VOR_ZEICHEN = re.compile(r" ([)\],.;:!?])")
_SEITE = re.compile(r"Seite\s+(\d+)")


def html_text(inhalt: bytes, content_type: str | None) -> str:
    if content_type and "charset" in content_type.lower():
        return abruf.als_text(inhalt, content_type)
    treffer = _META_CHARSET.search(inhalt[:4096])
    name = treffer.group(1).decode("ascii") if treffer else "utf-8"
    return abruf.als_text(inhalt, f"text/html; charset={name}")


def _zeile(text: str) -> str:
    return _LEER.sub(" ", text).strip()


@dataclass
class Gesetz:
    ueberschrift: str
    normtext: str


class _GesetzParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stapel = []        # offene divs: (klassen)
        self.in_h1 = False
        self.span = None        # "jnenbez" | "jnentitel" | None
        self.kopf = {"jnenbez": [], "jnentitel": []}
        self.absaetze = []      # je Absatz Liste von Zeilen (Teilstücke)
        self.absatz_tiefe = None

    def handle_starttag(self, tag, attrs):
        klassen = (dict(attrs).get("class") or "").split()
        if tag == "div":
            self.stapel.append(klassen)
            if self.absatz_tiefe is None and "jurAbsatz" in klassen:
                self.absatz_tiefe = len(self.stapel)
                self.absaetze.append([[]])
            elif self.absatz_tiefe is not None:
                self.absaetze[-1].append([])
        elif tag in ("dt", "dd", "br") and self.absatz_tiefe is not None:
            self.absaetze[-1].append([])
        elif tag == "h1" and any("jnheader" in k for k in self.stapel):
            self.in_h1 = True
        elif tag == "span" and self.in_h1:
            self.span = next((k for k in klassen if k in self.kopf), None)

    def handle_endtag(self, tag):
        if tag == "div" and self.stapel:
            if self.absatz_tiefe == len(self.stapel):
                self.absatz_tiefe = None
            self.stapel.pop()
            if self.absatz_tiefe is not None:
                self.absaetze[-1].append([])
        elif tag == "h1":
            self.in_h1 = False
        elif tag == "span":
            self.span = None

    def handle_data(self, data):
        if self.span:
            self.kopf[self.span].append(data)
        elif self.absatz_tiefe is not None:
            self.absaetze[-1][-1].append(data)


def gesetz(html: str) -> Gesetz:
    p = _GesetzParser()
    p.feed(html)
    p.close()
    bez, titel = _zeile("".join(p.kopf["jnenbez"])), _zeile("".join(p.kopf["jnentitel"]))
    if not bez:
        raise ParserFehler("Keine Paragrafen-Bezeichnung (span.jnenbez) gefunden")
    zeilen = []
    for absatz in p.absaetze:
        zeilen += [z for z in (_zeile("".join(stueck)) for stueck in absatz) if z]
    if not zeilen:
        raise ParserFehler(f"Kein Normtext (div.jurAbsatz) gefunden bei {bez}")
    return Gesetz(f"{bez} {titel}".strip(), "\n".join(zeilen))


class _KorporaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titel, self.in_titel = [], False
        self.zeilen, self.reihe, self.zelle = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_titel = True
        elif tag == "tr":
            self.reihe = []
        elif tag == "td" and self.reihe is not None:
            self.zelle = []
            self.reihe.append(self.zelle)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_titel = False
        elif tag == "tr" and self.reihe is not None:
            zellen = ["".join(z) for z in self.reihe]
            # Textzeile: 2. Zelle Zeilennummer, 3. Zelle Text
            if len(zellen) >= 3 and zellen[1].strip().isdigit():
                self.zeilen.append(zellen[2])
            self.reihe = self.zelle = None

    def handle_data(self, data):
        if self.in_titel:
            self.titel.append(data)
        elif self.zelle is not None:
            self.zelle.append(data)


def korpora_zeile(text: str) -> str:
    text = _zeile(text.replace("\xa0", " "))
    return _VOR_ZEICHEN.sub(r"\1", _KLAMMER_AUF.sub(r"\1", text))


def korpora_seite(html: str) -> tuple[int, str]:
    p = _KorporaParser()
    p.feed(html)
    p.close()
    treffer = _SEITE.search("".join(p.titel))
    if not treffer:
        raise ParserFehler("Keine Seitenzahl im Titel der korpora-Seite")
    zeilen = [korpora_zeile(z) for z in p.zeilen]
    if not any(zeilen):
        raise ParserFehler(f"Kein Text auf korpora-Seite {treffer.group(1)}")
    return int(treffer.group(1)), "\n".join(zeilen)


def art_der_seite(url: str) -> str:
    """"gesetz" oder "korpora" nach dem Host der URL. Andere Hosts: ParserFehler (Teil C ergänzt)."""
    host = (urlsplit(url).hostname or "").lower()
    if host == "gesetze-im-internet.de" or host.endswith(".gesetze-im-internet.de"):
        return "gesetz"
    if host == "korpora.org" or host.endswith(".korpora.org"):
        return "korpora"
    raise ParserFehler(f"Kein Parser für {host}")


def textfassung(seiten: dict[int, str]) -> str:
    return "".join(f"--- Seite {n}\n{text.strip()}\n" for n, text in sorted(seiten.items()))
