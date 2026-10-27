"""Fallsuche: reine Logik ohne Netz (Kontext, Prompts, Prüfung von Claudes Dateien, Dossier-Beschreibung).

Auftrag Jan/Lia vom 27.10.2026: offene, gründliche Suche nach starken realen Fällen für Lias Examensreihe
(Straftheorien, Klasse 8), laufend gegen regelwerk_reihe.md abgeglichen; daraus Problem- bzw. Leitfragen.
Ablauf und Claude-Läufe stehen in fallsuche.py. Drei Dateiformate (von Claude geschrieben, hier geprüft):

sammeln-<fenster>.json  {"kandidaten": [{"titel", "fall", "quelle_art", "belege": [{"url", "zitat"}],
                          "lebenswelt", "strafzweck", "gewalt": bool}],
                         "verworfen": [{"titel", "grund", "regeln": [...]}], "luecken": [...]}
abgleich.json           {"faelle": [{"id", "kriterien": {<kriterium>: {"stufe", "begruendung", "regeln"}},
                          "gefaehrdet": [...], "gesamt"}]}
dossier.json            {"auswahl": [{"id", "warum"}], "leitfragen": [{"frage", "pole": [a, b], "faelle",
                          "kant", "liszt", "belege_register", "rlp", "regeln", "begruendung"}], "rueckfragen"}
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
MAX_FRAGE = 150
MAX_AUSWAHL = 8
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
            b["pruefung"] = webpruefung.beleg_pruefen(b, domains, seitentext, {})
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


def dossier_prompt(kontext: dict, ausgabe: str) -> str:
    return f"""Nächster Schritt: das Dossier. Wähle aus deinem Abgleich die stärksten Fälle (höchstens {MAX_AUSWAHL},
nur gesamt „stark“; „mittel“ nur, wenn es weniger als drei starke gibt, dann sag das in "rueckfragen").
Entwickle daraus Problem- bzw. Leitfragen für mögliche Reihen. Das ist der eigentliche Kern.

Für jede Leitfrage (drei bis sechs):
- "frage": höchstens {MAX_FRAGE} Zeichen, für Klasse 8 verständlich, nach dem Regelwerk (P1–P7, K4–K6).
- "pole": genau zwei Antworten, die sich klar widersprechen.
- "faelle": ids der gewählten Fälle, die sie tragen.
- "kant" und "liszt": wie die beiden Positionen die Frage am Fall beantworten, je ein bis zwei Sätze, fachlich
  korrekt (K1: von Liszt will Besserung durch Strafe, auch Haft). "belege_register": Verweise auf die geprüften
  Stellen unten, genau als „<quelle>:<seite>“.
- "rlp": ids aus dem RLP-Auszug unten. "regeln": Kennungen, die die Frage erfüllt. "begruendung": warum diese
  Frage trägt, höchstens {MAX_BEGRUENDUNG} Zeichen.
Keine Bewertungsbögen.

GEPRÜFTE STELLEN (Quellenregister)
{kontext['register']}

RLP-AUSZUG
{_liste(kontext['rlp'])}

AUSGABE: Schreibe NUR in die Datei {ausgabe}, als JSON:
{{"auswahl": [{{"id": "F01", "warum": "..."}}], "leitfragen": [{{"frage": "...", "pole": ["...", "..."],
"faelle": ["F01"], "kant": "...", "liszt": "...", "belege_register": ["kant-mds-strafrecht:331"], "rlp": ["..."],
"regeln": ["P3"], "begruendung": "..."}}], "rueckfragen": ["..."]}}
Antworte danach mit einem Satz."""


def dossier_lesen(pfad: Path, abgleich: dict[str, dict], regel_ids: set[str], rlp_ids: set[str],
                  register_ids: set[str]) -> tuple[dict, list[str]]:
    """Dossier prüfen. Gibt (daten, fehler) zurück; bei Fehlern sind die betroffenen Teile entfernt."""
    daten = _json(pfad)
    fehler = []
    auswahl = []
    for a in daten.get("auswahl", []) if isinstance(daten.get("auswahl"), list) else []:
        if not isinstance(a, dict) or a.get("id") not in abgleich or not _text(a.get("warum")):
            fehler.append(f"auswahl: {a!r:.80} (id aus dem Abgleich und warum nötig)")
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
        if not _text(q.get("frage")) or len(q["frage"]) > MAX_FRAGE:
            f.append(f"frage fehlt oder länger als {MAX_FRAGE} Zeichen")
        pole = q.get("pole")
        if not (isinstance(pole, list) and len(pole) == 2 and all(_text(p) for p in pole)):
            f.append("pole: genau zwei Texte")
        fl = q.get("faelle")
        if not isinstance(fl, list) or not fl or [x for x in fl if x not in gewaehlt]:
            f.append("faelle: nur ids aus der auswahl, mindestens eine")
        for feld in ("kant", "liszt", "begruendung"):
            if not _text(q.get(feld)) or len(q[feld]) > MAX_BEGRUENDUNG:
                f.append(f"{feld} fehlt oder länger als {MAX_BEGRUENDUNG} Zeichen")
        for feld, erlaubt in (("belege_register", register_ids), ("rlp", rlp_ids), ("regeln", regel_ids)):
            werte = q.get(feld)
            if not isinstance(werte, list) or not werte:
                f.append(f"{feld}: mindestens ein Eintrag")
            elif unbekannt := [x for x in werte if x not in erlaubt]:
                f.append(f"{feld}: unbekannt {unbekannt}")
        if f:
            fehler.append(f"leitfragen[{i}] ({str(q.get('frage', ''))[:60]}): {'; '.join(f)}")
        else:
            leitfragen.append(q)
    if not leitfragen:
        fehler.append("keine gültige Leitfrage")
    rueck = [x for x in daten.get("rueckfragen", []) if _text(x)]
    return {"auswahl": auswahl, "leitfragen": leitfragen, "rueckfragen": rueck}, fehler


# --- Dossier als docx (Renderer, Art arbeitsblatt) --------------------------------------------------------

def _liste_bloecke(punkte: list[str], nummeriert: bool = False) -> list[dict]:
    punkte = [p[:4900] for p in punkte]
    return [{"typ": "liste", "punkte": punkte[i:i + 50], "nummeriert": nummeriert} for i in range(0, len(punkte), 50)]


def _quellen(f: dict) -> str:
    teile = []
    for b in f["belege"]:
        st = b.get("pruefung", {}).get("status", "")
        teile.append(f"{b['url']} ({'Zitat geprüft' if st == 'bestanden' else 'ungeprüft' if st == 'ungeprueft' else st})")
    return "; ".join(teile)


def beschreibung(titel: str, ges: dict, abgleich: dict[str, dict], dossier: dict, regeltexte: dict[str, str],
                 zahlen: dict) -> dict:
    """Renderer-Beschreibung: Leitfragen, gewählte Fälle mit Abgleich, weitere Fälle, Verworfenes, Lücken,
    Rückfragen, Kurzfassung der genannten Regeln."""
    nach_id = {f["id"]: f for f in ges["faelle"]}
    genannt: set[str] = set()
    bloecke = [{"typ": "absatz", "text": (
        f"Automatisch recherchiert in {zahlen['fenster']} Suchfenstern, von Python geprüft. {zahlen['faelle']} Fälle "
        f"mit Quelle gefunden ({zahlen['belegt']} mit wörtlich geprüftem Zitat, {zahlen['ungeprueft']} nur mit Quelle "
        f"außerhalb der Liste), {zahlen['verworfen']} schon bei der Suche verworfen, {zahlen['nicht_belegt']} ohne "
        f"gültigen Beleg aussortiert. Alle Fälle gegen das Regelwerk abgeglichen; Kennungen in Klammern, Kurzfassung "
        "am Ende. Ausgewählt sind die stärksten Fälle.")}]
    bloecke.append({"typ": "ueberschrift", "text": "Leitfragen", "ebene": 1})
    for q in dossier["leitfragen"]:
        genannt |= set(q["regeln"])
        bloecke.append({"typ": "ueberschrift", "text": q["frage"], "ebene": 2})
        bloecke.append({"typ": "absatz", "text": (
            f"Pole: {q['pole'][0]} / {q['pole'][1]}. Fälle: {', '.join(nach_id[x]['titel'] + ' (' + x + ')' for x in q['faelle'])}. "
            f"Kant: {q['kant']} Von Liszt: {q['liszt']} Belege: {', '.join(q['belege_register'])}. RLP: "
            f"{', '.join(q['rlp'])}. Warum: {q['begruendung']} ({', '.join(q['regeln'])})")[:5000]})
    bloecke.append({"typ": "ueberschrift", "text": "Ausgewählte Fälle", "ebene": 1})
    for a in dossier["auswahl"]:
        f, e = nach_id[a["id"]], abgleich[a["id"]]
        marke = " (mit Gewalt)" if f["gewalt"] else ""
        bloecke.append({"typ": "ueberschrift", "text": f"{f['id']} {f['titel']}{marke}"[:200], "ebene": 2})
        bloecke.append({"typ": "absatz", "text": f"{f['fall']} Quellen: {_quellen(f)}"[:5000]})
        punkte = []
        for k, frage in KRITERIEN.items():
            w = e["kriterien"][k]
            genannt |= set(w["regeln"])
            punkte.append(f"{frage} {w['stufe']}: {w['begruendung']} ({', '.join(w['regeln'])})")
        if e["gefaehrdet"]:
            genannt |= set(e["gefaehrdet"])
            punkte.append(f"Gefährdet: {', '.join(e['gefaehrdet'])}")
        punkte.append(f"Gesamt: {e['gesamt']}. Warum ausgewählt: {a['warum']}")
        bloecke += _liste_bloecke(punkte)
    gewaehlt = {a["id"] for a in dossier["auswahl"]}
    weitere = [f"{f['id']} {f['titel']}: {abgleich[f['id']]['gesamt'] if f['id'] in abgleich else 'nicht abgeglichen'}"
               f"{'; gefährdet ' + ', '.join(abgleich[f['id']]['gefaehrdet']) if abgleich.get(f['id'], {}).get('gefaehrdet') else ''}"
               f". {_quellen(f)}" for f in ges["faelle"] if f["id"] not in gewaehlt]
    for kopf, punkte in (
        ("Weitere geprüfte Fälle", weitere),
        ("Bei der Suche verworfen", [f"{v['titel']}: {v.get('grund', '')} ({', '.join(v.get('regeln', []))})"
                                     for v in ges["verworfen"]]),
        ("Ohne gültigen Beleg aussortiert", [f"{k['titel']}: {_quellen(k)}" for k in ges["nicht_belegt"]]),
        ("Lücken", ges["luecken"]),
        ("Rückfragen", dossier["rueckfragen"]),
    ):
        if punkte:
            bloecke.append({"typ": "ueberschrift", "text": kopf, "ebene": 1})
            bloecke += _liste_bloecke(punkte)
    regeln = [f"{k}: {regeltexte[k]}" for k in regeltexte if k in genannt]
    if regeln:
        bloecke.append({"typ": "ueberschrift", "text": "Genannte Regeln (Kurzfassung)", "ebene": 1})
        bloecke += _liste_bloecke(regeln)
    return {"art": "arbeitsblatt", "titel": titel[:200], "nummer": "F", "bloecke": bloecke[:200]}
