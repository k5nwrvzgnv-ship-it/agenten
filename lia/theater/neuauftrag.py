"""Neue Aufträge aus Lias Web-App (quelle portal-theater, Plan Jan 30.10.2026, board-plan.md Punkt 8).

- „Spielfassung: …“: eine ganze Runde wie runde.py (Szenenkarte, Ablauf mit Prüfschritt, Spielfassung, Stück im
  Stück), mit Lias Länge, Spieler*innen und was bleiben muss (wunsch.py). Die vier docx gehen direkt an Lia,
  an_lia.json verknüpft die Runde mit dem Auftrag (Lias Rückmeldungen finden sie so, nachbesserung.runde_finden).
  Nur für das Stück aus theater.toml: Für ein anderes gibt es keinen Text (NeuesStueck, Jan kümmert sich).
- „Szenenaufgabe: …“: ein Arbeitsblatt für eine Gruppe, auf Grundlage der Runde, die Lia zuletzt bekommen hat, und
  des Ablaufs, der dort gerade gilt. Ein Claude-Lauf (neue Sitzung), höchstens eine Nachbesserung.
Claude und Renderer kommen über nachbesserung.Umgebung herein.
"""

import json
import re
import time
from pathlib import Path

import aufgabe
import fassung
import karte
import nachbesserung
import runde
import stueck
import wunsch
from agentkit import textfassung

AUFTRAG_MUSTER = re.compile(r"\d{8}-\d{6}-")  # echte Auftrags-IDs (nicht „probe-…“)
BILD_ENDUNGEN = (".jpg", ".jpeg", ".png")
NEUES_STUECK_LIA = "Für dieses Stück habe ich den Text noch nicht. Jan kümmert sich darum."


class NeuesStueck(nachbesserung.NachbesserungFehler):
    """Spielfassung für ein Stück ohne Textfassung. Der Text ist für Jan."""


def spielfassung(auftrag: dict, u: nachbesserung.Umgebung) -> nachbesserung.Ergebnis:
    a = wunsch.spielfassung_angaben(auftrag["text"])
    titel = u.vorgaben["stueck"]["titel"]
    if not wunsch.stueck_passt(a["stueck"], titel):
        raise NeuesStueck(f"Spielfassung für „{a['stueck']}“ gewünscht, es gibt nur den Text von „{titel}“. Dafür "
                          "bräuchte es die Textfassung, eine Prüfung der Zerlegung (stueck.py) und eigene Vorgaben.")
    erg = nachbesserung.Ergebnis(text="", daten={})

    def laufen(prompt: str, sitzung: str | None = None):
        erg.laeufe += 1
        return u.laufen(prompt, sitzung)

    h = u.hier
    pfade = runde.Pfade(hier=h, vorgaben=h / "theater.toml", nachricht=h / "data" / "vorgaben" / "nachricht.md",
                        texte=h / "data" / "text", profil=h / "profil.toml")
    try:
        z = runde.runde(pfade, laufen=laufen, renderer_bauen=u.renderer_bauen, wunsch=a)
    except runde.RundenFehler as f:
        raise nachbesserung.NachbesserungFehler(f"Runde: {f}") from None
    ordner = Path(z["ordner"]).parent
    erg.dateien = [ordner / "fuer-lia" / name for name in runde.DOKUMENTE]
    (ordner / "an_lia.json").write_text(json.dumps(
        {"auftrag": auftrag["id"], "zeit": time.strftime("%Y-%m-%dT%H:%M:%S"),
         "dateien": [d.name for d in erg.dateien]}, ensure_ascii=False), encoding="utf-8")
    erg.text, erg.daten = runde.nachricht_an_lia(z, anfang="Hier ist deine neue Spielfassung.", pruefen="")
    erg.usd, erg.sitzung = z["usd"], z["sitzung"]
    erg.fuer_jan = runde.melden_text(z, an_lia_auftrag=auftrag["id"])
    return erg


def fruehere_szenenaufgabe(auftrag: dict, data: Path) -> Path | None:
    """Ordner der Szenenaufgabe, auf die sich der Auftrag bezieht (Lias Rückmeldung dazu), sonst None."""
    bezug = auftrag.get("bezug")
    treffer = sorted(data.glob(f"runde-*/szenenaufgabe-{bezug}")) if bezug else []
    return treffer[0] if treffer else None


def gilt_in(r: Path) -> Path:
    """Ablauf, der in Runde r gilt: Stand des letzten echten Auftrags (nachbesserung-<id>/stand.json), sonst der
    der Runde."""
    staende = [p for p in r.glob("nachbesserung-*/stand.json")
               if AUFTRAG_MUSTER.match(p.parent.name.removeprefix("nachbesserung-"))]
    if staende:
        letzter = max(staende, key=lambda p: p.parent.name)
        return r / json.loads(letzter.read_text(encoding="utf-8"))["ablauf"]
    return nachbesserung.ablauf_finden(r, None)


def aktuelle_runde(data: Path) -> Path:
    """Die Runde, die Lia zuletzt bekommen hat (an_lia.json, nach Zeit)."""
    zustellungen = []
    for merker in data.glob("runde-*/an_lia.json"):
        try:
            zustellungen.append((json.loads(merker.read_text(encoding="utf-8")).get("zeit") or "", merker.parent))
        except (OSError, json.JSONDecodeError):
            continue
    if not zustellungen:
        raise nachbesserung.NachbesserungFehler("Noch keine Runde an Lia geschickt, Szenenaufgabe braucht eine")
    return max(zustellungen)[1]


def anhaenge(hier: Path, dateien: list[str]) -> list[str]:
    """Zeilen für den Prompt; Office und PDF bekommen eine Textfassung daneben (agentkit.textfassung)."""
    zeilen = []
    for rel in dateien:
        pfad = hier / rel
        if pfad.suffix.lower() in BILD_ENDUNGEN:
            zeilen.append(f"{rel} (Bild, mit Read öffnen)")
            continue
        try:
            text = textfassung.als_text(pfad)
        except Exception as e:  # kaputte Datei: Claude arbeitet ohne, Lia sieht es im Blatt nicht
            zeilen.append(f"{rel} (Text nicht lesbar: {type(e).__name__})")
            continue
        if text:
            txt = pfad.with_name(pfad.name + ".txt")
            txt.write_text(text, encoding="utf-8")
            zeilen.append(f"{rel} (Textfassung: {txt.relative_to(hier)})")
        else:
            zeilen.append(f"{rel} (Format ohne Textfassung, versuche Read)")
    return zeilen


def dateiname(titel: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", titel)
    return " ".join(name.split())[:80] or "Szenenaufgabe"


def szenenaufgabe(auftrag: dict, u: nachbesserung.Umgebung, vorher: Path | None = None) -> nachbesserung.Ergebnis:
    """vorher: Ordner einer früheren Szenenaufgabe, zu der Lia zurückmeldet (Überarbeitung in derselben Runde)."""
    r = vorher.parent if vorher else aktuelle_runde(u.hier / "data")
    ablauf_pfad = gilt_in(r)
    einheiten = stueck.aus_dicts(json.loads((r / "einheiten.json").read_text(encoding="utf-8")))
    nach_nr = {e.nr: e for e in einheiten}
    try:
        ablauf = karte.antwort_lesen(ablauf_pfad)
    except karte.AntwortFehler as e:
        raise nachbesserung.NachbesserungFehler(f"Ablauf der Runde {r.name}: {e}") from None
    ordner = r / f"szenenaufgabe-{auftrag['id']}"
    ordner.mkdir(exist_ok=True)
    ausgabe = ordner / "aufgabe.json"
    ausgabe.unlink(missing_ok=True)  # Rest eines abgebrochenen Laufs zählt nicht
    fassung.schreiben_text(ordner / "spielfassung.txt", ablauf, einheiten)
    rel = lambda p: str(p.relative_to(u.hier))  # noqa: E731
    kontext = r / "kontext"
    erg = nachbesserung.Ergebnis(text="", daten={})

    def lauf(text: str, sitzung: str | None):
        x = u.laufen(text, sitzung)
        erg.usd += x.usd or 0
        erg.laeufe += 1
        return x

    alt = sorted((vorher / "fuer-lia").glob("*.json")) if vorher else []
    x = lauf(aufgabe.szenen_prompt(
        rel(ausgabe), auftrag["text"], rel(kontext / "vorgaben.md"), rel(kontext / "grundlagen.md"),
        [rel(p) for p in sorted(kontext.glob("stueck-teil-*.txt"))], aufgabe.ablauf_kurz(ablauf),
        rel(ordner / "spielfassung.txt"), anhaenge(u.hier, auftrag.get("dateien") or []), aufgabe.format_abschnitte(),
        [rel(p) for p in sorted(kontext.glob("buch-teil-*.md"))], rel(alt[0]) if alt else None), None)
    erg.sitzung = x.sitzung

    def lesen() -> tuple[dict, list[str]]:
        try:
            d = karte.antwort_lesen(ausgabe)
        except karte.AntwortFehler as e:
            return {}, [str(e)]
        f = aufgabe.szenen_pruefen(d, len(einheiten))
        return d, f or aufgabe.pruefen(aufgabe.mit_text(d, lambda s: fassung._originalbloecke({"stellen": s}, nach_nr)))

    daten, fehler = lesen()
    if fehler:
        x = lauf(karte.nachbesserung_prompt(fehler, rel(ausgabe)), erg.sitzung)
        erg.sitzung = x.sitzung or erg.sitzung
        daten, fehler = lesen()
        if fehler:
            raise nachbesserung.NachbesserungFehler(f"Szenenaufgabe nach Nachbesserung noch fehlerhaft: "
                                                    f"{'; '.join(fehler)}")
    blatt = aufgabe.mit_text(daten, lambda s: fassung._originalbloecke({"stellen": s}, nach_nr))
    ziel = ordner / "fuer-lia"
    ziel.mkdir(exist_ok=True)
    docx = ziel / f"{dateiname(blatt['titel'])}.docx"
    docx.with_suffix(".json").write_text(json.dumps(blatt, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        u.renderer_bauen(blatt, docx, profil=u.profil)
    except ValueError as e:  # BeschreibungUngueltig ist ein ValueError
        raise nachbesserung.NachbesserungFehler(f"Renderer lehnt die Szenenaufgabe ab: {e}") from None
    erg.dateien = [docx]
    kern = "Hier ist die Szenenaufgabe für deine Gruppe."
    pruefen = "Passt sie so? Antworte einfach auf diese Nachricht."
    erg.text, erg.daten = f"{kern}\n{pruefen}", {"kern": kern, "punkte": [], "pruefen": pruefen}
    return erg


def bearbeiten(auftrag: dict, u: nachbesserung.Umgebung) -> nachbesserung.Ergebnis:
    """Nach Art des Auftrags (wunsch.art): Spielfassung, Szenenaufgabe oder Nachbesserung wie bisher; Lias
    Rückmeldung zu einer Szenenaufgabe überarbeitet diese."""
    vorher = fruehere_szenenaufgabe(auftrag, u.hier / "data")
    if vorher:
        return szenenaufgabe(auftrag, u, vorher)
    art = wunsch.art(auftrag)
    if art == "spielfassung":
        return spielfassung(auftrag, u)
    if art == "szenenaufgabe":
        return szenenaufgabe(auftrag, u)
    return nachbesserung.bearbeiten(auftrag, u)
