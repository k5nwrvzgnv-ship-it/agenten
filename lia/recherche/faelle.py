"""Fallsuche: reine Logik ohne Netz (Kontext, Prompts, Prüfung von Claudes Dateien, Dossier-Beschreibung).

Auftrag Jan/Lia vom 27.10.2026: offene, gründliche Suche nach starken realen Fällen für Lias Examensreihe
(Straftheorien, Klasse 8), laufend gegen regelwerk_reihe.md abgeglichen; daraus Problem- bzw. Leitfragen.
Ablauf und Claude-Läufe stehen in fallsuche.py. Drei Dateiformate (von Claude geschrieben, hier geprüft):

sammeln-<fenster>.json  {"kandidaten": [{"titel", "fall", "quelle_art", "belege": [{"url", "zitat"}],
                          "lebenswelt", "strafzweck", "gewalt": bool}],
                         "verworfen": [{"titel", "grund", "regeln": [...]}], "luecken": [...]}
abgleich.json           {"faelle": [{"id", "kriterien": {<kriterium>: {"stufe", "begruendung", "regeln"}},
                          "gefaehrdet": [...], "gesamt"}]}
dossier.json            {"auswahl": [{"id", "kurztitel", "warum", "achten"}], "leitfragen": [{"frage", "pole": [a, b],
                          "faelle", "einstieg", "kant", "liszt", "belege_register", "rlp", "regeln"}],
                         "auch_interessant": [{"ref": "F07" | "V03", "warum"}], "rueckfragen"}
Reihenfragen sind allgemein wie Lias eigene (Jan 27.10.2026): keine Namen, Orte oder Zahlen aus den Fällen.
"""

import json
import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

import webpruefung

QUELLE_ARTEN = ("reportage", "urteil", "social_media", "popkultur", "alltag", "sonstiges")
KRITERIEN = {  # Prüfkriterien je Fund (Auftrag 27.10.2026, regelwerk_reihe.md Abschnitt E)
    "lebenswelt": "Trifft er die Lebenswelt dieser Lerngruppe?",
    "passung": "Passt er präzise auf die Fragestellung der Reihe?",
    "regeln": "Ist er mit Rosenberger-Regeln, bisheriger Kritik und Lias Gelernten Regeln vereinbar?",
    "natuerlich": "Wirkt er natürlich oder konstruiert?",
    "tragweite": "Trägt er eine ganze Reihe bzw. lässt er sich anschlussfähig ausbauen?",
}
STUFEN = ("stark", "mittel", "schwach")
MAX_FALL = 800
MAX_BEGRUENDUNG = 600
MAX_FRAGE = 100
MAX_AUSWAHL = 6
MAX_INTERESSANT = 6
MAX_RUECKFRAGEN = 4
MAX_LIA = 400  # Texte für Lia im Dossier
MAX_ZITAT = 300

# Suchfenster: je eines ein eigener Claude-Lauf. Die Beispiele sind Suchrichtungen, keine Tatsachen.
FENSTER = {
    "nachrichten": ("Reportagen, Kommentare, Lokalnachrichten",
                    "Reportagen und Kommentare über reale Straftaten und Strafen, besonders mit Jugendlichen oder jungen "
                    "Erwachsenen, gern aus Berlin; Debatten, ob eine Strafe zu hart oder zu mild war."),
    "urteile": ("Gerichtsurteile und reale Verfahren",
                "Gerichtsurteile und Verfahren, über die berichtet wurde: Jugendstrafrecht, Strafmaß-Debatten, "
                "Bewährung oder Haft, Täter-Opfer-Ausgleich, Wiederholungstäter."),
    "social_media": ("Social Media und Netzphänomene",
                     "Social-Media-Phänomene mit Straftat und Strafe: Influencer vor Gericht, Challenges oder Pranks mit "
                     "strafrechtlichen Folgen, Online-Pranger und Selbstjustiz, Videos von Taten."),
    "popkultur": ("Popkultur, Musik, Sport, Gaming",
                  "Popkultur: Deutschrap (Haft, Prozesse, Comeback), Serien und Filme, Fußball (Spieler, Fans), "
                  "Gaming und Streaming, soweit dort echte Straftaten und Strafen verhandelt werden."),
    "lebenswelt": ("Alltag, Schule, Familie, Religion",
                   "Alltag der Lerngruppe: Strafen in Schule und Familie, Rache oder Strafe, Vergebung und Reue, Strafe "
                   "und Sünde in Religionen (Islam, Christentum; der RLP nennt das ausdrücklich), Nachbarschaft."),
}


class FallFehler(Exception):
    pass


def _text(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _json(pfad: Path) -> dict:
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FallFehler(f"{Path(pfad).name} fehlt oder ist kein JSON: {e}") from None
    if not isinstance(daten, dict):
        raise FallFehler(f"{Path(pfad).name}: Objekt erwartet")
    return daten


# --- Kontext ---------------------------------------------------------------------------------------------

def abschnitt(text: str, ueberschrift: str) -> str:
    """Text unter „## <ueberschrift>“ bis zur nächsten Überschrift gleicher Ebene."""
    drin, zeilen = False, []
    for zeile in text.splitlines():
        if zeile.startswith("## "):
            drin = zeile[3:].strip() == ueberschrift
            continue
        if drin:
            zeilen.append(zeile)
    return "\n".join(zeilen).strip()


def regeln_aus_regelwerk(text: str) -> dict[str, str]:
    """{"L1": "Text", ...} aus den Punkten „- <Kennung> Text“ (Folgezeilen eingerückt)."""
    regeln, aktuell = {}, None
    for zeile in text.splitlines():
        m = re.match(r"- ([A-Z]\d+) (.*)", zeile)
        if m:
            aktuell = m.group(1)
            regeln[aktuell] = m.group(2).strip()
        elif aktuell and zeile.startswith("  ") and zeile.strip():
            regeln[aktuell] += " " + zeile.strip()
        else:
            aktuell = None
    return regeln


def gelernte_regeln(status_text: str) -> dict[str, str]:
    """Lias Gelernte Regeln (lia/unterricht/STATUS.md) als {"GR1": "Text", ...}."""
    punkte = [z[2:].strip() for z in abschnitt(status_text, "Gelernte Regeln").splitlines() if z.startswith("- ")]
    return {f"GR{i}": p for i, p in enumerate(punkte, 1) if "noch keine" not in p}


def rlp_stellen(rlp_toml: str) -> dict[str, str]:
    return {s["id"]: f"{s.get('abschnitt', '')}: {s['text']}" for s in tomllib.loads(rlp_toml).get("stelle", [])}


def reihenfragen_lias(reihen_toml: str) -> list[str]:
    """Lias bisherige Reihenfragen aus reihen.toml (bisherige_reihen: „Klasse 7, Thema: Frage? Merksätze …“)."""
    fragen = []
    for r in tomllib.loads(reihen_toml).get("reihe", []):
        for eintrag in r.get("bisherige_reihen", []):
            m = re.search(r":\s*([^:?]+\?)", eintrag)
            if m:
                fragen.append(m.group(1).strip())
    return fragen


def _liste(d: dict[str, str]) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in d.items()) or "(keine)"


# --- Stufe 1: Sammeln ------------------------------------------------------------------------------------

def sammel_prompt(fenster: str, kontext: dict, domains: list[str], ausgabe: str) -> str:
    titel, richtung = FENSTER[fenster]
    return f"""Aufgabe: Suche im Web nach realen Fällen für eine Unterrichtsreihe. Suchfenster: {titel}.

WORUM ES GEHT
Lias Examensreihe Ethik, Klasse 8, Straftheorien: Wozu strafen wir? Kant (Strafe, weil Unrecht geschah,
Vergeltung) gegen von Liszt (Strafe, damit keine neue Tat folgt: Besserung, Abschreckung, Schutz; auch Haft).
Die Prüfungsstunde wendet von Liszt an. Gesucht sind besonders gute, nahrhafte Beispielfälle, aus denen sich
überzeugende Problem- bzw. Leitfragen entwickeln lassen. Lieber wenige sehr gute als viele mittelmäßige.
Es müssen keine Philosophen sein: Reportagen, Kommentare, Debatten, Social Media, Popkultur, Urteile und
Alltagssituationen sind ausdrücklich erwünscht. Philosophische Positionen kommen später in der Reihe dazu.

DIESES SUCHFENSTER: {richtung}
Das sind Suchrichtungen. Folge guten Spuren auch darüber hinaus. Suche gründlich und breit, mit vielen
verschiedenen Suchanfragen, nicht nur bei dem, was naheliegt.

REIHE UND LERNGRUPPE
{kontext['reihe']}

REGELWERK (laufender Abgleich, kein Suchfilter): Prüfe jeden Fund schon während der Suche grob dagegen.
Klare Fehlgriffe nimmst du nicht als Kandidaten, sondern unter "verworfen" mit Grund und Regel-Kennungen.
{kontext['regelwerk']}

LIAS GELERNTE REGELN (Kennung GR<n>):
{_liste(kontext['gelernte'])}

WERKZEUGE
- WebSearch ist frei. WebFetch funktioniert nur für diese Domains: {", ".join(domains)}
- Fälle von anderen Seiten darfst du aufnehmen; ihr Beleg gilt dann als ungeprüft. Suche wenn möglich eine
  zweite Quelle auf der Liste, die denselben Fall berichtet.
- Schreibe die Datei früh und ergänze sie laufend; dein Arbeitsschritt-Kontingent ist begrenzt.

REGELN FÜR DIE DATEI
- Nur reale Fälle, so wie berichtet. Nichts erfinden, nichts zurechtbiegen, keine Namen ergänzen.
- Jeder Kandidat braucht mindestens einen Beleg {{"url", "zitat"}}. Das Zitat steht Zeichen für Zeichen auf der
  Seite (höchstens {MAX_ZITAT} Zeichen). Python prüft das wörtlich. Keine Zusammenfassung als Zitat.
- "fall": was geschah, sachlich, höchstens {MAX_FALL} Zeichen, Alter und Strafe nennen, soweit berichtet.
- "lebenswelt": warum gerade diese Jugendlichen das packt (konkret, nicht allgemein).
- "strafzweck": welche Spannung zwischen Vergeltung und Zweck der Fall aufmacht.
- "gewalt": true, wenn die Tat Gewalt enthält (wird markiert, nicht verworfen; Tötung bleibt ausgeschlossen).
- "quelle_art": eines von {", ".join(QUELLE_ARTEN)}.

AUSGABE: Schreibe NUR in die Datei {ausgabe}, als JSON:
{{"kandidaten": [{{"titel": "...", "fall": "...", "quelle_art": "reportage", "belege": [{{"url": "https://...",
"zitat": "..."}}], "lebenswelt": "...", "strafzweck": "...", "gewalt": false}}],
"verworfen": [{{"titel": "...", "grund": "...", "regeln": ["L3"]}}], "luecken": ["..."]}}
Antworte danach mit einem Satz."""


def weiter_prompt(ausgabe: str) -> str:
    return f"""Suche im selben Fenster weiter: andere Suchanfragen, andere Quellen, Spuren, die du noch nicht
verfolgt hast. Ergänze die Datei {ausgabe} (vollständig neu schreiben, bisherige Kandidaten behalten, nur
bessere dazu oder schwache nach "verworfen"). Gleiches Format, gleiche Regeln. Antworte danach mit einem Satz."""


def nachbesserung_prompt(liste: list[str], ausgabe: str) -> str:
    zeilen = "\n".join(f"- {x}" for x in liste)
    return f"""Python hat geprüft. Das ist durchgefallen:
{zeilen}

Korrigiere es: Zitat wörtlich von der Seite übernehmen (WebFetch erneut nutzen), anderen Beleg suchen, Feld
ergänzen oder den Kandidaten nach "verworfen" verschieben. Nichts erfinden. Schreibe die VOLLSTÄNDIGE Datei
neu nach {ausgabe}, im selben Format. Antworte danach mit einem Satz."""


def sammeln_lesen(pfad: Path) -> tuple[dict, list[str]]:
    """Claudes sammeln-<fenster>.json. Gibt (daten mit gültigen Kandidaten, Fehlerliste) zurück; ungültige
    Kandidaten fallen heraus und stehen in der Fehlerliste (für die Nachbesserung)."""
    daten = _json(pfad)
    fehler, gut = [], []
    kandidaten = daten.get("kandidaten")
    if not isinstance(kandidaten, list):
        raise FallFehler(f"{Path(pfad).name}: kandidaten fehlt")
    for i, k in enumerate(kandidaten):
        f = []
        if not isinstance(k, dict):
            fehler.append(f"kandidaten[{i}]: Objekt erwartet")
            continue
        for feld in ("titel", "fall", "lebenswelt", "strafzweck"):
            if not _text(k.get(feld)):
                f.append(f"{feld} fehlt")
        if _text(k.get("fall")) and len(k["fall"]) > MAX_FALL:
            f.append(f"fall länger als {MAX_FALL} Zeichen")
        if k.get("quelle_art") not in QUELLE_ARTEN:
            f.append(f"quelle_art muss eines von {', '.join(QUELLE_ARTEN)} sein")
        if not isinstance(k.get("gewalt"), bool):
            f.append("gewalt muss true oder false sein")
        belege = k.get("belege")
        if not isinstance(belege, list) or not belege:
            f.append("mindestens ein Beleg nötig")
        elif not all(isinstance(b, dict) and _text(b.get("url")) and _text(b.get("zitat")) for b in belege):
            f.append("Belege brauchen url und zitat")
        if f:
            fehler.append(f"kandidaten[{i}] ({str(k.get('titel', ''))[:60]}): {'; '.join(f)}")
        else:
            gut.append(k)
    verworfen = [v for v in daten.get("verworfen", []) if isinstance(v, dict) and _text(v.get("titel"))]
    luecken = [x for x in daten.get("luecken", []) if _text(x)]
    return {"kandidaten": gut, "verworfen": verworfen, "luecken": luecken}, fehler


def belege_pruefen(daten: dict, domains: list[str], seitentext) -> dict:
    """Je Beleg "pruefung" (webpruefung.beleg_pruefen), je Kandidat "status": belegt | ungeprueft | nicht_belegt."""
    for k in daten["kandidaten"]:
        for b in k["belege"]:
            try:
                b["pruefung"] = webpruefung.beleg_pruefen(b, domains, seitentext, {})
            except (UnicodeError, OSError, ValueError) as e:  # eine kaputte Adresse darf das Fenster nicht kosten
                b["pruefung"] = {"status": "durchgefallen", "vermerk": f"Seite nicht ladbar: {e}"}
        werte = {b["pruefung"]["status"] for b in k["belege"]}
        k["status"] = "belegt" if "bestanden" in werte else "ungeprueft" if "ungeprueft" in werte else "nicht_belegt"
    return daten


def durchgefallene(daten: dict) -> list[str]:
    aus = []
    for i, k in enumerate(daten["kandidaten"]):
        if k.get("status") == "nicht_belegt":
            for b in k["belege"]:
                aus.append(f"kandidaten[{i}] ({k['titel'][:60]}): {b['url']} | Zitat: {b['zitat']!r} -> "
                           f"{b['pruefung']['vermerk']}")
    return aus


def _url_schluessel(url: str) -> str:
    t = urlsplit(url.strip())
    return f"{(t.hostname or '').removeprefix('www.')}{t.path.rstrip('/')}"


def zusammenfuehren(je_fenster: dict[str, dict]) -> dict:
    """Alle Fenster zusammen: Kandidaten mit Beleg (belegt oder ungeprüft) bekommen ids F01…; doppelte
    (gleiche Beleg-URL oder gleicher Titel) werden vereint. Nicht belegte kommen nach "nicht_belegt"."""
    faelle, nicht_belegt, verworfen, luecken = [], [], [], []
    for fenster, d in je_fenster.items():
        verworfen += [{**v, "fenster": fenster} for v in d["verworfen"]]
        luecken += [f"{FENSTER[fenster][0]}: {x}" for x in d["luecken"]]
        for k in d["kandidaten"]:
            if k["status"] == "nicht_belegt":
                nicht_belegt.append({**k, "fenster": [fenster]})
                continue
            urls = {_url_schluessel(b["url"]) for b in k["belege"]}
            titel = k["titel"].strip().lower()
            gleich = next((f for f in faelle if urls & f["_urls"] or f["titel"].strip().lower() == titel), None)
            if gleich:
                neu = [b for b in k["belege"] if _url_schluessel(b["url"]) not in gleich["_urls"]]
                gleich["belege"] += neu
                gleich["_urls"] |= urls
                gleich["fenster"].append(fenster)
                if k["status"] == "belegt":
                    gleich["status"] = "belegt"
                continue
            faelle.append({**k, "fenster": [fenster], "_urls": urls})
    for i, f in enumerate(faelle, 1):
        f["id"] = f"F{i:02d}"
        del f["_urls"]
    return {"faelle": faelle, "nicht_belegt": nicht_belegt, "verworfen": verworfen, "luecken": luecken}


# --- Stufe 2: Abgleich, Stufe 3: Dossier ------------------------------------------------------------------

def _faelle_json(faelle: list[dict]) -> str:
    kurz = [{"id": f["id"], "titel": f["titel"], "fall": f["fall"], "quelle_art": f["quelle_art"],
             "beleg": f["status"], "quellen": [b["url"] for b in f["belege"]], "lebenswelt": f["lebenswelt"],
             "strafzweck": f["strafzweck"], "gewalt": f["gewalt"]} for f in faelle]
    return json.dumps(kurz, ensure_ascii=False, indent=1)


def abgleich_prompt(faelle: list[dict], kontext: dict, ausgabe: str) -> str:
    kriterien = "\n".join(f"- {k}: {v}" for k, v in KRITERIEN.items())
    return f"""Aufgabe: Gleiche jeden gefundenen Fall gegen das Regelwerk für Lias Examensreihe ab. Du brauchst dafür
kein Web; alles steht hier. Sei streng und konkret: Lia soll diesen Abgleich nicht mehr selbst machen müssen.

REIHE UND LERNGRUPPE
{kontext['reihe']}

PRÜFUNGSANGABEN
{kontext['examen']}

REGELWERK (Kennungen L, P, F, R, K, G)
{kontext['regelwerk']}

LIAS GELERNTE REGELN
{_liste(kontext['gelernte'])}

LEITFADEN „So unterrichtet Lia“
{kontext['leitfaden']}

VORBILD DES FACHSEMINARS
{kontext['vorbild']}

RUBRIK (Entwurf, Kriterien einer guten Reihe)
{kontext['rubrik']}

FÄLLE (JSON; "beleg": belegt = wörtlich geprüft, ungeprueft = Quelle nicht auf der Liste)
{_faelle_json(faelle)}

PRÜFKRITERIEN je Fall, je mit stufe ({" | ".join(STUFEN)}), begruendung (konkret, höchstens
{MAX_BEGRUENDUNG} Zeichen) und regeln (Kennungen, auf die sich das Urteil stützt, mindestens eine):
{kriterien}
Dazu "gefaehrdet": Kennungen der Regeln, die der Fall verletzen oder gefährden würde (leer, wenn keine), und
"gesamt" ({" | ".join(STUFEN)}). Nur Kennungen aus dem Regelwerk oder GR<n>.

AUSGABE: Schreibe NUR in die Datei {ausgabe}, als JSON, jede id genau einmal:
{{"faelle": [{{"id": "F01", "kriterien": {{"lebenswelt": {{"stufe": "stark", "begruendung": "...", "regeln": ["L2"]}},
"passung": {{...}}, "regeln": {{...}}, "natuerlich": {{...}}, "tragweite": {{...}}}}, "gefaehrdet": [], "gesamt": "stark"}}]}}
Antworte danach mit einem Satz."""


def abgleich_lesen(pfad: Path, ids: list[str], regel_ids: set[str]) -> tuple[dict[str, dict], list[str]]:
    """Gültige Abgleiche {id: eintrag} und Fehlerliste."""
    daten = _json(pfad)
    if not isinstance(daten.get("faelle"), list):
        raise FallFehler(f"{Path(pfad).name}: faelle fehlt")
    gut, fehler, gesehen = {}, [], set()
    for e in daten["faelle"]:
        fid = e.get("id") if isinstance(e, dict) else None
        if fid not in ids:
            fehler.append(f"unbekannte id {fid!r}")
            continue
        if fid in gesehen:
            fehler.append(f"{fid} doppelt")
            continue
        gesehen.add(fid)
        f = []
        kr = e.get("kriterien") if isinstance(e.get("kriterien"), dict) else {}
        for k in KRITERIEN:
            w = kr.get(k)
            if not isinstance(w, dict):
                f.append(f"{k} fehlt")
                continue
            if w.get("stufe") not in STUFEN:
                f.append(f"{k}.stufe muss {'|'.join(STUFEN)} sein")
            if not _text(w.get("begruendung")) or len(w["begruendung"]) > MAX_BEGRUENDUNG:
                f.append(f"{k}.begruendung fehlt oder ist länger als {MAX_BEGRUENDUNG} Zeichen")
            r = w.get("regeln")
            if not isinstance(r, list) or not r:
                f.append(f"{k}.regeln: mindestens eine Kennung")
            elif unbekannt := [x for x in r if x not in regel_ids]:
                f.append(f"{k}.regeln: unbekannte Kennungen {unbekannt}")
        g = e.get("gefaehrdet", [])
        if not isinstance(g, list) or [x for x in g if x not in regel_ids]:
            f.append("gefaehrdet: nur bekannte Kennungen")
        if e.get("gesamt") not in STUFEN:
            f.append(f"gesamt muss {'|'.join(STUFEN)} sein")
        if f:
            fehler.append(f"{fid}: {'; '.join(f)}")
        else:
            gut[fid] = e
    fehler += [f"{i}: fehlt" for i in ids if i not in gesehen]
    return gut, fehler


def verworfen_ids(verworfen: list[dict]) -> dict[str, dict]:
    return {f"V{i:02d}": v for i, v in enumerate(verworfen, 1)}


KENNUNG = re.compile(r"\b(?:GR|[LPFRKGE])\d+\b")


def fallwoerter(faelle: list[dict], allgemein: str) -> set[str]:
    """Wörter, die eine Reihenfrage an einen Fall binden: groß geschriebene Wörter aus Titeln und Fallberichten,
    die nicht im allgemeinen Kontext stehen und in höchstens zwei Fällen vorkommen (Namen, Orte, Marken)."""
    allgemein = allgemein.lower()
    zaehler: dict[str, int] = {}
    for f in faelle:
        for w in set(re.findall(r"\b[A-ZÄÖÜ][\wäöüß-]{2,}", f"{f['titel']} {f['fall']}")):
            zaehler[w] = zaehler.get(w, 0) + 1
    return {w for w, n in zaehler.items() if n <= 2 and w.lower() not in allgemein}


def dossier_prompt(faelle: list[dict], abgleich: dict[str, dict], verworfen: dict[str, dict], kontext: dict,
                   ausgabe: str) -> str:
    uebersicht = [{"id": f["id"], "titel": f["titel"], "fall": f["fall"], "gewalt": f["gewalt"],
                   "gesamt": abgleich[f["id"]]["gesamt"],
                   "abgleich": {k: f"{w['stufe']}: {w['begruendung']}" for k, w in abgleich[f["id"]]["kriterien"].items()},
                   "gefaehrdet": abgleich[f["id"]]["gefaehrdet"]} for f in faelle if f["id"] in abgleich]
    weg = [{"id": k, "titel": v["titel"], "grund": v.get("grund", "")} for k, v in verworfen.items()]
    fragen = "\n".join(f"- {q}" for q in kontext["reihenfragen"]) or "(keine)"
    return f"""Aufgabe: Schreibe das Dossier für Lia aus einer fertigen Fallsuche. Kein Web nötig.
Lia ist Lehrerin; sie liest das Dossier und spricht danach ihr Feedback ein. Es soll sie nicht erschlagen:
kurz, klar, ohne Regel-Kennungen (L1, P3, GR2 usw.) in den Texten für sie.

REIHE UND LERNGRUPPE
{kontext['reihe']}

REGELWERK (für dich; Kennungen nur in den Feldern "regeln")
{kontext['regelwerk']}

LIAS GELERNTE REGELN
{_liste(kontext['gelernte'])}

FÄLLE MIT ABGLEICH (JSON)
{json.dumps(uebersicht, ensure_ascii=False, indent=1)}

BEIM SUCHEN VERWORFEN (JSON)
{json.dumps(weg, ensure_ascii=False, indent=1)}

1. "auswahl": die stärksten Fälle (höchstens {MAX_AUSWAHL}, gesamt „stark“; „mittel“ nur, wenn es weniger als drei
   starke gibt). Je Fall "kurztitel" (höchstens 60 Zeichen), "warum" (warum er für diese Klasse trägt) und
   "achten" (worauf Lia achten muss), je höchstens {MAX_LIA} Zeichen, in normaler Sprache.
2. "leitfragen": drei bis fünf mögliche Reihenfragen. WICHTIG: Eine Reihenfrage ist allgemein, wie Lias eigene:
{fragen}
   Also keine Namen, Orte, Zahlen oder Einzelheiten aus einem Fall, höchstens {MAX_FRAGE} Zeichen, für Klasse 8
   verständlich, offen, mit zwei klar getrennten Antworten ("pole"). Der Fall ist der Einstieg, nicht die Frage:
   "einstieg" sagt in ein bis zwei Sätzen, wie ein ausgewählter Fall ("faelle") zur Frage führt. "kant" und
   "liszt": wie die beiden die Frage beantworten, je ein bis zwei Sätze, fachlich korrekt (von Liszt will Besserung
   durch Strafe, auch Haft), mit "belege_register" (Verweise unten, genau als „<quelle>:<seite>“). Dazu "rlp"
   (ids unten) und "regeln" (Kennungen, die die Frage erfüllt).
3. "auch_interessant": höchstens {MAX_INTERESSANT} weitere Fälle, die Lia wahrscheinlich interessieren, aus den
   übrigen Fällen (id F..) oder den verworfenen (id V..), je "ref" und "warum" (ein Satz). Abwegiges weglassen.
4. "rueckfragen": höchstens {MAX_RUECKFRAGEN}, nur was Lia wirklich entscheiden muss.

GEPRÜFTE STELLEN (Quellenregister)
{kontext['register']}

RLP-AUSZUG
{_liste(kontext['rlp'])}

AUSGABE: Schreibe NUR in die Datei {ausgabe}, als JSON:
{{"auswahl": [{{"id": "F01", "kurztitel": "...", "warum": "...", "achten": "..."}}],
"leitfragen": [{{"frage": "...", "pole": ["...", "..."], "faelle": ["F01"], "einstieg": "...", "kant": "...",
"liszt": "...", "belege_register": ["kant-mds-strafrecht:331"], "rlp": ["..."], "regeln": ["P1"]}}],
"auch_interessant": [{{"ref": "V03", "warum": "..."}}], "rueckfragen": ["..."]}}
Antworte danach mit einem Satz."""


def _lia_text(wert, feld: str, f: list[str], laenge: int = MAX_LIA) -> None:
    if not _text(wert) or len(wert) > laenge:
        f.append(f"{feld} fehlt oder länger als {laenge} Zeichen")
    elif KENNUNG.search(wert):
        f.append(f"{feld}: keine Regel-Kennungen im Text für Lia ({KENNUNG.search(wert).group(0)})")


def dossier_lesen(pfad: Path, abgleich: dict[str, dict], regel_ids: set[str], rlp_ids: set[str],
                  register_ids: set[str], verworfen: dict[str, dict] = None,
                  fallbezug: set[str] = frozenset()) -> tuple[dict, list[str]]:
    """Dossier prüfen. Gibt (daten, fehler) zurück; fehlerhafte Teile sind entfernt."""
    daten = _json(pfad)
    verworfen = verworfen or {}
    fehler, auswahl = [], []
    for a in daten.get("auswahl", []) if isinstance(daten.get("auswahl"), list) else []:
        f = []
        if not isinstance(a, dict) or a.get("id") not in abgleich:
            fehler.append(f"auswahl: {a!r:.80} (id aus dem Abgleich nötig)")
            continue
        _lia_text(a.get("kurztitel"), "kurztitel", f, 60)
        _lia_text(a.get("warum"), "warum", f)
        _lia_text(a.get("achten"), "achten", f)
        if f:
            fehler.append(f"auswahl {a['id']}: {'; '.join(f)}")
        elif a["id"] not in {x["id"] for x in auswahl}:
            auswahl.append(a)
    if not auswahl:
        fehler.append("auswahl ist leer")
    if len(auswahl) > MAX_AUSWAHL:
        fehler.append(f"höchstens {MAX_AUSWAHL} Fälle")
        auswahl = auswahl[:MAX_AUSWAHL]
    gewaehlt = {a["id"] for a in auswahl}
    leitfragen = []
    for i, q in enumerate(daten.get("leitfragen", []) if isinstance(daten.get("leitfragen"), list) else []):
        f = []
        if not isinstance(q, dict):
            fehler.append(f"leitfragen[{i}]: Objekt erwartet")
            continue
        frage = q.get("frage")
        _lia_text(frage, "frage", f, MAX_FRAGE)
        if _text(frage):
            if re.search(r"\d", frage):
                f.append("frage: keine Zahlen aus dem Fall, allgemein formulieren")
            if gebunden := sorted(w for w in fallbezug if re.search(rf"\b{re.escape(w)}\b", frage)):
                f.append(f"frage: allgemein formulieren wie Lias Reihenfragen, ohne {', '.join(gebunden)}")
        pole = q.get("pole")
        if not (isinstance(pole, list) and len(pole) == 2 and all(_text(p) for p in pole)):
            f.append("pole: genau zwei Texte")
        fl = q.get("faelle")
        if not isinstance(fl, list) or not fl or [x for x in fl if x not in gewaehlt]:
            f.append("faelle: nur ids aus der auswahl, mindestens eine")
        for feld in ("einstieg", "kant", "liszt"):
            _lia_text(q.get(feld), feld, f)
        for feld, erlaubt in (("belege_register", register_ids), ("rlp", rlp_ids), ("regeln", regel_ids)):
            werte = q.get(feld)
            if not isinstance(werte, list) or not werte:
                f.append(f"{feld}: mindestens ein Eintrag")
            elif unbekannt := [x for x in werte if x not in erlaubt]:
                f.append(f"{feld}: unbekannt {unbekannt}")
        if f:
            fehler.append(f"leitfragen[{i}] ({str(frage or '')[:60]}): {'; '.join(f)}")
        else:
            leitfragen.append(q)
    if not leitfragen:
        fehler.append("keine gültige Leitfrage")
    interessant = []
    for x in daten.get("auch_interessant", []) if isinstance(daten.get("auch_interessant"), list) else []:
        f = []
        ref = x.get("ref") if isinstance(x, dict) else None
        if ref in gewaehlt or not (ref in abgleich or ref in verworfen):
            fehler.append(f"auch_interessant: {ref!r} ist kein übriger Fall (F..) oder verworfener (V..)")
            continue
        _lia_text(x.get("warum"), "warum", f)
        if f:
            fehler.append(f"auch_interessant {ref}: {'; '.join(f)}")
        elif len(interessant) < MAX_INTERESSANT:
            interessant.append(x)
    rueck = [x for x in daten.get("rueckfragen", []) if _text(x) and not KENNUNG.search(x)][:MAX_RUECKFRAGEN]
    return {"auswahl": auswahl, "leitfragen": leitfragen, "auch_interessant": interessant, "rueckfragen": rueck}, fehler


# --- Dossier als docx (Renderer, Art arbeitsblatt) --------------------------------------------------------

def _quelle(f: dict) -> str:
    """Erste Quelle mit geprüftem Zitat, sonst die erste."""
    belege = sorted(f["belege"], key=lambda b: b.get("pruefung", {}).get("status") != "bestanden")
    b = belege[0]
    return b["url"] + ("" if b.get("pruefung", {}).get("status") == "bestanden" else " (Zitat nicht geprüft)")


def beschreibung(titel: str, ges: dict, dossier: dict, zahlen: dict) -> dict:
    """Schlankes Dossier für Lia: Reihenfragen, stärkste Fälle, einige weitere, offene Fragen. Keine Kennungen,
    keine langen Listen (alles Übrige steht in den JSON-Dateien)."""
    nach_id = {f["id"]: f for f in ges["faelle"]}
    verworfen = verworfen_ids(ges["verworfen"])
    kurz = {a["id"]: a["kurztitel"] for a in dossier["auswahl"]}
    bloecke = [{"typ": "absatz", "text": (
        f"Die Agenten haben {zahlen['faelle'] + zahlen['verworfen']} reale Fälle angesehen (Nachrichten, Urteile, "
        "Social Media, Popkultur, Alltag) und jeden gegen deine Regeln, Rosenbergers Vorgaben und die Kritik an "
        f"früheren Reihen geprüft. Hier stehen nur die stärksten {len(dossier['auswahl'])} und die Reihenfragen, "
        "die sich daraus ergeben.")}]
    bloecke.append({"typ": "ueberschrift", "text": "Mögliche Reihenfragen", "ebene": 1})
    for i, q in enumerate(dossier["leitfragen"], 1):
        bloecke.append({"typ": "merksatz", "titel": f"Reihenfrage {i}", "text": q["frage"]})
        einstieg = ", ".join(kurz[x] for x in q["faelle"])
        bloecke.append({"typ": "liste", "punkte": [
            f"Zwei Antworten: {q['pole'][0].rstrip('.')} oder {q['pole'][1].rstrip('.')}.",
            f"Einstieg ({einstieg}): {q['einstieg']}",
            f"Kant: {q['kant']}",
            f"Von Liszt: {q['liszt']}"]})
    bloecke.append({"typ": "ueberschrift", "text": "Die stärksten Fälle", "ebene": 1})
    for a in dossier["auswahl"]:
        f = nach_id[a["id"]]
        bloecke.append({"typ": "material", "titel": a["kurztitel"] + (" (mit Gewalt)" if f["gewalt"] else ""),
                        "text": f["fall"]})
        bloecke.append({"typ": "liste", "punkte": [f"Warum er trägt: {a['warum']}", f"Worauf achten: {a['achten']}",
                                                   f"Quelle: {_quelle(f)}"]})
    if dossier["auch_interessant"]:
        bloecke.append({"typ": "ueberschrift", "text": "Vielleicht auch interessant", "ebene": 1})
        punkte = []
        for x in dossier["auch_interessant"]:
            if x["ref"] in nach_id:
                punkte.append(f"{nach_id[x['ref']]['titel']}: {x['warum']}")
            else:
                punkte.append(f"{verworfen[x['ref']]['titel']} (beim Suchen aussortiert): {x['warum']}")
        bloecke.append({"typ": "liste", "punkte": punkte})
    if dossier["rueckfragen"]:
        bloecke.append({"typ": "ueberschrift", "text": "Offene Fragen an dich", "ebene": 1})
        bloecke.append({"typ": "liste", "punkte": dossier["rueckfragen"]})
    return {"art": "arbeitsblatt", "titel": titel[:200], "nummer": "F", "bloecke": bloecke}
