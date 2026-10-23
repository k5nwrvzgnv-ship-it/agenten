"""Lias Chats aufbereiten und anonymisieren (Schritt 5).

aufbereiten: aus dem Exportformat nur, was die Auswertung braucht (Titel, Datum, Zusammenfassung, je
  Nachricht Absender, Vorgänger, Text, Anhänge mit Text, Dateinamen). Werkzeugaufrufe, Suchergebnisse
  und Denkschritte fallen weg.
Ersetzer: ersetzt Namen aus einer Liste (data/namen.json, nicht im Repo) durch Platzhalter wie
  [Schüler 3], [Person 1], [Schule A], dazu per Muster E-Mail, Telefon, Adressen, lange Nummern.
  Namen: ganzes Wort (auch zwischen Unterstrichen wie in Bewertung_NAME.docx), längste zuerst, ohne Rücksicht
  auf Groß- und Kleinschreibung (Lia schreibt Namen oft klein oder groß), außer bei nur_gross (Wörter wie
  "said" oder "Amine", die es auch klein gibt). Genitiv-s bleibt hinten.
Ohne Netz, getestet in tests/test_anonym.py.
"""

import re

from auswahl import nachricht_text

VORNE = r"(?<![^\W_])"  # davor kein Buchstabe und keine Ziffer (Unterstrich, Bindestrich zählen als Grenze)
HINTEN = r"(?=s?(?![^\W_]))"

PLATZHALTER = {"schueler": "Schüler {n}", "person": "Person {n}", "schule": "Schule {b}",
               "lehrkraft": "Lehrkraft", "partner": "Partner"}

MUSTER = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[E-Mail]"),
    (re.compile(r"(?:\+49|\b0)\d{2,4}[ /-]?\d{3,}(?:[ /-]?\d{2,})*"), "[Telefon]"),
    (re.compile(r"\b[A-ZÄÖÜ][\w-]*(?:straße|strasse|str\.|weg|platz|allee|damm|ufer|gasse)\s*\d+\s?[a-z]?\b",
                re.I), "[Adresse]"),
    (re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+"), "[PLZ Ort]"),
    (re.compile(r"\b(?!97[89]\d{10}\b)\d{5,}\b"), "[Nummer]"),
    (re.compile(r"\b\d{2}[A-Z]\d{2}\b"), "[Schulnummer]"),
]


def aufbereiten(chats: list[dict]) -> list[dict]:
    aus = []
    for c in chats:
        nachrichten = []
        for n in c.get("chat_messages") or []:
            nachrichten.append({
                "uuid": n.get("uuid"), "vorgaenger": n.get("parent_message_uuid"),
                "absender": "lia" if n.get("sender") == "human" else "claude",
                "zeit": n.get("created_at"), "text": nachricht_text(n),
                "anhaenge": [{"name": a.get("file_name") or "", "text": a.get("extracted_content") or ""}
                             for a in n.get("attachments") or []],
                "dateien": [f.get("file_name") or "" for f in n.get("files") or []],
            })
        aus.append({"uuid": c.get("uuid"), "titel": c.get("name") or "", "datum": (c.get("created_at") or "")[:10],
                    "zusammenfassung": c.get("summary") or "", "nachrichten": nachrichten})
    return aus


class Ersetzer:
    """namen: Liste von {"name": ..., "art": schueler|person|schule|lehrkraft|partner, "nur_gross": bool,
    "gleich_wie": anderer Name (gleicher Platzhalter, z. B. Vor- und Nachname)}."""

    def __init__(self, namen: list[dict]):
        self.zuordnung: dict[str, str] = {}
        zaehler: dict[str, int] = {}
        for e in namen:
            if e.get("gleich_wie"):
                if e["gleich_wie"] not in self.zuordnung:
                    raise ValueError(f"gleich_wie verweist auf unbekannten Namen: {e['gleich_wie']}")
                self.zuordnung[e["name"]] = self.zuordnung[e["gleich_wie"]]
                continue
            art = e["art"]
            zaehler[art] = zaehler.get(art, 0) + 1
            n = zaehler[art]
            self.zuordnung[e["name"]] = "[" + PLATZHALTER[art].format(n=n, b=chr(ord("A") + n - 1)) + "]"
        teile = []
        for e in sorted(namen, key=lambda e: -len(e["name"])):
            name = e["name"]
            muster = re.escape(name).replace(r"\ ", "[ _]")  # Vor- und Nachname auch mit Unterstrich
            muster = muster if e.get("nur_gross") else f"(?i:{muster})"
            teile.append(f"(?P<n{len(teile)}>{muster})")
        self._namen = [e["name"] for e in sorted(namen, key=lambda e: -len(e["name"]))]
        self._regex = re.compile(VORNE + "(?:" + "|".join(teile) + ")" + HINTEN) if teile else None
        self.treffer: dict[str, int] = {}

    def _ersatz(self, m: re.Match) -> str:
        name = self._namen[int(m.lastgroup[1:])]
        self.treffer[name] = self.treffer.get(name, 0) + 1
        return self.zuordnung[name]

    def text(self, s: str) -> str:
        if self._regex:
            s = self._regex.sub(self._ersatz, s)
        for muster, ersatz in MUSTER:
            s = muster.sub(ersatz, s)
        return s

    def alles(self, wert):
        """Ersetzt in allen Texten einer JSON-Struktur (Schlüssel bleiben)."""
        if isinstance(wert, str):
            return self.text(wert)
        if isinstance(wert, list):
            return [self.alles(w) for w in wert]
        if isinstance(wert, dict):
            return {k: (w if k in ("uuid", "vorgaenger", "zeit", "datum") else self.alles(w)) for k, w in wert.items()}
        return wert


def reste(chats: list[dict], namen: list[dict]) -> dict[str, int]:
    """Zählt Namen aus der Liste, die nach dem Ersetzen noch vorkommen (sollte leer sein)."""
    text = "\n".join(_texte(chats))
    funde = {}
    for e in namen:
        anzahl = len(re.findall(VORNE + re.escape(e["name"]) + HINTEN, text,
                                0 if e.get("nur_gross") else re.I))
        if anzahl:
            funde[e["name"]] = anzahl
    return funde


def _texte(wert):
    if isinstance(wert, str):
        yield wert
    elif isinstance(wert, list):
        for w in wert:
            yield from _texte(w)
    elif isinstance(wert, dict):
        for w in wert.values():
            yield from _texte(w)
