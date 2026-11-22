"""Lernen im Arbeitsplatz (Nachtauftrag 22./23.11.2026, docs/befund-ux.md Abschnitt 5, S12): Prüfungsmodule finden
und die Seiten des Uni-Portals durchreichen.

Karten üben und mündliche Übungen bleiben im Uni-Portal (uni/portal, 127.0.0.1:8793, fsrs in uni/.venv). Seit
uni.meldro.de auf den Arbeitsplatz zeigt (19.11.2026), reicht der Arbeitsplatz `/modul/…` an das Portal weiter und
setzt sein eigenes Aussehen ein. Hier steht nur Logik ohne Netz; den Abruf macht app.py. Gelesen wird nur:
uni/portal/ablage.py (die Liste MODULE, per ast, ohne Import) und uni/data/lernen/<modul>/karten.json.
"""

import ast
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("arbeitsplatz")

# Nur diese Pfade gehen ans Portal; Bilder, Bewerten und Übungen liegen alle darunter
PFAD_MUSTER = re.compile(r"/modul/[a-z0-9][a-z0-9_-]{0,60}(/[A-Za-z0-9._-]{1,80}){0,4}")
# Kopfzeilen, die zum Portal gehen (Herkunftsprüfung des Portals braucht host, origin, sec-fetch-site)
ANFRAGE_KOPF = ("host", "origin", "sec-fetch-site", "content-type", "content-length", "accept")
# Kopfzeilen, die vom Portal zurückkommen; CSP und no-store setzt der Arbeitsplatz selbst
ANTWORT_KOPF = ("content-type", "location", "content-disposition", "last-modified")
MAX_KOERPER = 2 * 1024 * 1024  # Portal nimmt höchstens 1 MB Formular (Transkript), Rest Reserve
STILE = ('<link rel="stylesheet" href="/statisch/ruhig.css">\n<link rel="stylesheet" href="/statisch/arbeitsplatz.css">\n'
         '<link rel="stylesheet" href="/statisch/lernen.css">')


def portal_module(uni: Path) -> dict[str, str]:
    """Modul-ID -> Anzeigename aus uni/portal/ablage.py (MODULE = {...}); fehlt oder unlesbar: leer, im Log."""
    datei = uni / "portal" / "ablage.py"
    try:
        baum = ast.parse(datei.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as f:
        if datei.exists():
            logger.warning("Lernmodule nicht lesbar (%s): %s", datei, f)
        return {}
    for knoten in baum.body:
        if isinstance(knoten, ast.Assign) and any(isinstance(z, ast.Name) and z.id == "MODULE" for z in knoten.targets):
            try:
                wert = ast.literal_eval(knoten.value)
            except ValueError:
                logger.warning("MODULE in %s ist kein fester Wert", datei)
                return {}
            if isinstance(wert, dict):
                return {str(k): str(v) for k, v in wert.items() if isinstance(k, str) and PFAD_MUSTER.fullmatch(f"/modul/{k}")}
    return {}


def karten_zahl(uni: Path, modul: str) -> int | None:
    """Zahl der Karten eines Moduls (uni/data/lernen/<modul>/karten.json, Liste); fehlt oder kaputt: None."""
    try:
        karten = json.loads((uni / "data" / "lernen" / modul / "karten.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return len(karten) if isinstance(karten, list) else None


def module(uni: Path) -> list[dict]:
    """Prüfungsmodule mit Karten: {"id", "name", "karten", "link", "ueben"}. Nur Module, die das Portal kennt."""
    zeilen = []
    for mid, name in portal_module(uni).items():
        n = karten_zahl(uni, mid)
        if n is None:
            continue
        zeilen.append({"id": mid, "name": name, "karten": n, "link": f"/modul/{mid}", "ueben": f"/modul/{mid}/ueben"})
    return zeilen


def ort_des_moduls(modul: str, ort_ids: set[str]) -> str | None:
    """Ordner eines Moduls: „modul-<id>“ oder die ID selbst, sonst ein Ordner „modul-<id>-…“ (z. B. modul-holzschutz)."""
    for kandidat in (f"modul-{modul}", modul):
        if kandidat in ort_ids:
            return kandidat
    passend = sorted(o for o in ort_ids if o.startswith(f"modul-{modul}-"))
    return passend[0] if passend else None


def fuer_ort(mods: list[dict], ort_ids: set[str], unter: set[str]) -> list[dict]:
    """Module, deren Ordner in `unter` liegt (der Ordner selbst und alle darunter)."""
    return [m for m in mods if ort_des_moduls(m["id"], ort_ids) in unter]


def pfad_erlaubt(pfad: str) -> bool:
    return bool(PFAD_MUSTER.fullmatch(pfad)) and ".." not in pfad


def anfrage_kopf(kopf: dict[str, str]) -> dict[str, str]:
    """Kopfzeilen der Anfrage, die ans Portal gehen (Namen klein)."""
    return {k: v for k, v in kopf.items() if k.lower() in ANFRAGE_KOPF}


def antwort_kopf(kopf: list[tuple[str, str]]) -> dict[str, str]:
    """Kopfzeilen der Portal-Antwort, die zurück zum Browser gehen. Weiterleitungen bleiben auf /modul/…"""
    aus = {}
    for k, v in kopf:
        k = k.lower()
        if k not in ANTWORT_KOPF:
            continue
        if k == "location" and not (v.startswith("/modul/") and pfad_erlaubt(v.split("?")[0])):
            continue
        aus[k] = v
    return aus


_PROJEKT_ZEILE = re.compile(r'\s*<li><a class="baum-eintrag" href="/projekt/[^"]*"[^>]*>.*?</a></li>', re.S)


def html_umschreiben(html: str) -> str:
    """Portal-Seite im Aussehen des Arbeitsplatzes: ruhig.css statt stil.css, oben „Arbeitsplatz“ (führt nach Heute)
    statt „Uni“, ohne die alten Projektseiten des Portals (das Exposé steht im Arbeitsplatz am Ordner)."""
    html = html.replace('<link rel="stylesheet" href="/statisch/stil.css">', STILE)
    html = html.replace('<a class="baum-name" href="/">Uni</a>',
                        '<a class="baum-name" href="/">Arbeitsplatz</a>\n  <a class="baum-eintrag" href="/"><span>Heute</span></a>')
    html = re.sub(r"(<title>[^<]*?) · Uni</title>", r"\1 · Arbeitsplatz</title>", html)
    html = html.replace('<div class="rahmen">', '<div class="rahmen ohne-rechts lernen-seite">', 1)
    # Karten üben hat keine sichtbare Überschrift (die Frage ist der Inhalt): eine für Vorleser
    html = html.replace('<article class="lernkarte">', '<h1 class="unsichtbar">Karten üben</h1>\n<article class="lernkarte">', 1)
    return _PROJEKT_ZEILE.sub("", html)
