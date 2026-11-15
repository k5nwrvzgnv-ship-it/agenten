"""Prompts für Claude und Prüfung der Antworten (ohne Netz).

Zwei Aufgaben: aus Text oder Foto eine Suche machen, und neue Anzeigen einer Suche bewerten.
Claude antwortet als Text mit genau einem JSON-Objekt; Python prüft es streng.
"""

import json
import re

from seite import Anzeige

MELDE_SCHWELLE = 70  # fürs Schnappen: passt und guter Preis
MAX_BEGRIFFE = 2  # jeder Begriff ist ein Abruf je Takt
MAX_TEXT = 400  # Zeichen Beschreibung je Anzeige im Prompt


class AntwortFehler(Exception):
    """Claudes Antwort ist kein gültiges JSON im erwarteten Aufbau."""


def json_lesen(text: str) -> dict:
    """Das erste JSON-Objekt aus Claudes Text (auch in ```json ... ```)."""
    t = (text or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    start, ende = t.find("{"), t.rfind("}")
    if start < 0 or ende <= start:
        raise AntwortFehler(f"Kein JSON in der Antwort: {text[:200]!r}")
    try:
        daten = json.loads(t[start:ende + 1])
    except json.JSONDecodeError as f:
        raise AntwortFehler(f"Ungültiges JSON: {f}") from f
    if not isinstance(daten, dict):
        raise AntwortFehler("JSON ist kein Objekt")
    return daten


def _zahl(w) -> float | None:
    if isinstance(w, bool) or w is None:
        return None
    if isinstance(w, (int, float)) and w >= 0:
        return float(w)
    return None


# ---------- Suche anlegen ----------

def such_prompt(text: str, foto: str | None = None) -> str:
    """foto: absoluter Pfad des Fotos (Claude öffnet es mit Read), sonst nur Text."""
    quelle = (f"Der Nutzer hat ein Foto geschickt, öffne es mit dem Read-Werkzeug: {foto}"
              + (f"\nDazu schreibt er: {text!r}." if text else "")) if foto \
        else f"Der Nutzer schreibt: {text!r}."
    return f"""Ein Nutzer will auf Kleinanzeigen.de (Gebrauchtmarkt) ein gutes Angebot schnappen.
{quelle}

Mach daraus eine Suche. Antworte nur mit einem JSON-Objekt, ohne weiteren Text:
{{"titel": "kurzer Name der Suche, 2-5 Wörter",
  "beschreibung": "1-2 Sätze: was genau gesucht ist und worauf es ankommt (Modell, Zustand, Merkmale)",
  "begriffe": ["1 bis {MAX_BEGRIFFE} kurze Suchbegriffe (1-3 Wörter), wie man sie bei Kleinanzeigen eintippt"],
  "ausschluss": ["Wörter, die sicher ein falsches Angebot bedeuten, z. B. defekt, Ersatzteile; gern leer"],
  "max_preis": Zahl in Euro, falls der Nutzer eine Grenze nennt, sonst null,
  "marktwert": Zahl in Euro, üblicher Gebrauchtpreis in gutem Zustand, falls du ihn kennst, sonst null}}
Kleinanzeigen findet nur Anzeigen, die alle Wörter eines Begriffs enthalten, und zeigt die neuesten zuerst.
Darum lieber breit suchen (z. B. "rennrad 56" statt "rennrad 56 shimano 105"): Feinheiten wie Ausstattung,
Zustand oder Größe prüft später die Bewertung jeder einzelnen Anzeige. Der zweite Begriff darf eine andere übliche
Bezeichnung sein (z. B. "roadbike"), keine bloße Verkürzung des ersten.
Kann man auf dem Foto nichts Kaufbares erkennen, gib "begriffe": [] und erkläre es in "beschreibung"."""


def such_antwort_pruefen(text: str) -> dict:
    """Prüft die Antwort auf such_prompt. AntwortFehler, wenn etwas fehlt."""
    d = json_lesen(text)
    titel = str(d.get("titel") or "").strip()
    beschreibung = str(d.get("beschreibung") or "").strip()
    begriffe = [str(b).strip() for b in d.get("begriffe") or [] if str(b).strip()][:MAX_BEGRIFFE]
    ausschluss = [str(w).strip() for w in d.get("ausschluss") or [] if str(w).strip()][:15]
    if not beschreibung:
        raise AntwortFehler("Beschreibung fehlt")
    if begriffe and not titel:
        titel = begriffe[0]
    return {"titel": titel[:60], "beschreibung": beschreibung[:500], "begriffe": begriffe,
            "ausschluss": ausschluss, "max_preis": _zahl(d.get("max_preis")),
            "marktwert": _zahl(d.get("marktwert"))}


# ---------- Anzeigen bewerten ----------

def _anzeige_zeile(a: Anzeige) -> str:
    preis = a.preis_text or "kein Preis"
    text = a.beschreibung.replace("\n", " ")[:MAX_TEXT]
    extra = ", gewerblich" if a.gewerblich else ""
    return f"- id {a.id}: {a.titel} | {preis}{extra} | {a.plz} {a.ort} | {text}"


def bewertungs_prompt(suche: dict, kandidaten: list[Anzeige], markt: float | None) -> str:
    werte = []
    if suche.get("marktwert"):
        werte.append(f"geschätzter Gebrauchtpreis bei Anlage der Suche: {suche['marktwert']:g} €")
    if markt:
        werte.append(f"Median der bisher gesehenen Angebote dieser Suche: {markt:g} €")
    if suche.get("max_preis") is not None:
        werte.append(f"Preisgrenze des Nutzers: {suche['max_preis']:g} €")
    zeilen = "\n".join(_anzeige_zeile(a) for a in kandidaten)
    return f"""Ein Nutzer will auf Kleinanzeigen.de gute Angebote schnappen, bevor andere schneller sind.
Gesucht: {suche['titel']}. {suche['beschreibung']}
{chr(10).join(werte)}

Neue Anzeigen:
{zeilen}

Bewerte jede Anzeige mit Punkten von 0 bis 100:
- 85-100: passt genau und ist ein klares Schnäppchen (deutlich unter üblichem Gebrauchtpreis)
- 70-84: passt und guter Preis
- 60-69: passt, fairer Preis
- unter 60: passt nicht, Zubehör statt Gerät, defekt, zu teuer oder unseriös wirkend
Antworte nur mit einem JSON-Objekt, ohne weiteren Text:
{{"bewertungen": [{{"id": Anzeigen-ID, "punkte": 0-100, "marktwert": üblicher Gebrauchtpreis in Euro oder null,
  "grund": "ein kurzer Satz auf Deutsch, bei Schnäppchen warum"}}]}}"""


def bewertung_pruefen(text: str, kandidaten_ids: set[int]) -> dict[int, dict]:
    """Antwort auf bewertungs_prompt -> {id: {"punkte", "marktwert", "grund"}}, nur bekannte IDs."""
    d = json_lesen(text)
    liste = d.get("bewertungen")
    if not isinstance(liste, list):
        raise AntwortFehler("bewertungen fehlt")
    raus = {}
    for e in liste:
        if not isinstance(e, dict):
            continue
        try:
            aid = int(e.get("id"))
            punkte = int(e.get("punkte"))
        except (TypeError, ValueError):
            continue
        if aid not in kandidaten_ids:
            continue
        raus[aid] = {"punkte": max(0, min(100, punkte)), "marktwert": _zahl(e.get("marktwert")),
                     "grund": str(e.get("grund") or "").strip()[:200]}
    return raus


def treffer_auswaehlen(kandidaten: list[Anzeige], bewertungen: dict[int, dict],
                       schwelle: int = MELDE_SCHWELLE) -> list[tuple[Anzeige, dict]]:
    """Anzeigen ab der Schwelle, beste zuerst."""
    paare = [(a, bewertungen[a.id]) for a in kandidaten if a.id in bewertungen
             and bewertungen[a.id]["punkte"] >= schwelle]
    return sorted(paare, key=lambda p: -p[1]["punkte"])
