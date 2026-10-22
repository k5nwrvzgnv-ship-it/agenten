"""Material auf Zuruf (Skill einzelmaterial): Claude beschreibt, der Renderer baut.

Ablauf je Auftrag (bearbeiten):
1. Claude bekommt Lias Wunsch, den Skill (skills/einzelmaterial/SKILL.md) und die passenden Abschnitte aus
   shared/renderer/FORMAT.md und schreibt die Beschreibung nach data/arbeit/<auftrag>/beschreibung.json.
2. Python baut die Datei mit dem Renderer. Ist die Beschreibung ungültig, bekommt Claude die Fehler in
   derselben Sitzung zurück (höchstens MAX_KORREKTUREN Mal).
3. Claude prüft Kontrolltext und Vorschaubilder. Ändert Claude dabei die Beschreibung, baut Python neu
   (eine Kontrollrunde). Claudes letzte Antwort ist der Begleittext an Lia.

Claude und der Renderer werden übergeben (laufen, bauen), damit die Logik ohne Netz testbar ist.
"""

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from renderer import BeschreibungUngueltig

SKILL = "einzelmaterial"
SKILL_VERSION = 1
SKILL_DATEI = Path(__file__).resolve().parent / "skills" / SKILL / "SKILL.md"
FORMAT_DATEI = Path(__file__).resolve().parents[2] / "shared" / "renderer" / "FORMAT.md"
ARTEN = {"arbeitsblatt": ".docx", "folien": ".pptx"}
# Abschnitte aus FORMAT.md, die Claude bekommt (Überschriften "## ..."), dazu immer der Text davor
ABSCHNITTE = ("Allgemein", "Arbeitsblatt", "Folien")
MAX_KORREKTUREN = 3
# Danach kein neuer Claude-Lauf mehr; der Dienst bricht nach 25 Minuten ab (TimeoutStartSec)
ZEIT_BUDGET_S = 18 * 60
STANDARD_BEGLEITTEXT = "Hier ist dein Material."


class MaterialFehler(Exception):
    """Es ist kein Material entstanden. Der Text ist für Jan (Ursache), nicht für Lia."""


class _Korrektur(Exception):
    """Fehler in Claudes Beschreibung, geht an Claude zurück."""


@dataclass
class Fertig:
    datei: Path
    begleittext: str
    sitzung: str | None
    laeufe: int
    usd: float
    tokens: int
    hinweise: list[str]


def format_abschnitte(text: str) -> str:
    """Einleitung und die Abschnitte aus ABSCHNITTE aus FORMAT.md (andere Arten bekommt Claude nicht zu sehen)."""
    teile = re.split(r"^(?=## )", text, flags=re.M)
    behalten = [teile[0]]
    for name in ABSCHNITTE:
        treffer = [t for t in teile[1:] if t.startswith(f"## {name}")]
        if not treffer:
            raise ValueError(f"FORMAT.md: Abschnitt '## {name}' fehlt")
        behalten += treffer
    return "".join(behalten).strip()


def dateiname(beschreibung: dict) -> str:
    """z. B. 'Arbeitsblatt Kategorischer Imperativ.docx' (Titel gekürzt, ohne Sonderzeichen)."""
    art = beschreibung["art"]
    titel = re.sub(r"[^\w\s-]", "", beschreibung.get("titel", ""))
    titel = re.sub(r"\s+", " ", titel).strip()
    if len(titel) > 60:  # am Wortende kürzen
        titel = titel[:61].rsplit(" ", 1)[0] if " " in titel[:61] else titel[:60]
    return f"{art.capitalize()} {titel}".strip() + ARTEN[art]


def _beschreibung_lesen(pfad: Path, rel: str) -> dict:
    if not pfad.exists():
        raise _Korrektur(f"Die Datei {rel} fehlt. Schreibe die Beschreibung mit Write genau dorthin.")
    try:
        beschreibung = json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise _Korrektur(f"{rel} ist kein gültiges JSON: {e}") from None
    if not isinstance(beschreibung, dict) or beschreibung.get("art") not in ARTEN:
        raise _Korrektur(f"art: muss \"arbeitsblatt\" oder \"folien\" sein, ist {beschreibung.get('art')!r}"
                         if isinstance(beschreibung, dict) else "Die Beschreibung muss ein JSON-Objekt sein.")
    return beschreibung


def prompt_start(wunsch: str, fach: str, rel: str, skill: str, format_text: str) -> str:
    return f"""Lia unterrichtet {fach} und wünscht sich Material. Ihr Wunsch:
---
{wunsch}
---

{skill}

## So lieferst du das Material
- Schreibe die Beschreibung als JSON mit dem Werkzeug Write in die Datei {rel}. Schreibe keine anderen Dateien.
- Python baut daraus die Datei. Ist etwas ungültig, bekommst du die Fehler zurück.
- Deine letzte Antwort geht wörtlich an Lia: zwei bis vier Sätze, was das Material enthält und worauf sie achten
  sollte (z. B. Annahmen zu Klasse oder Dauer). Reiner Text ohne Markdown, ohne Dateinamen oder Technik.

{format_text}"""


def prompt_korrektur(rel: str, fehler: str) -> str:
    return (f"Die Beschreibung in {rel} ist noch nicht gültig:\n{fehler}\n\n"
            "Korrigiere alle genannten Stellen und schreibe die vollständige Beschreibung neu in dieselbe Datei. "
            "Antworte danach wieder nur mit dem Begleittext für Lia.")


def prompt_kontrolle(rel: str, kontrolltext: str, bilder: list[str], hinweise: list[str]) -> str:
    if bilder:
        vorschau = ("Vorschaubilder, je Seite bzw. Folie ein PNG. Öffne jedes mit Read:\n"
                    + "\n".join(f"- {b}" for b in bilder)
                    + "\nDie Vorschau nutzt Ersatzschriften, leicht andere Zeilenumbrüche sind normal.")
    else:
        vorschau = f"Vorschaubilder gibt es diesmal nicht ({'; '.join(hinweise)}). Prüfe den Kontrolltext."
    return f"""Die Datei ist gebaut. Prüfe sie, bevor sie an Lia geht.

Kontrolltext (Inhalt in Lesereihenfolge):
---
{kontrolltext}
---

{vorschau}

Achte auf abgeschnittenen oder überlappenden Text, überfüllte oder fast leere Seiten und Folien, Tippfehler,
fachliche Fehler und ob alles zu Lias Wunsch passt (Klasse, Dauer, Thema).
Passt alles, ändere nichts. Sonst schreibe die vollständige, verbesserte Beschreibung neu nach {rel}.
Antworte am Ende wieder nur mit dem Begleittext für Lia."""


def bearbeiten(
    auftrag: dict,
    hier: Path,
    profil: dict,
    laufen: Callable,
    bauen: Callable,
    uhr: Callable[[], float] = time.monotonic,
) -> Fertig:
    """Erstellt das Material zu einem Auftrag. laufen(prompt, sitzung) -> claude_lauf.Ergebnis,
    bauen(beschreibung, ziel, profil=...) -> renderer.Ergebnis. MaterialFehler, wenn nichts entsteht;
    Fehler von claude_lauf (z. B. LimitErreicht) gehen unverändert weiter."""
    ordner = hier / "data" / "arbeit" / auftrag["id"]
    ordner.mkdir(parents=True, exist_ok=True)
    json_pfad = ordner / "beschreibung.json"
    rel = str(json_pfad.relative_to(hier))
    start = uhr()
    laeufe = []

    def claude(prompt: str, sitzung: str | None = None):
        if laeufe and uhr() - start > ZEIT_BUDGET_S:
            raise MaterialFehler(f"Zeitbudget ({ZEIT_BUDGET_S // 60} min) nach {len(laeufe)} Läufen überschritten")
        e = laufen(prompt, sitzung)
        laeufe.append(e)
        if not e.ok:
            raise MaterialFehler(f"Claude-Lauf {len(laeufe)} fehlgeschlagen: {e.text[:500]}")
        return e

    def bauen_mit_korrektur(e):
        for runde in range(MAX_KORREKTUREN + 1):
            try:
                beschreibung = _beschreibung_lesen(json_pfad, rel)
                try:
                    return bauen(beschreibung, ordner / dateiname(beschreibung), profil=profil), e
                except BeschreibungUngueltig as f:
                    raise _Korrektur(str(f)) from None
            except _Korrektur as f:
                if runde == MAX_KORREKTUREN:
                    raise MaterialFehler(f"Beschreibung nach {MAX_KORREKTUREN} Korrekturen ungültig: {f}") from None
                e = claude(prompt_korrektur(rel, str(f)), e.sitzung)
        raise AssertionError("nicht erreichbar")

    skill = SKILL_DATEI.read_text(encoding="utf-8")
    format_text = format_abschnitte(FORMAT_DATEI.read_text(encoding="utf-8"))
    e = claude(prompt_start(auftrag["text"], profil.get("fach") or "an einer Schule", rel, skill, format_text))
    ergebnis, e = bauen_mit_korrektur(e)

    stand = json_pfad.read_bytes()
    bilder = [str(Path(b).relative_to(hier)) if Path(b).is_relative_to(hier) else str(b) for b in ergebnis.bilder]
    e = claude(prompt_kontrolle(rel, ergebnis.kontrolltext, bilder, ergebnis.hinweise), e.sitzung)
    if json_pfad.read_bytes() != stand:
        ergebnis, e = bauen_mit_korrektur(e)

    return Fertig(
        datei=ergebnis.pfad,
        begleittext=e.text.strip() or STANDARD_BEGLEITTEXT,
        sitzung=e.sitzung,
        laeufe=len(laeufe),
        usd=sum(x.usd for x in laeufe),
        tokens=sum(x.tokens for x in laeufe),
        hinweise=list(ergebnis.hinweise),
    )
