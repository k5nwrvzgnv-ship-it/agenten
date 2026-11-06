"""Prüfstand: Läufe ablegen, Codefassung festhalten, mit dem Vorlauf vergleichen (rein, ohne Netz).

Ablage je Lauf: data/laeufe/<lauf-id>/lauf.json, daneben je Reihe ein Ordner mit den Berichten
und der Konsolenausgabe. lauf.json:
    {"id", "zeit", "code", "auftrag", "speicher", "reihen": {name: Ergebnis}}
Ergebnis einer Reihe: {"status", "schritte": {"vorpruefung"|"zusammenbau": Schritt}, "vorpruefung": {...},
"zusammenbau": {...}} mit Schritt = {"exit", "dauer_s", "spitze_mb", "status"}.

Vergleichsbasis: der letzte frühere Lauf, der die Reihe enthält; sonst der Referenzbericht
data/referenz/<reihe>.txt (Ergebnis des Auftraggebers), sonst keine.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import kennzahlen

CODE_DATEIEN = ("*.py", "*.json")
GROESSE = re.compile(r"(\d+)\s*([MG])", re.IGNORECASE)
RESERVE_MB = 500  # bleibt neben der Speichergrenze frei, damit die übrigen Dienste weiterlaufen

# Schwellen für "geändert" im Vergleich (Feld: absolute Abweichung). Felder ohne Eintrag gelten
# als geändert, sobald sie sich überhaupt unterscheiden. Rechenzeit: relativ (Anteil).
SCHWELLEN = {
    "px_mm_band": 0.02, "px_mm_min": 0.05, "px_mm_max": 0.05,
    "nahtversatz_median_mm": 0.02, "nahtversatz_max_mm": 0.05,
    "laengsabweichung_prozent": 0.05, "laenge_roh_mm": 2, "laengsabweichung_mm": 2,
    "kante_streuung_mm": 0.05, "kante_langwellig_mm": 0.2, "kante_gefunden_prozent": 2,
    "nahtkanten": 2, "nahtkante_staerke": 2, "punktpaar_rest_median_mm": 0.01, "einpassfaktor": 0.0005,
    "belegt_prozent": 0.1, "aufloesung_px_mm": 0.02,
    "ueberlappung_median_prozent": 0.5, "ueberlappung_min_prozent": 0.5,
}
RECHENZEIT_ANTEIL = 0.2
NICHT_VERGLEICHEN = {"aufmass_mm", "aufnahmen"}
NAMEN = {
    "px_mm_band": "Px/mm (Band)", "px_mm_min": "Px/mm je Bild min", "px_mm_max": "Px/mm je Bild max",
    "naehte": "Nähte", "nahtversatz_median_mm": "Nahtversatz Median mm", "nahtversatz_max_mm": "Nahtversatz max mm",
    "laenge_roh_mm": "Länge roh mm", "laengsabweichung_mm": "Längsabweichung mm",
    "laengsabweichung_prozent": "Längsabweichung %", "einpassfaktor": "Einpassfaktor",
    "kante_streuung_mm": "Kante Streuung mm", "kante_langwellig_mm": "Kante langwellig (Drift) mm",
    "kante_gefunden_prozent": "Kante gefunden %", "nahtkanten": "sichtbare Nahtkanten",
    "nahtkante_staerke": "stärkste Nahtkante", "punktpaar_rest_median_mm": "Punktpaare Rest Median mm",
    "belegt_prozent": "belegt %", "rechenzeit_s": "Rechenzeit s", "aufloesung_px_mm": "Auflösung Px/mm",
    "ueberlappung_median_prozent": "Überlappung Median %", "ueberlappung_min_prozent": "Überlappung min %",
    "masstreue": "Maßtreue", "farbtreue": "Farbtreue",
    "ohne_verbindung": "ohne Verbindung", "pruefbericht": "Prüfbericht", "maengel": "Mängel der Vorprüfung",
}


# --- Codefassung und Ablage ------------------------------------------------------------------

def codefassung(verfahren: Path) -> str:
    """Prüfsumme (12 Zeichen) über die Programmdateien des Verfahrens, Name und Inhalt."""
    h = hashlib.sha256()
    for muster in CODE_DATEIEN:
        for p in sorted(verfahren.glob(muster)):
            h.update(p.name.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:12]


def lauf_id(jetzt: datetime) -> str:
    return jetzt.strftime("%Y%m%d-%H%M%S")


def reihen_finden(reihen_dir: Path) -> list[str]:
    """Reihen = Unterordner mit bauteil.json und mindestens zwei JPEG-Dateien, sortiert."""
    if not reihen_dir.is_dir():
        return []
    gefunden = []
    for d in sorted(reihen_dir.iterdir()):
        if d.is_dir() and (d / "bauteil.json").is_file():
            if len([p for p in d.iterdir() if p.suffix.lower() in (".jpg", ".jpeg")]) >= 2:
                gefunden.append(d.name)
    return gefunden


def auswahl(text: str, reihen: list[str]) -> list[str]:
    """Reihen, deren Name im Auftragstext steht (ohne Groß-/Kleinschreibung); keine genannt: alle."""
    t = text.casefold()
    genannt = [r for r in reihen if r.casefold() in t]
    return genannt or list(reihen)


def speicher_aus_text(text: str, standard: str) -> str:
    """'speicher 4G' oder 'speicher=3500M' im Auftrag setzt die Grenze, sonst standard."""
    m = re.search(r"speicher\s*=?\s*(\d+\s*[MG])\b", text, re.IGNORECASE)
    return m.group(1).replace(" ", "").upper() if m else standard


def in_mb(groesse: str) -> int:
    m = GROESSE.fullmatch(groesse.strip())
    if not m:
        raise ValueError(f"Ungültige Speichergröße: {groesse!r}")
    return int(m.group(1)) * (1024 if m.group(2).upper() == "G" else 1)


def verfuegbar_mb(meminfo: str) -> int | None:
    """MemAvailable aus /proc/meminfo in MB."""
    m = re.search(r"^MemAvailable:\s+(\d+) kB", meminfo, re.MULTILINE)
    return int(m.group(1)) // 1024 if m else None


def genug_speicher(meminfo: str, grenze: str) -> tuple[bool, str]:
    frei = verfuegbar_mb(meminfo)
    noetig = in_mb(grenze) + RESERVE_MB
    if frei is None:
        return False, "freier Speicher nicht lesbar (/proc/meminfo)"
    if frei < noetig:
        return False, f"nur {frei} MB frei, nötig {noetig} MB (Grenze {grenze} + {RESERVE_MB} MB Reserve)"
    return True, f"{frei} MB frei, nötig {noetig} MB"


def befehl(python: str, skript: Path, argumente: list[str], grenze: str, name: str) -> list[str]:
    """Aufruf in einem eigenen systemd-Scope mit fester Speichergrenze: wird es zu groß, stirbt nur dieser."""
    return ["systemd-run", "--user", "--scope", "--quiet", f"--unit={name}",
            "-p", f"MemoryMax={grenze}", "-p", "MemorySwapMax=0",
            python, str(skript), *argumente]


def scope_name(lauf: str, reihe: str, schritt: str) -> str:
    """Eindeutiger Unit-Name, nur erlaubte Zeichen."""
    return "holzbalkenscan-" + re.sub(r"[^A-Za-z0-9]+", "-", f"{lauf}-{reihe}-{schritt}").strip("-").lower()


def schritt_status(schritt: str, exit_code: int, zeit_um: bool, bericht_da: bool) -> str:
    """ok | speichergrenze | zeitgrenze | fehler.

    zusammensetzen2.py: 0 ohne, 1 mit Prüfpunkten (beides gelungen), 2 Eingabe fehlt, 3 Absturz.
    pruefen.py: 0/1/2 = grün/gelb/rot, das Urteil steht im Bericht; ohne Bericht ist es ein Fehler.
    SIGKILL (-9 bzw. 137) ohne Zeitgrenze: der Kernel hat an der Speichergrenze abgebrochen.
    """
    if zeit_um:
        return "zeitgrenze"
    if exit_code in (-9, 137):
        return "speichergrenze"
    if not bericht_da:
        return "fehler"
    if schritt == "zusammenbau":
        return "ok" if exit_code in (0, 1) else "fehler"
    return "ok" if exit_code in (0, 1, 2) else "fehler"


def speichern(lauf_dir: Path, lauf: dict) -> Path:
    lauf_dir.mkdir(parents=True, exist_ok=True)
    pfad = lauf_dir / "lauf.json"
    tmp = pfad.with_suffix(".tmp")
    tmp.write_text(json.dumps(lauf, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(pfad)
    return pfad


def vorlauf(laeufe_dir: Path, vor_id: str, reihe: str) -> dict | None:
    """Letzter Lauf vor vor_id, der die Reihe enthält."""
    if not laeufe_dir.is_dir():
        return None
    for d in sorted((d for d in laeufe_dir.iterdir() if d.is_dir() and d.name < vor_id), reverse=True):
        try:
            lauf = json.loads((d / "lauf.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if reihe in lauf.get("reihen", {}):
            return lauf
    return None


def basis(laeufe_dir: Path, referenz_dir: Path, vor_id: str, reihe: str) -> tuple[str, dict] | None:
    """(Bezeichnung, Ergebnis der Reihe) zum Vergleichen, siehe Kopf."""
    alt = vorlauf(laeufe_dir, vor_id, reihe)
    if alt:
        return f"Vorlauf {alt['id']} (Code {alt['code']})", alt["reihen"][reihe]
    ref = referenz_dir / f"{reihe}.txt"
    if ref.is_file():
        return "Referenzbericht", {"zusammenbau": kennzahlen.aus_zusammenbau(ref.read_text(encoding="utf-8"))}
    return None


# --- Vergleich und Meldetext -----------------------------------------------------------------

def _zahl(w):
    return isinstance(w, (int, float)) and not isinstance(w, bool)


def vergleichen(alt: dict, neu: dict) -> list[str]:
    """Zeilen mit allen Unterschieden zwischen zwei Kennzahl-Sätzen (gleiche Art)."""
    zeilen = []
    for feld in neu.keys() | alt.keys():
        if feld in NICHT_VERGLEICHEN:
            continue
        a, n = alt.get(feld), neu.get(feld)
        name = NAMEN.get(feld, feld)
        if isinstance(a, list) or isinstance(n, list):
            a, n = a or [], n or []
            dazu = [x for x in n if x not in a]
            weg = [x for x in a if x not in n]
            if dazu:
                zeilen.append(f"{name} neu: " + "; ".join(dazu))
            if weg:
                zeilen.append(f"{name} weg: " + "; ".join(weg))
        elif _zahl(a) and _zahl(n):
            d = n - a
            if feld == "rechenzeit_s":
                geaendert = a > 0 and abs(d) / a > RECHENZEIT_ANTEIL
            else:
                geaendert = abs(d) > SCHWELLEN.get(feld, 0) + 1e-9
            if geaendert:
                zeilen.append(f"{name}: {_fmt(a)} -> {_fmt(n)} ({d:+.4g})")
        elif a != n:
            zeilen.append(f"{name}: {_fmt(a)} -> {_fmt(n)}")
    return sorted(zeilen)


def _fmt(w) -> str:
    if w is None:
        return "–"
    if isinstance(w, float):
        return f"{w:g}"
    return str(w)


def reihe_kurz(name: str, erg: dict) -> list[str]:
    """Kernzahlen einer Reihe für die Meldung."""
    z = [f"{name}: {erg['status']}"]
    for schritt, s in erg.get("schritte", {}).items():
        z.append(f"  {schritt}: {s['status']}, Exit {s['exit']}, {s['dauer_s']:.0f} s, "
                 f"Speicherspitze {_fmt(s.get('spitze_mb'))} MB")
    v = erg.get("vorpruefung") or {}
    if v:
        z.append(f"  Vorprüfung: Maß {_fmt(v.get('masstreue'))}, Farbe {_fmt(v.get('farbtreue'))}, "
                 f"{len(v.get('maengel') or [])} Mängel")
    k = erg.get("zusammenbau") or {}
    if k:
        ohne = k.get("ohne_verbindung") or []
        pb = k.get("pruefbericht")
        z.append(f"  Px/mm {_fmt(k.get('px_mm_band'))}, Nahtversatz Median {_fmt(k.get('nahtversatz_median_mm'))}"
                 f" / max {_fmt(k.get('nahtversatz_max_mm'))} mm, ohne Verbindung: {', '.join(ohne) or 'keine'}")
        z.append(f"  Länge roh {_fmt(k.get('laengsabweichung_prozent'))} %, Kante langwellig "
                 f"{_fmt(k.get('kante_langwellig_mm'))} mm, Nahtkanten {_fmt(k.get('nahtkanten'))}, "
                 f"Prüfpunkte {'–' if pb is None else len(pb)}, Rechenzeit {_fmt(k.get('rechenzeit_s'))} s")
    return z


def vergleich_text(bezeichnung: str, alt: dict, neu: dict) -> list[str]:
    z = []
    for art in ("vorpruefung", "zusammenbau"):
        if alt.get(art) and neu.get(art):
            z += [f"    {art}: {u}" for u in vergleichen(alt[art], neu[art])]
    if not z:
        return [f"  gegen {bezeichnung}: keine Änderung über den Schwellen"]
    return [f"  gegen {bezeichnung}:"] + z


def meldetext(lauf: dict, vergleiche: dict[str, tuple[str, dict] | None]) -> str:
    """Meldung an Jan: Kopf, je Reihe Kernzahlen und Unterschiede zur Vergleichsbasis."""
    z = [f"Prüfstand holzbalkenscan, Lauf {lauf['id']}, Code {lauf['code']}, Speichergrenze {lauf['speicher']}"]
    for name, erg in lauf["reihen"].items():
        z.append("")
        z += reihe_kurz(name, erg)
        b = vergleiche.get(name)
        if b is None:
            z.append("  kein Vorlauf und kein Referenzbericht zum Vergleichen")
        else:
            z += vergleich_text(b[0], b[1], erg)
    return "\n".join(z)


def reihe_status(schritte: dict) -> str:
    """Gesamtstatus einer Reihe: ok nur, wenn alle Schritte ok sind, sonst der erste Fehlerstatus."""
    for s in schritte.values():
        if s["status"] != "ok":
            return s["status"]
    return "ok"
