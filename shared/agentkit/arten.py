"""Dokumentarten des Arbeitsplatzes aus shared/arbeitsplatz/arten.toml (docs/arbeitsplatz-plan.md, Arten-Datei).

Eine Art ist eine Arbeitsanweisung: Kennung, Name, Beschreibung, zuständiger Agent, aktiv (nur aktive stehen in der
Galerie), Ausgabe (Dateiformate), Ansicht ("" = Standardansicht) und die Felder des Formulars. material sagt, ob das
Formular Dateien annimmt: "nein", "optional" (Standard) oder "pflicht". material_oder = "<Feldname>": dieses Feld oder
mindestens eine Datei ist Pflicht (z. B. Transkript als Text oder als Datei). rueckmeldung = false: der Agent nimmt zu
dieser Art keine Rückmeldung an, die App bietet sie nicht an (Standard true).

Aufruf:
  from agentkit import arten
  alle = arten.laden()                  # prüft die Datei, ArtFehler mit allen Fehlern
  arten.aktive(alle); arten.finden(alle, "praesentation")
  werte = arten.formular_pruefen(art, {"Thema": "Holz"})   # dict Feldname -> Text, ArtFehler bei Fehlern
  text = arten.auftragstext(art, werte)  # "Art: Präsentation\\nThema: Holz\\n..."
"""

import re
import tomllib
from pathlib import Path

from . import auftraege, config

DATEI = config.KONTINGENT_DIR / "arbeitsplatz" / "arten.toml"
FELDARTEN = ("zeile", "text", "auswahl", "zahl")
AUSGABEN = ("pdf", "docx", "pptx", "xlsx", "md", "html")
MATERIAL = ("nein", "optional", "pflicht")
ART_SCHLUESSEL = {"kennung", "name", "beschreibung", "agent", "aktiv", "ausgabe", "ansicht", "material", "feld",
                  "material_oder", "rueckmeldung"}
FELD_SCHLUESSEL = {"name", "art", "pflicht", "werte", "hilfe"}
MAX_ZEILE = 500
MAX_TEXT = auftraege.MAX_FELDWERT
ZAHL = re.compile(r"-?\d{1,9}([.,]\d{1,6})?")


class ArtFehler(Exception):
    pass


def pruefen(daten: dict, agenten_dir: Path | None = None) -> list[str]:
    """Fehler der Arten-Datei (leer = in Ordnung). agenten_dir: Ordner, in dem jeder Agent einen Ordner mit agent.py
    haben muss (Standard: Hauptordner)."""
    agenten_dir = agenten_dir or auftraege.AGENTEN_DIR
    fehler = []
    liste = daten.get("art")
    if set(daten) - {"art"}:
        fehler.append(f"Unbekannte Schlüssel oben: {', '.join(sorted(set(daten) - {'art'}))}")
    if not isinstance(liste, list) or not liste:
        return fehler + ["Keine [[art]] eingetragen"]
    kennungen = set()
    for i, art in enumerate(liste, start=1):
        wo = f"Art {i} ({art.get('kennung', '?')})" if isinstance(art, dict) else f"Art {i}"
        if not isinstance(art, dict):
            fehler.append(f"{wo}: keine Tabelle")
            continue
        if unbekannt := set(art) - ART_SCHLUESSEL:
            fehler.append(f"{wo}: unbekannte Schlüssel {', '.join(sorted(unbekannt))}")
        k = art.get("kennung")
        if not isinstance(k, str) or not auftraege.REIHE_MUSTER.fullmatch(k):
            fehler.append(f"{wo}: kennung fehlt oder ungültig")
        elif k in kennungen:
            fehler.append(f"{wo}: kennung doppelt")
        else:
            kennungen.add(k)
        for s in ("name", "beschreibung"):
            if not isinstance(art.get(s), str) or not art[s].strip():
                fehler.append(f"{wo}: {s} fehlt")
        agent = art.get("agent")
        if not isinstance(agent, str) or not re.fullmatch(r"[a-z]+", agent):
            fehler.append(f"{wo}: agent fehlt oder ungültig")
        elif not (agenten_dir / agent / "agent.py").is_file():
            fehler.append(f"{wo}: Agent {agent} gibt es nicht")
        if not isinstance(art.get("aktiv"), bool):
            fehler.append(f"{wo}: aktiv muss true oder false sein")
        ausgabe = art.get("ausgabe", [])
        if not isinstance(ausgabe, list) or any(a not in AUSGABEN for a in ausgabe):
            fehler.append(f"{wo}: ausgabe nur aus {', '.join(AUSGABEN)}")
        ansicht = art.get("ansicht", "")
        if not isinstance(ansicht, str) or (ansicht and not auftraege.REIHE_MUSTER.fullmatch(ansicht)):
            fehler.append(f"{wo}: ansicht ungültig")
        if art.get("material", "optional") not in MATERIAL:
            fehler.append(f"{wo}: material nur {', '.join(MATERIAL)}")
        if not isinstance(art.get("rueckmeldung", True), bool):
            fehler.append(f"{wo}: rueckmeldung muss true oder false sein")
        if "material_oder" in art:
            namen = [f.get("name") for f in art.get("feld", []) if isinstance(f, dict)]
            if art["material_oder"] not in namen or art.get("material", "optional") != "optional":
                fehler.append(f"{wo}: material_oder muss ein Feld nennen, material dann optional")
        fehler += _felder_pruefen(wo, art.get("feld", []))
    return fehler


def _felder_pruefen(wo: str, felder) -> list[str]:
    if not isinstance(felder, list):
        return [f"{wo}: feld muss eine Liste sein ([[art.feld]])"]
    fehler, namen = [], set()
    if len(felder) > auftraege.MAX_FELDER - 1:
        fehler.append(f"{wo}: mehr als {auftraege.MAX_FELDER - 1} Felder")
    for j, f in enumerate(felder, start=1):
        fw = f"{wo}, Feld {j}"
        if not isinstance(f, dict):
            fehler.append(f"{fw}: keine Tabelle")
            continue
        if unbekannt := set(f) - FELD_SCHLUESSEL:
            fehler.append(f"{fw}: unbekannte Schlüssel {', '.join(sorted(unbekannt))}")
        name = f.get("name")
        if not isinstance(name, str) or not name.strip() or len(name) > auftraege.MAX_FELDNAME \
                or ":" in name or "\n" in name:
            fehler.append(f"{fw}: name fehlt oder ungültig (kein Doppelpunkt)")
        elif name.casefold() in namen or name.casefold() == "art":
            fehler.append(f"{fw}: name {name} doppelt oder reserviert")
        else:
            namen.add(name.casefold())
        if f.get("art") not in FELDARTEN:
            fehler.append(f"{fw}: art nur {', '.join(FELDARTEN)}")
        if not isinstance(f.get("pflicht", False), bool):
            fehler.append(f"{fw}: pflicht muss true oder false sein")
        werte = f.get("werte")
        if f.get("art") == "auswahl":
            if not isinstance(werte, list) or not werte or not all(isinstance(w, str) and w.strip() for w in werte):
                fehler.append(f"{fw}: auswahl braucht werte (Liste aus Text)")
        elif werte is not None:
            fehler.append(f"{fw}: werte nur bei auswahl")
        if not isinstance(f.get("hilfe", ""), str):
            fehler.append(f"{fw}: hilfe muss Text sein")
    return fehler


def laden(datei: Path | None = None, agenten_dir: Path | None = None) -> list[dict]:
    """Alle Arten der Datei mit Standardwerten (ansicht "", material "optional", ausgabe [], feld []).
    Fehler in der Datei: ArtFehler mit allen Fehlern."""
    datei = datei or DATEI
    try:
        daten = tomllib.loads(datei.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as f:
        raise ArtFehler(f"{datei} nicht lesbar: {f}") from f
    if fehler := pruefen(daten, agenten_dir):
        raise ArtFehler(f"{datei}: " + "; ".join(fehler))
    return [{"ansicht": "", "material": "optional", "material_oder": "", "rueckmeldung": True, "ausgabe": [], **a,
             "feld": [{"pflicht": False, "hilfe": "", **f} for f in a.get("feld", [])]} for a in daten["art"]]


def aktive(alle: list[dict]) -> list[dict]:
    return [a for a in alle if a["aktiv"]]


def finden(alle: list[dict], kennung: str) -> dict | None:
    return next((a for a in alle if a["kennung"] == kennung), None)


def formular_pruefen(art: dict, eingabe: dict) -> dict[str, str]:
    """Werte des Formulars zu art: nur bekannte Felder, Pflicht gefüllt, Auswahl aus den Werten, Zahl als Zahl,
    Zeile einzeilig. Gibt {Feldname: Text} in der Reihenfolge der Felder zurück (leere optionale Felder mit "").
    Fehler: ArtFehler mit allen Fehlern, lesbar für Jan."""
    fehler, werte = [], {}
    for f in art["feld"]:
        roh = eingabe.get(f["name"], "")
        wert = (roh if isinstance(roh, str) else "").replace("\r\n", "\n").strip()
        if f["art"] != "text":
            wert = " ".join(wert.split())
        if not wert:
            if f["pflicht"]:
                fehler.append(f"{f['name']}: bitte ausfüllen")
        elif f["art"] == "auswahl" and wert not in f["werte"]:
            fehler.append(f"{f['name']}: bitte aus der Liste wählen")
        elif f["art"] == "zahl" and not ZAHL.fullmatch(wert):
            fehler.append(f"{f['name']}: bitte eine Zahl")
        elif len(wert) > (MAX_TEXT if f["art"] == "text" else MAX_ZEILE):
            fehler.append(f"{f['name']}: zu lang")
        werte[f["name"]] = wert
    if fehler:
        raise ArtFehler("; ".join(fehler))
    return werte


def material_fehler(art: dict, werte: dict[str, str], anzahl_dateien: int) -> list[str]:
    """Passt die Zahl der Dateien zu material und material_oder der Art? Fehlertexte für das Formular."""
    if art["material"] == "pflicht" and not anzahl_dateien:
        return ["Material: bitte mindestens eine Datei anhängen"]
    if art["material"] == "nein" and anzahl_dateien:
        return ["Diese Art nimmt keine Dateien"]
    if art.get("material_oder") and not anzahl_dateien and not werte.get(art["material_oder"]):
        return [f"{art['material_oder']}: bitte ausfüllen oder eine Datei anhängen"]
    return []


def auftragstext(art: dict, werte: dict[str, str]) -> str:
    """Erste Zeile "Art: <Name>", dann je gefülltes Feld "Feldname: Wert" (mehrzeilige Werte eingerückt)."""
    zeilen = [f"Art: {art['name']}"]
    for name, wert in werte.items():
        if wert:
            zeilen.append(f"{name}: " + wert.replace("\n", "\n  "))
    return "\n".join(zeilen)
