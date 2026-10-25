"""Runde 1: drei Grobskizzen einer Unterrichtsreihe (Prompt, Prüfung der Antwort, Darstellung).

Plan Examensreihe, Schritt 3 (Jan 25.10.2026): drei Skizzen je eine Seite mit verschiedener didaktischer
Grundentscheidung, rückwärts geplant ab der Abschlussaufgabe, je mit Reihenfrage und RLP-Bezug. Claude schreibt
die Skizzen als JSON, Python prüft alles Prüfbare (RLP-ids, Quellenverweise, Stundenzahl, Perspektiven, Länge).
Zitate schreibt Claude nicht: Quellen nur als Verweis auf das Register von lia/recherche ("<quelle>:<seite>").
Allgemein gehalten: Die Reihe kommt aus examen.toml und reihen.toml, nichts ist auf Straftheorien festgelegt.
"""

import json
import re
from pathlib import Path

KENNUNGEN = ("A", "B", "C")
# Erlaubte Abkürzungen (Jan 25.10.2026: Skizzen müssen ohne Vorwissen lesbar sein). Andere Großbuchstaben-Kürzel
# lehnt die Prüfung ab; die Kurzfassung erklärt die verwendeten.
GLOSSAR = {
    "AFB": "Anforderungsbereich: I wiedergeben, II anwenden, III beurteilen",
    "BBB": "Behauptung, Begründung, Beispiel (Lias Schema für ein Argument)",
    "LEK": "Lernerfolgskontrolle (benotete Überprüfung)",
    "RLP": "Rahmenlehrplan",
    "StGB": "Strafgesetzbuch",
    "JGG": "Jugendgerichtsgesetz",
    "ISS": "Integrierte Sekundarschule",
    "UB": "Unterrichtsbesuch",
    "OCR": "Texterkennung aus einem Scan",
    "Doku": "Dokumentarfilm",
}
_KUERZEL = re.compile(r"\b[A-ZÄÖÜ]{2,}\b")
_ROEMISCH = {"II", "III", "IV"}
FALL_MAX = 600  # Zeichen für fall und abschlussfall (zwei bis drei Sätze)
PERSPEKTIVEN = ("individuell", "gesellschaftlich", "ideengeschichtlich")
STUNDEN_ANNAHME = (8, 10)  # solange Lia die Stundenzahl nicht genannt hat
MAX_ZEICHEN = 3000  # Text je Skizze (ohne Darstellung), entspricht etwa einer Seite
TEXTFELDER = ("titel", "grundentscheidung", "reihenfrage", "abschlussaufgabe", "differenzierung", "risiken")
STUNDENFELDER = ("thema", "ziel", "perspektive")


class SkizzenFehler(Exception):
    """Antwort fehlt oder ist kein JSON. Der Text ist für Jan."""


def quellen_aus_register(register: dict) -> dict[str, list[dict]]:
    """Verweis "<quelle>:<seite>" -> Stellen, nur aus verwendbaren Quellen."""
    verweise: dict[str, list[dict]] = {}
    for q in register.get("quellen", []):
        if not q.get("gemeinfreiheit", {}).get("verwendbar"):
            continue
        for s in q.get("stellen", []):
            eintrag = {"werk": q["werk"], "zitat": s["zitat"], "position": s.get("position") or "",
                       "am_scan_pruefen": bool(s.get("am_scan_pruefen"))}
            verweise.setdefault(f"{q['id']}:{s['seite']}", []).append(eintrag)
    return verweise


def stundenzahl(examen: dict) -> int | None:
    """Stundenzahl aus examen.toml, None solange offen."""
    wert = str(examen.get("pruefung", {}).get("stundenzahl", "")).strip()
    return int(wert) if wert.isdigit() else None


def pruefungsstunde(examen: dict) -> int | None:
    wert = str(examen.get("pruefung", {}).get("pruefungsstunde_in_reihe", "")).strip()
    return int(wert) if wert.isdigit() else None


def _stundenvorgabe(examen: dict) -> str:
    n = stundenzahl(examen)
    if n:
        return f"genau {n} Stunden"
    von, bis = STUNDEN_ANNAHME
    return f"{von} bis {bis} Stunden (Lia hat die Zahl noch nicht genannt; deine Wahl unter annahmen nennen)"


def kontext(rubrik: dict, rlp: list[dict], examen: dict, reihe: str, quellen: dict[str, list[dict]],
            regeln: str, leitfaden: str) -> str:
    """Alles, was Skizzen- und Prüfer-Lauf über die Reihe wissen müssen, als Textblock."""
    teile = ["# Reihe (aus Lias Reihenkontext)", reihe.strip()]
    pr = examen.get("pruefung", {})
    teile += ["", "# Prüfung", *(f"- {k}: {v}" for k, v in pr.items() if str(v).strip())]
    r = examen.get("reihe", {})
    if r.get("reihenfrage_kandidaten"):
        teile += ["", "# Kandidaten für die Reihenfrage (Lia hat noch nicht entschieden)",
                  *(f"- {k}" for k in r["reihenfrage_kandidaten"])]
    if r.get("anregungen"):
        teile += ["", "# Anregungen aus Lias Material (keine Vorgaben)", *(f"- {a}" for a in r["anregungen"])]
    teile += ["", "# RLP-Stellen (wörtlich, Verweis über id)"]
    teile += [f"- {s['id']}" + (f" [Stufe {s['stufe']}]" if s.get("stufe") else "") + f": {s['text']}" for s in rlp]
    teile += ["", "# Rubrik (danach wird jede Skizze bewertet; Schwelle: "
              f"„{rubrik['stufen']['mindestens']}“)"]
    teile += [f"- {k['id']} – {k['name']}: {k['gut']}" for k in rubrik["kriterium"]]
    teile += ["", "# Quellen (nur diese Verweise verwenden, Form <quelle>:<seite>)"]
    for ref, stellen in quellen.items():
        for s in stellen:
            scan = " (OCR-Quelle, Lia prüft am Scan)" if s["am_scan_pruefen"] else ""
            teile.append(f"- {ref} | {s['werk']} | {s['position']}{scan} | {s['zitat']}")
    teile += ["", "# Lias Regeln (von ihr freigegeben)", regeln.strip() or "(keine)"]
    teile += ["", "# So unterrichtet Lia (Leitfaden)", leitfaden.strip() or "(keiner)"]
    return "\n".join(teile)


def prompt(kontext_text: str, ausgabe: str, examen: dict) -> str:
    ps = pruefungsstunde(examen)
    ps_text = (f"Die Prüfungsstunde ist Stunde {ps}; markiere sie mit pruefungsstunde = true."
               if ps else "Markiere genau eine Stunde als pruefungsstunde = true (die, die sich am besten "
               "für eine Prüfungsstunde eignet) und begründe die Wahl unter annahmen.")
    return f"""Du entwirfst drei Grobskizzen für eine Unterrichtsreihe von Lia (Referendarin, Ethik). Es sind
Varianten zur Auswahl: Lia wählt eine Richtung, die dann vertieft wird. Jede Skizze passt auf eine Seite.

{kontext_text}

# Auftrag
1. Drei Skizzen A, B, C mit jeweils einer anderen didaktischen Grundentscheidung (z. B. Reihenfolge der
   Positionen, Einstieg über Fall oder Text, Art der Abschlussaufgabe, Gewichtung der Perspektiven). Die
   Unterschiede sollen echt sein, nicht nur andere Wörter. Nenne die Grundentscheidung in einem bis zwei Sätzen.
2. Plane rückwärts: zuerst die Abschlussaufgabe (was die Schülerinnen und Schüler am Ende können und zeigen),
   dann die Stunden, die dahin führen.
3. Je Skizze eine Reihenfrage (offene ethische Problemfrage, für die Lerngruppe verständlich) und 2 bis 4
   RLP-ids aus der Liste oben, die zur Abschlussaufgabe passen.
4. {_stundenvorgabe(examen)} je Skizze. Je Stunde: nr, thema, ziel (mit Operator), perspektive
   (individuell, gesellschaftlich oder ideengeschichtlich), quellen (Liste von Verweisen <quelle>:<seite>
   aus der Liste oben, darf leer sein), pruefungsstunde (true/false). Alle drei Perspektiven müssen vorkommen.
   {ps_text}
5. differenzierung: wie alle am selben Inhalt arbeiten (Lias Regel: drei Niveaus). risiken: was an dieser
   Variante schiefgehen kann, ehrlich.
6. Jede Skizze muss ohne Vorwissen verständlich sein, auch für jemanden außerhalb der Schule:
   - fall: der Fall, mit dem die Reihe arbeitet, in zwei bis drei ganzen Sätzen (wer, was passiert ist, welche
     Entscheidung offen ist). Jede Person, die in der Skizze vorkommt, wird hier eingeführt.
   - abschlussfall: ebenso der Fall der Abschlussaufgabe.
   - material_fehlt: alles, was Lia noch erstellen oder suchen muss (Audio, Video, Film, vereinfachte Texte,
     Rollenkarten, Statistiken …), je Eintrag mit Stunde. Nichts so schreiben, als gäbe es es schon.
   - Abkürzungen nur diese: {", ".join(GLOSSAR)}. Alles andere ausschreiben.
7. Keine Zitate schreiben, nur Verweise. Nichts erfinden: Was du über eine Position sagst, muss zu den Quellen
   passen; was du annimmst, steht unter annahmen. annahmen kurz: je Annahme ein bis zwei Sätze.

# Ausgabe
Schreibe mit Write genau diese Datei: {ausgabe}
Nur JSON, kein weiterer Text:
{{"annahmen": ["..."], "skizzen": [{{"kennung": "A", "titel": "...", "grundentscheidung": "...",
"fall": "...", "reihenfrage": "...", "abschlussaufgabe": "...", "abschlussfall": "...", "rlp": ["id", "..."],
"stunden": [{{"nr": 1, "thema": "...", "ziel": "...", "perspektive": "individuell", "quellen": [],
"pruefungsstunde": false}}], "differenzierung": "...", "risiken": "...",
"material_fehlt": ["Stunde 1: ..."]}}]}}
Deine letzte Antwort ist ein Satz: welche drei Grundentscheidungen du gewählt hast."""


def nachbesserung_prompt(fehler: list[str], ausgabe: str) -> str:
    return ("Die Prüfung deiner Datei hat Fehler gefunden. Verbessere genau diese Punkte und schreibe die "
            f"ganze Datei {ausgabe} neu (gleiches Format):\n" + "\n".join(f"- {f}" for f in fehler))


def antwort_lesen(pfad: Path) -> dict:
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SkizzenFehler(f"Claude hat {Path(pfad).name} nicht geschrieben") from None
    except json.JSONDecodeError as e:
        raise SkizzenFehler(f"{Path(pfad).name} ist kein JSON: {e}") from None
    if not isinstance(daten, dict):
        raise SkizzenFehler(f"{Path(pfad).name}: erwartet ein Objekt mit annahmen und skizzen")
    return daten


def _textlaenge(sk: dict) -> int:
    teile = [str(sk.get(f, "")) for f in TEXTFELDER]
    for st in sk.get("stunden", []) if isinstance(sk.get("stunden"), list) else []:
        teile += [str(st.get("thema", "")), str(st.get("ziel", ""))]
    return sum(len(t) for t in teile)


def _stunden_pruefen(k: str, stunden, n: int | None, ps: int | None, refs: set[str]) -> list[str]:
    if not isinstance(stunden, list) or not stunden:
        return [f"Skizze {k}: stunden fehlen"]
    fehler = []
    von, bis = (n, n) if n else STUNDEN_ANNAHME
    if not von <= len(stunden) <= bis:
        fehler.append(f"Skizze {k}: {len(stunden)} Stunden, erwartet {von}" + (f" bis {bis}" if bis != von else ""))
    if [st.get("nr") for st in stunden] != list(range(1, len(stunden) + 1)):
        fehler.append(f"Skizze {k}: Stunden nicht fortlaufend ab 1 nummeriert")
    for st in stunden:
        nr = st.get("nr")
        for feld in STUNDENFELDER:
            if not str(st.get(feld, "")).strip():
                fehler.append(f"Skizze {k}, Stunde {nr}: {feld} fehlt")
        if st.get("perspektive") and st["perspektive"] not in PERSPEKTIVEN:
            fehler.append(f"Skizze {k}, Stunde {nr}: perspektive {st['perspektive']!r} unbekannt")
        for ref in st.get("quellen", []) or []:
            if ref not in refs:
                fehler.append(f"Skizze {k}, Stunde {nr}: Quellenverweis {ref!r} steht nicht im Register")
    fehlend = [p for p in PERSPEKTIVEN if p not in {st.get("perspektive") for st in stunden}]
    if fehlend:
        fehler.append(f"Skizze {k}: Perspektive fehlt ({', '.join(fehlend)}), der RLP verlangt alle drei")
    markiert = [st.get("nr") for st in stunden if st.get("pruefungsstunde") is True]
    if ps and markiert != [ps]:
        fehler.append(f"Skizze {k}: Prüfungsstunde muss Stunde {ps} sein, markiert: {markiert}")
    elif not ps and len(markiert) != 1:
        fehler.append(f"Skizze {k}: genau eine Stunde als pruefungsstunde markieren, markiert: {markiert}")
    return fehler


def _alle_texte(wert) -> list[str]:
    if isinstance(wert, str):
        return [wert]
    if isinstance(wert, dict):
        return [t for v in wert.values() for t in _alle_texte(v)]
    if isinstance(wert, list):
        return [t for v in wert for t in _alle_texte(v)]
    return []


def fremde_kuerzel(texte: list[str]) -> list[str]:
    """Großbuchstaben-Kürzel, die nicht im GLOSSAR stehen (römische Zahlen erlaubt)."""
    return sorted({k for t in texte for k in _KUERZEL.findall(t)} - set(GLOSSAR) - _ROEMISCH)


def _erklaerung_pruefen(k: str, sk: dict) -> list[str]:
    """Fall, Abschlussfall und fehlendes Material müssen da sein, Abkürzungen nur aus dem GLOSSAR."""
    fehler = []
    for feld in ("fall", "abschlussfall"):
        text = str(sk.get(feld, "")).strip()
        if not text:
            fehler.append(f"Skizze {k}: {feld} fehlt (zwei bis drei Sätze, die den Fall erklären)")
        elif len(text) > FALL_MAX:
            fehler.append(f"Skizze {k}: {feld} hat {len(text)} Zeichen, höchstens {FALL_MAX}")
    mf = sk.get("material_fehlt")
    if not isinstance(mf, list) or not all(isinstance(m, str) and m.strip() for m in mf):
        fehler.append(f"Skizze {k}: material_fehlt muss eine Liste von Texten sein (leer, wenn nichts fehlt)")
    fremd = fremde_kuerzel(_alle_texte({f: v for f, v in sk.items() if f not in ("kennung", "rlp", "stunden")})
                           + _alle_texte([{f: v for f, v in st.items() if f != "quellen"}
                                          for st in sk.get("stunden") or [] if isinstance(st, dict)]))
    if fremd:
        fehler.append(f"Skizze {k}: Abkürzungen ausschreiben oder nur erlaubte verwenden: {', '.join(fremd)}")
    return fehler


def pruefen(daten: dict, rlp_ids: set[str], refs: set[str], examen: dict) -> list[str]:
    """Fehlerliste (leer = in Ordnung). Prüft nur, was Python sicher prüfen kann, nicht die Didaktik."""
    fehler = []
    skizzen = daten.get("skizzen")
    if not isinstance(skizzen, list):
        return ["skizzen fehlt oder ist keine Liste"]
    if [s.get("kennung") for s in skizzen] != list(KENNUNGEN):
        fehler.append(f"Erwartet genau drei Skizzen mit kennung A, B, C, gefunden: {[s.get('kennung') for s in skizzen]}")
    n, ps = stundenzahl(examen), pruefungsstunde(examen)
    if not n and not daten.get("annahmen"):
        fehler.append("annahmen fehlt: Stundenzahl ist offen, deine Annahme muss dort stehen")
    for sk in skizzen:
        k = sk.get("kennung", "?")
        for feld in TEXTFELDER:
            if not str(sk.get(feld, "")).strip():
                fehler.append(f"Skizze {k}: {feld} fehlt")
        rlp = sk.get("rlp")
        if not isinstance(rlp, list) or not 2 <= len(rlp) <= 4:
            fehler.append(f"Skizze {k}: 2 bis 4 RLP-ids erwartet")
        else:
            fehler += [f"Skizze {k}: RLP-id {r!r} gibt es nicht" for r in rlp if r not in rlp_ids]
        fehler += _stunden_pruefen(k, sk.get("stunden"), n, ps, refs)
        fehler += _erklaerung_pruefen(k, sk)
        laenge = _textlaenge(sk)
        if laenge > MAX_ZEICHEN:
            fehler.append(f"Skizze {k}: {laenge} Zeichen, höchstens {MAX_ZEICHEN} (eine Seite), bitte kürzen")
    return fehler


def darstellen(sk: dict, rlp: dict[str, dict], quellen: dict[str, list[dict]]) -> str:
    """Eine Skizze als Markdown (für Lia lesbar, eine Seite plus Quellenanhang)."""
    zeilen = [f"## Skizze {sk['kennung']}: {sk['titel']}", "",
              f"**Grundentscheidung:** {sk['grundentscheidung']}", ""]
    if sk.get("fall"):
        zeilen += [f"**Fall:** {sk['fall']}", ""]
    zeilen += [f"**Reihenfrage:** {sk['reihenfrage']}", "",
               f"**Abschlussaufgabe:** {sk['abschlussaufgabe']}", ""]
    if sk.get("abschlussfall"):
        zeilen += [f"**Fall der Abschlussaufgabe:** {sk['abschlussfall']}", ""]
    zeilen += [
              "**RLP:** " + "; ".join(
                  f"{r} ({rlp[r].get('stufe') or rlp[r]['abschnitt']})" for r in sk["rlp"] if r in rlp), "",
              "| Nr. | Thema | Ziel | Perspektive | Quellen |", "|---|---|---|---|---|"]
    for st in sk["stunden"]:
        nr = f"**{st['nr']} (Prüfung)**" if st.get("pruefungsstunde") else str(st["nr"])
        zeilen.append(f"| {nr} | {st['thema']} | {st['ziel']} | {st['perspektive']} | "
                      f"{', '.join(st.get('quellen') or []) or '–'} |")
    zeilen += ["", f"**Differenzierung:** {sk['differenzierung']}", "", f"**Risiken:** {sk['risiken']}"]
    if sk.get("material_fehlt"):
        zeilen += ["", "**Gibt es noch nicht (erstellen oder suchen):**", *(f"- {m}" for m in sk["material_fehlt"])]
    refs = sorted({r for st in sk["stunden"] for r in st.get("quellen") or []})
    if refs:
        zeilen += ["", "**Quellen (wörtlich aus dem Register):**"]
        for ref in refs:
            for s in quellen.get(ref, []):
                scan = " *(am Scan prüfen)*" if s["am_scan_pruefen"] else ""
                zeilen.append(f"- {ref}, {s['werk']}: „{s['zitat']}“{scan}")
    return "\n".join(zeilen)
