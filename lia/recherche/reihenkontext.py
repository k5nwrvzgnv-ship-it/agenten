"""Welche Reihe recherche meint und was davon in die Prompts geht, über agentkit.struktur (ohne Netz).

Strukturplan docs/struktur-pflege-plan.md, Bauschritt 2: recherche liest reihen.toml nicht mehr selbst, sondern
nur über struktur.laden(), und erkennt eine Reihe nur an ihrer id, nie am Titel.

Welche Reihe:
1. die aus dem Auftrag: Feld ort (id einer Reihe oder Stunde) oder reihe. Läufe von Hand geben sie mit
   --reihe <id> an (agent.py, fallsuche.py).
2. sonst die eine Prüfungsreihe (nicht archivierte Reihe mit einer Stunde mit Marke „Prüfung“, Jan 03.11.2026:
   Examen ist eine Stunde), denn Kernstellen und Fallsuche dienen Lias Examensreihe.
Gibt es keine eindeutige, läuft der Schritt ohne Reihenkontext, und der Grund geht an Jan. Bis die Migration
(Bauschritt 3) eine Prüfungsstunde einträgt, gilt das ohne --reihe immer.

Frühere Reihenfragen (Vorbild für allgemeine Reihenfragen im Dossier): Reihenfragen abgeschlossener und
archivierter Reihen desselben Fachs; im alten Format zusätzlich aus dem Freitext bisherige_reihen („Klasse 7,
Thema: Frage? …“), der erst mit der Migration wegfällt (F10).
"""

import re
from pathlib import Path

from agentkit import struktur


def waehlen(s: struktur.Struktur, ort: str | None = None) -> tuple[dict | None, str]:
    """(Reihe, "") oder (None, Grund für Jan)."""
    if ort:
        lage = s.ort(ort)
        if lage is None:
            return None, f"Reihe oder Stunde {ort!r} gibt es nicht in {struktur.DATEI}"
        if lage["reihe"] is None:
            return None, f"{ort!r} ist ein(e) {lage['ebene']}, keine Reihe oder Stunde"
        return lage["reihe"], ""
    treffer = s.pruefungsreihen()
    if len(treffer) == 1:
        return treffer[0], ""
    if not treffer:
        return None, "keine Reihe mit einer Stunde mit Marke „Prüfung“ (Reihe mit --reihe <id> angeben)"
    return None, f"{len(treffer)} Reihen mit Prüfungsstunde ({', '.join(r['id'] for r in treffer)})"


def laden(instanz: Path | None = None, ort: str | None = None) -> tuple[struktur.Struktur | None, dict | None, str]:
    """Struktur laden und die Reihe wählen: (Struktur, Reihe, Grund). Kaputte Datei: (None, None, Grund)."""
    try:
        s = struktur.laden(instanz)
    except (struktur.StrukturFehler, OSError) as e:
        return None, None, f"{struktur.DATEI} nicht lesbar: {e}"
    reihe, grund = waehlen(s, ort)
    return s, reihe, grund


def text(reihe: dict | None) -> str:
    """Prompt-Abschnitt zur Reihe (wie bisher: Fach, Klasse, Titel, Lerngruppe, Planung). Ohne Reihe leer."""
    if not reihe:
        return ""
    klasse = f"Klasse {reihe['klasse']}" if reihe["klasse"][:1].isdigit() else reihe["klasse"]
    teile = [f"{reihe['fach']} {klasse}, Reihe {reihe['titel']}."]
    for feld, name in (("lerngruppe", "Lerngruppe"), ("notizen", "Planung")):
        if reihe[feld]:
            teile.append(f"{name}: {reihe[feld]}")
    return "\n".join(teile)


def fruehere_reihenfragen(s: struktur.Struktur | None, reihe: dict | None = None) -> list[str]:
    """Lias Reihenfragen aus abgeschlossenen und archivierten Reihen (mit Reihe: nur desselben Fachs, ohne sie
    selbst), im alten Format dazu die aus bisherige_reihen. Ohne Doppelte, in Dateireihenfolge."""
    if s is None:
        return []
    reihen = [r for r in s.reihen if reihe is None or (r["fach_id"] == reihe["fach_id"] and r["id"] != reihe["id"])]
    fragen = [r["reihenfrage"] for r in reihen
              if r["reihenfrage"] and (r["stand"] == "abgeschlossen" or r["im_archiv"])]
    if s.format == "alt":
        quellen = reihen + ([reihe] if reihe else [])
        for eintrag in (e for r in quellen for e in r["bisherige_reihen"]):
            m = re.search(r":\s*([^:?]+\?)", eintrag)
            if m:
                fragen.append(m.group(1).strip())
    return list(dict.fromkeys(fragen))


def woerter(s: struktur.Struktur | None) -> str:
    """Alle Texte der Struktur (für die Prüfung „keine Namen aus dem Fall“ in faelle.fallwoerter)."""
    if s is None:
        return ""
    teile = []
    for r in s.reihen:
        teile += [r[f] for f in ("fach", "klasse", "titel", "reihenfrage", "lerngruppe", "notizen")]
        teile += r["behandelt"] + r["merksaetze"] + r["bisherige_reihen"]
        teile += [st["thema"] for st in r["stunden"] + r["ausgeblendete_stunden"]]
    return "\n".join(t for t in teile if t)
